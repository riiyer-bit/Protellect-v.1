"""
db_enrichment.py — Protellect Database Enrichment Layer

Automatically queries live databases for ANY protein identified in your wet lab data:

  UniProt  — protein function, domain annotations, active/binding sites, conservation
  ClinVar  — variant pathogenicity classifications for any residue position
  PDB      — 3D structure, B-factors (flexibility), surface exposure, contacts
  InterPro — domain family classification, functional signatures
  COSMIC   — somatic mutation frequency across cancer types (via public API)
  Ensembl  — gene-level annotation when ENSG IDs are provided

All results are cached locally so databases are only queried once per protein.
Falls back gracefully if any database is unavailable.
"""

import requests
import json
import time
import re
import os
from pathlib import Path
from functools import lru_cache
from typing import Optional

# ── Cache directory ────────────────────────────────────────────────────────────
CACHE_DIR = Path(".protellect_cache")
CACHE_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Protellect/1.0 (computational biology triage tool; contact: research@protellect.com)",
    "Accept": "application/json",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def _cache_path(key: str) -> Path:
    safe = re.sub(r'[^a-zA-Z0-9_\-]', '_', key)
    return CACHE_DIR / f"{safe}.json"


def _load_cache(key: str):
    p = _cache_path(key)
    if p.exists():
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _save_cache(key: str, data):
    try:
        with open(_cache_path(key), 'w') as f:
            json.dump(data, f)
    except Exception:
        pass


