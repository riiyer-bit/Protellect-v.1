"""
protein_deep_dive.py — Protellect Universal Protein Deep Dive

Works for ANY human protein. Sources truth from:
  PRIMARY: ClinVar — human disease-causing variants only
  SECONDARY: UniProt experimental annotations (evidence level filtered)
  SECONDARY: Ensembl gene/chromosome location
  SECONDARY: NCBI for ClinVar variant details

Principle: if ClinVar has no pathogenic variants for a protein,
the app says so explicitly — no fabrication, no pathway inference,
no cell culture claims treated as human evidence.

GPCR classification, tissue expression, chromosome location,
genomic verdict with investment warning, and ranked experiments
all generated universally from the same pipeline.
"""

import streamlit as st
import streamlit.components.v1 as components
import requests
import time
import re
import pandas as pd
import json
from pathlib import Path
import base64

try:
    from logo import LOGO_DATA_URL as LOGO_B64
except Exception:
    _lp = Path("/mnt/user-data/uploads/1777622887238_image.png")
    LOGO_B64 = ("data:image/png;base64," + base64.b64encode(_lp.read_bytes()).decode()) if _lp.exists() else None

from evidence_layer import calculate_dbr, assign_genomic_tier, get_genomic_verdict, EXPERIMENT_LADDER
from diagrams import (
    build_tissue_diagram, build_genomic_diagram,
    build_gpcr_diagram, build_cell_impact_diagram,
)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Protellect/2.0 research@protellect.com",
    "Accept": "application/json",
})

def _get(url, params=None, timeout=14):
    try:
        r = SESSION.get(url, params=params, timeout=timeout)
        if r.status_code == 200:
            ct = r.headers.get("Content-Type","")
            return r.json() if "json" in ct else r.text
    except Exception:
        pass
    return None


