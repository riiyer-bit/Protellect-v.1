from __future__ import annotations
# ═══════════════════════════════════════════════════════════════════
#  Protellect v4 — single-file, no local imports
#  Run: streamlit run app.py
# ═══════════════════════════════════════════════════════════════════

import re, time, json, math, io
from collections import Counter, defaultdict

import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# ─── Page config ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Protellect", page_icon="🧬",
    layout="wide", initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;}
.stApp{background:#04080f;}
[data-testid="stSidebar"]{background:#05101f!important;border-right:1px solid #0c2040;}
/* Header */
.ph{background:linear-gradient(135deg,#04080f,#050e20);border:1px solid #0c2040;border-radius:14px;
  padding:1rem 1.8rem .8rem;margin-bottom:.6rem;position:relative;overflow:hidden;}
.ph::after{content:'';position:absolute;bottom:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,#00e5ff44,transparent);}
.pt{font-size:1.9rem;font-weight:800;letter-spacing:-.5px;margin:0;
  background:linear-gradient(90deg,#00e5ff,#6478ff,#00e5ff);background-size:200%;
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  animation:sh 4s linear infinite;}
.ps{color:#1e4060;font-size:.82rem;margin:.2rem 0 0;}
@keyframes sh{0%{background-position:0%}100%{background-position:200%}}
/* Metric card */
.mc{background:linear-gradient(145deg,#06111e,#040d18);border:1px solid #0c2040;
  border-radius:12px;padding:.9rem 1rem;text-align:center;position:relative;overflow:hidden;
  transition:border-color .3s,transform .2s;}
.mc:hover{border-color:#00e5ff33;transform:translateY(-2px);}
.mc::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:var(--acc,linear-gradient(90deg,#00e5ff,#6478ff));}
.mv{font-size:1.7rem;font-weight:800;line-height:1;color:var(--clr,#00e5ff);}
.ml2{font-size:.68rem;color:#1e4060;margin-top:4px;text-transform:uppercase;letter-spacing:.7px;}
/* Content cards */
.card{background:#06111e;border:1px solid #0c2040;border-radius:12px;
  padding:1rem 1.3rem;margin-bottom:.7rem;transition:border-color .2s;}
.card:hover{border-color:#1a3a5f;}
.card h4{color:#00e5ff;font-size:.88rem;font-weight:700;margin:0 0 .4rem;}
.card p{color:#3a6080;font-size:.82rem;line-height:1.6;margin:0;}
/* Badges */
.badge{display:inline-block;padding:2px 9px;border-radius:16px;font-size:.67rem;font-weight:800;letter-spacing:.3px;}
.bC{background:rgba(255,45,85,.12);color:#ff2d55;border:1px solid #ff2d5540;}
.bH{background:rgba(255,140,66,.12);color:#ff8c42;border:1px solid #ff8c4240;}
.bM{background:rgba(255,214,10,.1);color:#ffd60a;border:1px solid #ffd60a35;}
.bN{background:rgba(58,90,122,.2);color:#3a6080;border:1px solid #1e404050;}
/* Tabs — sticky at top */
.stTabs{position:sticky;top:0;z-index:100;background:#04080f;padding-top:4px;}
.stTabs [data-baseweb="tab-list"]{background:#04080f!important;gap:3px;
  border-bottom:1px solid #0c2040;padding:0 4px;}
.stTabs [data-baseweb="tab"]{background:transparent;border-radius:8px 8px 0 0;
  padding:7px 16px;color:#1a3a5a!important;font-weight:600;font-size:.84rem;}
.stTabs [aria-selected="true"]{background:#06111e!important;color:#00e5ff!important;
  border-bottom:2px solid #00e5ff!important;}
/* Goal box */
.goal-box{background:linear-gradient(135deg,#04101e,#050d1a);border:1px solid #00e5ff22;
  border-radius:12px;padding:1rem 1.4rem;margin-bottom:1rem;}
.goal-box h4{color:#00e5ff;font-size:.88rem;font-weight:700;margin:0 0 .3rem;}
.goal-tag{display:inline-block;background:#040d18;border:1px solid #00e5ff33;color:#3a8090;
  padding:3px 10px;border-radius:12px;font-size:.76rem;margin:3px 3px 0 0;cursor:default;}
/* CSV upload box */
.csv-box{background:#040d18;border:1px dashed #0c3050;border-radius:10px;
  padding:.9rem;margin:.5rem 0;}
/* Divider */
.dv{border:none;border-top:1px solid #091830;margin:1.2rem 0;}
/* Section head */
.sh2{display:flex;align-items:center;gap:8px;margin:0 0 .8rem;
  padding-bottom:6px;border-bottom:1px solid #0c2040;}
.sh2 h3{color:#a0c8e8;font-size:.92rem;font-weight:700;margin:0;}
/* Cite */
.cite{border-left:2px solid #00e5ff22;padding:6px 10px;margin:3px 0;
  background:#040e1c;border-radius:0 8px 8px 0;}
.cite a{color:#2a80a4;text-decoration:none;font-size:.78rem;}
.cite a:hover{color:#00e5ff;}
.cm{color:#0e2840;font-size:.7rem;margin-top:1px;}
/* Table */
.pt2{width:100%;border-collapse:collapse;font-size:.8rem;}
.pt2 thead tr{background:#040d18;}
.pt2 th{color:#00e5ff;padding:8px 10px;text-align:left;font-size:.67rem;
  font-weight:700;text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid #0c2040;}
.pt2 td{padding:8px 10px;border-bottom:1px solid #060f1c;color:#4a7090;vertical-align:middle;}
.pt2 tr:hover td{background:#05101e;}
/* Sidebar */
.sb-t{font-size:.64rem;font-weight:700;color:#0e2840;text-transform:uppercase;
  letter-spacing:1px;margin:.8rem 0 .3rem;padding-bottom:3px;border-bottom:1px solid #0c2040;}
/* Sensitivity */
.sens-wrap{background:#040d18;border:1px solid #0c2040;border-radius:8px;padding:.8rem;}
/* Info */
.info-land{background:#040d18;border:1px solid #0c2040;border-radius:14px;
  padding:2rem;text-align:center;margin-top:.5rem;}
/* CSV result card */
.csv-card{background:#05101e;border:1px solid #0c3050;border-radius:10px;
  padding:.9rem 1.1rem;margin:.6rem 0;}
.csv-card h4{color:#4adaff;font-size:.86rem;font-weight:700;margin:0 0 .4rem;}
/* Stbutton */
.stButton>button{background:linear-gradient(135deg,#003d55,#002868)!important;
  color:#00e5ff!important;border:1px solid #00e5ff22!important;border-radius:8px!important;font-weight:700!important;}
.stButton>button:hover{border-color:#00e5ff55!important;box-shadow:0 4px 18px rgba(0,229,255,.15)!important;}
.stTextInput input,.stTextArea textarea,.stSelectbox div{
  background:#040d18!important;border:1px solid #0c2040!important;color:#c0d8f8!important;}
details{border:1px solid #0c2040!important;border-radius:10px!important;background:#050f1d!important;}
</style>
""", unsafe_allow_html=True)

# ─── Constants ────────────────────────────────────────────────────
SIG_SCORE = {
    "pathogenic":5,"likely pathogenic":4,"pathogenic/likely pathogenic":4,
    "risk factor":3,"uncertain significance":2,"conflicting interpretations":2,
    "likely benign":1,"benign":0,"benign/likely benign":0,"not provided":-1,
}
AA_HYDRO = {"A":1.8,"R":-4.5,"N":-3.5,"D":-3.5,"C":2.5,"Q":-3.5,"E":-3.5,"G":-0.4,
            "H":-3.2,"I":4.5,"L":3.8,"K":-3.9,"M":1.9,"F":2.8,"P":-1.6,"S":-0.8,
            "T":-0.7,"W":-0.9,"Y":-1.3,"V":4.2,"*":-10}
AA_CHG   = {"R":1,"K":1,"H":0.5,"D":-1,"E":-1}
AA_NAMES = {"A":"Alanine","R":"Arginine","N":"Asparagine","D":"Aspartate","C":"Cysteine",
            "Q":"Glutamine","E":"Glutamate","G":"Glycine","H":"Histidine","I":"Isoleucine",
            "L":"Leucine","K":"Lysine","M":"Methionine","F":"Phenylalanine","P":"Proline",
            "S":"Serine","T":"Threonine","W":"Tryptophan","Y":"Tyrosine","V":"Valine"}
RANK_CLR = {"CRITICAL":"#ff2d55","HIGH":"#ff8c42","MEDIUM":"#ffd60a","NEUTRAL":"#3a5a7a"}
RANK_CSS = {"CRITICAL":"bC","HIGH":"bH","MEDIUM":"bM","NEUTRAL":"bN"}
ESEARCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

GOAL_OPTIONS = [
    "🎯 Identify therapeutic targets",
    "🔬 Understand disease mechanism",
    "💊 Drug discovery & development",
    "📊 Biomarker identification",
    "🧬 Basic research / functional characterisation",
    "🧪 Experimental pathway prioritisation",
    "📋 Clinical variant interpretation",
    "✏️ Custom goal (type below)",
]

# ─── Helpers ─────────────────────────────────────────────────────
def badge(rank):
    css = RANK_CSS.get(rank, "bN")
    return f"<span class='badge {css}'>{rank}</span>"

def sh(icon, title):
    st.markdown(f"<div class='sh2'><span style='font-size:1.1rem'>{icon}</span><h3>{title}</h3></div>", unsafe_allow_html=True)

def mc(val, label, clr="#00e5ff", acc=None):
    a = acc or f"linear-gradient(90deg,{clr},{clr}88)"
    return f"<div class='mc' style='--clr:{clr};--acc:{a};'><div class='mv'>{val}</div><div class='ml2'>{label}</div></div>"

def score_rank(s, sensitivity=50):
    # Sensitivity shifts thresholds: higher = more sensitive (more variants flagged)
    shift = (sensitivity - 50) / 100.0  # -0.5 to +0.5
    if s >= 5: return "CRITICAL"
    if s >= 4 - shift: return "HIGH"
    if s >= 2 - shift: return "MEDIUM"
    return "NEUTRAL"

def ml_rank_fn(ml, sensitivity=50):
    shift = (sensitivity - 50) / 200.0  # -0.25 to +0.25
    if ml >= 0.85 - shift: return "CRITICAL"
    if ml >= 0.65 - shift: return "HIGH"
    if ml >= 0.40 - shift: return "MEDIUM"
    return "NEUTRAL"

def parse_aa(name):
    aa3 = {"Ala":"A","Arg":"R","Asn":"N","Asp":"D","Cys":"C","Gln":"Q","Glu":"E","Gly":"G",
           "His":"H","Ile":"I","Leu":"L","Lys":"K","Met":"M","Phe":"F","Pro":"P","Ser":"S",
           "Thr":"T","Trp":"W","Tyr":"Y","Val":"V","Ter":"*","Xaa":"X"}
    m = re.search(r"p\.([A-Z][a-z]{2})\d+([A-Z][a-z]{2}|Ter|\*)", name or "")
    if m: return aa3.get(m.group(1),"?"), aa3.get(m.group(2),"?")
    return "?","?"

# ─── API functions ────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_uniprot(query):
    base = "https://rest.uniprot.org/uniprotkb"
    # Try direct accession first
    acc_pat = re.compile(r"^[OPQ][0-9][A-Z0-9]{3}[0-9]$|^[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$", re.I)
    if acc_pat.match(query.strip()):
        r = requests.get(f"{base}/{query.strip().upper()}", headers={"Accept":"application/json"}, timeout=20)
        r.raise_for_status(); return r.json()
    # Search — use minimal safe fields, then fetch full entry
    params = {
        "query": f'gene:{query} AND reviewed:true AND organism_id:9606',
        "format": "json",
        "size": 1,
    }
    r = requests.get(f"{base}/search", params=params, headers={"Accept":"application/json"}, timeout=20)
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        # Broader fallback
        params["query"] = f'({query}) AND reviewed:true AND organism_id:9606'
        r = requests.get(f"{base}/search", params=params, headers={"Accept":"application/json"}, timeout=20)
        r.raise_for_status(); results = r.json().get("results", [])
    if not results:
        # Unreviewed fallback
        params["query"] = query
        params["size"] = 1
        r = requests.get(f"{base}/search", params=params, headers={"Accept":"application/json"}, timeout=20)
        r.raise_for_status(); results = r.json().get("results", [])
    if not results:
        raise ValueError(f"No UniProt entry found for '{query}'. Try the UniProt accession directly (e.g. P04637 for TP53).")
    uid = results[0]["primaryAccession"]
    r2 = requests.get(f"{base}/{uid}", headers={"Accept":"application/json"}, timeout=20)
    r2.raise_for_status(); return r2.json()

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_clinvar(gene, max_v=100):
    try:
        r = requests.get(ESEARCH, params={"db":"clinvar","term":f"{gene}[gene]","retmax":max_v,"retmode":"json"}, timeout=20)
        r.raise_for_status(); ids = r.json().get("esearchresult",{}).get("idlist",[])
    except: return {"variants":[],"summary":{}}
    if not ids: return {"variants":[],"summary":{}}
    variants = []
    for i in range(0, len(ids), 100):
        try:
            r2 = requests.get(ESUMMARY, params={"db":"clinvar","id":",".join(ids[i:i+100]),"retmode":"json"}, timeout=30)
            r2.raise_for_status(); data = r2.json().get("result",{})
            for uid in data.get("uids",[]):
                e = data.get(uid,{}); gc = e.get("germline_classification",{})
                sig = gc.get("description","Not provided")
                sc  = SIG_SCORE.get(sig.lower().strip(), 0)
                traits = [t.get("trait_name","") for t in e.get("trait_set",{}).get("trait",[]) if t.get("trait_name")]
                locs = e.get("location_list",[{}]); vset = e.get("variation_set",[{}])
                variants.append({
                    "uid":uid, "title":e.get("title",""),
                    "variant_name": vset[0].get("variation_name","") if vset else "",
                    "sig":sig, "score":sc,
                    "condition": "; ".join(traits) if traits else "Not specified",
                    "origin": e.get("origin",{}).get("origin",""),
                    "review": gc.get("review_status",""),
                    "start": locs[0].get("start","") if locs else "",
                    "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{e.get('variation_id',uid)}/",
                    "somatic": bool(e.get("somatic_classifications",{})),
                })
        except: pass
        time.sleep(0.1)
    variants.sort(key=lambda x: -x["score"])
    sigs  = Counter(v["sig"] for v in variants)
    conds = Counter()
    for v in variants:
        for c in v["condition"].split(";"):
            c = c.strip()
            if c and c != "Not specified": conds[c] += 1
    return {"variants":variants, "summary":{"total":len(variants),"by_sig":dict(sigs.most_common(8)),
            "top_conds":dict(conds.most_common(10)),
            "pathogenic":sum(1 for v in variants if v["score"]>=4),
            "vus":sum(1 for v in variants if v["score"]==2)}}

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_pdb(uid):
    if not uid: return ""
    try:
        r = requests.get(f"https://alphafold.ebi.ac.uk/api/prediction/{uid}", timeout=15)
        if r.status_code == 404: return ""
        r.raise_for_status(); entries = r.json()
        if not entries: return ""
        pdb_url = entries[0].get("pdbUrl","")
        if not pdb_url: return ""
        r2 = requests.get(pdb_url, timeout=30); r2.raise_for_status(); return r2.text
    except: return ""

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_papers(gene, n=6):
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
            pt = [p.get("value","").lower() for p in e.get("pubtype",[])]
            sc = (3 if "review" in pt else 0) + (2 if e.get("pubdate","")[:4] >= "2020" else 0)
            papers.append({"pmid":uid,"title":e.get("title","No title"),"authors":authors,
                           "journal":e.get("source",""),"year":e.get("pubdate","")[:4],
                           "url":f"https://pubmed.ncbi.nlm.nih.gov/{uid}/","score":sc,"pt":pt})
        return sorted(papers, key=lambda x: -x["score"])[:n]
    except: return []

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_ncbi_gene(symbol):
    try:
        r = requests.get(ESEARCH, params={"db":"gene","term":f"{symbol}[gene name] AND Homo sapiens[organism] AND alive[property]","retmax":1,"retmode":"json"}, timeout=15)
        r.raise_for_status(); ids = r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return {}
        gid = ids[0]
        r2 = requests.get(ESUMMARY, params={"db":"gene","id":gid,"retmode":"json"}, timeout=15)
        r2.raise_for_status(); e = r2.json().get("result",{}).get(gid,{})
        gi = e.get("genomicinfo",[{}])[0] if e.get("genomicinfo") else {}
        return {"id":gid,"chr":e.get("chromosome",""),"map":e.get("maplocation",""),
                "summary":e.get("summary",""),"start":gi.get("chrstart",""),
                "exons":gi.get("exoncount",""),"link":f"https://www.ncbi.nlm.nih.gov/gene/{gid}"}
    except: return {}

def parse_bfactors(pdb):
    out = {}
    for line in pdb.splitlines():
        if line.startswith(("ATOM","HETATM")):
            try:
                rn=int(line[22:26]); bf=float(line[60:66]); an=line[12:16].strip()
                if an=="CA": out[rn]=bf
            except: pass
    return out

def ml_score_variants(variants, sensitivity=50):
    out = []
    for v in variants:
        name = v.get("variant_name","") or v.get("title","")
        orig, alt = parse_aa(name)
        hd = abs(AA_HYDRO.get(orig,0) - AA_HYDRO.get(alt,0))
        cd = abs(AA_CHG.get(orig,0)   - AA_CHG.get(alt,0))
        stop  = float(alt == "*"); frame = float("frame" in name.lower())
        stars = {"practice guideline":1,"reviewed by expert panel":.9,
                 "criteria provided, multiple submitters":.7,
                 "criteria provided, single submitter":.5}.get(v.get("review","").lower(),.2)
        base = v.get("score",0) / 5.0
        ml   = min(1.0, base*.5 + stop*.25 + frame*.15 + (hd/10)*.05 + cd*.03 + stars*.02)
        vc   = dict(v); vc["ml"] = round(float(ml),3)
        vc["ml_rank"] = ml_rank_fn(ml, sensitivity)
        vc["rank"]    = score_rank(v.get("score",0), sensitivity)
        out.append(vc)
    return sorted(out, key=lambda x: -x["ml"])

# UniProt helpers
def g_gene(p):
    try: return p["genes"][0]["geneName"]["value"]
    except: return p.get("primaryAccession","?")
def g_name(p):
    try: return p["proteinDescription"]["recommendedName"]["fullName"]["value"]
    except: return "Unknown protein"
def g_seq(p): return p.get("sequence",{}).get("value","")
def g_diseases(p):
    out = []
    for c in p.get("comments",[]):
        if c.get("commentType") == "DISEASE":
            d = c.get("disease",{})
            out.append({"name":d.get("diseaseId",d.get("diseaseAcronym","Unknown")),
                        "desc":d.get("description",""),
                        "note":(c.get("note",{}).get("texts",[{}])[0].get("value","") if c.get("note") else "")})
    return out
def g_sub(p):
    locs = []
    for c in p.get("comments",[]):
        if c.get("commentType") == "SUBCELLULAR LOCATION":
            for e in c.get("subcellularLocations",[]):
                v = e.get("location",{}).get("value","")
                if v: locs.append(v)
    return list(dict.fromkeys(locs))
def g_tissue(p):
    for c in p.get("comments",[]):
        if c.get("commentType") == "TISSUE SPECIFICITY":
            t = c.get("texts",[])
            if t: return t[0].get("value","")
    return ""
def g_func(p):
    for c in p.get("comments",[]):
        if c.get("commentType") == "FUNCTION":
            t = c.get("texts",[])
            if t: return t[0].get("value","")
    return ""
def g_xref(p, db):
    for x in p.get("uniProtKBCrossReferences",[]):
        if x.get("database") == db: return x.get("id","")
    return ""
def g_gpcr(p):
    kws = [k.get("value","").lower() for k in p.get("keywords",[])]
    return any(x in " ".join(kws) for x in ["gpcr","g protein","rhodopsin","adrenergic"])
def g_ptype(p):
    kws = [k.get("value","").lower() for k in p.get("keywords",[])]
    if any("kinase" in k for k in kws): return "kinase"
    if any("gpcr" in k or "g protein" in k for k in kws): return "gpcr"
    if any("transcription" in k for k in kws): return "transcription_factor"
    if any("receptor" in k for k in kws): return "receptor"
    return "general"

# ─── CSV processing ───────────────────────────────────────────────
def detect_csv_type(df):
    cols = [c.lower() for c in df.columns]
    joined = " ".join(cols)
    if any(k in joined for k in ["fold","log2","logfc","expr","fpkm","rpkm","tpm","count"]):
        return "expression"
    if any(k in joined for k in ["variant","mutation","chrom","pos","ref","alt","rsid"]):
        return "variants"
    if any(k in joined for k in ["protein","abundance","intensity","peptide","spectral"]):
        return "proteomics"
    if any(k in joined for k in ["pvalue","p_value","padj","fdr","qvalue"]):
        return "stats_results"
    return "generic"

def analyse_csv(df, csv_type, goal, gene):
    findings = []
    if csv_type == "expression":
        fc_col  = next((c for c in df.columns if any(k in c.lower() for k in ["fold","logfc","log2","fc"])), None)
        p_col   = next((c for c in df.columns if any(k in c.lower() for k in ["pvalue","p_val","padj","fdr"])), None)
        gene_col= next((c for c in df.columns if any(k in c.lower() for k in ["gene","symbol","name"])), None)
        findings.append(("📊 Dataset shape", f"{len(df):,} rows × {len(df.columns)} columns detected as expression data."))
        if fc_col:
            up   = (df[fc_col] > 1).sum() if df[fc_col].dtype in [float,int] else "?"
            down = (df[fc_col] < -1).sum() if df[fc_col].dtype in [float,int] else "?"
            findings.append(("📈 Differential expression", f"Upregulated (FC>1): **{up}** · Downregulated (FC<-1): **{down}**"))
        if gene_col and gene:
            hits = df[df[gene_col].astype(str).str.upper() == gene.upper()]
            if not hits.empty:
                findings.append(("🎯 Your protein in dataset", f"**{gene}** found at row(s): {list(hits.index[:5])}. Values: {hits.iloc[0].to_dict()}"))
    elif csv_type == "variants":
        findings.append(("🧬 Variant dataset", f"{len(df):,} variants detected."))
        sig_col = next((c for c in df.columns if "sig" in c.lower() or "class" in c.lower() or "clin" in c.lower()), None)
        if sig_col:
            vc = df[sig_col].value_counts()
            top3 = ", ".join(f"{k}: {v}" for k,v in list(vc.items())[:5])
            findings.append(("📋 Classification breakdown", top3))
    elif csv_type == "proteomics":
        findings.append(("🔬 Proteomics dataset", f"{len(df):,} proteins/peptides detected."))
        int_col = next((c for c in df.columns if any(k in c.lower() for k in ["intensity","abundance","area"])), None)
        if int_col and df[int_col].dtype in [float,int]:
            findings.append(("📊 Intensity range", f"Min: {df[int_col].min():.2e} · Max: {df[int_col].max():.2e} · Median: {df[int_col].median():.2e}"))
    else:
        findings.append(("📋 Generic dataset", f"{len(df):,} rows × {len(df.columns)} columns loaded."))
        findings.append(("🔍 Columns detected", ", ".join(df.columns[:10].tolist())))
    # Goal-tailored insight
    goal_insights = {
        "therapeutic": f"Cross-reference these {len(df)} entries against CRITICAL/HIGH ClinVar variants to prioritise druggable targets.",
        "drug": "Flag proteins with both high expression AND ClinVar pathogenic variants as primary drug targets.",
        "biomarker": "Focus on genes with significant expression change + germline pathogenic variants as candidate biomarkers.",
        "mechanism": "Correlate expression changes with variant positions to identify mechanistic drivers.",
        "clinical": "Filter for clinically reviewed (2+ star) variants in your expression-altered gene list.",
    }
    for k, insight in goal_insights.items():
        if k in goal.lower():
            findings.append(("🎯 Goal-tailored insight", insight))
            break
    return findings

# ─── 3-D viewer ───────────────────────────────────────────────────
def viewer_html(pdb_text, scored, height=480):
    path_pos = {}
    for v in scored[:50]:
        pos = v.get("start") or v.get("position")
        try:
            p = int(pos)
            path_pos[p] = {"rank":v.get("ml_rank","NEUTRAL"),"ml":v.get("ml",0),
                           "cond":v.get("condition","")[:60],"sig":v.get("sig",""),
                           "var":v.get("variant_name","")[:40]}
        except: pass
    pp_js  = json.dumps({str(k):v for k,v in path_pos.items()})
    pdb_esc = pdb_text.replace("`","\\`").replace("\\","\\\\")
    return f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.1.0/3Dmol-min.js"></script>
<style>*{{margin:0;padding:0;box-sizing:border-box;}}body{{background:#04080f;font-family:Inter,sans-serif;display:flex;flex-direction:column;height:{height}px;}}
#ctrl{{display:flex;gap:4px;padding:6px 8px;background:#050f1e;border-bottom:1px solid #0c2040;flex-wrap:wrap;flex-shrink:0;}}
.btn{{background:#05101e;color:#2a5070;border:1px solid #0c2040;padding:3px 10px;border-radius:14px;cursor:pointer;font-size:11px;transition:all .2s;}}
.btn:hover,.btn.on{{background:#00e5ff;color:#000;font-weight:700;border-color:#00e5ff;}}
#wrap{{position:relative;flex:1;}}#v{{width:100%;height:100%;}}
#panel{{position:absolute;top:8px;right:8px;width:220px;background:rgba(4,8,15,.94);border:1px solid #0c2040;border-radius:10px;padding:12px;display:none;backdrop-filter:blur(8px);max-height:88%;overflow-y:auto;}}
#panel h3{{color:#00e5ff;font-size:12px;margin:0 0 7px;border-bottom:1px solid #0c2040;padding-bottom:4px;}}
.pr{{display:flex;justify-content:space-between;margin:3px 0;font-size:11px;}}.pk{{color:#0e2840;}}.pv{{color:#5a8090;font-weight:600;}}
#cl{{position:absolute;top:6px;right:8px;color:#1e4060;cursor:pointer;font-size:14px;}}
#leg{{position:absolute;bottom:7px;left:7px;background:rgba(4,8,15,.9);border:1px solid #0c2040;border-radius:8px;padding:7px 10px;font-size:10px;color:#1e4060;}}
.li{{display:flex;align-items:center;gap:5px;margin:2px 0;}}.ld{{width:8px;height:8px;border-radius:50%;flex-shrink:0;}}</style></head><body>
<div id="ctrl">
<button class="btn on" onclick="ss('cartoon',this)">🎀 Ribbon</button>
<button class="btn" onclick="ss('stick',this)">🦴 Stick</button>
<button class="btn" onclick="ss('sphere',this)">⬤ Sphere</button>
<button class="btn" onclick="ss('surface',this)">🌊 Surface</button>
<button class="btn" id="spb" onclick="toggleSpin()">▶ Spin</button>
<button class="btn" onclick="v.zoomTo();v.render()">🎯 Reset</button>
<button class="btn" onclick="toggleV()">🔴 Variants</button>
<button class="btn" onclick="toggleL()">🏷 Labels</button>
</div>
<div id="wrap"><div id="v"></div>
<div id="panel"><span id="cl" onclick="document.getElementById('panel').style.display='none'">✕</span>
<h3 id="pt">Residue Info</h3><div id="pc"></div></div>
<div id="leg">
<div class="li"><div class="ld" style="background:#1565C0"></div>pLDDT ≥90</div>
<div class="li"><div class="ld" style="background:#29B6F6"></div>70–90</div>
<div class="li"><div class="ld" style="background:#FDD835"></div>50–70</div>
<div class="li"><div class="ld" style="background:#FF7043"></div>&lt;50</div>
<div class="li"><div class="ld" style="background:#ff2d55;border:1px solid #fff5;"></div>Pathogenic</div>
</div></div>
<script>
const pp={pp_js};const pdb=`{pdb_esc}`;
const an={{ALA:"A",ARG:"R",ASN:"N",ASP:"D",CYS:"C",GLN:"Q",GLU:"E",GLY:"G",HIS:"H",ILE:"I",LEU:"L",LYS:"K",MET:"M",PHE:"F",PRO:"P",SER:"S",THR:"T",TRP:"W",TYR:"Y",VAL:"V"}};
const fn={{A:"Alanine",R:"Arginine",N:"Asparagine",D:"Aspartate",C:"Cysteine",Q:"Glutamine",E:"Glutamate",G:"Glycine",H:"Histidine",I:"Isoleucine",L:"Leucine",K:"Lysine",M:"Methionine",F:"Phenylalanine",P:"Proline",S:"Serine",T:"Threonine",W:"Tryptophan",Y:"Tyrosine",V:"Valine"}};
const hy={{A:1.8,R:-4.5,N:-3.5,D:-3.5,C:2.5,Q:-3.5,E:-3.5,G:-0.4,H:-3.2,I:4.5,L:3.8,K:-3.9,M:1.9,F:2.8,P:-1.6,S:-0.8,T:-0.7,W:-0.9,Y:-1.3,V:4.2}};
let spinning=false,showV=true,showL=false,curStyle='cartoon';
const v=$3Dmol.createViewer(document.getElementById('v'),{{backgroundColor:'0x04080f'}});
v.addModel(pdb,'pdb');
function cf(a){{const b=a.b;if(b>=90)return'#1565C0';if(b>=70)return'#29B6F6';if(b>=50)return'#FDD835';return'#FF7043';}}
function ap(){{v.removeAllSurfaces();
if(curStyle==='surface')v.addSurface($3Dmol.SurfaceType.VDW,{{colorfunc:cf,opacity:.78}});
else if(curStyle==='sphere')v.setStyle({{}},{{sphere:{{colorfunc:cf,radius:.7}}}});
else if(curStyle==='stick')v.setStyle({{}},{{cartoon:{{colorfunc:cf,thickness:.2}},stick:{{colorscheme:'chainHetatm',radius:.12}}}});
else v.setStyle({{}},{{cartoon:{{colorfunc:cf,thickness:.42}}}});
if(showV)Object.entries(pp).forEach(([pos,info])=>{{const rk=info.rank;const c=rk==='CRITICAL'?'#ff2d55':rk==='HIGH'?'#ff8c42':rk==='MEDIUM'?'#ffd60a':'#3a5a7a';v.addStyle({{resi:parseInt(pos),atom:'CA'}},{{sphere:{{radius:1.3,color:c,opacity:.93}}}});}});
v.render();}}
ap();v.zoomTo();v.render();
v.setClickable({{}},true,function(atom){{
const pos=atom.resi,r3=(atom.resn||'').toUpperCase(),r1=an[r3]||'?';
const full=fn[r1]||r3,pl=atom.b||0,cl=pl>=90?'Very High':pl>=70?'Confident':pl>=50?'Low':'Very Low';
const inf=pp[String(pos)];let html='';
if(inf){{const rc={{CRITICAL:'#ff2d55',HIGH:'#ff8c42',MEDIUM:'#ffd60a',NEUTRAL:'#3a5a7a'}};
html+=`<span style="color:${{rc[inf.rank]}};font-weight:800;font-size:11px;display:block;margin-bottom:6px;">${{inf.rank}}</span>`;}}
html+=`<div class="pr"><span class="pk">Residue</span><span class="pv">${{r1}} (${{full}})</span></div>`;
html+=`<div class="pr"><span class="pk">Position</span><span class="pv">${{pos}}</span></div>`;
html+=`<div class="pr"><span class="pk">pLDDT</span><span class="pv">${{pl.toFixed(1)}} (${{cl}})</span></div>`;
html+=`<div class="pr"><span class="pk">Hydropathy</span><span class="pv">${{hy[r1]!==undefined?hy[r1].toFixed(1):'?'}}</span></div>`;
if(inf){{html+='<hr style="border-color:#0c2040;margin:6px 0;">';
html+=`<div class="pr"><span class="pk">Variant</span><span class="pv" style="font-size:10px;">${{inf.var||'—'}}</span></div>`;
html+=`<div class="pr"><span class="pk">ClinVar</span><span class="pv" style="font-size:10px;">${{inf.sig||'—'}}</span></div>`;
html+=`<div class="pr"><span class="pk">ML</span><span class="pv" style="color:#00e5ff;">${{(inf.ml*100).toFixed(0)}}%</span></div>`;
if(inf.cond)html+=`<div style="margin-top:4px;color:#0e2840;font-size:10px;line-height:1.4;">${{inf.cond}}</div>`;}}
document.getElementById('pt').textContent=r3+pos;document.getElementById('pc').innerHTML=html;document.getElementById('panel').style.display='block';}});
function ss(style,btn){{curStyle=style;document.querySelectorAll('.btn').forEach(b=>b.classList.remove('on'));btn.classList.add('on');ap();}}
function toggleSpin(){{spinning=!spinning;v.spin(spinning?'y':false,.6);const b=document.getElementById('spb');b.textContent=spinning?'⏸ Stop':'▶ Spin';b.classList.toggle('on',spinning);}}
function toggleV(){{showV=!showV;ap();}}
function toggleL(){{showL=!showL;v.removeAllLabels();if(showL)Object.entries(pp).forEach(([pos,info])=>{{if(info.rank==='CRITICAL'||info.rank==='HIGH')v.addLabel('P'+pos,{{position:{{resi:parseInt(pos),atom:'CA'}},backgroundColor:'#ff2d55',backgroundOpacity:.8,fontSize:9,fontColor:'white',borderRadius:3}});}});v.render();}}
</script></body></html>""".replace("{pp_js}", pp_js)

def render_citations(papers, n=4):
    if not papers: return
    st.markdown("<div style='color:#0e2840;font-size:.66rem;text-transform:uppercase;letter-spacing:.8px;margin:.7rem 0 .3rem;'>📚 Supporting Literature</div>", unsafe_allow_html=True)
    for p in papers[:n]:
        pt = " ".join(f"<span style='background:#07152a;color:#1a4060;font-size:.65rem;padding:1px 5px;border-radius:6px;margin-left:3px;'>{t.title()}</span>" for t in p.get("pt",[])[:2])
        st.markdown(f"<div class='cite'><a href='{p['url']}' target='_blank'>{p['title'][:110]}</a>{pt}<div class='cm'>{p['authors']} · {p['journal']} · {p['year']} · PMID {p['pmid']}</div></div>", unsafe_allow_html=True)

def goal_banner(goal_label, goal_custom):
    goal = goal_custom if "Custom" in goal_label else goal_label
    if not goal: return ""
    return f"<div class='goal-box'><h4>🎯 Research Goal</h4><div style='color:#3a8090;font-size:.84rem;'>{goal}</div><div style='margin-top:.5rem;'><span class='goal-tag'>Findings tailored to this goal</span><span class='goal-tag'>ClinVar primary source</span><span class='goal-tag'>ML-ranked</span></div></div>"

def goal_context(goal_label):
    """Return a short contextual sentence to inject into each section."""
    g = goal_label.lower()
    if "therapeutic" in g: return "Prioritising variants in druggable domains and known disease genes as therapeutic targets."
    if "drug" in g: return "Highlighting actionable mutations and binding-pocket variants suitable for small-molecule targeting."
    if "biomarker" in g: return "Emphasising variants with strong disease association and tissue-specific expression changes."
    if "mechanism" in g: return "Focusing on mechanistic variants that disrupt key functional domains or interaction interfaces."
    if "clinical" in g: return "Emphasising ClinVar classification, review status, and clinical evidence quality."
    if "experimental" in g: return "Ranking experiments by expected mechanistic yield and cost-efficiency."
    return "Providing a comprehensive overview across all analytical dimensions."

# ─── Genomic Integrity Engine ─────────────────────────────────────
def compute_genomic_integrity(cv, protein_length):
    variants  = cv.get('variants', [])
    total     = len(variants)
    germline  = [v for v in variants if not v.get('somatic', False)]
    pathogenic= [v for v in germline if v.get('score', 0) >= 4]
    vus       = [v for v in germline if v.get('score', 0) == 2]
    benign    = [v for v in germline if v.get('score', 0) <= 0]
    n_p       = len(pathogenic)
    n_g       = max(len(germline), 1)
    length    = max(protein_length or 1, 1)
    density   = n_p / n_g
    per100    = (n_p / length) * 100
    if total < 10:
        return dict(verdict="UNDERSTUDIED", label="Insufficient ClinVar data", css="gi-unknown",
                    color="#1e6080", icon="❓", pursue="neutral", density=density, per100=per100,
                    n_pathogenic=n_p, n_vus=len(vus), n_benign=len(benign), n_total=total, n_germline=len(germline),
                    explanation="Too few ClinVar entries to draw conclusions. May be understudied or recently characterised.",
                    pathogenic_list=pathogenic)
    elif n_p == 0:
        return dict(verdict="NO DISEASE VARIANTS", label="Zero pathogenic germline variants in ClinVar",
                    css="gi-redundant", color="#3a5a7a", icon="⚪", pursue="deprioritise", density=0, per100=0,
                    n_pathogenic=0, n_vus=len(vus), n_benign=len(benign), n_total=total, n_germline=len(germline),
                    explanation=(f"Despite {total} ClinVar entries, zero cause a Mendelian disease. "
                                 "This protein may be redundant or bypassable in biochemical signalling. "
                                 "Famous proteins can be wrong targets — β2-arrestin, β-adrenergic receptors "
                                 "and GRKs are all extensively studied but carry no dominant disease variants."),
                    pathogenic_list=[])
    elif density < 0.01 and n_p < 5:
        return dict(verdict="VERY LOW DISEASE BURDEN", label=f"Only {n_p} of {len(germline)} germline variants pathogenic",
                    css="gi-redundant", color="#4a6a30", icon="🟡", pursue="caution", density=density, per100=per100,
                    n_pathogenic=n_p, n_vus=len(vus), n_benign=len(benign), n_total=total, n_germline=len(germline),
                    explanation="Extremely low pathogenic density. Rare associations may be incidental. Check if interaction partners carry the actual disease burden.",
                    pathogenic_list=pathogenic)
    elif density < 0.05 or per100 < 0.5:
        return dict(verdict="MODERATE", label=f"{n_p} pathogenic variants ({density*100:.1f}% of total)",
                    css="gi-moderate", color="#ffd60a", icon="🟡", pursue="selective", density=density, per100=per100,
                    n_pathogenic=n_p, n_vus=len(vus), n_benign=len(benign), n_total=total, n_germline=len(germline),
                    explanation="Some disease association but low density. Focus only on confirmed P/LP variants. Do not extrapolate to nearby benign entries.",
                    pathogenic_list=pathogenic)
    elif per100 >= 1 or (n_p >= 20 and density >= 0.05):
        return dict(verdict="DISEASE-CRITICAL", label=f"{n_p} pathogenic variants · {per100:.1f} per 100 aa",
                    css="gi-critical", color="#ff2d55", icon="🔴", pursue="prioritise", density=density, per100=per100,
                    n_pathogenic=n_p, n_vus=len(vus), n_benign=len(benign), n_total=total, n_germline=len(germline),
                    explanation="Strong genomic evidence. This protein is critical for human physiology. Variants follow Mendelian inheritance — validated disease driver.",
                    pathogenic_list=pathogenic)
    else:
        return dict(verdict="DISEASE-ASSOCIATED", label=f"{n_p} pathogenic variants ({density*100:.1f}%)",
                    css="gi-moderate", color="#ff8c42", icon="🟠", pursue="proceed", density=density, per100=per100,
                    n_pathogenic=n_p, n_vus=len(vus), n_benign=len(benign), n_total=total, n_germline=len(germline),
                    explanation="Meaningful disease association confirmed. Prioritise P/LP variants over VUS and benign entries.",
                    pathogenic_list=pathogenic)

def variant_landscape_chart(variants, protein_length, scored):
    if not variants: return None
    sig_c = {5:"#ff2d55",4:"#ff6b55",3:"#ff8c42",2:"#ffd60a",1:"#2a6040",0:"#0e2840",-1:"#060f18"}
    sig_l = {5:"Pathogenic",4:"Likely Pathogenic",3:"Risk Factor",2:"VUS",1:"Likely Benign",0:"Benign",-1:"Not Provided"}
    ml_map = {v.get("uid",""): v.get("ml",0) for v in scored}
    positions, ys, colours, labels = [], [], [], []
    for v in variants:
        try: pos_int = int(v.get("start",""))
        except: continue
        sc = v.get("score",-1); ml2 = ml_map.get(v.get("uid",""),0)
        name2 = (v.get("variant_name") or v.get("title",""))[:40]
        positions.append(pos_int)
        ys.append(max(sc,0) + ml2*0.4)
        colours.append(sig_c.get(sc,"#0e2840"))
        labels.append(f"{name2}<br>Sig: {sig_l.get(sc,'?')}<br>ML: {ml2:.2f}")
    if not positions: return None
    fig = go.Figure()
    for x, y, c in zip(positions, ys, colours):
        fig.add_trace(go.Scatter(x=[x,x],y=[0,y],mode="lines",
            line=dict(color=c,width=1),showlegend=False,hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=positions,y=ys,mode="markers",
        marker=dict(color=colours,size=7,opacity=0.85,line=dict(color="#04080f",width=0.5)),
        text=labels,hovertemplate="%{text}<extra></extra>",showlegend=False))
    fig.add_hrect(y0=0,y1=0.8,fillcolor="rgba(6,30,6,0.2)",line_width=0)
    fig.add_hrect(y0=3.5,y1=6,fillcolor="rgba(80,0,20,0.15)",line_width=0)
    maxpos = max(protein_length or 100, max(positions)+10)
    fig.update_layout(paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#1e4060",
        xaxis=dict(title="Residue position",range=[0,maxpos],gridcolor="#060f1c",color="#0e2840"),
        yaxis=dict(title="Pathogenicity",range=[-0.1,6.2],
            tickvals=[0,2,4,5],ticktext=["Benign","VUS","Likely P.","Pathogenic"],
            gridcolor="#060f1c",color="#0e2840"),
        height=270,margin=dict(t=8,b=30,l=65,r=8),hovermode="closest")
    return fig

def partner_html(gene1, gi1, gene2, gi2):
    def col_html(gene, gi):
        clr = gi["color"]
        dens_pct = min(100, int(gi["density"]*2000))
        return (f"<div style='flex:1;background:#050d1a;border:1px solid {clr}33;"
                f"border-radius:10px;padding:.9rem;min-width:0;'>"
                f"<div style='color:{clr};font-weight:800;font-size:.9rem;margin-bottom:3px;'>{gi['icon']} {gene}</div>"
                f"<div style='color:{clr}88;font-size:.72rem;margin-bottom:6px;'>{gi['verdict']}</div>"
                f"<div style='color:#1e4060;font-size:.73rem;'>Pathogenic: <b style='color:{clr};'>{gi['n_pathogenic']}</b></div>"
                f"<div style='color:#1e4060;font-size:.73rem;'>Total ClinVar: <b style='color:#2a5070;'>{gi['n_total']}</b></div>"
                f"<div style='color:#1e4060;font-size:.73rem;'>Density: <b style='color:{clr};'>{gi['density']*100:.1f}%</b></div>"
                f"<div style='margin-top:5px;height:4px;background:#07152a;border-radius:3px;overflow:hidden;'>"
                f"<div style='width:{dens_pct}%;height:100%;background:{clr};'></div></div></div>")
    both = col_html(gene1,gi1) + col_html(gene2,gi2)
    if gi1["n_pathogenic"]>0 and gi2["n_pathogenic"]>0:
        verdict = (f"<div style='color:#00c896;font-size:.79rem;margin-top:.6rem;padding:.6rem;background:#030a06;border-radius:8px;border:1px solid #00c89622;'>"
                   f"✅ Both proteins carry disease variants — supports a shared pathway or complex (analogous to ITA2B+ITB3 in Glanzmann thrombasthenia).</div>")
    elif gi1["n_pathogenic"]>0 and gi2["n_pathogenic"]==0:
        verdict = (f"<div style='color:#ffd60a;font-size:.79rem;margin-top:.6rem;padding:.6rem;background:#0a0900;border-radius:8px;border:1px solid #ffd60a22;'>"
                   f"⚠️ {gene1} has disease variants; {gene2} does not. The proposed interaction may not be biologically critical — {gene2} may be redundant.</div>")
    elif gi1["n_pathogenic"]==0 and gi2["n_pathogenic"]>0:
        verdict = (f"<div style='color:#ffd60a;font-size:.79rem;margin-top:.6rem;padding:.6rem;background:#0a0900;border-radius:8px;border:1px solid #ffd60a22;'>"
                   f"⚠️ {gene2} has disease variants; {gene1} does not. Focus resources on {gene2}.</div>")
    else:
        verdict = (f"<div style='color:#3a6080;font-size:.79rem;margin-top:.6rem;padding:.6rem;background:#040d18;border-radius:8px;border:1px solid #1e404022;'>"
                   f"⚪ Neither protein shows disease-causing variants. The proposed interaction may not be a meaningful disease pathway.</div>")
    return f"<div style='display:flex;gap:.6rem;'>{both}</div>{verdict}"

# ─── Session state ────────────────────────────────────────────────
for k,v in {"pdata":None,"cv":None,"pdb":"","papers":[],"scored":[],"gene":"","uid":"",
            "assay":"","last":"","csv_df":None,"csv_type":"","goal_label":GOAL_OPTIONS[0],
            "goal_custom":"","sensitivity":50,"gi":None,"partner_query":"","partner_cv":None,"partner_gi":None}.items():
    if k not in st.session_state: st.session_state[k]=v

# ─── Sidebar ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='text-align:center;padding:.3rem 0 .6rem;'><div style='font-size:1.6rem;'>🧬</div><div style='color:#00e5ff;font-size:1.1rem;font-weight:800;'>Protellect</div><div style='color:#0a2040;font-size:.68rem;'>Protein Intelligence Platform</div></div><div style='border-top:1px solid #0c2040;margin-bottom:.7rem;'></div>", unsafe_allow_html=True)

    # ── Research goal ──────────────────────────────────────────────
    st.markdown("<div class='sb-t'>🎯 Research Goal</div>", unsafe_allow_html=True)
    goal_label = st.selectbox("Goal", GOAL_OPTIONS, index=GOAL_OPTIONS.index(st.session_state["goal_label"]), label_visibility="collapsed")
    st.session_state["goal_label"] = goal_label
    goal_custom = ""
    if "Custom" in goal_label:
        goal_custom = st.text_input("Describe your goal", value=st.session_state["goal_custom"], placeholder="e.g. Find splice-site variants that affect exon 4 inclusion…", label_visibility="collapsed")
        st.session_state["goal_custom"] = goal_custom
    active_goal = goal_custom if "Custom" in goal_label else goal_label

    # ── Protein search ─────────────────────────────────────────────
    st.markdown("<div class='sb-t'>🔍 Protein Search</div>", unsafe_allow_html=True)
    query  = st.text_input("Gene / UniProt ID", placeholder="TP53 · BRCA1 · P04637 · EGFR", label_visibility="collapsed")
    search = st.button("🔬 Analyse Protein", use_container_width=True)

    # ── CSV upload ─────────────────────────────────────────────────
    st.markdown("<div class='sb-t'>📂 Wet-Lab Data (CSV)</div>", unsafe_allow_html=True)
    uploaded_csv = st.file_uploader("Upload CSV (any format)", type=["csv","tsv","txt"], label_visibility="collapsed")
    if uploaded_csv:
        try:
            sep = "\t" if uploaded_csv.name.endswith((".tsv",".txt")) else ","
            df  = pd.read_csv(uploaded_csv, sep=sep, on_bad_lines="skip")
            csv_type = detect_csv_type(df)
            st.session_state["csv_df"]   = df
            st.session_state["csv_type"] = csv_type
            st.markdown(f"<div style='background:#040d18;border:1px solid #0c3050;border-radius:8px;padding:7px 10px;margin-top:4px;'><div style='color:#4adaff;font-size:.78rem;font-weight:700;'>{uploaded_csv.name}</div><div style='color:#1a4060;font-size:.72rem;'>{len(df):,} rows · {len(df.columns)} cols · <b style=\"color:#4adaff;\">{csv_type.replace('_',' ').title()}</b></div></div>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"CSV error: {e}")

    # ── Wet-lab text assay ─────────────────────────────────────────
    st.markdown("<div class='sb-t'>🧫 Assay Notes (text)</div>", unsafe_allow_html=True)
    assay_txt = st.text_area("Assay description", height=75, placeholder="e.g. Western blot shows 3× increase in expression…", label_visibility="collapsed")

    # ── Sensitivity ────────────────────────────────────────────────
    st.markdown("<div class='sb-t'>🎚️ Triage Sensitivity</div>", unsafe_allow_html=True)
    st.markdown("<div class='sens-wrap'>", unsafe_allow_html=True)
    sensitivity = st.slider("", 0, 100, st.session_state["sensitivity"], 5,
                            help="Higher = more variants flagged as HIGH/CRITICAL. Lower = only the most certain variants elevated.",
                            label_visibility="collapsed")
    st.session_state["sensitivity"] = sensitivity
    sens_label = "🔬 Strict" if sensitivity < 30 else "⚖️ Balanced" if sensitivity < 70 else "🔓 Sensitive"
    st.markdown(f"<div style='display:flex;justify-content:space-between;margin-top:2px;'><span style='color:#0e2840;font-size:.68rem;'>Strict</span><span style='color:#00e5ff;font-size:.72rem;font-weight:700;'>{sens_label} ({sensitivity})</span><span style='color:#0e2840;font-size:.68rem;'>Sensitive</span></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Data depth ─────────────────────────────────────────────────
    st.markdown("<div class='sb-t'>⚙️ Data Depth</div>", unsafe_allow_html=True)
    depth = st.selectbox("Depth", ["Standard (100 variants)","Deep (300 variants)"], label_visibility="collapsed")
    max_v = 100 if "Standard" in depth else 300

    # ── Partner protein ─────────────────────────────────────────────
    st.markdown("<div class='sb-t'>🔗 Compare Interaction Partner</div>", unsafe_allow_html=True)
    partner_q = st.text_input("Partner gene / UniProt ID", value=st.session_state["partner_query"],
                               placeholder="e.g. ITGAL · GNB1 · ARRB2", label_visibility="collapsed",
                               key="partner_inp")
    fetch_partner = st.button("Compare Partner", use_container_width=True, key="partner_btn")
    if fetch_partner and partner_q:
        with st.spinner("Fetching partner ClinVar data..."):
            try:
                p2 = fetch_uniprot(partner_q)
                g2 = g_gene(p2); uid2 = p2.get("primaryAccession","")
                cv2 = fetch_clinvar(g2, 100)
                ln2 = p2.get("sequence",{}).get("length",1)
                gi2 = compute_genomic_integrity(cv2, ln2)
                st.session_state["partner_query"] = partner_q
                st.session_state["partner_cv"]    = cv2
                st.session_state["partner_gi"]    = {"gi":gi2,"gene":g2,"uid":uid2}
            except Exception as e:
                st.error(f"Partner fetch error: {e}")

    # ── Protein summary ─────────────────────────────────────────────
    if st.session_state["pdata"]:
        p = st.session_state["pdata"]; gene = st.session_state["gene"]
        uid = st.session_state["uid"]; scored = st.session_state["scored"]
        cv  = st.session_state["cv"]
        st.markdown(f"<div style='border-top:1px solid #0c2040;margin:.7rem 0 .4rem;'></div><div style='background:#040d18;border:1px solid #0c2040;border-radius:8px;padding:8px 10px;'><div style='color:#00e5ff;font-weight:700;font-size:.9rem;'>{gene}</div><div style='color:#0e2840;font-size:.7rem;'>{uid}</div></div>", unsafe_allow_html=True)
        # Disease ranking
        diseases = g_diseases(p); ds_scores = {}
        for sv in scored:
            for c in sv.get("condition","").split(";"):
                c = c.strip()
                if c: ds_scores[c] = max(ds_scores.get(c,0), sv.get("ml",0))
        all_names = list(dict.fromkeys([d["name"] for d in diseases]+[c for sv in cv.get("variants",[]) for c in sv.get("condition","").split(";") if c.strip() and c.strip()!="Not specified"]))
        if all_names:
            st.markdown("<div class='sb-t'>🏥 Disease Affiliations</div>", unsafe_allow_html=True)
            for name in all_names[:10]:
                score = ds_scores.get(name,.4); rk = "CRITICAL" if score>=.85 else "HIGH" if score>=.65 else "MEDIUM" if score>=.40 else "NEUTRAL"
                if any(k in name.lower() for k in ["cancer","carcinoma","leukemia","sarcoma"]) and rk=="MEDIUM": rk="HIGH"
                clr = RANK_CLR[rk]
                css_cls = RANK_CSS[rk]
                st.markdown(f"<div style='display:flex;align-items:center;gap:6px;margin:3px 0;'><span class='badge {css_cls}'>{rk}</span><span style='color:#0e2840;font-size:.74rem;'>{name[:33]}</span></div>", unsafe_allow_html=True)
        # Suggestions tailored to goal
        ptype = g_ptype(p)
        base_sugg = {"kinase":["ADP-Glo kinase assay","Phospho-proteomics","Kinase inhibitor screen"],"gpcr":["cAMP (HTRF)","β-arrestin (BRET)","Radioligand binding"],"transcription_factor":["ChIP-seq","EMSA","Luciferase reporter"],"general":["Co-IP/AP-MS","CRISPR KO screen","Thermal shift"]}.get(ptype,["Co-IP","CRISPR KO"])
        st.markdown("<div class='sb-t'>🔭 Suggested Experiments</div>", unsafe_allow_html=True)
        for s in base_sugg: st.markdown(f"<div style='color:#0d2840;font-size:.74rem;margin:2px 0;'>▸ {s}</div>", unsafe_allow_html=True)

# ─── Header (compact) ─────────────────────────────────────────────
st.markdown("<div class='ph'><span class='pt'>🧬 Protellect</span><div class='ps'>AI-powered protein triage · Eliminate wasted experiments · Follow the science</div></div>", unsafe_allow_html=True)

# ─── Load data ────────────────────────────────────────────────────
if search and query and query != st.session_state["last"]:
    with st.spinner("🔬 Fetching UniProt · ClinVar · AlphaFold · PubMed…"):
        try:
            pdata = fetch_uniprot(query); st.session_state["pdata"] = pdata
            gene  = g_gene(pdata); uid = pdata.get("primaryAccession","")
            st.session_state["gene"] = gene; st.session_state["uid"] = uid
            cv    = fetch_clinvar(gene, max_v); st.session_state["cv"] = cv
            pdb   = fetch_pdb(uid); st.session_state["pdb"] = pdb
            papers= fetch_papers(gene); st.session_state["papers"] = papers
            scored= ml_score_variants(cv.get("variants",[]), sensitivity)
            protein_len = pdata.get("sequence",{}).get("length",1)
            gi = compute_genomic_integrity(cv, protein_len)
            st.session_state["gi"] = gi
            st.session_state["scored"] = scored
            st.session_state["assay"]  = assay_txt; st.session_state["last"] = query
            st.rerun()
        except Exception as e:
            st.error(f"⚠️ {e}")

# Re-score if sensitivity changed
if st.session_state["pdata"] and st.session_state["cv"]:
    prev_scored = st.session_state["scored"]
    if prev_scored and prev_scored[0].get("ml_rank") != ml_rank_fn(prev_scored[0]["ml"], sensitivity):
        st.session_state["scored"] = ml_score_variants(st.session_state["cv"].get("variants",[]), sensitivity)
        scored = st.session_state["scored"]

# ─── Landing page ─────────────────────────────────────────────────
if not st.session_state["pdata"]:
    st.markdown("""<div class='info-land'>
<div style='font-size:2.5rem;margin-bottom:.6rem;'>🧬</div>
<div style='color:#0e2840;font-size:1rem;font-weight:600;margin-bottom:.4rem;'>Enter a protein or gene in the sidebar to begin</div>
<div style='color:#061828;font-size:.84rem;margin-bottom:1.2rem;'>Try: <b style='color:#0d2840;'>TP53</b> · <b style='color:#0d2840;'>BRCA1</b> · <b style='color:#0d2840;'>EGFR</b> · <b style='color:#0d2840;'>P04637</b></div>
<div style='display:flex;gap:.7rem;justify-content:center;flex-wrap:wrap;'>"""
+"".join(f"<div style='background:#05101e;border:1px solid #0c2040;border-radius:9px;padding:.6rem .9rem;width:145px;'><div style='font-size:1.1rem;'>{ic}</div><div style='color:#0e2840;font-size:.75rem;margin-top:3px;'><b style='color:#1e4060;'>{t}</b><br>{d}</div></div>" for ic,t,d in [("🔴","Triage","3D + hotspots"),("📋","Case Study","Tissue · GPCR"),("🔬","Explorer","Click & mutate"),("🧪","Experiments","Protocols")])
+"</div></div>", unsafe_allow_html=True)
    if st.session_state["csv_df"] is not None:
        st.markdown("<hr class='dv'>", unsafe_allow_html=True)
        sh("📂","CSV Data Analysis")
        df = st.session_state["csv_df"]; csv_type = st.session_state["csv_type"]
        st.markdown(f"<div style='color:#1e4060;font-size:.8rem;margin-bottom:.5rem;'>Type detected: <b style='color:#4adaff;'>{csv_type.replace('_',' ').title()}</b></div>", unsafe_allow_html=True)
        st.dataframe(df.head(10), use_container_width=True)
        findings = analyse_csv(df, csv_type, active_goal, st.session_state["gene"])
        for title, body in findings:
            st.markdown(f"<div class='csv-card'><h4>{title}</h4><p style='color:#3a6080;font-size:.83rem;'>{body}</p></div>", unsafe_allow_html=True)
    st.stop()

# ─── Main tabs (sticky at top) ────────────────────────────────────
pdata  = st.session_state["pdata"]; cv     = st.session_state["cv"]
pdb    = st.session_state["pdb"];   papers = st.session_state["papers"]
scored = st.session_state["scored"]; gene   = st.session_state["gene"]
assay  = st.session_state["assay"]; uid    = st.session_state["uid"]
summary= cv.get("summary",{}); variants = cv.get("variants",[])
diseases = g_diseases(pdata)
protein_length = pdata.get("sequence",{}).get("length",1)
gi = st.session_state.get("gi") or compute_genomic_integrity(cv, protein_length)
if not st.session_state.get("gi"): st.session_state["gi"] = gi
partner_info = st.session_state.get("partner_gi")
ds_scores = {}
for sv in scored:
    for c in sv.get("condition","").split(";"):
        c = c.strip()
        if c: ds_scores[c] = max(ds_scores.get(c,0), sv.get("ml",0))

# Goal banner
st.markdown(goal_banner(goal_label, goal_custom), unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🔴  Triage","📋  Case Study","🔬  Protein Explorer","🧪  Experiments & Therapy"])

# ══════════════════════════════════════════
# TAB 1 — TRIAGE
# ══════════════════════════════════════════
with tab1:
    # ── Genomic Integrity Panel (bias-elimination layer) ───────────
    gi_box_col, gi_meta_col = st.columns([2,1], gap="large")
    with gi_box_col:
        gi_clr = gi["color"]
        st.markdown(
            f"<div class='{gi['css']}'>"
            f"<div class='gi-title' style='color:{gi_clr};'>{gi['icon']} Genomic Integrity: {gi['verdict']}</div>"
            f"<div class='gi-sub' style='color:{gi_clr}88;'>{gi['label']}</div>"
            f"<div style='color:#1e4060;font-size:.82rem;line-height:1.6;margin-bottom:.7rem;'>{gi['explanation']}</div>"
            f"<span class='gi-stat' style='color:{gi_clr};'>🔴 Pathogenic: <b>{gi['n_pathogenic']}</b></span>"
            f"<span class='gi-stat' style='color:#ffd60a;'>🟡 VUS: <b>{gi['n_vus']}</b></span>"
            f"<span class='gi-stat' style='color:#2a6040;'>✅ Benign: <b>{gi['n_benign']}</b></span>"
            f"<span class='gi-stat' style='color:#3a6080;'>Total: <b>{gi['n_total']}</b></span>"
            f"<span class='gi-stat' style='color:{gi_clr};'>Density: <b>{gi['density']*100:.2f}%</b></span>"
            f"<span class='gi-stat' style='color:{gi_clr};'>Per 100aa: <b>{gi['per100']:.2f}</b></span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with gi_meta_col:
        pursue_map = {
            "prioritise": ("🔴 PURSUE — strong genomic evidence", "#ff2d55"),
            "proceed":    ("🟠 PROCEED — meaningful evidence",    "#ff8c42"),
            "selective":  ("🟡 SELECTIVE — focus on P/LP only",   "#ffd60a"),
            "caution":    ("⚠️ CAUTION — very low evidence",      "#5a7a2a"),
            "deprioritise":("⚪ DEPRIORITISE — no disease link",  "#3a6080"),
            "neutral":    ("❓ NEUTRAL — insufficient data",      "#1e6080"),
        }
        rec_label, rec_clr2 = pursue_map.get(gi["pursue"], ("❓ Unknown","#1e6080"))
        st.markdown(
            f"<div style='background:#04080f;border:1px solid {rec_clr2}33;border-radius:10px;"
            f"padding:.9rem;height:100%;'>"
            f"<div style='color:{rec_clr2};font-weight:800;font-size:.85rem;margin-bottom:.5rem;'>Recommendation</div>"
            f"<div style='color:{rec_clr2};font-size:.88rem;font-weight:700;'>{rec_label}</div>"
            f"<div style='color:#0e2840;font-size:.74rem;margin-top:.5rem;line-height:1.5;'>"
            f"{'Genetics-first principle: proteins without Mendelian disease variants may be bypassable regardless of structural data or in vitro studies.' if gi['pursue'] in ['deprioritise','caution'] else 'This protein has confirmed disease-causing germline variants — genuine biological importance validated by human genetics.'}"
            f"</div></div>",
            unsafe_allow_html=True,
        )
    # Bias warning for famous proteins with no disease variants
    if gi["pursue"] == "deprioritise":
        st.markdown(
            "<div class='bias-warn'>"
            "<p>⚠️ <b style='color:#ff2d55;'>Potential Research Bias Alert:</b> "
            "This protein has been extensively studied but carries no disease-causing germline variants in ClinVar. "
            "Famous examples of this pattern include β2-arrestin (ARRB2), β-adrenergic receptors (ADRB1/2), "
            "and several GRKs — all touted as major drug targets, yet none carry dominant Mendelian disease variants. "
            "Before committing wet-lab resources, verify whether this protein's role is supported by human genetics "
            "rather than only cell-culture or structural data. "
            "<b style='color:#ffd60a;'>Protein structures by themselves are not a validation of biology — DNA sequences are.</b></p>"
            "</div>",
            unsafe_allow_html=True,
        )
    st.markdown("<hr class='dv'>", unsafe_allow_html=True)

    # ── Variant landscape ─────────────────────────────────────────
    sh("📊","Variant Landscape — Position × Pathogenicity")
    st.caption("Every ClinVar variant plotted by position. Red = pathogenic; yellow = VUS; dark = benign. A flat benign-only profile signals a potentially redundant protein.")
    landscape_fig = variant_landscape_chart(variants, protein_length, scored)
    if landscape_fig:
        st.plotly_chart(landscape_fig, use_container_width=True, config={"displayModeBar":False})
    else:
        st.caption("No positional data available for landscape plot.")
    st.markdown("<hr class='dv'>", unsafe_allow_html=True)

    n_crit = sum(1 for v in scored if v.get("ml_rank")=="CRITICAL")
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(mc(len(diseases),"Disease Links"),unsafe_allow_html=True)
    with c2: st.markdown(mc(summary.get("total",0),"ClinVar Variants","#4a90d9"),unsafe_allow_html=True)
    with c3: st.markdown(mc(summary.get("pathogenic",0),"Pathogenic","#ff2d55","linear-gradient(90deg,#ff2d55,#ff8080)"),unsafe_allow_html=True)
    with c4: st.markdown(mc(n_crit,"CRITICAL (ML)","#ff8c42","linear-gradient(90deg,#ff8c42,#ffb380)"),unsafe_allow_html=True)
    st.markdown(f"<div style='color:#1a4060;font-size:.78rem;margin:.4rem 0 .6rem;font-style:italic;'>🎯 {goal_context(active_goal)}</div>", unsafe_allow_html=True)
    st.markdown("<hr class='dv'>", unsafe_allow_html=True)

    cs, cd = st.columns([3,2], gap="large")
    with cs:
        sh("🏗️","AlphaFold Structure")
        if pdb:
            bf = parse_bfactors(pdb); avg = round(sum(bf.values())/max(len(bf),1),1)
            pct = round(sum(1 for b in bf.values() if b>=70)/max(len(bf),1)*100)
            n_sites = sum(1 for v in scored[:50] if v.get("start"))
            components.html(viewer_html(pdb, scored, 460), height=465, scrolling=False)
            st.markdown(f"<div style='color:#0e2840;font-size:.72rem;margin-top:3px;'>pLDDT avg: <b style='color:#3a7090;'>{avg}</b> · {pct}% reliable · <b style='color:#ff2d55;'>{n_sites}</b> variant sites</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='background:#040d18;border:1px dashed #0c2040;border-radius:12px;height:380px;display:flex;align-items:center;justify-content:center;'><div style='text-align:center;color:#0e2840;'><div style='font-size:2rem;'>🧬</div><div style='font-size:.82rem;margin-top:5px;'>AlphaFold unavailable — try UniProt accession</div></div></div>", unsafe_allow_html=True)

    with cd:
        sh("🔴","Disease Triage")
        all_d = []
        for d in diseases:
            sc2 = ds_scores.get(d["name"],.5); rk2 = "CRITICAL" if sc2>=.85 else "HIGH" if sc2>=.65 else "MEDIUM" if sc2>=.40 else "NEUTRAL"
            if any(k in (d["name"]+d.get("desc","")).lower() for k in ["cancer","carcinoma","leukemia"]) and rk2=="MEDIUM": rk2="HIGH"
            all_d.append({"name":d["name"],"desc":d.get("desc",""),"rk":rk2,"sc":sc2})
        for cn,cnt in summary.get("top_conds",{}).items():
            if cn not in [x["name"] for x in all_d]:
                sc2 = ds_scores.get(cn,.3); rk2 = "CRITICAL" if sc2>=.85 else "HIGH" if sc2>=.65 else "MEDIUM" if sc2>=.40 else "NEUTRAL"
                all_d.append({"name":cn,"desc":f"{cnt} ClinVar submissions","rk":rk2,"sc":sc2})
        all_d.sort(key=lambda x:(["CRITICAL","HIGH","MEDIUM","NEUTRAL"].index(x["rk"]),-x["sc"]))
        for d in all_d[:10]:
            bw = int(d["sc"]*100); clr = RANK_CLR[d["rk"]]; css_c = RANK_CSS[d["rk"]]
            st.markdown(f"<div style='display:flex;align-items:flex-start;gap:9px;background:#050e1c;border:1px solid #0c2040;border-radius:9px;padding:10px 12px;margin:4px 0;'><div style='flex-shrink:0;margin-top:1px;'><span class='badge {css_c}'>{d['rk']}</span></div><div style='flex:1;min-width:0;'><div style='color:#9ac0d8;font-size:.83rem;font-weight:600;'>{d['name']}</div><div style='color:#0e2840;font-size:.74rem;margin-top:2px;'>{d['desc'][:90]}</div><div style='height:3px;background:#07152a;border-radius:3px;overflow:hidden;margin-top:4px;'><div style='width:{bw}%;height:100%;background:{clr};'></div></div></div></div>", unsafe_allow_html=True)
        if summary.get("by_sig"):
            sd = summary["by_sig"]; clrs2 = ["#ff2d55","#ff8c42","#ffd60a","#4a90d9","#00c896","#6478ff","#a855f7","#1e4060"]
            fig = go.Figure(go.Pie(labels=list(sd.keys()),values=list(sd.values()),hole=.58,marker_colors=clrs2[:len(sd)],textfont_size=9))
            fig.update_layout(paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#1e4060",showlegend=True,legend=dict(font_size=9,bgcolor="#04080f"),margin=dict(t=0,b=0,l=0,r=0),height=185,annotations=[dict(text=f"<b>{summary.get('total',0)}</b>",x=.5,y=.5,font_size=13,font_color="#00e5ff",showarrow=False)])
            st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("🔮","Residue Hotspot Triage")
    if scored:
        rows = ""
        for v in scored[:50]:
            rk = v.get("ml_rank","NEUTRAL"); ml2 = v.get("ml",0)
            clr = RANK_CLR.get(rk,"#3a5a7a"); css_c = RANK_CSS.get(rk,"bN")
            bw = int(ml2*100); url = v.get("url","")
            name2 = (v.get("variant_name") or v.get("title","—"))[:55]
            sig2 = v.get("sig","—")[:35]; cond2 = v.get("condition","—")[:45]
            pos2 = str(v.get("start","—"))
            lnk = f"<a href='{url}' target='_blank' style='color:#2a6a8a;font-size:.72rem;'>↗</a>" if url else "—"
            row_bg = RANK_CLR.get(rk, '#3a5a7a') + '08'
            rows += (f"<tr style='background:{row_bg};'>"
                     f"<td><span class='badge {css_c}'>{rk}</span></td>"
                     f"<td style='color:#8ab0c8;font-size:.78rem;'>{name2}</td>"
                     f"<td style='color:#2a5070;text-align:center;'>{pos2}</td>"
                     f"<td style='color:#3a6080;font-size:.76rem;'>{sig2}</td>"
                     f"<td style='color:#2a5070;font-size:.74rem;'>{cond2}</td>"
                     f"<td><div style='display:flex;align-items:center;gap:5px;'><div style='width:34px;height:4px;background:#07152a;border-radius:3px;overflow:hidden;'><div style='width:{bw}%;height:100%;background:{clr};'></div></div><span style='color:{clr};font-size:.77rem;font-weight:700;'>{ml2:.2f}</span></div></td>"
                     f"<td style='text-align:center;'>{lnk}</td></tr>")
        st.markdown(f"<div style='overflow-x:auto;border-radius:10px;border:1px solid #0c2040;'><table class='pt2'><thead><tr><th>Rank</th><th>Variant</th><th>Pos</th><th>ClinVar Sig.</th><th>Condition</th><th>ML Score</th><th>Link</th></tr></thead><tbody>{rows}</tbody></table></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color:#0a1e30;font-size:.7rem;margin-top:4px;'>Top {min(50,len(scored))} of {len(scored)} · ML-ranked · Sensitivity: {sensitivity}/100</div>", unsafe_allow_html=True)

    # CSV panel if uploaded
    if st.session_state["csv_df"] is not None:
        st.markdown("<hr class='dv'>", unsafe_allow_html=True)
        sh("📂","Wet-Lab CSV Analysis")
        df = st.session_state["csv_df"]; csv_type = st.session_state["csv_type"]
        findings = analyse_csv(df, csv_type, active_goal, gene)
        for title, body in findings:
            st.markdown(f"<div class='csv-card'><h4>{title}</h4><p style='color:#2a5070;font-size:.82rem;'>{body}</p></div>", unsafe_allow_html=True)
        with st.expander("📋 View CSV data"):
            st.dataframe(df, use_container_width=True)

    render_citations(papers, 4)

# ══════════════════════════════════════════
# TAB 2 — CASE STUDY
# ══════════════════════════════════════════
with tab2:
    st.markdown(f"<div style='color:#1a4060;font-size:.78rem;margin-bottom:.8rem;font-style:italic;'>🎯 {goal_context(active_goal)}</div>", unsafe_allow_html=True)
    TKWS = {"Brain":["brain","neuron","cerebral","cortex"],"Liver":["liver","hepatic"],"Heart":["heart","cardiac","myocardium"],"Kidney":["kidney","renal"],"Lung":["lung","pulmonary"],"Blood":["blood","erythrocyte","platelet"],"Breast":["breast","mammary"],"Colon":["colon","colorectal","intestine"],"Prostate":["prostate"],"Skin":["skin","keratinocyte","melanocyte"],"Muscle":["muscle","skeletal"],"Pancreas":["pancreas","islet"]}
    c1, c2 = st.columns([1,1], gap="large")
    with c1:
        sh("🫀","Tissue Associations")
        tt = g_tissue(pdata)
        if tt: st.markdown(f"<div class='card'><p>{tt[:500]}</p></div>", unsafe_allow_html=True)
        blob = (tt+" "+g_func(pdata)+" "+" ".join(k.get("value","") for k in pdata.get("keywords",[]))).lower()
        tsc = {t:sum(1 for k in ks if k in blob) for t,ks in TKWS.items()}; tsc = {t:s for t,s in tsc.items() if s>0}
        if tsc:
            tsc = dict(sorted(tsc.items(),key=lambda x:-x[1])[:10])
            fig2 = go.Figure(go.Bar(y=list(tsc.keys()),x=list(tsc.values()),orientation="h",marker=dict(color=list(tsc.values()),colorscale=[[0,"#0c2040"],[.5,"#0d4080"],[1,"#00e5ff"]],cmin=0,cmax=max(tsc.values()))))
            fig2.update_layout(paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#1e4060",xaxis=dict(showgrid=False,zeroline=False,showticklabels=False),yaxis=dict(tickfont=dict(size=11,color="#3a6080")),margin=dict(l=0,r=0,t=5,b=0),height=160+len(tsc)*17)
            st.plotly_chart(fig2,use_container_width=True,config={"displayModeBar":False})
    with c2:
        sh("📍","Subcellular & PTM")
        for loc in g_sub(pdata): st.markdown(f"<div style='display:flex;align-items:center;gap:7px;margin:4px 0;'><span style='color:#00e5ff;font-size:.72rem;'>◆</span><span style='color:#3a6080;font-size:.82rem;'>{loc}</span></div>", unsafe_allow_html=True)
        ptm = next((c.get("texts",[{}])[0].get("value","") for c in pdata.get("comments",[]) if c.get("commentType")=="PTM"),"")
        if ptm: st.markdown(f"<div class='card' style='margin-top:.7rem;'><h4>PTMs</h4><p>{ptm[:350]}</p></div>", unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("🧬","Genomic Data")
    omim = g_xref(pdata,"MIM"); hgnc = g_xref(pdata,"HGNC"); ens = g_xref(pdata,"Ensembl")
    gd   = fetch_ncbi_gene(gene) if gene else {}
    c1,c2,c3 = st.columns(3)
    with c1: st.markdown(f"<div class='card'><h4>Protein</h4><p>UniProt: <b style='color:#00e5ff;'>{uid}</b><br>Length: <b>{pdata.get('sequence',{}).get('length','—')} aa</b><br>HGNC: {hgnc or '—'}</p></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='card'><h4>Genomic Location</h4><p>Chr: <b style='color:#00e5ff;'>{gd.get('chr','—')}</b><br>Cytoband: <b>{gd.get('map','—')}</b><br>Exons: <b>{gd.get('exons','—')}</b></p></div>", unsafe_allow_html=True)
    with c3:
        omim_link = f"<a href='https://omim.org/entry/{omim}' target='_blank' style='color:#3a90c4;'>{omim}</a>" if omim else "—"
        ncbi_link = f"<a href='{gd['link']}' target='_blank' style='color:#3a90c4;'>NCBI Gene ↗</a>" if gd.get("link") else ""
        up_link   = f"<a href='https://www.uniprot.org/uniprotkb/{uid}' target='_blank' style='color:#3a90c4;'>UniProt ↗</a>"
        st.markdown(f"<div class='card'><h4>Cross-References</h4><p>OMIM: {omim_link}<br>Ensembl: {ens[:20] if ens else '—'}<br>{up_link} {'· '+ncbi_link if ncbi_link else ''}</p></div>", unsafe_allow_html=True)
    if gd.get("summary"):
        with st.expander("📖 NCBI Gene Summary"): st.write(gd["summary"])

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("📡","GPCR Association")
    if g_gpcr(pdata):
        st.markdown("<div style='background:linear-gradient(135deg,#03111f,#04101c);border:1px solid #00e5ff22;border-radius:12px;padding:1rem 1.3rem;display:flex;gap:12px;align-items:flex-start;'><div style='font-size:1.9rem;'>📡</div><div><p style='color:#00e5ff;font-weight:700;font-size:.92rem;margin:0 0 3px;'>GPCR — Important / Piggybacked Target</p><p style='color:#1e4060;font-size:.82rem;margin:0;'>GPCRs represent ~34% of all FDA-approved drug targets. Consider biased agonism, allosteric modulation, and antibody-based approaches for therapeutic development.</p></div></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='background:#04080f;border:1px solid #0c2040;border-radius:9px;padding:.7rem 1rem;color:#0e2840;font-size:.82rem;'>Not classified as a GPCR in UniProt.</div>", unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("🔬","Disease Classification — Somatic vs Germline")
    somatic = set(); germline = set()
    for v in variants:
        origin = v.get("origin","").lower(); cond3 = v.get("condition","")
        if not cond3 or cond3=="Not specified": continue
        if "somatic" in origin or v.get("somatic"): somatic.add(cond3)
        elif any(x in origin for x in ["germline","inherited","de novo"]): germline.add(cond3)
        elif v.get("score",0)>=4: germline.add(cond3)
    cg, cs2 = st.columns(2)
    with cg:
        st.markdown(f"<div style='background:#03100a;border:1px solid #00c89628;border-radius:11px;padding:1rem;'><p style='color:#00c896;font-weight:700;font-size:.88rem;margin:0 0 3px;'>🧬 Germline ({len(germline)})</p><p style='color:#1a4030;font-size:.72rem;margin:0 0 6px;'>Heritable — all cells from birth</p>", unsafe_allow_html=True)
        for c3 in sorted(germline)[:7]: st.markdown(f"<div style='color:#2a6040;font-size:.78rem;margin:2px 0;'>◆ {c3[:65]}</div>", unsafe_allow_html=True)
        if not germline: st.markdown("<div style='color:#0d2a1a;font-size:.78rem;'>None found.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with cs2:
        st.markdown(f"<div style='background:#100308;border:1px solid #ff2d5528;border-radius:11px;padding:1rem;'><p style='color:#ff2d55;font-weight:700;font-size:.88rem;margin:0 0 3px;'>🔴 Somatic ({len(somatic)})</p><p style='color:#3a1020;font-size:.72rem;margin:0 0 6px;'>Acquired — specific cell populations</p>", unsafe_allow_html=True)
        for c3 in sorted(somatic)[:7]: st.markdown(f"<div style='color:#602030;font-size:.78rem;margin:2px 0;'>◆ {c3[:65]}</div>", unsafe_allow_html=True)
        if not somatic: st.markdown("<div style='color:#2a0810;font-size:.78rem;'>None found.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    for d in diseases[:5]:
        note_h = f"<p style='color:#ffd60a;font-size:.76rem;margin-top:3px;'>{d['note'][:150]}</p>" if d.get("note") else ""
        st.markdown(f"<div class='card'><h4>{d['name']}</h4><p>{d.get('desc','')[:260]}</p>{note_h}</div>", unsafe_allow_html=True)

    # ── Partner comparison ─────────────────────────────────────────
    if partner_info:
        st.markdown("<hr class='dv'>", unsafe_allow_html=True)
        sh("🔗","Interaction Partner — Genomic Integrity Comparison")
        st.caption("Do both proteins carry disease-causing variants? If only one does, the proposed interaction may not be a disease-relevant pathway.")
        p_gi = partner_info["gi"]; p_gene = partner_info["gene"]
        st.markdown(partner_html(gene, gi, p_gene, p_gi), unsafe_allow_html=True)
        # Side by side landscape
        p_cv  = st.session_state.get("partner_cv",{})
        p_vars= p_cv.get("variants",[]) if p_cv else []
        p_len = partner_info.get("uid","") and 1 or 1
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"<div style='color:#1e4060;font-size:.78rem;margin-bottom:.3rem;'><b style='color:#00e5ff;'>{gene}</b> variant landscape</div>", unsafe_allow_html=True)
            fig_a = variant_landscape_chart(variants, protein_length, scored)
            if fig_a: st.plotly_chart(fig_a, use_container_width=True, config={"displayModeBar":False})
        with col_b:
            st.markdown(f"<div style='color:#1e4060;font-size:.78rem;margin-bottom:.3rem;'><b style='color:#00e5ff;'>{p_gene}</b> variant landscape</div>", unsafe_allow_html=True)
            fig_b = variant_landscape_chart(p_vars, 1000, [])
            if fig_b: st.plotly_chart(fig_b, use_container_width=True, config={"displayModeBar":False})
    render_citations(papers, 4)

# ══════════════════════════════════════════
# TAB 3 — PROTEIN EXPLORER
# ══════════════════════════════════════════
with tab3:
    sh("🔬","Protein Explorer")
    st.caption("Click any residue sphere to inspect. Use mutation panel below to simulate substitutions.")
    if pdb:
        components.html(viewer_html(pdb, scored, 590), height=595, scrolling=False)
    else:
        st.info("No AlphaFold structure — search by UniProt accession for 3D view.")
    st.markdown("<hr class='dv'>", unsafe_allow_html=True)

    sh("🧫","Residue Mutation Analysis")
    seq = g_seq(pdata)
    if seq:
        bf = parse_bfactors(pdb) if pdb else {}
        pos_to_v = {}
        for sv in scored:
            try: pos_to_v[int(sv.get("start",0))] = sv
            except: pass
        csel, cmut = st.columns([1,2], gap="large")
        with csel:
            position = int(st.number_input("Residue position",1,max(len(seq),1),1,1,key="rpos"))
            aa = seq[position-1] if position<=len(seq) else "?"
            pl = bf.get(position)
            conf = ("Very High" if pl and pl>=90 else "Confident" if pl and pl>=70 else "Low" if pl and pl>=50 else "Very Low") if pl else "—"
            st.markdown(f"<div class='card'><h4>Residue {position} — {aa}</h4><p>{AA_NAMES.get(aa,'Unknown')}<br>pLDDT: <b style='color:#00e5ff;'>{f'{pl:.1f}' if pl else '—'}</b> ({conf})<br>Hydropathy: <b>{AA_HYDRO.get(aa,0):+.1f}</b></p></div>", unsafe_allow_html=True)
            vd = pos_to_v.get(position)
            if vd:
                rk2 = vd.get("ml_rank","NEUTRAL"); clr2 = RANK_CLR[rk2]; css2 = RANK_CSS[rk2]
                st.markdown(f"<div class='card' style='border-color:{clr2}33;'><h4 style='color:{clr2};'>⚠️ ClinVar Variant</h4><p>{vd.get('sig','—')}<br><small style='color:#0e2840;'>{vd.get('condition','')[:80]}</small></p></div>", unsafe_allow_html=True)
            else:
                st.success("No ClinVar variant at this position", icon="✅")
        with cmut:
            tb1, tb2 = st.tabs(["Properties","If Mutated →"])
            with tb1:
                SPECIAL = {"C":"Disulfide bonds · metal binding","G":"Flexible · helix-breaker","P":"Rigid · helix-breaker","H":"pH-sensitive (pKa≈6)","W":"Largest AA · UV-absorbing","Y":"Phosphorylation target","R":"DNA/RNA binding · +1","K":"Ubiquitination target","D":"Catalytic acid · −1","E":"Catalytic acid · −1"}
                for lbl, val in [("Amino acid",f"{aa} — {AA_NAMES.get(aa,'?')}"),("Hydropathy",f"{AA_HYDRO.get(aa,0):+.1f}"),("Charge",f"{AA_CHG.get(aa,0):+.1f}"),("Note",SPECIAL.get(aa,"—"))]:
                    st.markdown(f"<div style='display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #060f1c;'><span style='color:#0e2840;font-size:.79rem;'>{lbl}</span><span style='color:#5a8090;font-size:.79rem;font-weight:600;'>{val}</span></div>", unsafe_allow_html=True)
            with tb2:
                alts = [a for a in AA_NAMES.keys() if a != aa]
                alt = st.selectbox("Substitute with:", alts, key="alt_aa")
                sev = st.slider("Perturbation", 0.0, 1.0, 0.5, 0.05, key="sev")
                if bf:
                    pos_list = sorted(bf.keys()); window = 32
                    center = min(max(position,window+1), max(pos_list)-window)
                    dp = [p for p in pos_list if abs(p-center)<=window]
                    wt2 = [bf.get(p,70) for p in dp]
                    mt2 = [max(0, wt2[i]-sev*28*math.exp(-.5*((p-position)/6)**2)) for i,p in enumerate(dp)]
                    fig3 = go.Figure()
                    fig3.add_trace(go.Scatter(x=dp,y=wt2,mode="lines",name="Wild-type",line=dict(color="#00e5ff",width=2)))
                    fig3.add_trace(go.Scatter(x=dp,y=mt2,mode="lines",name=f"{aa}{position}{alt}",line=dict(color="#ff2d55",width=2,dash="dash")))
                    fig3.add_trace(go.Scatter(x=dp+dp[::-1],y=mt2+wt2[::-1],fill="toself",fillcolor="rgba(255,45,85,.07)",line=dict(color="rgba(0,0,0,0)"),showlegend=False))
                    fig3.add_vline(x=position,line_color="#ffd60a",line_dash="dot",annotation_text=f"p.{aa}{position}{alt}",annotation_font_color="#ffd60a",annotation_font_size=10)
                    fig3.update_layout(paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#1e4060",xaxis=dict(title="Position",gridcolor="#060f1c"),yaxis=dict(title="pLDDT",range=[0,100],gridcolor="#060f1c"),legend=dict(bgcolor="#04080f",font_size=10),margin=dict(t=8,b=28,l=28,r=8),height=220)
                    st.plotly_chart(fig3,use_container_width=True,config={"displayModeBar":False})
                hd = abs(AA_HYDRO.get(aa,0)-AA_HYDRO.get(alt,0)); cd = abs(AA_CHG.get(aa,0)-AA_CHG.get(alt,0))
                imps = []
                if alt=="*": imps.append(("🔴","Stop-gain","Premature termination → NMD → loss-of-function"))
                if hd>3: imps.append(("🟠","Large hydropathy shift",f"Δ{hd:.1f} — buried polarity change may destabilise core"))
                if cd>=1: imps.append(("⚡","Charge change",f"Δ{cd:+.0f} — disrupted electrostatic contacts"))
                if aa=="C": imps.append(("🔗","Cysteine lost","Disulfide bond or metal-chelation disruption"))
                if alt=="P": imps.append(("🔀","Proline introduced","Rigid backbone — helix/sheet may break"))
                if not imps: imps.append(("🟡","Conservative","Low physicochemical change — likely low impact"))
                for icon,title2,body2 in imps:
                    st.markdown(f"<div style='display:flex;gap:8px;background:#05101e;border:1px solid #0c2040;border-radius:8px;padding:8px 10px;margin:4px 0;'><span style='font-size:.95rem;flex-shrink:0;'>{icon}</span><div><div style='color:#5a8090;font-size:.78rem;font-weight:700;'>{title2}</div><div style='color:#0e2840;font-size:.74rem;margin-top:1px;'>{body2}</div></div></div>", unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("🗺️","Disease → Mutation → Genomic Implication")
    cond_map = defaultdict(list)
    for sv in scored[:30]:
        for c3 in sv.get("condition","Not specified").split(";"):
            c3 = c3.strip()
            if c3 and c3 != "Not specified": cond_map[c3].append(sv)
    for cond3, vlist in list(cond_map.items())[:10]:
        vlist_s = sorted(vlist, key=lambda x:-x.get("ml",0)); best = vlist_s[0].get("ml_rank","NEUTRAL")
        with st.expander(f"{cond3[:70]}  ({len(vlist_s)} variants)", expanded=(best in ("CRITICAL","HIGH"))):
            cv3, mech = st.columns([2,3])
            with cv3:
                st.markdown("**Top variants:**")
                for sv in vlist_s[:5]:
                    ml3=sv.get("ml",0); clr3=RANK_CLR.get(sv.get("ml_rank","NEUTRAL"),"#3a5a7a")
                    vn=(sv.get("variant_name") or sv.get("title","—"))[:45]; url3=sv.get("url","")
                    lnk3=f" [↗]({url3})" if url3 else ""
                    st.markdown(f"<div style='font-size:.78rem;margin:3px 0;'><span style='color:{clr3};font-weight:700;'>{ml3:.2f}</span> <span style='color:#4a7090;'>{vn}</span>{lnk3}</div>", unsafe_allow_html=True)
            with mech:
                st.markdown("**Likely mechanism:**")
                cl3=cond3.lower(); vn_all=" ".join(sv.get("variant_name","") for sv in vlist_s).lower(); mechs=[]
                if any(k in cl3 for k in ["cancer","carcinoma","tumor","leukemia","glioma"]): mechs+=["Oncogenic GoF or dominant-negative.","Somatic acquisition → clonal expansion."]
                if "stop" in vn_all or "ter" in vn_all: mechs.append("Stop-gain → truncated protein → haploinsufficiency.")
                if "frameshift" in vn_all: mechs.append("Frameshift → aberrant isoform → LoF.")
                if "missense" in vn_all: mechs.append("Missense → altered conformation / binding affinity.")
                if not mechs: mechs.append("Mechanism not fully characterised — functional assays needed.")
                for m in mechs: st.markdown(f"<div style='color:#1e4060;font-size:.78rem;margin:2px 0;'>• {m}</div>", unsafe_allow_html=True)
    render_citations(papers, 4)

# ══════════════════════════════════════════
# TAB 4 — EXPERIMENTS & THERAPY
# ══════════════════════════════════════════
with tab4:
    st.markdown(f"<div style='color:#1a4060;font-size:.78rem;margin-bottom:.8rem;font-style:italic;'>🎯 {goal_context(active_goal)}</div>", unsafe_allow_html=True)
    ptype = g_ptype(pdata); drugg = {"kinase":.9,"gpcr":.95,"transcription_factor":.35,"receptor":.8,"general":.5}.get(ptype,.5)
    n_crit2 = sum(1 for sv in scored if sv.get("ml_rank")=="CRITICAL"); n_high2 = sum(1 for sv in scored if sv.get("ml_rank")=="HIGH")
    priority = min(100, n_crit2*15 + n_high2*8 + len(scored)*.5 + drugg*20)
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(mc(n_crit2,"CRITICAL","#ff2d55","linear-gradient(90deg,#ff2d55,#ff8080)"),unsafe_allow_html=True)
    with c2: st.markdown(mc(n_high2,"HIGH","#ff8c42"),unsafe_allow_html=True)
    with c3: st.markdown(mc(f"{drugg:.0%}","Druggability","#00c896"),unsafe_allow_html=True)
    with c4: st.markdown(mc(int(priority),"Priority / 100","#00e5ff"),unsafe_allow_html=True)
    rec_msg = ("⚡ High priority. Recommend immediate CRISPR knock-in + biochemical validation." if priority>=70 else "🟡 Moderate priority. Start with Rosetta ΔΔG + low-cost cell assays." if priority>=40 else "🟢 Low priority. Insufficient evidence. Monitor ClinVar. Do not commit resources yet.")
    rec_clr = "#ff2d55" if priority>=70 else "#ffd60a" if priority>=40 else "#00c896"
    st.markdown(f"<div style='background:#04080f;border-left:3px solid {rec_clr};border-radius:0 9px 9px 0;padding:.8rem 1.2rem;margin:.7rem 0;'><p style='color:#4a7090;margin:0;font-size:.86rem;'>{rec_msg}</p></div>", unsafe_allow_html=True)

    if assay:
        st.markdown("<hr class='dv'>", unsafe_allow_html=True); sh("🧫","Assay Next Steps")
        tl4 = assay.lower()
        for kws4,title4,body4 in [(["western","wb"],"Western Blot → Follow Up","CHX chase (protein half-life) + SILAC/TMT-MS proteomics for orthogonal validation."),(["crispr","knockout"],"CRISPR KO → Follow Up","Rescue: re-introduce WT + each variant. RNA-seq KO vs WT. Xenograft if oncogene confirmed."),(["flow","facs"],"Flow Cytometry → Follow Up","WB for caspase 3/7 + Bcl-2. Add CDK inhibitor comparison for cell cycle arrest."),(["co-ip","binding"],"Interaction Data → Follow Up","HDX-MS to map interface. Cryo-EM for structure. Design peptide/small-molecule disruptors.")]:
            if any(k in tl4 for k in kws4): st.markdown(f"<div class='card'><h4>{title4}</h4><p>{body4}</p></div>", unsafe_allow_html=True)

    # CSV in experiments
    if st.session_state["csv_df"] is not None:
        st.markdown("<hr class='dv'>", unsafe_allow_html=True); sh("📂","CSV-Informed Experimental Strategy")
        df4 = st.session_state["csv_df"]; csv_type4 = st.session_state["csv_type"]
        findings4 = analyse_csv(df4, csv_type4, active_goal, gene)
        for t4,b4 in findings4:
            st.markdown(f"<div class='csv-card'><h4>{t4}</h4><p style='color:#2a5070;font-size:.81rem;'>{b4}</p></div>", unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    COST_MAP = {"Free":("#00c896","rgba(0,200,150,.08)"),"$":("#4a90d9","rgba(74,144,217,.08)"),"$$":("#ffd60a","rgba(255,214,10,.08)"),"$$$":("#ff8c42","rgba(255,140,66,.08)"),"$$$$":("#ff2d55","rgba(255,45,85,.08)")}
    cost_labels = {"Free":"No cost","$":"<$1K","$$":"$1–10K","$$$":"$10–50K","$$$$":"$50K+"}
    cc = st.columns(5)
    for (sym,(clr,bg)),col in zip(COST_MAP.items(),cc):
        col.markdown(f"<div style='background:{bg};border:1px solid {clr}33;border-radius:8px;padding:5px;text-align:center;'><div style='color:{clr};font-weight:800;'>{sym}</div><div style='color:{clr}88;font-size:.68rem;'>{cost_labels[sym]}</div></div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    EXPS = [
        ("🧬","ADP-Glo Kinase / Enzyme Assay","$$","3–6 wks","Measure gain/loss of enzymatic activity for variant proteins.",["Express WT & variants (E. coli/baculovirus).","Purify via His-tag + SEC.","ADP-Glo™ kinase reaction.","Compare Km/Vmax WT vs variants.","Triplicate; SEM ≤10%."],"Catalytic-residue variants (D-loop, activation loop).","Disordered linkers / pLDDT <50.","Quantitative activity ratio."),
        ("🧬","Co-IP / AP-MS","$$$","4–8 wks","Map interaction network changes per variant.",["3×FLAG or GFP tag in HEK293T.","Native NP-40 lysis.","Anti-tag pulldown + Protein A/G beads.","TMT-labelled MS or SDS-PAGE.","Reverse Co-IP to validate."],"Interface residues (AlphaFold-Multimer).","Splice variants with identical domains.","Interaction rewiring map."),
        ("🧬","Thermal Shift Assay (TSA)","$","1–2 wks","Screen binders and variant folding stability.",["Purify WT & variants (0.5 mg/mL).","96-well + SYPRO Orange (5×).","Ramp 25→95°C at 1°C/min.","Boltzmann fit → Tm.","Flag ΔTm ≥1°C hits."],"Destabilising missense in structured domains.","IDRs — no Tm signal.","ΔTm per variant; compound leads."),
        ("🔬","CRISPR-Cas9 Knock-in","$$$","6–12 wks","Introduce patient-like variants into endogenous locus.",["Design sgRNAs (CRISPOR).","SpCas9 RNP + ssODN HDR donor.","Screen ≥50 colonies (NGS).","Validate WB + IF.","Phenotypic assays on confirmed clones."],"ClinVar P/LP + ML ≥0.75.","VUS <2 star review.","Isogenic cell lines; gold-standard evidence."),
        ("🔬","Luciferase Reporter","$","1–3 wks","Quantify transcriptional activity changes.",["Clone 1 kb target promoter into pGL4.","Transfect WT or mutant TF + Renilla.","Read ratio at 48h; ≥3 independent runs."],"DNA-binding or transactivation domain variants.","N-terminal disordered segments.","Fold-change in activation/repression."),
        ("🔬","Cell Viability / CellTiter-Glo","$","1–2 wks","Assess oncogenic or tumour-suppressive phenotype.",["Seed 5,000 cells/well.","Express variant for 72h.","CellTiter-Glo luminescence.","Normalise to vehicle; compute IC₅₀."],"GoF oncogenic CRITICAL tier variants.","Benign variants.","Viability % vs WT."),
        ("🧫","AlphaFold + Rosetta ΔΔG","Free","1–3 days","Rank missense variants in silico before wet lab.",["Download AF2 PDB.","FastRelax on WT.","MutateResidue per variant.","Flag ΔΔG ≥2 REU.","Cross-reference ML scores."],"All missense in structured domains (pLDDT ≥70).","IDRs.","Ranked list — eliminates ~50% before any wet lab."),
        ("🧫","SPR / Biacore","$$$","2–4 wks","Binding kinetics WT vs mutant.",["Immobilise ligand on CM5 chip.","Flow analyte at 5 concentrations.","Fit 1:1 Langmuir → KD, kon, koff."],"Interface variants (charge/hydrophobicity).","Variants >15 Å from binding site.","KD shift per variant."),
        ("🐭","Xenograft Mouse Model","$$$$","8–16 wks","Test tumorigenic potential in vivo.",["Inject 1×10⁶ knock-in cells SC in NSG mice.","Monitor tumour volume twice weekly.","H&E + IHC at endpoint.","Log-rank test WT vs mutant."],"Variants with in vitro proliferation data.","VUS without prior in vitro validation.","In vivo growth curves."),
        ("💊","Small Molecule HTS","$$$$","6–12 mo","Identify rescue or inhibitor compounds.",["HTS-compatible assay.","Screen at 10 µM.","Counter-screen cytotoxicity.","IC₅₀ top 50 hits. SAR top 5."],"CRITICAL/HIGH variants with druggable pockets.","IDPs.","Lead compound series."),
        ("💊","PROTAC / Degradation","$$$$","6–12 mo","Degrade undruggable GoF mutant proteins.",["Warhead + E3-recruiter (CRBN/VHL).","Synthesise 10–20 candidates.","DC₅₀ in target cell line.","Proteome-wide TMT-MS selectivity."],"GoF resistant to catalytic inhibition.","Tumour suppressor LoF.","Selective degrader DC₅₀ <100 nM."),
    ]
    for icon,name,cost,timeline,purpose,protocol,focus,neglect,outcome in EXPS:
        clr_e, bg_e = COST_MAP.get(cost,("#3a6080","rgba(58,96,128,.08)"))
        with st.expander(f"{icon} {name}  ·  {cost}  ·  ⏱ {timeline}"):
            c_l, c_r = st.columns([3,2])
            with c_l:
                st.markdown(f"**Purpose:** {purpose}")
                st.markdown("**Protocol:**")
                for i,step in enumerate(protocol,1): st.markdown(f"{i}. {step}")
                st.markdown(f"**Outcome:** {outcome}")
            with c_r:
                st.markdown(f"<div style='background:{bg_e};border:1px solid {clr_e}33;border-radius:10px;padding:.9rem;'><div style='color:{clr_e};font-weight:800;font-size:.95rem;'>{cost}</div><div style='color:{clr_e}88;font-size:.76rem;margin-bottom:8px;'>⏱ {timeline}</div><div style='color:#00c896;font-size:.76rem;font-weight:700;margin-bottom:2px;'>✅ Focus on:</div><div style='color:#1a5030;font-size:.74rem;margin-bottom:7px;'>{focus}</div><div style='color:#ff8c42;font-size:.76rem;font-weight:700;margin-bottom:2px;'>❌ Deprioritise:</div><div style='color:#5a2a10;font-size:.74rem;'>{neglect}</div></div>", unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("🧬","Genomic Verdict — Should You Pursue This Protein?")
    gi_clr4 = gi["color"]
    st.markdown(
        f"<div class='{gi['css']}'>"
        f"<div style='display:flex;align-items:flex-start;gap:1rem;'>"
        f"<div style='font-size:2.5rem;flex-shrink:0;'>{gi['icon']}</div>"
        f"<div>"
        f"<div style='color:{gi_clr4};font-weight:800;font-size:1rem;margin-bottom:4px;'>{gi['verdict']}: {gi['label']}</div>"
        f"<div style='color:#3a6080;font-size:.84rem;line-height:1.6;margin-bottom:.6rem;'>{gi['explanation']}</div>"
        f"<div style='color:{gi_clr4};font-weight:700;font-size:.86rem;'>"
        f"{'🧬 Genetics says: STOP. Commit no further resources until disease-variant evidence exists in ClinVar.' if gi['pursue']=='deprioritise' else '🧬 Genetics says: PROCEED. Human disease genetics validates this as a real target.' if gi['pursue'] in ['prioritise','proceed'] else '🧬 Genetics says: BE SELECTIVE. Work only with confirmed P/LP variants.'}"
        f"</div></div></div>"
        f"<div style='margin-top:.8rem;font-size:.78rem;color:#0e2840;font-style:italic;border-top:1px solid {gi_clr4}22;padding-top:.6rem;'>"
        f"Principle: Protein structures by themselves are not a validation of biology. DNA sequences are. "
        f"Genomic variants that cause disease define the true importance of a protein — not citation count, "
        f"not the number of solved structures, not in vitro binding data. (Lamarckism and Lysenkoism "
        f"failed for the same reason: ignoring genetic evidence.)"
        f"</div></div>",
        unsafe_allow_html=True,
    )
    if partner_info:
        st.markdown("<br>", unsafe_allow_html=True)
        p_gi4 = partner_info["gi"]; p_gene4 = partner_info["gene"]
        st.markdown(partner_html(gene, gi, p_gene4, p_gi4), unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True); sh("🗺️","Decision Framework")
    counts4 = {r:sum(1 for sv in scored if sv.get("ml_rank")==r) for r in RANK_CLR}
    labels4 = [r for r in RANK_CLR if counts4[r]>0]; values4 = [counts4[r] for r in labels4]; clrs4 = [RANK_CLR[r] for r in labels4]
    if labels4:
        fig4 = go.Figure(go.Funnel(y=labels4,x=values4,textinfo="value+percent initial",marker=dict(color=clrs4),textfont=dict(color="white",size=12)))
        fig4.update_layout(paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#1e4060",height=270,margin=dict(t=5,b=5,l=70,r=5))
        st.plotly_chart(fig4,use_container_width=True,config={"displayModeBar":False})
    for rank,clr,rec in [("CRITICAL","#ff2d55","Immediate wet-lab validation now."),("HIGH","#ff8c42","Functional assay + ΔΔG. In vivo only after in vitro phenotype."),("MEDIUM","#ffd60a","In silico + low-cost assay. Hold before animal work."),("NEUTRAL","#3a5a7a","Deprioritise. Monitor ClinVar. No wet-lab spend.")]:
        st.markdown(f"<div style='display:flex;gap:9px;align-items:center;background:#04080f;border-left:3px solid {clr};border-radius:0 8px 8px 0;padding:8px 12px;margin:4px 0;'><span class='badge {RANK_CSS[rank]}'>{rank}</span><span style='color:#4a7090;font-size:.83rem;'>{rec}</span></div>", unsafe_allow_html=True)
    render_citations(papers, 5)

# ─── Footer ───────────────────────────────────────────────────────
st.markdown("<hr class='dv'><p style='text-align:center;color:#050f1c;font-size:.7rem;'>Protellect · UniProt · ClinVar · AlphaFold · PubMed · NCBI · Not a substitute for expert clinical judgment.</p>", unsafe_allow_html=True)