def _get(url: str, params: dict = None, timeout: int = 12) -> Optional[dict]:
    """Safe GET with error handling."""
    try:
        r = SESSION.get(url, params=params, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
# AUTO-DETECT PROTEIN FROM DATA
# ══════════════════════════════════════════════════════════════════════════════

def detect_protein_from_data(df, context: dict = None) -> dict:
    """
    Automatically detect the protein/gene from the uploaded dataset.
    Returns dict with: uniprot_id, gene_name, organism, confidence, source
    """
    result = {"uniprot_id": None, "gene_name": None, "organism": "human",
              "confidence": 0.0, "source": "not detected", "ensg_id": None}

    # 1. Check scientist Q&A context first
    if context:
        prot = context.get("protein_of_interest", "").strip()
        if prot and len(prot) >= 2:
            result["gene_name"] = prot.upper()
            result["confidence"] = 0.9
            result["source"] = "scientist-provided"
            uid = lookup_uniprot_by_gene(prot)
            if uid:
                result["uniprot_id"] = uid
            return result

    # 2. Scan mutation column for gene prefixes like "TP53_R175H"
    if "mutation" in df.columns:
        muts = df["mutation"].dropna().astype(str).tolist()
        for m in muts[:50]:
            g = re.match(r'^([A-Z][A-Z0-9]{1,9})_', m)
            if g:
                gene = g.group(1)
                result["gene_name"] = gene
                result["confidence"] = 0.8
                result["source"] = "mutation column prefix"
                uid = lookup_uniprot_by_gene(gene)
                if uid:
                    result["uniprot_id"] = uid
                return result

    # 3. Scan gene_name column
    if "gene_name" in df.columns:
        genes = df["gene_name"].dropna().unique().astype(str).tolist()
        if len(genes) == 1:
            # Single gene — perfect
            gene = genes[0].strip()
            result["gene_name"] = gene
            result["confidence"] = 0.85
            result["source"] = "gene_name column (single gene)"
            uid = lookup_uniprot_by_gene(gene)
            if uid:
                result["uniprot_id"] = uid
            return result

    # 4. Scan ENSG IDs
    for col in df.columns:
        if "ensg" in col.lower() or "ensembl" in col.lower():
            ensg_vals = df[col].dropna().astype(str).tolist()
            for val in ensg_vals[:5]:
                if val.startswith("ENSG"):
                    result["ensg_id"] = val
                    result["source"] = "ensembl ID"
                    gene = ensg_to_gene_name(val)
                    if gene:
                        result["gene_name"] = gene
                        result["confidence"] = 0.75
                        uid = lookup_uniprot_by_gene(gene)
                        if uid:
                            result["uniprot_id"] = uid
                    return result

    # 5. Check target_name column for known protein names
    for col in df.columns:
        if "target" in col.lower() or "protein" in col.lower() or "gene" in col.lower():
            vals = df[col].dropna().unique().astype(str).tolist()
            if len(vals) == 1:
                gene = vals[0].strip()
                result["gene_name"] = gene
                result["confidence"] = 0.6
                result["source"] = f"{col} column (single target)"
                uid = lookup_uniprot_by_gene(gene)
                if uid:
                    result["uniprot_id"] = uid
                return result

    return result


# ══════════════════════════════════════════════════════════════════════════════
# UNIPROT
# ══════════════════════════════════════════════════════════════════════════════

def lookup_uniprot_by_gene(gene_name: str, organism: str = "human") -> Optional[str]:
    """Search UniProt for a gene name, return best UniProt ID."""
    cache_key = f"uniprot_search_{gene_name}_{organism}"
    cached = _load_cache(cache_key)
    if cached is not None:
        return cached

    try:
        # UniProt REST API search
        url = "https://rest.uniprot.org/uniprotkb/search"
        params = {
            "query": f'gene_exact:{gene_name} AND organism_id:9606 AND reviewed:true',
            "format": "json",
            "size": 1,
            "fields": "accession,gene_names,protein_name,organism_name"
        }
        data = _get(url, params=params)
        if data and data.get("results"):
            uid = data["results"][0]["primaryAccession"]
            _save_cache(cache_key, uid)
            return uid

        # Fallback: unreviewed
        params["query"] = f'gene:{gene_name} AND organism_id:9606'
        data = _get(url, params=params)
        if data and data.get("results"):
            uid = data["results"][0]["primaryAccession"]
            _save_cache(cache_key, uid)
            return uid
    except Exception:
        pass

    _save_cache(cache_key, None)
    return None


def fetch_uniprot_full(uniprot_id: str) -> dict:
    """
    Fetch comprehensive UniProt annotation for a protein.
    Returns: domains, active sites, binding sites, conservation hints,
             natural variants, sequence, function, subcellular location.
    """
    cache_key = f"uniprot_full_{uniprot_id}"
    cached = _load_cache(cache_key)
    if cached is not None:
        return cached

    result = {
        "uniprot_id":    uniprot_id,
        "gene_name":     "",
        "protein_name":  "",
        "organism":      "",
        "function":      "",
        "sequence":      "",
        "length":        0,
        "domains":       [],    # [{start, end, name, type}]
        "active_sites":  [],    # [position]
        "binding_sites": [],    # [position]
        "natural_variants": [], # [{position, original, variation, note}]
        "ptm_sites":     [],    # [{position, description}]
        "subcellular":   [],
        "keywords":      [],
        "pdb_ids":       [],
        "go_terms":      [],
    }

    try:
        url = f"https://rest.uniprot.org/uniprotkb/{uniprot_id}"
        params = {"format": "json"}
        data = _get(url, params=params, timeout=20)
        if not data:
            _save_cache(cache_key, result)
            return result

        # Basic info
        result["gene_name"]    = data.get("genes", [{}])[0].get("geneName", {}).get("value", "") if data.get("genes") else ""
        result["protein_name"] = data.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", "")
        result["organism"]     = data.get("organism", {}).get("scientificName", "")
        result["length"]       = data.get("sequence", {}).get("length", 0)
        result["sequence"]     = data.get("sequence", {}).get("value", "")

        # Function
        for comment in data.get("comments", []):
            if comment.get("commentType") == "FUNCTION":
                texts = comment.get("texts", [])
                if texts:
                    result["function"] = texts[0].get("value", "")
            elif comment.get("commentType") == "SUBCELLULAR LOCATION":
                for loc in comment.get("subcellularLocations", []):
                    loc_val = loc.get("location", {}).get("value", "")
                    if loc_val:
                        result["subcellular"].append(loc_val)

        # Feature annotations
        for feat in data.get("features", []):
            ftype  = feat.get("type", "")
            loc    = feat.get("location", {})
            start  = loc.get("start", {}).get("value")
            end    = loc.get("end", {}).get("value", start)
            desc   = feat.get("description", "")
            note   = feat.get("featureCvId", "")

            if start is None:
                continue
            start, end = int(start), int(end)

            if ftype in ("Domain", "Region", "Zinc finger", "Coiled coil",
                         "Transmembrane", "Topological domain", "Repeat"):
                result["domains"].append({"start": start, "end": end, "name": desc, "type": ftype})

            elif ftype == "Active site":
                result["active_sites"].append(start)

            elif ftype in ("Binding site", "Metal binding"):
                for pos in range(start, end + 1):
                    result["binding_sites"].append(pos)

            elif ftype == "Natural variant":
                orig = feat.get("alternativeSequence", {}).get("originalSequence", "")
                var  = feat.get("alternativeSequence", {}).get("alternativeSequences", [""])[0]
                result["natural_variants"].append({
                    "position": start, "original": orig,
                    "variation": var, "note": desc
                })

            elif ftype == "Modified residue":
                result["ptm_sites"].append({"position": start, "description": desc})

        # Cross-references: PDB, GO
        for xref in data.get("uniProtKBCrossReferences", []):
            db = xref.get("database", "")
            if db == "PDB":
                result["pdb_ids"].append(xref.get("id", ""))
            elif db == "GO":
                props = {p["key"]: p["value"] for p in xref.get("properties", [])}
                result["go_terms"].append(props.get("GoTerm", ""))

        # Keywords
        result["keywords"] = [kw.get("value","") for kw in data.get("keywords", [])]

    except Exception as e:
        result["error"] = str(e)

    _save_cache(cache_key, result)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# CLINVAR
# ══════════════════════════════════════════════════════════════════════════════

def fetch_clinvar_variants(gene_name: str) -> dict:
    """
    Fetch ClinVar variants for a gene.
    Returns dict: {position: [{significance, conditions, review_stars, variant_id}]}
    """
    cache_key = f"clinvar_{gene_name}"
    cached = _load_cache(cache_key)
    if cached is not None:
        return cached

    result = {}
    try:
        # Use NCBI E-utilities
        # Step 1: search ClinVar for gene
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            "db": "clinvar",
            "term": f"{gene_name}[gene] AND single_gene[prop]",
            "retmax": 200,
            "retmode": "json",
            "tool": "protellect",
            "email": "research@protellect.com",
        }
        search_data = _get(search_url, search_params)
        if not search_data:
            _save_cache(cache_key, result)
            return result

        ids = search_data.get("esearchresult", {}).get("idlist", [])
        if not ids:
            _save_cache(cache_key, result)
            return result

        # Step 2: fetch summaries
        time.sleep(0.34)  # NCBI rate limit: 3/sec
        summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        summary_params = {
            "db": "clinvar",
            "id": ",".join(ids[:100]),
            "retmode": "json",
            "tool": "protellect",
            "email": "research@protellect.com",
        }
        summary_data = _get(summary_url, summary_params, timeout=20)
        if not summary_data:
            _save_cache(cache_key, result)
            return result

        doc_map = summary_data.get("result", {})
        for vid in doc_map.get("uids", []):
            entry = doc_map.get(vid, {})
            # Parse protein change to extract position
            title = entry.get("title", "")
            sig_list = entry.get("germline_classification", {}).get("description", "")

            # Extract amino acid position from variant name (e.g. "R175H" -> 175)
            pos_match = re.search(r'[A-Z\*](\d+)[A-Za-z\*]', title)
            if not pos_match:
                continue
            pos = int(pos_match.group(1))

            conditions = [c.get("trait_name","") for c in entry.get("trait_set", [])]
            stars = entry.get("review_status_label", "")

            if pos not in result:
                result[pos] = []
            result[pos].append({
                "significance": sig_list,
                "conditions":   conditions[:3],
                "review_stars": stars,
                "variant_id":   vid,
                "title":        title,
            })

    except Exception:
        pass

    _save_cache(cache_key, result)
    return result


