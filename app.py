from __future__ import annotations
# ═══════════════════════════════════════════════════════════════════
#  Protellect v6 — single-file, no local imports
#  All new: pursue banner · disease→proteins · GPCR detail ·
#           genomic visual · mutation cascade · source links ·
#           plain-language terms · CSV standalone · fixed empty sections
# ═══════════════════════════════════════════════════════════════════

import re, time, json, math, io
from collections import Counter, defaultdict

import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Protellect", page_icon="🧬",
                   layout="wide", initial_sidebar_state="expanded")

# ─── CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;}
.stApp{background:#04080f;}
[data-testid="stSidebar"]{background:#05101f!important;border-right:1px solid #0c2040;}
.ph{background:linear-gradient(135deg,#04080f,#050e20);border:1px solid #0c2040;border-radius:14px;
  padding:1rem 1.8rem .7rem;margin-bottom:.5rem;position:relative;overflow:hidden;}
.ph::after{content:'';position:absolute;bottom:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,#00e5ff44,transparent);}
.pt{font-size:1.8rem;font-weight:800;letter-spacing:-.5px;margin:0;
  background:linear-gradient(90deg,#00e5ff,#6478ff,#00e5ff);background-size:200%;
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  animation:sh 4s linear infinite;}
.ps{color:#1e4060;font-size:.8rem;margin:.2rem 0 0;}
@keyframes sh{0%{background-position:0%}100%{background-position:200%}}
.pursue-yes{background:linear-gradient(135deg,#0a0205,#12040a);border:2px solid #ff2d55;
  border-radius:12px;padding:.9rem 1.4rem;margin-bottom:.8rem;display:flex;gap:12px;align-items:center;}
.pursue-no{background:linear-gradient(135deg,#040808,#05101e);border:2px dashed #3a6080;
  border-radius:12px;padding:.9rem 1.4rem;margin-bottom:.8rem;display:flex;gap:12px;align-items:center;}
.pursue-caution{background:linear-gradient(135deg,#0a0900,#120e00);border:2px solid #ffd60a;
  border-radius:12px;padding:.9rem 1.4rem;margin-bottom:.8rem;display:flex;gap:12px;align-items:center;}
.mc{background:linear-gradient(145deg,#06111e,#040d18);border:1px solid #0c2040;
  border-radius:12px;padding:.9rem 1rem;text-align:center;position:relative;overflow:hidden;transition:transform .2s;}
.mc:hover{transform:translateY(-2px);}
.mc::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--acc);}
.mv{font-size:1.7rem;font-weight:800;line-height:1;color:var(--clr,#00e5ff);}
.ml2{font-size:.67rem;color:#1e4060;margin-top:3px;text-transform:uppercase;letter-spacing:.7px;}
.card{background:#06111e;border:1px solid #0c2040;border-radius:12px;padding:1rem 1.3rem;margin-bottom:.7rem;}
.card h4{color:#00e5ff;font-size:.88rem;font-weight:700;margin:0 0 .4rem;}
.card p{color:#3a6080;font-size:.82rem;line-height:1.6;margin:0;}
.badge{display:inline-block;padding:2px 9px;border-radius:16px;font-size:.67rem;font-weight:800;}
.bC{background:rgba(255,45,85,.12);color:#ff2d55;border:1px solid #ff2d5540;}
.bH{background:rgba(255,140,66,.12);color:#ff8c42;border:1px solid #ff8c4240;}
.bM{background:rgba(255,214,10,.1);color:#ffd60a;border:1px solid #ffd60a35;}
.bN{background:rgba(58,90,122,.2);color:#3a6080;border:1px solid #1e404050;}
.stTabs{position:sticky;top:0;z-index:100;background:#04080f;padding-top:3px;}
.stTabs [data-baseweb="tab-list"]{background:#04080f!important;gap:3px;border-bottom:1px solid #0c2040;}
.stTabs [data-baseweb="tab"]{background:transparent;border-radius:8px 8px 0 0;
  padding:6px 14px;color:#1a3a5a!important;font-weight:600;font-size:.82rem;}
.stTabs [aria-selected="true"]{background:#06111e!important;color:#00e5ff!important;border-bottom:2px solid #00e5ff!important;}
.sh2{display:flex;align-items:center;gap:8px;margin:0 0 .7rem;padding-bottom:5px;border-bottom:1px solid #0c2040;}
.sh2 h3{color:#a0c8e8;font-size:.9rem;font-weight:700;margin:0;}
.dv{border:none;border-top:1px solid #091830;margin:1.1rem 0;}
.cite{border-left:2px solid #00e5ff22;padding:6px 10px;margin:3px 0;background:#040e1c;border-radius:0 8px 8px 0;}
.cite a{color:#2a80a4;text-decoration:none;font-size:.78rem;}
.cite a:hover{color:#00e5ff;}
.cm{color:#0e2840;font-size:.7rem;margin-top:1px;}
.src-badge{display:inline-block;background:#04080f;border:1px solid #1e4060;color:#2a6080;
  padding:1px 8px;border-radius:6px;font-size:.68rem;margin-left:5px;text-decoration:none;}
.src-badge:hover{border-color:#00e5ff44;color:#4a90c0;}
.pt2{width:100%;border-collapse:collapse;font-size:.79rem;}
.pt2 thead tr{background:#040d18;}
.pt2 th{color:#00e5ff;padding:7px 10px;text-align:left;font-size:.66rem;font-weight:700;
  text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid #0c2040;}
.pt2 td{padding:7px 10px;border-bottom:1px solid #060f1c;color:#4a7090;vertical-align:middle;}
.pt2 tr:hover td{background:#05101e;}
.sb-t{font-size:.63rem;font-weight:700;color:#0e2840;text-transform:uppercase;
  letter-spacing:1px;margin:.8rem 0 .3rem;padding-bottom:3px;border-bottom:1px solid #0c2040;}
.stButton>button{background:linear-gradient(135deg,#003d55,#002868)!important;
  color:#00e5ff!important;border:1px solid #00e5ff22!important;border-radius:8px!important;font-weight:700!important;}
.stButton>button:hover{border-color:#00e5ff55!important;box-shadow:0 4px 18px rgba(0,229,255,.15)!important;}
.stTextInput input,.stTextArea textarea{background:#040d18!important;border:1px solid #0c2040!important;color:#c0d8f8!important;border-radius:8px!important;}
details{border:1px solid #0c2040!important;border-radius:10px!important;background:#050f1d!important;}
.gi-critical{background:#0d020a;border:2px solid #ff2d55;border-radius:12px;padding:1.1rem 1.4rem;margin-bottom:.7rem;}
.gi-moderate{background:#0a0900;border:2px solid #ffd60a;border-radius:12px;padding:1.1rem 1.4rem;margin-bottom:.7rem;}
.gi-redundant{background:#04080f;border:2px dashed #3a6080;border-radius:12px;padding:1.1rem 1.4rem;margin-bottom:.7rem;}
.gi-unknown{background:#04080f;border:1px solid #1e4060;border-radius:12px;padding:1.1rem 1.4rem;margin-bottom:.7rem;}
.gi-stat{display:inline-block;background:#04080f;border-radius:7px;padding:4px 10px;margin:3px 3px 0 0;font-size:.74rem;}
.plain{color:#2a5070;font-size:.76rem;font-style:italic;}
.dis-row{display:flex;align-items:flex-start;gap:10px;background:#050e1c;border:1px solid #0c2040;
  border-radius:9px;padding:10px 12px;margin:4px 0;}
.dis-name{color:#9ac0d8;font-size:.83rem;font-weight:600;}
.dis-desc{color:#0e2840;font-size:.74rem;margin-top:2px;line-height:1.5;}
.gpcr-box{background:linear-gradient(135deg,#030f1e,#04101c);border:1px solid #00e5ff22;border-radius:12px;padding:1.1rem 1.4rem;}
.cascade-stage{background:#050d1a;border:1px solid #0c2040;border-radius:10px;padding:.8rem 1rem;margin:.4rem 0;}
.cascade-stage h5{color:#00e5ff;font-size:.83rem;font-weight:700;margin:0 0 4px;}
.cascade-stage p{color:#2a5070;font-size:.78rem;margin:0;line-height:1.5;}
.bias-warn{background:#04080f;border:1px solid #ff2d5525;border-radius:10px;padding:.9rem 1.2rem;margin:.7rem 0;}
.bias-warn p{color:#2a1520;font-size:.81rem;margin:0;line-height:1.6;}
.dis-protein-row{display:flex;align-items:center;gap:10px;background:#050d18;border:1px solid #0c2040;
  border-radius:8px;padding:8px 12px;margin:4px 0;transition:border-color .2s;}
.dis-protein-row:hover{border-color:#1e4060;}
</style>
""", unsafe_allow_html=True)

# ─── Constants ─────────────────────────────────────────────────────
SIG_SCORE = {"pathogenic":5,"likely pathogenic":4,"pathogenic/likely pathogenic":4,
             "risk factor":3,"uncertain significance":2,"conflicting interpretations":2,
             "likely benign":1,"benign":0,"benign/likely benign":0,"not provided":-1}
AA_HYDRO  = {"A":1.8,"R":-4.5,"N":-3.5,"D":-3.5,"C":2.5,"Q":-3.5,"E":-3.5,"G":-0.4,
             "H":-3.2,"I":4.5,"L":3.8,"K":-3.9,"M":1.9,"F":2.8,"P":-1.6,"S":-0.8,
             "T":-0.7,"W":-0.9,"Y":-1.3,"V":4.2,"*":-10}
AA_CHG    = {"R":1,"K":1,"H":.5,"D":-1,"E":-1}
AA_NAMES  = {"A":"Alanine","R":"Arginine","N":"Asparagine","D":"Aspartate","C":"Cysteine",
             "Q":"Glutamine","E":"Glutamate","G":"Glycine","H":"Histidine","I":"Isoleucine",
             "L":"Leucine","K":"Lysine","M":"Methionine","F":"Phenylalanine","P":"Proline",
             "S":"Serine","T":"Threonine","W":"Tryptophan","Y":"Tyrosine","V":"Valine"}
RANK_CLR  = {"CRITICAL":"#ff2d55","HIGH":"#ff8c42","MEDIUM":"#ffd60a","NEUTRAL":"#3a5a7a"}
RANK_CSS  = {"CRITICAL":"bC","HIGH":"bH","MEDIUM":"bM","NEUTRAL":"bN"}
ESEARCH   = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

# Plain-language term pairs
PLAIN = {
    "apoptosis":"cell death (apoptosis)","phosphorylation":"chemical tagging (phosphorylation)",
    "haploinsufficiency":"half-dose shortage (haploinsufficiency)",
    "missense":"letter-swap mutation (missense)","nonsense":"early-stop mutation (stop-gain)",
    "frameshift":"reading-frame shift (frameshift)","splice":"splice-site disruption",
    "dominant negative":"protein blocker (dominant-negative)","gain of function":"hyperactive mutation (gain-of-function)",
    "loss of function":"broken gene (loss-of-function)","germline":"heritable / born-with (germline)",
    "somatic":"acquired / developed (somatic)","heterozygous":"one-copy affected (heterozygous)",
    "homozygous":"both-copies affected (homozygous)","GPCR":"cell-surface signal receiver (GPCR)",
    "second messenger":"internal signal relay (second messenger)","G-protein":"signal relay switch (G-protein)",
    "kinase":"protein tagger/activator (kinase)","phenotype":"observable trait (phenotype)",
    "pathogenic":"disease-causing (pathogenic)","benign":"harmless variant (benign)",
    "VUS":"unknown-significance variant (VUS)","variant":"DNA spelling change (variant)",
}

GOAL_OPTIONS = ["🎯 Identify therapeutic targets","🔬 Understand disease mechanism",
                "💊 Drug discovery & development","📊 Biomarker identification",
                "🧬 Basic research / functional characterisation",
                "🧪 Experimental pathway prioritisation","📋 Clinical variant interpretation",
                "✏️ Custom goal (type below)"]

def p(term): return PLAIN.get(term, term)
def badge(rank): return f"<span class='badge {RANK_CSS.get(rank,'bN')}'>{rank}</span>"
def sh(icon, title): st.markdown(f"<div class='sh2'><span style='font-size:1.1rem'>{icon}</span><h3>{title}</h3></div>", unsafe_allow_html=True)
def mc(val, label, clr="#00e5ff", acc=None):
    a = acc or f"linear-gradient(90deg,{clr},{clr}88)"
    return f"<div class='mc' style='--clr:{clr};--acc:{a};'><div class='mv'>{val}</div><div class='ml2'>{label}</div></div>"
def src_link(label, url): return f"<a class='src-badge' href='{url}' target='_blank'>↗ {label}</a>"
def score_rank(s, sens=50):
    shift=(sens-50)/100
    if s>=5: return "CRITICAL"
    if s>=4-shift: return "HIGH"
    if s>=2-shift: return "MEDIUM"
    return "NEUTRAL"
def ml_rank_fn(ml, sens=50):
    shift=(sens-50)/200
    if ml>=.85-shift: return "CRITICAL"
    if ml>=.65-shift: return "HIGH"
    if ml>=.40-shift: return "MEDIUM"
    return "NEUTRAL"
def parse_aa(name):
    aa3={"Ala":"A","Arg":"R","Asn":"N","Asp":"D","Cys":"C","Gln":"Q","Glu":"E","Gly":"G",
         "His":"H","Ile":"I","Leu":"L","Lys":"K","Met":"M","Phe":"F","Pro":"P","Ser":"S",
         "Thr":"T","Trp":"W","Tyr":"Y","Val":"V","Ter":"*","Xaa":"X"}
    m=re.search(r"p\.([A-Z][a-z]{2})\d+([A-Z][a-z]{2}|Ter|\*)",name or "")
    return (aa3.get(m.group(1),"?"),aa3.get(m.group(2),"?")) if m else ("?","?")

# ─── API functions ─────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_uniprot(query):
    base="https://rest.uniprot.org/uniprotkb"
    if re.match(r"^[OPQ][0-9][A-Z0-9]{3}[0-9]$|^[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$",query.strip(),re.I):
        r=requests.get(f"{base}/{query.strip().upper()}",headers={"Accept":"application/json"},timeout=20)
        r.raise_for_status(); return r.json()
    for qry in [f"gene:{query} AND reviewed:true AND organism_id:9606",
                f"({query}) AND reviewed:true AND organism_id:9606", query]:
        r=requests.get(f"{base}/search",params={"query":qry,"format":"json","size":1},
                       headers={"Accept":"application/json"},timeout=20)
        r.raise_for_status(); res=r.json().get("results",[])
        if res:
            uid=res[0]["primaryAccession"]
            r2=requests.get(f"{base}/{uid}",headers={"Accept":"application/json"},timeout=20)
            r2.raise_for_status(); return r2.json()
    raise ValueError(f"No UniProt entry for '{query}'. Try a UniProt accession (e.g. P04637).")

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_clinvar(gene, max_v=150):
    try:
        r=requests.get(ESEARCH,params={"db":"clinvar","term":f"{gene}[gene]","retmax":max_v,"retmode":"json"},timeout=20)
        r.raise_for_status(); ids=r.json().get("esearchresult",{}).get("idlist",[])
    except: return {"variants":[],"summary":{}}
    if not ids: return {"variants":[],"summary":{}}
    variants=[]
    for i in range(0,len(ids),100):
        try:
            r2=requests.get(ESUMMARY,params={"db":"clinvar","id":",".join(ids[i:i+100]),"retmode":"json"},timeout=30)
            r2.raise_for_status(); data=r2.json().get("result",{})
            for uid in data.get("uids",[]):
                e=data.get(uid,{}); gc=e.get("germline_classification",{})
                sig=gc.get("description","Not provided"); sc=SIG_SCORE.get(sig.lower().strip(),0)
                traits=[t.get("trait_name","") for t in e.get("trait_set",{}).get("trait",[]) if t.get("trait_name")]
                locs=e.get("location_list",[{}]); vset=e.get("variation_set",[{}])
                variants.append({
                    "uid":uid,"title":e.get("title",""),
                    "variant_name":vset[0].get("variation_name","") if vset else "",
                    "sig":sig,"score":sc,"condition":"; ".join(traits) if traits else "Not specified",
                    "origin":e.get("origin",{}).get("origin",""),"review":gc.get("review_status",""),
                    "start":locs[0].get("start","") if locs else "",
                    "somatic":bool(e.get("somatic_classifications",{})),
                    "url":f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{e.get('variation_id',uid)}/",
                })
        except: pass
        time.sleep(0.1)
    variants.sort(key=lambda x:-x["score"])
    sigs=Counter(v["sig"] for v in variants)
    conds=Counter()
    for v in variants:
        for c in v["condition"].split(";"):
            c=c.strip()
            if c and c!="Not specified": conds[c]+=1
    return {"variants":variants,"summary":{"total":len(variants),"by_sig":dict(sigs.most_common(8)),
            "top_conds":dict(conds.most_common(10)),"pathogenic":sum(1 for v in variants if v["score"]>=4),
            "vus":sum(1 for v in variants if v["score"]==2)}}

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_disease_proteins(disease_name, max_genes=15):
    """Search ClinVar for all genes/proteins linked to a disease."""
    try:
        query=f'"{disease_name}"[dis] AND (pathogenic[clnsig] OR "likely pathogenic"[clnsig])'
        r=requests.get(ESEARCH,params={"db":"clinvar","term":query,"retmax":200,"retmode":"json"},timeout=20)
        r.raise_for_status(); ids=r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return []
        r2=requests.get(ESUMMARY,params={"db":"clinvar","id":",".join(ids[:200]),"retmode":"json"},timeout=30)
        r2.raise_for_status(); data=r2.json().get("result",{})
        gene_map=defaultdict(lambda:{"count":0,"conditions":set(),"sigs":[],"uid":""})
        for uid in data.get("uids",[]):
            e=data.get(uid,{}); gs=e.get("gene_sort","") or e.get("genes",{}).get("gene",{}).get("symbol","")
            if not gs:
                vset=e.get("variation_set",[{}])
                if vset: gs=vset[0].get("gene_id","")
            gc=e.get("germline_classification",{}); sig=gc.get("description","")
            traits=[t.get("trait_name","") for t in e.get("trait_set",{}).get("trait",[]) if t.get("trait_name")]
            gene_map[gs]["count"]+=1
            gene_map[gs]["sigs"].append(sig)
            gene_map[gs]["uid"]=uid
            for t in traits: gene_map[gs]["conditions"].add(t)
        results=[]
        for gene,info in sorted(gene_map.items(),key=lambda x:-x[1]["count"]):
            if not gene or gene=="0": continue
            results.append({"gene":gene,"n_pathogenic":info["count"],
                           "conditions":list(info["conditions"])[:3],
                           "sigs":list(set(info["sigs"]))[:3],
                           "clinvar_url":f"https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]+{disease_name}[disease]"})
        return results[:max_genes]
    except: return []

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_pdb(uid):
    if not uid: return ""
    try:
        r=requests.get(f"https://alphafold.ebi.ac.uk/api/prediction/{uid}",timeout=15)
        if r.status_code==404: return ""
        r.raise_for_status(); entries=r.json()
        if not entries: return ""
        r2=requests.get(entries[0].get("pdbUrl",""),timeout=30); r2.raise_for_status(); return r2.text
    except: return ""

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_papers(gene, n=6):
    try:
        r=requests.get(ESEARCH,params={"db":"pubmed","term":gene,"retmax":n*2,"retmode":"json","sort":"relevance"},timeout=15)
        r.raise_for_status(); ids=r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return []
        r2=requests.get(ESUMMARY,params={"db":"pubmed","id":",".join(ids),"retmode":"json"},timeout=15)
        r2.raise_for_status(); data=r2.json().get("result",{})
        papers=[]
        for uid in data.get("uids",[]):
            e=data.get(uid,{})
            authors=", ".join(a.get("name","") for a in e.get("authors",[])[:3])
            if len(e.get("authors",[]))>3: authors+=" et al."
            pt=[p2.get("value","").lower() for p2 in e.get("pubtype",[])]
            sc=(3 if "review" in pt else 0)+(2 if e.get("pubdate","")[:4]>="2020" else 0)
            papers.append({"pmid":uid,"title":e.get("title","No title"),"authors":authors,
                           "journal":e.get("source",""),"year":e.get("pubdate","")[:4],
                           "url":f"https://pubmed.ncbi.nlm.nih.gov/{uid}/","score":sc,"pt":pt})
        return sorted(papers,key=lambda x:-x["score"])[:n]
    except: return []

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_ncbi_gene(symbol):
    try:
        r=requests.get(ESEARCH,params={"db":"gene","term":f"{symbol}[gene name] AND Homo sapiens[organism] AND alive[property]","retmax":1,"retmode":"json"},timeout=15)
        r.raise_for_status(); ids=r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return {}
        gid=ids[0]
        r2=requests.get(ESUMMARY,params={"db":"gene","id":gid,"retmode":"json"},timeout=15)
        r2.raise_for_status(); e=r2.json().get("result",{}).get(gid,{})
        gi=e.get("genomicinfo",[{}])[0] if e.get("genomicinfo") else {}
        return {"id":gid,"chr":e.get("chromosome",""),"map":e.get("maplocation",""),
                "summary":e.get("summary",""),"start":gi.get("chrstart",""),
                "stop":gi.get("chrstop",""),"exons":gi.get("exoncount",""),
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

def ml_score_variants(variants, sens=50):
    out=[]
    for v in variants:
        name=v.get("variant_name","") or v.get("title","")
        orig,alt=parse_aa(name)
        hd=abs(AA_HYDRO.get(orig,0)-AA_HYDRO.get(alt,0))
        cd=abs(AA_CHG.get(orig,0)-AA_CHG.get(alt,0))
        stop=float(alt=="*"); frame=float("frame" in name.lower())
        stars={"practice guideline":1,"reviewed by expert panel":.9,
               "criteria provided, multiple submitters":.7,"criteria provided, single submitter":.5}.get(v.get("review","").lower(),.2)
        base=v.get("score",0)/5.0
        ml=min(1.0,base*.5+stop*.25+frame*.15+(hd/10)*.05+cd*.03+stars*.02)
        vc=dict(v); vc["ml"]=round(float(ml),3); vc["ml_rank"]=ml_rank_fn(ml,sens)
        vc["rank"]=score_rank(v.get("score",0),sens)
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
            d=c.get("disease",{})
            out.append({"name":d.get("diseaseId",d.get("diseaseAcronym","Unknown")),
                        "desc":d.get("description",""),
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
            t=c.get("texts",[])
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
    return any(x in " ".join(kws) for x in ["gpcr","g protein","rhodopsin","adrenergic","muscarinic","serotonin receptor"])
def g_gpcr_class(p):
    kws=[k.get("value","") for k in p.get("keywords",[])]
    fn=g_func(p).lower()
    coupling=[]
    if "gi" in fn or "inhibit" in fn: coupling.append("Gi/o (↓ cAMP)")
    if "gs" in fn or "stimulat" in fn: coupling.append("Gs (↑ cAMP)")
    if "gq" in fn or "phospholipase" in fn or "calcium" in fn: coupling.append("Gq/11 (↑ Ca²⁺)")
    if "g12" in fn or "g13" in fn: coupling.append("G12/13 (Rho signalling)")
    return {"coupling": coupling or ["Unknown coupling"], "keywords": kws}
def g_ptype(p):
    kws=[k.get("value","").lower() for k in p.get("keywords",[])]
    if any("kinase" in k for k in kws): return "kinase"
    if any("gpcr" in k or "g protein" in k for k in kws): return "gpcr"
    if any("transcription" in k for k in kws): return "transcription_factor"
    if any("receptor" in k for k in kws): return "receptor"
    return "general"

# ─── Genomic integrity ─────────────────────────────────────────────
def compute_gi(cv, protein_length):
    variants=cv.get("variants",[]); total=len(variants)
    germline=[v for v in variants if not v.get("somatic",False)]
    pathogenic=[v for v in germline if v.get("score",0)>=4]
    vus=[v for v in germline if v.get("score",0)==2]
    benign=[v for v in germline if v.get("score",0)<=0]
    n_p=len(pathogenic); n_g=max(len(germline),1); length=max(protein_length or 1,1)
    density=n_p/n_g; per100=(n_p/length)*100
    if total<10:
        return dict(verdict="UNDERSTUDIED",label="Insufficient ClinVar data",css="gi-unknown",
                    color="#1e6080",icon="❓",pursue="neutral",density=density,per100=per100,
                    n_pathogenic=n_p,n_vus=len(vus),n_benign=len(benign),n_total=total,n_germline=len(germline),
                    explanation="Too few ClinVar entries to draw conclusions.",pathogenic_list=pathogenic)
    elif n_p==0:
        return dict(verdict="NO DISEASE VARIANTS",label="Zero pathogenic / likely-pathogenic germline variants in ClinVar",
                    css="gi-redundant",color="#3a5a7a",icon="⚪",pursue="deprioritise",density=0,per100=0,
                    n_pathogenic=0,n_vus=len(vus),n_benign=len(benign),n_total=total,n_germline=len(germline),
                    explanation=(f"Despite {total} ClinVar entries, not a single germline variant causes a Mendelian disease. "
                                 "This protein may be redundant or bypassable in biochemical signalling. "
                                 "β2-arrestin (ARRB2), β-adrenergic receptors and GRKs share this pattern — "
                                 "extensively studied but without confirmed dominant disease variants."),
                    pathogenic_list=[])
    elif density<0.01 and n_p<5:
        return dict(verdict="VERY LOW DISEASE BURDEN",label=f"Only {n_p} of {len(germline)} germline variants are disease-causing",
                    css="gi-redundant",color="#4a6a30",icon="🟡",pursue="caution",density=density,per100=per100,
                    n_pathogenic=n_p,n_vus=len(vus),n_benign=len(benign),n_total=total,n_germline=len(germline),
                    explanation="Very low pathogenic density. Check if interaction partners carry the actual disease burden.",
                    pathogenic_list=pathogenic)
    elif per100>=1 or (n_p>=20 and density>=0.05):
        return dict(verdict="DISEASE-CRITICAL",label=f"{n_p} disease-causing variants · {per100:.1f} per 100 aa",
                    css="gi-critical",color="#ff2d55",icon="🔴",pursue="prioritise",density=density,per100=per100,
                    n_pathogenic=n_p,n_vus=len(vus),n_benign=len(benign),n_total=total,n_germline=len(germline),
                    explanation="Strong genomic evidence. This protein is critical for human physiology. Genuine disease driver validated by human genetics.",
                    pathogenic_list=pathogenic)
    elif density>=0.05 or per100>=0.5:
        return dict(verdict="DISEASE-ASSOCIATED",label=f"{n_p} disease-causing variants ({density*100:.1f}% of total)",
                    css="gi-moderate",color="#ff8c42",icon="🟠",pursue="proceed",density=density,per100=per100,
                    n_pathogenic=n_p,n_vus=len(vus),n_benign=len(benign),n_total=total,n_germline=len(germline),
                    explanation="Meaningful disease association. Focus on confirmed P/LP variants only.",
                    pathogenic_list=pathogenic)
    else:
        return dict(verdict="MODERATE",label=f"{n_p} disease-causing variants ({density*100:.1f}%)",
                    css="gi-moderate",color="#ffd60a",icon="🟡",pursue="selective",density=density,per100=per100,
                    n_pathogenic=n_p,n_vus=len(vus),n_benign=len(benign),n_total=total,n_germline=len(germline),
                    explanation="Some association but low density. Do not extrapolate to nearby benign entries.",
                    pathogenic_list=pathogenic)

# ─── CSV processing ─────────────────────────────────────────────────
def detect_csv_type(df):
    cols=" ".join(c.lower() for c in df.columns)
    if any(k in cols for k in ["fold","logfc","log2","fpkm","rpkm","tpm","count","expr"]): return "expression"
    if any(k in cols for k in ["variant","mutation","chrom","ref","alt","rsid","pos"]): return "variants"
    if any(k in cols for k in ["protein","abundance","intensity","peptide","spectral"]): return "proteomics"
    if any(k in cols for k in ["pvalue","p_val","padj","fdr","qvalue"]): return "stats"
    return "generic"

def summarise_assay(df, csv_type):
    n_rows,n_cols=len(df),len(df.columns)
    summaries={"expression":f"Gene expression dataset: {n_rows:,} genes/transcripts across {n_cols} columns. "
                             "Likely contains fold-change or normalised counts from RNA-seq, microarray, or qPCR.",
               "variants":f"Variant dataset: {n_rows:,} genetic variants across {n_cols} columns. "
                          "May include genomic positions, reference/alt alleles, or clinical classifications.",
               "proteomics":f"Proteomics dataset: {n_rows:,} proteins/peptides. "
                            "May include mass-spectrometry intensity values or protein abundance ratios.",
               "stats":f"Statistical results table: {n_rows:,} entries. "
                       "Contains p-values or adjusted significance scores — likely from a differential analysis.",
               "generic":f"Dataset: {n_rows:,} rows × {n_cols} columns. Column headers: {', '.join(df.columns[:6].tolist())}."}
    return summaries.get(csv_type, summaries["generic"])

def analyse_csv_standalone(df, csv_type, goal):
    findings=[]
    fc_col=next((c for c in df.columns if any(k in c.lower() for k in ["fold","logfc","log2fc"])),None)
    p_col=next((c for c in df.columns if any(k in c.lower() for k in ["pvalue","p_val","padj","fdr"])),None)
    gene_col=next((c for c in df.columns if any(k in c.lower() for k in ["gene","symbol","name","id"])),None)
    findings.append(("📋 Dataset type",f"Auto-detected: **{csv_type.replace('_',' ').title()}** · {len(df):,} rows · {len(df.columns)} columns"))
    if fc_col and df[fc_col].dtype in [float,int,'float64','int64']:
        up=(df[fc_col]>1).sum(); dn=(df[fc_col]<-1).sum()
        findings.append(("📈 Expression changes (cell activity level changes)",
                         f"Upregulated (increased activity): **{up:,}** genes · Downregulated (decreased activity): **{dn:,}** genes · Threshold: |log₂FC| > 1"))
    if p_col and df[p_col].dtype in [float,'float64']:
        sig=(df[p_col]<0.05).sum()
        findings.append(("📊 Statistically significant hits (reliable results)",f"**{sig:,}** entries with p < 0.05 out of {len(df):,} total"))
    if gene_col:
        top5=df[gene_col].dropna().astype(str).head(5).tolist()
        findings.append(("🧬 Top gene identifiers",f"{', '.join(top5)}{'...' if len(df)>5 else ''}"))
    # Goal-specific
    goal_l=goal.lower()
    if "therapeutic" in goal_l or "drug" in goal_l:
        findings.append(("🎯 Drug target insight","Filter for genes with: (1) fold-change >2, (2) p<0.01, AND (3) known ClinVar pathogenic variants. Only proteins at this intersection are credible targets."))
    if "biomarker" in goal_l:
        findings.append(("📊 Biomarker candidate strategy","Biomarker candidates = genes significantly changed in disease state + detectable in accessible tissue (blood, urine). Cross-reference expression changes with OMIM disease gene list."))
    if "mechanism" in goal_l:
        findings.append(("🔬 Mechanistic insight","Perform pathway enrichment (GSEA/ORA) on significant genes. Prioritise pathways with ≥3 significant hits AND known genetic disease association."))
    return findings

# ─── 3-D viewer ─────────────────────────────────────────────────────
def viewer_html(pdb_text, scored, height=480):
    path_pos={}
    for v in scored[:50]:
        pos=v.get("start") or v.get("position")
        try:
            p2=int(pos)
            path_pos[p2]={"rank":v.get("ml_rank","NEUTRAL"),"ml":v.get("ml",0),
                          "cond":v.get("condition","")[:60],"sig":v.get("sig",""),
                          "var":v.get("variant_name","")[:40],"url":v.get("url","")}
        except: pass
    pp_js=json.dumps({str(k):v for k,v in path_pos.items()})
    pdb_esc=pdb_text.replace("`","\\`").replace("\\","\\\\")
    return f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.1.0/3Dmol-min.js"></script>
<style>*{{margin:0;padding:0;box-sizing:border-box;}}body{{background:#04080f;font-family:Inter,sans-serif;display:flex;flex-direction:column;height:{height}px;}}
#ctrl{{display:flex;gap:4px;padding:6px 8px;background:#050f1e;border-bottom:1px solid #0c2040;flex-wrap:wrap;flex-shrink:0;}}
.btn{{background:#05101e;color:#2a5070;border:1px solid #0c2040;padding:3px 10px;border-radius:14px;cursor:pointer;font-size:11px;transition:all .2s;}}
.btn:hover,.btn.on{{background:#00e5ff;color:#000;font-weight:700;border-color:#00e5ff;}}
#wrap{{position:relative;flex:1;}}#v{{width:100%;height:100%;}}
#panel{{position:absolute;top:8px;right:8px;width:230px;background:rgba(4,8,15,.95);border:1px solid #0c2040;border-radius:10px;padding:12px;display:none;backdrop-filter:blur(8px);max-height:88%;overflow-y:auto;}}
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
<div class="li"><div class="ld" style="background:#1565C0"></div>Very confident (pLDDT ≥90)</div>
<div class="li"><div class="ld" style="background:#29B6F6"></div>Confident (70–90)</div>
<div class="li"><div class="ld" style="background:#FDD835"></div>Low confidence (50–70)</div>
<div class="li"><div class="ld" style="background:#FF7043"></div>Very low (&lt;50)</div>
<div class="li"><div class="ld" style="background:#ff2d55;border:1px solid #fff5;"></div>Disease-causing variant</div>
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
html+=`<span style="color:${{rc[inf.rank]}};font-weight:800;font-size:11px;display:block;margin-bottom:5px;">${{inf.rank}}</span>`;}}
html+=`<div class="pr"><span class="pk">Residue (building block)</span><span class="pv">${{r1}} (${{full}})</span></div>`;
html+=`<div class="pr"><span class="pk">Position in chain</span><span class="pv">${{pos}}</span></div>`;
html+=`<div class="pr"><span class="pk">Model confidence</span><span class="pv">${{pl.toFixed(1)}} (${{cl}})</span></div>`;
html+=`<div class="pr"><span class="pk">Hydropathy (water-love)</span><span class="pv">${{hy[r1]!==undefined?hy[r1].toFixed(1):'?'}}</span></div>`;
if(inf){{html+='<hr style="border-color:#0c2040;margin:5px 0;">';
html+=`<div class="pr"><span class="pk">Variant (DNA change)</span><span class="pv" style="font-size:10px;">${{inf.var||'—'}}</span></div>`;
html+=`<div class="pr"><span class="pk">Clinical significance</span><span class="pv" style="font-size:10px;">${{inf.sig||'—'}}</span></div>`;
html+=`<div class="pr"><span class="pk">ML disease score</span><span class="pv" style="color:#00e5ff;">${{(inf.ml*100).toFixed(0)}}%</span></div>`;
if(inf.url)html+=`<a href="${{inf.url}}" target="_blank" style="color:#2a80a4;font-size:10px;display:block;margin-top:4px;">↗ View in ClinVar</a>`;
if(inf.cond)html+=`<div style="margin-top:4px;color:#0e2840;font-size:10px;line-height:1.4;">${{inf.cond}}</div>`;}}
document.getElementById('pt').textContent=r3+pos;document.getElementById('pc').innerHTML=html;document.getElementById('panel').style.display='block';}});
function ss(style,btn){{curStyle=style;document.querySelectorAll('.btn').forEach(b=>b.classList.remove('on'));btn.classList.add('on');ap();}}
function toggleSpin(){{spinning=!spinning;v.spin(spinning?'y':false,.6);const b=document.getElementById('spb');b.textContent=spinning?'⏸ Stop':'▶ Spin';b.classList.toggle('on',spinning);}}
function toggleV(){{showV=!showV;ap();}}
function toggleL(){{showL=!showL;v.removeAllLabels();if(showL)Object.entries(pp).forEach(([pos,info])=>{{if(info.rank==='CRITICAL'||info.rank==='HIGH')v.addLabel('P'+pos,{{position:{{resi:parseInt(pos),atom:'CA'}},backgroundColor:'#ff2d55',backgroundOpacity:.8,fontSize:9,fontColor:'white',borderRadius:3}});}});v.render();}}
</script></body></html>""".replace("{pp_js}",pp_js)

# ─── Mutation cascade HTML animation ──────────────────────────────
def mutation_cascade_html(gene, is_gpcr, pursue, top_variants):
    """Full-page HTML slider showing how a mutation cascades through biology."""
    top_var = top_variants[0] if top_variants else {}
    var_name = (top_var.get("variant_name","") or "Unknown variant")[:30]
    condition = (top_var.get("condition","Unknown disease"))[:40]
    pursue_color = "#ff2d55" if pursue=="prioritise" else "#ffd60a" if pursue in ["proceed","selective"] else "#3a5a7a"
    
    stages = [
        {"title":"① Healthy protein",
         "plain":"The normal, correctly folded protein doing its job",
         "desc":f"Wild-type {gene} is folded correctly. All domains functional. Signalling pathway intact.",
         "cell_color":"#00c896","shape":"circle","signal":100,"apoptosis":0},
        {"title":"② DNA spelling change (mutation) introduced",
         "plain":"A single letter in the DNA blueprint is changed",
         "desc":f"Variant {var_name} introduced. One amino acid (protein building block) replaced. Structure at risk.",
         "cell_color":"#ffd60a","shape":"circle","signal":80,"apoptosis":5},
        {"title":"③ Protein shape distortion (misfolding / instability)",
         "plain":"The protein loses its correct 3D shape",
         "desc":"Altered amino acid disrupts local folding. Domain stability reduced. Binding pocket geometry changed.",
         "cell_color":"#ff8c42","shape":"ellipse","signal":55,"apoptosis":15},
        {"title":"④ Signal receiver disrupted" + (" — GPCR uncoupled" if is_gpcr else " — pathway broken"),
         "plain":"The protein can no longer pass signals correctly into the cell",
         "desc":("GPCR coupling impaired. G-protein (signal relay switch) cannot be activated. "
                 "Second messenger (internal signal relay: cAMP / Ca²⁺) levels altered." if is_gpcr else
                 "Downstream pathway disrupted. Protein cannot bind partners or substrates correctly."),
         "cell_color":"#ff6b00","shape":"ellipse","signal":30,"apoptosis":30},
        {"title":"⑤ Cell stress response activated",
         "plain":"The cell recognises something is wrong and starts emergency protocols",
         "desc":"ER stress pathway activated. Unfolded protein response (UPR) triggered. Mitochondrial membrane potential changes.",
         "cell_color":"#ff4444","shape":"irregular","signal":15,"apoptosis":60},
        {"title":"⑥ Cell death (apoptosis) / shape change",
         "plain":"The cell either dies or changes shape, causing tissue damage",
         "desc":"Caspase cascade initiated (cell-death machinery). Cytoskeletal reorganisation. Cell rounding or blebbing.",
         "cell_color":"#ff2d55","shape":"fragments","signal":5,"apoptosis":90},
        {"title":f"⑦ Disease: {condition}",
         "plain":"The accumulated cell damage leads to a visible disease",
         "desc":f"Repeated cycles of cell dysfunction accumulate into the clinical presentation: {condition}. "
                f"Tissue-level pathology becomes detectable.",
         "cell_color":"#c0102a","shape":"fragments","signal":0,"apoptosis":100},
    ]
    
    stages_js = json.dumps(stages)
    
    return f"""<!DOCTYPE html><html><head>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:Inter,sans-serif;}}
body{{background:#04080f;color:#c0d8f8;padding:16px;}}
#slider-wrap{{margin-bottom:16px;}}
#stg-slider{{width:100%;-webkit-appearance:none;appearance:none;height:6px;
  border-radius:3px;background:linear-gradient(90deg,{pursue_color},#1e4060);outline:none;}}
#stg-slider::-webkit-slider-thumb{{-webkit-appearance:none;width:20px;height:20px;
  border-radius:50%;background:{pursue_color};cursor:pointer;box-shadow:0 0 10px {pursue_color}88;}}
#stage-title{{font-size:1rem;font-weight:800;color:{pursue_color};margin-bottom:3px;}}
#stage-plain{{font-size:.8rem;color:#3a8090;margin-bottom:10px;font-style:italic;}}
#stage-desc{{font-size:.82rem;color:#3a6080;line-height:1.6;margin-bottom:12px;}}
#stage-num{{color:#1e4060;font-size:.72rem;margin-bottom:8px;}}
.vis-row{{display:flex;gap:12px;align-items:flex-end;margin-bottom:12px;}}
.vis-col{{flex:1;background:#050d1a;border:1px solid #0c2040;border-radius:10px;padding:10px;text-align:center;}}
.vis-label{{font-size:.68rem;color:#1e4060;text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px;}}
.bar-wrap{{height:80px;background:#07152a;border-radius:6px;overflow:hidden;display:flex;align-items:flex-end;}}
.bar{{width:100%;border-radius:6px;transition:height .5s ease,background .5s ease;}}
.cell-vis{{width:60px;height:60px;margin:0 auto 4px;transition:all .5s ease;}}
.step-dots{{display:flex;gap:6px;justify-content:center;margin-top:8px;}}
.dot{{width:8px;height:8px;border-radius:50%;background:#0c2040;transition:background .3s;}}
.dot.active{{background:{pursue_color};box-shadow:0 0 8px {pursue_color}88;}}
</style></head><body>
<div id="stage-num">Stage <span id="sn">1</span> of 7</div>
<div id="stage-title">Loading…</div>
<div id="stage-plain"></div>
<div id="stage-desc"></div>
<div class="vis-row">
  <div class="vis-col">
    <div class="vis-label">Signal strength (how well the protein works)</div>
    <div class="bar-wrap"><div class="bar" id="sig-bar" style="height:100%;background:#00c896;"></div></div>
    <div style="color:#1e4060;font-size:.7rem;margin-top:4px;"><span id="sig-val">100</span>%</div>
  </div>
  <div class="vis-col">
    <div class="vis-label">Cell shape</div>
    <svg id="cell-svg" width="70" height="70" viewBox="0 0 70 70" style="display:block;margin:0 auto;">
      <ellipse id="cell-shape" cx="35" cy="35" rx="30" ry="30" fill="#00c89622" stroke="#00c896" stroke-width="2"/>
      <circle id="nucleus" cx="35" cy="35" r="10" fill="#1e6040" opacity="0.8"/>
    </svg>
  </div>
  <div class="vis-col">
    <div class="vis-label">Cell death risk (apoptosis)</div>
    <div class="bar-wrap"><div class="bar" id="apo-bar" style="height:0%;background:#ff2d55;"></div></div>
    <div style="color:#1e4060;font-size:.7rem;margin-top:4px;"><span id="apo-val">0</span>%</div>
  </div>
</div>
<div id="slider-wrap">
  <input type="range" id="stg-slider" min="0" max="6" value="0" step="1">
</div>
<div class="step-dots" id="dots"></div>
<script>
const stages={stages_js};
const dotsEl=document.getElementById('dots');
stages.forEach((_,i)=>{{const d=document.createElement('div');d.className='dot'+(i===0?' active':'');dotsEl.appendChild(d);}});
function update(idx){{
  const s=stages[idx];
  document.getElementById('stage-title').textContent=s.title;
  document.getElementById('stage-plain').textContent='"'+s.plain+'"';
  document.getElementById('stage-desc').textContent=s.desc;
  document.getElementById('sn').textContent=idx+1;
  document.getElementById('sig-bar').style.height=s.signal+'%';
  document.getElementById('sig-bar').style.background=s.cell_color;
  document.getElementById('sig-val').textContent=s.signal;
  document.getElementById('apo-bar').style.height=s.apoptosis+'%';
  document.getElementById('apo-val').textContent=s.apoptosis;
  // Cell shape
  const cs=document.getElementById('cell-shape');
  const nuc=document.getElementById('nucleus');
  if(s.shape==='circle'){{cs.setAttribute('rx',30);cs.setAttribute('ry',30);nuc.setAttribute('r',10);nuc.setAttribute('opacity','0.8');}}
  else if(s.shape==='ellipse'){{cs.setAttribute('rx',34);cs.setAttribute('ry',24);nuc.setAttribute('r',9);nuc.setAttribute('opacity','0.7');}}
  else if(s.shape==='irregular'){{cs.setAttribute('rx',36);cs.setAttribute('ry',20);nuc.setAttribute('r',7);nuc.setAttribute('opacity','0.5');}}
  else{{cs.setAttribute('rx',20);cs.setAttribute('ry',14);nuc.setAttribute('r',4);nuc.setAttribute('opacity','0.2');}}
  cs.setAttribute('fill',s.cell_color+'22');
  cs.setAttribute('stroke',s.cell_color);
  nuc.setAttribute('fill',s.cell_color+'88');
  document.querySelectorAll('.dot').forEach((d,i)=>d.classList.toggle('active',i===idx));
}}
update(0);
document.getElementById('stg-slider').addEventListener('input',function(){{update(parseInt(this.value));}});
</script></body></html>"""

def render_citations(papers, n=4):
    if not papers: return
    st.markdown("<div style='color:#0e2840;font-size:.65rem;text-transform:uppercase;letter-spacing:.8px;margin:.7rem 0 .3rem;'>📚 Supporting Literature <span style=\"color:#0a1828;font-size:.6rem;\">(click to open on PubMed)</span></div>", unsafe_allow_html=True)
    for p2 in papers[:n]:
        pt=" ".join(f"<span style='background:#07152a;color:#1a4060;font-size:.64rem;padding:1px 5px;border-radius:6px;margin-left:3px;'>{t.title()}</span>" for t in p2.get("pt",[])[:2])
        st.markdown(f"<div class='cite'><a href='{p2['url']}' target='_blank'>{p2['title'][:110]}</a>{pt}<div class='cm'>{p2['authors']} · {p2['journal']} · {p2['year']} · PMID {p2['pmid']}</div></div>", unsafe_allow_html=True)

def variant_landscape_fig(variants, protein_length, scored):
    if not variants: return None
    sig_c={5:"#ff2d55",4:"#ff6b55",3:"#ff8c42",2:"#ffd60a",1:"#2a6040",0:"#0e2840",-1:"#060f18"}
    sig_l={5:"Disease-causing (pathogenic)",4:"Likely disease-causing",3:"Risk factor",
           2:"Unknown significance (VUS)",1:"Likely harmless (likely benign)",0:"Harmless (benign)",-1:"Not classified"}
    ml_map={v.get("uid",""):v.get("ml",0) for v in scored}
    positions,ys,colours,labels,urls=[],[],[],[],[]
    for v in variants:
        try: pos_int=int(v.get("start",""))
        except: continue
        sc=v.get("score",-1); ml2=ml_map.get(v.get("uid",""),0)
        name2=(v.get("variant_name") or v.get("title",""))[:40]; url=v.get("url","")
        positions.append(pos_int); ys.append(max(sc,0)+ml2*.4)
        colours.append(sig_c.get(sc,"#0e2840"))
        labels.append(f"{name2}<br>{sig_l.get(sc,'?')}<br>ML score: {ml2:.2f}<extra></extra>")
        urls.append(url)
    if not positions: return None
    fig=go.Figure()
    for x,y,c in zip(positions,ys,colours):
        fig.add_trace(go.Scatter(x=[x,x],y=[0,y],mode="lines",line=dict(color=c,width=1),showlegend=False,hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=positions,y=ys,mode="markers",
        marker=dict(color=colours,size=7,opacity=.85,line=dict(color="#04080f",width=.5)),
        text=labels,hovertemplate="%{text}",showlegend=False))
    fig.add_hrect(y0=0,y1=.8,fillcolor="rgba(6,30,6,0.2)",line_width=0,annotation_text="Harmless zone",annotation_font_size=9,annotation_font_color="#1a4030")
    fig.add_hrect(y0=3.5,y1=6,fillcolor="rgba(80,0,20,0.15)",line_width=0,annotation_text="Disease-causing zone",annotation_font_size=9,annotation_font_color="#5a1020")
    maxpos=max(protein_length or 100,max(positions)+10)
    fig.update_layout(paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#1e4060",
        xaxis=dict(title="Position in protein chain (amino acid number)",range=[0,maxpos],gridcolor="#060f1c",color="#0e2840"),
        yaxis=dict(title="Disease severity score",range=[-0.1,6.2],
            tickvals=[0,2,4,5],ticktext=["Harmless","Unknown","Likely Disease","Disease-causing"],
            gridcolor="#060f1c",color="#0e2840"),
        height=270,margin=dict(t=8,b=30,l=90,r=8),hovermode="closest")
    return fig

# ─── Session state ──────────────────────────────────────────────────
for k,v0 in {"pdata":None,"cv":None,"pdb":"","papers":[],"scored":[],"gene":"","uid":"",
             "assay":"","last":"","csv_df":None,"csv_type":"","goal_label":GOAL_OPTIONS[0],
             "goal_custom":"","sensitivity":50,"gi":None,"partner_query":"",
             "partner_cv":None,"partner_gi":None,"disease_search":"","disease_proteins":[]}.items():
    if k not in st.session_state: st.session_state[k]=v0

# ─── Sidebar ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='text-align:center;padding:.3rem 0 .6rem;'><div style='font-size:1.6rem;'>🧬</div><div style='color:#00e5ff;font-size:1.1rem;font-weight:800;'>Protellect</div><div style='color:#0a2040;font-size:.68rem;'>Protein Intelligence Platform</div></div><div style='border-top:1px solid #0c2040;margin-bottom:.7rem;'></div>", unsafe_allow_html=True)

    st.markdown("<div class='sb-t'>🎯 Research Goal</div>", unsafe_allow_html=True)
    goal_label=st.selectbox("Goal",GOAL_OPTIONS,label_visibility="collapsed")
    goal_custom=""
    if "Custom" in goal_label:
        goal_custom=st.text_input("Describe your goal",placeholder="e.g. Find splice variants affecting exon 4…",label_visibility="collapsed")
    active_goal=goal_custom if "Custom" in goal_label else goal_label

    st.markdown("<div class='sb-t'>🔍 Protein Search</div>", unsafe_allow_html=True)
    query=st.text_input("Gene / UniProt ID",placeholder="TP53 · BRCA1 · P04637 · FLNC · ACM2",label_visibility="collapsed")
    search=st.button("🔬 Analyse Protein",use_container_width=True)

    st.markdown("<div class='sb-t'>🏥 Disease → Proteins</div>", unsafe_allow_html=True)
    disease_q=st.text_input("Search by disease name",placeholder="e.g. dilated cardiomyopathy · Glanzmann",label_visibility="collapsed",key="dis_q_inp")
    dis_search=st.button("🔎 Find Disease Proteins",use_container_width=True,key="dis_btn")
    if dis_search and disease_q:
        with st.spinner("Searching ClinVar for disease proteins..."):
            dp=fetch_disease_proteins(disease_q)
            st.session_state["disease_search"]=disease_q
            st.session_state["disease_proteins"]=dp

    st.markdown("<div class='sb-t'>📂 Wet-Lab Data (CSV)</div>", unsafe_allow_html=True)
    uploaded_csv=st.file_uploader("Upload CSV (any format)",type=["csv","tsv","txt"],label_visibility="collapsed")
    if uploaded_csv:
        try:
            sep="\t" if uploaded_csv.name.endswith((".tsv",".txt")) else ","
            df=pd.read_csv(uploaded_csv,sep=sep,on_bad_lines="skip")
            csv_type=detect_csv_type(df)
            st.session_state["csv_df"]=df; st.session_state["csv_type"]=csv_type
            # Assay summary in sidebar
            summary_text=summarise_assay(df,csv_type)
            st.markdown(f"<div style='background:#040d18;border:1px solid #0c3050;border-radius:8px;padding:8px 10px;margin-top:4px;'><div style='color:#4adaff;font-size:.76rem;font-weight:700;margin-bottom:3px;'>{uploaded_csv.name}</div><div style='color:#1a4060;font-size:.72rem;'>{csv_type.replace('_',' ').title()} · {len(df):,} rows</div><div style='color:#0d2840;font-size:.7rem;margin-top:3px;line-height:1.4;'>{summary_text[:200]}</div></div>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"CSV error: {e}")

    st.markdown("<div class='sb-t'>🧫 Assay Notes</div>", unsafe_allow_html=True)
    assay_txt=st.text_area("Assay description",height=70,placeholder="e.g. Western blot shows 3× expression increase…",label_visibility="collapsed")

    st.markdown("<div class='sb-t'>🎚️ Triage Sensitivity (how strict the filter is)</div>", unsafe_allow_html=True)
    sensitivity=st.slider("",0,100,st.session_state["sensitivity"],5,label_visibility="collapsed",
                          help="High = more variants flagged. Low = only the most certain variants elevated.")
    st.session_state["sensitivity"]=sensitivity
    sens_lbl="🔬 Strict" if sensitivity<30 else "⚖️ Balanced" if sensitivity<70 else "🔓 Sensitive"
    st.markdown(f"<div style='display:flex;justify-content:space-between;margin-top:1px;'><span style='color:#0e2840;font-size:.67rem;'>Strict</span><span style='color:#00e5ff;font-size:.7rem;font-weight:700;'>{sens_lbl}</span><span style='color:#0e2840;font-size:.67rem;'>Sensitive</span></div>", unsafe_allow_html=True)

    st.markdown("<div class='sb-t'>🔗 Compare Interaction Partner</div>", unsafe_allow_html=True)
    partner_q=st.text_input("Partner gene / UniProt ID",placeholder="e.g. ITGAL · FLNC · ARRB2",label_visibility="collapsed",key="partner_inp")
    fetch_partner=st.button("Compare Partner",use_container_width=True,key="partner_btn")
    if fetch_partner and partner_q:
        with st.spinner("Fetching partner data..."):
            try:
                p2=fetch_uniprot(partner_q); g2=g_gene(p2); uid2=p2.get("primaryAccession","")
                cv2=fetch_clinvar(g2,100); ln2=p2.get("sequence",{}).get("length",1)
                gi2=compute_gi(cv2,ln2)
                st.session_state["partner_query"]=partner_q
                st.session_state["partner_cv"]=cv2
                st.session_state["partner_gi"]={"gi":gi2,"gene":g2,"uid":uid2}
            except Exception as e: st.error(f"Partner: {e}")

    st.markdown("<div class='sb-t'>⚙️ Data Depth</div>", unsafe_allow_html=True)
    depth=st.selectbox("Depth",["Standard (150 variants)","Deep (400 variants)"],label_visibility="collapsed")
    max_v=150 if "Standard" in depth else 400

    # Sidebar protein summary
    if st.session_state["pdata"]:
        p3=st.session_state["pdata"]; gene3=st.session_state["gene"]; uid3=st.session_state["uid"]
        scored3=st.session_state["scored"]; cv3=st.session_state["cv"]
        st.markdown(f"<div style='border-top:1px solid #0c2040;margin:.6rem 0 .3rem;'></div><div style='background:#040d18;border:1px solid #0c2040;border-radius:8px;padding:7px 9px;'><div style='color:#00e5ff;font-weight:700;font-size:.88rem;'>{gene3}</div><div style='color:#0e2840;font-size:.7rem;'>{uid3}</div></div>", unsafe_allow_html=True)
        gi3=st.session_state.get("gi"); ds_scores={}
        for sv in scored3:
            for c2 in sv.get("condition","").split(";"):
                c2=c2.strip()
                if c2: ds_scores[c2]=max(ds_scores.get(c2,0),sv.get("ml",0))
        diseases3=g_diseases(p3)
        all_names=list(dict.fromkeys([d["name"] for d in diseases3]+[c2 for sv in cv3.get("variants",[]) for c2 in sv.get("condition","").split(";") if c2.strip() and c2.strip()!="Not specified"]))
        if all_names:
            st.markdown("<div class='sb-t'>🏥 Disease Affiliations</div>", unsafe_allow_html=True)
            for name3 in all_names[:8]:
                score3=ds_scores.get(name3,.4); rk3="CRITICAL" if score3>=.85 else "HIGH" if score3>=.65 else "MEDIUM" if score3>=.40 else "NEUTRAL"
                if any(k in name3.lower() for k in ["cancer","carcinoma","leukemia","sarcoma"]) and rk3=="MEDIUM": rk3="HIGH"
                css3=RANK_CSS[rk3]
                st.markdown(f"<div style='display:flex;align-items:center;gap:6px;margin:3px 0;'><span class='badge {css3}'>{rk3}</span><span style='color:#0e2840;font-size:.73rem;'>{name3[:32]}</span></div>", unsafe_allow_html=True)
        ptype3=g_ptype(p3)
        sugg3={"kinase":["ADP-Glo kinase assay","Phospho-proteomics","Inhibitor screen"],"gpcr":["cAMP (HTRF)","β-arrestin (BRET)","Radioligand binding"],"transcription_factor":["ChIP-seq","EMSA","Luciferase reporter"],"general":["Co-IP/AP-MS","CRISPR KO","Thermal shift"]}.get(ptype3,["Co-IP","CRISPR KO"])
        st.markdown("<div class='sb-t'>🔭 Suggested Experiments</div>", unsafe_allow_html=True)
        for s3 in sugg3: st.markdown(f"<div style='color:#0d2840;font-size:.73rem;margin:2px 0;'>▸ {s3}</div>", unsafe_allow_html=True)

# ─── Header ─────────────────────────────────────────────────────────
st.markdown("<div class='ph'><span class='pt'>🧬 Protellect</span><div class='ps'>AI-powered protein triage · Genetics-first · Eliminate wasted experiments</div></div>", unsafe_allow_html=True)

# ─── Disease proteins panel ─────────────────────────────────────────
if st.session_state["disease_proteins"]:
    dp_list=st.session_state["disease_proteins"]; dis_name=st.session_state["disease_search"]
    with st.expander(f"🏥 Disease → Proteins: '{dis_name}' — {len(dp_list)} genes found (ClinVar)", expanded=True):
        st.markdown(f"<div style='color:#1e4060;font-size:.78rem;margin-bottom:.6rem;'>All genes with <b>pathogenic / likely-pathogenic</b> (disease-causing) germline variants for <b>{dis_name}</b>, ranked by number of confirmed variants. Source: {src_link('ClinVar',f'https://www.ncbi.nlm.nih.gov/clinvar/?term={dis_name}[disease]')}</div>", unsafe_allow_html=True)
        for dp_row in dp_list:
            gn=dp_row.get("gene","?"); np2=dp_row.get("n_pathogenic",0)
            cond_str="; ".join(dp_row.get("conditions",[]))[:80]
            cv_url=dp_row.get("clinvar_url","")
            bar_w=min(100,int(np2/max(dp_list[0].get("n_pathogenic",1),1)*100))
            st.markdown(
                f"<div class='dis-protein-row'>"
                f"<div style='width:90px;flex-shrink:0;'><span style='color:#ff2d55;font-weight:800;font-size:.85rem;'>{np2}</span> <span style='color:#0e2840;font-size:.7rem;'>variants</span></div>"
                f"<div style='flex:1;min-width:0;'><div style='color:#9ac0d8;font-weight:700;font-size:.84rem;'>{gn}</div>"
                f"<div style='color:#0e2840;font-size:.72rem;margin-top:2px;'>{cond_str}</div>"
                f"<div style='height:3px;background:#07152a;border-radius:3px;overflow:hidden;margin-top:4px;'><div style='width:{bar_w}%;height:100%;background:#ff2d55;'></div></div></div>"
                f"<div style='flex-shrink:0;'><a class='src-badge' href='{cv_url}' target='_blank'>ClinVar ↗</a></div>"
                f"</div>", unsafe_allow_html=True)

# ─── Data loading ────────────────────────────────────────────────────
if search and query and query!=st.session_state["last"]:
    with st.spinner("🔬 Fetching UniProt · ClinVar · AlphaFold · PubMed…"):
        try:
            pdata=fetch_uniprot(query); st.session_state["pdata"]=pdata
            gene=g_gene(pdata); uid=pdata.get("primaryAccession","")
            st.session_state["gene"]=gene; st.session_state["uid"]=uid
            cv=fetch_clinvar(gene,max_v); st.session_state["cv"]=cv
            pdb=fetch_pdb(uid); st.session_state["pdb"]=pdb
            papers=fetch_papers(gene); st.session_state["papers"]=papers
            scored=ml_score_variants(cv.get("variants",[]),sensitivity)
            st.session_state["scored"]=scored
            protein_len=pdata.get("sequence",{}).get("length",1)
            gi=compute_gi(cv,protein_len); st.session_state["gi"]=gi
            st.session_state["assay"]=assay_txt; st.session_state["last"]=query
            st.rerun()
        except Exception as e:
            st.error(f"⚠️ {e}")

# CSV-only mode (no protein needed)
if st.session_state["csv_df"] is not None and not st.session_state["pdata"]:
    df=st.session_state["csv_df"]; csv_type=st.session_state["csv_type"]
    st.markdown("<hr style='border-color:#091830;margin:.8rem 0;'>", unsafe_allow_html=True)
    sh("📂","Wet-Lab CSV Analysis — Standalone Mode")
    st.caption("No protein entered — analysing CSV data independently. Enter a gene/protein in the sidebar for integrated analysis.")
    c1,c2,c3 = st.columns(3)
    with c1: st.markdown(mc(f"{len(df):,}","Rows in dataset"),unsafe_allow_html=True)
    with c2: st.markdown(mc(len(df.columns),"Columns","#4a90d9"),unsafe_allow_html=True)
    with c3: st.markdown(mc(csv_type.replace("_"," ").title(),"Data type detected","#00c896"),unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    findings=analyse_csv_standalone(df,csv_type,active_goal)
    for title4,body4 in findings:
        st.markdown(f"<div class='card'><h4>{title4}</h4><p>{body4}</p></div>", unsafe_allow_html=True)
    with st.expander("📋 Preview data"):
        st.dataframe(df.head(20),use_container_width=True)
    fc_col=next((c4 for c4 in df.columns if any(k in c4.lower() for k in ["fold","logfc","log2fc"])),None)
    p_col=next((c4 for c4 in df.columns if any(k in c4.lower() for k in ["pvalue","p_val","padj","fdr"])),None)
    if fc_col and p_col and df[fc_col].dtype in [float,'float64'] and df[p_col].dtype in [float,'float64']:
        fig_v=go.Figure()
        neg_log_p=(-np.log10(df[p_col].clip(1e-300))).clip(0,50)
        colours_v=["#ff2d55" if (fc>1 and p2<0.05) else "#1e4060" if (fc<-1 and p2<0.05) else "#3a5a7a"
                  for fc,p2 in zip(df[fc_col],df[p_col])]
        fig_v.add_trace(go.Scatter(x=df[fc_col],y=neg_log_p,mode="markers",
            marker=dict(color=colours_v,size=4,opacity=.7),
            hovertemplate="FC: %{x:.2f}<br>-log10(p): %{y:.2f}<extra></extra>"))
        fig_v.add_vline(x=1,line_color="#ff2d5555",line_dash="dot")
        fig_v.add_vline(x=-1,line_color="#3a5a7a55",line_dash="dot")
        fig_v.add_hline(y=-np.log10(0.05),line_color="#ffd60a55",line_dash="dot")
        fig_v.update_layout(paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#1e4060",
            xaxis=dict(title="Fold change (log₂) — how much expression increased/decreased",gridcolor="#060f1c"),
            yaxis=dict(title="-log₁₀(p-value) — confidence in the result",gridcolor="#060f1c"),
            height=350,margin=dict(t=10,b=40,l=60,r=10),
            title=dict(text="Volcano plot — red = significantly upregulated · blue = significantly downregulated",font_color="#2a5070",font_size=11))
        st.plotly_chart(fig_v,use_container_width=True,config={"displayModeBar":False})
    if not st.session_state["pdata"]:
        st.stop()

if not st.session_state["pdata"] and st.session_state["csv_df"] is None:
    st.markdown("""<div style='background:#040d18;border:1px solid #0c2040;border-radius:14px;padding:2rem;text-align:center;margin-top:.5rem;'>
<div style='font-size:2.5rem;margin-bottom:.6rem;'>🧬</div>
<div style='color:#0e2840;font-size:1rem;font-weight:600;margin-bottom:.4rem;'>Enter a protein in the sidebar, or upload a wet-lab CSV to begin</div>
<div style='color:#061828;font-size:.82rem;margin-bottom:1.2rem;'>Try: <b style='color:#0d2840;'>TP53</b> · <b style='color:#0d2840;'>FLNC</b> · <b style='color:#0d2840;'>ACM2</b> · <b style='color:#0d2840;'>ARRB2</b> · <b style='color:#0d2840;'>P04637</b></div>
<div style='display:flex;gap:.7rem;justify-content:center;flex-wrap:wrap;'>"""
+"".join(f"<div style='background:#05101e;border:1px solid #0c2040;border-radius:9px;padding:.6rem .9rem;width:145px;'><div style='font-size:1.1rem;'>{ic}</div><div style='color:#0e2840;font-size:.73rem;margin-top:3px;'><b style='color:#1e4060;'>{tt}</b><br>{dd}</div></div>" for ic,tt,dd in [("🔴","Triage","Structure + hotspots"),("📋","Case Study","Tissue · GPCR"),("🔬","Explorer","Click & mutate"),("🧪","Experiments","Protocols")])
+"</div></div>", unsafe_allow_html=True)
    st.stop()

# ─── Main variables ──────────────────────────────────────────────────
pdata=st.session_state["pdata"]; cv=st.session_state["cv"]
pdb=st.session_state["pdb"]; papers=st.session_state["papers"]
scored=st.session_state["scored"]; gene=st.session_state["gene"]
assay=st.session_state["assay"]; uid=st.session_state["uid"]
summary=cv.get("summary",{}); variants=cv.get("variants",[])
diseases=g_diseases(pdata)
protein_length=pdata.get("sequence",{}).get("length",1)
gi=st.session_state.get("gi") or compute_gi(cv,protein_length)
if not st.session_state.get("gi"): st.session_state["gi"]=gi
partner_info=st.session_state.get("partner_gi")
is_gpcr=g_gpcr(pdata)

# ─── PURSUE BANNER (immediate, above tabs) ──────────────────────────
pursue_map = {
    "prioritise": ("pursue-yes","🔴 PURSUE THIS PROTEIN","Strong genetic evidence. Multiple confirmed disease-causing variants. Justified for full wet-lab investment.","#ff2d55"),
    "proceed":    ("pursue-yes","🟠 PROCEED — Meaningful evidence","Confirmed disease association. Focus wet-lab work on pathogenic variants only.","#ff8c42"),
    "selective":  ("pursue-caution","🟡 BE SELECTIVE","Low pathogenic density. Work only with confirmed P/LP variants. Do not overinterpret benign entries.","#ffd60a"),
    "caution":    ("pursue-caution","⚠️ APPROACH WITH CAUTION","Very low disease variant burden. Verify interaction partners carry the actual disease risk.","#ffd60a"),
    "deprioritise":("pursue-no","⚪ DEPRIORITISE — No confirmed disease variants","Zero Mendelian disease variants in ClinVar. This protein may be redundant or bypassable. Do NOT invest major wet-lab resources without first finding disease-causing variants.","#3a5a7a"),
    "neutral":    ("pursue-no","❓ INSUFFICIENT DATA","Too few ClinVar entries. Understudied protein — cannot make a genetics-based recommendation yet.","#1e6080"),
}
css_p, verdict_label, verdict_body, v_clr = pursue_map.get(gi["pursue"], pursue_map["neutral"])
st.markdown(
    f"<div class='{css_p}'>"
    f"<div style='font-size:2rem;flex-shrink:0;'>{gi['icon']}</div>"
    f"<div>"
    f"<div style='color:{v_clr};font-weight:800;font-size:.95rem;margin-bottom:2px;'>{verdict_label}</div>"
    f"<div style='color:{v_clr}88;font-size:.8rem;'>{verdict_body}</div>"
    f"<div style='margin-top:4px;color:#0e2840;font-size:.72rem;'>"
    f"Genomic Integrity: <b style='color:{v_clr};'>{gi['verdict']}</b> · "
    f"{gi['n_pathogenic']} disease-causing / {gi['n_total']} total ClinVar variants · "
    f"Density: {gi['density']*100:.2f}% · "
    f"{src_link('ClinVar',f'https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]')} "
    f"{src_link('UniProt',f'https://www.uniprot.org/uniprotkb/{uid}')}"
    f"</div></div></div>",
    unsafe_allow_html=True,
)
if gi["pursue"]=="deprioritise":
    st.markdown("<div class='bias-warn'><p>⚠️ <b style='color:#ff2d55;'>Genomics Warning:</b> This protein carries no confirmed disease-causing germline variants. The principle — <em>genetics must be the starting point of any biology</em> — means we should not commit wet-lab resources here based on structural data or cell-culture results alone. Famous proteins like β2-arrestin (ARRB2), β-adrenergic receptors, and GRKs share this pattern: extensively studied, no dominant disease variants, likely non-essential in vivo. <b style='color:#ffd60a;'>Protein structures are not a validation of biology. DNA sequences are.</b></p></div>", unsafe_allow_html=True)

# ─── TABS ─────────────────────────────────────────────────────────────
tab1,tab2,tab3,tab4=st.tabs(["🔴  Triage","📋  Case Study","🔬  Protein Explorer","🧪  Experiments & Therapy"])

# ════════════ TAB 1 — TRIAGE ════════════
with tab1:
    # Metrics
    n_crit=sum(1 for v in scored if v.get("ml_rank")=="CRITICAL")
    c1,c2,c3,c4=st.columns(4)
    with c1: st.markdown(mc(len(diseases),"Disease links"),unsafe_allow_html=True)
    with c2: st.markdown(mc(summary.get("total",0),"ClinVar variants","#4a90d9"),unsafe_allow_html=True)
    with c3: st.markdown(mc(summary.get("pathogenic",0),"Disease-causing (pathogenic)","#ff2d55","linear-gradient(90deg,#ff2d55,#ff8080)"),unsafe_allow_html=True)
    with c4: st.markdown(mc(n_crit,"CRITICAL (ML-scored)","#ff8c42","linear-gradient(90deg,#ff8c42,#ffb380)"),unsafe_allow_html=True)
    st.markdown("<hr class='dv'>", unsafe_allow_html=True)

    cs,cd=st.columns([3,2],gap="large")
    with cs:
        sh("🏗️",f"AlphaFold Structure — {gene}")
        st.caption(f"AI-predicted 3D shape. Coloured by confidence. Red spheres = disease-causing variant sites. {src_link('AlphaFold DB',f'https://alphafold.ebi.ac.uk/entry/{uid}')}")
        if pdb:
            bf=parse_bfactors(pdb); avg_pl=round(sum(bf.values())/max(len(bf),1),1)
            pct_conf=round(sum(1 for b in bf.values() if b>=70)/max(len(bf),1)*100)
            n_sites=sum(1 for v in scored[:50] if v.get("start"))
            components.html(viewer_html(pdb,scored,445),height=450,scrolling=False)
            st.markdown(f"<div style='color:#0e2840;font-size:.71rem;margin-top:3px;'>Confidence avg (pLDDT): <b style='color:#3a7090;'>{avg_pl}</b> · {pct_conf}% reliably modelled · <b style='color:#ff2d55;'>{n_sites}</b> variant sites shown</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='background:#040d18;border:1px dashed #0c2040;border-radius:12px;height:340px;display:flex;align-items:center;justify-content:center;'><div style='text-align:center;color:#0e2840;'><div style='font-size:2rem;'>🧬</div><div style='font-size:.8rem;margin-top:5px;'>AlphaFold structure unavailable<br>Try a direct UniProt accession (e.g. P04637)</div></div></div>", unsafe_allow_html=True)

    with cd:
        sh("🔴","Disease Triage")
        st.caption(f"Ranked by ML disease score. Source: {src_link('ClinVar',f'https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]')} + {src_link('UniProt',f'https://www.uniprot.org/uniprotkb/{uid}')}")
        ds_scores={}
        for sv in scored:
            for c2 in sv.get("condition","").split(";"):
                c2=c2.strip()
                if c2: ds_scores[c2]=max(ds_scores.get(c2,0),sv.get("ml",0))
        all_d=[]
        for d in diseases:
            sc2=ds_scores.get(d["name"],.5); rk2="CRITICAL" if sc2>=.85 else "HIGH" if sc2>=.65 else "MEDIUM" if sc2>=.40 else "NEUTRAL"
            if any(k in (d["name"]+d.get("desc","")).lower() for k in ["cancer","carcinoma","leukemia"]) and rk2=="MEDIUM": rk2="HIGH"
            all_d.append({"name":d["name"],"desc":d.get("desc",""),"rk":rk2,"sc":sc2})
        for cn,cnt in summary.get("top_conds",{}).items():
            if cn not in [x["name"] for x in all_d]:
                sc2=ds_scores.get(cn,.3); rk2="CRITICAL" if sc2>=.85 else "HIGH" if sc2>=.65 else "MEDIUM" if sc2>=.40 else "NEUTRAL"
                all_d.append({"name":cn,"desc":f"{cnt} ClinVar submissions","rk":rk2,"sc":sc2})
        all_d.sort(key=lambda x:(["CRITICAL","HIGH","MEDIUM","NEUTRAL"].index(x["rk"]),-x["sc"]))
        for d2 in all_d[:10]:
            bw=int(d2["sc"]*100); clr2=RANK_CLR[d2["rk"]]; css2=RANK_CSS[d2["rk"]]
            st.markdown(f"<div class='dis-row'><div style='flex-shrink:0;'><span class='badge {css2}'>{d2['rk']}</span></div><div style='flex:1;min-width:0;'><div class='dis-name'>{d2['name']}</div><div class='dis-desc'>{d2['desc'][:90]}</div><div style='height:3px;background:#07152a;border-radius:3px;overflow:hidden;margin-top:3px;'><div style='width:{bw}%;height:100%;background:{clr2};'></div></div></div></div>", unsafe_allow_html=True)
        if summary.get("by_sig"):
            sd=summary["by_sig"]; clrs3=["#ff2d55","#ff8c42","#ffd60a","#4a90d9","#00c896","#6478ff","#a855f7","#1e4060"]
            fig2=go.Figure(go.Pie(labels=list(sd.keys()),values=list(sd.values()),hole=.58,marker_colors=clrs3[:len(sd)],textfont_size=9))
            fig2.update_layout(paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#1e4060",showlegend=True,legend=dict(font_size=9,bgcolor="#04080f"),margin=dict(t=0,b=0,l=0,r=0),height=185,annotations=[dict(text=f"<b>{summary.get('total',0)}</b>",x=.5,y=.5,font_size=13,font_color="#00e5ff",showarrow=False)])
            st.plotly_chart(fig2,use_container_width=True,config={"displayModeBar":False})

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("📊","Variant Landscape — Where on the protein do disease-causing mutations cluster?")
    st.caption(f"Each dot = one ClinVar variant. Red/orange = disease-causing (pathogenic). Dark = harmless (benign). Flat dark profile = protein may be redundant. {src_link('ClinVar',f'https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]')}")
    landscape=variant_landscape_fig(variants,protein_length,scored)
    if landscape: st.plotly_chart(landscape,use_container_width=True,config={"displayModeBar":False})
    else: st.caption("No positional data available.")

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("🔮","Residue Hotspot Triage — Which specific mutations matter most?")
    st.caption(f"Ranked by ML disease score. Source: {src_link('ClinVar',f'https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]')}")
    if scored:
        rows=""
        for v2 in scored[:50]:
            rk=v2.get("ml_rank","NEUTRAL"); ml2=v2.get("ml",0)
            clr3=RANK_CLR.get(rk,"#3a5a7a"); css3=RANK_CSS.get(rk,"bN")
            bw=int(ml2*100); url=v2.get("url","")
            nm=(v2.get("variant_name") or v2.get("title","—"))[:55]
            sig2=v2.get("sig","—")[:35]; cond2=v2.get("condition","—")[:45]
            pos2=str(v2.get("start","—"))
            lnk=f"<a href='{url}' target='_blank' style='color:#2a6a8a;font-size:.72rem;'>ClinVar ↗</a>" if url else "—"
            row_bg=RANK_CLR.get(rk,"#3a5a7a")+"08"
            rows+=(f"<tr style='background:{row_bg};'><td><span class='badge {css3}'>{rk}</span></td>"
                   f"<td style='color:#8ab0c8;font-size:.78rem;'>{nm}</td>"
                   f"<td style='color:#2a5070;text-align:center;'>{pos2}</td>"
                   f"<td style='color:#3a6080;font-size:.76rem;'>{sig2}</td>"
                   f"<td style='color:#2a5070;font-size:.74rem;'>{cond2}</td>"
                   f"<td><div style='display:flex;align-items:center;gap:4px;'><div style='width:32px;height:4px;background:#07152a;border-radius:3px;overflow:hidden;'><div style='width:{bw}%;height:100%;background:{clr3};'></div></div><span style='color:{clr3};font-size:.77rem;font-weight:700;'>{ml2:.2f}</span></div></td>"
                   f"<td style='text-align:center;'>{lnk}</td></tr>")
        st.markdown(f"<div style='overflow-x:auto;border-radius:10px;border:1px solid #0c2040;'><table class='pt2'><thead><tr><th>Rank</th><th>Variant (DNA change)</th><th>Position</th><th>ClinVar Classification</th><th>Disease</th><th>ML Score</th><th>Source</th></tr></thead><tbody>{rows}</tbody></table></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color:#0a1e30;font-size:.7rem;margin-top:4px;'>Top {min(50,len(scored))} of {len(scored)} · ML-ranked · Sensitivity: {sensitivity}/100 · {src_link('ClinVar',f'https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]')}</div>", unsafe_allow_html=True)

    # CSV panel
    if st.session_state["csv_df"] is not None:
        st.markdown("<hr class='dv'>", unsafe_allow_html=True); sh("📂","Wet-Lab CSV Analysis")
        df2=st.session_state["csv_df"]; ct2=st.session_state["csv_type"]
        for t5,b5 in analyse_csv_standalone(df2,ct2,active_goal):
            st.markdown(f"<div class='card'><h4>{t5}</h4><p>{b5}</p></div>", unsafe_allow_html=True)
        with st.expander("📋 View data"): st.dataframe(df2,use_container_width=True)

    render_citations(papers,4)

# ════════════ TAB 2 — CASE STUDY ════════════
with tab2:
    TKWS={"Brain":["brain","neuron","cerebral","cortex"],"Liver":["liver","hepatic"],"Heart":["heart","cardiac","myocardium"],"Kidney":["kidney","renal"],"Lung":["lung","pulmonary"],"Blood":["blood","erythrocyte","platelet"],"Breast":["breast","mammary"],"Colon":["colon","colorectal","intestine"],"Prostate":["prostate"],"Skin":["skin","keratinocyte"],"Muscle":["muscle","skeletal"],"Pancreas":["pancreas","islet"]}
    c_t,c_s=st.columns([1,1],gap="large")
    with c_t:
        sh("🫀","Tissue Associations (where in the body is this protein active?)")
        tt=g_tissue(pdata)
        if tt: st.markdown(f"<div class='card'><p>{tt[:500]}</p><div style='margin-top:5px;'>{src_link('UniProt',f'https://www.uniprot.org/uniprotkb/{uid}#expression')}</div></div>", unsafe_allow_html=True)
        blob=(tt+" "+g_func(pdata)+" "+" ".join(k.get("value","") for k in pdata.get("keywords",[]))).lower()
        tsc={t:sum(1 for k in ks if k in blob) for t,ks in TKWS.items()}; tsc={t:s for t,s in tsc.items() if s>0}
        if tsc:
            tsc=dict(sorted(tsc.items(),key=lambda x:-x[1])[:10])
            fig3=go.Figure(go.Bar(y=list(tsc.keys()),x=list(tsc.values()),orientation="h",marker=dict(color=list(tsc.values()),colorscale=[[0,"#0c2040"],[.5,"#0d4080"],[1,"#00e5ff"]],cmin=0,cmax=max(tsc.values()))))
            fig3.update_layout(paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#1e4060",xaxis=dict(showgrid=False,zeroline=False,showticklabels=False),yaxis=dict(tickfont=dict(size=11,color="#3a6080")),margin=dict(l=0,r=0,t=5,b=0),height=160+len(tsc)*17)
            st.plotly_chart(fig3,use_container_width=True,config={"displayModeBar":False})
    with c_s:
        sh("📍","Where in the cell? (Subcellular location)")
        locs=g_sub(pdata)
        for loc in locs: st.markdown(f"<div style='display:flex;align-items:center;gap:7px;margin:4px 0;'><span style='color:#00e5ff;font-size:.72rem;'>◆</span><span style='color:#3a6080;font-size:.82rem;'>{loc}</span></div>", unsafe_allow_html=True)
        if not locs: st.caption("No subcellular localisation data in UniProt.")
        ptm=next((c5.get("texts",[{}])[0].get("value","") for c5 in pdata.get("comments",[]) if c5.get("commentType")=="PTM"),"")
        if ptm: st.markdown(f"<div class='card' style='margin-top:.7rem;'><h4>Chemical tags on the protein (PTMs — post-translational modifications)</h4><p>{ptm[:350]}</p></div>", unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("🧬",f"Genomic Framework — where in the genome does {gene} live?")
    omim=g_xref(pdata,"MIM"); hgnc=g_xref(pdata,"HGNC"); ens=g_xref(pdata,"Ensembl")
    gd=fetch_ncbi_gene(gene) if gene else {}
    c1g,c2g,c3g=st.columns(3)
    with c1g: st.markdown(f"<div class='card'><h4>Protein identity</h4><p>UniProt: <b style='color:#00e5ff;'>{uid}</b><br>Length: <b>{protein_length} amino acids (building blocks)</b><br>HGNC: {hgnc or '—'}</p><div style='margin-top:5px;'>{src_link('UniProt',f'https://www.uniprot.org/uniprotkb/{uid}')}</div></div>", unsafe_allow_html=True)
    with c2g:
        chrom=gd.get("chr","?"); cyto=gd.get("map","?"); exons=gd.get("exons","?")
        start_g=gd.get("start","?"); stop_g=gd.get("stop","?")
        st.markdown(f"<div class='card'><h4>Location in genome (DNA blueprint)</h4><p>Chromosome: <b style='color:#00e5ff;'>{chrom}</b><br>Cytoband (address): <b>{cyto}</b><br>Exons (coding sections): <b>{exons}</b><br>Genomic span: {start_g}–{stop_g}</p><div style='margin-top:5px;'>{src_link('NCBI Gene',gd.get('link','https://www.ncbi.nlm.nih.gov/gene')) if gd.get('link') else ''}</div></div>", unsafe_allow_html=True)
    with c3g:
        omim_link=f"<a href='https://omim.org/entry/{omim}' target='_blank' style='color:#3a90c4;'>{omim} ↗</a>" if omim else "—"
        ens_link=f"<a href='https://www.ensembl.org/id/{ens}' target='_blank' style='color:#3a90c4;'>{ens[:18]} ↗</a>" if ens else "—"
        st.markdown(f"<div class='card'><h4>Cross-references (databases)</h4><p>OMIM (disease DB): {omim_link}<br>Ensembl (genome DB): {ens_link}<br>{src_link('UniProt',f'https://www.uniprot.org/uniprotkb/{uid}')} {src_link('ClinVar',f'https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]') if gene else ''}</p></div>", unsafe_allow_html=True)

    # Genomic bar visual
    if gd.get("start") and gd.get("stop"):
        try:
            gs=int(str(gd["start"]).replace(",","")); ge=int(str(gd["stop"]).replace(",",""))
            gene_len=ge-gs
            fig_g=go.Figure()
            fig_g.add_trace(go.Bar(x=[gene_len],y=[gene],orientation="h",marker_color="#00e5ff44",
                                   base=gs,name="Gene span",width=0.4))
            if gd.get("exons"):
                try:
                    n_ex=int(gd["exons"]); ex_size=gene_len/(n_ex*2)
                    for ei in range(min(n_ex,20)):
                        ex_start=gs+ei*(gene_len/n_ex)
                        fig_g.add_trace(go.Bar(x=[ex_size],y=[gene],orientation="h",
                                               marker_color="#00e5ff",base=ex_start,width=0.4,showlegend=False))
                except: pass
            fig_g.update_layout(paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#1e4060",
                barmode="overlay",height=120,margin=dict(t=10,b=20,l=60,r=10),
                xaxis=dict(title="Chromosomal position (base pairs)",color="#0e2840",gridcolor="#060f1c"),
                yaxis=dict(color="#3a6080"),showlegend=False,
                title=dict(text=f"Gene map — chromosome {chrom} · {gene_len:,} bp · {gd.get('exons','?')} exons (coding blocks shown in bright blue)",font_color="#1e4060",font_size=10))
            st.plotly_chart(fig_g,use_container_width=True,config={"displayModeBar":False})
        except: pass

    if gd.get("summary"):
        with st.expander("📖 NCBI Gene Summary"): st.write(gd["summary"])

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)

    # GPCR section — detailed
    sh("📡","GPCR Association (cell-surface signal receiver) — detailed breakdown")
    if is_gpcr:
        gpcr_info=g_gpcr_class(pdata)
        coup=", ".join(gpcr_info["coupling"])
        fn_text=g_func(pdata)
        st.markdown(
            f"<div class='gpcr-box'>"
            f"<div style='display:flex;gap:12px;align-items:flex-start;margin-bottom:.8rem;'>"
            f"<div style='font-size:2rem;'>📡</div>"
            f"<div>"
            f"<div style='color:#00e5ff;font-weight:800;font-size:.95rem;margin-bottom:3px;'>GPCR confirmed — <span style='color:#3a90d4;font-size:.82rem;'>Important / Piggybacked Target</span></div>"
            f"<div style='color:#1e4060;font-size:.81rem;'>GPCRs = cell-surface signal receivers (G protein–coupled receptors). "
            f"~34% of all FDA-approved drugs target GPCRs. A mutation in this protein disrupts signal transmission into the cell.</div>"
            f"</div></div>"
            f"<div style='display:flex;gap:.6rem;flex-wrap:wrap;margin-bottom:.7rem;'>",
            unsafe_allow_html=True,
        )
        for cp in gpcr_info["coupling"]:
            cp_desc={"Gi/o (↓ cAMP)":"Switches OFF internal alarm signal (cAMP) — inhibitory pathway","Gs (↑ cAMP)":"Switches ON internal alarm signal (cAMP) — stimulatory pathway","Gq/11 (↑ Ca²⁺)":"Raises internal calcium — activates muscle/secretion","G12/13 (Rho signalling)":"Controls cell shape and movement (cytoskeletal reorganisation)"}.get(cp,"Signal relay switch")
            st.markdown(f"<div style='background:#040d18;border:1px solid #00e5ff22;border-radius:8px;padding:6px 10px;flex:1;min-width:140px;'><div style='color:#00e5ff;font-size:.78rem;font-weight:700;'>{cp}</div><div style='color:#1e4060;font-size:.72rem;margin-top:2px;'>{cp_desc}</div></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        # GPCR pathway flow
        gpcr_stages=[("1. Ligand binds","Signal molecule (drug/hormone) binds GPCR"),("2. G-protein activated","G-protein (signal relay switch) exchanges GDP→GTP"),("3. Second messenger","cAMP / Ca²⁺ levels change inside cell"),("4. Downstream effects","Kinases activated, gene expression changed"),("5. β-arrestin / desensitisation","Signal switched off (receptor internalised)")]
        st.markdown("<div style='display:flex;gap:4px;align-items:center;flex-wrap:wrap;margin-bottom:.6rem;'>", unsafe_allow_html=True)
        for i,(stage_t,stage_d) in enumerate(gpcr_stages):
            st.markdown(f"<div style='flex:1;min-width:110px;background:#040d18;border:1px solid #0c2040;border-radius:8px;padding:6px 8px;'><div style='color:#00e5ff;font-size:.72rem;font-weight:700;margin-bottom:2px;'>{stage_t}</div><div style='color:#0e2840;font-size:.67rem;line-height:1.4;'>{stage_d}</div></div>{'<div style=\"color:#1e4060;\">→</div>' if i<4 else ''}", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        if fn_text: st.markdown(f"<div class='card'><h4>Function</h4><p>{fn_text[:400]}</p><div style='margin-top:4px;'>{src_link('UniProt Function',f'https://www.uniprot.org/uniprotkb/{uid}#function')}</div></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        fn_text=g_func(pdata)
        st.markdown(f"<div style='background:#040d18;border:1px solid #0c2040;border-radius:9px;padding:.8rem 1rem;'><span style='color:#0e2840;font-size:.82rem;'>Not classified as a GPCR in UniProt.</span> {src_link('UniProt',f'https://www.uniprot.org/uniprotkb/{uid}')}</div>", unsafe_allow_html=True)
        if fn_text: st.markdown(f"<div class='card' style='margin-top:.5rem;'><h4>Function</h4><p>{fn_text[:400]}</p></div>", unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("🔬","Disease Classification — Inherited (germline) vs Acquired (somatic)")
    somatic=set(); germline=set()
    for v2 in variants:
        origin=v2.get("origin","").lower(); cond4=v2.get("condition","")
        if not cond4 or cond4=="Not specified": continue
        if "somatic" in origin or v2.get("somatic"): somatic.add(cond4)
        elif any(x in origin for x in ["germline","inherited","de novo"]): germline.add(cond4)
        elif v2.get("score",0)>=4: germline.add(cond4)
    cg2,cs3=st.columns(2)
    with cg2:
        st.markdown(f"<div style='background:#03100a;border:1px solid #00c89628;border-radius:11px;padding:1rem;'><p style='color:#00c896;font-weight:700;font-size:.88rem;margin:0 0 2px;'>🧬 Inherited / born-with (Germline) ({len(germline)})</p><p style='color:#1a4030;font-size:.72rem;margin:0 0 6px;'>Variant present in DNA from birth — heritable, runs in families</p>", unsafe_allow_html=True)
        for c5 in sorted(germline)[:7]: st.markdown(f"<div style='color:#2a6040;font-size:.78rem;margin:2px 0;'>◆ {c5[:65]}</div>", unsafe_allow_html=True)
        if not germline: st.markdown("<div style='color:#0d2a1a;font-size:.78rem;'>None found.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with cs3:
        st.markdown(f"<div style='background:#100308;border:1px solid #ff2d5528;border-radius:11px;padding:1rem;'><p style='color:#ff2d55;font-weight:700;font-size:.88rem;margin:0 0 2px;'>🔴 Acquired / developed (Somatic) ({len(somatic)})</p><p style='color:#3a1020;font-size:.72rem;margin:0 0 6px;'>Variant acquired after birth in specific cells — not heritable (e.g. cancer mutations)</p>", unsafe_allow_html=True)
        for c5 in sorted(somatic)[:7]: st.markdown(f"<div style='color:#602030;font-size:.78rem;margin:2px 0;'>◆ {c5[:65]}</div>", unsafe_allow_html=True)
        if not somatic: st.markdown("<div style='color:#2a0810;font-size:.78rem;'>None found.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    for d5 in diseases[:5]:
        note_h=f"<p style='color:#ffd60a;font-size:.76rem;margin-top:3px;'>{d5['note'][:150]}</p>" if d5.get("note") else ""
        st.markdown(f"<div class='card'><h4>{d5['name']} {src_link('UniProt',f'https://www.uniprot.org/uniprotkb/{uid}#disease')}</h4><p>{d5.get('desc','')[:260]}</p>{note_h}</div>", unsafe_allow_html=True)
    render_citations(papers,4)

# ════════════ TAB 3 — EXPLORER ════════════
with tab3:
    sh("🔬","Protein Explorer — click any residue to inspect")
    st.caption(f"3D structure from AlphaFold. Red spheres = disease-causing (pathogenic) variants. Click residues to inspect. {src_link('AlphaFold',f'https://alphafold.ebi.ac.uk/entry/{uid}')}")
    if pdb: components.html(viewer_html(pdb,scored,570),height=575,scrolling=False)
    else: st.info("No AlphaFold structure — try searching by UniProt accession (e.g. P04637).")

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("🧫","Mutation Analysis — what happens when you change one building block?")
    seq=g_seq(pdata)
    if seq:
        bf=parse_bfactors(pdb) if pdb else {}
        pos_to_v={};[pos_to_v.__setitem__(int(v2.get("start",0)),v2) for v2 in scored if v2.get("start","")]
        cs4,cm=st.columns([1,2],gap="large")
        with cs4:
            position=int(st.number_input("Amino acid (building block) position",1,max(len(seq),1),1,1,key="rpos"))
            aa=seq[position-1] if position<=len(seq) else "?"
            pl=bf.get(position)
            conf=("Very High" if pl and pl>=90 else "Confident" if pl and pl>=70 else "Low" if pl and pl>=50 else "Very Low") if pl else "—"
            st.markdown(f"<div class='card'><h4>Position {position} — {aa} ({AA_NAMES.get(aa,'Unknown')})</h4><p>Model confidence (pLDDT): <b style='color:#00e5ff;'>{f'{pl:.1f}' if pl else '—'}</b> ({conf})<br>Water affinity (hydropathy): <b>{AA_HYDRO.get(aa,0):+.1f}</b><br>Electric charge: <b>{AA_CHG.get(aa,0):+.1f}</b></p></div>", unsafe_allow_html=True)
            vd=pos_to_v.get(position)
            if vd:
                rk2=vd.get("ml_rank","NEUTRAL"); clr2=RANK_CLR[rk2]; css2=RANK_CSS[rk2]
                url_vd=vd.get("url","")
                st.markdown(f"<div class='card' style='border-color:{clr2}33;'><h4 style='color:{clr2};'>⚠️ ClinVar Disease Variant Here</h4><p>{p('pathogenic') if vd.get('score',0)>=4 else vd.get('sig','—')}<br><small style='color:#0e2840;'>{vd.get('condition','')[:80]}</small></p>{'<a href=\"'+url_vd+'\" target=\"_blank\" style=\"color:#2a6a8a;font-size:.74rem;\">View in ClinVar ↗</a>' if url_vd else ''}</div>", unsafe_allow_html=True)
            else: st.success("No ClinVar disease variant at this position",icon="✅")
        with cm:
            tb1,tb2=st.tabs(["Building-block properties","What if it mutates? →"])
            with tb1:
                SPECIAL={"C":"Disulfide bonds · metal binding","G":"Most flexible · helix-breaker","P":"Rigid ring · helix-breaker","H":"pH-sensitive (pKa≈6)","W":"Largest · UV-absorbing","Y":"Phosphorylation (chemical tagging) target","R":"DNA/RNA binding · +1 charge","K":"Ubiquitination target · +1","D":"Catalytic acid · −1","E":"Catalytic acid · −1"}
                for lbl,val in [("Building block (amino acid)",f"{aa} — {AA_NAMES.get(aa,'?')}"),("Water affinity (hydropathy)",f"{AA_HYDRO.get(aa,0):+.1f} (positive=water-hating, negative=water-loving)"),("Electric charge",f"{AA_CHG.get(aa,0):+.1f}"),("Special role",SPECIAL.get(aa,"No special designation"))]:
                    st.markdown(f"<div style='display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #060f1c;'><span style='color:#0e2840;font-size:.79rem;'>{lbl}</span><span style='color:#5a8090;font-size:.79rem;font-weight:600;'>{val}</span></div>", unsafe_allow_html=True)
            with tb2:
                alts=[a for a in AA_NAMES.keys() if a!=aa]
                alt=st.selectbox("Replace with:",alts,key="alt_aa")
                sev=st.slider("Structural disruption magnitude (how severe?)",0.0,1.0,.5,.05,key="sev")
                if bf:
                    pos_list=sorted(bf.keys()); window=32; center=min(max(position,window+1),max(pos_list)-window)
                    dp=[p4 for p4 in pos_list if abs(p4-center)<=window]
                    wt2=[bf.get(p4,70) for p4 in dp]
                    mt2=[max(0,wt2[i]-sev*28*math.exp(-.5*((p4-position)/6)**2)) for i,p4 in enumerate(dp)]
                    fig5=go.Figure()
                    fig5.add_trace(go.Scatter(x=dp,y=wt2,mode="lines",name="Normal protein",line=dict(color="#00e5ff",width=2)))
                    fig5.add_trace(go.Scatter(x=dp,y=mt2,mode="lines",name=f"Mutant {aa}{position}{alt}",line=dict(color="#ff2d55",width=2,dash="dash")))
                    fig5.add_trace(go.Scatter(x=dp+dp[::-1],y=mt2+wt2[::-1],fill="toself",fillcolor="rgba(255,45,85,.07)",line=dict(color="rgba(0,0,0,0)"),showlegend=False))
                    fig5.add_vline(x=position,line_color="#ffd60a",line_dash="dot",annotation_text=f"p.{aa}{position}{alt}",annotation_font_color="#ffd60a",annotation_font_size=10)
                    fig5.update_layout(paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#1e4060",xaxis=dict(title="Position in protein",gridcolor="#060f1c"),yaxis=dict(title="Model confidence (pLDDT)",range=[0,100],gridcolor="#060f1c"),legend=dict(bgcolor="#04080f",font_size=10),margin=dict(t=8,b=28,l=28,r=8),height=220)
                    st.plotly_chart(fig5,use_container_width=True,config={"displayModeBar":False})
                    st.caption("Shaded area = predicted confidence loss due to mutation. Larger = more structurally disruptive.")
                hd=abs(AA_HYDRO.get(aa,0)-AA_HYDRO.get(alt,0)); cd=abs(AA_CHG.get(aa,0)-AA_CHG.get(alt,0))
                imps=[]
                if alt=="*": imps.append(("🔴",f"Early-stop mutation ({p('nonsense')})","Protein production halts early → half-sized, non-functional protein → likely destroyed by cell (NMD)"))
                if hd>3: imps.append(("🟠",f"Large water-affinity shift",f"Δ{hd:.1f} — buried building block changes polarity → protein core destabilised"))
                if cd>=1: imps.append(("⚡",f"Electric charge change",f"Δ{cd:+.0f} — disrupts molecular attraction/repulsion in protein core"))
                if aa=="C": imps.append(("🔗","Cysteine lost","Molecular bridge (disulfide bond) broken → protein shape collapses"))
                if alt=="P": imps.append(("🔀","Proline introduced","Rigid kink inserted → helix or sheet structure likely disrupted"))
                if not imps: imps.append(("🟡","Conservative substitution","Small physicochemical change — likely low structural impact"))
                for icon2,title2,body2 in imps:
                    st.markdown(f"<div style='display:flex;gap:8px;background:#05101e;border:1px solid #0c2040;border-radius:8px;padding:8px 10px;margin:4px 0;'><span style='font-size:.95rem;flex-shrink:0;'>{icon2}</span><div><div style='color:#5a8090;font-size:.78rem;font-weight:700;'>{title2}</div><div style='color:#0e2840;font-size:.74rem;margin-top:1px;'>{body2}</div></div></div>", unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)

    # ── Disease → Mutation → Genomic Implication (FIXED) ──────────────
    sh("🗺️","Disease → Mutation → Genomic Implication")
    st.caption(f"How do specific mutations in {gene} cause each disease? Source: {src_link('ClinVar',f'https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]')}")

    # Build condition map from ALL variants (not just scored top 30)
    all_variants_with_cond = [v2 for v2 in variants if v2.get("condition","Not specified") != "Not specified" and v2.get("score",0) >= 2]
    if not all_variants_with_cond:
        all_variants_with_cond = [v2 for v2 in variants if v2.get("condition","Not specified") != "Not specified"]
    
    # Create ML score lookup
    ml_lookup = {v2.get("uid",""):v2 for v2 in scored}
    
    cond_map2=defaultdict(list)
    for v2 in all_variants_with_cond:
        # Merge ML data
        if v2.get("uid") in ml_lookup:
            v2 = {**v2, **{k:vv for k,vv in ml_lookup[v2["uid"]].items() if k in ["ml","ml_rank"]}}
        for c5 in v2.get("condition","").split(";"):
            c5=c5.strip()
            if c5 and c5!="Not specified" and len(c5)>3: cond_map2[c5].append(v2)

    if not cond_map2:
        # Fallback: show top conditions from summary
        st.markdown("<div style='color:#1e4060;font-size:.82rem;'>No condition-linked variant data with sufficient evidence.</div>", unsafe_allow_html=True)
        if summary.get("top_conds"):
            st.markdown("**Top associated conditions from ClinVar:**")
            for cond_name,cnt in list(summary["top_conds"].items())[:8]:
                st.markdown(f"<div style='color:#3a6080;font-size:.81rem;margin:3px 0;'>◆ <b>{cond_name}</b> — {cnt} variants {src_link('Search ClinVar',f'https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]+{cond_name}[disease]')}</div>", unsafe_allow_html=True)
    else:
        for cond5,vlist in sorted(cond_map2.items(),key=lambda x:-len(x[1]))[:12]:
            vlist_s=sorted(vlist,key=lambda x:-x.get("score",0)); best_sc=vlist_s[0].get("score",0)
            best_rk="CRITICAL" if best_sc>=5 else "HIGH" if best_sc>=4 else "MEDIUM" if best_sc>=2 else "NEUTRAL"
            cv_url=f"https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]+{cond5.replace(' ','+')}[disease]"
            with st.expander(f"{cond5[:70]}  ·  {len(vlist_s)} variants  ·  {badge(best_rk)}", expanded=(best_sc>=4)):
                cv2_col,mech_col=st.columns([2,3])
                with cv2_col:
                    st.markdown(f"**Top disease-causing mutations:** {src_link('ClinVar',cv_url)}")
                    for v2 in vlist_s[:6]:
                        ml3=v2.get("ml",v2.get("score",0)/5.0); sc3=v2.get("score",0)
                        clr3=RANK_CLR.get(v2.get("ml_rank","NEUTRAL"),RANK_CLR.get(score_rank(sc3),"#3a5a7a"))
                        vn=(v2.get("variant_name") or v2.get("title","—"))[:50]
                        url3=v2.get("url",""); lnk3=f" [ClinVar ↗]({url3})" if url3 else ""
                        sig3=v2.get("sig","—")
                        st.markdown(f"<div style='font-size:.78rem;margin:3px 0;'><span style='color:{clr3};font-weight:700;'>{sig3[:25]}</span> <span style='color:#4a7090;'>{vn}</span>{lnk3}</div>", unsafe_allow_html=True)
                with mech_col:
                    st.markdown("**How does this mutation cause the disease?**")
                    cl5=cond5.lower(); vn_all=" ".join(v2.get("variant_name","") for v2 in vlist_s).lower(); mechs=[]
                    if any(k in cl5 for k in ["cancer","carcinoma","tumor","leukemia","glioma","lymphoma"]): mechs+=["Hyperactive (gain-of-function) or blocking (dominant-negative) effect → uncontrolled cell growth.","Acquired in specific cell → cell population overgrows (clonal expansion)."]
                    if any(k in cl5 for k in ["cardiomyopathy","cardiac","heart"]): mechs+=["Protein failure in heart muscle cells → impaired contractility.","Progressive fibrosis (scarring) of heart tissue."]
                    if any(k in cl5 for k in ["neural","epilep","brain","intellectual","development"]): mechs+=["Critical developmental pathway disrupted → abnormal brain wiring."]
                    if "stop" in vn_all or "ter" in vn_all: mechs.append(f"Early-stop mutation ({p('nonsense')}) → short non-functional protein → cell destroys it (NMD).")
                    if "frameshift" in vn_all or "del" in vn_all: mechs.append(f"Reading-frame shift ({p('frameshift')}) → completely wrong protein sequence from mutation site onward.")
                    if "splice" in vn_all: mechs.append("Splice-site disruption → exon (coding section) skipped or intron (non-coding) included → corrupted protein.")
                    if "missense" in vn_all: mechs.append(f"Letter-swap mutation ({p('missense')}) → one wrong building block → altered shape or lost function.")
                    if not mechs: mechs.append("Mechanism not yet fully characterised — functional studies needed to confirm causality.")
                    for m in mechs: st.markdown(f"<div style='color:#1e4060;font-size:.78rem;margin:2px 0;'>• {m}</div>", unsafe_allow_html=True)

    render_citations(papers,4)

# ════════════ TAB 4 — EXPERIMENTS ════════════
with tab4:
    # Scorecard
    ptype=g_ptype(pdata); drugg={"kinase":.9,"gpcr":.95,"transcription_factor":.35,"receptor":.8,"general":.5}.get(ptype,.5)
    n_crit2=sum(1 for v2 in scored if v2.get("ml_rank")=="CRITICAL"); n_high2=sum(1 for v2 in scored if v2.get("ml_rank")=="HIGH")
    priority=min(100,n_crit2*15+n_high2*8+len(scored)*.5+drugg*20)
    c1e,c2e,c3e,c4e=st.columns(4)
    with c1e: st.markdown(mc(n_crit2,"CRITICAL (ML)","#ff2d55","linear-gradient(90deg,#ff2d55,#ff8080)"),unsafe_allow_html=True)
    with c2e: st.markdown(mc(n_high2,"HIGH (ML)","#ff8c42"),unsafe_allow_html=True)
    with c3e: st.markdown(mc(f"{drugg:.0%}","Druggability est.","#00c896"),unsafe_allow_html=True)
    with c4e: st.markdown(mc(int(priority),"Priority score / 100","#00e5ff"),unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)

    # Mutation cascade animation
    sh("🎬","Mutation Cascade — How does a DNA change lead to disease?")
    st.caption("Drag the slider to see how a mutation cascades from protein → cell → disease. Plain language descriptions at each stage.")
    top_p_vars=gi.get("pathogenic_list",[]) or scored[:3]
    if not top_p_vars: top_p_vars=scored[:3]
    components.html(mutation_cascade_html(gene,is_gpcr,gi["pursue"],top_p_vars),height=480,scrolling=False)

    if is_gpcr:
        st.markdown("<div class='card'><h4>📡 GPCR-specific cascade</h4><p>For this GPCR (cell-surface signal receiver): mutation → receptor shape change → G-protein (signal relay switch) fails to activate → second messenger (internal relay: cAMP / Ca²⁺) levels altered → downstream kinase (protein tagger) activity changes → gene expression reprogrammed → cell death (apoptosis) or shape change → organ dysfunction.</p></div>", unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)

    # Genomic verdict
    sh("🧬","Genomic Verdict — Should you invest in this protein?")
    gi_clr4=gi["color"]
    pursue_recs={"prioritise":"✅ INVEST — genetics confirms this is a real, important target. Proceed to CRISPR knock-in + biochemical validation immediately.",
                 "proceed":"🟠 PROCEED — meaningful evidence. Focus only on confirmed disease-causing variants.",
                 "selective":"🟡 BE SELECTIVE — work only on confirmed P/LP variants. Do not extrapolate.",
                 "caution":"⚠️ CAUTION — very low disease burden. Verify partner proteins carry the actual risk first.",
                 "deprioritise":"🛑 DO NOT INVEST — zero Mendelian disease variants. Risk of wasted resources is high. Protein structures and cell-culture data alone are insufficient justification.",
                 "neutral":"❓ HOLD — insufficient data. Need more ClinVar submissions before a genetics-based decision."}
    st.markdown(f"<div class='{gi['css']}'><div style='color:{gi_clr4};font-weight:800;font-size:.95rem;margin-bottom:5px;'>{gi['icon']} {gi['verdict']}: {gi['label']}</div><div style='color:{gi_clr4}88;font-size:.82rem;margin-bottom:.6rem;'>{gi['explanation']}</div><div style='color:{gi_clr4};font-weight:700;font-size:.84rem;margin-bottom:.5rem;'>{pursue_recs.get(gi['pursue'],'—')}</div><div style='color:#0e2840;font-size:.73rem;font-style:italic;border-top:1px solid {gi_clr4}22;padding-top:.5rem;'>Principle: <em>Protein structures by themselves are not a validation of biology. DNA sequences are. Genetics must be the starting point of any biology.</em><br>Sources: {src_link('ClinVar',f'https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]')} · {src_link('UniProt',f'https://www.uniprot.org/uniprotkb/{uid}')}</div></div>", unsafe_allow_html=True)

    if assay:
        st.markdown("<hr class='dv'>", unsafe_allow_html=True); sh("🧫","Assay Next Steps")
        tl=assay.lower()
        for kws,t2,b2 in [(["western","wb"],"Western blot → Follow Up","Quantify in ≥2 cell lines. CHX chase (protein half-life). Validate with mass-spec proteomics."),(["crispr","knockout"],"CRISPR gene knockout → Follow Up","Rescue: re-introduce normal + each variant. RNA-seq. If cancer gene → xenograft (tumour implant in mouse)."),(["flow","facs"],"Flow cytometry (cell sorting) → Follow Up","Western blot for cell-death proteins (caspase 3/7, Bcl-2). Cell-cycle arrest → CDK inhibitor comparison."),(["co-ip","binding"],"Interaction / binding data → Follow Up","Map exact binding interface by HDX-MS (hydrogen exchange mass spec). Cryo-EM structure. Design interface disruptors.")]:
            if any(k in tl for k in kws): st.markdown(f"<div class='card'><h4>{t2}</h4><p>{b2}</p></div>", unsafe_allow_html=True)

    if st.session_state["csv_df"] is not None:
        st.markdown("<hr class='dv'>", unsafe_allow_html=True); sh("📂","CSV-Informed Experimental Strategy")
        df3=st.session_state["csv_df"]; ct3=st.session_state["csv_type"]
        for t3,b3 in analyse_csv_standalone(df3,ct3,active_goal):
            st.markdown(f"<div class='card'><h4>{t3}</h4><p>{b3}</p></div>", unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    COST_MAP={"Free":("#00c896","rgba(0,200,150,.08)"),"$":("#4a90d9","rgba(74,144,217,.08)"),"$$":("#ffd60a","rgba(255,214,10,.08)"),"$$$":("#ff8c42","rgba(255,140,66,.08)"),"$$$$":("#ff2d55","rgba(255,45,85,.08)")}
    cc=st.columns(5)
    for (sym,(clr,bg)),col in zip(COST_MAP.items(),cc):
        col.markdown(f"<div style='background:{bg};border:1px solid {clr}33;border-radius:8px;padding:5px;text-align:center;'><div style='color:{clr};font-weight:800;'>{sym}</div><div style='color:{clr}88;font-size:.67rem;'>{{'Free':'No cost','$':'<$1K','$$':'$1-10K','$$$':'$10-50K','$$$$':'$50K+'}}[sym]</div></div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    EXPS=[
        ("🧬","Enzyme activity assay (ADP-Glo™ kinase assay)","$$","3–6 wks","Directly measure whether a mutation makes the protein hyperactive or broken.",["Express normal and mutant proteins (bacteria or insect cells).","Purify via His-tag column + size-exclusion.","ADP-Glo™ luminescent kinase reaction.","Compare efficiency (Km/Vmax): normal vs each variant.","Triplicate; error ≤10%."],"Mutations at catalytic (active) sites.","Mutations in unstructured regions or pLDDT <50.","Quantitative activity ratio — direct functional evidence."),
        ("🧬","Protein interaction mapping (Co-IP / AP-MS)","$$$","4–8 wks","Discover which partner proteins are lost or gained with each mutation.",["Tag protein (3×FLAG or GFP) in HEK293T cells.","Native cell lysis (NP-40 buffer).","Pull-down + protein A/G beads.","Mass-spectrometry (TMT-labelled) or gel electrophoresis.","Confirm top hits with reverse pull-down."],"Interface residues predicted by AlphaFold-Multimer.","Variants with identical binding domains.","Interaction network rewiring map per mutation."),
        ("🧬","Protein stability screen (Thermal Shift Assay)","$","1–2 wks","Find drugs that stabilise mutant proteins, or confirm protein is destabilised.",["Purify protein (0.5 mg/mL).","96-well plate + SYPRO Orange fluorescent dye.","Heat ramp 25→95°C at 1°C/min.","Melting temperature (Tm) by curve fitting.","Flag compounds shifting Tm ≥1°C as stabilisers."],"Destabilising missense variants in structured domains.","Unstructured regions — no Tm signal expected.","Stability change per mutation; drug hit identification."),
        ("🔬","CRISPR gene knock-in (precise mutation introduction)","$$$","6–12 wks","Put exact patient mutations into cells to study their effects.",["Design guide RNAs (CRISPOR tool).","SpCas9 protein + guide RNA + repair template.","Screen ≥50 cell clones by DNA sequencing.","Confirm protein expression by western blot.","Run all functional assays on confirmed mutant cells."],"Confirmed disease-causing (P/LP) variants + ML score ≥0.75.","Variants of unknown significance with <2-star review — too uncertain.","Isogenic (genetically identical except for mutation) cell lines — gold standard."),
        ("🔬","Luciferase reporter assay (gene activation test)","$","1–3 wks","Test whether a transcription-factor mutation changes gene activation.",["Clone target gene promoter (1 kb) into luciferase (light-emitting) vector.","Express normal or mutant protein + control reporter.","Measure light output ratio at 48h.","≥3 independent experiments in triplicate."],"Mutations in DNA-binding or activation domains.","Unstructured N-terminal segments.","Fold-change in target gene activation/repression."),
        ("🧫","Structure prediction + stability scoring (Rosetta ΔΔG)","Free","1–3 days","Computationally rank ALL mutations by structural damage before wet lab — eliminates ~50% of candidates.",["Download AlphaFold structure.","Rosetta FastRelax on normal structure.","Introduce each mutation computationally.","Flag ΔΔG ≥2 REU as structurally disruptive.","Cross-reference with ClinVar + ML scores."],"All letter-swap mutations (missense) in well-structured regions (pLDDT ≥70).","Unstructured regions (pLDDT <50) — Rosetta not reliable here.","Pre-ranked candidate list — eliminates ~50% before any wet-lab spend."),
        ("🐭","Tumour implant model (xenograft)","$$$$","8–16 wks","Test cancer-causing mutations in living organisms.",["Implant 1×10⁶ mutant cells under skin of immunocompromised mice.","Measure tumour size twice weekly (callipers).","Stain tumour tissue at study end (H&E + protein markers).","Statistical comparison (log-rank test): normal vs mutant growth."],"Mutations with in-vitro proliferation data already confirming cancer activity.","Variants of uncertain significance without prior cell data — too costly.","In vivo tumour growth curves; tissue-level disease confirmation."),
        ("💊","Drug screen (High-Throughput Screening)","$$$$","6–12 mo","Find drugs that fix or block mutant protein function.",["Set up automated assay compatible with 96/384-well plates.","Screen compound library at 10 µM (10K–1M compounds).","Eliminate compounds that are just toxic to cells.","Confirm dose-response (IC₅₀) for top 50 compounds.","Progress top 5 for medicinal chemistry optimisation."],"Confirmed high-priority variants with drug-binding pockets.","Unstructured proteins without defined pockets.","Lead drug compound series for further development."),
        ("💊","Protein degrader (PROTAC)","$$$$","6–12 mo","Destroy hyperactive mutant proteins that cannot be inhibited by conventional drugs.",["Design PROTAC molecule: target-binding warhead + cell-recycling-machinery recruiter.","Synthesise 10–20 candidates.","Measure protein destruction efficiency (DC₅₀) in cells.","Confirm by western blot and mass-spectrometry.","Full proteome check — ensure only target is degraded."],"Hyperactive (gain-of-function) mutations that conventional drugs cannot block.","Loss-of-function mutations — destroying remaining protein makes disease worse.","Selective protein degrader DC₅₀ <100 nM."),
    ]
    for icon3,name3,cost3,timeline3,purpose3,protocol3,focus3,neglect3,outcome3 in EXPS:
        clr_e,bg_e=COST_MAP.get(cost3,("#3a6080","rgba(58,96,128,.08)"))
        with st.expander(f"{icon3} {name3}  ·  {cost3}  ·  ⏱ {timeline3}"):
            c_l,c_r=st.columns([3,2])
            with c_l:
                st.markdown(f"**What it does:** {purpose3}")
                st.markdown("**Step-by-step protocol:**")
                for i2,step in enumerate(protocol3,1): st.markdown(f"{i2}. {step}")
                st.markdown(f"**Expected result:** {outcome3}")
            with c_r:
                st.markdown(f"<div style='background:{bg_e};border:1px solid {clr_e}33;border-radius:10px;padding:.8rem;'><div style='color:{clr_e};font-weight:800;font-size:.92rem;'>{cost3}</div><div style='color:{clr_e}88;font-size:.74rem;margin-bottom:7px;'>⏱ {timeline3}</div><div style='color:#00c896;font-size:.75rem;font-weight:700;margin-bottom:2px;'>✅ Focus on:</div><div style='color:#1a5030;font-size:.73rem;margin-bottom:6px;'>{focus3}</div><div style='color:#ff8c42;font-size:.75rem;font-weight:700;margin-bottom:2px;'>❌ Skip / deprioritise:</div><div style='color:#5a2a10;font-size:.73rem;'>{neglect3}</div></div>", unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("🗺️","Decision Framework — Which variants to pursue?")
    counts5={r:sum(1 for v2 in scored if v2.get("ml_rank")==r) for r in RANK_CLR}
    labels5=[r for r in RANK_CLR if counts5[r]>0]; vals5=[counts5[r] for r in labels5]; clrs5=[RANK_CLR[r] for r in labels5]
    if labels5:
        fig6=go.Figure(go.Funnel(y=labels5,x=vals5,textinfo="value+percent initial",marker=dict(color=clrs5),textfont=dict(color="white",size=12)))
        fig6.update_layout(paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#1e4060",height=260,margin=dict(t=5,b=5,l=70,r=5))
        st.plotly_chart(fig6,use_container_width=True,config={"displayModeBar":False})
    for rank3,clr3,rec3 in [("CRITICAL","#ff2d55","Immediate wet-lab validation. CRISPR knock-in + biochemical assay now. In vivo only after in-vitro phenotype confirmed."),("HIGH","#ff8c42","Functional assay + in-silico stability (ΔΔG). Animal models only after clear in-vitro data."),("MEDIUM","#ffd60a","In-silico modelling + low-cost cell assay only. Do NOT spend on animal work yet."),("NEUTRAL","#3a5a7a","Deprioritise. Monitor ClinVar for reclassification. No wet-lab spend at this stage.")]:
        st.markdown(f"<div style='display:flex;gap:9px;align-items:center;background:#04080f;border-left:3px solid {clr3};border-radius:0 8px 8px 0;padding:8px 12px;margin:4px 0;'><span class='badge {RANK_CSS[rank3]}'>{rank3}</span><span style='color:#4a7090;font-size:.82rem;'>{rec3}</span></div>", unsafe_allow_html=True)

    render_citations(papers,5)

# ─── Footer ────────────────────────────────────────────────────────
st.markdown(f"<hr style='border-color:#050f1c;margin:.8rem 0;'><p style='text-align:center;color:#040d18;font-size:.69rem;'>Protellect · {src_link('UniProt','https://www.uniprot.org')} · {src_link('ClinVar','https://www.ncbi.nlm.nih.gov/clinvar/')} · {src_link('AlphaFold DB','https://alphafold.ebi.ac.uk')} · {src_link('PubMed','https://pubmed.ncbi.nlm.nih.gov')} · {src_link('NCBI Gene','https://www.ncbi.nlm.nih.gov/gene/')} · Not a substitute for expert clinical judgment.</p>", unsafe_allow_html=True)
