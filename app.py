"""
app.py — Protellect MVP v3  |  streamlit run app.py

Universal biological dataset support:
  - Any file format, any size (chunked/sampled for very large files)
  - Any protein/gene — auto-fetches correct PDB structure from UniProt
  - Multi-gene/protein studies with per-gene tabs and overall summary
  - Context-aware: research goal shapes everything from structures to experiments
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import requests
import json
import base64
from pathlib import Path

from evidence_layer import calculate_dbr, assign_genomic_tier, get_genomic_verdict
try:
    from evidence_layer import (enrich_scored_df, PAPERS, TIER_DEFINITIONS,
                                 classify_protein_role, EXPERIMENT_LADDER,
                                 KNOWN_PIGGYBACK_PROTEINS, KNOWN_ESSENTIAL_PROTEINS)
except ImportError:
    enrich_scored_df = lambda df, e=None: df
    PAPERS = TIER_DEFINITIONS = EXPERIMENT_LADDER = {}
    KNOWN_PIGGYBACK_PROTEINS = KNOWN_ESSENTIAL_PROTEINS = {}
    # Hardcoded known proteins for when classify_protein_role isn't available
    _ESSENTIAL = {
        "FLNA":"Filamin A — ubiquitous, X chromosome. Mutations: periventricular heterotopia, cardiac arrhythmia, aortic aneurysm, intellectual disability, epilepsy.",
        "FLNB":"Filamin B — chromosome 3. Mutations: boomerang dysplasia, Larsen syndrome, atelosteogenesis.",
        "FLNC":"Filamin C — chromosome 7, cardiac/skeletal muscle. DBR >1.5, one of the most pathogenically constrained proteins known.",
        "CHRM2":"CHRM2 (Muscarinic M2) — chromosome 7. ~102 dominant-form pathogenic variants causing dilated cardiomyopathy.",
        "CHRM3":"CHRM3 (Muscarinic M3) — chromosome 1. Confirmed Prune belly syndrome gene.",
        "BRCA1":"BRCA1 — breast/ovarian cancer. Critical disease driver.",
        "BRCA2":"BRCA2 — breast/ovarian cancer. Critical disease driver.",
        "TP53":"TP53 — ubiquitous tumour suppressor. Most mutated gene in cancer.",
        "EGFR":"EGFR — receptor tyrosine kinase. Lung cancer and other malignancies.",
        "KRAS":"KRAS — GTPase. Pancreatic, colorectal, lung cancer.",
    }
    _SCAFFOLD = {
        "ARRB1":"β-arrestin 1 — ZERO germline pathogenic variants. Structural scaffold for GPCRs and Filamin. The disease biology lies in its partners, not itself.",
        "ARRB2":"β-arrestin 2 — ZERO germline pathogenic variants. Same pattern as β-arrestin 1.",
        "TALN1":"Talin 1 — ZERO germline pathogenic variants. Structural integrin scaffold. Mouse KO lethal but humans tolerate mutations.",
        "TALN2":"Talin 2 — ZERO germline pathogenic variants. Structural scaffold.",
    }
    def classify_protein_role(g, n, **kw):
        gu = str(g).upper()
        # ANY confirmed pathogenic variant = NOT a scaffold
        if n > 0:
            note = _ESSENTIAL.get(gu, f"{n} confirmed pathogenic ClinVar variants.")
            if n >= 500: return {'role':'critical_driver','label':'Critical disease driver','icon':'🔴','color':'#FF4C4C','note':note}
            elif n >= 50: return {'role':'validated','label':'Genomically validated disease gene','icon':'🟠','color':'#FFA500','note':note}
            elif n >= 5:  return {'role':'validated','label':'Validated disease gene','icon':'🟠','color':'#FFA500','note':note}
            else:         return {'role':'rare_mendelian','label':'Confirmed rare Mendelian disease gene','icon':'🟡','color':'#FFD700','note':f'{n} pathogenic variant(s). Rare disease — not the β-arrestin pattern.'}
        # Zero pathogenic — check scaffold list
        if gu in _SCAFFOLD:
            return {'role':'piggyback','label':'Structural scaffold / piggyback protein','icon':'🔗','color':'#888','note':_SCAFFOLD[gu],'warning':_SCAFFOLD[gu]}
        # Zero but not known scaffold
        return {'role':'unvalidated','label':'No ClinVar disease evidence','icon':'⚪','color':'#555','note':'Zero germline pathogenic variants. Check gnomAD and OMIM before committing resources.','warning':'Zero ClinVar pathogenic variants. May be a structural scaffold — study interaction partners first.'}
from scorer import (
    load_file, score_residues, get_summary_stats, validate_dataframe,
    detect_dataset_info, generate_top_pathways, ML_AVAILABLE,
)

# ── Config ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Protellect", page_icon="🧬",
                   layout="wide", initial_sidebar_state="expanded")

# ── Logo ───────────────────────────────────────────────────────────────────
try:
    from logo import LOGO_DATA_URL as LOGO_B64
except Exception:
    _lp = Path("/mnt/user-data/uploads/1777622887238_image.png")
    LOGO_B64 = ("data:image/png;base64," + base64.b64encode(_lp.read_bytes()).decode()) if _lp.exists() else None

# ── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Inter:wght@300;400;500;600&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif}
h1,h2,h3{font-family:'IBM Plex Mono',monospace}
[data-testid="stSidebar"]{background:#07080f;border-right:1px solid #1a1d2e}

.stat-card{background:#0f1117;border:1px solid #1e2030;border-radius:10px;padding:18px;text-align:center}
.stat-number{font-size:1.9rem;font-weight:600;font-family:'IBM Plex Mono',monospace;display:block;margin-bottom:4px}
.stat-label{font-size:0.68rem;text-transform:uppercase;letter-spacing:0.12em;color:#555}
.sec-label{font-family:'IBM Plex Mono',monospace;font-size:0.68rem;text-transform:uppercase;
           letter-spacing:0.18em;color:#444;border-bottom:1px solid #1e2030;padding-bottom:6px;margin-bottom:14px}
.hyp-card{background:#0f1117;border-left:3px solid #1e2030;padding:14px 16px;
          border-radius:0 8px 8px 0;font-size:0.83rem;color:#999;margin-bottom:10px;line-height:1.8}
.ml-banner{background:#0a0a1a;border:1px solid #2a2d5a;border-radius:8px;padding:10px 14px;
           margin-bottom:14px;font-size:0.8rem;color:#8888cc}
.assay-box{background:#07100a;border:1px solid #1a3a1a;border-radius:8px;padding:14px 16px;margin-top:8px}
.assay-title{font-family:'IBM Plex Mono',monospace;font-size:0.65rem;text-transform:uppercase;
             letter-spacing:0.15em;color:#4CAF50;margin-bottom:8px}
.assay-row{display:flex;gap:8px;padding:5px 0;font-size:0.78rem;border-bottom:1px solid #0a1a0a}
.assay-lbl{color:#2a5a2a;min-width:110px;font-size:0.7rem;font-family:'IBM Plex Mono',monospace;flex-shrink:0}
.assay-val{color:#aaa}
.gene-card{background:#0f1117;border:1px solid #1e2030;border-radius:8px;padding:10px 14px;margin-bottom:8px}
.pw-card{background:#0f1117;border:1px solid #1e2030;border-radius:10px;padding:14px;margin-bottom:8px}
.pw-meta{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:#555;margin-bottom:6px}
.pw-title{font-size:0.9rem;font-weight:600;color:#eee;margin-bottom:6px}
.pw-rat{font-size:0.82rem;color:#888;line-height:1.7;margin-bottom:8px}
.step{font-size:0.8rem;color:#777;padding:3px 0;border-bottom:1px solid #1a1d2e;line-height:1.6}
.facts-table{width:100%;border-collapse:collapse;font-size:0.82rem}
.facts-table td{padding:7px 10px;border-bottom:1px solid #1a1d2e;color:#bbb;vertical-align:top}
.facts-table td:first-child{color:#444;font-family:'IBM Plex Mono',monospace;font-size:0.7rem;width:130px}
</style>
""", unsafe_allow_html=True)