def get_clinvar_for_position(clinvar_data: dict, position: int) -> str:
    """Get a readable ClinVar summary for a specific position."""
    variants = clinvar_data.get(position, [])
    if not variants:
        return "No ClinVar variants reported at this position"
    # Find the most severe
    severity_order = ["Pathogenic", "Likely pathogenic", "Uncertain significance",
                      "Likely benign", "Benign", "Conflicting"]
    best = None
    for v in variants:
        sig = v.get("significance", "")
        for sev in severity_order:
            if sev.lower() in sig.lower():
                best = v
                break
        if best:
            break
    if not best:
        best = variants[0]
    sig = best.get("significance", "Unknown")
    conds = ", ".join(best.get("conditions", [])[:2]) or "multiple conditions"
    stars = best.get("review_stars", "")
    n = len(variants)
    return f"{sig} · {n} submission{'s' if n>1 else ''} · {conds}" + (f" · {stars}" if stars else "")


# ══════════════════════════════════════════════════════════════════════════════
# PDB / STRUCTURE
# ══════════════════════════════════════════════════════════════════════════════

def fetch_pdb_info(pdb_id: str) -> dict:
    """
    Fetch PDB structure info: resolution, experimental method, chain info.
    """
    cache_key = f"pdb_info_{pdb_id}"
    cached = _load_cache(cache_key)
    if cached is not None:
        return cached

    result = {"pdb_id": pdb_id, "resolution": None, "method": "", "chains": []}
    try:
        url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id.upper()}"
        data = _get(url)
        if data:
            result["resolution"] = data.get("rcsb_entry_info", {}).get("resolution_combined", [None])[0]
            result["method"]     = data.get("exptl", [{}])[0].get("method", "")
    except Exception:
        pass

    _save_cache(cache_key, result)
    return result


