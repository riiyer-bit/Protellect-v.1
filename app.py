from __future__ import annotations
"""All API calls: UniProt, ClinVar, AlphaFold, PubMed, NCBI Gene."""

import requests, time, re
import streamlit as st

ESEARCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
AF_API   = "https://alphafold.ebi.ac.uk/api"
UNIPROT  = "https://rest.uniprot.org/uniprotkb"

SIG_SCORE = {
    "pathogenic": 5, "likely pathogenic": 4,
    "pathogenic/likely pathogenic": 4, "risk factor": 3,
    "uncertain significance": 2, "conflicting interpretations": 2,
    "likely benign": 1, "benign": 0, "benign/likely benign": 0,
    "not provided": -1,
}

# ── UniProt ─────────────────────────────────────────────────────────────────
def fetch_uniprot(query: str) -> dict:
    acc_pat = re.compile(r"^[OPQ][0-9][A-Z0-9]{3}[0-9]$|^[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$", re.I)
    if acc_pat.match(query.strip()):
        r = requests.get(f"{UNIPROT}/{query.strip().upper()}", headers={"Accept":"application/json"}, timeout=20)
        r.raise_for_status(); return r.json()

    params = {
        "query": f'(gene:{query} OR protein_name:{query}) AND reviewed:true',
        "format": "json", "size": 1,
        "fields": "accession,gene_names,protein_name,organism_name,length,"
                  "cc_disease,cc_tissue_specificity,cc_function,keyword,"
                  "cc_subcellular_location,xref_omim,xref_hgnc,sequence,"
                  "ft_variant,cc_pathway,cc_interaction,cc_ptm,feature",
    }
    r = requests.get(f"{UNIPROT}/search", params=params, headers={"Accept":"application/json"}, timeout=20)
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        params["query"] = query
        r = requests.get(f"{UNIPROT}/search", params=params, headers={"Accept":"application/json"}, timeout=20)
        r.raise_for_status(); results = r.json().get("results", [])
    if not results: raise ValueError(f"No UniProt entry found for '{query}'.")
    acc = results[0]["primaryAccession"]
    r2 = requests.get(f"{UNIPROT}/{acc}", headers={"Accept":"application/json"}, timeout=20)
    r2.raise_for_status(); return r2.json()

def get_gene_name(pdata: dict) -> str:
    try: return pdata["genes"][0]["geneName"]["value"]
    except: return pdata.get("primaryAccession","?")

def get_protein_name(pdata: dict) -> str:
    try: return pdata["proteinDescription"]["recommendedName"]["fullName"]["value"]
    except: return "Unknown protein"

def get_sequence(pdata: dict) -> str:
    return pdata.get("sequence",{}).get("value","")

def get_diseases(pdata: dict) -> list:
    out = []
    for c in pdata.get("comments",[]):
        if c.get("commentType") == "DISEASE":
            d = c.get("disease",{})
            out.append({
                "name": d.get("diseaseId", d.get("diseaseAcronym","Unknown")),
                "desc": d.get("description",""),
                "omim": d.get("diseaseCrossReference",{}).get("id",""),
                "note": (c.get("note",{}).get("texts",[{}])[0].get("value","") if c.get("note") else ""),
            })
    return out

def get_subcellular(pdata: dict) -> list:
    locs = []
    for c in pdata.get("comments",[]):
        if c.get("commentType") == "SUBCELLULAR LOCATION":
            for e in c.get("subcellularLocations",[]):
                v = e.get("location",{}).get("value","")
                if v: locs.append(v)
    return list(dict.fromkeys(locs))

def get_tissue(pdata: dict) -> str:
    for c in pdata.get("comments",[]):
        if c.get("commentType") == "TISSUE SPECIFICITY":
            t = c.get("texts",[])
            if t: return t[0].get("value","")
    return ""

def get_function(pdata: dict) -> str:
    for c in pdata.get("comments",[]):
        if c.get("commentType") == "FUNCTION":
            t = c.get("texts",[])
            if t: return t[0].get("value","")
    return ""

def get_gpcr(pdata: dict) -> dict:
    kws = [k.get("value","").lower() for k in pdata.get("keywords",[])]
    is_gpcr = any(x in " ".join(kws) for x in ["gpcr","g protein","rhodopsin","adrenergic"])
    return {"is_gpcr": is_gpcr, "keywords": kws}

def get_xref(pdata: dict, db: str) -> str:
    for x in pdata.get("uniProtKBCrossReferences",[]):
        if x.get("database") == db: return x.get("id","")
    return ""

