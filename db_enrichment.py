"""
db_enrichment.py — Protellect Database Enrichment Layer v2

Queries live databases for ANY protein:
  UniProt  — function, domains, active/binding sites, natural variants, PTMs
  ClinVar  — variant pathogenicity for any gene/position
  PDB      — auto-selects best available structure, B-factors, resolution
  InterPro — domain family classification
  Ensembl  — gene-level annotation from ENSG IDs
  AlphaFold — fallback structure when no experimental PDB available
"""

import requests
import json
import time
import re
import os
from pathlib import Path
from typing import Optional

CACHE_DIR = Path(".protellect_cache")
CACHE_DIR.mkdir(exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Protellect/2.0 (computational biology platform; contact: research@protellect.com)",
    "Accept": "application/json",
})


def _cache_key(key: str) -> Path:
    safe = re.sub(r'[^a-zA-Z0-9_\-]', '_', key)[:120]
    return CACHE_DIR / f"{safe}.json"


def _load(key: str):
    p = _cache_key(key)
    if p.exists():
        try:
            return json.load(open(p))
        except Exception:
            pass
    return None


def _save(key: str, data):
    try:
        json.dump(data, open(_cache_key(key),'w'))
    except Exception:
        pass


def _get(url: str, params=None, timeout=12) -> Optional[dict]:
    try:
        r = SESSION.get(url, params=params, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _get_text(url: str, timeout=20) -> Optional[str]:
    try:
        r = SESSION.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════════════════════
# PROTEIN AUTO-DETECTION FROM DATA
# ══════════════════════════════════════════════════════════════════════════

def detect_protein_from_data(df, context: dict = None) -> dict:
    """Auto-detect protein/gene from dataset. Returns {gene_name, uniprot_id, confidence, source}."""
    result = {"uniprot_id":None,"gene_name":None,"organism":"human",
              "confidence":0.0,"source":"not detected","ensg_id":None}

    # 1. Scientist Q&A takes highest priority
    if context:
        prot = context.get("protein_of_interest","").strip()
        if prot and len(prot) >= 2:
            result.update({"gene_name":prot.upper(),"confidence":0.95,"source":"scientist Q&A"})
            uid = lookup_uniprot_by_gene(prot)
            if uid: result["uniprot_id"] = uid
            return result

    # 2. Mutation column gene prefixes (e.g. TP53_R175H)
    if "mutation" in df.columns:
        for m in df["mutation"].dropna().astype(str).tolist()[:100]:
            g = re.match(r'^([A-Z][A-Z0-9]{1,9})_', m)
            if g:
                gene = g.group(1)
                uid  = lookup_uniprot_by_gene(gene)
                result.update({"gene_name":gene,"confidence":0.85,"source":"mutation prefix",
                                "uniprot_id":uid})
                return result

    # 3. Single-gene gene_name column
    if "gene_name" in df.columns:
        genes = [str(g) for g in df["gene_name"].dropna().unique() if str(g) not in ("nan","")]
        if len(genes) == 1:
            uid = lookup_uniprot_by_gene(genes[0])
            result.update({"gene_name":genes[0],"confidence":0.88,"source":"gene_name column",
                            "uniprot_id":uid})
            return result

    # 4. ENSG IDs
    for col in df.columns:
        if any(x in col.lower() for x in ("ensg","ensembl")):
            vals = [str(v) for v in df[col].dropna() if str(v).startswith("ENSG")][:3]
            if vals:
                gene = ensg_to_gene_name(vals[0])
                uid  = lookup_uniprot_by_gene(gene) if gene else None
                result.update({"ensg_id":vals[0],"gene_name":gene,"confidence":0.75,
                                "source":"ENSG ID","uniprot_id":uid})
                return result

    # 5. Target/protein name column with single value
    for col in df.columns:
        cl = col.lower()
        if any(x in cl for x in ("target","protein","gene")):
            vals = [str(v) for v in df[col].dropna().unique() if str(v) not in ("nan","")]
            if len(vals) == 1:
                uid = lookup_uniprot_by_gene(vals[0])
                result.update({"gene_name":vals[0],"confidence":0.65,"source":f"{col} column",
                                "uniprot_id":uid})
                return result

    return result


# ══════════════════════════════════════════════════════════════════════════
# UNIPROT
# ══════════════════════════════════════════════════════════════════════════

def lookup_uniprot_by_gene(gene_name: str, organism_id: int = 9606) -> Optional[str]:
    """Search UniProt for gene name → return best UniProt accession."""
    if not gene_name: return None
    key = f"uid_{gene_name}_{organism_id}"
    cached = _load(key)
    if cached is not None: return cached

    for query in [
        f'gene_exact:{gene_name} AND organism_id:{organism_id} AND reviewed:true',
        f'gene:{gene_name} AND organism_id:{organism_id} AND reviewed:true',
        f'gene:{gene_name} AND organism_id:{organism_id}',
        f'protein_name:{gene_name} AND organism_id:{organism_id} AND reviewed:true',
    ]:
        data = _get("https://rest.uniprot.org/uniprotkb/search",
                    {"query":query,"format":"json","size":1,"fields":"accession"})
        if data and data.get("results"):
            uid = data["results"][0]["primaryAccession"]
            _save(key, uid); return uid

    _save(key, None); return None


def fetch_uniprot_full(uniprot_id: str) -> dict:
    """Full UniProt annotation: domains, sites, variants, function, PDB IDs."""
    key = f"uni_{uniprot_id}"
    cached = _load(key)
    if cached is not None: return cached

    r = {
        "uniprot_id":uniprot_id,"gene_name":"","protein_name":"","organism":"",
        "function":"","sequence":"","length":0,
        "domains":[],"active_sites":[],"binding_sites":[],
        "natural_variants":[],"ptm_sites":[],"subcellular":[],
        "keywords":[],"pdb_ids":[],"go_terms":[],
    }

    data = _get(f"https://rest.uniprot.org/uniprotkb/{uniprot_id}", {"format":"json"}, timeout=20)
    if not data:
        _save(key, r); return r

    r["gene_name"]    = (data.get("genes",[{}])[0].get("geneName",{}).get("value","") if data.get("genes") else "")
    r["protein_name"] = data.get("proteinDescription",{}).get("recommendedName",{}).get("fullName",{}).get("value","")
    r["organism"]     = data.get("organism",{}).get("scientificName","")
    r["length"]       = data.get("sequence",{}).get("length",0)
    r["sequence"]     = data.get("sequence",{}).get("value","")

    for comment in data.get("comments",[]):
        ct = comment.get("commentType","")
        if ct == "FUNCTION":
            texts = comment.get("texts",[])
            if texts: r["function"] = texts[0].get("value","")[:500]
        elif ct == "SUBCELLULAR LOCATION":
            for loc in comment.get("subcellularLocations",[]):
                v = loc.get("location",{}).get("value","")
                if v: r["subcellular"].append(v)

    for feat in data.get("features",[]):
        ft    = feat.get("type","")
        loc   = feat.get("location",{})
        start = loc.get("start",{}).get("value")
        end   = loc.get("end",{}).get("value",start)
        desc  = feat.get("description","")
        if start is None: continue
        start, end = int(start), int(end)
        if ft in ("Domain","Region","Zinc finger","Coiled coil","Transmembrane","Repeat","Motif"):
            r["domains"].append({"start":start,"end":end,"name":desc,"type":ft})
        elif ft == "Active site":
            r["active_sites"].append(start)
        elif ft in ("Binding site","Metal binding"):
            for p in range(start, end+1): r["binding_sites"].append(p)
        elif ft == "Natural variant":
            orig = feat.get("alternativeSequence",{}).get("originalSequence","")
            var  = feat.get("alternativeSequence",{}).get("alternativeSequences",[""])[0]
            r["natural_variants"].append({"position":start,"original":orig,"variation":var,"note":desc})
        elif ft == "Modified residue":
            r["ptm_sites"].append({"position":start,"description":desc})

    for xref in data.get("uniProtKBCrossReferences",[]):
        db = xref.get("database","")
        if db == "PDB":
            r["pdb_ids"].append(xref.get("id",""))
        elif db == "GO":
            props = {p["key"]:p["value"] for p in xref.get("properties",[])}
            r["go_terms"].append(props.get("GoTerm",""))

    r["keywords"] = [kw.get("value","") for kw in data.get("keywords",[])]
    _save(key, r); return r


# ══════════════════════════════════════════════════════════════════════════
# PDB — AUTO-SELECT BEST STRUCTURE
# ══════════════════════════════════════════════════════════════════════════

def get_best_pdb_id(pdb_ids: list, uniprot_id: str = None) -> Optional[str]:
    """
    Select the best PDB structure: highest resolution, most complete coverage.
    Falls back to first available if API unavailable.
    """
    if not pdb_ids: return None
    key = f"best_pdb_{'_'.join(sorted(pdb_ids[:5]))}"
    cached = _load(key)
    if cached is not None: return cached

    best = None
    best_res = 99.0
    for pdb_id in pdb_ids[:10]:  # check first 10
        try:
            data = _get(f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id.upper()}")
            if not data: continue
            info = data.get("rcsb_entry_info",{})
            res_list = info.get("resolution_combined",[99.0])
            res = float(res_list[0]) if res_list else 99.0
            method = data.get("exptl",[{}])[0].get("method","")
            # Prefer X-ray/cryo-EM over NMR; prefer higher resolution
            is_good = method in ("X-RAY DIFFRACTION","ELECTRON MICROSCOPY")
            if res < best_res and is_good:
                best_res, best = res, pdb_id
        except Exception:
            continue

    if not best:
        best = pdb_ids[0]

    _save(key, best)
    return best


def fetch_pdb_structure(pdb_id: str) -> Optional[str]:
    """Download PDB file content for any structure."""
    key = f"pdb_raw_{pdb_id}"
    cached = _load(key)
    if cached is not None: return cached

    pdb_text = _get_text(f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb")
    if pdb_text:
        # Cache truncated (first 500kb) to avoid giant cache files
        _save(key, pdb_text[:500000])
        return pdb_text

    return None


def fetch_alphafold_structure(uniprot_id: str) -> Optional[str]:
    """Fetch AlphaFold predicted structure as fallback when no experimental PDB exists."""
    key = f"af_{uniprot_id}"
    cached = _load(key)
    if cached is not None: return cached

    # AlphaFold DB API
    data = _get(f"https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}")
    if data and isinstance(data, list) and data:
        pdb_url = data[0].get("pdbUrl","")
        if pdb_url:
            pdb_text = _get_text(pdb_url)
            if pdb_text:
                _save(key, pdb_text[:500000])
                return pdb_text

    _save(key, None)
    return None


def get_structure_for_protein(uniprot_data: dict, uniprot_id: str = None) -> tuple:
    """
    Get the best available 3D structure for a protein.
    Returns (pdb_text, source_description)
    Tries: experimental PDB → AlphaFold → TP53 fallback
    """
    pdb_ids = uniprot_data.get("pdb_ids", [])
    uid     = uniprot_id or uniprot_data.get("uniprot_id","")
    gene    = uniprot_data.get("gene_name","")

    # Try experimental structures
    if pdb_ids:
        best_id = get_best_pdb_id(pdb_ids, uid)
        if best_id:
            pdb_text = fetch_pdb_structure(best_id)
            if pdb_text:
                return pdb_text, f"PDB {best_id} ({uniprot_data.get('protein_name',gene)} — experimental structure)"

    # Try AlphaFold
    if uid:
        af_text = fetch_alphafold_structure(uid)
        if af_text:
            return af_text, f"AlphaFold predicted structure ({gene})"

    # Fallback: TP53 reference structure
    fallback = fetch_pdb_structure("2OCJ")
    if fallback:
        return fallback, "TP53 reference structure (PDB 2OCJ) — shown as visual reference only"

    return None, "No structure available"


def fetch_pdb_bfactors(pdb_id: str, chain: str = "A") -> dict:
    """B-factors (flexibility) per residue from PDB."""
    key = f"bf_{pdb_id}_{chain}"
    cached = _load(key)
    if cached is not None: return cached

    result = {}
    pdb_text = fetch_pdb_structure(pdb_id)
    if not pdb_text:
        _save(key, result); return result

    res_bf = {}
    for line in pdb_text.split('\n'):
        if not line.startswith('ATOM'): continue
        try:
            rec_chain = line[21].strip()
            if chain != "*" and rec_chain != chain: continue
            resnum  = int(line[22:26].strip())
            bfactor = float(line[60:66].strip())
            atom    = line[12:16].strip()
            if atom == 'CA': res_bf[resnum] = bfactor
        except (ValueError,IndexError): continue

    if res_bf:
        bvals = list(res_bf.values())
        mn, mx = min(bvals), max(bvals)
        if mx > mn:
            result = {k: round((v-mn)/(mx-mn), 3) for k,v in res_bf.items()}
        else:
            result = {k: 0.5 for k in res_bf}

    _save(key, result); return result


# ══════════════════════════════════════════════════════════════════════════
# CLINVAR
# ══════════════════════════════════════════════════════════════════════════

def fetch_clinvar_variants(gene_name: str) -> dict:
    """Fetch ClinVar variants for a gene → {position: [{significance, conditions}]}."""
    key = f"cv_{gene_name}"
    cached = _load(key)
    if cached is not None: return cached

    result = {}
    try:
        search = _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                      {"db":"clinvar","term":f"{gene_name}[gene] AND single_gene[prop]",
                       "retmax":200,"retmode":"json","tool":"protellect","email":"research@protellect.com"})
        if not search: _save(key,result); return result
        ids = search.get("esearchresult",{}).get("idlist",[])
        if not ids: _save(key,result); return result

        time.sleep(0.35)
        summary = _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                       {"db":"clinvar","id":",".join(ids[:100]),"retmode":"json",
                        "tool":"protellect","email":"research@protellect.com"}, timeout=20)
        if not summary: _save(key,result); return result

        doc = summary.get("result",{})
        for vid in doc.get("uids",[]):
            entry = doc.get(vid,{})
            title = entry.get("title","")
            sig   = entry.get("germline_classification",{}).get("description","")
            pm = re.search(r'[A-Z\*](\d+)[A-Za-z\*]', title)
            if not pm: continue
            pos = int(pm.group(1))
            conds = [c.get("trait_name","") for c in entry.get("trait_set",[])]
            if pos not in result: result[pos] = []
            result[pos].append({"significance":sig,"conditions":conds[:3],"title":title})
    except Exception:
        pass

    _save(key, result); return result