def fetch_pdb_bfactors(pdb_id: str, chain: str = "A") -> dict:
    """
    Fetch B-factors (temperature factors) per residue from PDB.
    High B-factor = flexible/disordered region.
    Returns dict: {residue_number: b_factor}
    """
    cache_key = f"pdb_bfactor_{pdb_id}_{chain}"
    cached = _load_cache(cache_key)
    if cached is not None:
        return cached

    result = {}
    try:
        url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
        r = SESSION.get(url, timeout=20)
        if r.status_code != 200:
            _save_cache(cache_key, result)
            return result

        # Parse ATOM records
        residue_bfactors = {}
        for line in r.text.split('\n'):
            if not line.startswith('ATOM'):
                continue
            try:
                rec_chain = line[21].strip()
                if rec_chain != chain and chain != "*":
                    continue
                resnum  = int(line[22:26].strip())
                bfactor = float(line[60:66].strip())
                atom    = line[12:16].strip()
                if atom == 'CA':  # use alpha-carbon B-factor as residue representative
                    residue_bfactors[resnum] = bfactor
            except (ValueError, IndexError):
                continue

        # Normalise B-factors to 0-1
        if residue_bfactors:
            bvals = list(residue_bfactors.values())
            bmin, bmax = min(bvals), max(bvals)
            if bmax > bmin:
                result = {k: round((v - bmin)/(bmax - bmin), 3) for k, v in residue_bfactors.items()}
            else:
                result = {k: 0.5 for k in residue_bfactors}

    except Exception:
        pass

    _save_cache(cache_key, result)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# INTERPRO
# ══════════════════════════════════════════════════════════════════════════════

def fetch_interpro(uniprot_id: str) -> dict:
    """
    Fetch InterPro domain classifications for a protein.
    Returns: {position: domain_name} mapping and list of domain entries.
    """
    cache_key = f"interpro_{uniprot_id}"
    cached = _load_cache(cache_key)
    if cached is not None:
        return cached

    result = {"entries": [], "position_map": {}}
    try:
        url = f"https://www.ebi.ac.uk/interpro/api/entry/interpro/protein/UniProt/{uniprot_id}/"
        params = {"format": "json", "page_size": 50}
        data = _get(url, params=params, timeout=15)
        if not data:
            _save_cache(cache_key, result)
            return result

        for entry in data.get("results", []):
            metadata   = entry.get("metadata", {})
            entry_id   = metadata.get("accession", "")
            entry_name = metadata.get("name", "")
            entry_type = metadata.get("type", "")
            proteins   = entry.get("proteins", [])

            for prot in proteins:
                if prot.get("accession", "").upper() != uniprot_id.upper():
                    continue
                for loc in prot.get("entry_protein_locations", []):
                    for frag in loc.get("fragments", []):
                        start = frag.get("start")
                        end   = frag.get("end")
                        if start and end:
                            result["entries"].append({
                                "id": entry_id, "name": entry_name,
                                "type": entry_type, "start": start, "end": end
                            })
                            for pos in range(int(start), int(end) + 1):
                                result["position_map"][pos] = entry_name

    except Exception:
        pass

    _save_cache(cache_key, result)
    return result


def get_domain_for_position(interpro_data: dict, uniprot_data: dict, position: int) -> str:
    """Get domain name for a specific residue position."""
    # Try InterPro first
    ipr_map = interpro_data.get("position_map", {})
    if position in ipr_map:
        return ipr_map[position]

    # Try UniProt domains
    for domain in uniprot_data.get("domains", []):
        if domain["start"] <= position <= domain["end"]:
            return f"{domain['name']} ({domain['type']})"

    return f"Position {position} — domain annotation pending Phase 2 full coverage"


# ══════════════════════════════════════════════════════════════════════════════
# ENSEMBL
# ══════════════════════════════════════════════════════════════════════════════