def get_variants_from_uniprot(pdata: dict) -> list:
    out = []
    for f in pdata.get("features",[]):
        if f.get("type") in ("Natural variant","VARIANT"):
            loc = f.get("location",{})
            out.append({
                "position": loc.get("start",{}).get("value","?"),
                "original": f.get("alternativeSequence",{}).get("originalSequence",""),
                "alt":      ", ".join(f.get("alternativeSequence",{}).get("alternativeSequences",[])),
                "desc":     f.get("description",""),
            })
    return out

# ── ClinVar ──────────────────────────────────────────────────────────────────
def fetch_clinvar(gene: str, max_results: int = 300) -> dict:
    params = {"db":"clinvar","term":f"{gene}[gene]","retmax":max_results,"retmode":"json"}
    try:
        r = requests.get(ESEARCH, params=params, timeout=20); r.raise_for_status()
        ids = r.json().get("esearchresult",{}).get("idlist",[])
    except: return {"variants":[], "summary":{}}
    if not ids: return {"variants":[], "summary":{}}

    variants = []
    for i in range(0, len(ids), 100):
        batch = ids[i:i+100]
        try:
            r2 = requests.get(ESUMMARY, params={"db":"clinvar","id":",".join(batch),"retmode":"json"}, timeout=30)
            r2.raise_for_status(); data = r2.json().get("result",{})
            for uid in data.get("uids",[]):
                e = data.get(uid,{}); gc = e.get("germline_classification",{})
                sig = gc.get("description","Not provided")
                score = SIG_SCORE.get(sig.lower().strip(), 0)
                traits = [t.get("trait_name","") for t in e.get("trait_set",{}).get("trait",[]) if t.get("trait_name")]
                locs = e.get("location_list",[{}])
                vset = e.get("variation_set",[{}])
                variants.append({
                    "uid": uid,
                    "title": e.get("title",""),
                    "variant_name": vset[0].get("variation_name","") if vset else "",
                    "sig": sig, "score": score,
                    "rank": _score_rank(score),
                    "condition": "; ".join(traits) if traits else "Not specified",
                    "origin": e.get("origin",{}).get("origin",""),
                    "review": gc.get("review_status",""),
                    "chr": locs[0].get("chr","") if locs else "",
                    "start": locs[0].get("start","") if locs else "",
                    "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{e.get('variation_id',uid)}/",
                    "somatic": bool(e.get("somatic_classifications",{})),
                })
        except: pass
        time.sleep(0.1)

    variants.sort(key=lambda x: -x["score"])
    from collections import Counter
    sigs  = Counter(v["sig"] for v in variants)
    ranks = Counter(v["rank"] for v in variants)
    conds = Counter()
    for v in variants:
        for c in v["condition"].split(";"):
            c = c.strip()
            if c and c != "Not specified": conds[c] += 1
    return {
        "variants": variants,
        "summary": {
            "total": len(variants),
            "by_sig": dict(sigs.most_common(8)),
            "by_rank": dict(ranks),
            "top_conds": dict(conds.most_common(10)),
            "pathogenic": sum(1 for v in variants if v["score"] >= 4),
            "vus": sum(1 for v in variants if v["score"] == 2),
            "benign": sum(1 for v in variants if v["score"] <= 0),
        }
    }

def _score_rank(s: int) -> str:
    if s >= 5: return "CRITICAL"
    if s >= 4: return "HIGH"
    if s >= 2: return "MEDIUM"
    return "NEUTRAL"

# ── AlphaFold ─────────────────────────────────────────────────────────────────
def fetch_alphafold_pdb(uniprot_id: str) -> str:
    if not uniprot_id: return ""
    try:
        r = requests.get(f"{AF_API}/prediction/{uniprot_id}", timeout=15)
        if r.status_code == 404: return ""
        r.raise_for_status(); entries = r.json()
        if not entries: return ""
        pdb_url = entries[0].get("pdbUrl","")
        if not pdb_url: return ""
        r2 = requests.get(pdb_url, timeout=30); r2.raise_for_status()
        return r2.text
    except: return ""

def parse_bfactors(pdb: str) -> dict:
    out = {}
    for line in pdb.splitlines():
        if line.startswith(("ATOM","HETATM")):
            try:
                rn = int(line[22:26]); bf = float(line[60:66]); an = line[12:16].strip()
                if an == "CA": out[rn] = bf
            except: pass
    return out

def plddt_colour(v: float) -> str:
    if v >= 90: return "#1565C0"
    if v >= 70: return "#29B6F6"
    if v >= 50: return "#FDD835"
    return "#FF7043"

