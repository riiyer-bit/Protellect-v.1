import streamlit as st
import requests, re, json
from datetime import datetime
import plotly.graph_objects as go
import pandas as pd

from auth import render_auth_page, is_logged_in, current_user, logout, save_lab_profile, can_search, decrement_search
from apis import (api_uniprot, api_clinvar, api_gnomad, api_string, api_opentargets,
                  api_clinicaltrials, api_pubmed, api_alphafold, api_alphamissense,
                  api_pubchem_structure, classify_tier, detect_weaknesses, gi_score, TIER_MAP)
from molcell import render_phospho_network, render_kinase_phosphatase_panel, render_gpcr_signalling_diagram, render_alphamissense_chart, render_chemical_structure
from microbiome_ai import annotate_microbial_genes_llm, annotate_microbe_taxonomy_llm, parse_functional_annotation_file, pathway_annotation_analysis, pubmed_microbiome
from assay_analysis import render_assay_analysis_tab

st.set_page_config(page_title="Protellect",page_icon="🔬",layout="wide",initial_sidebar_state="collapsed")

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
*{font-family:'Space Grotesk',sans-serif;box-sizing:border-box}
code,.mono{font-family:'JetBrains Mono',monospace}
#MainMenu,footer,header,[data-testid="stDeployButton"]{display:none!important}
[data-testid="stSidebar"]{background:#030810!important;border-right:1px solid #0d2545!important}
.block-container{padding:0!important;max-width:100%!important}
[data-testid="stAppViewContainer"]{background:#010306}
div[data-testid="metric-container"]{background:#070d1a;border:1px solid #0d2545;border-radius:11px;padding:.75rem}
div[data-testid="metric-container"] label{color:#3a6080!important;font-size:.68rem!important;letter-spacing:.07em!important;text-transform:uppercase!important}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{color:#00e5ff!important;font-size:1.35rem!important;font-weight:600!important}
.stTabs [data-baseweb="tab-list"]{gap:2px;background:#030810;border-radius:10px;padding:3px;border:1px solid #0d2545}
.stTabs [data-baseweb="tab"]{background:transparent;color:#3a6080;border-radius:7px;font-size:.75rem;padding:.28rem .75rem;font-weight:500}
.stTabs [aria-selected="true"]{background:#0d2545!important;color:#00e5ff!important}
.stButton>button{background:transparent;border:1px solid #0d2545;color:#d0e8ff;font-size:.78rem;border-radius:8px;font-weight:500;transition:all .2s;padding:.28rem .75rem}
.stButton>button:hover{border-color:#00e5ff44;color:#00e5ff;background:#00e5ff08}
.stButton>button[kind="primary"]{background:#00e5ff!important;color:#010306!important;border:none!important;font-weight:600!important}
.stTextInput>div>div>input,.stSelectbox>div>div,.stTextArea textarea{background:#030810!important;border:1px solid #0d2545!important;color:#d0e8ff!important;border-radius:8px!important}
.stExpander{border:1px solid #0d2545!important;border-radius:10px!important;background:#040c14!important;margin-bottom:.28rem!important}
.stFileUploader{background:#030810;border:1px dashed #0d2545;border-radius:10px;padding:.5rem}
h1,h2,h3{color:#d0e8ff!important}
a{color:#00e5ff!important;text-decoration:none!important}
@keyframes fadeUp{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:.4;transform:scale(.98)}50%{opacity:1;transform:scale(1.02)}}
@keyframes glow{0%,100%{box-shadow:0 0 20px #00e5ff22}50%{box-shadow:0 0 50px #00e5ff55}}
@keyframes rotateDNA{0%{transform:rotate(0deg) scale(1)}50%{transform:rotate(180deg) scale(1.1)}100%{transform:rotate(360deg) scale(1)}}
@keyframes scanline{0%{top:-10px}100%{top:100%}}
</style>"""
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ── helpers ─────────────────────────────────────────────────────────────────────
def sh(icon,title,color="#00e5ff"):
    st.markdown(f"<div style='display:flex;align-items:center;gap:8px;margin:.8rem 0 .35rem'><span style='font-size:.9rem'>{icon}</span><span style='color:{color};font-weight:600;font-size:.88rem;letter-spacing:-.01em'>{title}</span></div>",unsafe_allow_html=True)

def badge(text,color="#00e5ff"):
    return f"<span style='background:{color}18;color:{color};font-size:.67rem;padding:2px 8px;border-radius:7px;border:1px solid {color}44;font-weight:600'>{text}</span>"

def warn_box(title,body):
    st.markdown(f"<div style='background:#0a0205;border:1px solid #ff2d5544;border-radius:9px;padding:.6rem .9rem;margin:.25rem 0'><div style='color:#ff2d55;font-weight:600;font-size:.76rem;margin-bottom:2px'>{title}</div><div style='color:#6a3040;font-size:.76rem;line-height:1.6'>{body}</div></div>",unsafe_allow_html=True)

def info_box(body,color="#00e5ff"):
    st.markdown(f"<div style='background:{color}0a;border:1px solid {color}33;border-radius:9px;padding:.6rem .9rem;margin:.25rem 0'><div style='color:{color};font-size:.8rem;line-height:1.7'>{body}</div></div>",unsafe_allow_html=True)

def tier_badge(t): c=TIER_MAP.get(t,{}).get("color","#3a5a7a"); return badge(t,c)

def src_link(label,url):
    return f"<a href='{url}' target='_blank' style='display:inline-flex;align-items:center;gap:3px;font-size:.68rem;color:#00e5ff;background:#00e5ff0d;border:1px solid #00e5ff33;border-radius:6px;padding:2px 7px;margin:2px'>{label} ↗</a>"

# ── session init ────────────────────────────────────────────────────────────────
for k,v in [("domain",None),("subdomain",None),("onboarding_done",False),("lab_profile",None),("analysis_cache",{})]:
    if k not in st.session_state: st.session_state[k]=v

# ── auth gate ───────────────────────────────────────────────────────────────────
if not is_logged_in():
    render_auth_page(); st.stop()

u = current_user()

# ── onboarding ──────────────────────────────────────────────────────────────────
def render_onboarding():
    st.markdown("""
    <div style='min-height:100vh;display:flex;align-items:center;justify-content:center;padding:2rem'>
    <div style='max-width:600px;width:100%;animation:fadeUp .8s ease both'>""", unsafe_allow_html=True)

    # Animated logo
    st.markdown("""
    <div style='text-align:center;margin-bottom:2rem'>
      <div style='position:relative;width:90px;height:90px;margin:0 auto .8rem;display:flex;align-items:center;justify-content:center'>
        <div style='position:absolute;width:90px;height:90px;border:2px solid #00e5ff33;border-radius:50%;animation:pulse 3s infinite'></div>
        <div style='position:absolute;width:70px;height:70px;border:1px solid #00e5ff22;border-radius:50%;animation:pulse 3s infinite .5s'></div>
        <div style='font-size:2.5rem;animation:rotateDNA 8s linear infinite'>🔬</div>
      </div>
      <div style='font-size:2.4rem;font-weight:700;color:#00e5ff;letter-spacing:-.03em'>Protellect</div>
      <div style='font-size:.8rem;color:#3a6080;letter-spacing:.1em;text-transform:uppercase'>Biology Intelligence Platform</div>
      <div style='width:50px;height:2px;background:linear-gradient(90deg,transparent,#00e5ff,transparent);margin:.8rem auto;animation:pulse 2s infinite'></div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"<div style='text-align:center;color:#5a8090;font-size:.85rem;margin-bottom:1.5rem'>Welcome, <b style='color:#d0e8ff'>{u.get('name','')}</b> — let's personalise your experience</div>", unsafe_allow_html=True)

    with st.form("onboarding_form"):
        st.markdown("<div style='color:#00e5ff;font-weight:600;font-size:.9rem;margin-bottom:.8rem'>Tell us about your lab</div>", unsafe_allow_html=True)

        lab_name = st.text_input("Lab / Institute name", placeholder="e.g. Smith Lab, Wellcome Sanger Institute", key="ob_lab")
        pi_name  = st.text_input("Principal Investigator name", placeholder="e.g. Prof. Jane Smith", key="ob_pi")
        lab_focus= st.text_area("What does your lab research?", placeholder="e.g. We study GPCR signalling in cardiac disease, focusing on filamin phosphorylation and arrhythmia mechanisms...", height=100, key="ob_focus")
        domain_pref = st.selectbox("Primary domain of interest", ["Neuroscience & Pharma","Oncology","Proteins & Structural Biology","Microbiome","All domains equally"], key="ob_domain")
        organisms = st.multiselect("Organisms you work with", ["Human","Mouse","Zebrafish","C. elegans","Drosophila","E. coli","Yeast","Gut bacteria/microbiome","In vitro only"], default=["Human"], key="ob_org")
        assay_types = st.multiselect("Primary assay types", ["Western blot","CRISPR knock-in/out","RNA-seq","16S microbiome","Mass spectrometry","BRET/FRET","SPR/ITC binding","Flow cytometry","Patch clamp","In vivo mouse","Computational/dry-lab only"], key="ob_assays")
        budget = st.select_slider("Lab budget for new experiments", ["<$10K","$10K–50K","$50K–200K","$200K–1M",">$1M"], value="$50K–200K", key="ob_budget")
        pi_pubmed = st.text_input("PI PubMed search term (to pull your lab's papers)", placeholder="e.g. Smith J[au] GPCR OR Smith Jane filamin", key="ob_pubmed")

        submitted = st.form_submit_button("Begin Research →", type="primary", use_container_width=True)
        if submitted:
            if not lab_name or not lab_focus:
                st.error("Please provide at least a lab name and research focus.")
            else:
                save_lab_profile({
                    "lab_name": lab_name, "pi_name": pi_name, "research_focus": lab_focus,
                    "domain_pref": domain_pref, "organisms": organisms, "assay_types": assay_types,
                    "budget": budget, "pi_pubmed_query": pi_pubmed
                })
                st.rerun()

    st.markdown("</div></div>", unsafe_allow_html=True)

if not st.session_state.onboarding_done and not u.get("onboarded"):
    render_onboarding(); st.stop()

lab = st.session_state.lab_profile or u.get("lab_profile") or {}

# ── domain splash ───────────────────────────────────────────────────────────────
DOMAINS_META = {
    "neuro":{"label":"Neuroscience & Pharma","icon":"🧠","color":"#a855f7","tagline":"Alzheimer's · Parkinson's · Epilepsy · ALS · Psychiatry · BBB"},
    "onco":{"label":"Oncology","icon":"🎗️","color":"#ff2d55","tagline":"Somatic mutations · Immunotherapy · ADCs · Liquid biopsy · Resistance"},
    "proteins":{"label":"Proteins & Structural","icon":"🧬","color":"#00e5ff","tagline":"AlphaFold · AlphaMissense · Kinases · GPCRs · FBM-Filamin · PTMs"},
    "microbiome":{"label":"Microbiome","icon":"🦠","color":"#00c896","tagline":"AI functional annotation · TMAO · FMT · Host-microbe · Pathway reannotation"},
}

def render_splash():
    # Animated logo
    st.markdown("""
    <div style='text-align:center;padding:3rem 1rem 1.5rem;animation:fadeUp .7s ease both'>
      <div style='position:relative;width:80px;height:80px;margin:0 auto .6rem;display:flex;align-items:center;justify-content:center'>
        <div style='position:absolute;inset:0;border:2px solid #00e5ff33;border-radius:50%;animation:glow 3s infinite'></div>
        <span style='font-size:2.2rem'>🔬</span>
      </div>
      <div style='font-size:2.6rem;font-weight:700;color:#00e5ff;letter-spacing:-.03em'>Protellect</div>
      <div style='font-size:.78rem;color:#3a6080;letter-spacing:.1em;text-transform:uppercase;margin:.2rem 0'>Biology Intelligence Platform</div>
      <div style='width:50px;height:2px;background:linear-gradient(90deg,transparent,#00e5ff,transparent);margin:.8rem auto;animation:pulse 2s infinite'></div>
    </div>""", unsafe_allow_html=True)

    if lab.get("lab_name"):
        st.markdown(f"<div style='text-align:center;color:#3a6080;font-size:.82rem;margin-bottom:1.5rem'>Welcome back, <b style='color:#d0e8ff'>{lab['lab_name']}</b></div>", unsafe_allow_html=True)

    cols = st.columns(4, gap="medium")
    for i,(col,(key,D)) in enumerate(zip(cols, DOMAINS_META.items())):
        with col:
            # Highlight recommended domain based on lab profile
            lab_dom = lab.get("domain_pref","")
            is_rec = D["label"].lower() in lab_dom.lower() if lab_dom and lab_dom!="All domains equally" else False
            border = f"border:2px solid {D['color']}88" if is_rec else "border:1px solid #0d2545"
            rec_badge = f"<div style='background:{D['color']}22;color:{D['color']};font-size:.65rem;padding:1px 7px;border-radius:6px;margin-bottom:.3rem'>Recommended for your lab</div>" if is_rec else ""
            st.markdown(
                f"<div style='background:#040c14;{border};border-radius:16px;padding:1.5rem 1rem;text-align:center;animation:fadeUp {.6+i*.1}s ease both;margin-bottom:.4rem'>"
                f"{rec_badge}"
                f"<div style='font-size:2rem;margin-bottom:.4rem'>{D['icon']}</div>"
                f"<div style='color:{D['color']};font-weight:700;font-size:.88rem;margin-bottom:.2rem'>{D['label']}</div>"
                f"<div style='color:#2a4050;font-size:.7rem;line-height:1.5'>{D['tagline']}</div>"
                f"</div>", unsafe_allow_html=True)
            if st.button(f"Open {D['icon']}", key=f"open_{key}", use_container_width=True):
                st.session_state.domain = key; st.rerun()

    # Lab papers if PI name set
    if lab.get("pi_pubmed_query"):
        st.markdown("---")
        sh("📄","Your Lab's Recent Papers","#ffd60a")
        if st.button("Load lab papers", key="load_lab_papers"):
            with st.spinner("Fetching your lab's papers from PubMed..."):
                lab_papers = api_pubmed(lab["pi_pubmed_query"]+" 2020:2025[pdat]", 6)
            if lab_papers:
                for p in lab_papers:
                    pm_url = p.get("url","")
                    pm_id = p.get("pmid","")
                    st.markdown(f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:9px;padding:.6rem .9rem;margin-bottom:.25rem'><div style='color:#d0e8ff;font-size:.82rem;font-weight:500'>{p['title'][:80]}...</div><div style='color:#3a6080;font-size:.74rem'>{p['authors']} · {p['journal']} · {p['year']} · <a href='{pm_url}' target='_blank'>PMID {pm_id}</a></div></div>", unsafe_allow_html=True)
            else:
                st.info("No recent papers found. Adjust the PubMed search term in your lab profile.")

# ── SIDEBAR ─────────────────────────────────────────────────────────────────────
def render_sidebar(domain_key):
    D = DOMAINS_META[domain_key]; color = D["color"]
    with st.sidebar:
        st.markdown(f"<div style='color:{color};font-weight:700;font-size:.95rem;padding:.4rem 0'>🔬 Protellect</div>", unsafe_allow_html=True)
        if lab.get("lab_name"):
            st.markdown(f"<div style='color:#3a5060;font-size:.72rem;margin-bottom:.4rem'>{lab['lab_name']}</div>", unsafe_allow_html=True)
        st.markdown("---")
        gene_input = st.text_input("🔍 Gene / protein", placeholder="FLNC, EGFR, LRRK2, ARRB2...", key="gene_box")
        do_search  = st.button("Analyse ↗", use_container_width=True, key="search_btn", type="primary")
        
        # Search quota
        if u.get("plan","free") == "free":
            used = u.get("searches_used",0); mx = u.get("max_searches",10)
            st.markdown(f"<div style='color:#3a6080;font-size:.7rem;text-align:center'>{used}/{mx} searches used</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f"<div style='color:#3a6080;font-size:.68rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin-bottom:.3rem'>Quick Genes</div>", unsafe_allow_html=True)
        quick_genes = {
            "neuro":["APP","LRRK2","SNCA","GBA","SCN1A","DRD2","SOD1","MAPT","TREM2","KCNQ2"],
            "onco":["TP53","KRAS","BRCA1","EGFR","HER2","ALK","BRAF","PIK3CA","CDK4","FLT3"],
            "proteins":["FLNA","FLNC","ARRB2","EGFR","HSP90","GRK2","ADRB2","AGTR1","MDM2","PTEN"],
            "microbiome":["FXR","TLR4","NLRP3","GPR41","NOD2","FMO3","FUT2","CARD9","IL10","TGR5"],
        }.get(domain_key, [])
        for g in quick_genes[:10]:
            if st.button(g, key=f"qg_{g}", use_container_width=True):
                st.session_state["_run_gene"]=g; st.rerun()

        st.markdown("---")
        if st.button("← Domains", key="back", use_container_width=True):
            st.session_state.domain=None; st.rerun()
        if st.button(f"👤 {u.get('name','').split()[0] if u.get('name') else 'Profile'} · Sign Out", key="signout", use_container_width=True):
            logout(); st.rerun()

    return gene_input, do_search

# ── GENE ANALYSIS ────────────────────────────────────────────────────────────────
def render_gene_analysis(gene: str, domain_key: str):
    D = DOMAINS_META[domain_key]; color = D["color"]
    gene = gene.upper().strip()

    if not can_search():
        st.error("Search quota reached. Upgrade to Pro for unlimited searches.")
        return

    sh("🔎", f"Live Analysis — {gene}", color)
    with st.spinner(f"Fetching {gene} from 7 databases..."):
        pdata    = api_uniprot(gene)
        cv       = api_clinvar(gene)
        partners = api_string(gene)
        ot       = api_opentargets(gene)
        gnomad   = api_gnomad(gene)
        trials   = api_clinicaltrials(gene)
        af       = api_alphafold(pdata.get("uid","")) if pdata.get("uid") else {}
        am_data  = api_alphamissense(pdata.get("uid","")) if pdata.get("uid") else {}

    decrement_search()

    is_arrb = gene in ("ARRB1","ARRB2","BARR1","BARR2")
    gi = gi_score(cv, pdata.get("length",500) if pdata else 500)

    if is_arrb:
        st.markdown(
            f"<div style='background:#0a0205;border:2px solid #ff2d55;border-radius:12px;padding:1.1rem 1.4rem;margin-bottom:.7rem'>"
            f"<div style='color:#ff2d55;font-weight:700;font-size:1rem;margin-bottom:.25rem'>⛔ DEPRIORITISE — {gene}: $4,050,000 in avoidable spend</div>"
            f"<div style='color:#6a3040;font-size:.8rem;line-height:1.7'>ARRB1/ARRB2 double KO mice are viable and fertile. Zero confirmed Mendelian disease-causing variants in ClinVar. Beta-arrestin phosphorylation codes are kinase noise — no disease variant validates any phospho-site on ARRB proteins. Redirect investment to: Filamin A Ser2152-P assay ($2K) · ADRB1 · ADRB2 · AGTR1 · MAS1</div>"
            f"<div style='display:flex;gap:5px;flex-wrap:wrap;margin-top:.5rem'>"
            + "".join(f"<span style='background:#ff2d5511;border:1px solid #ff2d5533;border-radius:6px;padding:2px 9px;font-size:.7rem;color:#ff8c42'>${v:,} — {k}</span>"
                      for k,v in [("HTS screen",2500000),("CRISPR x6",150000),("Cryo-EM",500000),("Mouse x2",800000),("BRET screens",100000)])
            + "</div></div>", unsafe_allow_html=True)

    # Verdict banner
    gc = gi.get("color","#3a5a7a")
    af_link = f"<a href='{af.get('af_url','')}' target='_blank' style='font-size:.74rem;color:#a855f7;margin-left:auto'>AlphaFold ↗</a>" if af.get("af_url") else ""
    st.markdown(
        f"<div style='background:{gc}10;border:1px solid {gc}44;border-radius:11px;padding:.85rem 1.1rem;margin-bottom:.5rem'>"
        f"<div style='color:{gc};font-weight:700;font-size:.92rem'>{gi.get('icon','')} {gi.get('verdict','')}</div>"
        f"<div style='color:#5a8090;font-size:.78rem;margin-top:2px'>{gi.get('explanation','')}</div>"
        f"<div style='display:flex;gap:12px;margin-top:.4rem;align-items:center'>"
        f"<span style='font-size:.76rem;color:#3a6080'>P/LP: <b style='color:{gc}'>{gi.get('n',0)}</b></span>"
        f"<span style='font-size:.76rem;color:#3a6080'>Per 100 aa: <b style='color:{gc}'>{gi.get('per100',0)}</b></span>"
        f"<span style='font-size:.76rem;color:#3a6080'>CRITICAL: <b style='color:{gc}'>{gi.get('n_crit',0)}</b></span>"
        f"<span style='font-size:.76rem;color:#3a6080'>pLI: <b style='color:{gc}'>{gnomad.get('pLI','—')}</b></span>"
        f"{af_link}</div></div>", unsafe_allow_html=True)

    # Pull lab-relevant papers if PI name set
    lab_paper_note = ""
    if lab.get("pi_pubmed_query") and gene.upper() in (lab.get("research_focus","").upper()+"FLNA ADRB KRAS TP53"):
        lab_paper_note = f" · Your lab may have publications on {gene}"

    # Tab structure
    tabs = st.tabs(["🧬 Protein","🔬 Variants","🧠 AlphaMissense","⚙️ Pathways","💊 Drugs","🏥 Trials","📚 Literature","🧪 Experiments","📊 Assay Analysis"])
    t_prot, t_var, t_am, t_path, t_drugs, t_trials, t_lit, t_exp, t_assay = tabs

    with t_prot:
        c1,c2 = st.columns(2)
        with c1:
            if pdata.get("name"):
                st.markdown(f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:10px;padding:.75rem 1rem;margin-bottom:.4rem'>"
                            f"<div style='color:{color};font-weight:600;font-size:.88rem'>{pdata['name']}</div>"
                            f"<div style='color:#3a6080;font-size:.72rem'>{gene} · {pdata.get('length',0)} aa</div>"
                            f"<div style='color:#3a5060;font-size:.76rem;line-height:1.6;margin-top:.35rem'>{pdata.get('function','')[:400]}{'...' if len(pdata.get('function',''))>400 else ''}</div>"
                            f"</div>", unsafe_allow_html=True)
            for d in pdata.get("diseases",[])[:5]:
                st.markdown(f"<div style='padding:4px 0;border-bottom:1px solid #0d2545;font-size:.78rem'><span style='color:#d0e8ff'>{d['name']}</span><div style='color:#2a4050;font-size:.72rem'>{d.get('desc','')[:100]}</div></div>", unsafe_allow_html=True)
            if pdata.get("ptms"):
                sh("🔘","PTM data (UniProt)",color)
                for ptm in pdata["ptms"]: st.markdown(f"<div style='color:#5a8090;font-size:.76rem;padding:3px 0;border-bottom:1px solid #0d2545'>{ptm[:200]}</div>", unsafe_allow_html=True)
        with c2:
            if partners:
                sh("🕸️","STRING Interaction Partners ≥700",color)
                for p in partners:
                    st.markdown(f"<div style='display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #0d2545;font-size:.78rem'><span style='color:#d0e8ff'>{p['partner']}</span><span style='color:#00c896;font-size:.73rem'>Score {p['score']} · {p.get('mode','')}</span></div>", unsafe_allow_html=True)
            if gnomad:
                sh("📊","gnomAD Constraint",color); cc=st.columns(3)
                with cc[0]: st.metric("pLI",gnomad.get("pLI","—"))
                with cc[1]: st.metric("o/e LoF",gnomad.get("oe_lof","—"))
                with cc[2]: st.metric("o/e Mis",gnomad.get("oe_mis","—"))
            if ot.get("disease_assoc"):
                sh("🎯","Disease Associations — OpenTargets",color)
                for da in ot["disease_assoc"][:5]:
                    st.markdown(f"<div style='display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #0d2545;font-size:.78rem'><span style='color:#d0e8ff'>{da['name']}</span><span style='color:#ff8c42;font-size:.73rem'>{da['score']}</span></div>", unsafe_allow_html=True)
            if pdata.get("keywords"):
                sh("🏷️","Keywords",color)
                st.markdown(" ".join(badge(k,"#3a6080") for k in pdata["keywords"][:10]), unsafe_allow_html=True)

    with t_var:
        if is_arrb:
            warn_box("Disease triage suppressed","ClinVar entries for ARRB proteins reflect co-occurrence with GPCR-driven disease, not independent pathogenicity.")
        elif not cv:
            st.info("No P/LP variants in ClinVar for this gene.")
        else:
            sh("🔴",f"ClinVar — {len(cv)} Pathogenic/Likely Pathogenic Variants",color)
            info_box("ClinVar is the triage filter — not the truth source. Multi-star reviewed P/LP variants are the starting point. Superimpose onto drug structures or run functional assays to validate target engagement.",color)
            for v in cv[:20]:
                rc={"CRITICAL":"#ff2d55","HIGH":"#ff8c42","MODERATE":"#ffd60a","LOW":"#5a8090"}.get(v["ml_rank"],"#3a5a7a")
                with st.expander(f"{badge(v['ml_rank'],rc)} &nbsp; {v['title'][:68]}...",expanded=False):
                    st.markdown(f"{badge(v['cs'],'#4a90d9')} &nbsp; {'⭐'*v['stars'] if v['stars'] else '☆ No review'} &nbsp; <a href='{v['url']}' target='_blank' style='font-size:.72rem'>ClinVar ↗</a>",unsafe_allow_html=True)
                    if v.get("condition"): st.markdown(f"<div style='color:#5a8090;font-size:.76rem;margin-top:2px'>{v['condition'][:150]}</div>",unsafe_allow_html=True)

    with t_am:
        sh("🧠","AlphaMissense — DeepMind Per-Residue Pathogenicity",color)
        if am_data:
            render_alphamissense_chart(am_data, cv, color)
        else:
            st.info("AlphaMissense data not available. UniProt accession may not have an AlphaFold structure.")

        if pdata.get("ptms"):
            st.markdown("---")
            sh("🔘","Phosphorylation Signal vs Noise",color)
            render_phospho_network(gene, pdata.get("ptms",[]), cv)

    with t_path:
        sh("⚙️","Pathway & Signalling Analysis",color)
        t_kin, t_gpcr, t_chem = st.tabs(["Kinases & Phosphatases","GPCR Signalling","Chemical Structures"])
        with t_kin:
            render_kinase_phosphatase_panel(gene, color)
        with t_gpcr:
            render_gpcr_signalling_diagram(gene, color)
        with t_chem:
            sh("⚗️","Chemical Structure Lookup",color)
            compound = st.text_input("Drug/compound name", placeholder="e.g. imatinib, sotorasib, venetoclax", key=f"chem_{gene}")
            if compound:
                with st.spinner("Fetching from PubChem..."):
                    render_chemical_structure(compound)

    with t_drugs:
        if ot.get("drugs"):
            sh("💊","Known Drugs — OpenTargets",color)
            ph_l={4:"Approved",3:"Phase 3",2:"Phase 2",1:"Phase 1",0:"Preclinical"}; ph_c={4:"#00c896",3:"#4a90d9",2:"#ffd60a",1:"#5a8090",0:"#3a4050"}
            for drug in ot["drugs"]:
                ph=int(drug.get("phase",0) or 0)
                st.markdown(f"<div style='display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid #0d2545;font-size:.8rem'><span style='color:#d0e8ff'>{drug['name']}</span><span style='background:{ph_c.get(ph,'#3a4050')}22;color:{ph_c.get(ph,'#5a8090')};padding:2px 7px;border-radius:6px;font-size:.7rem'>{ph_l.get(ph,'?')}</span></div>", unsafe_allow_html=True)
        if ot.get("tractability"):
            sh("🎯","Tractability",color); st.markdown(" ".join(badge(t,"#00c896") for t in ot["tractability"]),unsafe_allow_html=True)
        if not ot.get("drugs") and not ot.get("tractability"): st.info("No drug data found.")

    with t_trials:
        sh("🏥","Active Recruiting Trials — ClinicalTrials.gov",color)
        if not trials: st.info("No actively recruiting trials found.")
        else:
            for tr in trials:
                ph_clr="#4a90d9" if "3" in tr.get("phase","") else "#ffd60a" if "2" in tr.get("phase","") else "#5a8090"
                st.markdown(f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:9px;padding:.6rem .85rem;margin-bottom:.25rem;display:flex;justify-content:space-between;align-items:center'><div style='flex:1'><a href='{tr['url']}' target='_blank' style='color:#d0e8ff;font-size:.8rem;font-weight:500'>{tr['title']}</a><div style='color:#2a4050;font-size:.71rem;margin-top:1px'>{tr['sponsor']} · {tr['nct']}</div></div><span style='background:{ph_clr}22;color:{ph_clr};padding:2px 7px;border-radius:6px;font-size:.7rem;margin-left:8px;white-space:nowrap'>{tr['phase'] or 'Unspecified'}</span></div>", unsafe_allow_html=True)

    with t_lit:
        sh("📄",f"PubMed Literature 2022–2025 · {gene}{lab_paper_note}",color)
        lit_q = f"{gene}[gene] 2022:2025[pdat]"
        if lab.get("pi_pubmed_query"):
            lit_q_lab = f"{gene} AND ({lab['pi_pubmed_query']})"
            show_lab = st.checkbox("Show only your lab's papers about this gene", key=f"lab_lit_{gene}")
            if show_lab: lit_q = lit_q_lab
        with st.spinner("Fetching papers..."):
            papers = api_pubmed(lit_q, 12)
        if not papers: st.info("No papers found.")
        for p in papers:
            wk = detect_weaknesses(p["title"])
            with st.expander(f"{tier_badge(p['tier'])} &nbsp; {p['title'][:70]}{'...' if len(p['title'])>70 else ''}",expanded=False):
                st.markdown(f"<div style='font-size:.76rem;color:#5a8090'>{p['authors']} · <i>{p['journal']}</i> · {p['year']}</div>",unsafe_allow_html=True)
                pm=p.get("pmid",""); doi=p.get("doi",""); url=p.get("url","")
                if doi: st.markdown(f"<a href='https://doi.org/{doi}' target='_blank' style='font-size:.7rem'>DOI ↗</a> &nbsp; <a href='{url}' target='_blank' style='font-size:.7rem'>PubMed {pm} ↗</a>",unsafe_allow_html=True)
                else: st.markdown(f"<a href='{url}' target='_blank' style='font-size:.7rem'>PubMed {pm} ↗</a>",unsafe_allow_html=True)
                for wt,wb in wk: warn_box(wt,wb)

    with t_exp:
        sh("🧪","Protein-Specific Experiments",color)
        render_experiments_panel(gene, pdata, cv, gnomad, ot, partners, am_data, is_arrb, color, lab)

    with t_assay:
        render_assay_analysis_tab(gene, color, lab)

# ── EXPERIMENTS ──────────────────────────────────────────────────────────────────
def render_experiments_panel(gene,pdata,cv,gnomad,ot,partners,am_data,is_arrb,color,lab):
    if is_arrb: warn_box("Experiments suppressed","Zero disease variants. ARRB1/ARRB2 KO mice viable. Redirect investment to genetically validated targets."); return
    n_cv=len(cv); pli=gnomad.get("pLI",0); n_crit=sum(1 for v in cv if v.get("ml_rank")=="CRITICAL")
    n_lof=gi_score(cv,pdata.get("length",500) if pdata else 500).get("n_lof",0); n_miss=n_cv-n_lof
    top_cv=cv[0].get("title","")[:35] if cv else "top pathogenic variant"
    top_part=partners[0]["partner"] if partners else "key interaction partner"
    concordant=am_data.get("pathogenic_count",0) if am_data else 0
    is_gpcr=any(x in gene for x in ["ADRB","AGTR","MAS1","CHRM","ADRA","DRD","HTR","CCR","CXCR"])
    is_kin=any(x in gene for x in ["GRK","CDK","BRAF","EGFR","ALK","FGFR","MET","RET","JAK","ABL","LRRK"])
    is_fil=gene in ("FLNA","FLNB","FLNC")
    is_sm=any("small" in t.lower() for t in ot.get("tractability",[]))
    lab_assays=lab.get("assay_types",[])
    budget_tier={"<$10K":0,"$10K–50K":1,"$50K–200K":2,"$200K–1M":3,">$1M":4}.get(lab.get("budget","$50K–200K"),2)

    exps=[]
    exps.append({"name":f"Rosetta ΔΔG + AlphaMissense dual screen — {n_miss} missense variants","cost":"Free","time":"1–3d","p":.92,"v":8,"first":True,"body":f"Zero-cost dual validation. Rosetta ΔΔG: structural destabilisation. AlphaMissense (DeepMind): independent pathogenicity prediction. Concordant (ClinVar P/LP + AM ≥0.564 + ΔΔG ≥2 REU) = highest priority for TSA/chaperone. Discordant (ClinVar P/LP, AM <0.564) = non-structural mechanism → Co-IP or functional assay instead. {concordant} AlphaMissense-pathogenic positions detected."})
    if n_lof>n_miss:
        exps.append({"name":f"Western blot — protein level in {n_lof} LoF variant models","cost":"$500","time":"1 wk","p":.90,"v":9,"first":True,"body":f"LoF-dominant ({n_lof}/{n_cv} P/LP are frameshift/stop-gain). Anti-{gene} antibody (HPA-validated). CRISPR knock-in or patient-derived cells. pLI={pli} — {'expect absent band (NMD/proteasomal degradation)' if pli>0.8 else 'may show truncated band (NMD-escape or dominant-negative)'}. Absent = gene supplementation strategy. Truncated = different approach."})
    elif n_miss>0:
        exps.append({"name":f"Thermal shift assay (DSF) — {min(n_crit+3,8)} missense variants vs WT","cost":"$2,000","time":"2 wks","p":.85,"v":9,"first":True,"body":f"Missense-dominant ({n_miss}/{n_cv} P/LP). Purify WT + {top_cv[:25]}... DSF (SYPRO Orange, 384-well, 0.3mg/mL). ΔTm ≤-2°C = structurally destabilising → pharmacochaperone screen (Prestwick 1,280 drugs, $2K, 2 wks — fastest path to clinical candidate). ΔTm <1°C but P/LP = functional mechanism → Co-IP with {top_part}. AlphaMissense concordance strengthens structural interpretation. {'Matches your lab assay repertoire.' if 'Western blot' in lab_assays else ''}"})
    if is_gpcr:
        exps.append({"name":f"Filamin A Ser2152-P western — agonist-stimulated {gene} (PRIMARY GPCR readout)","cost":"$2,000","time":"1 wk","p":.90,"v":10,"first":True,"body":f"H8 helix dislodgement → Filamin Ig21 binding → PKA phosphorylates Ser2152. More receptor-proximal than cAMP, IP3, or beta-arrestin. Agonist → anti-Filamin A IP → pSer2152 western (Cell Signaling anti-pS2152). Variant in H8 or ICL3 → REDUCED Filamin-P despite normal cAMP. PhosphoSite highest FLNA peak = only non-noise signal. Nakamura JBC 2015. IP-protected readout."})
        exps.append({"name":f"cAMP HTRF — G-protein coupling WT vs {top_cv[:20]}...","cost":"$3,000","time":"2 wks","p":.85,"v":8,"first":False,"body":f"Gs/Gi primary coupling. cAMP HTRF (Cisbio 384-well). WT vs each P/LP variant at matched expression (confirm by western first). Kills cAMP not Filamin-P = G-protein defect. Kills Filamin-P not cAMP = cytoskeletal decoupling. Different mechanism = different target."})
    if is_kin:
        exps.append({"name":f"ADP-Glo kinase activity — {top_cv[:25]}... vs WT","cost":"$5,000","time":"3 wks","p":.85,"v":9,"first":True,"body":f"ADP-Glo (Promega) = most direct kinase activity readout. WT vs {top_cv} at matched protein concentration (confirm by western). ≥70% activity reduced = LoF → substrate accumulation is disease mechanism. Unchanged = allosteric/scaffolding defect → test {top_part} interaction. Before HTS: KINOMEscan 468-kinase panel ($50K) to confirm selectivity."})
    if is_fil:
        exps.append({"name":"SPR — Filamin Ig21 vs GPCR FBM peptides","cost":"$8,000","time":"3 wks","p":.85,"v":10,"first":True,"body":f"Pathogenic FLNA variants in Ig19-21 disrupt FBM binding. Immobilise Filamin Ig21 on CM5 chip. Analytes: AT1R C-tail (positive control), MAS1 C-tail, {top_cv[:20]}... peptide. KD >10-fold increased = FBM disruption confirmed. Follow with PKA Ser2152-P assay: reduced Filamin-P in cells confirms cytoskeletal decoupling mechanism."})
    crispr_ok=n_crit>=2 and budget_tier>=2
    exps.append({"name":f"CRISPR knock-in — {top_cv[:30]}... in disease-relevant cells","cost":"$25,000","time":"8 wks","p":.80 if crispr_ok else .35,"v":10 if crispr_ok else 3,"first":False,"body":f"{'JUSTIFIED: ' + str(n_crit) + ' CRITICAL variants + budget allows.' if crispr_ok else 'PREMATURE: run TSA/western first. Only ' + str(n_crit) + ' CRITICAL variants, or budget may be limiting.'} HDR in {gene} endogenous locus. Screen ≥50 clones Sanger + western. Readout: {'Filamin Ser2152-P after agonist' if is_gpcr else 'kinase activity assay' if is_kin else 'disease-relevant functional assay'}. Positive = ClinGen PS3 evidence. pLI={pli}."})
    if top_part and top_part!="key interaction partner":
        exps.append({"name":f"AP-MS interactome — {gene}:{top_part} WT vs {top_cv[:18]}...","cost":"$15,000","time":"6 wks","p":.75,"v":8,"first":False,"body":f"Endogenous 3xFLAG-tag {gene} via CRISPR. Anti-FLAG IP × 3 replicates. TMT-LC-MS/MS. SAINTexpress + CRAPome filtering. Hypothesis: {top_cv[:25]}... reduces interaction with {top_part}. Gained HSP70/HSP90 interactions = protein misfolding and dominant-negative behaviour."})
    if is_sm or n_miss>5:
        exps.append({"name":"Pharmacochaperone screen — Prestwick 1,280 approved drugs","cost":"$3,000","time":"2 wks","p":.60,"v":8,"first":False,"body":"Screen Prestwick at 10µM by DSF. Flag ΔTm ≥1°C. Dose-response (0.1–100µM) on top 20. Cellular rescue: add hit to CRISPR mutant cells. Approved drug = known safety profile → accelerated clinical translation. Fastest path to clinical candidate for missense-dominant proteins."})

    first=[e for e in exps if e.get("first")]; rest=sorted([e for e in exps if not e.get("first")],key=lambda x:-x["v"])
    for i,exp in enumerate(first+rest):
        border="#00c896" if exp.get("first") else "#0d2545"
        with st.expander(f"{'🥇 DO FIRST — ' if exp.get('first') else f'#{i+1} — '}{exp['name']}  ·  {exp['cost']}  ·  ⏱ {exp['time']}",expanded=(i<2)):
            cl,cr=st.columns([4,1])
            with cl: st.markdown(f"<div style='background:#020810;border-left:3px solid {border};padding:.7rem 1rem;border-radius:0 8px 8px 0;color:#7ab0c0;font-size:.81rem;line-height:1.7'>{exp['body']}</div>",unsafe_allow_html=True)
            with cr: st.markdown(f"<div style='background:#030810;border:1px solid #0d2545;border-radius:9px;padding:.55rem;text-align:center'><div style='color:#3a6080;font-size:.63rem;font-weight:600;text-transform:uppercase'>P(success)</div><div style='color:#ffd60a;font-size:1.15rem;font-weight:700'>{int(exp['p']*100)}%</div><div style='color:#3a6080;font-size:.63rem;margin-top:3px'>Value</div><div style='color:#00c896;font-size:.9rem;font-weight:600'>{exp['v']}/10</div></div>",unsafe_allow_html=True)

# ── MICROBIOME DOMAIN ────────────────────────────────────────────────────────────
def render_microbiome_domain():
    color = "#00c896"
    gene_input, do_search = render_sidebar("microbiome")
    run_gene = st.session_state.pop("_run_gene", None)
    if do_search and gene_input.strip(): run_gene = gene_input.strip()

    st.markdown(f"<div style='padding:1.1rem 1.5rem .5rem;border-bottom:1px solid #0d2545'><span style='font-size:1.7rem'>🦠</span> <span style='color:{color};font-weight:700;font-size:1.1rem'>Microbiome Intelligence</span><div style='color:#2a4050;font-size:.75rem;margin-top:2px'>AI-powered functional annotation · Host-microbe interactions · TMAO · FMT · Pathway reannotation</div></div>", unsafe_allow_html=True)

    if run_gene: render_gene_analysis(run_gene, "microbiome"); st.markdown("<hr style='border-color:#0d2545;margin:.6rem 0'>", unsafe_allow_html=True)

    t_ai, t_tax, t_file, t_lit = st.tabs(["🤖 AI Functional Annotation","🔬 Microbe Profile","📁 Annotate My Data","📚 Literature"])

    with t_ai:
        sh("🤖","AI-Powered Gene Function Reannotation","#00c896")
        st.markdown("<div style='background:#020d10;border:1px solid #00c89633;border-radius:10px;padding:.8rem 1.1rem;margin-bottom:.8rem'><div style='color:#00c896;font-weight:600;font-size:.85rem;margin-bottom:.3rem'>The annotation problem — solved</div><div style='color:#3a6060;font-size:.8rem;line-height:1.7'>Standard tools (KEGG, GO, COG) annotate microbial genes as \"biosynthesis\", \"chemosynthesis\", \"protein aggregation\" — these terms are useless for understanding what the microbe actually DOES in the host. This tool uses Claude to reannotate database IDs with meaningful biological context: specific metabolites produced, host receptor interactions, disease associations, and community-level function.</div></div>", unsafe_allow_html=True)
        gene_ids_input = st.text_area("Paste gene IDs or functional annotations (one per line)", placeholder="COG0001\nK00001\nGO:0009058\nbiosynthesis\nbeta-oxidation\nphosphate transport", height=120, key="micro_gene_ids")
        research_ctx = st.text_input("Research context (optional)", placeholder="e.g. Gut dysbiosis in IBD patients, analysing Firmicutes-to-Bacteroidetes ratio changes", key="micro_ctx")
        if st.button("🧠 Reannotate with AI", key="micro_annotate", type="primary"):
            if gene_ids_input.strip():
                ids = parse_functional_annotation_file(gene_ids_input)
                lab_focus = lab.get("research_focus","")
                with st.spinner(f"Claude is reannotating {len(ids)} functional annotations..."):
                    result = annotate_microbial_genes_llm(ids, research_ctx, lab_focus)
                if result.get("error"): st.error(result["error"])
                elif result.get("annotations"):
                    for ann in result["annotations"]:
                        conf_c = {"high":"#00c896","medium":"#ffd60a","low":"#ff8c42"}.get(ann.get("evidence_quality","low"),"#5a8090")
                        with st.expander(f"**{ann.get('id','')}** — {ann.get('true_function','')[:60]}...", expanded=True):
                            st.markdown(f"<div style='background:#020d10;border-left:3px solid {conf_c};padding:.75rem 1rem;border-radius:0 9px 9px 0'>", unsafe_allow_html=True)
                            for field,label,clr in [("true_function","True biological function","#00c896"),("metabolite","Metabolite","#4a90d9"),("host_interaction","Host interaction","#a855f7"),("disease_relevance","Disease relevance","#ff8c42"),("research_gap","Research gap","#ffd60a")]:
                                val = ann.get(field,"")
                                if val: st.markdown(f"<div style='margin-bottom:.25rem'><span style='color:{clr};font-weight:600;font-size:.76rem'>{label}:</span> <span style='color:#8ab0c0;font-size:.8rem'>{val}</span></div>", unsafe_allow_html=True)
                            orgs = ann.get("key_organisms",[])
                            if orgs: st.markdown(f"<div style='color:#3a6080;font-size:.74rem'>Key organisms: {', '.join(orgs[:4])}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div style='color:{conf_c};font-size:.7rem'>Evidence: {ann.get('evidence_quality','?')}</div>", unsafe_allow_html=True)
                            st.markdown("</div>", unsafe_allow_html=True)
                elif result.get("raw"): st.markdown(result["raw"])
            else:
                st.warning("Paste some gene IDs or functional annotations first.")

    with t_tax:
        sh("🔬","Microbe Biological Profile","#00c896")
        taxon_input = st.text_input("Microbe name", placeholder="e.g. Akkermansia muciniphila, Bacteroides fragilis, Faecalibacterium prausnitzii", key="taxon_input")
        tax_ctx = st.text_input("Host/disease context (optional)", placeholder="e.g. Gut microbiome in colorectal cancer patients", key="tax_ctx")
        if st.button("🧬 Generate Microbe Profile", key="taxon_btn", type="primary"):
            if taxon_input.strip():
                with st.spinner(f"Claude is profiling {taxon_input}..."):
                    profile = annotate_microbe_taxonomy_llm(taxon_input, tax_ctx)
                if profile.get("error"): st.error(profile["error"])
                elif profile.get("raw"): st.markdown(profile["raw"])
                else:
                    # Structured display
                    c1,c2 = st.columns(2)
                    with c1:
                        for field,label,clr in [("classification","Classification","#00c896"),("gram_status","Gram status","#4a90d9"),("metabolism","Metabolism","#a855f7"),("gut_niche","Gut niche","#ffd60a")]:
                            val=profile.get(field,""); st.markdown(f"<div style='padding:4px 0;border-bottom:1px solid #0d2545;font-size:.8rem'><span style='color:{clr};font-weight:600'>{label}:</span> <span style='color:#d0e8ff'>{val}</span></div>", unsafe_allow_html=True) if val else None
                        if profile.get("key_functions"):
                            sh("⚙️","Key functions",color)
                            for f in profile["key_functions"]: st.markdown(f"<div style='color:#6a9ab0;font-size:.78rem;padding:2px 0'>→ {f}</div>", unsafe_allow_html=True)
                    with c2:
                        if profile.get("metabolites_produced"):
                            sh("⚗️","Metabolites produced",color)
                            for m in profile["metabolites_produced"]: st.markdown(f"<div style='color:#6a9ab0;font-size:.78rem;padding:2px 0'>• {m}</div>", unsafe_allow_html=True)
                        if profile.get("disease_associations"):
                            sh("🩺","Disease associations",color)
                            for da in profile["disease_associations"]:
                                dir_clr="#ff2d55" if da.get("direction")=="increased" else "#4a90d9"
                                ev_clr={"strong":"#00c896","moderate":"#ffd60a","weak":"#ff8c42"}.get(da.get("evidence","weak"),"#5a8090")
                                st.markdown(f"<div style='font-size:.78rem;padding:3px 0;border-bottom:1px solid #0d2545'><span style='color:#d0e8ff'>{da.get('condition','')}</span> <span style='color:{dir_clr}'>{da.get('direction','')}</span> <span style='color:{ev_clr};font-size:.7rem'>({da.get('evidence','')})</span></div>", unsafe_allow_html=True)
                        if profile.get("therapeutic_potential"):
                            sh("💊","Therapeutic potential",color)
                            st.markdown(f"<div style='color:#6a9ab0;font-size:.8rem'>{profile['therapeutic_potential']}</div>", unsafe_allow_html=True)
            else:
                st.warning("Enter a microbe name.")

    with t_file:
        sh("📁","Annotate My Metagenome Data","#00c896")
        st.markdown("<div style='color:#5a8090;font-size:.8rem;margin-bottom:.6rem'>Upload your functional annotation output from DIAMOND, HUMAnN3, PROKKA, eggNOG-mapper, or any tool that produces COG/KEGG/GO/InterPro annotations. Claude will explain what your community is ACTUALLY doing.</div>", unsafe_allow_html=True)
        uploaded = st.file_uploader("Upload functional annotation file (CSV, TSV, TXT)", type=["csv","tsv","txt"], key="micro_file")
        pathway_text = st.text_area("Or paste pathway/function list directly", placeholder="K00001\nK00002\nbiosynthesis of cofactors\nCOG0001\nGO:0009058", height=100, key="micro_paste")
        context_input = st.text_input("Sample context", placeholder="e.g. Gut microbiome, IBD patient, post-FMT day 7", key="micro_sample_ctx")
        if st.button("🧠 Annotate Community Function", key="annotate_file", type="primary"):
            text_to_parse = pathway_text
            if uploaded:
                try:
                    import pandas as pd, io
                    if uploaded.name.endswith(".csv"): df=pd.read_csv(uploaded)
                    else: df=pd.read_csv(uploaded,sep="\t")
                    text_to_parse = "\n".join(df.iloc[:,0].astype(str).tolist()[:50])
                except: text_to_parse = uploaded.read().decode("utf-8","ignore")[:3000]
            if text_to_parse.strip():
                ids = parse_functional_annotation_file(text_to_parse)
                with st.spinner(f"Reannotating {len(ids)} functions with Claude..."):
                    result = annotate_microbial_genes_llm(ids, context_input, lab.get("research_focus",""))
                    if ids[:5]:
                        pathway_interp = pathway_annotation_analysis(ids[:15], context_input)
                with st.spinner("Generating community-level interpretation..."):
                    pass  # Already done above
                if pathway_interp and not pathway_interp.get("error"):
                    st.markdown("---")
                    sh("🌐","Community-Level Interpretation","#00c896")
                    if pathway_interp.get("pathway_summary"): info_box(pathway_interp["pathway_summary"], "#00c896")
                    if pathway_interp.get("key_metabolites_predicted"):
                        sh("⚗️","Predicted metabolites reaching host","#00c896")
                        for met in pathway_interp["key_metabolites_predicted"][:5]:
                            if isinstance(met, dict):
                                st.markdown(f"<div style='padding:4px 0;border-bottom:1px solid #0d2545;font-size:.8rem'><span style='color:#00c896;font-weight:500'>{met.get('metabolite','')}</span> <span style='color:#3a6060;font-size:.75rem'>from {met.get('source_pathway','')} → {met.get('host_effect','')}</span></div>", unsafe_allow_html=True)
                if result.get("annotations"):
                    st.markdown("---")
                    sh("🔬","Per-function annotations","#00c896")
                    for ann in result["annotations"][:8]:
                        with st.expander(f"{ann.get('id','')} — {ann.get('true_function','')[:55]}...", expanded=False):
                            for field,label in [("true_function","True function"),("metabolite","Metabolite"),("host_interaction","Host interaction"),("disease_relevance","Disease relevance")]:
                                val=ann.get(field,"")
                                if val: st.markdown(f"**{label}:** {val}")
            else:
                st.warning("Upload a file or paste annotations.")

    with t_lit:
        sh("📄","Microbiome Literature — PubMed 2022–2025","#00c896")
        micro_qs = ["gut microbiome disease mechanism metabolite 2023 2024[pdat]","TMAO cardiovascular arrhythmia gut bacteria 2023 2024[pdat]","fecal microbiota transplant clinical trial 2023 2024[pdat]","gut-brain axis serotonin 2023 2024[pdat]","microbiome AI machine learning functional annotation 2023 2024[pdat]","16S metagenomics annotation LLM 2023 2024[pdat]"]
        sel_q = st.selectbox("Query",micro_qs,key="micro_lit_q")
        if st.button("Fetch ↗",key="micro_fetch"):
            with st.spinner("Fetching..."):
                papers = pubmed_microbiome(sel_q, 10)
            for p in papers:
                with st.expander(f"{tier_badge(classify_tier(p['title']))} &nbsp; {p['title'][:70]}...", expanded=False):
                    st.markdown(f"<div style='font-size:.76rem;color:#5a8090'>{p['authors']} · <i>{p['journal']}</i> · {p['year']}</div>",unsafe_allow_html=True)
                    st.markdown(f"<a href='{p['url']}' target='_blank' style='font-size:.7rem'>PubMed {p['pmid']} ↗</a>",unsafe_allow_html=True)
        else:
            st.info("Select a query and click Fetch.")

# ── DOMAIN ROUTER ────────────────────────────────────────────────────────────────
def render_standard_domain(domain_key):
    D = DOMAINS_META[domain_key]; color = D["color"]
    gene_input, do_search = render_sidebar(domain_key)
    run_gene = st.session_state.pop("_run_gene", None)
    if do_search and gene_input.strip(): run_gene = gene_input.strip()

    st.markdown(f"<div style='padding:1.1rem 1.5rem .5rem;border-bottom:1px solid #0d2545;display:flex;align-items:center;gap:10px'><span style='font-size:1.7rem'>{D['icon']}</span><div><div style='color:{color};font-weight:700;font-size:1.1rem'>{D['label']}</div><div style='color:#2a4050;font-size:.75rem'>{D['tagline']}</div></div></div>", unsafe_allow_html=True)

    if run_gene: render_gene_analysis(run_gene, domain_key); st.markdown("<hr style='border-color:#0d2545;margin:.6rem 0'>", unsafe_allow_html=True)

    # Domain info tabs
    t_quick, t_ref = st.tabs(["Quick Reference","Domain Resources"])
    with t_quick:
        domain_facts = {
            "neuro":[("Tau (MAPT) phosphorylation","85+ phospho-sites on PhosphoSite — most are kinase noise. Only disease-causing mutations (R406W FTLD, P301L/S) and NFT-forming sites (Ser202/Thr205) are validated signals.","#a855f7"),("GBA + LRRK2 interaction","GBA variants + LRRK2 variants together cause earlier-onset Parkinson's than either alone. Digenic genetics.","#a855f7"),("BBB penetration rules","MW <500 Da, logP 1–3, few H-bond donors, few H-bond acceptors. P-gp efflux substrate = CNS failure.","#a855f7"),("DRD2 occupancy","65% receptor occupancy = therapeutic threshold. >80% = EPS risk. Clozapine: lower D2 + higher 5-HT2A = atypical.","#a855f7"),("SOD1 G93A model warning","100+ drugs worked in this model, zero translated to ALS. Not a reliable preclinical model for non-SOD1 ALS.","#ff2d55")],
            "onco":[("KRAS targetability","G12C = covalently targetable (sotorasib, adagrasib). G12D and G12V still lack approved direct inhibitors. Different chemistries required.","#ff2d55"),("TMB threshold","≥10 mut/Mb predicts pembrolizumab response (FDA pan-tumour approval). Ultra-high TMB (>100, POLE) = exceptional IO response.","#ff2d55"),("Founder mutation principle","Earliest somatic mutation in tumour evolution = primary target. Late mutations are passengers — targeting them causes rapid resistance.","#ff2d55"),("HER2-low","IHC 1+ or 2+/ISH- was previously HER2-negative. T-DXd (Enhertu) achieves 57% ORR — redefined a new targetable population.","#ff2d55"),("Biomarker-unselected trial failure","EGFR inhibitors failed in unselected NSCLC until EGFR mutation testing was mandatory. Never run a targeted therapy trial without predictive biomarker selection.","#ff8c42")],
            "proteins":[("AlphaMissense threshold","Score ≥0.564 = pathogenic prediction. Sensitivity 90%, specificity 73% vs ClinVar. Concordant + ClinVar P/LP = highest priority.","#00e5ff"),("FLNA Ser2152 gating","PKA cannot phosphorylate FLNA Ser2152 in the autoinhibited state. Gating by GPCR H8 dislodgement = mechanistically distinct from background noise.","#00e5ff"),("ARRB2 deprioritise","Zero confirmed Mendelian disease variants. ARRB1/ARRB2 double KO mice viable. $4,050,000 in avoidable spend if pursuing. Use Filamin Ser2152-P instead.","#ff2d55"),("Cryo-EM resolution","Now routinely sub-2Å for soluble proteins. Below ~1.5Å: direct observation of H atoms, water networks, protonation states.","#00e5ff"),("Discordant variants","ClinVar P/LP but AlphaMissense <0.564 = non-structural mechanism. Do NOT do TSA — do Co-IP or splicing assay instead.","#ffd60a")],
        }
        facts = domain_facts.get(domain_key, [])
        for fact_title, fact_body, fact_color in facts:
            st.markdown(f"<div style='display:flex;gap:9px;padding:6px 0;border-bottom:1px solid #0d2545'><span style='color:{fact_color};flex-shrink:0;font-size:.9rem;margin-top:1px'>→</span><div><div style='color:{fact_color};font-size:.78rem;font-weight:600'>{fact_title}</div><div style='color:#6a9ab0;font-size:.77rem;line-height:1.6'>{fact_body}</div></div></div>", unsafe_allow_html=True)

    with t_ref:
        resources = {
            "neuro":[("AlzForum","https://www.alzforum.org","Free","AD mutations, failed drugs, models"),("PDGene","https://pdgene.org","Free","PD GWAS loci"),("DisGeNET","https://www.disgenet.org","Free/API","Gene-disease associations"),("Allen Brain Atlas","https://portal.brain-map.org","Free/API","Brain region-specific expression"),("ADNI","https://adni.loni.usc.edu","Controlled","AD Neuroimaging Initiative — longitudinal")],
            "onco":[("cBioPortal","https://www.cbioportal.org","Free/API","Cancer genomics — TCGA + cohorts"),("OncoKB","https://www.oncokb.org","Free/API","Actionable variants — 4-level evidence"),("COSMIC","https://cancer.sanger.ac.uk/cosmic","Free/API","Somatic mutations — curated signatures"),("DepMap","https://depmap.org","Free","CRISPR screens — 900+ cell lines"),("IARC TP53","https://tp53.isb-cgc.org","Free","TP53 variant functional data")],
            "proteins":[("UniProt","https://www.uniprot.org","Free/API","Gold-standard curated proteins"),("AlphaFold DB","https://alphafold.ebi.ac.uk","Free/API","DeepMind structure predictions"),("AlphaMissense","https://alphamissense.hegelab.org","Free/API","Per-residue pathogenicity"),("PhosphoSite","https://www.phosphosite.org","Free","PTMs — curated modifications"),("GPCRdb","https://gpcrdb.org","Free","GPCR H8 conservation, FBM motifs")],
        }.get(domain_key, [])
        for rname,rurl,rtag,rdesc in resources:
            tc="#00c896" if "Free" in rtag and "API" not in rtag else "#ffd60a" if "API" in rtag else "#5a8090"
            st.markdown(f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:9px;padding:.55rem .85rem;margin-bottom:.22rem;display:flex;justify-content:space-between;align-items:center'><div><a href='{rurl}' target='_blank' style='color:#d0e8ff;font-weight:500;font-size:.83rem'>{rname}</a><div style='color:#2a4050;font-size:.71rem'>{rdesc}</div></div><span style='background:{tc}18;color:{tc};font-size:.67rem;padding:2px 7px;border-radius:6px;border:1px solid {tc}44;margin-left:8px;white-space:nowrap'>{rtag}</span></div>", unsafe_allow_html=True)

    st.markdown(f"<div style='color:#1e3a5a;font-size:.68rem;text-align:center;padding:1.2rem 0'>Protellect · {lab.get('lab_name','Biology Intelligence')} · UniProt · ClinVar · gnomAD · STRING · OpenTargets · AlphaFold · AlphaMissense · PubMed · ClinicalTrials.gov · {datetime.now().year}</div>", unsafe_allow_html=True)

# ── MAIN ROUTER ──────────────────────────────────────────────────────────────────
d = st.session_state.domain
if d is None:
    render_splash()
elif d == "microbiome":
    render_microbiome_domain()
else:
    render_standard_domain(d)