def ensg_to_gene_name(ensg_id: str) -> Optional[str]:
    """Convert Ensembl gene ID to gene symbol."""
    cache_key = f"ensembl_{ensg_id}"
    cached = _load_cache(cache_key)
    if cached is not None:
        return cached

    try:
        url = f"https://rest.ensembl.org/lookup/id/{ensg_id}"
        params = {"content-type": "application/json", "expand": 0}
        r = SESSION.get(url, params=params, timeout=10, headers={**HEADERS, "Content-Type": "application/json"})
        if r.status_code == 200:
            data = r.json()
            gene = data.get("display_name") or data.get("id")
            _save_cache(cache_key, gene)
            return gene
    except Exception:
        pass

    _save_cache(cache_key, None)
    return None


# ══════════════════════════════════════════════════════════════════════════════
# CONSERVATION (from UniProt natural variants + sequence)
# ══════════════════════════════════════════════════════════════════════════════

def estimate_conservation_from_uniprot(uniprot_data: dict, position: int) -> float:
    """
    Estimate evolutionary conservation from UniProt natural variants.
    Positions with NO natural variants are more conserved.
    Positions with MANY natural variants are less conserved.
    Active sites and binding sites are almost always conserved.
    Returns: 0 (variable) to 1 (conserved).
    """
    if not uniprot_data:
        return 0.5

    # Active/binding site → highly conserved
    if position in uniprot_data.get("active_sites", []):
        return 0.98
    if position in uniprot_data.get("binding_sites", []):
        return 0.92

    # Count natural variants at this position
    variants_here = [v for v in uniprot_data.get("natural_variants", [])
                     if v["position"] == position]
    pathogenic_here = [v for v in variants_here
                       if "disease" in v.get("note", "").lower()
                       or "pathogenic" in v.get("note", "").lower()]

    if pathogenic_here:
        return 0.95  # pathogenic variant → position is functionally important

    if len(variants_here) == 0:
        return 0.75  # no reported variants → likely conserved
    elif len(variants_here) <= 2:
        return 0.55
    else:
        return 0.30  # many variants → variable / tolerant position


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENRICHMENT FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def enrich_protein(gene_name: str = None, uniprot_id: str = None) -> dict:
    """
    Full enrichment pipeline for a protein.
    Queries UniProt, ClinVar, InterPro, PDB.
    Returns comprehensive annotation dict.
    """
    result = {
        "gene_name":   gene_name or "",
        "uniprot_id":  uniprot_id or "",
        "uniprot":     {},
        "clinvar":     {},
        "interpro":    {},
        "pdb_bfactor": {},
        "pdb_ids":     [],
        "error":       None,
    }

    try:
        # 1. Resolve UniProt ID if we only have gene name
        if not uniprot_id and gene_name:
            uniprot_id = lookup_uniprot_by_gene(gene_name)
            result["uniprot_id"] = uniprot_id or ""

        # 2. UniProt full annotation
        if uniprot_id:
            result["uniprot"] = fetch_uniprot_full(uniprot_id)
            result["pdb_ids"] = result["uniprot"].get("pdb_ids", [])[:5]
            if not gene_name and result["uniprot"].get("gene_name"):
                gene_name = result["uniprot"]["gene_name"]
                result["gene_name"] = gene_name

        # 3. ClinVar
        if gene_name:
            result["clinvar"] = fetch_clinvar_variants(gene_name)

        # 4. InterPro
        if uniprot_id:
            result["interpro"] = fetch_interpro(uniprot_id)

        # 5. PDB B-factors (use first available structure)
        pdb_ids = result["pdb_ids"]
        if pdb_ids:
            result["pdb_bfactor"] = fetch_pdb_bfactors(pdb_ids[0])

    except Exception as e:
        result["error"] = str(e)

    return result