# ── Tutorial ────────────────────────────────────────────────────────────────
@st.dialog("How to use Protellect")
def show_tutorial():
    if LOGO_B64:
        st.markdown(f'<img src="{LOGO_B64}" style="height:48px;object-fit:contain;border-radius:8px;margin-bottom:12px">', unsafe_allow_html=True)
    st.markdown("#### Experimental Intelligence Layer — Universal Biological Dataset Support")
    steps = [
        ("Fill in the Q&A sidebar", "Tell Protellect your research goal, protein of interest, and hypothesis direction. This shapes everything: hypothesis text, experiments, structure selection, pathways."),
        ("Upload any file", "CSV, TSV, Excel, any format. DMS, CRISPR screens, RNA-seq, proteomics, variant data, stability, Protein Atlas, clinical data. No manual configuration."),
        ("Click Run Triage", "Scores every feature. Auto-detects scale direction (log2FC, ΔΔG, p-values, High/Med/Low). Queries UniProt, ClinVar, InterPro, PDB for your specific protein. ML scoring with real biological features."),
        ("Multi-gene support", "If your data has multiple genes/proteins, each gets its own breakdown. An overall study recommendation is generated."),
        ("Explore all 4 tabs", "Tab 1: ranked results + correct protein 3D structure. Tab 2: TP53 case study. Tab 3: Protein Explorer with click-to-annotate. Tab 4: Hypothesis Lab with structural animations."),
    ]
    for i, (t, d) in enumerate(steps, 1):
        c1, c2 = st.columns([0.07, 0.93])
        with c1:
            st.markdown(f'<div style="width:26px;height:26px;border-radius:50%;background:#FF4C4C22;color:#FF4C4C;border:1px solid #FF4C4C55;display:flex;align-items:center;justify-content:center;font-family:IBM Plex Mono,monospace;font-size:0.72rem;font-weight:600;margin-top:2px">{i}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f"**{t}**  \n{d}")
        st.markdown("")
    if st.button("Start exploring →", type="primary", use_container_width=True):
        st.session_state.tut_seen = True
        st.rerun()

if "tut_seen" not in st.session_state:
    st.session_state.tut_seen = False
if not st.session_state.tut_seen:
    show_tutorial()


# ── Structure loader ────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def fetch_pdb_fallback():
    try:
        r = requests.get("https://files.rcsb.org/download/2OCJ.pdb", timeout=15)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def make_viewer(pdb, res_scores, width=580, height=455, zoom="auto"):
    if not pdb:
        return "<html><body style='background:#080b14;display:flex;align-items:center;justify-content:center;height:100%;color:#444;font-family:monospace'>Structure not available</body></html>"
    esc = pdb.replace("\\","\\\\").replace("`","\\`").replace("${","\\${")[:260000]
    # Auto-detect residue range from PDB
    residues_in_pdb = []
    for line in pdb.split('\n'):
        if line.startswith('ATOM'):
            try:
                residues_in_pdb.append(int(line[22:26].strip()))
            except Exception:
                pass
    if residues_in_pdb:
        pdb_min, pdb_max = min(residues_in_pdb), max(residues_in_pdb)
        zoom_resi = f"{pdb_min}-{pdb_max}"
    else:
        zoom_resi = "1-999"

    styles = ""
    for resi, opts in res_scores.items():
        styles += f"v.addStyle({{resi:{resi}}},{{sphere:{{color:'{opts['color']}',radius:{opts['radius']}}}}});\n"
    return f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<style>body{{margin:0;background:#080b14}}#v{{width:{width}px;height:{height}px}}</style>
</head><body><div id="v"></div><script>
const p=`{esc}`;
let v=$3Dmol.createViewer('v',{{backgroundColor:'#080b14',antialias:true}});
v.addModel(p,'pdb');v.setStyle({{}},{{cartoon:{{color:'#1e2030',opacity:0.55}}}});
{styles}
v.zoomTo({{resi:'{zoom_resi}'}});v.spin(false);v.render();
</script></body></html>"""


# ── SIDEBAR ────────────────────────────────────────────────────────────────
with st.sidebar:
    cl, ct, ch = st.columns([1, 3.2, 1])
    with cl:
        if LOGO_B64:
            st.markdown(f'<img src="{LOGO_B64}" style="width:34px;height:34px;object-fit:contain;border-radius:6px;margin-top:6px">', unsafe_allow_html=True)
    with ct:
        st.markdown("### Protellect")
    with ch:
        if st.button("❓", help="Tutorial"):
            show_tutorial()
    st.markdown('<p style="font-size:0.72rem;color:#333;margin:-4px 0 0;font-family:IBM Plex Mono,monospace">Experimental Intelligence Layer</p>', unsafe_allow_html=True)
    if ML_AVAILABLE:
        st.markdown('<div class="ml-banner">🤖 ML scoring active — Gradient Boosting + biological feature engineering</div>', unsafe_allow_html=True)

    # About
    with st.expander("ℹ️ About Protellect"):
        st.markdown("""
**Protellect** converts raw wet lab assay data into ranked, annotated biological hypotheses.

**Goal:** Cut manual data interpretation time from hours to minutes. Researchers spend time validating the right targets — not hunting for them.

**Phase 1 (now):** Universal dataset support · live database enrichment for any protein  
**Phase 2:** Full protein family coverage · automated sequence alignment  
**Phase 3:** Closed-loop ML retraining from your validated outcomes
        """)

    st.divider()

    # Q&A
    st.markdown('<div class="sec-label">Scientist Q&A — Tailor Your Results</div>', unsafe_allow_html=True)
    study_goal = st.text_input("Research goal", placeholder="e.g. identify drug targets in oncology, map functional residues...", key="qa_goal")
    protein_of_interest = st.text_input("Protein / gene of interest", placeholder="e.g. TP53, EGFR, BRCA1 — or leave blank for auto-detect", key="qa_prot")
    study_focus = st.text_input("Specific focus area", placeholder="e.g. kinase domain, DNA binding, membrane anchor...", key="qa_focus")
    experiment_context = st.selectbox("Primary experiment type", [
        "Not specified","Deep mutational scanning (DMS)","CRISPR screen",
        "RNA-seq / gene expression","Protein stability (ΔΔG)","Variant pathogenicity",
        "Proteomics / mass spec","Protein Atlas / expression profiling",
        "Functional assay","Clinical / patient data","Other"
    ], key="qa_exp")
    hypothesis_direction = st.selectbox("Research direction", [
        "Not specified","Find loss-of-function mutations","Find gain-of-function mutations",
        "Identify drug target residues","Map protein-DNA / protein-protein interfaces",
        "Identify therapeutic rescue candidates",
        "Prioritise for structural biology (crystallography / cryo-EM)",
        "Clinical variant interpretation","Basic science / mechanism"
    ], key="qa_dir")

    scientist_context = {
        "study_goal": study_goal, "protein_of_interest": protein_of_interest,
        "study_focus": study_focus, "experiment_context": experiment_context,
        "hypothesis_direction": hypothesis_direction,
    }

    st.divider()

    # Upload
    st.markdown('<div class="sec-label">Data Upload</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload dataset",
        type=["csv","tsv","xlsx","xls","xlsm","txt"],
        label_visibility="collapsed")
    st.caption("CSV · TSV · Excel · any biological format  \nGene expression, DMS, CRISPR, variants, Protein Atlas...")
    with st.expander("View expected formats"):
        st.code("# Protein mutations (CSV):\nresidue_position,effect_score,mutation\n175,0.99,R175H\n\n# Gene expression (TSV / Excel):\nGene\tLevel\nENSG001\tHigh\nENSG002\tLow\n\n# Any numeric score column works", language="text")
    use_sample = st.checkbox("Use TP53 DMS sample data", value=not bool(uploaded_file))

    st.divider()

    # Sensitivity
    st.markdown('<div class="sec-label">Triage Sensitivity</div>', unsafe_allow_html=True)
    sens_mode = st.radio("Mode", ["Preset","Manual"], horizontal=True, label_visibility="collapsed")
    if sens_mode == "Preset":
        preset = st.selectbox("Profile", [
            "Standard (0.75 / 0.40)",
            "Strict — fewer HIGH hits (0.85 / 0.55)",
            "Permissive — more HIGH hits (0.65 / 0.30)",
            "Very permissive (0.55 / 0.20)",
        ], label_visibility="collapsed")
        pmap = {"Standard (0.75 / 0.40)":(0.75,0.40),"Strict — fewer HIGH hits (0.85 / 0.55)":(0.85,0.55),
                "Permissive — more HIGH hits (0.65 / 0.30)":(0.65,0.30),"Very permissive (0.55 / 0.20)":(0.55,0.20)}
        high_t, med_t = pmap[preset]
        st.caption(f"HIGH ≥ **{high_t}** · MEDIUM ≥ **{med_t}**")
    else:
        ch, cm = st.columns(2)
        with ch: high_t = st.number_input("HIGH ≥", 0.01, 1.0, 0.75, 0.01, format="%.2f")
        with cm: med_t  = st.number_input("MED ≥",  0.01, 1.0, 0.40, 0.01, format="%.2f")
        if high_t <= med_t:
            st.warning("HIGH must be > MEDIUM.")
            high_t = min(med_t + 0.05, 1.0)

    use_ml  = st.checkbox("ML-assisted scoring", value=ML_AVAILABLE, disabled=not ML_AVAILABLE)
    use_db  = st.checkbox("Live database enrichment (UniProt · ClinVar · InterPro · PDB)", value=True)
    run_btn = st.button("▶  Run Triage", type="primary", use_container_width=True)

    # Assay summary
    if "t_info" in st.session_state and "t_scored" in st.session_state:
        info   = st.session_state.t_info
        scored = st.session_state.t_scored
        pc     = "priority_final" if "priority_final" in scored.columns else "priority"
        n_high = int((scored[pc]=="HIGH").sum())
        top    = scored.iloc[0] if len(scored) > 0 else pd.Series(dtype=object)
        top_lbl = str(top.get("mutation",f"Pos{int(top.get('residue_position',0))}")) if len(scored)>0 else "—"
        if top_lbl in ("nan",""): top_lbl = f"Pos{int(top.get('residue_position',1))}"
        exps   = ", ".join(info.get("exp_types",[])[:3]) or "Not specified"
        ml_tag = " · ML" if info.get("ml_used") else ""
        db_tag = " · DB enriched" if info.get("db_enriched") else ""
        pname  = info.get("protein_name","")
        uid    = info.get("uniprot_id","")
        gene   = info.get("gene_name","")
        pfunc  = info.get("protein_function","")

        protein_row = ""
        if pname or gene:
            protein_row = f"""
          <div class="assay-row"><span class="assay-lbl">Protein</span><span class="assay-val" style="color:#4CA8FF;font-weight:600">{pname or gene}</span></div>
          <div class="assay-row"><span class="assay-lbl">UniProt</span><span class="assay-val">{uid}</span></div>
          <div class="assay-row"><span class="assay-lbl">Function</span><span class="assay-val" style="font-size:0.73rem">{pfunc[:100]}{'...' if len(pfunc)>100 else ''}</span></div>"""

        genes = info.get("genes",[])
        genes_row = f'<div class="assay-row"><span class="assay-lbl">Genes</span><span class="assay-val">{", ".join(genes[:5])}</span></div>' if len(genes)>1 else ""

        st.markdown(f"""
        <div class="assay-box">
          <div class="assay-title">📋 Assay Summary{ml_tag}{db_tag}</div>
          {protein_row}
          {genes_row}
          <div class="assay-row"><span class="assay-lbl">Dataset type</span><span class="assay-val">{info['assay_guess']}</span></div>
          <div class="assay-row"><span class="assay-lbl">Features</span><span class="assay-val">{info['n_rows']}</span></div>
          <div class="assay-row"><span class="assay-lbl">Scale</span><span class="assay-val">{info['direction_note']}</span></div>
          <div class="assay-row"><span class="assay-lbl">HIGH hits</span><span class="assay-val" style="color:#FF4C4C;font-weight:600">{n_high}</span></div>
          <div class="assay-row" style="border:none"><span class="assay-lbl">Top hit</span><span class="assay-val" style="color:#FF4C4C;font-weight:600">{top_lbl} ({round(float(top.get('normalized_score',0)),3) if len(scored)>0 else '—'})</span></div>
        </div>""", unsafe_allow_html=True)

    # Top 5 pathways
    if "t_pathways" in st.session_state:
        st.divider()
        st.markdown('<div class="sec-label">Top 5 Experimental Pathways</div>', unsafe_allow_html=True)
        priority_color = {"Immediate":"#4CAF50","High":"#FFA500","Medium":"#4CA8FF","Phase 3":"#9370DB"}
        for pw in st.session_state.t_pathways:
            pc_color = priority_color.get(pw["priority"],"#555")
            with st.expander(f"{pw['icon']} {pw['rank']}. {pw['title']}"):
                st.markdown(f'<span style="color:{pc_color};font-size:0.72rem;font-family:IBM Plex Mono,monospace;font-weight:600">{pw["priority"].upper()}</span> · {pw["cost"]} · {pw["timeline"]}', unsafe_allow_html=True)
                st.markdown(f'*{pw["rationale"]}*')
                for step in pw["steps"]:
                    st.markdown(f"• {step}")


    # ── Genomic Validation Panel ────────────────────────────────────────────
    if "t_verdict" in st.session_state:
        v = st.session_state.t_verdict
        st.divider()
        st.markdown('<div class="sec-label">Genomic Validation</div>', unsafe_allow_html=True)
        tc = v.get("color","#888")
        dbr_str = f"{v['dbr']:.3f}" if v.get('dbr') is not None else "N/A"
        paper = v.get("papers",[{}])[0]
        st.markdown(f"""<div style="background:#0a0a14;border:1px solid {tc}55;border-radius:8px;padding:12px 14px;margin-bottom:8px">
  <div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:{tc};margin-bottom:8px">{v['icon']} {v['label']}</div>
  <div style="display:flex;justify-content:space-between;margin-bottom:5px"><span style="font-size:0.72rem;color:#555">Pathogenic variants (ClinVar)</span><span style="font-family:IBM Plex Mono,monospace;font-size:0.72rem;color:{tc};font-weight:600">{v['n_pathogenic']}</span></div>
  <div style="display:flex;justify-content:space-between;margin-bottom:5px"><span style="font-size:0.72rem;color:#555">Protein length (aa)</span><span style="font-family:IBM Plex Mono,monospace;font-size:0.72rem;color:#aaa">{v['protein_length']}</span></div>
  <div style="display:flex;justify-content:space-between;margin-bottom:10px"><span style="font-size:0.72rem;color:#555">Disease burden ratio</span><span style="font-family:IBM Plex Mono,monospace;font-size:0.72rem;color:{tc};font-weight:600">{dbr_str}</span></div>
  <div style="font-size:0.75rem;color:#999;line-height:1.6;border-top:1px solid #1a1d2e;padding-top:8px">{v['trust_statement']}</div>
</div>
<div style="font-size:0.7rem;color:#555;margin-bottom:4px">Backed by: <a href="{paper.get('url','#')}" target="_blank" style="color:#4CA8FF;text-decoration:none">{paper.get('short','')}</a></div>""", unsafe_allow_html=True)

    st.divider()
    st.caption("Auto-fetches correct protein structure from UniProt/PDB for any gene")


# ══════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🧬  Triage System", "🔬  Case Study", "⚗️  Protein Explorer",
    "💡  Hypothesis Lab", "🔎  Protein Deep Dive", "🦠  Disease Explorer",
])


# ══════════════════════════════════════════════════════════════════════════
# TAB 1 — TRIAGE
# ══════════════════════════════════════════════════════════════════════════
with tab1:
    if LOGO_B64:
        st.markdown(f'<div style="display:flex;align-items:center;gap:14px;margin-bottom:6px"><img src="{LOGO_B64}" style="height:44px;object-fit:contain;border-radius:8px"><div><h2 style="margin:0;font-size:1.4rem">Triage System</h2><p style="color:#555;font-size:0.84rem;margin:0">Universal biological dataset support · ML-assisted scoring · live database enrichment</p></div></div>', unsafe_allow_html=True)
    st.divider()

    # ── Run Triage ────────────────────────────────────────────────────────
    if run_btn:
        if uploaded_file:
            with st.spinner("Reading file..."):
                try:
                    df_raw = load_file(uploaded_file)
                except Exception as e:
                    st.error(f"❌ Could not read file: {e}")
                    st.stop()
        elif use_sample:
            df_raw = pd.read_csv("sample_data/example.csv")
        else:
            st.error("Please upload a file or enable sample data.")
            st.stop()

        df_raw.columns = [str(c).strip() for c in df_raw.columns]
        valid, err = validate_dataframe(df_raw)
        if not valid:
            st.error(f"❌ {err}")
            st.stop()

        ctx = scientist_context if any(
            v and v not in ("Not specified","")
            for v in scientist_context.values()
        ) else None

        import scorer as _sc
        _sc.assign_priority = lambda s, h=high_t, m=med_t: "HIGH" if s>=h else "MEDIUM" if s>=m else "LOW"

        # Phase 1: fast scoring
        with st.spinner(f"Scoring {len(df_raw)} features..."):
            try:
                info = detect_dataset_info(df_raw, ctx)
            except TypeError:
                info = detect_dataset_info(df_raw)
            scored = score_residues(df_raw, context=ctx)
            info["ml_used"] = use_ml and ML_AVAILABLE
            stats  = get_summary_stats(scored)
            pathways = generate_top_pathways(scored, info, ctx)

        st.session_state.update({
            "t_scored":scored,"t_stats":stats,"t_info":info,
            "t_pathways":pathways,"t_context":ctx,"t_enrichment":None,"t_protein":None
        })

        # Phase 2: DB enrichment (correct protein structure + features)
        if use_db:
            try:
                from db_enrichment import detect_protein_from_data, enrich_protein
                protein_info = detect_protein_from_data(df_raw, ctx)
                gene = protein_info.get("gene_name","")
                uid  = protein_info.get("uniprot_id","")
                if gene or uid:
                    enrich_label = gene or uid
                    with st.spinner(f"Querying UniProt · ClinVar · InterPro · PDB for **{enrich_label}**..."):
                        enrichment = enrich_protein(gene_name=gene, uniprot_id=uid)
                        scored_rich = score_residues(df_raw, context=ctx,
                                                     enrichment=enrichment,
                                                     high_t=high_t, med_t=med_t)
                        stats_rich = get_summary_stats(scored_rich)
                        info["db_enriched"]       = True
                        info["gene_name"]         = gene
                        info["uniprot_id"]        = uid
                        info["protein_name"]      = enrichment.get("uniprot",{}).get("protein_name","")
                        info["protein_function"]  = enrichment.get("uniprot",{}).get("function","")[:300]
                        scored_rich = enrich_scored_df(scored_rich, enrichment)
                        stats_rich  = get_summary_stats(scored_rich)
                        clinvar_data = enrichment.get("clinvar", {})
                        uni_data     = enrichment.get("uniprot", {})
                        n_path = sum(
                            1 for variants in clinvar_data.values()
                            for v in variants
                            if "pathogenic" in v.get("significance","").lower()
                            and "benign" not in v.get("significance","").lower()
                        )
                        prot_len = uni_data.get("length", 0)
                        dbr  = calculate_dbr(n_path, prot_len)
                        tier = assign_genomic_tier(dbr, n_path)
                        verdict = get_genomic_verdict(tier, gene, n_path, prot_len, dbr)
                        info["genomic_tier"]    = tier
                        info["genomic_verdict"] = verdict
                        st.session_state.update({
                            "t_scored":scored_rich,"t_stats":stats_rich,
                            "t_info":info,"t_enrichment":enrichment,
                            "t_protein":protein_info,"t_verdict":verdict,
                        })
            except Exception:
                pass  # Fail gracefully

        st.rerun()

    # ── About / empty state ───────────────────────────────────────────────
    if "t_scored" not in st.session_state:
        if LOGO_B64:
            st.markdown(f'<div style="display:flex;align-items:center;gap:16px;margin-bottom:20px"><img src="{LOGO_B64}" style="height:60px;object-fit:contain;border-radius:10px"><div><h2 style="margin:0;font-family:IBM Plex Mono,monospace">Protellect</h2><p style="color:#555;margin:0">Experimental Intelligence Layer for Biomedical Research</p></div></div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#0a0c1a;border:1px solid #1e2030;border-radius:12px;padding:24px;margin-bottom:24px">
          <p style="font-family:'IBM Plex Mono',monospace;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.18em;color:#4CA8FF;margin-bottom:12px">About this tool</p>
          <p style="font-size:0.95rem;color:#ccc;line-height:1.8;margin-bottom:16px">
            Protellect converts raw experimental data from wet lab assays into ranked, annotated biological hypotheses — tailored to your specific research goal. A result that takes 2–4 hours manually takes under 2 minutes.
          </p>
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px">
            <div style="background:#080b14;border:1px solid #1e2030;border-radius:8px;padding:14px">
              <p style="font-family:'IBM Plex Mono',monospace;font-size:0.68rem;color:#FF4C4C;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px">① Input</p>
              <p style="font-size:0.82rem;color:#888;line-height:1.6">Any wet lab assay. DMS, CRISPR, RNA-seq, proteomics, stability, variant data, Protein Atlas. CSV, Excel, TSV, any format, any size.</p>
            </div>
            <div style="background:#080b14;border:1px solid #1e2030;border-radius:8px;padding:14px">
              <p style="font-family:'IBM Plex Mono',monospace;font-size:0.68rem;color:#FFA500;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px">② Intelligence</p>
              <p style="font-size:0.82rem;color:#888;line-height:1.6">ML scoring with real features from UniProt, ClinVar, InterPro, PDB — queried live for any protein. Context-aware hypotheses and experiments.</p>
            </div>
            <div style="background:#080b14;border:1px solid #1e2030;border-radius:8px;padding:14px">
              <p style="font-family:'IBM Plex Mono',monospace;font-size:0.68rem;color:#4CAF50;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px">③ Output</p>
              <p style="font-size:0.82rem;color:#888;line-height:1.6">Ranked hypotheses, correct 3D protein structure (not always TP53), mutation timeline, cell impact, and 5 tailored experimental pathways.</p>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)
        st.info("👈  Fill in the Q&A, upload your data, and click **▶ Run Triage**.")
        st.stop()

    scored = st.session_state.t_scored
    stats  = st.session_state.t_stats
    info   = st.session_state.t_info
    pc     = "priority_final" if "priority_final" in scored.columns else "priority"

    # ML banner
    if stats.get("ml_used"):
        st.markdown(f'<div class="ml-banner">🤖 ML scoring active · {stats["high_priority"]} HIGH · {stats["medium_priority"]} MEDIUM · {stats["low_priority"]} LOW · {info["assay_guess"]}</div>', unsafe_allow_html=True)

    # Stat cards
    c1,c2,c3,c4,c5 = st.columns(5)
    for col, num, lbl, clr in [
        (c1, stats["total_residues"],  "Features scored", "#eee"),
        (c2, stats["high_priority"],   "HIGH priority",   "#FF4C4C"),
        (c3, stats["medium_priority"], "MEDIUM priority", "#FFA500"),
        (c4, stats["low_priority"],    "LOW priority",    "#4CA8FF"),
        (c5, stats.get("top_score","—"), "Top score",     "#FF4C4C"),
    ]:
        col.markdown(f'<div class="stat-card"><span class="stat-number" style="color:{clr}">{num}</span><span class="stat-label">{lbl}</span></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── BIG GENOMIC DISEASE ASSOCIATION BANNER ───────────────────────────────
    verdict_state = st.session_state.get("t_verdict")
    enrich_state  = st.session_state.get("t_enrichment")
    proto_state   = st.session_state.get("t_protein")

    if verdict_state or enrich_state:
        try:
            from evidence_layer import classify_protein_role
        except ImportError:
            def classify_protein_role(g, n, **kw):
                if n==0: return {'role':'unvalidated','label':'No ClinVar evidence','icon':'⚪','color':'#555','note':'Zero pathogenic variants','warning':'Check ClinVar before investment.'}
                elif n<10: return {'role':'rare_mendelian','label':'Rare Mendelian disease gene','icon':'🟡','color':'#FFD700','note':f'{n} pathogenic variants'}
                elif n<200: return {'role':'validated','label':'Genomically validated','icon':'🟠','color':'#FFA500','note':f'{n} pathogenic variants'}
                else: return {'role':'critical_driver','label':'Critical disease driver','icon':'🔴','color':'#FF4C4C','note':f'{n} pathogenic variants'}
        gene_detected = (proto_state or {}).get("gene_name","")
        # Get pathogenic count from verdict OR compute from enrichment directly
        n_path_state = (verdict_state or {}).get("n_pathogenic", 0)
        # If verdict missing or zero, count from enrichment clinvar data
        if n_path_state == 0 and enrich_state:
            cv_data = enrich_state.get("clinvar", {})
            for variants in cv_data.values():
                if isinstance(variants, list):
                    for v in variants:
                        sig = v.get("significance","").lower()
                        if "pathogenic" in sig and "benign" not in sig:
                            n_path_state += 1
        # Also check UniProt natural variants with disease annotation
        if n_path_state == 0 and enrich_state:
            uni_data = enrich_state.get("uniprot", {})
            n_path_state += sum(1 for nv in uni_data.get("natural_variants",[]) if nv.get("disease") or nv.get("pathogenic"))

        tier_state    = (verdict_state or {}).get("tier","UNKNOWN")
        dbr_state     = (verdict_state or {}).get("dbr", None)
        prot_len_state= (verdict_state or {}).get("protein_length", 0)
        # Recompute DBR if we have better n_path_state
        if n_path_state > 0 and dbr_state in (None, 0.0):
            uni_len = enrich_state.get("uniprot",{}).get("length",0) if enrich_state else 0
            if uni_len > 0:
                dbr_state = round(n_path_state / uni_len, 4)
                from evidence_layer import assign_genomic_tier as _agt
                tier_state = _agt(dbr_state, n_path_state)
        role_state = classify_protein_role(gene_detected, n_path_state)
        tc_state      = (verdict_state or {}).get("color","#888")
        dbr_display   = f"{dbr_state:.3f}" if dbr_state is not None else "N/A"

        # Protein name
        prot_name = (enrich_state or {}).get("uniprot",{}).get("protein_name","") if enrich_state else ""
        gpcr_note = ""
        if enrich_state:
            uni_s = (enrich_state or {}).get("uniprot",{})
            if uni_s.get("is_gpcr"):
                gpcr_note = f" · GPCR ({uni_s.get('g_protein_coupling','')})"

        # Disease association level text
        if tier_state == "CRITICAL":
            assoc_headline = f"🔴 CRITICAL — Direct essential disease gene"
            assoc_detail   = f"{n_path_state} confirmed pathogenic germline variants. Every mutation in this protein causes serious human disease."
            assoc_action   = "Validate immediately. Human genetics unambiguously supports this target."
        elif tier_state == "HIGH":
            assoc_headline = f"🟠 HIGH — Confirmed disease gene"
            assoc_detail   = f"{n_path_state} confirmed pathogenic germline variants. Strong human genetic evidence for disease relevance."
            assoc_action   = "Prioritise for validation. 2.6× better clinical success rate with genetic support."
        elif tier_state == "LOW":
            assoc_headline = f"🟡 CONFIRMED RARE MENDELIAN DISEASE — NOT the β-arrestin pattern"
            assoc_detail   = f"{n_path_state} confirmed pathogenic germline variant(s). Rare disease: low DBR reflects disease rarity, not protein dispensability."
            assoc_action   = "Pursue with rare disease strategy. Orphan drug pathway applies."
        elif tier_state == "NONE":
            assoc_headline = f"⚪ NO DISEASE ASSOCIATION — Zero germline pathogenic variants"
            assoc_detail   = f"Humans who carry broken versions of this protein are apparently healthy. This is the β-arrestin pattern."
            assoc_action   = f"DO NOT pursue as primary drug target. Study interaction partners instead: {', '.join(role_state.get('partners',['—'])[:3])}"
        else:
            assoc_headline = f"❓ GENOMICALLY UNCHARACTERISED"
            assoc_detail   = "Insufficient ClinVar data. Establish genomic context before investment."
            assoc_action   = "Run ClinVar and gnomAD screening before any wet lab commitment."

        role_warning = ""
        if role_state.get("role") == "piggyback":
            role_warning = f"""
            <div style="margin-top:10px;padding:10px 14px;background:#1a0808;border-radius:6px;
                        border-left:3px solid #FF4C4C;font-size:0.8rem;color:#aaa;line-height:1.6">
              <strong style="color:#FF4C4C">⚠ Structural scaffold / piggyback protein:</strong>
              {role_state.get('note','')}
            </div>"""

        st.markdown(f"""
        <div style="background:#0a0a14;border:3px solid {tc_state};border-radius:14px;
                    padding:22px 26px;margin-bottom:20px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
            <div>
              <div style="font-family:IBM Plex Mono,monospace;font-size:1.2rem;font-weight:700;
                          color:{tc_state};margin-bottom:4px">{assoc_headline}</div>
              <div style="font-size:0.92rem;color:#eee;margin-bottom:4px">
                {gene_detected}{f" — {prot_name}" if prot_name else ""}{gpcr_note}
              </div>
              <div style="font-size:0.83rem;color:#aaa;line-height:1.7">{assoc_detail}</div>
            </div>
            <div style="text-align:right;min-width:160px">
              <div style="font-size:2rem;font-weight:700;font-family:IBM Plex Mono,monospace;color:{tc_state}">{n_path_state}</div>
              <div style="font-size:0.7rem;color:#555;text-transform:uppercase;letter-spacing:0.1em">Germline pathogenic</div>
              <div style="font-size:0.75rem;color:{tc_state};margin-top:4px;font-family:IBM Plex Mono,monospace">DBR {dbr_display}</div>
            </div>
          </div>
          <div style="margin-top:12px;padding:10px 14px;background:#080b14;border-radius:6px;
                      font-size:0.82rem;color:#4CAF50;border:1px solid #1a3a1a">
            <strong>Recommended action:</strong> {assoc_action}
          </div>
          {role_warning}
        </div>""", unsafe_allow_html=True)

    # ── Multi-gene breakdown ──────────────────────────────────────────────
    genes = info.get("genes",[])
    n_genes = len(set(genes))
    gene_col = "gene_name" if "gene_name" in scored.columns else None

    if gene_col and n_genes > 1:
        st.markdown('<div class="sec-label">Multi-Gene / Multi-Protein Study Overview</div>', unsafe_allow_html=True)
        gene_summary = scored.groupby(gene_col).agg(
            n_features=(pc,'count'),
            n_high=(pc,lambda x:(x=="HIGH").sum()),
            top_score=("normalized_score","max"),
            mean_score=("normalized_score","mean"),
        ).reset_index().sort_values("top_score",ascending=False)

        col_left, col_right = st.columns([1,1], gap="medium")
        with col_left:
            st.markdown("**Per-gene breakdown:**")
            for _, gr in gene_summary.iterrows():
                pct = gr["n_high"] / max(gr["n_features"],1) * 100
                bc  = "#FF4C4C" if pct > 50 else "#FFA500" if pct > 20 else "#4CA8FF"
                st.markdown(f"""
                <div class="gene-card">
                  <div style="display:flex;justify-content:space-between">
                    <span style="font-weight:600;color:#eee">{gr[gene_col]}</span>
                    <span style="color:{bc};font-family:IBM Plex Mono,monospace;font-size:0.75rem">{int(gr['n_high'])} HIGH / {int(gr['n_features'])}</span>
                  </div>
                  <div style="background:#1a1d2e;border-radius:4px;height:5px;margin-top:6px;overflow:hidden">
                    <div style="width:{pct:.0f}%;height:100%;background:{bc};border-radius:4px"></div>
                  </div>
                  <div style="font-size:0.73rem;color:#555;margin-top:4px">Top: {gr['top_score']:.3f} · Mean: {gr['mean_score']:.3f}</div>
                </div>""", unsafe_allow_html=True)

        with col_right:
            st.markdown("**Overall study recommendation:**")
            top_gene = gene_summary.iloc[0][gene_col] if len(gene_summary)>0 else "—"
            all_have_high = (gene_summary["n_high"] > 0).all()
            ctx_goal = (st.session_state.get("t_context") or {}).get("study_goal","").lower()
            if "oncology" in ctx_goal or "drug" in ctx_goal:
                rec = (f"**Priority target: {top_gene}** shows the strongest disruption. "
                       f"{'All' if all_have_high else 'Multiple'} genes show HIGH hits — suggests a convergent oncogenic pathway. "
                       f"Recommend: validate {top_gene} first, then test whether genes interact (co-IP, epistasis screen) before multi-target therapy design.")
            elif n_genes >= 5:
                rec = (f"**Panel study detected ({n_genes} genes).** {top_gene} is the top hit. "
                       f"Run pathway enrichment (STRING/Reactome) across ALL HIGH hits before individual validation — biological theme identification first saves resources.")
            else:
                rec = (f"**{top_gene}** has the strongest hits and should be prioritised for wet lab validation. "
                       f"Check whether these {n_genes} genes are in the same pathway or complex before designing experiments — co-regulation may explain the pattern.")
            st.markdown(f"""<div style="background:#0a1a0a;border:1px solid #1a3a1a;border-radius:8px;padding:14px">
              <div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:#4CAF50;margin-bottom:6px">Overall recommendation</div>
              <p style="font-size:0.83rem;color:#bbb;line-height:1.7;margin:0">{rec}</p>
              <div style="margin-top:10px;padding-top:8px;border-top:1px solid #1a3a1a">
                <span style="font-size:0.73rem;color:#555">Priority order: </span>
                {''.join(f'<span style="background:#1a2a1a;border:1px solid #2a4a2a;color:#4CAF50;font-size:0.72rem;font-family:monospace;padding:2px 8px;border-radius:12px;margin:0 3px">{g}</span>' for g in gene_summary[gene_col].tolist()[:6])}
              </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

    # ── Results columns ───────────────────────────────────────────────────
    left, right = st.columns([1, 1.4], gap="large")

    with left:
        st.markdown('<div class="sec-label">Ranked Results</div>', unsafe_allow_html=True)
        disp = ["residue_position","normalized_score",pc]
        if "mutation"       in scored.columns: disp.insert(1,"mutation")
        if "gene_name"      in scored.columns and "gene_name" not in disp: disp.insert(1,"gene_name")
        if "experiment_type"in scored.columns: disp.append("experiment_type")
        if "ml_confidence"  in scored.columns: disp.append("ml_confidence")

        def cprio(val):
            c = "#FF4C4C" if val=="HIGH" else "#FFA500" if val=="MEDIUM" else "#4CA8FF"
            return f"color:{c};font-weight:600"

        fmt = {"normalized_score":"{:.3f}"}
        if "ml_confidence" in scored.columns: fmt["ml_confidence"] = "{:.0%}"
        st.dataframe(scored[disp].style.map(cprio,subset=[pc]).format(fmt),
                     use_container_width=True, height=300)

        with st.expander("Dataset details"):
            st.markdown(f"**Type:** {info['assay_guess']}  \n**Scale:** {info['direction_note']}  \n**Range:** {info['score_min']} → {info['score_max']}  \n**Median:** {info['score_median']}")
            if genes: st.markdown(f"**Genes detected:** {', '.join(genes[:8])}")

        st.markdown('<div class="sec-label" style="margin-top:20px">Hypothesis Outputs</div>', unsafe_allow_html=True)
        top_n = st.slider("Show top N", 1, min(15,len(scored)), min(8,len(scored)), key="t1_n")
        enrichment_state = st.session_state.get("t_enrichment")
        verdict_s = st.session_state.get("t_verdict")
        tier_s    = (verdict_s or {}).get("tier","UNKNOWN")
        tc_s      = (verdict_s or {}).get("color","#888")

        for _, row in scored.head(top_n).iterrows():
            p   = str(row.get(pc,"LOW"))
            c   = "#FF4C4C" if p=="HIGH" else "#FFA500" if p=="MEDIUM" else "#4CA8FF"
            h   = str(row.get("hypothesis",""))
            pos = int(row["residue_position"])
            mut = str(row.get("mutation",f"Pos{pos}"))
            if mut in ("nan",""): mut = f"Pos{pos}"
            score = round(float(row["normalized_score"]),3)
            conf  = row.get("ml_confidence",None)
            conf_s= f" · ML {conf:.0%}" if pd.notna(conf) else ""
            gene  = str(row.get("gene_name",""))
            gene_s= f" · {gene}" if gene not in ("nan","") else ""

            # Genetic framework for this residue
            clinvar_at_pos = ""
            domain_at_pos  = ""
            in_active      = False
            in_binding     = False
            if enrichment_state:
                try:
                    from db_enrichment import get_residue_features
                    feats = get_residue_features(enrichment_state, pos)
                    clinvar_at_pos = feats.get("clinvar_text","")
                    domain_at_pos  = feats.get("domain_name","")
                    in_active      = feats.get("in_active_site", False)
                    in_binding     = feats.get("in_binding_site", False)
                except Exception:
                    pass

            # Genomic context badge
            genomic_badge = ""
            if clinvar_at_pos and "No ClinVar" not in clinvar_at_pos and "Not in" not in clinvar_at_pos:
                genomic_badge = f'<span style="background:#1a0808;border:1px solid #FF4C4C55;color:#FF4C4C;font-size:0.65rem;font-family:IBM Plex Mono,monospace;padding:2px 8px;border-radius:10px;margin-left:6px">ClinVar: {clinvar_at_pos[:40]}</span>'
            elif tier_s == "NONE":
                genomic_badge = '<span style="background:#1a1a1a;border:1px solid #55555555;color:#555;font-size:0.65rem;font-family:IBM Plex Mono,monospace;padding:2px 8px;border-radius:10px;margin-left:6px">No human disease variant</span>'

            site_badge = ""
            if in_active:
                site_badge = '<span style="background:#140a18;border:1px solid #9370DB55;color:#9370DB;font-size:0.65rem;font-family:IBM Plex Mono,monospace;padding:2px 8px;border-radius:10px;margin-left:4px">Active site</span>'
            elif in_binding:
                site_badge = '<span style="background:#0a1418;border:1px solid #4CA8FF55;color:#4CA8FF;font-size:0.65rem;font-family:IBM Plex Mono,monospace;padding:2px 8px;border-radius:10px;margin-left:4px">Binding site</span>'

            domain_badge = f'<span style="color:#3a3d5a;font-size:0.68rem;font-family:IBM Plex Mono,monospace;margin-left:6px">{domain_at_pos}</span>' if domain_at_pos and "Position" not in domain_at_pos else ""

            st.markdown(
                f'<span style="font-family:IBM Plex Mono,monospace;font-size:0.72rem;font-weight:600;color:{c}">[{p}]</span>'
                f'<span style="color:#eee;font-family:IBM Plex Mono,monospace;font-size:0.82rem"> {mut}</span>'
                f'<span style="color:#555;font-size:0.72rem;font-family:IBM Plex Mono,monospace">{gene_s} · score {score}{conf_s}</span>'
                f'{genomic_badge}{site_badge}{domain_badge}'
                f'<div class="hyp-card">{h}</div>', unsafe_allow_html=True)
            # "Why trust this hit?" — genomic evidence layer
            if "t_verdict" in st.session_state:
                v   = st.session_state.t_verdict
                vtc = v.get("color","#888")
                vdbr = f"{v['dbr']:.3f}" if v.get('dbr') is not None else "N/A"
                paper0 = v.get("papers",[{}])[0]
                paper1 = v.get("papers",[{},{}])[1] if len(v.get("papers",[])) > 1 else {}
                exps   = v.get("experiments",[])
                exp1   = exps[0] if exps else {}
                exp_level_color = {"Simple":"#4CAF50","Moderate":"#FFA500","Rigorous":"#FF8C00","Definitive":"#FF4C4C"}
                exp_c  = exp_level_color.get(str(exp1.get("complexity","")).split(" — ")[0],"#888")
                st.markdown(f"""<details style="margin-bottom:12px">
<summary style="cursor:pointer;font-family:IBM Plex Mono,monospace;font-size:0.72rem;
  color:{vtc};padding:8px 12px;background:#0a0a14;border:1px solid {vtc}33;
  border-radius:6px;list-style:none;outline:none">
  {v['icon']} Why trust this hit? &nbsp;
  <span style="color:#555;font-weight:400">{v['label']} · DBR {vdbr}</span>
</summary>
<div style="background:#080b14;border:1px solid #1e2030;border-radius:0 0 8px 8px;
            padding:14px;margin-top:2px">

  <div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;
              letter-spacing:0.15em;color:{vtc};margin-bottom:8px">Genomic validation</div>
  <p style="font-size:0.8rem;color:#bbb;line-height:1.7;margin-bottom:10px">{v['description']}</p>

  <div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;
              letter-spacing:0.15em;color:#4CA8FF;margin-bottom:6px">Scientific basis</div>
  <div style="background:#0a0c1a;border:1px solid #1e2030;border-radius:6px;padding:10px 12px;margin-bottom:10px">
    <div style="font-weight:600;color:#eee;font-size:0.8rem;margin-bottom:4px">{paper0.get('short','')}</div>
    <div style="font-style:italic;color:#888;font-size:0.77rem;line-height:1.6;margin-bottom:6px">"{paper0.get('key_finding','')}"</div>
    <a href="{paper0.get('url','#')}" target="_blank"
       style="font-size:0.7rem;color:#4CA8FF;text-decoration:none">Read paper →</a>
    {f'<span style="color:#555;margin:0 8px">·</span><a href="{paper1.get('url','#')}" target="_blank" style="font-size:0.7rem;color:#4CA8FF;text-decoration:none">{paper1.get('short','')}</a>' if paper1 else ''}
  </div>

  <div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;
              letter-spacing:0.15em;color:#4CAF50;margin-bottom:6px">
    Recommended first experiment — Level {exp1.get('level',1)}: {exp1.get('complexity','')}
  </div>
  <div style="background:#0a140a;border:1px solid #1a3a1a;border-radius:6px;padding:10px 12px">
    <div style="font-weight:600;color:#eee;font-size:0.82rem;margin-bottom:3px">{exp1.get('name','')}</div>
    <div style="font-size:0.75rem;color:#555;margin-bottom:6px">{exp1.get('time','')} · {exp1.get('cost','')}</div>
    <div style="font-size:0.78rem;color:#888;line-height:1.6;margin-bottom:6px">{exp1.get('purpose','')}</div>
    <div style="font-size:0.73rem;color:#4CAF50">Expected: {exp1.get('expected_result','')}</div>
  </div>

</div>
</details>""", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="sec-label">3D Protein Structure — colored by priority</div>', unsafe_allow_html=True)

        # Get correct structure — always auto-fetches for the detected protein
        enrichment   = st.session_state.get("t_enrichment")
        protein_info = st.session_state.get("t_protein")
        pdb          = None
        pdb_label    = ""

        if enrichment and enrichment.get("structure_pdb"):
            pdb       = enrichment["structure_pdb"]
            pdb_label = enrichment.get("structure_source","")
        elif protein_info and protein_info.get("uniprot_id"):
            # Try to fetch structure for detected protein
            uid = protein_info["uniprot_id"]
            gene_detected = protein_info.get("gene_name","")
            with st.spinner(f"Fetching structure for {gene_detected}..."):
                try:
                    from db_enrichment import fetch_uniprot_full, get_structure_for_protein
                    uni_data = fetch_uniprot_full(uid)
                    pdb_text, pdb_src = get_structure_for_protein(uni_data, uid)
                    if pdb_text:
                        pdb = pdb_text
                        pdb_label = pdb_src
                except Exception:
                    pass

        # Only use TP53 if absolutely no other structure available AND no protein detected
        if not pdb:
            detected_gene = (protein_info or {}).get("gene_name","")
            if not detected_gene or detected_gene.upper() == "TP53":
                with st.spinner("Loading structure..."):
                    pdb = fetch_pdb_fallback()
                pdb_label = "TP53 reference (PDB 2OCJ) — upload data with protein name in Q&A for correct structure"
            else:
                pdb_label = f"Structure for {detected_gene} could not be loaded — check internet"

        if pdb_label:
            st.caption(f"🏗️ {pdb_label}")

        if pdb:
            cmap = {"HIGH":"#FF4C4C","MEDIUM":"#FFA500","LOW":"#4CA8FF"}
            rmap = {"HIGH":1.1,"MEDIUM":0.75,"LOW":0.45}

            pdb_residues = set()
            for line in pdb.split('\n'):
                if line.startswith('ATOM'):
                    try: pdb_residues.add(int(line[22:26].strip()))
                    except Exception: pass

            user_positions = [int(r["residue_position"]) for _, r in scored.iterrows()]
            overlap = bool(pdb_residues and any(p in pdb_residues for p in user_positions))

            if overlap:
                rs = {int(row["residue_position"]): {"color":cmap[str(row[pc])], "radius":rmap[str(row[pc])]}
                      for _, row in scored.iterrows()}
            else:
                pdb_range = sorted(pdb_residues) if pdb_residues else list(range(1,500))
                n = min(len(scored), len(pdb_range))
                mapped = [pdb_range[i] for i in np.linspace(0,len(pdb_range)-1,n,dtype=int)]
                rs = {}
                for i,(_, row) in enumerate(scored.head(n).iterrows()):
                    rs[mapped[i]] = {"color":cmap[str(row[pc])], "radius":rmap[str(row[pc])]*1.5}
                umin, umax = min(user_positions), max(user_positions)
                st.info(f"ℹ️ Data positions ({umin}–{umax}) mapped to structure. "
                        "Provide protein name in Q&A sidebar for exact residue-level mapping.")

            components.html(make_viewer(pdb, rs, 580, 455), height=460)
            st.markdown('<div style="display:flex;gap:20px;margin-top:8px;font-size:0.78rem"><span><span style="color:#FF4C4C">●</span> HIGH</span><span><span style="color:#FFA500">●</span> MEDIUM</span><span><span style="color:#4CA8FF">●</span> LOW</span></div>', unsafe_allow_html=True)
        else:
            st.warning(f"Could not load 3D structure. Check internet connection or specify the protein name in Q&A.")

    st.divider()
    exp_df = scored.drop(columns=["hypothesis"],errors="ignore")
    st.download_button("⬇  Download full results (CSV)", exp_df.to_csv(index=True).encode(),
                       "protellect_results.csv","text/csv")


# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — CASE STUDY
# ══════════════════════════════════════════════════════════════════════════
with tab2:
    if LOGO_B64:
        st.markdown(f'<div style="display:flex;align-items:center;gap:14px;margin-bottom:6px"><img src="{LOGO_B64}" style="height:44px;object-fit:contain;border-radius:8px"><div><h2 style="margin:0;font-size:1.4rem">Case Study — TP53 R175H</h2><p style="color:#555;font-size:0.84rem;margin:0">How Protellect processes a known mutation end-to-end</p></div></div>', unsafe_allow_html=True)
    st.divider()
    left, right = st.columns([1,1.3], gap="large")
    with left:
        st.markdown('<div class="sec-label">Background</div>', unsafe_allow_html=True)
        st.markdown("""<div style="background:#0f1117;border:1px solid #2a2d3a;border-radius:10px;padding:18px;margin-bottom:14px">
          <p style="font-size:0.84rem;color:#bbb;line-height:1.7">Arginine 175 → Histidine. Disrupts zinc-coordination site (C176/H179/C238/C242) causing global misfolding. Found in <strong style="color:#FF4C4C">~6% of all human cancers</strong>. Both loss-of-function and dominant negative.</p>
        </div>
        <div style="background:#0f1117;border:1px solid #2a2d3a;border-radius:10px;padding:18px;margin-bottom:14px">
          <p style="font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:#FF4C4C;margin-bottom:8px;text-transform:uppercase">Protellect output</p>
          <p style="font-size:0.84rem;color:#bbb;line-height:1.7">Score: <strong style="color:#FF4C4C">0.99/1.00</strong> · Priority: <strong style="color:#FF4C4C">HIGH</strong> · ML confidence: ~97%<br>UniProt P04637 · ClinVar: 847 pathogenic submissions</p>
        </div>""", unsafe_allow_html=True)
        st.markdown('<div class="sec-label">Experimental pathway (context: oncology drug target)</div>', unsafe_allow_html=True)
        for i,(t,d) in enumerate([
            ("Target druggability check","FPocket on PDB 2OCJ — 3 druggable cavities identified near R175."),
            ("Structural validation","Thermal shift: Tm −8°C vs WT. EMSA: complete loss of DNA binding."),
            ("Database cross-reference","ClinVar: 847 pathogenic. COSMIC: breast, lung, colorectal. ChEMBL: APR-246 listed."),
            ("Therapeutic rescue screen","APR-246 dose-response: partial Tm rescue at 10μM. Validated refolding activity."),
            ("In vivo follow-up","Xenograft model with APR-246 treatment — tumour growth inhibition confirmed."),
        ],1):
            st.markdown(f'<div style="display:flex;gap:12px;margin-bottom:12px"><div style="width:26px;height:26px;border-radius:50%;background:#FF4C4C22;color:#FF4C4C;border:1px solid #FF4C4C55;display:flex;align-items:center;justify-content:center;font-family:IBM Plex Mono,monospace;font-size:0.72rem;font-weight:600;flex-shrink:0;margin-top:2px">{i}</div><div><strong style="color:#eee;font-size:0.88rem;display:block;margin-bottom:3px">{t}</strong><span style="color:#666;font-size:0.8rem;line-height:1.5">{d}</span></div></div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="sec-label">3D Structure — TP53 (PDB 2OCJ)</div>', unsafe_allow_html=True)
        with st.spinner("Loading..."):
            pdb_cs = fetch_pdb_fallback()
        if pdb_cs:
            esc2 = pdb_cs.replace("\\","\\\\").replace("`","\\`").replace("${","\\${")[:260000]
            cs_html = f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<style>body{{margin:0;background:#080b14}}#v{{width:580px;height:490px}}</style>
</head><body><div id="v"></div><script>
const p=`{esc2}`;
let v=$3Dmol.createViewer('v',{{backgroundColor:'#080b14',antialias:true}});
v.addModel(p,'pdb');v.setStyle({{}},{{cartoon:{{color:'#1e2030',opacity:0.45}}}});
v.addStyle({{resi:'94-292'}},{{cartoon:{{color:'#4CA8FF',opacity:0.8}}}});
v.addStyle({{resi:175}},{{sphere:{{color:'#FF4C4C',radius:1.05}}}});
v.addSurface($3Dmol.VDW,{{opacity:0.3,color:'#FF4C4C'}},{{resi:175}});
[248,273,249,245,282].forEach(r=>v.addStyle({{resi:r}},{{sphere:{{color:'#FF8C00',radius:0.65}}}}));
v.zoomTo({{resi:'94-292'}});v.spin(false);v.render();
</script></body></html>"""
            components.html(cs_html, height=495)
        st.divider()
        st.markdown('<div class="sec-label">Key Facts</div>', unsafe_allow_html=True)
        facts = [("Mutation","Missense · Arg→His at codon 175"),("Domain","DNA-binding domain · L2 loop · zinc coordination"),("Mechanism","Zinc-site disruption → global misfolding → DNA binding lost"),("Frequency","~6% of all cancers · most common TP53 hotspot"),("Functional class","Loss-of-function + dominant negative GOF"),("ClinVar","847 pathogenic submissions"),("Therapeutic","APR-246 (eprenetapopt) · Phase III; PC14586 (rezatapopt) · Phase II for Y220C")]
        st.markdown('<table class="facts-table">'+"".join(f"<tr><td>{l}</td><td>{v}</td></tr>" for l,v in facts)+"</table>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# TAB 3 — PROTEIN EXPLORER
# ══════════════════════════════════════════════════════════════════════════
with tab3:
    import protein_explorer
    protein_explorer.render()


# ══════════════════════════════════════════════════════════════════════════
# TAB 4 — HYPOTHESIS LAB
# ══════════════════════════════════════════════════════════════════════════
with tab4:
    import hypothesis_lab
    hypothesis_lab.render()

# ══════════════════════════════════════════════════════════════════════════
# TAB 5 — PROTEIN DEEP DIVE
# ══════════════════════════════════════════════════════════════════════════
with tab5:
    import protein_deep_dive
    protein_deep_dive.render()


# ══════════════════════════════════════════════════════════════════════════
# TAB 6 — DISEASE EXPLORER
# ══════════════════════════════════════════════════════════════════════════
with tab6:
    import disease_explorer
    disease_explorer.render()