def get_clinvar_for_position(clinvar_data: dict, position: int) -> str:
    variants = clinvar_data.get(position, [])
    if not variants: return "No ClinVar variants at this position"
    severity = ["Pathogenic","Likely pathogenic","Uncertain significance","Likely benign","Benign"]
    best = None
    for v in variants:
        sig = v.get("significance","")
        for s in severity:
            if s.lower() in sig.lower():
                best = v; break
        if best: break
    if not best: best = variants[0]
    sig   = best.get("significance","Unknown")
    conds = ", ".join(best.get("conditions",[])[:2]) or "multiple conditions"
    n     = len(variants)
    return f"{sig} · {n} submission{'s' if n>1 else ''} · {conds}"


# ══════════════════════════════════════════════════════════════════════════
# INTERPRO
# ══════════════════════════════════════════════════════════════════════════

def fetch_interpro(uniprot_id: str) -> dict:
    """InterPro domain annotations → {entries, position_map}."""
    key = f"ipr_{uniprot_id}"
    cached = _load(key)
    if cached is not None: return cached

    result = {"entries":[],"position_map":{}}
    data = _get(f"https://www.ebi.ac.uk/interpro/api/entry/interpro/protein/UniProt/{uniprot_id}/",
                {"format":"json","page_size":50}, timeout=15)
    if not data: _save(key,result); return result

    for entry in data.get("results",[]):
        meta = entry.get("metadata",{})
        name = meta.get("name","")
        for prot in entry.get("proteins",[]):
            if prot.get("accession","").upper() != uniprot_id.upper(): continue
            for loc in prot.get("entry_protein_locations",[]):
                for frag in loc.get("fragments",[]):
                    s, e = frag.get("start"), frag.get("end")
                    if s and e:
                        result["entries"].append({"name":name,"start":int(s),"end":int(e)})
                        for p in range(int(s),int(e)+1):
                            result["position_map"][p] = name

    _save(key,result); return result