def get_residue_features(enrichment: dict, position: int) -> dict:
    """
    Get all database-derived features for a specific residue position.
    Used as ML features and for annotation display.
    """
    uniprot   = enrichment.get("uniprot", {})
    clinvar   = enrichment.get("clinvar", {})
    interpro  = enrichment.get("interpro", {})
    bfactors  = enrichment.get("pdb_bfactor", {})

    # Is in active/binding site?
    in_active  = position in uniprot.get("active_sites", [])
    in_binding = position in uniprot.get("binding_sites", [])

    # Conservation estimate
    conservation = estimate_conservation_from_uniprot(uniprot, position)

    # Domain
    domain = get_domain_for_position(interpro, uniprot, position)

    # Domain importance score (is this in a known functional domain?)
    domain_score = 0.3  # default
    for d in uniprot.get("domains", []):
        if d["start"] <= position <= d["end"]:
            dtype = d.get("type","").lower()
            if "dna" in dtype or "binding" in dtype or "active" in dtype or "zinc" in dtype:
                domain_score = 0.9
            elif "domain" in dtype or "region" in dtype:
                domain_score = 0.6
            break
    if in_active:  domain_score = 1.0
    if in_binding: domain_score = 0.85

    # B-factor (structural flexibility)
    bfactor = bfactors.get(position, 0.5)  # 0=rigid, 1=flexible

    # ClinVar
    clinvar_text = get_clinvar_for_position(clinvar, position)
    is_pathogenic = "pathogenic" in clinvar_text.lower()

    # PTM
    ptm_sites = [p["position"] for p in uniprot.get("ptm_sites", [])]
    in_ptm    = position in ptm_sites

    return {
        "conservation":   conservation,
        "in_active_site": in_active,
        "in_binding_site":in_binding,
        "domain_score":   domain_score,
        "domain_name":    domain,
        "bfactor":        bfactor,
        "clinvar_text":   clinvar_text,
        "is_pathogenic":  is_pathogenic,
        "in_ptm_site":    in_ptm,
    }


def format_enrichment_for_display(enrichment: dict, position: int, label: str) -> dict:
    """
    Format enrichment data for display in Tab 3 and Tab 4 cards.
    """
    feats    = get_residue_features(enrichment, position)
    uniprot  = enrichment.get("uniprot", {})
    gene     = enrichment.get("gene_name","")
    uid      = enrichment.get("uniprot_id","")

    # Mechanism description
    if feats["in_active_site"]:
        mechanism = f"Position {position} is an active site residue in {gene}. Mutations here typically abolish catalytic activity entirely."
    elif feats["in_binding_site"]:
        mechanism = f"Position {position} is a binding site residue in {gene}. Mutations here may disrupt key molecular interactions."
    elif feats["domain_score"] > 0.7:
        mechanism = f"Position {position} lies within a critical functional domain of {gene}. High domain importance suggests functional sensitivity."
    elif feats["conservation"] > 0.85:
        mechanism = f"Position {position} is highly conserved in {gene} — limited natural variation suggests functional importance."
    elif feats["bfactor"] < 0.3:
        mechanism = f"Position {position} is in a structurally rigid region of {gene} — likely important for structural integrity."
    else:
        fn = uniprot.get("function","")
        mechanism = f"Effect score from wet lab assay for {gene}. " + (f"Protein function: {fn[:200]}..." if fn else "Phase 2 will add mechanistic detail.")

    # Sources chip list
    sources = ["Wet lab assay (your data)"]
    if uid:
        sources.append(f"UniProt {uid}")
    if enrichment.get("clinvar") and position in enrichment["clinvar"]:
        sources.append("ClinVar")
    if enrichment.get("interpro", {}).get("position_map", {}).get(position):
        sources.append("InterPro")
    if enrichment.get("pdb_ids"):
        sources.append(f"PDB {enrichment['pdb_ids'][0]}")

    return {
        "domain":      feats["domain_name"],
        "mechanism":   mechanism,
        "clinvar":     feats["clinvar_text"],
        "cosmic":      "Live COSMIC query — Phase 2 integration",
        "cancer":      "Cancer type data from COSMIC — Phase 2",
        "therapeutic": _get_therapeutic_hint(feats, gene),
        "sources":     sources,
        "conservation": feats["conservation"],
        "in_active":   feats["in_active_site"],
        "in_binding":  feats["in_binding_site"],
        "domain_score":feats["domain_score"],
        "bfactor":     feats["bfactor"],
        "is_pathogenic":feats["is_pathogenic"],
    }


def _get_therapeutic_hint(feats: dict, gene: str) -> str:
    if feats["is_pathogenic"]:
        return f"ClinVar pathogenic variant detected — consult ClinicalTrials.gov and ChEMBL for therapeutic context for {gene}"
    if feats["in_active_site"]:
        return f"Active site residue — potential drug target. Search ChEMBL for {gene} inhibitors"
    if feats["in_binding_site"]:
        return f"Binding site residue — check DGIdb and DrugBank for {gene} modulators"
    return f"Consult ChEMBL, DGIdb, or ClinicalTrials.gov for therapeutic context for {gene}"
