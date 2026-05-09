import streamlit as st
import requests
import re
import json
from datetime import datetime

st.set_page_config(
    page_title="Protellect — Biology Intelligence",
    page_icon="🔬", layout="wide",
    initial_sidebar_state="collapsed"
)

# ═══════════════════════════════════════════════════════════════════════════════
#  STYLES
# ═══════════════════════════════════════════════════════════════════════════════
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
*{box-sizing:border-box;font-family:'Space Grotesk',sans-serif}
code,.mono{font-family:'JetBrains Mono',monospace}
#MainMenu,footer,header,[data-testid="stDeployButton"]{display:none!important}
[data-testid="stSidebar"]{background:#030810!important;border-right:1px solid #0d2545!important}
.block-container{padding:0!important;max-width:100%!important}
[data-testid="stAppViewContainer"]{background:#010306}
div[data-testid="metric-container"]{background:#070d1a;border:1px solid #0d2545;border-radius:12px;padding:.8rem}
div[data-testid="metric-container"] label{color:#3a6080!important;font-size:.72rem!important;letter-spacing:.05em!important;text-transform:uppercase!important}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{color:#00e5ff!important;font-size:1.5rem!important;font-weight:600!important}
.stTabs [data-baseweb="tab-list"]{gap:2px;background:#030810;border-radius:10px;padding:4px;border:1px solid #0d2545}
.stTabs [data-baseweb="tab"]{background:transparent;color:#3a6080;border-radius:8px;font-size:.78rem;padding:.3rem .9rem;font-weight:500}
.stTabs [aria-selected="true"]{background:#0d2545!important;color:#00e5ff!important}
.stButton>button{background:transparent;border:1px solid #0d2545;color:#d0e8ff;font-size:.82rem;border-radius:8px;font-family:'Space Grotesk',sans-serif;font-weight:500;transition:all .2s}
.stButton>button:hover{border-color:#00e5ff44;color:#00e5ff;background:#00e5ff08}
.stTextInput>div>div>input,.stSelectbox>div>div,.stTextArea textarea{background:#030810!important;border:1px solid #0d2545!important;color:#d0e8ff!important;border-radius:8px!important;font-family:'Space Grotesk',sans-serif!important}
.stExpander{border:1px solid #0d2545!important;border-radius:10px!important;background:#040c14!important;margin-bottom:.3rem!important}
h1,h2,h3{color:#d0e8ff!important;font-family:'Space Grotesk',sans-serif!important}
a{color:#00e5ff!important;text-decoration:none!important}
a:hover{opacity:.8!important}
.stAlert{border-radius:10px!important}

/* Splash animations */
@keyframes fadeUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:.6}50%{opacity:1}}
@keyframes rotate{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
@keyframes scanline{0%{top:-4px}100%{top:100%}}
@keyframes glow{0%,100%{box-shadow:0 0 20px #00e5ff22}50%{box-shadow:0 0 40px #00e5ff55}}
</style>"""

st.markdown(CSS, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════
if "domain" not in st.session_state:
    st.session_state.domain = None
if "gene_data" not in st.session_state:
    st.session_state.gene_data = {}

# ═══════════════════════════════════════════════════════════════════════════════
#  API LAYER — real data only, no hallucinations
# ═══════════════════════════════════════════════════════════════════════════════
ESEARCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
EFETCH   = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

@st.cache_data(ttl=3600, show_spinner=False)
def api_uniprot(gene: str) -> dict:
    """Fetch protein data from UniProt REST API. Human only (taxonId 9606)."""
    try:
        r = requests.get(
            "https://rest.uniprot.org/uniprotkb/search",
            params={"query": f"gene:{gene} AND organism_id:9606 AND reviewed:true",
                    "format": "json", "size": 1},
            timeout=12
        )
        results = r.json().get("results", [])
        if not results:
            return {}
        p = results[0]
        uid  = p.get("primaryAccession", "")
        name = (p.get("proteinDescription", {})
                  .get("recommendedName", {})
                  .get("fullName", {})
                  .get("value", ""))
        gene_sym = p.get("genes", [{}])[0].get("geneName", {}).get("value", gene)
        func = ""
        diseases = []
        tissues   = []
        for c in p.get("comments", []):
            ct = c.get("commentType", "")
            if ct == "FUNCTION" and not func:
                func = " ".join(t.get("value", "") for t in c.get("texts", []))[:400]
            if ct == "DISEASE":
                d = c.get("disease", {})
                diseases.append({
                    "name": d.get("diseaseId", d.get("diseaseName", "")),
                    "desc": " ".join(t.get("value", "") for t in c.get("texts", []))[:200]
                })
            if ct == "TISSUE SPECIFICITY":
                tissues.append(" ".join(t.get("value", "") for t in c.get("texts", []))[:200])
        length = p.get("sequence", {}).get("length", 0)
        organism = p.get("organism", {}).get("commonName", "Human")
        taxon = p.get("organism", {}).get("taxonId", 0)
        return {"uid": uid, "name": name, "gene": gene_sym, "function": func,
                "diseases": diseases[:8], "tissues": tissues[:3],
                "length": length, "organism": organism, "taxon": taxon,
                "human": taxon == 9606}
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(ttl=3600, show_spinner=False)
def api_clinvar(gene: str) -> list:
    """Fetch ClinVar variants — returns scored list. P/LP only in triage."""
    try:
        r = requests.get(ESEARCH, params={
            "db": "clinvar", "term": f"{gene}[gene] AND (pathogenic[clinsig] OR likely_pathogenic[clinsig])",
            "retmax": 40, "retmode": "json"
        }, timeout=12)
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []
        r2 = requests.get(EFETCH, params={
            "db": "clinvar", "id": ",".join(ids[:30]), "rettype": "vcv", "retmode": "json"
        }, timeout=15)
        data = r2.json()
        variants = []
        for uid, entry in data.get("result", {}).items():
            if uid == "uids": continue
            title = entry.get("title", "")
            cs    = entry.get("clinical_significance", {}).get("description", "")
            stars = entry.get("review_status", {}).get("stars", 0)
            cond  = "; ".join(entry.get("trait_set", [{}])[0].get("trait_name", [""]) if entry.get("trait_set") else [""])
            score = (5 if "pathogenic" in cs.lower() and "likely" not in cs.lower()
                     else 4 if "likely pathogenic" in cs.lower() else 0)
            score += min(stars, 2)
            variants.append({
                "uid": uid, "title": title, "cs": cs, "stars": stars,
                "condition": cond, "score": score,
                "ml_rank": ("CRITICAL" if score >= 6 else "HIGH" if score >= 5 else "MODERATE" if score >= 4 else "LOW"),
                "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/"
            })
        return sorted(variants, key=lambda x: -x["score"])
    except:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def api_gnomad(gene: str) -> dict:
    """Fetch gnomAD constraint metrics."""
    try:
        q = """{ gene(gene_symbol: "%s", reference_genome: GRCh38) {
            gnomad_constraint { pli oe_lof oe_lof_upper oe_mis } } }""" % gene
        r = requests.post("https://gnomad.broadinstitute.org/api", json={"query": q}, timeout=12)
        c = r.json().get("data", {}).get("gene", {}).get("gnomad_constraint", {})
        return {"pLI": round(c.get("pli", 0), 3),
                "oe_lof": round(c.get("oe_lof", 1), 3),
                "oe_mis": round(c.get("oe_mis", 1), 3)}
    except:
        return {}

@st.cache_data(ttl=3600, show_spinner=False)
def api_string(gene: str) -> list:
    """Fetch STRING interaction partners — deduplicated."""
    try:
        r = requests.get(
            "https://string-db.org/api/json/network",
            params={"identifiers": gene, "species": 9606,
                    "required_score": 700, "limit": 10},
            timeout=12
        )
        seen = set()
        partners = []
        for item in r.json():
            a = item.get("preferredName_A", "")
            b = item.get("preferredName_B", "")
            partner = b if a.upper() == gene.upper() else a
            if partner and partner.upper() != gene.upper() and partner not in seen:
                seen.add(partner)
                partners.append({"partner": partner,
                                  "score": round(item.get("score", 0), 3),
                                  "mode": item.get("mode", "")})
        return partners[:8]
    except:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def api_opentargets(gene: str) -> dict:
    """Fetch OpenTargets data — drugs, tractability, disease associations."""
    try:
        # First get Ensembl ID
        r0 = requests.get(
            f"https://mygene.info/v3/query?q={gene}&species=human&fields=ensembl.gene",
            timeout=8
        )
        hits = r0.json().get("hits", [])
        if not hits: return {}
        ensembl = hits[0].get("ensembl", {})
        if isinstance(ensembl, list): ensembl = ensembl[0]
        eid = ensembl.get("gene", "")
        if not eid: return {}

        q = """query($id:String!){ target(ensemblId:$id){
            knownDrugs{ rows{ drug{ name maxClinicalTrialPhase } approvedIndications phase } }
            tractability{ label modality value }
            associatedDiseases(page:{size:5}){ rows{ disease{ name } score } }
        }}"""
        r = requests.post(
            "https://api.platform.opentargets.org/api/v4/graphql",
            json={"query": q, "variables": {"id": eid}},
            timeout=12
        )
        t = r.json().get("data", {}).get("target", {})
        drugs = [{"name": row.get("drug", {}).get("name", ""),
                  "phase": row.get("phase", 0),
                  "indication": (row.get("approvedIndications") or [""])[0]}
                 for row in (t.get("knownDrugs") or {}).get("rows", [])[:6]]
        tract = [x.get("label", "") for x in (t.get("tractability") or []) if x.get("value")]
        diseases = [{"name": row.get("disease", {}).get("name", ""),
                     "score": round(row.get("score", 0), 3)}
                    for row in (t.get("associatedDiseases") or {}).get("rows", [])[:5]]
        return {"drugs": drugs, "tractability": tract, "disease_assoc": diseases, "ensembl": eid}
    except:
        return {}

@st.cache_data(ttl=3600, show_spinner=False)
def api_alphamissense(uniprot_id: str) -> dict:
    """Fetch AlphaMissense per-residue pathogenicity from EBI."""
    try:
        r = requests.get(
            f"https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}",
            timeout=10
        )
        data = r.json()
        if not data: return {}
        am_url = data[0].get("amAnnotationsUrl", "")
        if not am_url: return {}
        r2 = requests.get(am_url, timeout=15)
        lines = r2.text.strip().split("\n")
        scores = []
        pathogenic_count = 0
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) >= 4:
                try:
                    pos = int(parts[1])
                    score = float(parts[3])
                    cls = parts[4].strip() if len(parts) > 4 else ""
                    scores.append({"pos": pos, "score": score, "class": cls})
                    if score >= 0.564: pathogenic_count += 1
                except: pass
        mean_score = round(sum(s["score"] for s in scores) / len(scores), 3) if scores else 0
        return {"scores": scores[:50], "pathogenic_count": pathogenic_count,
                "mean_score": mean_score, "total": len(scores)}
    except:
        return {}

@st.cache_data(ttl=3600, show_spinner=False)
def api_pubmed(query: str, n: int = 8) -> list:
    """Multi-query PubMed fetch with abstract retrieval and evidence classification."""
    try:
        r = requests.get(ESEARCH, params={
            "db": "pubmed", "term": query, "retmax": n,
            "retmode": "json", "sort": "relevance"
        }, timeout=12)
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids: return []
        r2 = requests.get(ESUMMARY, params={
            "db": "pubmed", "id": ",".join(ids), "retmode": "json"
        }, timeout=12)
        result = r2.json().get("result", {})
        papers = []
        for uid in result.get("uids", []):
            e = result.get(uid, {})
            authors = ", ".join(a.get("name", "") for a in e.get("authors", [])[:3])
            if len(e.get("authors", [])) > 3: authors += " et al."
            title  = e.get("title", "")
            journal= e.get("source", "")
            year   = e.get("pubdate", "")[:4]
            doi    = e.get("elocationid", "").replace("doi: ", "")
            pt     = [p.get("value", "").lower() for p in e.get("pubtype", [])]
            tier   = classify_tier(title, " ".join(pt))
            papers.append({"pmid": uid, "title": title, "authors": authors,
                           "journal": journal, "year": year, "doi": doi,
                           "tier": tier, "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"})
        return papers
    except:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def api_alphafold(uniprot_id: str) -> dict:
    """Fetch AlphaFold structure metadata and pLDDT."""
    try:
        r = requests.get(
            f"https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}",
            timeout=10
        )
        data = r.json()
        if not data: return {}
        return {
            "pdb_url": data[0].get("pdbUrl", ""),
            "model_url": data[0].get("cifUrl", ""),
            "version": data[0].get("latestVersion", ""),
            "af_url": f"https://alphafold.ebi.ac.uk/entry/{uniprot_id}"
        }
    except:
        return {}

# ═══════════════════════════════════════════════════════════════════════════════
#  EVIDENCE + STUDY QUALITY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
TIER_MAP = {
    "Tier 1 — RCT": {"color": "#00c896", "weight": 10},
    "Tier 2 — Cohort": {"color": "#4a90d9", "weight": 8},
    "Tier 3 — Functional": {"color": "#ff8c42", "weight": 7},
    "Tier 4 — Structural": {"color": "#a855f7", "weight": 6},
    "Tier 5 — Animal": {"color": "#ffd60a", "weight": 5},
    "Tier 6 — Computational": {"color": "#5a8090", "weight": 4},
    "Tier 7 — Case report": {"color": "#3a5a7a", "weight": 3},
    "Tier 8 — Review": {"color": "#2a4060", "weight": 2},
    "Tier 9 — Preprint": {"color": "#ff2d55", "weight": 1},
}

def classify_tier(title: str, abstract: str = "") -> str:
    t = (title + " " + abstract).lower()
    if any(x in t for x in ["randomised","randomized","rct","placebo-controlled","double-blind"]): return "Tier 1 — RCT"
    if any(x in t for x in ["cohort","prospective","retrospective","patients with","case-control","multicentre"]): return "Tier 2 — Cohort"
    if any(x in t for x in ["crispr","knock-in","knock-out","functional assay","western blot","immunoprecipitation","luciferase","splicing assay","protein function"]): return "Tier 3 — Functional"
    if any(x in t for x in ["crystal structure","cryo-em","nmr structure","x-ray","alphafold","molecular dynamics","spr","itc","binding affinity"]): return "Tier 4 — Structural"
    if any(x in t for x in ["mouse model","zebrafish","drosophila","xenograft","in vivo","murine model","animal model"]): return "Tier 5 — Animal"
    if any(x in t for x in ["computational","in silico","machine learning","deep learning","neural network","algorithm","prediction model"]): return "Tier 6 — Computational"
    if any(x in t for x in ["case report","case series","patient report","single patient"]): return "Tier 7 — Case report"
    if any(x in t for x in ["review","meta-analysis","systematic review","narrative review","pooled analysis"]): return "Tier 8 — Review"
    return "Tier 9 — Preprint"

def detect_study_weaknesses(title: str, abstract: str = "", cv_variants: list = None) -> list:
    """
    Detect common methodological problems in published studies.
    Returns list of warnings with explanation.
    """
    warnings = []
    t = (title + " " + abstract).lower()

    # No genetic validation
    if any(x in t for x in ["beta-arrestin","beta arrestin","arrestin"]):
        has_cv = cv_variants and len([v for v in cv_variants if "arrb" in v.get("title","").lower()]) > 0
        if not has_cv:
            warnings.append(("⚠️ No germline disease variants", "Study uses beta-arrestin as a readout or target but provides no evidence that ARRB mutations cause Mendelian disease. Beta-arrestin phosphorylation codes are background kinase noise — only residues whose mutation causes disease are validated signals. ARRB1/ARRB2 double KO mice are viable."))

    # Cell line bias
    if any(x in t for x in ["hek293","hek 293","cos-7","cos7","u2os","cancer cell line"]):
        warnings.append(("⚠️ Cell line artefact risk", "Results from transformed cell lines (HEK293, COS-7, U2OS) may not reflect primary cell biology. Kinase activation in cancer lines causes promiscuous non-specific phosphorylation. Results should be validated in patient-derived primary cells or isogenic CRISPR knock-in models."))

    # Overexpression
    if any(x in t for x in ["overexpressed","overexpression","transiently transfected","ectopic"]):
        warnings.append(("⚠️ Overexpression artefact", "Ectopic overexpression can produce non-physiological protein concentrations causing artefactual interactions, phosphorylation, and signalling. Endogenous tagging (CRISPR knock-in) or primary cell validation required for mechanistic conclusions."))

    # No patient data
    if any(x in t for x in ["in vitro","cell-free","biochemical assay"]) and not any(x in t for x in ["patient","clinical","cohort","human sample"]):
        warnings.append(("⚠️ No patient validation", "Purely in vitro biochemical study. Findings have not been validated in patient samples or disease models. Translational relevance uncertain without genetic evidence in human disease."))

    # Small sample
    if any(x in t for x in ["n=3","n=4","n=5","three replicates","four replicates","n = 3","n = 4"]):
        warnings.append(("⚠️ Very small sample (n≤5)", "Statistical power is insufficient at n≤5 biological replicates for mechanistic conclusions. Findings may not be reproducible. Look for independent validation in separate labs."))

    # GRK/arrestin code claim
    if any(x in t for x in ["phosphorylation code","barcode","grk phosphorylation pattern"]):
        warnings.append(("⚠️ Phosphorylation 'code' claim", "GRK phosphorylation codes on GPCRs are controversial. PhosphoSite shows that most GPCR phosphorylation sites lack disease variant evidence — they represent background kinase activity, not a programmable code. This study should demonstrate that specific phospho-residue mutations cause disease."))

    return warnings

def gi_score(cv_variants: list, prot_length: int) -> dict:
    """Genomic integrity scoring — strict thresholds."""
    if not cv_variants:
        return {"verdict": "NO DISEASE VARIANTS", "color": "#1e3a5a",
                "pursue": "deprioritise", "n": 0, "per100": 0, "density": 0,
                "icon": "⚪", "explanation": "Zero pathogenic variants in ClinVar. Cannot classify as a disease driver without genetic evidence."}
    n = len(cv_variants)
    density = n / max(prot_length, 1)
    per100  = n / (prot_length / 100) if prot_length else 0
    n_crit  = sum(1 for v in cv_variants if v.get("ml_rank") == "CRITICAL")

    if per100 >= 1.0 and n >= 5 and n_crit >= 1:
        return {"verdict": "DISEASE-CRITICAL", "color": "#ff2d55", "pursue": "prioritise",
                "n": n, "per100": round(per100,2), "density": round(density,4),
                "icon": "🔴", "explanation": f"{n} confirmed germline pathogenic variants. {n_crit} CRITICAL (multi-star ClinVar review). Strong genetic validation — this protein is a genuine disease driver."}
    elif per100 >= 0.5 or n >= 15:
        return {"verdict": "DISEASE-ASSOCIATED", "color": "#ff8c42", "pursue": "proceed",
                "n": n, "per100": round(per100,2), "density": round(density,4),
                "icon": "🟠", "explanation": f"{n} pathogenic variants. Meaningful association. Focus only on confirmed P/LP variants for drug target work."}
    elif n >= 3:
        return {"verdict": "MODERATE", "color": "#ffd60a", "pursue": "selective",
                "n": n, "per100": round(per100,2), "density": round(density,4),
                "icon": "🟡", "explanation": f"{n} pathogenic variants but low density. Be selective — do not extrapolate beyond confirmed P/LP entries."}
    else:
        return {"verdict": "VERY LOW", "color": "#3a5a7a", "pursue": "caution",
                "n": n, "per100": round(per100,2), "density": round(density,4),
                "icon": "🔵", "explanation": f"Only {n} pathogenic variants. Very low disease burden. May be redundant or compensated by other genes."}

# ═══════════════════════════════════════════════════════════════════════════════
#  UI HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def sh(icon, title, color="#00e5ff"):
    st.markdown(f"<div style='display:flex;align-items:center;gap:8px;margin:1rem 0 .4rem'>"
                f"<span style='font-size:1rem'>{icon}</span>"
                f"<span style='color:{color};font-weight:600;font-size:.95rem;letter-spacing:-.01em'>{title}</span>"
                f"</div>", unsafe_allow_html=True)

def badge(text, color="#00e5ff"):
    return (f"<span style='background:{color}18;color:{color};font-size:.7rem;"
            f"padding:2px 9px;border-radius:8px;border:1px solid {color}44;"
            f"font-weight:600;letter-spacing:.02em'>{text}</span>")

def card_html(html, border_color="#0d2545", bg="#040c14"):
    st.markdown(
        f"<div style='background:{bg};border:1px solid {border_color};"
        f"border-radius:12px;padding:1rem 1.2rem;margin-bottom:.5rem'>{html}</div>",
        unsafe_allow_html=True
    )

def src_link(label, url):
    return (f"<a href='{url}' target='_blank' style='display:inline-flex;align-items:center;"
            f"gap:3px;font-size:.72rem;color:#00e5ff;background:#00e5ff0d;border:1px solid #00e5ff33;"
            f"border-radius:6px;padding:2px 8px;margin:2px;text-decoration:none'>{label} ↗</a>")

def tier_badge(tier):
    c = TIER_MAP.get(tier, {}).get("color", "#3a5a7a")
    return badge(tier, c)

def warn_box(title, body):
    st.markdown(
        f"<div style='background:#0a0205;border:1px solid #ff2d5544;border-radius:10px;"
        f"padding:.7rem 1rem;margin:.3rem 0'>"
        f"<div style='color:#ff2d55;font-weight:600;font-size:.8rem;margin-bottom:2px'>{title}</div>"
        f"<div style='color:#6a3040;font-size:.8rem;line-height:1.6'>{body}</div></div>",
        unsafe_allow_html=True
    )

def insight_box(body, color="#00e5ff"):
    st.markdown(
        f"<div style='background:{color}0a;border:1px solid {color}33;border-radius:10px;"
        f"padding:.8rem 1rem;margin:.4rem 0'>"
        f"<div style='color:{color};font-size:.84rem;line-height:1.7'>{body}</div></div>",
        unsafe_allow_html=True
    )

# ═══════════════════════════════════════════════════════════════════════════════
#  DOMAIN DATA
# ═══════════════════════════════════════════════════════════════════════════════
DOMAINS = {
    "neuro": {
        "label": "Neuroscience & Pharma",
        "icon": "🧠",
        "color": "#a855f7",
        "tagline": "CNS targets, neurodegeneration, psychiatric pharmacology, BBB penetration",
        "gradient": "linear-gradient(135deg, #1a0a2e 0%, #010306 100%)",
        "accent": "#a855f7",
        "key_genes": ["APP","MAPT","SNCA","LRRK2","GBA","PSEN1","PSEN2","HTT","BDNF","DRD2","SERT","GluN2B","GRIN2A","CACNA1A","SCN1A"],
        "pubmed_qs": [
            "Alzheimer disease genetic variant mechanism 2023 2024[pdat]",
            "Parkinson disease LRRK2 GBA drug target 2023 2024[pdat]",
            "psychiatric drug mechanism CNS 2023 2024[pdat]",
            "neurodegeneration protein aggregation therapeutic 2023 2024[pdat]"
        ],
        "databases": [
            ("DisGeNET","https://www.disgenet.org","Free/API","Gene-disease associations — 1M+ entries including CNS"),
            ("AlzForum","https://www.alzforum.org","Free","Alzheimer research — mutations, drugs, models"),
            ("PDGene","https://pdgene.org","Free","Parkinson disease genetics database"),
            ("SynGO","https://www.syngoportal.org","Free","Synaptic gene ontology — postsynaptic density"),
            ("BRAINCODE","https://www.humanbraincode.org","Free","Human brain transcriptomics atlas"),
            ("NeuroMorpho","http://neuromorpho.org","Free","3D neuron morphology database — 100K+ cells"),
        ],
        "tools": [("Allen Brain Atlas","https://portal.brain-map.org"),("OpenNeuro","https://openneuro.org"),("neuroSynth","https://neurosynth.org")],
        "key_facts": [
            "Tau (MAPT) hyperphosphorylation: 85 phospho-sites detected on PhosphoSite — most are kinase noise. Only sites whose mutation causes disease (e.g. R406W in frontotemporal dementia) are validated signals",
            "GBA variants (N370S, L444P) are the most common genetic risk factor for Parkinson disease — 5–10× increased risk",
            "LRRK2 G2019S is the most common dominant PD mutation — 1–2% of all PD globally; >40% in Ashkenazi Jewish and North African Arab populations",
            "BBB penetration: MW <500 Da, log P 1–3, few H-bond donors — CNS drugs must satisfy these constraints",
            "APP duplication causes early-onset Alzheimer (founder principle: gene dosage is sufficient)",
            "DRD2 is the primary target of all antipsychotic drugs — occupancy >65% correlates with therapeutic effect",
            "α-synuclein (SNCA) multiplication (duplication, triplication) causes PD — dose effect confirms protein gain-of-function"
        ],
        "arrb_note": True
    },
    "onco": {
        "label": "Oncology",
        "icon": "🎗️",
        "color": "#ff2d55",
        "tagline": "Somatic mutations, tumour suppressors, oncogenes, liquid biopsy, immunotherapy",
        "gradient": "linear-gradient(135deg, #1a0205 0%, #010306 100%)",
        "accent": "#ff2d55",
        "key_genes": ["TP53","KRAS","BRCA1","BRCA2","EGFR","HER2","CDKN2A","PIK3CA","BRAF","ALK","MET","RET","FGFR1","PD-L1","CTLA4"],
        "pubmed_qs": [
            "KRAS G12C inhibitor clinical trial resistance 2023 2024[pdat]",
            "tumour mutational burden immunotherapy response 2023 2024[pdat]",
            "circulating tumour DNA liquid biopsy early detection 2023 2024[pdat]",
            "CAR T cell solid tumour 2023 2024[pdat]"
        ],
        "databases": [
            ("TCGA","https://www.cancer.gov/tcga","Free","Somatic mutations + expression — 33 cancer types"),
            ("cBioPortal","https://www.cbioportal.org","Free/API","Cancer genomics — TCGA + ICGC cohorts visualised"),
            ("COSMIC","https://cancer.sanger.ac.uk/cosmic","Free/API","Catalogue of somatic mutations — curated"),
            ("OncoKB","https://www.oncokb.org","Free/API","Precision oncology — actionable variants + drug level evidence"),
            ("DepMap","https://depmap.org","Free","Cancer dependency map — CRISPR screens 900+ lines"),
            ("ClinVar","https://www.ncbi.nlm.nih.gov/clinvar","Free/API","Germline cancer susceptibility variants — BRCA1/2, Lynch"),
        ],
        "tools": [("cBioPortal","https://www.cbioportal.org"),("Oncotator","https://portals.broadinstitute.org/oncotator"),("MutSigCV","https://software.broadinstitute.org/cancer/cga/mutsig")],
        "key_facts": [
            "TP53 is mutated in >50% of all cancers — different hotspot mutations cause different gain-of-function phenotypes (not all TP53 mutations are equal)",
            "KRAS was 'undruggable' for 40 years. Sotorasib (AMG 510) targets KRAS G12C covalently — first direct KRAS inhibitor (FDA 2021). G12D and G12V still lack approved inhibitors",
            "Founder mutation principle: earliest somatic mutation in tumour evolution = primary therapeutic target. Late mutations are passengers",
            "BRCA1 frameshift and nonsense variants cause HBOC. Note: many VUS in BRCA1 — do not act on VUS without functional evidence",
            "Tumour mutational burden (TMB) ≥10 mut/Mb predicts pembrolizumab response (FDA approved as pan-tumour biomarker)",
            "MSI-H (mismatch repair deficient) tumours respond to checkpoint inhibitors regardless of tumour type",
            "CDK4/6 inhibitors (palbociclib, ribociclib) require Rb1 functional status — tumours with Rb1 loss are intrinsically resistant"
        ],
        "arrb_note": False
    },
    "proteins": {
        "label": "Proteins & Structural Biology",
        "icon": "🧬",
        "color": "#00e5ff",
        "tagline": "AlphaFold, AlphaMissense, PTMs, interaction networks, FBM-Filamin axis, drug targets",
        "gradient": "linear-gradient(135deg, #001a20 0%, #010306 100%)",
        "accent": "#00e5ff",
        "key_genes": ["FLNA","FLNC","TP53","BRCA1","EGFR","HSP90","MDM2","KRAS","VEGFA","AKT1","ARRB2","PKA","PKC","GRK2","GRK5"],
        "pubmed_qs": [
            "AlphaFold protein structure drug target 2023 2024[pdat]",
            "cryo-EM structure determination membrane protein 2023 2024[pdat]",
            "protein-protein interaction interface drug 2023 2024[pdat]",
            "Filamin GPCR signalling cytoskeleton 2023 2024[pdat]"
        ],
        "databases": [
            ("UniProt / Swiss-Prot","https://www.uniprot.org","Free/API","Gold-standard curated human proteins"),
            ("RCSB PDB","https://www.rcsb.org","Free","200K+ experimental structures — X-ray, cryo-EM, NMR"),
            ("AlphaFold DB","https://alphafold.ebi.ac.uk","Free/API","DeepMind structure predictions — all human proteins"),
            ("AlphaMissense","https://alphamissense.hegelab.org","Free/API","Per-residue pathogenicity predictions — DeepMind"),
            ("PhosphoSitePlus","https://www.phosphosite.org","Free","PTMs: phosphorylation, ubiquitination, acetylation — curated"),
            ("STRING DB","https://string-db.org","Free/API","Protein-protein interaction networks — 14K organisms"),
        ],
        "tools": [("Mol* Viewer","https://molstar.org"),("ChimeraX","https://www.cgl.ucsf.edu/chimerax"),("PyMOL","https://pymol.org"),("RoseTTAFold","https://robetta.bakerlab.org")],
        "key_facts": [
            "AlphaMissense (DeepMind 2023) scored all 216M possible missense variants in human proteome — score ≥0.564 = pathogenic prediction",
            "FLNA Ser2152 is the ONLY validated signal on Filamin A (PhosphoSite highest peak). All other FLNA phospho-sites are background kinase noise — no disease variant at those residues",
            "H8 helix dislodgement upon GPCR agonist binding → Filamin A Ig21 binding → PKA phosphorylates Ser2152. More receptor-proximal than cAMP, IP3, or beta-arrestin",
            "FBM anchors: Phe (hydrophobic, inward) — Arg (hydrophilic, outward) — Leu (hydrophobic, inward). Beta-strand augmentation geometry",
            "ARRB2 has zero confirmed Mendelian disease-causing variants. ARRB1/ARRB2 double KO mice are viable. Phosphorylation codes on ARRB proteins are kinase noise",
            "AlphaFold2 achieves <1Å backbone RMSD for most soluble proteins under 600 residues",
            "Discordant variants (ClinVar P/LP but AlphaMissense <0.564) act through non-structural mechanisms: splicing, interaction interfaces, regulatory domains"
        ],
        "arrb_note": True,
        "gpcr_protocol": True
    },
    "microbiome": {
        "label": "Microbiome",
        "icon": "🦠",
        "color": "#00c896",
        "tagline": "Host-microbiome interactions, dysbiosis, metabolites, therapeutic targets, 16S metagenomics",
        "gradient": "linear-gradient(135deg, #001a10 0%, #010306 100%)",
        "accent": "#00c896",
        "key_genes": ["FXR","TLR4","NLRP3","AhR","IL18","GPR41","GPR43","TGR5","MUC2","FFAR2","TMAO","PCSK9","FMO3"],
        "pubmed_qs": [
            "gut microbiome disease mechanism 2023 2024[pdat]",
            "microbiome metabolite TMAO cardiovascular 2023 2024[pdat]",
            "fecal microbiota transplant clinical trial 2023 2024[pdat]",
            "gut-brain axis neurotransmitter serotonin 2023 2024[pdat]"
        ],
        "databases": [
            ("Human Microbiome Project","https://hmpdacc.org","Free","Reference body-site microbiome data — HMP1+HMP2"),
            ("MGnify (EBI)","https://www.ebi.ac.uk/metagenomics","Free/API","Metagenome analysis pipeline + public studies"),
            ("SILVA rRNA","https://www.arb-silva.de","Free","16S/18S/23S rRNA taxonomy reference"),
            ("gutMDisorder","http://bio-annotation.cn/gutMDisorder","Free","Gut microbiome–disease associations curated"),
            ("MicrobiomeDB","https://microbiomedb.org","Free","Integrated microbiome study data"),
            ("NCBI SRA","https://www.ncbi.nlm.nih.gov/sra","Free","Raw 16S + shotgun sequencing data"),
        ],
        "tools": [("QIIME2","https://qiime2.org"),("MetaPhlAn4","https://github.com/biobakery/MetaPhlAn"),("Kraken2","https://ccb.jhu.edu/software/kraken2"),("HUMAnN3","https://huttenhower.sph.harvard.edu/humann")],
        "key_facts": [
            "TMAO (trimethylamine N-oxide): gut bacteria convert dietary choline/carnitine → TMA via TMA lyases → FMO3 in liver oxidises to TMAO → promotes atherosclerosis and cardiac arrhythmia",
            "TMAO causes GPCR rattling: rapid conformational transitions disrupting H8-Filamin A coupling — mechanistic link to arrhythmia beyond the classical foam cell pathway",
            "Akkermansia muciniphila abundance inversely correlates with obesity, T2D, and metabolic syndrome — promotes mucus layer integrity and GLP-1 secretion",
            "SCFAs (butyrate, propionate, acetate): produced by Firmicutes fermenting fibre → activate GPR41/GPR43 on colonocytes → regulate inflammation, energy balance",
            "Clostridioides difficile: toxins TcdA (NECTIN3 receptor) and TcdB (FZD1/FZD2 receptor) — bezlotoxumab (anti-TcdB mAb) FDA approved 2016",
            "Gut-brain axis: 90% of serotonin is produced in the gut (enterochromaffin cells). Gut dysbiosis alters serotonin signalling relevant to mood and IBS",
            "FMT (fecal microbiota transplant): >90% efficacy for recurrent C. difficile. RBX2660 (FDA approved 2023 — first FDA-approved FMT product)"
        ],
        "arrb_note": False
    }
}

GPCR_PROTOCOL = [
    ("Step 1","Confirm surface expression","Transfect SNAP/CLIP-tagged receptor into HEK293T. SNAP-Surface stain + confocal — confirm plasma membrane localisation before any signalling assay.","#00e5ff",True),
    ("Step 2","G-protein coupling — cAMP HTRF","Gs: cAMP HTRF (Cisbio). Gi: GTPγS or cAMP inhibition after forskolin. Primary efficacy readout. Test WT vs each ClinVar P/LP variant at matched expression.","#00c896",True),
    ("Step 3","Filamin A Ser2152-P (PRIMARY — receptor-proximal)","Stimulate → lyse → anti-Filamin A IP → pSer2152 western. H8 dislodgement is the mechanistic signature. More proximal than cAMP (2–4 steps via ryanodine receptors), IP3, or beta-arrestin. PhosphoSite confirms Ser2152 as the only non-noise FLNA peak. This is IP-protected.","#a855f7",True),
    ("Step 4","β-arrestin BRET (SECONDARY — biased agonism only)","RLuc8-receptor + Venus-β-arrestin2. Use ONLY for biased agonism characterisation. ARRB2 has no Mendelian disease variants — do not use as primary disease readout or drug target validation. Beta-arrestin codes are kinase noise.","#ff8c42",False),
    ("Step 5","Receptor internalisation","SNAP-surface before/after agonist. % receptor lost = internalisation rate. Variants in TM bundle or ECLs may alter trafficking independently of G-protein coupling.","#ffd60a",False),
    ("Step 6","Variant functional panel","For each ClinVar P/LP variant: run Steps 2+3 simultaneously. Variant kills cAMP but not Filamin-P = G-protein defect. Kills Filamin-P but not cAMP = cytoskeletal decoupling. Different biology → different drug target.","#ff2d55",False),
    ("Step 7","TMAO rattling assay (cardiac GPCRs only)","Add TMAO (5–50µM). Measure conformational dynamics by FlAsH-BRET or NanoBRET sensor. TMAO increases conformational sampling → reduces Filamin-P → arrhythmia mechanism.","#ff2d55",False),
]

# ═══════════════════════════════════════════════════════════════════════════════
#  SPLASH SCREEN
# ═══════════════════════════════════════════════════════════════════════════════
def render_splash():
    st.markdown("""
    <div style='min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:3rem 1rem;'>

    <div style='animation:fadeUp .8s ease both;text-align:center;margin-bottom:2rem'>
      <div style='font-size:3rem;font-weight:700;color:#00e5ff;letter-spacing:-.03em;
                  font-family:Space Grotesk,sans-serif;line-height:1'>Protellect</div>
      <div style='font-size:.95rem;color:#3a6080;margin-top:.4rem;letter-spacing:.08em;
                  text-transform:uppercase;font-weight:500'>Biology Intelligence Platform</div>
      <div style='width:60px;height:2px;background:linear-gradient(90deg,transparent,#00e5ff,transparent);
                  margin:1rem auto;animation:pulse 2s infinite'></div>
      <div style='font-size:.85rem;color:#2a4050;max-width:460px;line-height:1.7'>
        Genetics-first. Real-time data. AlphaFold + AlphaMissense + ClinVar triage.<br>
        Select a domain to begin.
      </div>
    </div>

    </div>
    """, unsafe_allow_html=True)

    # Domain cards
    cols = st.columns(4, gap="medium")
    domain_order = ["neuro","onco","proteins","microbiome"]
    for i, (col, key) in enumerate(zip(cols, domain_order)):
        D = DOMAINS[key]
        with col:
            st.markdown(
                f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:16px;"
                f"padding:1.8rem 1.2rem;text-align:center;cursor:pointer;"
                f"animation:fadeUp {.8+i*.15}s ease both;"
                f"transition:border-color .2s;margin-bottom:.5rem'>"
                f"<div style='font-size:2.5rem;margin-bottom:.6rem'>{D['icon']}</div>"
                f"<div style='color:{D['color']};font-weight:700;font-size:.95rem;margin-bottom:.3rem'>{D['label']}</div>"
                f"<div style='color:#2a4050;font-size:.76rem;line-height:1.5'>{D['tagline']}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
            if st.button(f"Open {D['icon']}", key=f"splash_{key}", use_container_width=True):
                st.session_state.domain = key
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
#  GENE ANALYSIS PANEL — full data integration
# ═══════════════════════════════════════════════════════════════════════════════
def render_gene_analysis(gene: str, domain_key: str):
    D = DOMAINS[domain_key]
    color = D["color"]
    gene = gene.upper().strip()

    sh("🔎", f"Live Analysis — {gene}", color)

    # Fetch all data in parallel (Streamlit runs top to bottom but caching helps)
    with st.spinner("Fetching UniProt, ClinVar, STRING, OpenTargets, AlphaFold..."):
        pdata   = api_uniprot(gene)
        cv      = api_clinvar(gene)
        partners= api_string(gene)
        ot      = api_opentargets(gene)
        gnomad  = api_gnomad(gene)
        af      = api_alphafold(pdata.get("uid","")) if pdata.get("uid") else {}

    # Non-human guard
    if pdata and not pdata.get("human", True):
        warn_box("⛔ Non-human protein rejected",
                 f"{gene} is not a human protein (taxon: {pdata.get('organism','?')}). "
                 "Protellect only analyses human proteins (taxonId 9606). "
                 "Search the correct human gene symbol.")
        return

    # ARRB guard
    is_arrb = gene in ("ARRB1","ARRB2","BARR1","BARR2")
    if is_arrb:
        st.markdown(
            f"<div style='background:#0a0205;border:2px solid #ff2d55;border-radius:14px;"
            f"padding:1.2rem 1.5rem;margin:.8rem 0'>"
            f"<div style='color:#ff2d55;font-weight:700;font-size:1.1rem;margin-bottom:.3rem'>"
            f"⛔ DEPRIORITISE — {gene}: No independent disease variants. $4,050,000 in avoidable spend.</div>"
            f"<div style='color:#6a3040;font-size:.84rem;line-height:1.7'>"
            f"ARRB1/ARRB2 double knockout mice are viable and fertile — these proteins are functionally redundant. "
            f"ClinVar shows {len(cv)} variants but none constitute independent Mendelian disease causation. "
            f"β-arrestin phosphorylation codes are background kinase noise — EGFR and other activated kinases "
            f"non-specifically phosphorylate thousands of substrates. A phospho site is only a signal if its mutation causes disease. "
            f"None of the ARRB2 phospho sites meet this criterion.<br><br>"
            f"<b style='color:#8a4050'>Redirect to:</b> Filamin A Ser2152-P assay ($2K) · ADRB1 · ADRB2 · AGTR1 · MAS1</div>"
            f"<div style='display:flex;gap:6px;flex-wrap:wrap;margin-top:.8rem'>"
            + "".join(f"<div style='background:#ff2d5511;border:1px solid #ff2d5533;border-radius:8px;padding:4px 12px;font-size:.75rem;color:#ff8c42;font-weight:600'>${v:,} — {k}</div>"
                      for k, v in [("HTS screen 1M compounds",2500000),("CRISPR knock-in x6",150000),("Cryo-EM structure",500000),("Mouse studies x2",800000),("BRET screens x4",100000)])
            + f"</div></div>",
            unsafe_allow_html=True
        )

    # Genomic integrity
    gi = gi_score(cv, pdata.get("length", 500) if pdata else 500)

    col_v, col_m = st.columns([3, 1])
    with col_v:
        st.markdown(
            f"<div style='background:{gi['color']}12;border:1px solid {gi['color']}44;border-radius:12px;"
            f"padding:1rem 1.2rem'>"
            f"<div style='color:{gi['color']};font-weight:700;font-size:1rem'>{gi['icon']} {gi['verdict']}</div>"
            f"<div style='color:#5a8090;font-size:.82rem;margin-top:3px'>{gi['explanation']}</div>"
            f"<div style='display:flex;gap:14px;margin-top:.6rem'>"
            f"<span style='font-size:.8rem;color:#3a6080'>P/LP variants: <b style='color:{gi['color']}'>{gi['n']}</b></span>"
            f"<span style='font-size:.8rem;color:#3a6080'>Per 100 aa: <b style='color:{gi['color']}'>{gi['per100']}</b></span>"
            f"<span style='font-size:.8rem;color:#3a6080'>pLI: <b style='color:{gi['color']}'>{gnomad.get('pLI','—')}</b></span>"
            f"</div></div>",
            unsafe_allow_html=True
        )
    with col_m:
        if pdata.get("uid"):
            st.markdown(
                f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:10px;padding:.7rem;text-align:center'>"
                f"<div style='color:#3a6080;font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.05em'>UniProt</div>"
                f"<a href='https://www.uniprot.org/uniprotkb/" + pdata.get('uid','') + "' target='_blank' style='color:#00e5ff;font-size:.85rem;font-weight:600'>" + pdata.get('uid','') + "</a><br>"
                + ("<a href='" + af.get('af_url','') + "' target='_blank' style='color:#a855f7;font-size:.76rem'>AlphaFold ↗</a>" if af.get('af_url') else "")
                + f"</div>",
                unsafe_allow_html=True
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Main analysis tabs
    t_over, t_var, t_lit, t_drugs, t_exp = st.tabs(
        ["🧬 Protein","🔬 Variants","📚 Literature","💊 Drugs","🧪 Experiments"]
    )

    with t_over:
        c1, c2 = st.columns(2)
        with c1:
            if pdata.get("name"):
                card_html(
                    f"<div style='color:{color};font-weight:600;font-size:.95rem;margin-bottom:.4rem'>{pdata['name']}</div>"
                    f"<div style='color:#5a8090;font-size:.8rem'>{gene} · {pdata.get('length',0)} aa · {pdata.get('organism','Human')}</div>"
                    + (f"<div style='color:#3a6080;font-size:.8rem;margin-top:.5rem;line-height:1.6'>{pdata.get('function','')[:350]}{'...' if len(pdata.get('function',''))>350 else ''}</div>" if pdata.get('function') else "")
                )
            if pdata.get("diseases"):
                sh("🩺","Disease Associations (UniProt)", color)
                for d in pdata["diseases"][:4]:
                    st.markdown(
                        f"<div style='padding:5px 0;border-bottom:1px solid #0d2545;font-size:.82rem'>"
                        f"<span style='color:#d0e8ff'>{d['name']}</span>"
                        f"<div style='color:#3a5060;font-size:.76rem;margin-top:1px'>{d.get('desc','')[:150]}</div>"
                        f"</div>", unsafe_allow_html=True
                    )
        with c2:
            if partners:
                sh("🕸️","Interaction Partners (STRING ≥700)", color)
                for p in partners:
                    st.markdown(
                        f"<div style='display:flex;justify-content:space-between;padding:4px 0;"
                        f"border-bottom:1px solid #0d2545;font-size:.82rem'>"
                        f"<span style='color:#d0e8ff'>{p['partner']}</span>"
                        f"<span style='color:#00c896;font-size:.78rem'>Score {p['score']}</span>"
                        f"</div>", unsafe_allow_html=True
                    )
            if gnomad:
                sh("📊","Constraint (gnomAD)", color)
                cc = st.columns(3)
                with cc[0]: st.metric("pLI", gnomad.get("pLI","—"))
                with cc[1]: st.metric("o/e LoF", gnomad.get("oe_lof","—"))
                with cc[2]: st.metric("o/e Mis", gnomad.get("oe_mis","—"))

            if ot.get("disease_assoc"):
                sh("🎯","Top Disease Associations (OpenTargets)", color)
                for da in ot["disease_assoc"][:4]:
                    st.markdown(
                        f"<div style='display:flex;justify-content:space-between;padding:4px 0;"
                        f"border-bottom:1px solid #0d2545;font-size:.82rem'>"
                        f"<span style='color:#d0e8ff'>{da['name']}</span>"
                        f"<span style='color:#ff8c42;font-size:.78rem'>Score {da['score']}</span>"
                        f"</div>", unsafe_allow_html=True
                    )

    with t_var:
        if is_arrb:
            warn_box("Disease triage suppressed",
                     f"ClinVar entries for {gene} reflect co-occurrence with GPCR-driven diseases, not independent pathogenicity. ARRB1/ARRB2 knockouts are viable. Do not use these variants as drug target evidence.")
        elif not cv:
            st.info("No pathogenic/likely-pathogenic variants found in ClinVar for this gene.")
        else:
            sh("🔴","ClinVar — Pathogenic / Likely Pathogenic Variants", color)
            st.markdown(
                f"<div style='color:#5a8090;font-size:.8rem;margin-bottom:.6rem'>"
                f"ClinVar is the triage filter — not the truth source. "
                f"Multi-star reviewed P/LP variants (scored ≥5) are the starting point. "
                f"Superimpose these onto drug structures or assay data to validate target engagement.</div>",
                unsafe_allow_html=True
            )
            for v in cv[:12]:
                rank_colors = {"CRITICAL":"#ff2d55","HIGH":"#ff8c42","MODERATE":"#ffd60a","LOW":"#5a8090"}
                rc = rank_colors.get(v["ml_rank"],"#3a5a7a")
                with st.expander(f"{badge(v['ml_rank'],rc)} {v['title'][:70]}...", expanded=False):
                    st.markdown(
                        f"{badge(v['cs'],'#4a90d9')} "
                        f"{'⭐'*v['stars'] if v['stars'] else '☆ No review'} "
                        f"<a href='{v['url']}' target='_blank' style='font-size:.75rem'>ClinVar ↗</a>",
                        unsafe_allow_html=True
                    )
                    if v.get("condition"):
                        st.markdown(f"<div style='color:#5a8090;font-size:.8rem;margin-top:3px'>Condition: {v['condition'][:150]}</div>", unsafe_allow_html=True)

    with t_lit:
        sh("📄","Live Literature — PubMed 2022–2025", color)
        lit_q = f"{gene}[gene] 2022:2025[pdat]"
        with st.spinner("Fetching papers..."):
            papers = api_pubmed(lit_q, 10)

        if not papers:
            st.info("No recent papers found.")
        else:
            for p in papers:
                tc = TIER_MAP.get(p["tier"],{}).get("color","#3a5a7a")
                wk = detect_study_weaknesses(p["title"])
                exp_label = f"{tier_badge(p['tier'])} &nbsp; {p['title'][:75]}{'...' if len(p['title'])>75 else ''}"
                with st.expander(exp_label, expanded=False):
                    st.markdown(
                        f"<div style='font-size:.8rem;color:#5a8090;margin-bottom:.3rem'>"
                        f"{p['authors']} · <i>{p['journal']}</i> · {p['year']}</div>",
                        unsafe_allow_html=True
                    )
                    _doi_url = f"https://doi.org/{p.get('doi','')}" if p.get('doi') else ''
                    _pm_url = p.get('url','')
                    _pm_id = p.get('pmid','')
                    _doi = p.get('doi','')
                    if _doi:
                        st.markdown(f"<a href='https://doi.org/{_doi}' target='_blank' style='font-size:.75rem'>DOI ↗</a> &nbsp; <a href='{_pm_url}' target='_blank' style='font-size:.75rem'>PubMed {_pm_id} ↗</a>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<a href='{_pm_url}' target='_blank' style='font-size:.75rem'>PubMed {_pm_id} ↗</a>", unsafe_allow_html=True)
                    if wk:
                        for w_title, w_body in wk:
                            warn_box(w_title, w_body)
                    

    with t_drugs:
        if ot.get("drugs"):
            sh("💊","Known Drugs (OpenTargets + DGIdb)", color)
            phase_colors = {4:"#00c896",3:"#4a90d9",2:"#ffd60a",1:"#5a8090",0:"#3a4050"}
            for drug in ot["drugs"]:
                pc = phase_colors.get(int(drug.get("phase",0) or 0),"#3a4050")
                phase_label = {4:"Approved",3:"Phase 3",2:"Phase 2",1:"Phase 1",0:"Preclinical"}.get(int(drug.get("phase",0) or 0),"Unknown")
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;align-items:center;"
                    f"padding:6px 0;border-bottom:1px solid #0d2545;font-size:.83rem'>"
                    f"<span style='color:#d0e8ff'>{drug['name']}</span>"
                    f"<span style='background:{pc}22;color:{pc};padding:2px 8px;border-radius:6px;font-size:.74rem'>{phase_label}</span>"
                    f"</div>", unsafe_allow_html=True
                )
        if ot.get("tractability"):
            sh("🎯","Tractability (OpenTargets)", color)
            st.markdown(" ".join(badge(t,"#00c896") for t in ot["tractability"]), unsafe_allow_html=True)
        if not ot.get("drugs") and not ot.get("tractability"):
            st.info("No drug data found in OpenTargets. May be an early-stage target.")

    with t_exp:
        sh("🧪","Protein-Specific Experiment Recommendations", color)
        _render_experiments(gene, pdata, cv, gnomad, ot, partners, is_arrb, color, domain_key)

def _render_experiments(gene, pdata, cv, gnomad, ot, partners, is_arrb, color, domain_key):
    """Generate protein-specific experiments using real fetched data."""
    if is_arrb:
        warn_box("Experiments suppressed for ARRB proteins",
                 "All standard GPCR/signalling experiments for ARRB1/ARRB2 will produce non-translatable results "
                 "because these proteins have no confirmed Mendelian disease variants. See Summary for cost analysis and alternatives.")
        return

    n_cv     = len(cv)
    pli      = gnomad.get("pLI", 0)
    n_crit   = sum(1 for v in cv if v.get("ml_rank") == "CRITICAL")
    n_lof    = sum(1 for v in cv if any(k in v.get("title","").lower() for k in ["frameshift","nonsense","stopgain","del"]))
    n_miss   = sum(1 for v in cv if "p." in v.get("title","").lower() and "del" not in v.get("title","").lower())
    top_cv   = cv[0].get("title","")[:40] if cv else "top pathogenic variant"
    top_part = partners[0]["partner"] if partners else "key interaction partner"
    is_sm    = any("small" in t.lower() for t in ot.get("tractability",[]))
    is_gpcr  = domain_key == "proteins" and any(x in gene for x in ["ADRB","AGTR","MAS","CHRM","ADRA"])
    is_card  = domain_key in ("proteins","neuro") and any(x in gene for x in ["ADRB","AGTR","KCNQ","SCN","FLNA","FLNC"])
    is_kin   = any(x in gene for x in ["GRK","CDK","BRAF","EGFR","ALK","FGFR","MET","RET"])

    exps = []

    # Computational — always first
    exps.append({
        "icon":"💻","name":f"Rosetta ΔΔG — all {n_miss} missense variants ranked",
        "cost":"Free","time":"1–3 days","p":0.92,"value":8,"do_first":True,
        "rationale":(
            f"Zero-cost pre-screen for all {n_miss} missense variants in {gene}. "
            f"Variants with ΔΔG ≥2 REU = structurally destabilising → pharmacochaperone or TSA screen next. "
            f"Variants with ΔΔG <1 REU but ClinVar P/LP = functional mechanism → Co-IP with {top_part} next. "
            f"Eliminates ~50% of candidates before any wet-lab spend. "
            f"Cross-reference with AlphaMissense (DeepMind) — concordant variants (ClinVar P/LP AND AlphaMissense ≥0.564) are highest priority."
        )
    })

    # Variant-type specific first wet-lab experiment
    if n_lof > n_miss:
        exps.append({
            "icon":"🧫","name":f"Western blot — protein abundance in {n_lof} LoF variant carriers",
            "cost":"$500","time":"1 wk","p":0.90,"value":9,"do_first":True,
            "rationale":(
                f"{gene} has {n_lof} frameshift/stop-gain variants ({n_lof} of {n_cv} pathogenic). "
                f"LoF-dominant profile: western blot (anti-{gene} antibody, HPA validated) on patient-derived or CRISPR cells. "
                f"pLI={pli} — {'high essentiality, expect absent or reduced band' if pli>0.8 else 'moderate essentiality'}. "
                f"Absent band = NMD/proteasomal degradation → supplementation therapy. "
                f"Present truncated band = NMD-escape/dominant-negative → different strategy."
            )
        })
    elif n_miss > 0:
        exps.append({
            "icon":"🌡️","name":f"Thermal shift assay (TSA/DSF) — {min(n_crit+3,8)} missense variants vs WT",
            "cost":"$2,000","time":"2 wks","p":0.85,"value":9,"do_first":True,
            "rationale":(
                f"{gene} is missense-dominant ({n_miss} missense P/LP variants). "
                f"TSA: purify WT and top variants (including {top_cv}), measure Tm by DSF (SYPRO Orange). "
                f"ΔTm ≥2°C = structurally destabilising → pharmacochaperone screen (Prestwick library, $2K). "
                f"ΔTm <1°C but ClinVar P/LP = functional mechanism → Co-IP next. "
                f"AlphaMissense concordance strengthens the structural interpretation."
            )
        })

    # Protein class specific
    if is_gpcr:
        exps.append({
            "icon":"📡","name":f"Filamin A Ser2152-P western — agonist-stimulated {gene} activation",
            "cost":"$2,000","time":"1 wk","p":0.90,"value":10,"do_first":True,
            "rationale":(
                f"Confirmed FBM-containing GPCR: H8 helix dislodgement upon agonist → Filamin Ig21 binding → PKA phosphorylates Ser2152. "
                f"This is MORE RECEPTOR-PROXIMAL than cAMP, IP3, or beta-arrestin. "
                f"Stimulate {gene}-expressing cells → anti-Filamin A IP → pSer2152 western blot (anti-pS2152 antibody). "
                f"Pathogenic variant in H8 or ICL3: expect REDUCED Ser2152-P vs WT despite normal cAMP. "
                f"PhosphoSite confirms Ser2152 as the only non-noise FLNA peak. "
                f"Source: Nakamura et al. JBC 2015."
            )
        })

    if is_kin:
        exps.append({
            "icon":"⚗️","name":f"ADP-Glo kinase assay — {top_cv[:30]} vs WT",
            "cost":"$5,000","time":"3 wks","p":0.85,"value":9,"do_first":False,
            "rationale":(
                f"{gene} is a protein kinase. ADP-Glo measures ATP consumption directly — the most specific kinase activity readout. "
                f"Test {top_cv} vs WT at matched protein concentration (confirmed by western). "
                f"Activity reduced ≥70%: LoF confirmed → substrate accumulation is the disease mechanism. "
                f"Activity unchanged: allosteric or scaffolding mechanism → test interaction with {top_part} next. "
                f"Follow with KINOMEscan (468-kinase panel, $50K) before any HTS to confirm selectivity."
            )
        })

    # CRISPR — conditional
    crispr_justified = n_crit >= 2
    exps.append({
        "icon":"✂️","name":f"CRISPR knock-in — {top_cv[:35]}",
        "cost":"$25,000","time":"8 wks",
        "p":0.80 if crispr_justified else 0.40,
        "value":10 if crispr_justified else 4,
        "do_first":False,
        "rationale":(
            f"{'JUSTIFIED: ' + str(n_crit) + ' CRITICAL variants with multi-star ClinVar review.' if crispr_justified else 'PREMATURE: run TSA and western blot first to confirm mechanism before $25K spend.'} "
            f"Introduce {top_cv} via HDR in {gene} locus. Screen ≥50 clones by Sanger + western. "
            f"Isogenic comparison eliminates confounders from genetic background. "
            f"Phenotypic readout: {'Filamin Ser2152-P after agonist' if is_gpcr else 'kinase activity assay' if is_kin else 'disease-relevant functional assay'}. "
            f"Positive result = ClinGen PS3 functional evidence → supports ClinVar P/LP reclassification."
        )
    })

    # Co-IP
    if top_part:
        exps.append({
            "icon":"🔗","name":f"Co-IP / AP-MS — {gene}:{top_part} interaction in WT vs variant",
            "cost":"$15,000","time":"6 wks","p":0.75,"value":8,"do_first":False,
            "rationale":(
                f"STRING confidence for {gene}:{top_part} interaction is high. "
                f"Endogenously 3xFLAG-tag {gene} via CRISPR (preserves expression level). "
                f"Anti-FLAG IP × 3 biological replicates, TMT-LC-MS/MS. "
                f"Hypothesis: {top_cv} will show reduced interaction with {top_part}. "
                f"Gained interactions (stress chaperones, HSP70/HSP90) indicate dominant-negative behaviour. "
                f"SAINTexpress + CRAPome filtering for high-confidence interactions only."
            )
        })

    # Drug screen — only if tractable
    if is_sm or n_miss > 5:
        exps.append({
            "icon":"💊","name":f"Pharmacochaperone screen — Prestwick 1,280 approved drugs",
            "cost":"$3,000","time":"2 wks","p":0.65,"value":8,"do_first":False,
            "rationale":(
                f"{'OpenTargets confirms small molecule tractability. ' if is_sm else ''}"
                f"Screen Prestwick repurposing library (1,280 FDA-approved drugs) at 10µM by TSA. "
                f"Flag: ΔTm ≥1°C = chaperone hit. Dose-response (0.1–100µM) on top 20 hits. "
                f"Cellular rescue: add hit to CRISPR mutant cells — does viability/function restore? "
                f"This is the fastest path to a clinical candidate for missense-dominant proteins."
            )
        })

    # Render
    first  = [e for e in exps if e.get("do_first")]
    rest   = sorted([e for e in exps if not e.get("do_first")], key=lambda x: -x["value"])
    all_exp = first + rest

    for i, exp in enumerate(all_exp):
        label = f"{'🥇 DO FIRST — ' if exp.get('do_first') else f'#{i+1} — '}{exp['name']}  ·  {exp['cost']}  ·  ⏱ {exp['time']}"
        border = "#00c896" if exp.get("do_first") else "#0d2545"
        with st.expander(label, expanded=(i < 2)):
            c_l, c_r = st.columns([4, 1])
            with c_l:
                st.markdown(
                    f"<div style='background:#020810;border-left:3px solid {border};"
                    f"padding:.8rem 1rem;border-radius:0 8px 8px 0'>"
                    f"<div style='color:#7ab0c0;font-size:.85rem;line-height:1.7'>{exp['rationale']}</div>"
                    f"</div>", unsafe_allow_html=True
                )
            with c_r:
                st.markdown(
                    f"<div style='background:#030810;border:1px solid #0d2545;border-radius:10px;"
                    f"padding:.7rem;text-align:center'>"
                    f"<div style='color:#3a6080;font-size:.68rem;font-weight:600;text-transform:uppercase'>P(success)</div>"
                    f"<div style='color:#ffd60a;font-size:1.3rem;font-weight:700'>{int(exp['p']*100)}%</div>"
                    f"<div style='color:#3a6080;font-size:.68rem;margin-top:4px'>Value</div>"
                    f"<div style='color:#00c896;font-size:1rem;font-weight:600'>{exp['value']}/10</div>"
                    f"</div>", unsafe_allow_html=True
                )

# ═══════════════════════════════════════════════════════════════════════════════
#  DOMAIN MAIN PAGE
# ═══════════════════════════════════════════════════════════════════════════════
def render_domain(domain_key: str):
    D = DOMAINS[domain_key]
    color = D["color"]

    # Top bar
    c_logo, c_back = st.columns([6, 1])
    with c_logo:
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:12px;padding:1.2rem 1.5rem .5rem'>"
            f"<span style='font-size:1.8rem'>{D['icon']}</span>"
            f"<div><div style='color:{color};font-weight:700;font-size:1.2rem;letter-spacing:-.02em'>{D['label']}</div>"
            f"<div style='color:#2a4050;font-size:.78rem'>{D['tagline']}</div></div>"
            f"</div>", unsafe_allow_html=True
        )
    with c_back:
        st.markdown("<div style='padding:1.2rem .5rem 0'>", unsafe_allow_html=True)
        if st.button("← Domains"):
            st.session_state.domain = None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#0d2545;margin:0'>", unsafe_allow_html=True)

    # Sidebar-style search
    with st.sidebar:
        st.markdown(
            f"<div style='color:{color};font-weight:700;font-size:1rem;padding:.5rem 0'>"
            f"🔬 Protellect</div>"
            f"<div style='color:#3a6080;font-size:.75rem;margin-bottom:.8rem'>Biology Intelligence</div>",
            unsafe_allow_html=True
        )
        st.markdown(f"**{D['icon']} {D['label']}**")
        gene_q = st.text_input("Gene / protein", placeholder="e.g. FLNC, EGFR, LRRK2", key="gene_input")
        do_search = st.button("🔍 Analyse", use_container_width=True)

        st.markdown("---")
        st.markdown("<div style='color:#3a6080;font-size:.72rem;font-weight:600;letter-spacing:.05em;text-transform:uppercase'>Key Genes</div>", unsafe_allow_html=True)
        for gene_chip in D["key_genes"][:10]:
            if st.button(gene_chip, key=f"chip_{gene_chip}", use_container_width=True):
                st.session_state["gene_input"] = gene_chip
                st.session_state["run_gene"] = gene_chip
                st.rerun()

        st.markdown("---")
        st.markdown("<div style='color:#3a6080;font-size:.72rem;font-weight:600;letter-spacing:.05em;text-transform:uppercase;margin-bottom:.4rem'>Quick Links</div>", unsafe_allow_html=True)
        for db_name, db_url, _, _ in D["databases"][:4]:
            st.markdown(f"<a href='{db_url}' target='_blank' style='display:block;font-size:.78rem;color:{color};padding:3px 0;border-bottom:1px solid #0d2545'>{db_name} ↗</a>", unsafe_allow_html=True)

    # Check if gene analysis triggered
    run_gene = st.session_state.pop("run_gene", None)
    if do_search and gene_q.strip():
        run_gene = gene_q.strip()
    if run_gene:
        render_gene_analysis(run_gene, domain_key)
        st.markdown("<hr style='border-color:#0d2545'>", unsafe_allow_html=True)

    # Domain content tabs
    tab_overview, tab_db, tab_lit, tab_facts = st.tabs(
        ["Overview","Databases","Live Literature","Key Facts & Insights"]
    )

    with tab_overview:
        st.markdown("<div style='padding:1rem 1.5rem'>", unsafe_allow_html=True)
        c1, c2 = st.columns([3, 2])
        with c1:
            sh("🎯","Key Research Targets", color)
            chips_html = "".join(
                f"<span style='display:inline-block;background:#040c14;border:1px solid {color}44;"
                f"border-radius:8px;padding:.25rem .7rem;margin:3px;font-size:.78rem;color:{color};cursor:pointer'>{g}</span>"
                for g in D["key_genes"]
            )
            st.markdown(f"<div style='margin-bottom:.8rem'>{chips_html}</div>", unsafe_allow_html=True)

        with c2:
            sh("🔧","Analysis Tools", color)
            for t_name, t_url in D["tools"]:
                st.markdown(
                    f"<div style='padding:5px 0;border-bottom:1px solid #0d2545'>"
                    f"<a href='{t_url}' target='_blank' style='color:{color};font-size:.83rem'>{t_name} ↗</a>"
                    f"</div>", unsafe_allow_html=True
                )

        if D.get("arrb_note"):
            st.markdown("---")
            st.markdown(
                f"<div style='background:#0a0205;border:1px solid #ff2d5544;border-radius:12px;padding:1rem 1.2rem'>"
                f"<div style='color:#ff2d55;font-weight:600;font-size:.85rem;margin-bottom:.3rem'>⚠️ ARRB1/ARRB2 — deprioritise</div>"
                f"<div style='color:#5a3040;font-size:.8rem;line-height:1.6'>"
                f"Beta-arrestin proteins have zero confirmed Mendelian disease-causing variants. "
                f"ARRB1/ARRB2 double KO mice are viable. Phosphorylation codes on PhosphoSite are kinase noise. "
                f"Use Filamin A Ser2152-P as the receptor-proximal GPCR readout instead. "
                f"Estimated avoidable spend if pursuing ARRB2: $4,050,000."
                f"</div></div>", unsafe_allow_html=True
            )

        if D.get("gpcr_protocol"):
            st.markdown("---")
            sh("📡","GPCR Study Protocol (7-step)", "#00e5ff")
            st.markdown("<div style='color:#3a6080;font-size:.8rem;margin-bottom:.6rem'>Step 3 is the primary receptor-proximal readout. Step 4 is secondary only. GPCRdb (gpcrdb.org) shows H8 FBM conservation across all Class A GPCRs.</div>", unsafe_allow_html=True)
            for step, title, body, clr, primary in GPCR_PROTOCOL:
                with st.expander(f"{step} — {title}{' ⭐ PRIMARY' if primary and step=='Step 3' else ' (secondary)' if step=='Step 4' else ''}", expanded=(step in ("Step 1","Step 2","Step 3"))):
                    st.markdown(
                        f"<div style='background:#020810;border-left:3px solid {clr};"
                        f"padding:.7rem 1rem;border-radius:0 8px 8px 0;color:#7ab0c0;font-size:.84rem;line-height:1.7'>"
                        f"{body}</div>", unsafe_allow_html=True
                    )
            st.markdown(" ".join([
                src_link("GPCRdb", "https://gpcrdb.org"),
                src_link("PhosphoSite FLNA", "https://www.phosphosite.org/proteinAction.action?id=2546"),
                src_link("Nakamura 2015", "https://doi.org/10.1074/jbc.M115.671826"),
            ]), unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    with tab_db:
        st.markdown("<div style='padding:1rem 1.5rem'>", unsafe_allow_html=True)
        sh("🗄️","Databases for this Domain", color)
        for db_name, db_url, db_tag, db_desc in D["databases"]:
            tc = "#00c896" if "Free" in db_tag else "#ffd60a" if "API" in db_tag else "#5a8090"
            st.markdown(
                f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:10px;"
                f"padding:.75rem 1rem;margin-bottom:.3rem;display:flex;align-items:center;justify-content:space-between'>"
                f"<div style='flex:1'>"
                f"<a href='{db_url}' target='_blank' style='color:#d0e8ff;font-weight:500;font-size:.88rem'>{db_name}</a>"
                f"<div style='color:#2a4050;font-size:.75rem;margin-top:1px'>{db_desc}</div>"
                f"</div>"
                f"<span style='background:{tc}18;color:{tc};font-size:.7rem;padding:2px 8px;border-radius:6px;border:1px solid {tc}44;margin-left:10px;white-space:nowrap'>{db_tag}</span>"
                f"</div>", unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_lit:
        st.markdown("<div style='padding:1rem 1.5rem'>", unsafe_allow_html=True)
        sh("📄","Live Literature — PubMed 2022–2025", color)
        selected_q = st.selectbox("Query", D["pubmed_qs"], key=f"lit_q_{domain_key}")
        if st.button("Fetch papers ↗", key=f"fetch_{domain_key}"):
            with st.spinner("Fetching from PubMed..."):
                papers = api_pubmed(selected_q, 10)
            if not papers:
                st.info("No papers found for this query.")
            else:
                for p in papers:
                    wk = detect_study_weaknesses(p["title"])
                    with st.expander(f"{tier_badge(p['tier'])} &nbsp; {p['title'][:80]}...", expanded=False):
                        st.markdown(
                            f"<div style='font-size:.8rem;color:#5a8090'>"
                            f"{p['authors']} · <i>{p['journal']}</i> · {p['year']}</div>",
                            unsafe_allow_html=True
                        )
                        st.markdown(f"<a href='{p['url']}' target='_blank' style='font-size:.75rem'>PubMed {p['pmid']} ↗</a>", unsafe_allow_html=True)
                        if wk:
                            for w_t, w_b in wk:
                                warn_box(w_t, w_b)
        else:
            st.info("Select a query and click Fetch.")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_facts:
        st.markdown("<div style='padding:1rem 1.5rem'>", unsafe_allow_html=True)
        sh("💡","Evidence-Based Key Facts", color)
        st.markdown(
            "<div style='color:#3a6080;font-size:.8rem;margin-bottom:.8rem'>"
            "Facts are grounded in published literature and genetic databases. "
            "Where evidence conflicts with common assumptions, the genetic evidence takes precedence over cell biology or in vitro data.</div>",
            unsafe_allow_html=True
        )
        for fact in D["key_facts"]:
            st.markdown(
                f"<div style='display:flex;gap:10px;padding:8px 0;border-bottom:1px solid #0d2545'>"
                f"<span style='color:{color};font-size:.9rem;margin-top:1px;flex-shrink:0'>→</span>"
                f"<span style='color:#8ab0c0;font-size:.83rem;line-height:1.6'>{fact}</span>"
                f"</div>", unsafe_allow_html=True
            )

        sh("🏗️","Evidence Tier Reference", color)
        for tier, meta in TIER_MAP.items():
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:10px;padding:4px 0;border-bottom:1px solid #0d2545'>"
                f"{badge(tier, meta['color'])}"
                f"<span style='color:#3a6080;font-size:.8rem'>Weight: {meta['weight']}/10</span>"
                f"</div>", unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # Footer
    st.markdown(
        f"<div style='color:#1e3a5a;font-size:.72rem;text-align:center;padding:2rem 0 1rem'>"
        f"Protellect · Biology Intelligence · Real-time: UniProt · ClinVar · gnomAD · STRING · OpenTargets · AlphaFold · PubMed · {datetime.now().year}</div>",
        unsafe_allow_html=True
    )

# ═══════════════════════════════════════════════════════════════════════════════
#  ROUTING
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.domain is None:
    render_splash()
else:
    render_domain(st.session_state.domain)