# ══════════════════════════════════════════════════════════════════════════
# ENSEMBL
# ══════════════════════════════════════════════════════════════════════════

def ensg_to_gene_name(ensg_id: str) -> Optional[str]:
    key = f"ensg_{ensg_id}"
    cached = _load(key)
    if cached is not None: return cached
    try:
        r = SESSION.get(f"https://rest.ensembl.org/lookup/id/{ensg_id}",
                        params={"content-type":"application/json"},
                        headers={"Content-Type":"application/json"}, timeout=10)
        if r.status_code == 200:
            gene = r.json().get("display_name") or r.json().get("id")
            _save(key, gene); return gene
    except Exception:
        pass
    _save(key, None); return None


# ══════════════════════════════════════════════════════════════════════════
# CONSERVATION
# ══════════════════════════════════════════════════════════════════════════

def estimate_conservation(uniprot_data: dict, position: int) -> float:
    if not uniprot_data: return 0.5
    if position in uniprot_data.get("active_sites",[]): return 0.98
    if position in uniprot_data.get("binding_sites",[]): return 0.92
    variants_here = [v for v in uniprot_data.get("natural_variants",[]) if v["position"]==position]
    pathogenic    = [v for v in variants_here if "disease" in v.get("note","").lower()]
    if pathogenic: return 0.95
    if not variants_here: return 0.75
    if len(variants_here) <= 2: return 0.55
    return 0.30


