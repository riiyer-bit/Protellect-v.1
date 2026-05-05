from __future__ import annotations
# ═══════════════════════════════════════════════════════════════════
#  Protellect — single-file build  (no local imports)
#  Run: streamlit run app.py
# ═══════════════════════════════════════════════════════════════════

import re, time, json, math
from collections import Counter, defaultdict

import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# ──────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Protellect",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────
# GLOBAL CSS
# ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;}
.stApp{background:#04080f;}
[data-testid="stSidebar"]{background:#05101f!important;border-right:1px solid #0c2040;}
.proto-header{background:linear-gradient(135deg,#04080f,#050e20,#041527);border:1px solid #0c2040;
  border-radius:16px;padding:1.8rem 2.2rem 1.4rem;margin-bottom:1.4rem;position:relative;overflow:hidden;}
.proto-header::after{content:'';position:absolute;bottom:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,#00e5ff44,transparent);}
.proto-title{font-size:2.4rem;font-weight:800;letter-spacing:-1px;margin:0;
  background:linear-gradient(90deg,#00e5ff,#6478ff,#00e5ff);background-size:200%;
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  animation:sh 4s linear infinite;}
.proto-sub{color:#2a5070;font-size:0.9rem;margin:0.3rem 0 0;}
@keyframes sh{0%{background-position:0%}100%{background-position:200%}}
.mc{background:linear-gradient(145deg,#06111e,#040d18);border:1px solid #0c2040;
  border-radius:12px;padding:1rem 1.2rem;text-align:center;position:relative;overflow:hidden;
  transition:border-color .3s,transform .2s;}
.mc:hover{border-color:#00e5ff33;transform:translateY(-2px);}
.mc::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:var(--acc,linear-gradient(90deg,#00e5ff,#6478ff));}
.mv{font-size:1.9rem;font-weight:800;line-height:1;color:var(--clr,#00e5ff);}
.ml{font-size:0.7rem;color:#1e4060;margin-top:4px;text-transform:uppercase;letter-spacing:.7px;}
.card{background:#06111e;border:1px solid #0c2040;border-radius:12px;
  padding:1.1rem 1.4rem;margin-bottom:.8rem;transition:border-color .2s;}
.card:hover{border-color:#1a3a5f;}
.card h4{color:#00e5ff;font-size:.9rem;font-weight:700;margin:0 0 .4rem;}
.card p{color:#5a8090;font-size:.84rem;line-height:1.6;margin:0;}
.badge{display:inline-block;padding:2px 10px;border-radius:18px;font-size:.68rem;font-weight:800;letter-spacing:.4px;}
.bC{background:rgba(255,45,85,.12);color:#ff2d55;border:1px solid #ff2d5540;}
.bH{background:rgba(255,140,66,.12);color:#ff8c42;border:1px solid #ff8c4240;}
.bM{background:rgba(255,214,10,.1);color:#ffd60a;border:1px solid #ffd60a35;}
.bN{background:rgba(58,90,122,.2);color:#3a6080;border:1px solid #1e4060;}
.divider{border:none;border-top:1px solid #091830;margin:1.4rem 0;}
.sh{display:flex;align-items:center;gap:9px;margin:0 0 .9rem;
  padding-bottom:7px;border-bottom:1px solid #0c2040;}
.sh h3{color:#b0d0f0;font-size:.95rem;font-weight:700;margin:0;}
.stTabs [data-baseweb="tab-list"]{background:transparent;gap:3px;border-bottom:1px solid #0c2040;}
.stTabs [data-baseweb="tab"]{background:transparent;border-radius:8px 8px 0 0;
  padding:7px 14px;color:#1e4060!important;font-weight:600;font-size:.86rem;}
.stTabs [aria-selected="true"]{background:#06111e!important;color:#00e5ff!important;
  border-bottom:2px solid #00e5ff!important;}
.stButton>button{background:linear-gradient(135deg,#003d55,#003068)!important;
  color:#00e5ff!important;border:1px solid #00e5ff25!important;border-radius:8px!important;
  font-weight:700!important;transition:all .2s!important;}
.stButton>button:hover{border-color:#00e5ff66!important;
  box-shadow:0 4px 18px rgba(0,229,255,.18)!important;}
.stTextInput input,.stTextArea textarea{background:#040d18!important;
  border:1px solid #0c2040!important;color:#c0d8f8!important;border-radius:8px!important;}
details{border:1px solid #0c2040!important;border-radius:10px!important;background:#05101e!important;}
.sb-t{font-size:.66rem;font-weight:700;color:#163050;text-transform:uppercase;
  letter-spacing:1px;margin:.9rem 0 .4rem;padding-bottom:3px;border-bottom:1px solid #0c2040;}
.cite{border-left:2px solid #00e5ff33;padding:7px 11px;margin:4px 0;
  background:#040e1c;border-radius:0 8px 8px 0;}
.cite a{color:#3a90c4;text-decoration:none;font-size:.8rem;}
.cite a:hover{color:#00e5ff;}
.cm{color:#1a4060;font-size:.72rem;margin-top:2px;}
.prow{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #060f1c;}
.pk{color:#1e4060;font-size:.8rem;}.pv{color:#7aA0c0;font-size:.8rem;font-weight:600;}
.imp{display:flex;gap:9px;background:#05101e;border:1px solid #0c2040;
  border-radius:8px;padding:9px 11px;margin:4px 0;}
.imp-t{color:#7aa0c0;font-size:.8rem;font-weight:700;}
.imp-b{color:#1e4060;font-size:.76rem;margin-top:2px;}
.dr{display:flex;align-items:flex-start;gap:10px;background:#050e1c;
  border:1px solid #0c2040;border-radius:9px;padding:11px 13px;margin:5px 0;
  transition:background .2s;}
.dr:hover{background:#061220;}
.dn{color:#b0ccec;font-size:.85rem;font-weight:600;}
.dd{color:#1e4060;font-size:.76rem;margin-top:2px;line-height:1.5;}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────
# CONSTANTS & LOOKUPS
# ──────────────────────────────────────────────────────────────────
SIG_SCORE = {
    "pathogenic":5,"likely pathogenic":4,"pathogenic/likely pathogenic":4,
    "risk factor":3,"uncertain significance":2,"conflicting interpretations":2,
    "likely benign":1,"benign":0,"benign/likely benign":0,"not provided":-1,
}
AA_HYDRO = {"A":1.8,"R":-4.5,"N":-3.5,"D":-3.5,"C":2.5,"Q":-3.5,"E":-3.5,
            "G":-0.4,"H":-3.2,"I":4.5,"L":3.8,"K":-3.9,"M":1.9,"F":2.8,
            "P":-1.6,"S":-0.8,"T":-0.7,"W":-0.9,"Y":-1.3,"V":4.2,"*":-10}
AA_CHG   = {"R":1,"K":1,"H":0.5,"D":-1,"E":-1}
AA_NAMES = {"A":"Alanine","R":"Arginine","N":"Asparagine","D":"Aspartate","C":"Cysteine",
            "Q":"Glutamine","E":"Glutamate","G":"Glycine","H":"Histidine","I":"Isoleucine",
            "L":"Leucine","K":"Lysine","M":"Methionine","F":"Phenylalanine","P":"Proline",
            "S":"Serine","T":"Threonine","W":"Tryptophan","Y":"Tyrosine","V":"Valine"}
RANK_CLR = {"CRITICAL":"#ff2d55","HIGH":"#ff8c42","MEDIUM":"#ffd60a","NEUTRAL":"#3a5a7a"}
RANK_BG  = {"CRITICAL":"#1a0510","HIGH":"#1a0f00","MEDIUM":"#1a1400","NEUTRAL":"#060e18"}
RANK_CSS = {"CRITICAL":"bC","HIGH":"bH","MEDIUM":"bM","NEUTRAL":"bN"}

ESEARCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

# ──────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────────
def badge(rank):
    css = RANK_CSS.get(rank,"bN")
    return f"<span class='badge {css}'>{rank}</span>"

def sh(icon, title):
    st.markdown(f"<div class='sh'><span style='font-size:1.2rem'>{icon}</span><h3>{title}</h3></div>", unsafe_allow_html=True)

def mc(val, label, clr="#00e5ff", acc=None):
    a = acc or f"linear-gradient(90deg,{clr},{clr}88)"
    return f"<div class='mc' style='--clr:{clr};--acc:{a};'><div class='mv'>{val}</div><div class='ml'>{label}</div></div>"

def score_rank(s):
    if s>=5: return "CRITICAL"
    if s>=4: return "HIGH"
    if s>=2: return "MEDIUM"
    return "NEUTRAL"

def ml_rank(ml):
    if ml>=.85: return "CRITICAL"
    if ml>=.65: return "HIGH"
    if ml>=.40: return "MEDIUM"
    return "NEUTRAL"

def parse_aa(name):
    aa3 = {"Ala":"A","Arg":"R","Asn":"N","Asp":"D","Cys":"C","Gln":"Q","Glu":"E","Gly":"G",
           "His":"H","Ile":"I","Leu":"L","Lys":"K","Met":"M","Phe":"F","Pro":"P","Ser":"S",
           "Thr":"T","Trp":"W","Tyr":"Y","Val":"V","Ter":"*","Xaa":"X"}
    m = re.search(r"p\.([A-Z][a-z]{2})\d+([A-Z][a-z]{2}|Ter|\*)", name or "")
    if m: return aa3.get(m.group(1),"?"), aa3.get(m.group(2),"?")
    return "?","?"

# ──────────────────────────────────────────────────────────────────
# API FUNCTIONS
# ──────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_uniprot(query):
    base = "https://rest.uniprot.org/uniprotkb"
    acc_pat = re.compile(r"^[OPQ][0-9][A-Z0-9]{3}[0-9]$|^[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$", re.I)
    if acc_pat.match(query.strip()):
        r = requests.get(f"{base}/{query.strip().upper()}", headers={"Accept":"application/json"}, timeout=20)
        r.raise_for_status(); return r.json()
    params = {"query":f"(gene:{query} OR protein_name:{query}) AND reviewed:true",
              "format":"json","size":1,
              "fields":"accession,gene_names,protein_name,organism_name,length,cc_disease,"
                       "cc_tissue_specificity,cc_function,keyword,cc_subcellular_location,"
                       "xref_omim,xref_hgnc,sequence,ft_variant,cc_interaction,cc_ptm,feature"}
    r = requests.get(f"{base}/search", params=params, headers={"Accept":"application/json"}, timeout=20)
    r.raise_for_status()
    results = r.json().get("results",[])
    if not results:
        params["query"] = query
        r = requests.get(f"{base}/search", params=params, headers={"Accept":"application/json"}, timeout=20)
        r.raise_for_status(); results = r.json().get("results",[])
    if not results: raise ValueError(f"No UniProt entry for '{query}'.")
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
    for i in range(0,len(ids),100):
        try:
            r2 = requests.get(ESUMMARY, params={"db":"clinvar","id":",".join(ids[i:i+100]),"retmode":"json"}, timeout=30)
            r2.raise_for_status(); data = r2.json().get("result",{})
            for uid in data.get("uids",[]):
                e = data.get(uid,{}); gc = e.get("germline_classification",{})
                sig = gc.get("description","Not provided")
                sc  = SIG_SCORE.get(sig.lower().strip(),0)
                traits = [t.get("trait_name","") for t in e.get("trait_set",{}).get("trait",[]) if t.get("trait_name")]
                locs = e.get("location_list",[{}]); vset = e.get("variation_set",[{}])
                variants.append({
                    "uid":uid,"title":e.get("title",""),
                    "variant_name":vset[0].get("variation_name","") if vset else "",
                    "sig":sig,"score":sc,"rank":score_rank(sc),
                    "condition":"; ".join(traits) if traits else "Not specified",
                    "origin":e.get("origin",{}).get("origin",""),
                    "review":gc.get("review_status",""),
                    "start":locs[0].get("start","") if locs else "",
                    "url":f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{e.get('variation_id',uid)}/",
                    "somatic":bool(e.get("somatic_classifications",{})),
                })
        except: pass
        time.sleep(0.1)
    variants.sort(key=lambda x:-x["score"])
    sigs  = Counter(v["sig"] for v in variants)
    ranks = Counter(v["rank"] for v in variants)
    conds = Counter()
    for v in variants:
        for c in v["condition"].split(";"):
            c=c.strip()
            if c and c!="Not specified": conds[c]+=1
    return {"variants":variants,"summary":{"total":len(variants),"by_sig":dict(sigs.most_common(8)),
            "by_rank":dict(ranks),"top_conds":dict(conds.most_common(10)),
            "pathogenic":sum(1 for v in variants if v["score"]>=4),
            "vus":sum(1 for v in variants if v["score"]==2)}}

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_pdb(uid):
    if not uid: return ""
    try:
        r = requests.get(f"https://alphafold.ebi.ac.uk/api/prediction/{uid}", timeout=15)
        if r.status_code==404: return ""
        r.raise_for_status(); entries=r.json()
        if not entries: return ""
        r2 = requests.get(entries[0].get("pdbUrl",""), timeout=30)
        r2.raise_for_status(); return r2.text
    except: return ""

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_papers(gene, n=6):
    try:
        r = requests.get(ESEARCH, params={"db":"pubmed","term":gene,"retmax":n*2,"retmode":"json","sort":"relevance"}, timeout=15)
        r.raise_for_status(); ids=r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return []
        r2 = requests.get(ESUMMARY, params={"db":"pubmed","id":",".join(ids),"retmode":"json"}, timeout=15)
        r2.raise_for_status(); data=r2.json().get("result",{})
        papers=[]
        for uid in data.get("uids",[]):
            e=data.get(uid,{})
            authors=", ".join(a.get("name","") for a in e.get("authors",[])[:3])
            if len(e.get("authors",[]))>3: authors+=" et al."
            pt=[p.get("value","").lower() for p in e.get("pubtype",[])]
            sc=(3 if "review" in pt else 0)+(2 if e.get("pubdate","")[:4]>="2020" else 0)
            papers.append({"pmid":uid,"title":e.get("title","No title"),"authors":authors,
                           "journal":e.get("source",""),"year":e.get("pubdate","")[:4],
                           "url":f"https://pubmed.ncbi.nlm.nih.gov/{uid}/","score":sc,"pt":pt})
        return sorted(papers,key=lambda x:-x["score"])[:n]
    except: return []

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_ncbi_gene(symbol):
    try:
        r = requests.get(ESEARCH, params={"db":"gene","term":f"{symbol}[gene name] AND Homo sapiens[organism] AND alive[property]","retmax":1,"retmode":"json"}, timeout=15)
        r.raise_for_status(); ids=r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return {}
        gid=ids[0]
        r2=requests.get(ESUMMARY, params={"db":"gene","id":gid,"retmode":"json"}, timeout=15)
        r2.raise_for_status(); e=r2.json().get("result",{}).get(gid,{})
        gi=e.get("genomicinfo",[{}])[0] if e.get("genomicinfo") else {}
        return {"id":gid,"full":e.get("description",""),"chr":e.get("chromosome",""),
                "map":e.get("maplocation",""),"summary":e.get("summary",""),
                "start":gi.get("chrstart",""),"stop":gi.get("chrstop",""),"exons":gi.get("exoncount",""),
                "link":f"https://www.ncbi.nlm.nih.gov/gene/{gid}"}
    except: return {}

def parse_bfactors(pdb):
    out={}
    for line in pdb.splitlines():
        if line.startswith(("ATOM","HETATM")):
            try:
                rn=int(line[22:26]); bf=float(line[60:66]); an=line[12:16].strip()
                if an=="CA": out[rn]=bf
            except: pass
    return out

def ml_score(variants):
    out=[]
    for v in variants:
        name=v.get("variant_name","") or v.get("title","")
        orig,alt=parse_aa(name)
        hd=abs(AA_HYDRO.get(orig,0)-AA_HYDRO.get(alt,0))
        cd=abs(AA_CHG.get(orig,0)-AA_CHG.get(alt,0))
        stop=float(alt=="*"); frame=float("frame" in name.lower())
        stars={"practice guideline":1,"reviewed by expert panel":.9,
               "criteria provided, multiple submitters":.7,
               "criteria provided, single submitter":.5}.get(v.get("review","").lower(),.2)
        base=v.get("score",0)/5.0
        ml=min(1.0,base*.5+stop*.25+frame*.15+(hd/10)*.05+cd*.03+stars*.02)
        vc=dict(v); vc["ml"]=round(float(ml),3); vc["ml_rank"]=ml_rank(ml)
        out.append(vc)
    return sorted(out,key=lambda x:-x["ml"])

# UniProt helpers
def g_gene(p):
    try: return p["genes"][0]["geneName"]["value"]
    except: return p.get("primaryAccession","?")
def g_name(p):
    try: return p["proteinDescription"]["recommendedName"]["fullName"]["value"]
    except: return "Unknown protein"
def g_seq(p): return p.get("sequence",{}).get("value","")
def g_diseases(p):
    out=[]
    for c in p.get("comments",[]):
        if c.get("commentType")=="DISEASE":
            d=c.get("disease",{}); omim=""
            for x in d.get("diseaseCrossReference",{}) if isinstance(d.get("diseaseCrossReference"),list) else [d.get("diseaseCrossReference",{})]:
                if isinstance(x,dict) and x.get("database")=="MIM": omim=x.get("id","")
            out.append({"name":d.get("diseaseId",d.get("diseaseAcronym","Unknown")),
                        "desc":d.get("description",""),"omim":omim,
                        "note":(c.get("note",{}).get("texts",[{}])[0].get("value","") if c.get("note") else "")})
    return out
def g_sub(p):
    locs=[]
    for c in p.get("comments",[]):
        if c.get("commentType")=="SUBCELLULAR LOCATION":
            for e in c.get("subcellularLocations",[]):
                v=e.get("location",{}).get("value","")
                if v: locs.append(v)
    return list(dict.fromkeys(locs))
def g_tissue(p):
    for c in p.get("comments",[]):
        if c.get("commentType")=="TISSUE SPECIFICITY":
            t=c.get("texts",[]);
            if t: return t[0].get("value","")
    return ""
def g_func(p):
    for c in p.get("comments",[]):
        if c.get("commentType")=="FUNCTION":
            t=c.get("texts",[])
            if t: return t[0].get("value","")
    return ""
def g_xref(p,db):
    for x in p.get("uniProtKBCrossReferences",[]):
        if x.get("database")==db: return x.get("id","")
    return ""
def g_gpcr(p):
    kws=[k.get("value","").lower() for k in p.get("keywords",[])]
    return any(x in " ".join(kws) for x in ["gpcr","g protein","rhodopsin","adrenergic"])
def g_ptype(p):
    kws=[k.get("value","").lower() for k in p.get("keywords",[])]
    if any("kinase" in k for k in kws): return "kinase"
    if any("gpcr" in k or "g protein" in k for k in kws): return "gpcr"
    if any("transcription" in k for k in kws): return "transcription_factor"
    if any("receptor" in k for k in kws): return "receptor"
    return "general"

# Shared renderers
def render_citations(papers,n=4):
    if not papers: return
    st.markdown("<div style='color:#163050;font-size:.68rem;text-transform:uppercase;letter-spacing:.8px;margin:.8rem 0 .3rem;'>📚 Supporting Literature</div>",unsafe_allow_html=True)
    for p in papers[:n]:
        pt=" ".join(f"<span style='background:#08162a;color:#1e5070;font-size:.66rem;padding:1px 6px;border-radius:8px;margin-left:3px;'>{t.title()}</span>" for t in p.get("pt",[])[:2])
        st.markdown(f"<div class='cite'><a href='{p['url']}' target='_blank'>{p['title'][:110]}</a>{pt}<div class='cm'>{p['authors']} · {p['journal']} · {p['year']} · PMID {p['pmid']}</div></div>",unsafe_allow_html=True)

def render_triage_table(top):
    if not top: st.info("No variant data."); return
    rows=""
    for v in top[:50]:
        rk=v.get("ml_rank","NEUTRAL"); ml=v.get("ml",0)
        clr=RANK_CLR.get(rk,"#3a5a7a"); bg=RANK_BG.get(rk,"#060e18")
        url=v.get("url",""); name=(v.get("variant_name") or v.get("title","—"))[:55]
        sig=v.get("sig","—")[:35]; cond=v.get("condition","—")[:45]
        pos=str(v.get("start","—"))
        lnk=f"<a href='{url}' target='_blank' style='color:#2a6a8a;font-size:.73rem;'>↗</a>" if url else "—"
        bw=int(ml*100)
        rows+=(f"<tr style='background:{bg};'>"
               f"<td><span class='badge {RANK_CSS.get(rk,'bN')}'>{rk}</span></td>"
               f"<td style='color:#b0ccec;font-size:.8rem;'>{name}</td>"
               f"<td style='color:#3a6080;text-align:center;'>{pos}</td>"
               f"<td style='color:#5a8090;font-size:.78rem;'>{sig}</td>"
               f"<td style='color:#3a6080;font-size:.76rem;'>{cond}</td>"
               f"<td><div style='display:flex;align-items:center;gap:5px;'>"
               f"<div style='width:36px;height:4px;background:#08162a;border-radius:3px;overflow:hidden;'>"
               f"<div style='width:{bw}%;height:100%;background:{clr};'></div></div>"
               f"<span style='color:{clr};font-size:.78rem;font-weight:700;'>{ml:.2f}</span></div></td>"
               f"<td style='text-align:center;'>{lnk}</td></tr>")
    st.markdown(
        f"<div style='overflow-x:auto;border-radius:12px;border:1px solid #0c2040;'>"
        f"<table style='width:100%;border-collapse:collapse;font-size:.82rem;'>"
        f"<thead><tr style='background:#040d18;'>"
        f"<th style='color:#00e5ff;padding:9px 11px;text-align:left;font-size:.69rem;font-weight:700;text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid #0c2040;'>Rank</th>"
        f"<th style='color:#00e5ff;padding:9px 11px;text-align:left;font-size:.69rem;font-weight:700;text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid #0c2040;'>Variant</th>"
        f"<th style='color:#00e5ff;padding:9px;text-align:center;font-size:.69rem;font-weight:700;text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid #0c2040;'>Pos</th>"
        f"<th style='color:#00e5ff;padding:9px 11px;text-align:left;font-size:.69rem;font-weight:700;text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid #0c2040;'>ClinVar Sig.</th>"
        f"<th style='color:#00e5ff;padding:9px 11px;text-align:left;font-size:.69rem;font-weight:700;text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid #0c2040;'>Condition</th>"
        f"<th style='color:#00e5ff;padding:9px;text-align:left;font-size:.69rem;font-weight:700;text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid #0c2040;'>ML Score</th>"
        f"<th style='color:#00e5ff;padding:9px;font-size:.69rem;font-weight:700;text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid #0c2040;'>Link</th>"
        f"</tr></thead><tbody>{rows}</tbody></table></div>",
        unsafe_allow_html=True)
    st.markdown(f"<div style='color:#0e2840;font-size:.72rem;margin-top:5px;'>Top {min(50,len(top))} of {len(top)} variants · ML-ranked · ClinVar</div>",unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────
# 3-D VIEWER HTML
# ──────────────────────────────────────────────────────────────────
def make_viewer_html(pdb_text, scored, height=500):
    path_pos={}
    for v in scored[:50]:
        pos=v.get("start") or v.get("position")
        try:
            p=int(pos)
            path_pos[p]={"rank":v.get("ml_rank","NEUTRAL"),"ml":v.get("ml",0),
                         "cond":v.get("condition","")[:60],"sig":v.get("sig",""),
                         "var":v.get("variant_name","")[:40]}
        except: pass
    pp_js=json.dumps({str(k):v for k,v in path_pos.items()})
    pdb_esc=pdb_text.replace("`","\\`").replace("\\","\\\\")
    return f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.1.0/3Dmol-min.js"></script>
<style>*{{margin:0;padding:0;box-sizing:border-box;}}body{{background:#04080f;font-family:Inter,sans-serif;display:flex;flex-direction:column;height:{height}px;}}
#ctrl{{display:flex;gap:5px;padding:7px 9px;background:#05101e;border-bottom:1px solid #0c2040;flex-wrap:wrap;flex-shrink:0;}}
.btn{{background:#06111e;color:#2a5070;border:1px solid #0c2040;padding:4px 11px;border-radius:15px;cursor:pointer;font-size:11px;transition:all .2s;}}
.btn:hover,.btn.on{{background:#00e5ff;color:#000;font-weight:700;border-color:#00e5ff;box-shadow:0 0 10px rgba(0,229,255,.25);}}
#wrap{{position:relative;flex:1;}}#v{{width:100%;height:100%;}}
#panel{{position:absolute;top:8px;right:8px;width:230px;background:rgba(4,8,15,.94);border:1px solid #0c2040;border-radius:10px;padding:13px;display:none;backdrop-filter:blur(8px);max-height:88%;overflow-y:auto;}}
#panel h3{{color:#00e5ff;font-size:12px;margin:0 0 8px;border-bottom:1px solid #0c2040;padding-bottom:5px;}}
.pr{{display:flex;justify-content:space-between;margin:4px 0;font-size:11px;}}.pk{{color:#1e4060;}}.pv{{color:#7aa0c0;font-weight:600;}}
#cl{{position:absolute;top:7px;right:9px;color:#1e4060;cursor:pointer;font-size:15px;}}
#leg{{position:absolute;bottom:8px;left:8px;background:rgba(4,8,15,.9);border:1px solid #0c2040;border-radius:8px;padding:8px 11px;font-size:10px;color:#1e4060;backdrop-filter:blur(4px);}}
.li{{display:flex;align-items:center;gap:5px;margin:2px 0;}}.ld{{width:9px;height:9px;border-radius:50%;flex-shrink:0;}}</style></head><body>
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
<div class="li"><div class="ld" style="background:#29B6F6"></div>pLDDT 70–90</div>
<div class="li"><div class="ld" style="background:#FDD835"></div>pLDDT 50–70</div>
<div class="li"><div class="ld" style="background:#FF7043"></div>pLDDT &lt;50</div>
<div class="li"><div class="ld" style="background:#ff2d55;border:1px solid #fff6;"></div>Pathogenic</div>
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
if(showV)Object.entries(pp).forEach(([pos,info])=>{{const rk=info.rank;const c=rk==='CRITICAL'?'#ff2d55':rk==='HIGH'?'#ff8c42':rk==='MEDIUM'?'#ffd60a':'#3a5a7a';v.addStyle({{resi:parseInt(pos),atom:'CA'}},{{sphere:{{radius:1.35,color:c,opacity:.93}}}});}});
v.render();}}
ap();v.zoomTo();v.render();
v.setClickable({{}},true,function(atom){{
const pos=atom.resi,r3=(atom.resn||'').toUpperCase(),r1=an[r3]||'?';
const full=fn[r1]||r3,pl=atom.b||0;
const cl=pl>=90?'Very High':pl>=70?'Confident':pl>=50?'Low':'Very Low';
const inf=pp[String(pos)];
let html='';
if(inf){{const rc={{CRITICAL:'#ff2d55',HIGH:'#ff8c42',MEDIUM:'#ffd60a',NEUTRAL:'#3a5a7a'}};
html+=`<span style="background:rgba(0,0,0,.3);color:${{rc[inf.rank]}};border:1px solid ${{rc[inf.rank]}}44;display:inline-block;padding:2px 9px;border-radius:11px;font-size:10px;font-weight:800;margin-bottom:7px;">${{inf.rank}}</span><br>`;}}
html+=`<div class="pr"><span class="pk">Residue</span><span class="pv">${{r1}} (${{full}})</span></div>`;
html+=`<div class="pr"><span class="pk">Position</span><span class="pv">${{pos}}</span></div>`;
html+=`<div class="pr"><span class="pk">pLDDT</span><span class="pv">${{pl.toFixed(1)}} (${{cl}})</span></div>`;
html+=`<div class="pr"><span class="pk">Hydropathy</span><span class="pv">${{hy[r1]!==undefined?hy[r1].toFixed(1):'?'}}</span></div>`;
if(inf){{html+='<hr style="border-color:#0c2040;margin:7px 0;">';
html+=`<div class="pr"><span class="pk">Variant</span><span class="pv" style="font-size:10px;">${{inf.var||'—'}}</span></div>`;
html+=`<div class="pr"><span class="pk">ClinVar</span><span class="pv" style="font-size:10px;">${{inf.sig||'—'}}</span></div>`;
html+=`<div class="pr"><span class="pk">ML score</span><span class="pv" style="color:#00e5ff;">${{(inf.ml*100).toFixed(0)}}%</span></div>`;
if(inf.cond)html+=`<div style="margin-top:5px;color:#1e4060;font-size:10px;line-height:1.4;">${{inf.cond}}</div>`;}}
document.getElementById('pt').textContent=r3+pos;document.getElementById('pc').innerHTML=html;document.getElementById('panel').style.display='block';}});
function ss(style,btn){{curStyle=style;document.querySelectorAll('.btn').forEach(b=>b.classList.remove('on'));btn.classList.add('on');ap();}}
function toggleSpin(){{spinning=!spinning;v.spin(spinning?'y':false,.6);const b=document.getElementById('spb');b.textContent=spinning?'⏸ Stop':'▶ Spin';b.classList.toggle('on',spinning);}}
function toggleV(){{showV=!showV;ap();}}
function toggleL(){{showL=!showL;v.removeAllLabels();if(showL)Object.entries(pp).forEach(([pos,info])=>{{if(info.rank==='CRITICAL'||info.rank==='HIGH')v.addLabel('P'+pos,{{position:{{resi:parseInt(pos),atom:'CA'}},backgroundColor:'#ff2d55',backgroundOpacity:.8,fontSize:9,fontColor:'white',borderRadius:3}});}});v.render();}}
</script></body></html>""".replace("{pp_js}",pp_js)

# ──────────────────────────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────────────────────────
for k,v in {"pdata":None,"cv":None,"pdb":"","papers":[],"scored":[],"gene":"","uid":"","assay":"","last":""}.items():
    if k not in st.session_state: st.session_state[k]=v

# ──────────────────────────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────────────────────────
st.markdown("<div class='proto-header'><div class='proto-title'>🧬 Protellect</div><div class='proto-sub'>AI-powered protein triage · Eliminate wasted experiments · Follow the science</div></div>",unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='text-align:center;padding:.4rem 0 .7rem;'><div style='font-size:1.8rem;'>🧬</div><div style='color:#00e5ff;font-size:1.2rem;font-weight:800;'>Protellect</div><div style='color:#0d2840;font-size:.7rem;'>Protein Intelligence Platform</div></div><div style='border-top:1px solid #0c2040;margin-bottom:.8rem;'></div>",unsafe_allow_html=True)
    tutorial=st.toggle("📖 Tutorial Mode",value=False)
    st.markdown("<div class='sb-t'>🔍 Protein Search</div>",unsafe_allow_html=True)
    query=st.text_input("Gene / UniProt ID",placeholder="TP53 · BRCA1 · P04637 · EGFR",label_visibility="collapsed")
    search=st.button("🔬 Analyse Protein",use_container_width=True)
    st.markdown("<div class='sb-t'>🧫 Wet-Lab Assay (optional)</div>",unsafe_allow_html=True)
    assay_txt=st.text_area("Assay results",height=90,placeholder="e.g. Western blot shows reduced expression…",label_visibility="collapsed")
    st.markdown("<div class='sb-t'>⚙️ Data Depth</div>",unsafe_allow_html=True)
    depth=st.selectbox("Depth",["Standard (100 variants)","Deep (300 variants)"],label_visibility="collapsed")
    max_v=100 if "Standard" in depth else 300

    if st.session_state["pdata"]:
        p=st.session_state["pdata"]; gene=st.session_state["gene"]; uid=st.session_state["uid"]
        scored=st.session_state["scored"]; cv=st.session_state["cv"]
        st.markdown(f"<div style='border-top:1px solid #0c2040;margin:.7rem 0 .4rem;'></div><div style='background:#040d18;border:1px solid #0c2040;border-radius:8px;padding:9px 11px;'><div style='color:#00e5ff;font-weight:700;font-size:.92rem;'>{gene}</div><div style='color:#1e4060;font-size:.76rem;margin:2px 0;'>{g_name(p)[:50]}</div><div style='color:#0d2840;font-size:.7rem;'>UniProt: {uid}</div></div>",unsafe_allow_html=True)
        # Disease ranking
        diseases=g_diseases(p); ds_scores={}
        for sv in scored:
            for c in sv.get("condition","").split(";"):
                c=c.strip()
                if c: ds_scores[c]=max(ds_scores.get(c,0),sv.get("ml",0))
        all_names=list(dict.fromkeys([d["name"] for d in diseases]+[c for sv in (cv or {}).get("variants",[]) for c in sv.get("condition","").split(";") if c.strip() and c.strip()!="Not specified"]))[:12]
        if all_names:
            st.markdown("<div class='sb-t'>🏥 Disease Affiliations</div>",unsafe_allow_html=True)
            for name in all_names[:10]:
                score=ds_scores.get(name,.4); rk="CRITICAL" if score>=.85 else "HIGH" if score>=.65 else "MEDIUM" if score>=.40 else "NEUTRAL"
                if any(k in name.lower() for k in ["cancer","carcinoma","leukemia","sarcoma"]) and rk=="MEDIUM": rk="HIGH"
                clr=RANK_CLR[rk]
                st.markdown(f"<div style='display:flex;align-items:center;gap:6px;margin:3px 0;'><span class='badge {RANK_CSS[rk]}'>{rk}</span><span style='color:#1e4060;font-size:.76rem;'>{name[:35]}</span></div>",unsafe_allow_html=True)
        # Assay interpretation
        if assay_txt:
            tl=assay_txt.lower(); findings=[]
            for kws,label in [(["western","wb"],"Expression (WB)"),(["crispr","knockout"],"Loss-of-function"),(["overexpression"],"Gain-of-function"),(["co-ip","binding","pulldown"],"Interaction data"),(["phospho"],"PTM detected"),(["apoptosis","caspase"],"Apoptosis active"),(["flow","facs"],"Flow cytometry"),(["in vivo","xenograft"],"In vivo model")]:
                if any(k in tl for k in kws): findings.append(label)
            if findings:
                st.markdown("<div class='sb-t'>🧫 Assay Findings</div>",unsafe_allow_html=True)
                for f in findings: st.markdown(f"<div style='color:#1e6040;font-size:.77rem;margin:2px 0;'>✓ {f}</div>",unsafe_allow_html=True)
        # Experiments
        ptype=g_ptype(p)
        sugg={"kinase":["ADP-Glo kinase assay","Phospho-proteomics","Kinase inhibitor screen","Substrate panel"],"gpcr":["cAMP assay (HTRF)","β-arrestin (BRET)","Radioligand binding","Biased agonism"],"transcription_factor":["ChIP-seq","EMSA","Luciferase reporter","RNA-seq post-KD"],"general":["Co-IP/AP-MS","Subcellular imaging","CRISPR KO screen","Thermal shift assay"]}.get(ptype,["Co-IP/AP-MS","CRISPR KO"])
        st.markdown("<div class='sb-t'>🔭 Suggested Experiments</div>",unsafe_allow_html=True)
        for s in sugg: st.markdown(f"<div style='color:#0d2840;font-size:.76rem;margin:2px 0;'>▸ {s}</div>",unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────
# TUTORIAL BANNER
# ──────────────────────────────────────────────────────────────────
if tutorial:
    st.markdown("<div style='background:#041008;border:1px solid #00c89630;border-radius:9px;padding:.8rem 1.1rem;margin-bottom:.9rem;'><span style='color:#00c896;font-weight:700;'>📖 Tutorial</span><span style='color:#1a5030;font-size:.84rem;margin-left:8px;'>1 Enter gene (try <b>TP53</b>) → 2 Triage = 3D structure & hotspots → 3 Case Study = tissue/genomics/GPCR → 4 Explorer = click residues & simulate mutations → 5 Experiments = full protocols & cost guide</span></div>",unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────
# DATA LOADING
# ──────────────────────────────────────────────────────────────────
if search and query and query!=st.session_state["last"]:
    with st.spinner("🔬 Fetching from UniProt, ClinVar, AlphaFold & PubMed…"):
        try:
            pdata=fetch_uniprot(query); st.session_state["pdata"]=pdata
            gene=g_gene(pdata); uid=pdata.get("primaryAccession","")
            st.session_state["gene"]=gene; st.session_state["uid"]=uid
            cv=fetch_clinvar(gene,max_v); st.session_state["cv"]=cv
            pdb=fetch_pdb(uid); st.session_state["pdb"]=pdb
            papers=fetch_papers(gene); st.session_state["papers"]=papers
            scored=ml_score(cv.get("variants",[])); st.session_state["scored"]=scored
            st.session_state["assay"]=assay_txt; st.session_state["last"]=query
            st.rerun()
        except Exception as e:
            st.error(f"⚠️ {e}")

# ──────────────────────────────────────────────────────────────────
# LANDING
# ──────────────────────────────────────────────────────────────────
if not st.session_state["pdata"]:
    st.markdown("""<div style='background:#040d18;border:1px solid #0c2040;border-radius:14px;padding:2.5rem;text-align:center;margin-top:1rem;'>
<div style='font-size:3rem;margin-bottom:.7rem;'>🧬</div>
<div style='color:#0e2840;font-size:1.1rem;font-weight:600;margin-bottom:.5rem;'>Enter a protein or gene in the sidebar to begin</div>
<div style='color:#081828;font-size:.86rem;'>Try: <b style='color:#0d2840;'>TP53</b> · <b style='color:#0d2840;'>BRCA1</b> · <b style='color:#0d2840;'>EGFR</b> · <b style='color:#0d2840;'>KRAS</b> · <b style='color:#0d2840;'>P04637</b></div>
<div style='display:flex;gap:.8rem;justify-content:center;flex-wrap:wrap;margin-top:1.5rem;'>
"""+
"".join(f"<div style='background:#05101e;border:1px solid #0c2040;border-radius:10px;padding:.7rem 1rem;width:160px;'><div style='font-size:1.2rem;'>{ic}</div><div style='color:#0e2840;font-size:.78rem;margin-top:4px;'><b style='color:#1e4060;'>{t}</b><br>{d}</div></div>"
        for ic,t,d in [("🔴","Triage","3D structure + variant hotspots"),("📋","Case Study","Tissue · genomics · GPCR"),("🔬","Explorer","Click residues · mutate"),("🧪","Experiments","Protocols + cost guide")])
+"</div></div>",unsafe_allow_html=True)
    st.stop()

# ──────────────────────────────────────────────────────────────────
# MAIN TABS
# ──────────────────────────────────────────────────────────────────
pdata=st.session_state["pdata"]; cv=st.session_state["cv"]
pdb=st.session_state["pdb"]; papers=st.session_state["papers"]
scored=st.session_state["scored"]; gene=st.session_state["gene"]
assay=st.session_state["assay"]; uid=st.session_state["uid"]
summary=cv.get("summary",{}); variants=cv.get("variants",[])
diseases=g_diseases(pdata)

t1,t2,t3,t4=st.tabs(["🔴 Triage","📋 Case Study","🔬 Protein Explorer","🧪 Experiments & Therapy"])

# ════════════════════════════════════════════════════════
# TAB 1 — TRIAGE
# ════════════════════════════════════════════════════════
with t1:
    c1,c2,c3,c4=st.columns(4)
    n_crit=sum(1 for v in scored if v.get("ml_rank")=="CRITICAL")
    with c1: st.markdown(mc(len(diseases),"Disease Links"),unsafe_allow_html=True)
    with c2: st.markdown(mc(summary.get("total",0),"ClinVar Variants","#4a90d9"),unsafe_allow_html=True)
    with c3: st.markdown(mc(summary.get("pathogenic",0),"Pathogenic","#ff2d55","linear-gradient(90deg,#ff2d55,#ff6b8a)"),unsafe_allow_html=True)
    with c4: st.markdown(mc(n_crit,"CRITICAL (ML)","#ff8c42","linear-gradient(90deg,#ff8c42,#ffb380)"),unsafe_allow_html=True)
    st.markdown("<div class='divider'></div>",unsafe_allow_html=True)

    cs,cd=st.columns([3,2],gap="large")
    with cs:
        sh("🏗️","AlphaFold Structure")
        if pdb:
            bf=parse_bfactors(pdb); avg=round(sum(bf.values())/max(len(bf),1),1)
            n_hi=sum(1 for b in bf.values() if b>=70)
            pct=round(n_hi/max(len(bf),1)*100)
            components.html(make_viewer_html(pdb,scored,460),height=465,scrolling=False)
            n_sites = sum(1 for v in scored[:50] if v.get('start'))
            st.markdown(f"<div style='color:#0e2840;font-size:.74rem;margin-top:4px;'>pLDDT avg: <b style='color:#3a7090;'>{avg}</b> · {pct}% reliably modelled · <b style='color:#ff2d55;'>{n_sites}</b> variant sites shown</div>",unsafe_allow_html=True)
        else:
            st.markdown("<div style='background:#04080f;border:1px dashed #0c2040;border-radius:12px;height:380px;display:flex;align-items:center;justify-content:center;'><div style='text-align:center;color:#0e2840;'><div style='font-size:2rem;'>🧬</div><div style='font-size:.85rem;margin-top:6px;'>AlphaFold structure not available<br>Try a direct UniProt accession</div></div></div>",unsafe_allow_html=True)

    with cd:
        sh("🔴","Disease Triage")
        ds_scores={}
        for sv in scored:
            for c in sv.get("condition","").split(";"):
                c=c.strip()
                if c: ds_scores[c]=max(ds_scores.get(c,0),sv.get("ml",0))
        all_d=[]
        for d in diseases:
            sc=ds_scores.get(d["name"],.5); rk="CRITICAL" if sc>=.85 else "HIGH" if sc>=.65 else "MEDIUM" if sc>=.40 else "NEUTRAL"
            if any(k in (d["name"]+d.get("desc","")).lower() for k in ["cancer","carcinoma","leukemia"]) and rk=="MEDIUM": rk="HIGH"
            all_d.append({"name":d["name"],"desc":d.get("desc",""),"rk":rk,"sc":sc})
        for cn,cnt in summary.get("top_conds",{}).items():
            if cn not in [x["name"] for x in all_d]:
                sc=ds_scores.get(cn,.3); rk="CRITICAL" if sc>=.85 else "HIGH" if sc>=.65 else "MEDIUM" if sc>=.40 else "NEUTRAL"
                all_d.append({"name":cn,"desc":f"{cnt} ClinVar submissions","rk":rk,"sc":sc})
        all_d.sort(key=lambda x:(["CRITICAL","HIGH","MEDIUM","NEUTRAL"].index(x["rk"]),-x["sc"]))
        for d in all_d[:10]:
            bw=int(d["sc"]*100); clr=RANK_CLR[d["rk"]]
            st.markdown(f"<div class='dr'><div style='flex-shrink:0;margin-top:1px;'>{badge(d['rk'])}</div><div style='flex:1;min-width:0;'><div class='dn'>{d['name']}</div><div class='dd'>{d['desc'][:100]}</div><div style='height:3px;background:#08162a;border-radius:3px;overflow:hidden;margin-top:5px;'><div style='width:{bw}%;height:100%;background:{clr};'></div></div></div></div>",unsafe_allow_html=True)
        if summary.get("by_sig"):
            sd=summary["by_sig"]; clrs=["#ff2d55","#ff8c42","#ffd60a","#4a90d9","#00c896","#6478ff","#a855f7","#1e4060"]
            fig=go.Figure(go.Pie(labels=list(sd.keys()),values=list(sd.values()),hole=.58,marker_colors=clrs[:len(sd)],textfont_size=9))
            fig.update_layout(paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#1e4060",showlegend=True,legend=dict(font_size=9,bgcolor="#04080f"),margin=dict(t=0,b=0,l=0,r=0),height=190,annotations=[dict(text=f"<b>{summary.get('total',0)}</b>",x=.5,y=.5,font_size=14,font_color="#00e5ff",showarrow=False)])
            st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

    st.markdown("<div class='divider'></div>",unsafe_allow_html=True)
    sh("🔮","Residue Hotspot Triage")
    render_triage_table(scored)
    render_citations(papers,4)

# ════════════════════════════════════════════════════════
# TAB 2 — CASE STUDY
# ════════════════════════════════════════════════════════
with t2:
    c1,c2=st.columns([1,1],gap="large")
    TKWS={"Brain":["brain","neuron","cerebral","cortex"],"Liver":["liver","hepatic"],"Heart":["heart","cardiac","myocardium"],"Kidney":["kidney","renal"],"Lung":["lung","pulmonary"],"Blood":["blood","erythrocyte","platelet"],"Breast":["breast","mammary"],"Colon":["colon","colorectal","intestine"],"Prostate":["prostate"],"Skin":["skin","keratinocyte","melanocyte"],"Muscle":["muscle","skeletal"],"Pancreas":["pancreas","islet"]}
    with c1:
        sh("🫀","Tissue Associations")
        tt=g_tissue(pdata)
        if tt: st.markdown(f"<div class='card'><p>{tt[:500]}</p></div>",unsafe_allow_html=True)
        blob=(tt+" "+g_func(pdata)+" "+" ".join(k.get("value","") for k in pdata.get("keywords",[]))).lower()
        tsc={t:sum(1 for k in ks if k in blob) for t,ks in TKWS.items()}; tsc={t:s for t,s in tsc.items() if s>0}
        if tsc:
            tsc=dict(sorted(tsc.items(),key=lambda x:-x[1])[:10])
            fig=go.Figure(go.Bar(y=list(tsc.keys()),x=list(tsc.values()),orientation="h",marker=dict(color=list(tsc.values()),colorscale=[[0,"#0c2040"],[.5,"#0d4080"],[1,"#00e5ff"]],cmin=0,cmax=max(tsc.values()))))
            fig.update_layout(paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#1e4060",xaxis=dict(showgrid=False,zeroline=False,showticklabels=False),yaxis=dict(tickfont=dict(size=11,color="#3a6080")),margin=dict(l=0,r=0,t=5,b=0),height=160+len(tsc)*18)
            st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
    with c2:
        sh("📍","Subcellular & PTM")
        for loc in g_sub(pdata): st.markdown(f"<div style='display:flex;align-items:center;gap:7px;margin:4px 0;'><span style='color:#00e5ff;font-size:.75rem;'>◆</span><span style='color:#5a8090;font-size:.84rem;'>{loc}</span></div>",unsafe_allow_html=True)
        ptm=next((c.get("texts",[{}])[0].get("value","") for c in pdata.get("comments",[]) if c.get("commentType")=="PTM"),"")
        if ptm: st.markdown("**PTMs**"); st.markdown(f"<div class='card'><p>{ptm[:350]}</p></div>",unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>",unsafe_allow_html=True)
    sh("🧬","Genomic Data")
    omim=g_xref(pdata,"MIM"); hgnc=g_xref(pdata,"HGNC"); ens=g_xref(pdata,"Ensembl")
    gd=fetch_ncbi_gene(gene) if gene else {}
    c1,c2,c3=st.columns(3)
    with c1: st.markdown(f"<div class='card'><h4>Protein</h4><p>UniProt: <b style='color:#00e5ff;'>{uid}</b><br>Length: <b>{pdata.get('sequence',{}).get('length','—')} aa</b><br>HGNC: {hgnc or '—'}</p></div>",unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='card'><h4>Genomic Location</h4><p>Chr: <b style='color:#00e5ff;'>{gd.get('chr','—')}</b><br>Cytoband: <b>{gd.get('map','—')}</b><br>Exons: <b>{gd.get('exons','—')}</b></p></div>",unsafe_allow_html=True)
    with c3:
        omim_link=f"<a href='https://omim.org/entry/{omim}' target='_blank' style='color:#3a90c4;'>{omim}</a>" if omim else "—"
        ncbi_link=f"<a href='{gd['link']}' target='_blank' style='color:#3a90c4;'>NCBI Gene ↗</a>" if gd.get("link") else ""
        st.markdown(f"<div class='card'><h4>Cross-References</h4><p>OMIM: {omim_link}<br>Ensembl: {ens[:20] if ens else '—'}<br><a href='https://www.uniprot.org/uniprotkb/{uid}' target='_blank' style='color:#3a90c4;'>UniProt ↗</a> {('· '+ncbi_link) if ncbi_link else ''}</p></div>",unsafe_allow_html=True)
    if gd.get("summary"):
        with st.expander("📖 NCBI Gene Summary"): st.write(gd["summary"])

    st.markdown("<div class='divider'></div>",unsafe_allow_html=True)
    sh("📡","GPCR Association")
    if g_gpcr(pdata):
        st.markdown("<div style='background:linear-gradient(135deg,#03111f,#04101c);border:1px solid #00e5ff25;border-radius:12px;padding:1.1rem 1.4rem;display:flex;gap:12px;align-items:flex-start;'><div style='font-size:2rem;'>📡</div><div><p style='color:#00e5ff;font-weight:700;font-size:.95rem;margin:0 0 4px;'>GPCR — Important / Piggybacked Target</p><p style='color:#1e4060;font-size:.84rem;margin:0;'>GPCRs represent ~34% of all FDA-approved drug targets. Consider biased agonism, allosteric modulation, and antibody-based approaches.</p></div></div>",unsafe_allow_html=True)
    else:
        st.markdown("<div style='background:#04080f;border:1px solid #0c2040;border-radius:9px;padding:.8rem 1.1rem;color:#0e2840;font-size:.84rem;'>Not classified as a GPCR in UniProt.</div>",unsafe_allow_html=True)
    inters=[]
    for c in pdata.get("comments",[]):
        if c.get("commentType")=="INTERACTION":
            for i in c.get("interactions",[]): g=i.get("interactantTwo",{}).get("geneName",""); inters.append(g) if g else None
    if inters: st.markdown("<div style='margin-top:.7rem;color:#0e2840;font-size:.78rem;'>Known interactors: "+"".join(f"<code style='background:#05101e;color:#3a7090;padding:1px 5px;border-radius:4px;margin:2px;'>{g}</code>" for g in inters[:12])+"</div>",unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>",unsafe_allow_html=True)
    sh("🔬","Disease Classification — Somatic vs Germline")
    somatic=set(); germline=set()
    for v in variants:
        origin=v.get("origin","").lower(); cond=v.get("condition","")
        if not cond or cond=="Not specified": continue
        if "somatic" in origin or v.get("somatic"): somatic.add(cond)
        elif any(x in origin for x in ["germline","inherited","de novo"]): germline.add(cond)
        elif v.get("score",0)>=4: germline.add(cond)
    cg,cs2=st.columns(2)
    with cg:
        st.markdown(f"<div style='background:#03100a;border:1px solid #00c89628;border-radius:11px;padding:1.1rem;'><p style='color:#00c896;font-weight:700;font-size:.9rem;margin:0 0 3px;'>🧬 Germline ({len(germline)})</p><p style='color:#1a4030;font-size:.74rem;margin:0 0 7px;'>Heritable — all cells from birth</p>",unsafe_allow_html=True)
        for c in sorted(germline)[:7]: st.markdown(f"<div style='color:#2a6040;font-size:.8rem;margin:2px 0;'>◆ {c[:65]}</div>",unsafe_allow_html=True)
        if not germline: st.markdown("<div style='color:#0d2a1a;font-size:.8rem;'>None found.</div>",unsafe_allow_html=True)
        st.markdown("</div>",unsafe_allow_html=True)
    with cs2:
        st.markdown(f"<div style='background:#100308;border:1px solid #ff2d5528;border-radius:11px;padding:1.1rem;'><p style='color:#ff2d55;font-weight:700;font-size:.9rem;margin:0 0 3px;'>🔴 Somatic ({len(somatic)})</p><p style='color:#3a1020;font-size:.74rem;margin:0 0 7px;'>Acquired — specific cell populations</p>",unsafe_allow_html=True)
        for c in sorted(somatic)[:7]: st.markdown(f"<div style='color:#602030;font-size:.8rem;margin:2px 0;'>◆ {c[:65]}</div>",unsafe_allow_html=True)
        if not somatic: st.markdown("<div style='color:#2a0810;font-size:.8rem;'>None found.</div>",unsafe_allow_html=True)
        st.markdown("</div>",unsafe_allow_html=True)
    for d in diseases[:6]:
        omim=d.get("omim","")
        omim_lnk=f" · <a href='https://omim.org/entry/{omim}' target='_blank' style='color:#3a90c4;font-size:.74rem;'>OMIM {omim}</a>" if omim else ""
        note_html=f"<p style='color:#ffd60a;font-size:.78rem;margin-top:3px;'>{d['note'][:150]}</p>" if d.get("note") else ""
        st.markdown(f"<div class='card'><h4>{d['name']}{omim_lnk}</h4><p>{d.get('desc','')[:280]}</p>{note_html}</div>",unsafe_allow_html=True)
    render_citations(papers,4)

# ════════════════════════════════════════════════════════
# TAB 3 — PROTEIN EXPLORER
# ════════════════════════════════════════════════════════
with t3:
    sh("🔬","Protein Explorer")
    st.caption("Click any residue sphere to inspect it. Use the mutation panel to simulate substitutions.")
    if pdb:
        components.html(make_viewer_html(pdb,scored,620),height=625,scrolling=False)
    else:
        st.info("No AlphaFold structure available. Search by UniProt accession for 3D view.")
    st.markdown("<div class='divider'></div>",unsafe_allow_html=True)

    sh("🧫","Residue Mutation Analysis")
    seq=g_seq(pdata)
    if seq:
        bf=parse_bfactors(pdb) if pdb else {}
        pos_to_v={};[pos_to_v.__setitem__(int(v.get("start") or 0),v) for v in scored if v.get("start","")]
        csel,cmut=st.columns([1,2],gap="large")
        with csel:
            position=int(st.number_input("Residue position",1,max(len(seq),1),1,1,key="rpos"))
            aa=seq[position-1] if position<=len(seq) else "?"
            pl=bf.get(position); conf=("Very High" if pl and pl>=90 else "Confident" if pl and pl>=70 else "Low" if pl and pl>=50 else "Very Low") if pl else "—"
            st.markdown(f"<div class='card'><h4>Residue {position} — {aa}</h4><p>{AA_NAMES.get(aa,'Unknown')}<br>pLDDT: <b style='color:#00e5ff;'>{f'{pl:.1f}' if pl else '—'}</b> ({conf})<br>Hydropathy: <b>{AA_HYDRO.get(aa,0):+.1f}</b></p></div>",unsafe_allow_html=True)
            vd=pos_to_v.get(position)
            if vd:
                rk=vd.get("ml_rank","NEUTRAL"); clr=RANK_CLR[rk]
                st.markdown(f"<div class='card' style='border-color:{clr}33;'><h4 style='color:{clr};'>⚠️ ClinVar Variant</h4><p>{vd.get('sig','—')}<br><small style='color:#0e2840;'>{vd.get('condition','')[:80]}</small></p></div>",unsafe_allow_html=True)
            else:
                st.success("No ClinVar variant at this position",icon="✅")
        with cmut:
            tb1,tb2=st.tabs(["Properties","If Mutated →"])
            with tb1:
                AA_SPECIAL={"C":"Disulfide bonds · metal binding","G":"Most flexible · helix-breaker","P":"Rigid ring · helix-breaker","H":"pH-sensitive (pKa≈6)","W":"Largest AA · UV-absorbing","Y":"Phosphorylation target","R":"DNA/RNA binding · +1 charge","K":"Ubiquitination target","D":"Catalytic acid · −1","E":"Catalytic acid · −1"}
                for k2,v2 in [("Amino acid",f"{aa} — {AA_NAMES.get(aa,'?')}"),("Hydropathy",f"{AA_HYDRO.get(aa,0):+.1f}"),("Charge",f"{AA_CHG.get(aa,0):+.1f}"),("Note",AA_SPECIAL.get(aa,"—"))]:
                    st.markdown(f"<div class='prow'><span class='pk'>{k2}</span><span class='pv'>{v2}</span></div>",unsafe_allow_html=True)
            with tb2:
                alts=[a for a in AA_NAMES.keys() if a!=aa]
                alt=st.selectbox("Substitute with:",alts,key="alt_aa")
                sev=st.slider("Perturbation",0.0,1.0,.5,.05,key="sev")
                if bf:
                    pos_list=sorted(bf.keys()); window=32; center=min(max(position,window+1),max(pos_list)-window)
                    dp=[p for p in pos_list if abs(p-center)<=window]
                    wt=[bf.get(p,70) for p in dp]
                    mt=[max(0,wt[i]-sev*28*math.exp(-.5*((p-position)/6)**2)) for i,p in enumerate(dp)]
                    fig=go.Figure()
                    fig.add_trace(go.Scatter(x=dp,y=wt,mode="lines",name="Wild-type",line=dict(color="#00e5ff",width=2)))
                    fig.add_trace(go.Scatter(x=dp,y=mt,mode="lines",name=f"{aa}{position}{alt}",line=dict(color="#ff2d55",width=2,dash="dash")))
                    fig.add_trace(go.Scatter(x=dp+dp[::-1],y=mt+wt[::-1],fill="toself",fillcolor="rgba(255,45,85,.07)",line=dict(color="rgba(0,0,0,0)"),showlegend=False))
                    fig.add_vline(x=position,line_color="#ffd60a",line_dash="dot",annotation_text=f"p.{aa}{position}{alt}",annotation_font_color="#ffd60a",annotation_font_size=10)
                    fig.update_layout(paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#1e4060",xaxis=dict(title="Position",gridcolor="#060f1c",color="#0e2840"),yaxis=dict(title="pLDDT",range=[0,100],gridcolor="#060f1c",color="#0e2840"),legend=dict(bgcolor="#04080f",font_size=10),margin=dict(t=8,b=28,l=28,r=8),height=230)
                    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
                    st.caption(f"Simulated perturbation of {aa}{position}{alt} · severity {sev:.0%}")
                # Implications
                hd=abs(AA_HYDRO.get(aa,0)-AA_HYDRO.get(alt,0)); cd=abs(AA_CHG.get(aa,0)-AA_CHG.get(alt,0))
                imps=[]
                if alt=="*": imps.append(("🔴","Nonsense / stop-gain","Premature termination → NMD → loss-of-function"))
                if hd>3: imps.append(("🟠","Large hydropathy shift",f"Δ{hd:.1f} — buried polarity change may destabilise core"))
                if cd>=1: imps.append(("⚡","Charge change",f"Δ{cd:+.0f} — disrupted electrostatic interactions"))
                if aa=="C": imps.append(("🔗","Cysteine lost","Disulfide bond or metal-chelation disruption"))
                if alt=="P": imps.append(("🔀","Proline introduced","Rigid backbone — helix/sheet may break"))
                if not imps: imps.append(("🟡","Conservative","Low physicochemical change — likely low impact"))
                for icon,title,body in imps:
                    st.markdown(f"<div class='imp'><span style='font-size:1rem;flex-shrink:0;'>{icon}</span><div><div class='imp-t'>{title}</div><div class='imp-b'>{body}</div></div></div>",unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>",unsafe_allow_html=True)
    sh("🗺️","Disease → Mutation → Genomic Implication")
    cond_map=defaultdict(list)
    for v in scored[:30]:
        for c in v.get("condition","Not specified").split(";"):
            c=c.strip()
            if c and c!="Not specified": cond_map[c].append(v)
    for cond,vlist in list(cond_map.items())[:12]:
        vlist_s=sorted(vlist,key=lambda x:-x.get("ml",0)); best=vlist_s[0].get("ml_rank","NEUTRAL")
        with st.expander(f"{cond[:75]}  ({len(vlist_s)} variants)",expanded=(best in ("CRITICAL","HIGH"))):
            cv2,mech=st.columns([2,3])
            with cv2:
                st.markdown("**Top variants:**")
                for v in vlist_s[:5]:
                    ml2=v.get("ml",0); clr2=RANK_CLR.get(v.get("ml_rank","NEUTRAL"),"#3a5a7a")
                    vn=(v.get("variant_name") or v.get("title","—"))[:50]
                    url2=v.get("url",""); lnk=f" [↗]({url2})" if url2 else ""
                    st.markdown(f"<div style='font-size:.8rem;margin:3px 0;color:#1e4060;'><span style='color:{clr2};font-weight:700;'>{ml2:.2f}</span> <span style='color:#5a8090;'>{vn}</span><br><span style='color:#0e2840;'>{v.get('sig','—')}</span>{lnk}</div>",unsafe_allow_html=True)
            with mech:
                st.markdown("**Likely mechanism:**")
                cl=cond.lower(); vn_all=" ".join(v.get("variant_name","") for v in vlist_s).lower(); mechs=[]
                if any(k in cl for k in ["cancer","carcinoma","tumor","leukemia","glioma"]): mechs+=["Oncogenic transformation via GoF or dominant-negative.","Somatic acquisition → clonal expansion → tumour."]
                if "stop" in vn_all or "ter" in vn_all: mechs.append("Stop-gain → truncated protein → haploinsufficiency.")
                if "frameshift" in vn_all or "del" in vn_all: mechs.append("Frameshift → aberrant isoform → LoF.")
                if "splice" in vn_all: mechs.append("Splice-site → exon skipping or intron retention.")
                if "missense" in vn_all: mechs.append("Missense → altered conformation / binding affinity.")
                if not mechs: mechs.append("Mechanism not fully characterised — functional assays recommended.")
                for m in mechs: st.markdown(f"<div style='color:#1e4060;font-size:.81rem;margin:2px 0;'>• {m}</div>",unsafe_allow_html=True)
    render_citations(papers,4)

# ════════════════════════════════════════════════════════
# TAB 4 — EXPERIMENTS & THERAPY
# ════════════════════════════════════════════════════════
with t4:
    sh("🧪","Experiments & Therapy")
    # Scorecard
    ptype=g_ptype(pdata); drugg={"kinase":.9,"gpcr":.95,"transcription_factor":.35,"receptor":.8,"general":.5}.get(ptype,.5)
    n_crit2=sum(1 for v in scored if v.get("ml_rank")=="CRITICAL"); n_high=sum(1 for v in scored if v.get("ml_rank")=="HIGH")
    priority=min(100,n_crit2*15+n_high*8+len(scored)*.5+drugg*20)
    c1,c2,c3,c4=st.columns(4)
    with c1: st.markdown(mc(n_crit2,"CRITICAL Variants","#ff2d55","linear-gradient(90deg,#ff2d55,#ff8c42)"),unsafe_allow_html=True)
    with c2: st.markdown(mc(n_high,"HIGH Variants","#ff8c42"),unsafe_allow_html=True)
    with c3: st.markdown(mc(f"{drugg:.0%}","Druggability","#00c896"),unsafe_allow_html=True)
    with c4: st.markdown(mc(int(priority),"Priority / 100","#00e5ff"),unsafe_allow_html=True)
    rec_msg=("⚡ High priority. Multiple pathogenic variants confirmed. Recommend CRISPR knock-in + biochemical validation immediately." if priority>=70 else "🟡 Moderate priority. Start with in silico stability (Rosetta ΔΔG) + low-cost cell assay before animal studies." if priority>=40 else "🟢 Low priority. Insufficient evidence. Monitor ClinVar reclassifications. Do not commit resources now.")
    rec_clr="#ff2d55" if priority>=70 else "#ffd60a" if priority>=40 else "#00c896"
    st.markdown(f"<div style='background:#04080f;border-left:3px solid {rec_clr};border-radius:0 9px 9px 0;padding:.9rem 1.3rem;margin:.8rem 0;'><p style='color:#5a8090;margin:0;font-size:.88rem;'>{rec_msg}</p></div>",unsafe_allow_html=True)

    if assay:
        st.markdown("<div class='divider'></div>",unsafe_allow_html=True)
        sh("🧫","Assay-Specific Next Steps")
        tl=assay.lower()
        for kws,title,body in [
            (["western","wb"],"Western Blot → Follow Up","Quantify in ≥2 cell lines. If expression change: CHX chase (half-life) + SILAC/TMT-MS proteomics."),
            (["crispr","knockout"],"CRISPR KO → Follow Up","Rescue experiment: re-introduce WT + variants. RNA-seq KO vs WT. Xenograft if oncogene."),
            (["flow","facs"],"Flow Cytometry → Follow Up","Apoptosis: WB for caspase 3/7 + Bcl-2 family. Cell cycle: add CDK inhibitor comparison."),
            (["co-ip","binding","pulldown"],"Interaction Data → Follow Up","Map interface by HDX-MS. Target for cryo-EM. Design interface disruptors."),
        ]:
            if any(k in tl for k in kws): st.markdown(f"<div class='card'><h4>{title}</h4><p>{body}</p></div>",unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>",unsafe_allow_html=True)

    # Cost legend
    COST_MAP={"Free":("#00c896","rgba(0,200,150,.1)"),"$":("#4a90d9","rgba(74,144,217,.1)"),"$$":("#ffd60a","rgba(255,214,10,.1)"),"$$$":("#ff8c42","rgba(255,140,66,.1)"),"$$$$":("#ff2d55","rgba(255,45,85,.1)")}
    cols_cl=st.columns(5)
    for (sym,(clr,bg)),col in zip(COST_MAP.items(),cols_cl):
        col.markdown(f"<div style='background:{bg};border:1px solid {clr}33;border-radius:8px;padding:5px;text-align:center;'><div style='color:{clr};font-weight:800;font-size:.95rem;'>{sym}</div><div style='color:{clr}88;font-size:.68rem;'>{{'Free':'No cost','$':'<$1K','$$':'$1-10K','$$$':'$10-50K','$$$$':'$50K+'}}.get(sym,'')</div></div>",unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)

    EXPS=[
        ("🧬 Functional","In vitro Kinase / Enzyme Activity (ADP-Glo™)","$$","3–6 wks",
         "Directly measure gain or loss of enzymatic activity for variant proteins.",
         ["Express WT & variants in E. coli or baculovirus.","Purify via His-tag + SEC.","Run ADP-Glo™ kinase reaction.","Compare Km/Vmax WT vs variants.","Triplicate; SEM ≤10%."],
         "Catalytic-residue variants (D-loop, activation loop).","Variants in disordered linkers / pLDDT <50.",
         "Quantitative activity ratio WT vs mutant."),
        ("🧬 Functional","Co-IP / AP-MS Interaction Mapping","$$$","4–8 wks",
         "Map protein–protein interaction network changes per variant.",
         ["Tag protein (3×FLAG or GFP) in HEK293T.","Lyse native (NP-40).","Pull down + Protein A/G beads.","TMT-labelled MS or SDS-PAGE.","Reverse Co-IP to validate top hits."],
         "Interface residues predicted by AlphaFold-Multimer.","Splice variants with identical binding domains.",
         "Interaction network rewiring per mutation."),
        ("🧬 Functional","Thermal Shift Assay (TSA/DSF)","$","1–2 wks",
         "Screen small-molecule binders and assess variant folding stability.",
         ["Purify WT & variants (0.5 mg/mL).","96-well + SYPRO Orange dye (5×).","Ramp 25→95°C at 1°C/min in qPCR.","Boltzmann fit → Tm.","Flag ΔTm ≥1°C hits."],
         "Pathogenic missense variants destabilising core fold.","IDRs — no Tm signal expected.",
         "ΔTm per variant; leads for stabilising compounds."),
        ("🔬 Cell-Based","CRISPR-Cas9 Knock-in","$$$","6–12 wks",
         "Introduce exact patient-like variants into the endogenous locus.",
         ["Design sgRNAs (CRISPOR).","Co-transfect sgRNA + SpCas9 RNP + ssODN HDR donor.","Screen ≥50 colonies (Sanger/NGS).","Validate by WB + IF.","Run phenotypic assays on confirmed clones."],
         "ClinVar P/LP + ML score ≥0.75.","VUS with <2 star review.",
         "Isogenic cell lines; gold-standard functional evidence."),
        ("🔬 Cell-Based","Luciferase Reporter Assay","$","1–3 wks",
         "Quantify transcriptional activity changes for TF variants.",
         ["Clone 1 kb target promoter into pGL4.","Transfect WT or mutant TF + Renilla control.","Read firefly:Renilla ratio at 48h.","≥3 independent experiments in triplicate."],
         "DNA-binding domain or transactivation domain variants.","N-terminal disordered segments.",
         "Fold-change in target gene activation/repression."),
        ("🔬 Cell-Based","Cell Viability — CellTiter-Glo","$","1–2 wks",
         "Assess oncogenic or tumour-suppressive phenotype.",
         ["Seed 5,000 cells/well in 96-well plates.","Express variant for 72h.","Add CellTiter-Glo; read luminescence.","Normalise to vehicle; compute IC₅₀."],
         "Gain-of-function oncogenic CRITICAL tier variants.","Benign / likely benign variants.",
         "Viability % vs WT; GO/NO-GO for animal models."),
        ("🧫 Structural","AlphaFold + Rosetta ΔΔG","Free","1–3 days",
         "Rank all missense variants by in silico stability — eliminates ~50% before wet lab.",
         ["Download AF2 PDB.","Rosetta FastRelax on WT.","MutateResidue mover per variant.","Flag ΔΔG ≥2 REU as destabilising.","Cross-reference ML scores."],
         "All missense in structured domains (pLDDT ≥70).","IDR variants (pLDDT <50).",
         "Pre-ranked list eliminating half of candidates before any wet lab."),
        ("🧫 Structural","Surface Plasmon Resonance (SPR)","$$$","2–4 wks",
         "Measure binding kinetics WT vs mutant to ligand / drug / partner.",
         ["Immobilise ligand on CM5 chip.","Flow analyte at 5 concentrations.","Fit 1:1 Langmuir → KD, kon, koff.","Compare KD shifts across variants."],
         "Variants altering binding interface (charge/hydrophobicity).","Variants >15 Å from binding site.",
         "KD shift per variant; structural drug design input."),
        ("🐭 In Vivo","Xenograft Mouse Model","$$$$","8–16 wks",
         "Test tumorigenic potential of GoF variants in vivo.",
         ["Inject 1×10⁶ CRISPR knock-in cells SC into NSG mice.","Monitor tumour volume twice weekly.","Harvest + H&E + IHC at endpoint.","Log-rank test WT vs mutant growth curves."],
         "Variants with in vitro proliferation data supporting oncogenicity.","VUS without prior in vitro validation.",
         "In vivo tumour growth curves; histological characterisation."),
        ("💊 Therapeutic","Small Molecule HTS","$$$$","6–12 months",
         "Identify compounds that rescue or inhibit mutant protein function.",
         ["Establish HTS-compatible assay.","Screen library at 10 µM.","Counter-screen for cytotoxicity.","Confirm IC₅₀ top 50 hits.","Advance top 5 for SAR."],
         "CRITICAL/HIGH variants with druggable pockets.","IDPs without defined pockets.",
         "Lead compound series for medicinal chemistry."),
        ("💊 Therapeutic","PROTAC / Targeted Degradation","$$$$","6–12 months",
         "Degrade undruggable gain-of-function mutant proteins.",
         ["Design PROTAC: warhead + E3-recruiter (CRBN/VHL).","Synthesise 10–20 candidates.","Assess DC₅₀ in target cell line.","Validate by WB/MS.","Proteome-wide selectivity (TMT-MS)."],
         "GoF mutations resistant to catalytic inhibition.","Tumour suppressor LoF — degradation worsens phenotype.",
         "Selective degrader DC₅₀ <100 nM."),
    ]
    for cat,name,cost,time2,purpose,protocol,focus,neglect,outcome in EXPS:
        clr_e,bg_e=COST_MAP.get(cost,("#3a6080","rgba(58,96,128,.1)"))
        with st.expander(f"{cat} · {name}  ·  {cost}  ·  ⏱ {time2}"):
            cl2,cr2=st.columns([3,2])
            with cl2:
                st.markdown(f"**Purpose:** {purpose}")
                st.markdown("**Protocol:**")
                for i,step in enumerate(protocol,1): st.markdown(f"{i}. {step}")
                st.markdown(f"**Outcome:** {outcome}")
            with cr2:
                st.markdown(f"<div style='background:{bg_e};border:1px solid {clr_e}33;border-radius:10px;padding:1rem;'><div style='color:{clr_e};font-weight:800;font-size:1rem;'>{cost}</div><div style='color:{clr_e}88;font-size:.78rem;margin-bottom:9px;'>⏱ {time2}</div><div style='color:#00c896;font-size:.78rem;font-weight:700;margin-bottom:2px;'>✅ Focus on:</div><div style='color:#1a5030;font-size:.76rem;margin-bottom:8px;'>{focus}</div><div style='color:#ff8c42;font-size:.78rem;font-weight:700;margin-bottom:2px;'>❌ Deprioritise:</div><div style='color:#5a2a10;font-size:.76rem;'>{neglect}</div></div>",unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>",unsafe_allow_html=True)
    sh("🗺️","Decision Framework")
    rc={"CRITICAL":"#ff2d55","HIGH":"#ff8c42","MEDIUM":"#ffd60a","NEUTRAL":"#3a5a7a"}
    counts={r:sum(1 for v in scored if v.get("ml_rank")==r) for r in rc}
    labels2=[r for r in rc if counts[r]>0]; values2=[counts[r] for r in labels2]; clrs2=[rc[r] for r in labels2]
    if labels2:
        fig2=go.Figure(go.Funnel(y=labels2,x=values2,textinfo="value+percent initial",marker=dict(color=clrs2),textfont=dict(color="white",size=12)))
        fig2.update_layout(paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#1e4060",height=280,margin=dict(t=8,b=8,l=70,r=8),title=dict(text="Variant Triage Funnel",font_color="#00e5ff",font_size=12))
        st.plotly_chart(fig2,use_container_width=True,config={"displayModeBar":False})
    for rank,clr,rec in [("CRITICAL","#ff2d55","Immediate validation. CRISPR knock-in + biochemical assay now. In vivo if in vitro confirms phenotype."),("HIGH","#ff8c42","Functional assay + ΔΔG. In vivo only after clear in vitro phenotype."),("MEDIUM","#ffd60a","In silico + low-cost cell assay. Hold before animal work."),("NEUTRAL","#3a5a7a","Deprioritise. Monitor ClinVar reclassifications. No wet-lab spend.")]:
        st.markdown(f"<div style='display:flex;gap:10px;align-items:flex-start;background:#04080f;border-left:3px solid {clr};border-radius:0 8px 8px 0;padding:9px 13px;margin:4px 0;'><span class='badge {RANK_CSS[rank]}'>{rank}</span><span style='color:#5a8090;font-size:.85rem;'>{rec}</span></div>",unsafe_allow_html=True)
    render_citations(papers,5)

# ──────────────────────────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────────────────────────
st.markdown("<div class='divider'></div><p style='text-align:center;color:#061828;font-size:.72rem;'>Protellect · Data: UniProt · ClinVar · AlphaFold DB · PubMed · NCBI Gene · Not a substitute for expert clinical judgment.</p>",unsafe_allow_html=True)