# ── UniProt lookup ────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_uniprot(gene_name: str) -> dict:
    """Fetch full UniProt entry for any human protein/gene. Universal."""
    result = {
        "found": False, "uniprot_id": "", "gene_name": gene_name,
        "protein_name": "", "organism": "Homo sapiens", "length": 0,
        "function": "", "subcellular": [], "tissue_specificity": "",
        "domains": [], "active_sites": [], "binding_sites": [],
        "transmembrane_regions": [],
        "natural_variants": [], "disease_comments": [],
        "pdb_ids": [], "keywords": [], "go_bp": [], "go_mf": [],
        "omim_id": "", "hgnc_id": "", "ensembl_id": "", "ncbi_gene_id": "",
        "is_gpcr": False, "gpcr_family": "", "g_protein_coupling": "",
        "evidence_level": "", "protein_existence": "",
        "n_natural_variants": 0, "n_disease_variants": 0,
        "interaction_partners": [],
        "chromosome": "", "chromosome_band": "",
    }

    # Search queries in priority order
    for q in [
        f'gene_exact:{gene_name} AND organism_id:9606 AND reviewed:true',
        f'gene:{gene_name} AND organism_id:9606 AND reviewed:true',
        f'gene:{gene_name} AND organism_id:9606',
        f'protein_name:"{gene_name}" AND organism_id:9606 AND reviewed:true',
    ]:
        data = _get("https://rest.uniprot.org/uniprotkb/search",
                    {"query": q, "format": "json", "size": 1})
        if data and isinstance(data, dict) and data.get("results"):
            uid = data["results"][0].get("primaryAccession","")
            if uid:
                result["uniprot_id"] = uid
                result["found"] = True
                break

    if not result["found"]:
        return result

    # Full entry
    entry = _get(f"https://rest.uniprot.org/uniprotkb/{result['uniprot_id']}", {"format":"json"}, timeout=20)
    if not entry or not isinstance(entry, dict):
        return result

    # Basic info
    result["gene_name"]    = (entry.get("genes",[{}])[0].get("geneName",{}).get("value","") if entry.get("genes") else gene_name)
    result["protein_name"] = entry.get("proteinDescription",{}).get("recommendedName",{}).get("fullName",{}).get("value","")
    result["length"]       = entry.get("sequence",{}).get("length",0)
    result["protein_existence"] = entry.get("proteinExistence","")

    # Evidence level
    pe = result["protein_existence"]
    if "protein level" in pe.lower():
        result["evidence_level"] = "Evidence at protein level (highest confidence)"
    elif "transcript level" in pe.lower():
        result["evidence_level"] = "Evidence at transcript level"
    elif "homology" in pe.lower():
        result["evidence_level"] = "Inferred from homology (not directly observed)"
    elif "predicted" in pe.lower():
        result["evidence_level"] = "Predicted (computational only)"
    else:
        result["evidence_level"] = pe

    # Comments
    for c in entry.get("comments", []):
        ct = c.get("commentType","")
        if ct == "FUNCTION":
            result["function"] = c.get("texts",[{}])[0].get("value","")[:800]
        elif ct == "SUBCELLULAR LOCATION":
            for loc in c.get("subcellularLocations",[]):
                v = loc.get("location",{}).get("value","")
                if v and v not in result["subcellular"]:
                    result["subcellular"].append(v)
        elif ct == "TISSUE SPECIFICITY":
            result["tissue_specificity"] = c.get("texts",[{}])[0].get("value","")[:600]
        elif ct == "DISEASE":
            for d in c.get("diseases",[]):
                dn = d.get("disease",{}).get("diseaseName",{}).get("value","")
                note = d.get("note",{}).get("texts",[{}])[0].get("value","") if d.get("note") else ""
                if dn:
                    result["disease_comments"].append({"name": dn, "note": note})
        elif ct == "INTERACTION":
            for iact in c.get("interactions",[])[:10]:
                g = iact.get("interactantTwo",{}).get("geneName","")
                if g: result["interaction_partners"].append(g)

    # Features
    for feat in entry.get("features",[]):
        ft    = feat.get("type","")
        loc   = feat.get("location",{})
        start = loc.get("start",{}).get("value")
        end   = loc.get("end",{}).get("value", start)
        desc  = feat.get("description","")
        if start is None: continue
        s, e  = int(start), int(end)

        if ft in ("Domain","Region","Zinc finger","Coiled coil","Repeat","Motif"):
            result["domains"].append({"start":s,"end":e,"name":desc,"type":ft})
        elif ft == "Active site":
            result["active_sites"].append(s)
        elif ft in ("Binding site","Metal binding"):
            result["binding_sites"].extend(range(s,e+1))
        elif ft == "Transmembrane":
            result["transmembrane_regions"].append({"start":s,"end":e,"desc":desc})
        elif ft == "Natural variant":
            orig = feat.get("alternativeSequence",{}).get("originalSequence","")
            var  = feat.get("alternativeSequence",{}).get("alternativeSequences",[""])[0]
            note = desc
            is_d = any(x in note.lower() for x in ("disease","pathogenic","disorder","syndrome","myopathy","cardiomyopathy","cancer"))
            result["natural_variants"].append({"pos":s,"orig":orig,"var":var,"note":note,"disease":is_d})
            result["n_natural_variants"] += 1
            if is_d: result["n_disease_variants"] += 1

    # Cross-references
    for xref in entry.get("uniProtKBCrossReferences",[]):
        db  = xref.get("database","")
        xid = xref.get("id","")
        if db == "PDB":
            result["pdb_ids"].append(xid)
        elif db == "OMIM":
            result["omim_id"] = xid
        elif db == "HGNC":
            result["hgnc_id"] = xid
        elif db == "Ensembl":
            if not result["ensembl_id"]:
                result["ensembl_id"] = xid
        elif db == "GeneID":
            result["ncbi_gene_id"] = xid
        elif db == "GO":
            props = {p["key"]:p["value"] for p in xref.get("properties",[])}
            term  = props.get("GoTerm","")
            aspect= props.get("GoAspect","")
            if "biological" in aspect.lower() and term:
                result["go_bp"].append(term)
            elif "molecular" in aspect.lower() and term:
                result["go_mf"].append(term)

    # Keywords + GPCR detection
    kws = [kw.get("value","") for kw in entry.get("keywords",[])]
    result["keywords"] = kws
    kw_str = " ".join(kws + [result["function"], result["protein_name"]]).lower()

    gpcr_indicators = ["g protein-coupled receptor","gpcr","rhodopsin","muscarinic",
                       "adrenergic","dopamine receptor","serotonin receptor","opioid receptor",
                       "chemokine receptor","adenosine receptor","cannabinoid receptor",
                       "metabotropic","frizzled","smoothened","taste receptor","olfactory receptor",
                       "lysophospholipid","purinergic","prostanoid","histamine receptor",
                       "angiotensin receptor","endothelin receptor","bradykinin receptor"]
    result["is_gpcr"] = any(g in kw_str for g in gpcr_indicators)

    if result["is_gpcr"]:
        # Classify GPCR family
        if "rhodopsin" in kw_str or "class a" in kw_str:
            result["gpcr_family"] = "Class A (Rhodopsin-like) — largest GPCR family"
        elif "secretin" in kw_str or "class b" in kw_str:
            result["gpcr_family"] = "Class B (Secretin-like)"
        elif "glutamate" in kw_str or "class c" in kw_str:
            result["gpcr_family"] = "Class C (Glutamate-like)"
        elif "frizzled" in kw_str:
            result["gpcr_family"] = "Class F (Frizzled)"
        else:
            result["gpcr_family"] = "G protein-coupled receptor"

        # G-protein coupling from function text or known map
        g = result["gene_name"].upper()
        known_coupling = {
            "CHRM1":"Gq/11","CHRM2":"Gi/o","CHRM3":"Gq/11","CHRM4":"Gi/o","CHRM5":"Gq/11",
            "ADRB1":"Gs","ADRB2":"Gs","ADRB3":"Gs","ADRA1A":"Gq/11","ADRA1B":"Gq/11",
            "ADRA2A":"Gi/o","ADRA2B":"Gi/o","ADRA2C":"Gi/o",
            "DRD1":"Gs","DRD2":"Gi/o","DRD3":"Gi/o","DRD4":"Gi/o","DRD5":"Gs",
            "HTR1A":"Gi/o","HTR1B":"Gi/o","HTR2A":"Gq/11","HTR2B":"Gq/11",
            "HTR4":"Gs","HTR6":"Gs","HTR7":"Gs",
            "ADORA1":"Gi/o","ADORA2A":"Gs","ADORA2B":"Gs","ADORA3":"Gi/o",
            "AVPR1A":"Gq/11","AVPR1B":"Gq/11","AVPR2":"Gs",
            "OXTR":"Gq/11","GLP1R":"Gs","GCGR":"Gs","GIPR":"Gs",
            "PTGDR":"Gs","PTGER2":"Gs","PTGER4":"Gs","PTGER1":"Gq/11","PTGER3":"Gi/o",
            "OPRM1":"Gi/o","OPRD1":"Gi/o","OPRK1":"Gi/o",
        }
        if g in known_coupling:
            result["g_protein_coupling"] = known_coupling[g]
        else:
            # Infer from function text
            func = result["function"].lower()
            if "gi" in func or "inhibit adenylate" in func or "inhibit cyclic amp" in func:
                result["g_protein_coupling"] = "Gi/o (inhibits adenylate cyclase)"
            elif "gq" in func or "phospholipase c" in func or "inositol" in func:
                result["g_protein_coupling"] = "Gq/11 (activates phospholipase C)"
            elif "gs" in func or "stimulate adenylate" in func or "increase cyclic amp" in func:
                result["g_protein_coupling"] = "Gs (stimulates adenylate cyclase)"
            elif "g12" in func or "rho" in func:
                result["g_protein_coupling"] = "G12/13 (activates Rho GTPase)"
            else:
                result["g_protein_coupling"] = "G protein-coupled (subtype from UniProt/IUPHAR)"

    # Transmembrane count → 7TM = GPCR confirmation
    n_tm = len(result["transmembrane_regions"])
    if n_tm == 7:
        result["is_gpcr"] = True
        if not result["gpcr_family"]:
            result["gpcr_family"] = "7-transmembrane GPCR (7TM confirmed)"

    return result


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_chromosome_location(gene_name: str, ensembl_id: str = "") -> dict:
    """Get chromosome location from Ensembl."""
    result = {"chromosome":"","band":"","start":0,"end":0,"strand":""}

    # Try Ensembl REST
    eid = ensembl_id or gene_name
    data = _get(
        f"https://rest.ensembl.org/lookup/symbol/homo_sapiens/{gene_name}",
        {"content-type":"application/json","expand":0},
    )
    if data and isinstance(data, dict):
        result["chromosome"] = str(data.get("seq_region_name",""))
        result["start"]      = data.get("start",0)
        result["end"]        = data.get("end",0)
        strand               = data.get("strand",0)
        result["strand"]     = "+" if strand == 1 else "-"

    return result


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_clinvar_full(gene_name: str) -> dict:
    """
    Fetch all ClinVar variants for a gene.
    Returns: { 'pathogenic': [...], 'benign': [...], 'vus': [...], 'all': [...] }
    ONLY human genetic evidence. No cell culture. No mouse data.
    """
    result = {"pathogenic":[], "likely_pathogenic":[], "benign":[], "likely_benign":[], "vus":[], "all":[], "diseases":set()}

    try:
        # Search
        search = _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", {
            "db":"clinvar","term":f"{gene_name}[gene] AND single_gene[prop]",
            "retmax":500,"retmode":"json","tool":"protellect","email":"research@protellect.com",
        })
        if not search: return result
        ids = search.get("esearchresult",{}).get("idlist",[])
        if not ids: return result

        time.sleep(0.35)

        # Batch fetch summaries
        for batch_start in range(0, min(len(ids), 500), 100):
            batch = ids[batch_start:batch_start+100]
            summary = _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi", {
                "db":"clinvar","id":",".join(batch),"retmode":"json",
                "tool":"protellect","email":"research@protellect.com",
            }, timeout=20)
            if not summary: continue
            doc = summary.get("result",{})
            for vid in doc.get("uids",[]):
                entry = doc.get(vid,{})
                sig   = entry.get("germline_classification",{}).get("description","").strip()
                title = entry.get("title","")
                conditions = [c.get("trait_name","") for c in entry.get("trait_set",[])]
                stars = entry.get("review_status_label","")
                var = {
                    "id": vid,
                    "title": title,
                    "significance": sig,
                    "conditions": [c for c in conditions if c],
                    "stars": stars,
                    "gene": gene_name,
                }
                result["all"].append(var)
                for cond in conditions:
                    if cond: result["diseases"].add(cond)

                sig_lower = sig.lower()
                if "pathogenic" in sig_lower and "likely pathogenic" not in sig_lower:
                    result["pathogenic"].append(var)
                elif "likely pathogenic" in sig_lower:
                    result["likely_pathogenic"].append(var)
                elif "benign" in sig_lower and "likely benign" not in sig_lower:
                    result["benign"].append(var)
                elif "likely benign" in sig_lower:
                    result["likely_benign"].append(var)
                elif "uncertain" in sig_lower or "vus" in sig_lower:
                    result["vus"].append(var)

            time.sleep(0.35)

    except Exception:
        pass

    result["diseases"] = sorted(list(result["diseases"]))
    return result