# ══════════════════════════════════════════════════════════════════════════
# MAIN ENRICHMENT
# ══════════════════════════════════════════════════════════════════════════

def enrich_protein(gene_name: str = None, uniprot_id: str = None) -> dict:
    """Full enrichment for one protein: UniProt + ClinVar + InterPro + PDB."""
    result = {"gene_name":gene_name or "","uniprot_id":uniprot_id or "",
              "uniprot":{},"clinvar":{},"interpro":{},"pdb_bfactor":{},
              "pdb_ids":[],"structure_pdb":None,"structure_source":"",
              "error":None}
    try:
        if not uniprot_id and gene_name:
            uniprot_id = lookup_uniprot_by_gene(gene_name)
            result["uniprot_id"] = uniprot_id or ""

        if uniprot_id:
            result["uniprot"]  = fetch_uniprot_full(uniprot_id)
            result["pdb_ids"]  = result["uniprot"].get("pdb_ids",[])[:10]
            if not gene_name:
                gene_name = result["uniprot"].get("gene_name","")
                result["gene_name"] = gene_name
            # Get best structure
            pdb_text, src = get_structure_for_protein(result["uniprot"], uniprot_id)
            result["structure_pdb"]    = pdb_text
            result["structure_source"] = src
            # B-factors from best experimental structure
            if result["pdb_ids"]:
                best_id = get_best_pdb_id(result["pdb_ids"], uniprot_id)
                if best_id:
                    result["pdb_bfactor"] = fetch_pdb_bfactors(best_id)

        if gene_name:
            result["clinvar"]  = fetch_clinvar_variants(gene_name)

        if uniprot_id:
            result["interpro"] = fetch_interpro(uniprot_id)

    except Exception as e:
        result["error"] = str(e)

    return result