# ── PubMed ───────────────────────────────────────────────────────────────────
def fetch_papers(gene: str, n: int = 6) -> list:
    try:
        r = requests.get(ESEARCH, params={"db":"pubmed","term":gene,"retmax":n*2,"retmode":"json","sort":"relevance"}, timeout=15)
        r.raise_for_status(); ids = r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return []
        r2 = requests.get(ESUMMARY, params={"db":"pubmed","id":",".join(ids),"retmode":"json"}, timeout=15)
        r2.raise_for_status(); data = r2.json().get("result",{})
        papers = []
        for uid in data.get("uids",[]):
            e = data.get(uid,{})
            authors = ", ".join(a.get("name","") for a in e.get("authors",[])[:3])
            if len(e.get("authors",[])) > 3: authors += " et al."
            ptype = [p.get("value","").lower() for p in e.get("pubtype",[])]
            score = (3 if "review" in ptype else 0) + (2 if e.get("pubdate","")[:4] >= "2020" else 0)
            papers.append({"pmid":uid,"title":e.get("title",""),"authors":authors,
                           "journal":e.get("source",""),"year":e.get("pubdate","")[:4],
                           "url":f"https://pubmed.ncbi.nlm.nih.gov/{uid}/","score":score,"ptype":ptype})
        return sorted(papers, key=lambda x:-x["score"])[:n]
    except: return []

# ── NCBI Gene ────────────────────────────────────────────────────────────────
def fetch_ncbi_gene(symbol: str) -> dict:
    try:
        r = requests.get(ESEARCH, params={"db":"gene","term":f"{symbol}[gene name] AND Homo sapiens[organism] AND alive[property]","retmax":1,"retmode":"json"}, timeout=15)
        r.raise_for_status(); ids = r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return {}
        gid = ids[0]
        r2 = requests.get(ESUMMARY, params={"db":"gene","id":gid,"retmode":"json"}, timeout=15)
        r2.raise_for_status(); e = r2.json().get("result",{}).get(gid,{})
        gi = e.get("genomicinfo",[{}])[0] if e.get("genomicinfo") else {}
        return {
            "id":e.get("name",""),"full":e.get("description",""),"chr":e.get("chromosome",""),
            "map":e.get("maplocation",""),"summary":e.get("summary",""),
            "start":gi.get("chrstart",""),"stop":gi.get("chrstop",""),"exons":gi.get("exoncount",""),
            "link":f"https://www.ncbi.nlm.nih.gov/gene/{gid}",
        }
    except: return {}

# ── ML scoring (pure numpy, no sklearn) ──────────────────────────────────────
AA_HYDRO = {"A":1.8,"R":-4.5,"N":-3.5,"D":-3.5,"C":2.5,"Q":-3.5,"E":-3.5,
            "G":-0.4,"H":-3.2,"I":4.5,"L":3.8,"K":-3.9,"M":1.9,"F":2.8,
            "P":-1.6,"S":-0.8,"T":-0.7,"W":-0.9,"Y":-1.3,"V":4.2,"*":-10}
AA_CHG   = {"R":1,"K":1,"H":0.5,"D":-1,"E":-1}

def ml_score_variants(variants: list) -> list:
    import numpy as np
    out = []
    for v in variants:
        name  = v.get("variant_name","") or v.get("title","")
        orig, alt = _parse_aa(name)
        h_d = abs(AA_HYDRO.get(orig,0) - AA_HYDRO.get(alt,0))
        c_d = abs(AA_CHG.get(orig,0)   - AA_CHG.get(alt,0))
        stop   = float(alt == "*")
        frame  = float("frame" in name.lower())
        stars  = {"practice guideline":1,"reviewed by expert panel":0.9,
                  "criteria provided, multiple submitters":0.7,
                  "criteria provided, single submitter":0.5}.get(v.get("review","").lower(),0.2)
        base   = v.get("score",0) / 5.0
        ml     = min(1.0, base*0.5 + stop*0.25 + frame*0.15 + (h_d/10)*0.05 + (c_d*0.03) + stars*0.02)
        vc = dict(v); vc["ml"] = round(float(ml),3); vc["ml_rank"] = _ml_rank(ml)
        out.append(vc)
    return sorted(out, key=lambda x:-x["ml"])

def _parse_aa(name: str):
    m = re.search(r"p\.([A-Z][a-z]{2})\d+([A-Z][a-z]{2}|Ter|\*)", name or "")
    if not m: return "?","?"
    aa3 = {"Ala":"A","Arg":"R","Asn":"N","Asp":"D","Cys":"C","Gln":"Q","Glu":"E","Gly":"G",
           "His":"H","Ile":"I","Leu":"L","Lys":"K","Met":"M","Phe":"F","Pro":"P","Ser":"S",
           "Thr":"T","Trp":"W","Tyr":"Y","Val":"V","Ter":"*","Xaa":"X"}
    return aa3.get(m.group(1),"?"), aa3.get(m.group(2),"?")

def _ml_rank(ml: float) -> str:
    if ml >= 0.85: return "CRITICAL"
    if ml >= 0.65: return "HIGH"
    if ml >= 0.40: return "MEDIUM"
    return "NEUTRAL"