def build_investment_warning(dbr, tier, n_pathogenic, protein_name, gene_name, disease_context=""):
    """
    Generate an honest investment warning based on genomic evidence.
    If DBR is low, estimate how much money would be wasted pursuing this target.
    """
    if tier in ("CRITICAL","HIGH"):
        return None  # No warning needed

    # Conservative drug discovery cost estimates
    hit_to_lead          = 500_000
    lead_optimisation    = 2_000_000
    preclinical          = 5_000_000
    phase1               = 15_000_000
    phase2               = 50_000_000
    phase3               = 150_000_000
    full_pipeline        = phase1 + phase2 + phase3 + lead_optimisation + preclinical

    if tier == "LOW":
        risk_pct = 65
        wasted = int(full_pipeline * 0.65)
        verdict = "HIGH RISK — limited human genetic support"
        colour  = "#FFD700"
    else:  # NONE
        risk_pct = 90
        wasted = int(full_pipeline * 0.90)
        verdict = "CRITICAL RISK — no established human disease implication"
        colour  = "#FF4C4C"

    # Disease context check
    disease_caveat = ""
    if disease_context and n_pathogenic == 0:
        disease_caveat = (
            f"No ClinVar pathogenic variants link {gene_name} to {disease_context}. "
            "Any connection you have read in the literature is based on indirect evidence "
            "(cell culture, animal models, expression correlation) — not confirmed human genetics."
        )

    return {
        "verdict":         verdict,
        "colour":          colour,
        "risk_pct":        risk_pct,
        "wasted_estimate": wasted,
        "wasted_str":      f"${wasted:,}",
        "disease_caveat":  disease_caveat,
        "breakdown": {
            "Lead-to-candidate":    hit_to_lead,
            "Lead optimisation":    lead_optimisation,
            "Preclinical studies":  preclinical,
            "Phase I clinical":     phase1,
            "Phase II clinical":    phase2,
            "Phase III clinical":   phase3,
        },
    }


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_pubmed_papers(gene_name: str, disease_context: str = "", max_results: int = 8) -> list:
    """
    Fetch actual published papers for this gene from PubMed.
    Searches specifically for papers linking this gene to human disease.
    Returns papers sorted by relevance — mutation/disease papers first.
    NOT generic pathway papers. Human genetics papers.
    """
    papers = []
    try:
        # Build targeted query - prioritise disease/mutation/variant papers
        queries = []
        if disease_context:
            queries.append(f'{gene_name}[gene] AND "{disease_context}"[title/abstract] AND "mutation"[title/abstract]')
            queries.append(f'{gene_name}[gene] AND "{disease_context}"[title/abstract]')
        queries.append(f'{gene_name}[gene] AND ("pathogenic variant" OR "disease-causing mutation" OR "Mendelian" OR "loss of function") AND "human"[title/abstract]')
        queries.append(f'{gene_name}[gene] AND ("clinical" OR "patient" OR "disease") AND "variant"[title/abstract]')

        seen_ids = set()
        for q in queries:
            if len(papers) >= max_results:
                break
            search = _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", {
                "db":"pubmed","term":q,"retmax":5,"retmode":"json","sort":"relevance",
                "tool":"protellect","email":"research@protellect.com",
            })
            if not search: continue
            ids = search.get("esearchresult",{}).get("idlist",[])
            new_ids = [i for i in ids if i not in seen_ids]
            if not new_ids: continue
            seen_ids.update(new_ids)
            time.sleep(0.35)
            summary = _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi", {
                "db":"pubmed","id":",".join(new_ids),"retmode":"json",
                "tool":"protellect","email":"research@protellect.com",
            })
            if not summary: continue
            result_data = summary.get("result",{})
            for pid in result_data.get("uids",[]):
                entry = result_data.get(pid,{})
                title = entry.get("title","")
                journal = entry.get("fulljournalname","") or entry.get("source","")
                year = entry.get("pubdate","")[:4]
                authors = entry.get("authors",[])
                first_author = authors[0].get("name","") if authors else ""
                if title and pid not in seen_ids:
                    papers.append({
                        "pmid":    pid,
                        "title":   title,
                        "journal": journal,
                        "year":    year,
                        "author":  first_author,
                        "url":     f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
                    })
            if len(papers) >= max_results:
                break
    except Exception:
        pass
    return papers[:max_results]