def get_residue_features(enrichment: dict, position: int) -> dict:
    uni     = enrichment.get("uniprot",{})
    clinvar = enrichment.get("clinvar",{})
    ipr     = enrichment.get("interpro",{})
    bf      = enrichment.get("pdb_bfactor",{})

    in_active  = position in uni.get("active_sites",[])
    in_binding = position in uni.get("binding_sites",[])
    conservation = estimate_conservation(uni, position)

    # Domain importance
    domain_score = 0.3
    domain_name  = ipr.get("position_map",{}).get(position,"")
    if not domain_name:
        for d in uni.get("domains",[]):
            if d["start"] <= position <= d["end"]:
                domain_name = d.get("name","")
                dt = d.get("type","").lower()
                domain_score = (0.9 if any(x in dt for x in ("dna","bind","active","zinc","catal"))
                                else 0.6 if "domain" in dt else 0.5)
                break
    if in_active:  domain_score = 1.0
    if in_binding: domain_score = 0.85

    clinvar_text = get_clinvar_for_position(clinvar, position)
    is_pathogenic = "pathogenic" in clinvar_text.lower()
    in_ptm = position in [p["position"] for p in uni.get("ptm_sites",[])]

    return {
        "conservation":   conservation,
        "in_active_site": in_active,
        "in_binding_site":in_binding,
        "domain_score":   domain_score,
        "domain_name":    domain_name or f"Position {position}",
        "bfactor":        bf.get(position, 0.5),
        "clinvar_text":   clinvar_text,
        "is_pathogenic":  is_pathogenic,
        "in_ptm_site":    in_ptm,
    }


def format_enrichment_for_display(enrichment: dict, position: int, label: str) -> dict:
    feats  = get_residue_features(enrichment, position)
    uni    = enrichment.get("uniprot",{})
    gene   = enrichment.get("gene_name","")
    uid    = enrichment.get("uniprot_id","")

    if feats["in_active_site"]:
        mechanism = f"Position {position} is an **active site residue** in {gene}. Mutations here typically abolish catalytic activity entirely."
    elif feats["in_binding_site"]:
        mechanism = f"Position {position} is a **binding site residue** in {gene}. Mutations here disrupt key molecular interactions."
    elif feats["domain_score"] > 0.7:
        mechanism = f"Position {position} lies within a **critical functional domain** ({feats['domain_name']}) of {gene}. High structural sensitivity."
    elif feats["conservation"] > 0.85:
        mechanism = f"Position {position} is **highly conserved** in {gene} — limited natural variation strongly suggests functional importance."
    else:
        fn = (uni.get("function",""))[:180]
        mechanism = f"Effect score from experimental assay. {gene} function: {fn}..." if fn else f"Effect score from experimental assay for {gene}."

    sources = ["Wet lab assay"]
    if uid: sources.append(f"UniProt {uid}")
    if enrichment.get("clinvar",{}).get(position): sources.append("ClinVar")
    if enrichment.get("interpro",{}).get("position_map",{}).get(position): sources.append("InterPro")
    if enrichment.get("pdb_ids"): sources.append(f"PDB {enrichment['pdb_ids'][0]}")
    if enrichment.get("structure_source","").startswith("AlphaFold"): sources.append("AlphaFold")

    return {
        "domain":      feats["domain_name"],
        "mechanism":   mechanism,
        "clinvar":     feats["clinvar_text"],
        "cancer":      f"COSMIC query via Phase 2 — check cbioportal.org for {gene} cancer data",
        "therapeutic": (f"ClinVar pathogenic → consult ClinicalTrials.gov & ChEMBL for {gene} therapeutics"
                        if feats["is_pathogenic"] else
                        f"Check ChEMBL, DGIdb, or DrugBank for {gene} modulators"),
        "sources":     sources,
        "conservation":feats["conservation"],
        "in_active":   feats["in_active_site"],
        "in_binding":  feats["in_binding_site"],
        "domain_score":feats["domain_score"],
        "bfactor":     feats["bfactor"],
        "is_pathogenic":feats["is_pathogenic"],
    }