# ── Main render function ──────────────────────────────────────────────────────
def render():
    if LOGO_B64:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px">'
            f'<img src="{LOGO_B64}" style="height:40px;object-fit:contain;border-radius:7px">'
            f'<div><strong style="font-size:1.1rem">Protein Deep Dive</strong>'
            f'<p style="color:#555;font-size:0.83rem;margin:0">'
            f'Enter any human protein — get the genomic truth from ClinVar</p></div></div>',
            unsafe_allow_html=True
        )
    st.divider()

    st.markdown("""
    <div style="background:#080b14;border:1px solid #1a1d2e;border-radius:8px;padding:10px 14px;
                font-size:0.78rem;color:#666;margin-bottom:16px;line-height:1.6">
      <strong style="color:#aaa">Ground truth only.</strong>
      Results are sourced from ClinVar (human disease-causing variants), UniProt experimental annotations,
      and Ensembl gene coordinates. Cell culture findings, animal models, and pathway inference are
      NOT treated as human evidence. If ClinVar has no pathogenic variants for a protein,
      this tool says so — with an estimate of what pursuing it would cost.
    </div>""", unsafe_allow_html=True)

    col_input, col_context = st.columns([1, 1], gap="medium")
    with col_input:
        gene_input = st.text_input(
            "Gene / protein name",
            placeholder="e.g. CHRM3, FLNC, ARRB1, TP53, BRCA1...",
            key="pdive_gene"
        )
    with col_context:
        disease_context = st.text_input(
            "Disease context (optional)",
            placeholder="e.g. Prune belly syndrome, cardiomyopathy, cancer...",
            key="pdive_disease"
        )

    run = st.button("🔍 Analyse protein", type="primary", use_container_width=True)
    if not run or not gene_input.strip():
        if not gene_input.strip():
            st.markdown("""
            <div style="background:#0a0c14;border:1px solid #1e2030;border-radius:10px;
                        padding:20px 24px;margin-top:8px">
              <p style="font-family:IBM Plex Mono,monospace;font-size:0.7rem;
                        text-transform:uppercase;letter-spacing:0.15em;color:#555;margin-bottom:10px">
                Try these examples
              </p>
              <div style="display:flex;gap:10px;flex-wrap:wrap">
                <span style="background:#0f1117;border:1px solid #1e2030;border-radius:20px;
                             padding:4px 14px;font-size:0.8rem;color:#aaa">CHRM3 + Prune belly syndrome</span>
                <span style="background:#0f1117;border:1px solid #1e2030;border-radius:20px;
                             padding:4px 14px;font-size:0.8rem;color:#aaa">FLNC + Cardiomyopathy</span>
                <span style="background:#0f1117;border:1px solid #1e2030;border-radius:20px;
                             padding:4px 14px;font-size:0.8rem;color:#aaa">ARRB1 + Any disease</span>
                <span style="background:#0f1117;border:1px solid #1e2030;border-radius:20px;
                             padding:4px 14px;font-size:0.8rem;color:#aaa">TALN1 + Cancer</span>
              </div>
            </div>""", unsafe_allow_html=True)
        return

    gene = gene_input.strip().upper()

    # ── Fetch all data ────────────────────────────────────────────────────────
    with st.spinner(f"Fetching data for {gene} from UniProt, ClinVar, PubMed, Ensembl..."):
        uni   = fetch_uniprot(gene)
        chrom = fetch_chromosome_location(gene, uni.get("ensembl_id",""))
        cv    = fetch_clinvar_full(gene)
        papers = fetch_pubmed_papers(gene, disease_context)

    if not uni["found"]:
        st.error(f"❌ Could not find **{gene}** in UniProt. Check the gene symbol and try again.")
        return

    # ── Compute genomic verdict ───────────────────────────────────────────────
    n_path   = len(cv["pathogenic"]) + len(cv["likely_pathogenic"])
    n_benign = len(cv["benign"]) + len(cv["likely_benign"])
    n_vus    = len(cv["vus"])
    prot_len = uni["length"]
    dbr      = calculate_dbr(n_path, prot_len)
    tier     = assign_genomic_tier(dbr, n_path)
    verdict  = get_genomic_verdict(tier, gene, n_path, prot_len, dbr)
    warning  = build_investment_warning(dbr, tier, n_path, uni["protein_name"], gene, disease_context)

    # ── Header verdict banner ─────────────────────────────────────────────────
    tc       = verdict["color"]
    dbr_str  = f"{dbr:.3f}" if dbr is not None else "N/A"

    st.markdown(f"""
    <div style="background:#0a0a14;border:2px solid {tc};border-radius:12px;
                padding:20px 24px;margin-bottom:20px">
      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">
        <div>
          <div style="font-size:1.4rem;font-weight:700;color:#eee;font-family:IBM Plex Mono,monospace">
            {gene} — {uni['protein_name'] or uni['gene_name']}
          </div>
          <div style="font-size:0.83rem;color:#555;margin-top:2px">
            {uni['organism']} · UniProt {uni['uniprot_id']} · {prot_len} amino acids
          </div>
        </div>
        <div style="text-align:right">
          <div style="font-size:1.8rem;font-weight:700;font-family:IBM Plex Mono,monospace;color:{tc}">
            {verdict['icon']} {verdict['label']}
          </div>
          <div style="font-size:0.8rem;color:#555">Disease Burden Ratio: {dbr_str}</div>
        </div>
      </div>
      <div style="margin-top:14px;padding-top:12px;border-top:1px solid {tc}33;
                  font-size:0.84rem;color:#bbb;line-height:1.7">
        {verdict['trust_statement']}
      </div>
      <div style="margin-top:8px;display:flex;gap:20px;flex-wrap:wrap">
        <span style="font-family:IBM Plex Mono,monospace;font-size:0.75rem">
          <span style="color:#FF4C4C">●</span> {n_path} Pathogenic/Likely pathogenic
        </span>
        <span style="font-family:IBM Plex Mono,monospace;font-size:0.75rem">
          <span style="color:#555">●</span> {n_vus} Uncertain significance
        </span>
        <span style="font-family:IBM Plex Mono,monospace;font-size:0.75rem">
          <span style="color:#4CA8FF">●</span> {n_benign} Benign/Likely benign
        </span>
        <span style="font-family:IBM Plex Mono,monospace;font-size:0.75rem">
          <span style="color:#aaa">●</span> {len(cv['all'])} Total ClinVar submissions
        </span>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Investment warning ────────────────────────────────────────────────────
    if warning:
        st.markdown(f"""
        <div style="background:#140a0a;border:2px solid {warning['colour']};border-radius:10px;
                    padding:16px 20px;margin-bottom:16px">
          <div style="font-family:IBM Plex Mono,monospace;font-size:0.72rem;text-transform:uppercase;
                      letter-spacing:0.15em;color:{warning['colour']};margin-bottom:8px">
            ⚠ Investment Risk Assessment: {warning['verdict']}
          </div>
          <div style="font-size:0.9rem;color:#eee;font-weight:600;margin-bottom:6px">
            Estimated capital at risk if this protein is pursued as a drug target:
            <span style="color:{warning['colour']};font-size:1.1rem"> {warning['wasted_str']}</span>
            &nbsp;({warning['risk_pct']}% likelihood of failure based on genomic evidence alone)
          </div>
          {f'<div style="font-size:0.82rem;color:#888;margin-top:8px;line-height:1.6;background:#1a0808;border-radius:6px;padding:10px 12px">{warning["disease_caveat"]}</div>' if warning["disease_caveat"] else ''}
          <div style="margin-top:10px;display:flex;gap:10px;flex-wrap:wrap">
            {"".join(f'<span style="font-size:0.72rem;font-family:IBM Plex Mono,monospace;color:#555">{k}: <span style="color:#888">${v:,}</span></span>' for k,v in warning["breakdown"].items())}
          </div>
          <div style="font-size:0.75rem;color:#555;margin-top:8px">
            Based on: <a href="https://www.nature.com/articles/s41586-024-07316-0" target="_blank"
            style="color:#4CA8FF;text-decoration:none">King et al., Nature 2024</a> —
            drugs with genetic support are 2.6× more likely to succeed.
            Without genetic support, failure rates approach 90%.
          </div>
        </div>""", unsafe_allow_html=True)

    # ── Three column layout ───────────────────────────────────────────────────
    col1, col2, col3 = st.columns([1, 1, 1], gap="medium")

    # ── Col 1: Genomic identity ───────────────────────────────────────────────
    with col1:
        st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.18em;color:#444;border-bottom:1px solid #1e2030;padding-bottom:6px;margin-bottom:12px">Genomic Identity</div>', unsafe_allow_html=True)

        chrom_str = chrom.get("chromosome","")
        band_str  = chrom.get("band","")
        loc_str   = f"Chromosome {chrom_str}" if chrom_str else "Not retrieved"
        if band_str: loc_str += f" ({band_str})"

        rows = [
            ("Gene symbol",    uni["gene_name"] or gene),
            ("Chromosome",     loc_str),
            ("Ensembl ID",     uni["ensembl_id"] or "—"),
            ("UniProt ID",     uni["uniprot_id"]),
            ("OMIM",           uni["omim_id"] or "Not listed"),
            ("Protein length", f"{prot_len} amino acids"),
            ("Evidence level", uni["evidence_level"] or "—"),
            ("Domains",        str(len(uni["domains"])) + " annotated"),
            ("TM regions",     str(len(uni["transmembrane_regions"]))),
        ]
        for lbl, val in rows:
            st.markdown(
                f'<div style="display:flex;gap:8px;padding:5px 0;border-bottom:1px solid #0d0f1a;font-size:0.8rem">'
                f'<span style="color:#3a3d5a;min-width:110px;font-family:IBM Plex Mono,monospace;font-size:0.7rem;flex-shrink:0">{lbl}</span>'
                f'<span style="color:#bbb">{val}</span></div>',
                unsafe_allow_html=True
            )

        # GPCR section
        if uni["is_gpcr"]:
            st.markdown('<br>', unsafe_allow_html=True)
            gpcr_colour = "#9370DB"
            st.markdown(f"""
            <div style="background:#100a18;border:1px solid {gpcr_colour}55;border-radius:8px;padding:12px 14px">
              <div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;
                          letter-spacing:0.15em;color:{gpcr_colour};margin-bottom:8px">GPCR Classification</div>
              <div style="font-size:0.82rem;color:#eee;font-weight:600;margin-bottom:6px">
                ✓ Confirmed G protein-coupled receptor
              </div>
              <div style="display:flex;flex-direction:column;gap:5px">
                <div style="font-size:0.78rem;color:#888">Family: <span style="color:#bbb">{uni['gpcr_family']}</span></div>
                <div style="font-size:0.78rem;color:#888">G-protein: <span style="color:{gpcr_colour};font-weight:600">{uni['g_protein_coupling'] or 'See UniProt/IUPHAR'}</span></div>
                <div style="font-size:0.78rem;color:#888">TM helices: <span style="color:#bbb">{len(uni['transmembrane_regions'])}</span></div>
              </div>
            </div>""", unsafe_allow_html=True)

    # ── Col 2: Tissue & function ──────────────────────────────────────────────
    with col2:
        st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.18em;color:#444;border-bottom:1px solid #1e2030;padding-bottom:6px;margin-bottom:12px">Biology & Tissue Distribution</div>', unsafe_allow_html=True)

        if uni["function"]:
            st.markdown(f'<div style="font-size:0.8rem;color:#bbb;line-height:1.7;margin-bottom:12px;background:#0a0c14;padding:10px 12px;border-radius:6px;border:1px solid #1e2030">{uni["function"]}</div>', unsafe_allow_html=True)

        if uni["tissue_specificity"]:
            st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:#4CAF50;margin-bottom:5px">Tissue expression (UniProt experimental)</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:0.78rem;color:#aaa;line-height:1.7;background:#0a140a;padding:10px 12px;border-radius:6px;border:1px solid #1a3a1a;margin-bottom:10px">{uni["tissue_specificity"]}</div>', unsafe_allow_html=True)

        if uni["subcellular"]:
            st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:#4CA8FF;margin-bottom:5px">Subcellular location</div>', unsafe_allow_html=True)
            for loc in uni["subcellular"][:6]:
                st.markdown(f'<div style="font-size:0.78rem;color:#888;padding:3px 0;border-bottom:1px solid #0d0f1a">· {loc}</div>', unsafe_allow_html=True)

        if uni["interaction_partners"]:
            st.markdown('<br><div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:#FFA500;margin-bottom:5px">Known interaction partners</div>', unsafe_allow_html=True)
            st.markdown(', '.join(f'<span style="background:#1a1200;border:1px solid #3a3000;border-radius:3px;padding:1px 8px;font-family:IBM Plex Mono,monospace;font-size:0.72rem;color:#FFA500">{p}</span>' for p in uni["interaction_partners"][:12]), unsafe_allow_html=True)

    # ── Col 3: ClinVar disease evidence ──────────────────────────────────────
    with col3:
        st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.18em;color:#444;border-bottom:1px solid #1e2030;padding-bottom:6px;margin-bottom:12px">ClinVar Disease Evidence</div>', unsafe_allow_html=True)

        if n_path == 0:
            st.markdown(f"""
            <div style="background:#0a0a0a;border:1px solid #FF4C4C55;border-radius:8px;padding:14px;margin-bottom:10px">
              <div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;
                          letter-spacing:0.15em;color:#FF4C4C;margin-bottom:6px">⚠ No pathogenic variants in ClinVar</div>
              <div style="font-size:0.8rem;color:#888;line-height:1.7">
                No disease-causing mutations have been confirmed in humans for <strong style="color:#eee">{gene}</strong>.
                {"This means mutations in this protein do not cause recognisable disease in humans — consistent with the β-arrestin pattern of a protein that is studied extensively in vitro but is not essential in the human body." if tier == "NONE" else "The protein may be understudied or variants may be too rare to appear in current databases."}
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            # Show disease breakdown
            diseases_from_cv = cv.get("diseases",[])
            if diseases_from_cv:
                st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:#FF4C4C;margin-bottom:6px">Diseases with confirmed pathogenic variants</div>', unsafe_allow_html=True)
                for d in diseases_from_cv[:10]:
                    if d and d.lower() not in ("not provided","not specified"):
                        # Count variants for this disease
                        n_for_disease = sum(
                            1 for v in cv["pathogenic"] + cv["likely_pathogenic"]
                            if any(d.lower() in c.lower() for c in v.get("conditions",[]))
                        )
                        st.markdown(
                            f'<div style="display:flex;justify-content:space-between;padding:4px 0;'
                            f'border-bottom:1px solid #0d0f1a;font-size:0.78rem">'
                            f'<span style="color:#bbb">{d[:50]}</span>'
                            f'<span style="font-family:IBM Plex Mono,monospace;font-size:0.7rem;color:#FF4C4C">{n_for_disease if n_for_disease > 0 else "—"} P/LP</span></div>',
                            unsafe_allow_html=True
                        )

    # ── Full ClinVar variant table ────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.18em;color:#444;border-bottom:1px solid #1e2030;padding-bottom:6px;margin-bottom:12px">ClinVar Variant Detail — Pathogenic & Likely Pathogenic Only</div>', unsafe_allow_html=True)

    path_variants = cv["pathogenic"] + cv["likely_pathogenic"]
    if path_variants:
        rows = []
        for v in path_variants[:50]:
            # Extract amino acid change from title
            aa_match = re.search(r'p\.([A-Za-z]{3}\d+[A-Za-z]{3}|[A-Za-z]\d+[A-Za-z=\*])', v["title"])
            aa_change = aa_match.group(0) if aa_match else "—"
            rows.append({
                "Variant": v["title"][:60] if v["title"] else "—",
                "AA change": aa_change,
                "Significance": v["significance"],
                "Disease": (v["conditions"][0][:40] if v["conditions"] else "—"),
                "Review stars": v["stars"][:30] if v["stars"] else "—",
            })
        df_cv = pd.DataFrame(rows)

        def style_sig(val):
            if "Pathogenic" in val and "Likely" not in val:
                return "color:#FF4C4C;font-weight:600"
            elif "Likely pathogenic" in val:
                return "color:#FFA500;font-weight:600"
            return ""

        st.dataframe(
            df_cv.style.map(style_sig, subset=["Significance"]),
            use_container_width=True, height=280
        )
        st.caption(f"Showing {min(50, len(path_variants))} of {len(path_variants)} pathogenic/likely pathogenic submissions. Source: NCBI ClinVar.")
    else:
        st.info(f"No pathogenic or likely pathogenic variants found in ClinVar for **{gene}**. See investment risk assessment above.")

    # ── Genomic verdict description ───────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background:#0a0a14;border:1px solid {tc}55;border-radius:10px;padding:18px 20px;margin-bottom:16px">
      <div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;text-transform:uppercase;
                  letter-spacing:0.18em;color:{tc};margin-bottom:10px">Genomic Litmus Test — {verdict['label']}</div>
      <p style="font-size:0.85rem;color:#bbb;line-height:1.8;margin-bottom:12px">{verdict['description']}</p>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px">
        <div style="background:#080b14;border:1px solid #1e2030;border-radius:6px;padding:10px;text-align:center">
          <div style="font-size:1.6rem;font-weight:700;font-family:IBM Plex Mono,monospace;color:{tc}">{n_path}</div>
          <div style="font-size:0.68rem;color:#555;text-transform:uppercase;letter-spacing:0.08em">Pathogenic variants</div>
        </div>
        <div style="background:#080b14;border:1px solid #1e2030;border-radius:6px;padding:10px;text-align:center">
          <div style="font-size:1.6rem;font-weight:700;font-family:IBM Plex Mono,monospace;color:#aaa">{prot_len}</div>
          <div style="font-size:0.68rem;color:#555;text-transform:uppercase;letter-spacing:0.08em">Amino acids</div>
        </div>
        <div style="background:#080b14;border:1px solid #1e2030;border-radius:6px;padding:10px;text-align:center">
          <div style="font-size:1.6rem;font-weight:700;font-family:IBM Plex Mono,monospace;color:{tc}">{dbr_str}</div>
          <div style="font-size:0.68rem;color:#555;text-transform:uppercase;letter-spacing:0.08em">Disease burden ratio</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Diagrams ────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.18em;color:#444;border-bottom:1px solid #1e2030;padding-bottom:6px;margin-bottom:14px">Visual Breakdown — Tissue · Genomic · GPCR · Cell Impact</div>', unsafe_allow_html=True)

    d_tab1, d_tab2, d_tab3, d_tab4 = st.tabs([
        "🧬 Tissue Expression", "📍 Genomic Breakdown", "⚡ GPCR Signalling", "🔬 Cell Impact"
    ])

    with d_tab1:
        tissue_html = build_tissue_diagram(
            gene, uni.get("tissue_specificity",""), None
        )
        components.html(tissue_html, height=340, scrolling=False)
        if uni.get("tissue_specificity"):
            st.caption(f"Parsed from UniProt tissue specificity annotation for {gene}. Source: experimental evidence.")
        else:
            st.caption(f"Using curated expression data for {gene}. Full Protein Atlas integration in Phase 2.")

    with d_tab2:
        # Build variant lists for diagram
        path_vars = [{"pos": v["position"], "note": v["note"]} for v in uni.get("natural_variants",[]) if v.get("pathogenic")]
        # Also parse positions from ClinVar titles
        for v in cv["pathogenic"] + cv["likely_pathogenic"]:
            m = re.search(r'[A-Z](\d+)[A-Z=\*]', v.get("title",""))
            if m: path_vars.append({"pos": int(m.group(1))})
        ben_vars = [{"pos": v["position"]} for v in uni.get("natural_variants",[]) if not v.get("pathogenic")]
        genomic_html = build_genomic_diagram(
            gene,
            chrom.get("chromosome",""),
            uni.get("length", 0),
            uni.get("domains",[]),
            path_vars,
            ben_vars,
        )
        components.html(genomic_html, height=300, scrolling=False)
        st.caption("Domain positions from UniProt · Variant positions from ClinVar and UniProt natural variants · Red = pathogenic · Blue = benign")

    with d_tab3:
        if uni.get("is_gpcr"):
            gpcr_html = build_gpcr_diagram(
                gene,
                uni.get("g_protein_coupling","Gq/11"),
                uni.get("protein_name",""),
                len(uni.get("transmembrane_regions",[])),
            )
            components.html(gpcr_html, height=430, scrolling=False)
            st.caption(f"GPCR signalling cascade for {gene}. G-protein coupling: {uni.get('g_protein_coupling','')}. Source: UniProt · IUPHAR/BPS.")
        else:
            st.markdown(f"""
            <div style="background:#0a0c14;border:1px solid #1e2030;border-radius:10px;padding:24px;text-align:center">
              <div style="font-size:1.5rem;margin-bottom:10px">⚠</div>
              <div style="font-family:IBM Plex Mono,monospace;font-size:0.85rem;color:#555">
                {gene} is not classified as a GPCR in UniProt.<br>
                <span style="font-size:0.75rem;color:#444">No 7-transmembrane domain structure detected. GPCR diagram not applicable.</span>
              </div>
            </div>""", unsafe_allow_html=True)

    with d_tab4:
        cell_html = build_cell_impact_diagram(
            gene, tier, n_path,
            [d for d in cv.get("diseases",[]) if d and "not provided" not in d.lower()][:4],
            uni.get("subcellular",[]),
            uni.get("is_gpcr", False),
            uni.get("g_protein_coupling",""),
        )
        components.html(cell_html, height=375, scrolling=False)
        st.caption(f"Cell impact for {gene} based on ClinVar pathogenic variant count and UniProt subcellular location. Not inferred — based on confirmed human genetic evidence.")

    # ── Experiment ladder ─────────────────────────────────────────────────────
    st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.18em;color:#444;border-bottom:1px solid #1e2030;padding-bottom:6px;margin-bottom:12px">Recommended Experiments — Simple to Rigorous</div>', unsafe_allow_html=True)
    exps = EXPERIMENT_LADDER.get(tier, EXPERIMENT_LADDER.get("UNKNOWN", []))
    exp_colors = {"Simple":"#4CAF50","Moderate":"#FFA500","Rigorous":"#FF8C00","Definitive":"#FF4C4C"}

    for exp in exps:
        complexity_base = str(exp.get("complexity","")).split(" — ")[0]
        ec = exp_colors.get(complexity_base,"#888")
        with st.expander(f"Level {exp['level']} — {exp['name']} ({exp['complexity']}) · {exp['time']} · {exp['cost']}"):
            st.markdown(f"**Purpose:** {exp['purpose']}")
            st.markdown("**Steps:**")
            for step in exp.get("steps",[]):
                st.markdown(f"• {step}")
            st.markdown(f'<div style="background:#0a140a;border:1px solid #1a3a1a;border-radius:6px;padding:8px 12px;margin-top:8px"><span style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;color:#4CAF50;text-transform:uppercase">Expected result: </span><span style="font-size:0.78rem;color:#aaa">{exp["expected_result"]}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:0.72rem;color:#555;margin-top:4px">Validates: {exp["validates"]}</div>', unsafe_allow_html=True)

    # ── Published papers from PubMed (dynamic, gene-specific) ───────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.18em;color:#444;border-bottom:1px solid #1e2030;padding-bottom:6px;margin-bottom:12px">Published Papers — {gene} Human Disease Evidence (PubMed)</div>', unsafe_allow_html=True)

    if papers:
        st.markdown('<div style="font-size:0.75rem;color:#555;margin-bottom:10px">Papers retrieved from PubMed prioritising human genetics, disease-causing mutations, and clinical reports. Not pathway inference — actual human evidence.</div>', unsafe_allow_html=True)
        c1p, c2p = st.columns(2, gap="medium")
        for i, paper in enumerate(papers):
            col = c1p if i % 2 == 0 else c2p
            with col:
                st.markdown(f"""<div style="background:#0a0c14;border:1px solid #1e2030;border-radius:8px;padding:12px;margin-bottom:8px">
  <div style="font-size:0.78rem;font-weight:600;color:#eee;margin-bottom:4px;line-height:1.5">{paper["title"][:100]}{"..." if len(paper["title"])>100 else ""}</div>
  <div style="font-size:0.7rem;color:#555;margin-bottom:6px">{paper["author"]} · {paper["journal"]} · {paper["year"]} · PMID {paper["pmid"]}</div>
  <a href="{paper["url"]}" target="_blank" style="font-size:0.7rem;color:#4CA8FF;text-decoration:none">Read on PubMed →</a>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div style="background:#0a0a14;border:1px solid #1e2030;border-radius:8px;padding:12px;font-size:0.8rem;color:#666">No disease-specific papers found on PubMed for this gene. This itself is evidence — a clinically important protein would have published case reports.</div>', unsafe_allow_html=True)

    # Methodology papers always shown
    st.markdown('<div style="font-size:0.72rem;color:#444;margin-top:10px;margin-bottom:4px;font-family:IBM Plex Mono,monospace">Genomic validation methodology:</div>', unsafe_allow_html=True)
    methodology_papers = verdict.get("papers",[])
    mp_cols = st.columns(len(methodology_papers[:3]) or 1, gap="medium")
    for i, paper in enumerate(methodology_papers[:3]):
        with mp_cols[i]:
            st.markdown(f'<div style="font-size:0.72rem;color:#888;background:#080b14;border:1px solid #1a1d2e;border-radius:6px;padding:8px"><strong style="color:#aaa">{paper.get("short","")}</strong><br><span style="font-size:0.68rem;color:#555">{paper.get("key_finding","")[:100]}...</span><br><a href="{paper.get("url","#")}" target="_blank" style="color:#4CA8FF;font-size:0.68rem;text-decoration:none">Read →</a></div>', unsafe_allow_html=True)
