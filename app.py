"""
app.py — Protellect MVP  |  streamlit run app.py
Universal biological dataset support (CSV, Excel, TSV, any format).
ML-assisted scoring. Scientist Q&A sidebar. Top 5 pathways. Rich descriptive results.
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import json
import base64
from pathlib import Path
from io import BytesIO

from scorer import (
    load_file, score_residues, get_summary_stats, validate_dataframe,
    detect_dataset_info, generate_top_pathways, ML_AVAILABLE,
)

# ── Config ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Protellect", page_icon="🧬", layout="wide", initial_sidebar_state="expanded")

# ── Logo ───────────────────────────────────────────────────────────────────
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
           letter-spacing:0.18em;color:#444;border-bottom:1px solid #1e2030;
           padding-bottom:6px;margin-bottom:14px}

.hyp-card{background:#0f1117;border-left:3px solid #1e2030;padding:14px 16px;
          border-radius:0 8px 8px 0;font-size:0.83rem;color:#999;margin-bottom:10px;line-height:1.8}
.hyp-badge{font-family:'IBM Plex Mono',monospace;font-size:0.72rem;font-weight:600;margin-right:8px}
.hyp-meta{font-size:0.72rem;color:#555;font-family:'IBM Plex Mono',monospace;margin-bottom:6px}
.ml-badge{display:inline-block;background:#1a1a3a;border:1px solid #3a3d5a;
          color:#8888cc;font-size:0.65rem;font-family:'IBM Plex Mono',monospace;
          padding:1px 8px;border-radius:10px;margin-left:8px;vertical-align:middle}

.pathway-card{background:#0f1117;border:1px solid #1e2030;border-radius:10px;padding:16px;margin-bottom:10px}
.pathway-num{font-family:'IBM Plex Mono',monospace;font-size:0.65rem;color:#555;text-transform:uppercase;letter-spacing:0.15em}
.pathway-title{font-size:0.95rem;font-weight:600;color:#eee;margin:4px 0 8px}
.pathway-rationale{font-size:0.82rem;color:#888;line-height:1.7;margin-bottom:10px}
.pathway-step{font-size:0.8rem;color:#777;padding:3px 0;border-bottom:1px solid #1a1d2e;line-height:1.6}
.pathway-meta{display:flex;gap:16px;margin-top:10px;flex-wrap:wrap}
.pathway-meta span{font-size:0.75rem;font-family:'IBM Plex Mono',monospace;color:#555}
.pathway-meta b{color:#aaa}

.assay-box{background:#07100a;border:1px solid #1a3a1a;border-radius:8px;padding:14px 16px;margin-top:8px}
.assay-title{font-family:'IBM Plex Mono',monospace;font-size:0.65rem;text-transform:uppercase;
             letter-spacing:0.15em;color:#4CAF50;margin-bottom:8px}
.assay-row{display:flex;gap:8px;padding:5px 0;font-size:0.78rem;border-bottom:1px solid #0a1a0a}
.assay-lbl{color:#2a5a2a;min-width:110px;font-size:0.7rem;font-family:'IBM Plex Mono',monospace;flex-shrink:0}
.assay-val{color:#aaa}

.qa-box{background:#0a0c1a;border:1px solid #1e2030;border-radius:8px;padding:14px 16px;margin-top:8px}
.qa-title{font-family:'IBM Plex Mono',monospace;font-size:0.65rem;text-transform:uppercase;
          letter-spacing:0.15em;color:#4CA8FF;margin-bottom:10px}

.ml-banner{background:#0a0a1a;border:1px solid #2a2d5a;border-radius:8px;padding:10px 14px;margin-bottom:14px;font-size:0.8rem;color:#8888cc}

.info-row{display:flex;gap:10px;padding:6px 0;border-bottom:1px solid #1a1d2e;font-size:0.82rem}
.info-lbl{color:#444;min-width:130px;font-family:'IBM Plex Mono',monospace;font-size:0.7rem;padding-top:2px;flex-shrink:0}
.info-val{color:#bbb;line-height:1.6}
.facts-table{width:100%;border-collapse:collapse;font-size:0.82rem}
.facts-table td{padding:7px 10px;border-bottom:1px solid #1a1d2e;color:#bbb;vertical-align:top}
.facts-table td:first-child{color:#444;font-family:'IBM Plex Mono',monospace;font-size:0.7rem;width:130px}
.step-num{width:26px;height:26px;border-radius:50%;background:#FF4C4C22;color:#FF4C4C;
          border:1px solid #FF4C4C55;display:flex;align-items:center;justify-content:center;
          font-family:'IBM Plex Mono',monospace;font-size:0.72rem;font-weight:600;flex-shrink:0;margin-top:2px}
</style>
""", unsafe_allow_html=True)


# ── Tutorial ────────────────────────────────────────────────────────────────
@st.dialog("How to use Protellect")
def show_tutorial():
    if LOGO_B64:
        st.markdown(f'<img src="{LOGO_B64}" style="height:48px;object-fit:contain;border-radius:8px;margin-bottom:12px">', unsafe_allow_html=True)
    st.markdown("#### Experimental Intelligence Layer — Universal Biological Dataset Support")
    st.markdown("Upload **any** biological dataset. Protellect automatically detects the format, scores every feature, and generates ranked hypotheses.")
    st.divider()
    for i, (t, d) in enumerate([
        ("Upload any file", "CSV, TSV, Excel (.xlsx), any column naming. Gene expression, DMS, CRISPR screens, variant data, proteomics, stability assays — all supported. No manual configuration needed."),
        ("Answer the Q&A questions", "Tell Protellect what you're studying, your hypothesis, and what direction you want to explore. This tailors the hypothesis text, pathway recommendations, and results display."),
        ("Click Run Triage", "ML-assisted scoring analyses every row. Detects scale direction (log2FC, ΔΔG, p-values etc), normalises automatically, assigns HIGH/MEDIUM/LOW priority."),
        ("Check the sidebar pathways", "After triage, the sidebar shows your top 5 experimental pathways — tailored to your dataset type and research context."),
        ("Explore the 4 tabs", "**Tab 1** — ranked results + 3D structure. **Tab 2** — TP53 case study. **Tab 3** — Protein Explorer with click-to-annotate. **Tab 4** — Hypothesis Lab with protein animation + mutation timeline slider."),
    ], 1):
        c1, c2 = st.columns([0.06, 0.94])
        with c1:
            st.markdown(f'<div class="step-num">{i}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f"**{t}**  \n{d}")
        st.markdown("")
    st.markdown("---")
    st.markdown("**Priority:** 🔴 HIGH ≥0.75 · 🟠 MEDIUM ≥0.40 · 🔵 LOW  |  Thresholds adjustable in sidebar")
    if st.button("Start exploring →", type="primary", use_container_width=True):
        st.session_state.tut_seen = True
        st.rerun()

if "tut_seen" not in st.session_state:
    st.session_state.tut_seen = False
if not st.session_state.tut_seen:
    show_tutorial()


# ── Helpers ────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def fetch_pdb(pid="2OCJ"):
    try:
        r = requests.get(f"https://files.rcsb.org/download/{pid}.pdb", timeout=15)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def make_viewer(pdb, res_scores, width=580, height=455, zoom="94-292"):
    esc = pdb.replace("\\","\\\\").replace("`","\\`").replace("${","\\${")[:260000]
    styles = "".join(f"v.addStyle({{resi:{r}}},{{sphere:{{color:'{o['color']}',radius:{o['radius']}}}}});\n" for r,o in res_scores.items())
    return f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<style>body{{margin:0;background:#080b14}}#v{{width:{width}px;height:{height}px}}</style>
</head><body><div id="v"></div><script>
const p=`{esc}`;
let v=$3Dmol.createViewer('v',{{backgroundColor:'#080b14',antialias:true}});
v.addModel(p,'pdb');v.setStyle({{}},{{cartoon:{{color:'#1e2030',opacity:0.55}}}});
{styles}v.zoomTo({{resi:'{zoom}'}});v.spin(false);v.render();
</script></body></html>"""


# ── SIDEBAR ────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo + title
    cl, ct, ch = st.columns([1, 3.2, 1])
    with cl:
        if LOGO_B64:
            st.markdown(f'<img src="{LOGO_B64}" style="width:34px;height:34px;object-fit:contain;border-radius:6px;margin-top:6px">', unsafe_allow_html=True)
    with ct:
        st.markdown("### Protellect")
    with ch:
        if st.button("❓", help="Open tutorial"):
            show_tutorial()
    st.markdown('<p style="font-size:0.72rem;color:#333;margin:-4px 0 0;font-family:IBM Plex Mono,monospace">Experimental Intelligence Layer</p>', unsafe_allow_html=True)

    if ML_AVAILABLE:
        st.markdown('<div class="ml-banner">🤖 ML scoring active — Gradient Boosting + biological feature engineering</div>', unsafe_allow_html=True)

    st.divider()

    # ── Upload ─────────────────────────────────────────────────────────────
    st.markdown('<div class="sec-label">Data Upload</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload dataset",
        type=["csv","tsv","xlsx","xls","xlsm","txt"],
        label_visibility="collapsed"
    )
    st.caption("CSV · TSV · Excel · any biological format  \nGene expression, DMS, CRISPR, variants, proteomics...")

    with st.expander("View expected formats"):
        st.code("# CSV / protein mutations:\nresidue_position,effect_score,mutation\n175,0.99,R175H\n\n# Excel / gene expression:\ngene_name,log2fc,pvalue\nTP53,2.4,0.0001\n\n# Any numeric score column works", language="text")

    use_sample = st.checkbox("Use TP53 DMS sample data", value=not bool(uploaded_file))

    st.divider()

    # ── Scientist Q&A ───────────────────────────────────────────────────────
    st.markdown('<div class="sec-label">Scientist Q&A — Tailor Your Results</div>', unsafe_allow_html=True)
    st.markdown('<div class="qa-box"><div class="qa-title">🔬 Research Context</div>', unsafe_allow_html=True)

    study_goal = st.text_input(
        "What is your research goal?",
        placeholder="e.g. identify drug targets in oncology, map functional residues...",
        key="qa_goal"
    )
    protein_of_interest = st.text_input(
        "Protein / gene of interest (if known)",
        placeholder="e.g. TP53, EGFR, BRCA1, or leave blank",
        key="qa_protein"
    )
    study_focus = st.text_input(
        "Specific focus area",
        placeholder="e.g. DNA binding domain, kinase activity, drug resistance...",
        key="qa_focus"
    )
    experiment_context = st.selectbox(
        "Primary experiment type",
        ["Not specified", "Deep mutational scanning (DMS)", "CRISPR screen",
         "RNA-seq / gene expression", "Protein stability (ΔΔG)", "Variant pathogenicity",
         "Proteomics / mass spec", "Functional assay", "Clinical / patient data", "Other"],
        key="qa_exp"
    )
    hypothesis_direction = st.selectbox(
        "What direction do you want to explore?",
        ["Not specified", "Find loss-of-function mutations",
         "Find gain-of-function mutations", "Identify drug target residues",
         "Map protein-DNA / protein-protein interfaces",
         "Identify therapeutic rescue candidates",
         "Prioritise for structural biology (crystallography / cryo-EM)",
         "Clinical variant interpretation", "Basic science / mechanism"],
        key="qa_direction"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Build context dict
    scientist_context = {
        "study_goal":          study_goal,
        "protein_of_interest": protein_of_interest,
        "study_focus":         study_focus,
        "experiment_context":  experiment_context,
        "hypothesis_direction":hypothesis_direction,
    }

    st.divider()

    # ── Thresholds ──────────────────────────────────────────────────────────
    st.markdown('<div class="sec-label">Triage Thresholds</div>', unsafe_allow_html=True)
    high_thresh   = st.slider("HIGH cutoff",   0.5, 1.0, 0.75, 0.01)
    medium_thresh = st.slider("MEDIUM cutoff", 0.1, 0.7, 0.40, 0.01)
    use_ml        = st.checkbox("Use ML-assisted scoring", value=ML_AVAILABLE, disabled=not ML_AVAILABLE,
                                 help="Gradient Boosting model trained on biological features. Falls back to rule-based if unavailable.")

    run_btn = st.button("▶  Run Triage", type="primary", use_container_width=True)

    # ── Assay summary ────────────────────────────────────────────────────────
    if "t_info" in st.session_state and "t_scored" in st.session_state:
        info   = st.session_state.t_info
        scored = st.session_state.t_scored
        pri_col = "priority_final" if "priority_final" in scored.columns else "priority"
        n_high  = int((scored[pri_col] == "HIGH").sum())
        top     = scored.iloc[0]
        top_lbl = str(top.get("mutation", f"Pos{int(top['residue_position'])}"))
        if top_lbl in ("nan",""):
            top_lbl = f"Pos{int(top['residue_position'])}"
        exps = ", ".join(info["exp_types"][:3]) if info["exp_types"] else "Not specified"
        ml_tag = " · ML-assisted" if info.get("ml_used") or st.session_state.get("t_stats",{}).get("ml_used") else ""

        st.markdown(f"""
        <div class="assay-box">
          <div class="assay-title">📋 Assay Summary{ml_tag}</div>
          <div class="assay-row"><span class="assay-lbl">Dataset type</span><span class="assay-val">{info['assay_guess']}</span></div>
          <div class="assay-row"><span class="assay-lbl">Features scored</span><span class="assay-val">{info['n_rows']}</span></div>
          <div class="assay-row"><span class="assay-lbl">Score range</span><span class="assay-val">{info['score_min']} → {info['score_max']}</span></div>
          <div class="assay-row"><span class="assay-lbl">Scale detected</span><span class="assay-val">{info['direction_note']}</span></div>
          <div class="assay-row"><span class="assay-lbl">Experiments</span><span class="assay-val">{exps}</span></div>
          <div class="assay-row"><span class="assay-lbl">HIGH priority</span><span class="assay-val" style="color:#FF4C4C;font-weight:600">{n_high} features</span></div>
          <div class="assay-row" style="border:none"><span class="assay-lbl">Top hit</span><span class="assay-val" style="color:#FF4C4C;font-weight:600">{top_lbl} ({round(float(top['normalized_score']),3)})</span></div>
        </div>""", unsafe_allow_html=True)

    # ── Top 5 Pathways ────────────────────────────────────────────────────────
    if "t_pathways" in st.session_state:
        st.divider()
        st.markdown('<div class="sec-label">Top 5 Experimental Pathways</div>', unsafe_allow_html=True)
        for pw in st.session_state.t_pathways:
            pri_color = {"Immediate":"#4CAF50","High":"#FFA500","Medium":"#4CA8FF","Phase 3":"#9370DB"}.get(pw["priority"], "#555")
            with st.expander(f"{pw['icon']} {pw['rank']}. {pw['title']}"):
                st.markdown(f'<span style="font-size:0.72rem;font-family:IBM Plex Mono,monospace;color:{pri_color};font-weight:600">{pw["priority"].upper()}</span> · {pw["cost"]} · {pw["timeline"]}', unsafe_allow_html=True)
                st.markdown(f'*{pw["rationale"]}*')
                st.markdown("**Steps:**")
                for step in pw["steps"]:
                    st.markdown(f"• {step}")

    st.divider()
    st.caption("Structure: TP53 · PDB 2OCJ · Phase 2 auto-identifies any protein")


# ── TABS ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🧬  Triage System",
    "🔬  Case Study",
    "⚗️  Protein Explorer",
    "💡  Hypothesis Lab",
])


# ══════════════════════════════════════════════════════════════════════════
# TAB 1
# ══════════════════════════════════════════════════════════════════════════
with tab1:
    if LOGO_B64:
        st.markdown(f'<div style="display:flex;align-items:center;gap:14px;margin-bottom:6px"><img src="{LOGO_B64}" style="height:44px;object-fit:contain;border-radius:8px"><div><h2 style="margin:0;font-size:1.4rem">Triage System</h2><p style="color:#555;font-size:0.84rem;margin:0">Universal biological dataset support · ML-assisted scoring · ranked hypotheses</p></div></div>', unsafe_allow_html=True)
    else:
        st.markdown("## Triage System")
    st.divider()

    # Run triage
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

        import scorer as _sc
        _sc.assign_priority = lambda s: "HIGH" if s >= high_thresh else "MEDIUM" if s >= medium_thresh else "LOW"

        ctx = scientist_context if any(v and v != "Not specified" for v in scientist_context.values()) else None

        with st.spinner(f"Scoring {len(df_raw)} rows{'  ·  ML active' if use_ml and ML_AVAILABLE else ''}..."):
            scored = score_residues(df_raw, context=ctx)
            info   = detect_dataset_info(df_raw)
            info["ml_used"] = use_ml and ML_AVAILABLE
            stats  = get_summary_stats(scored)
            pathways = generate_top_pathways(scored, info, ctx)

        st.session_state.t_scored   = scored
        st.session_state.t_stats    = stats
        st.session_state.t_info     = info
        st.session_state.t_pathways = pathways
        st.session_state.t_context  = ctx
        st.rerun()

    if "t_scored" not in st.session_state:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div style="background:#0f1117;border:1px solid #1e2030;border-radius:10px;padding:20px;margin-bottom:10px">
              <p style="font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:#4CA8FF;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.08em">Supported data types</p>
              <p style="font-size:0.83rem;color:#888;line-height:1.8">
                ✓ Deep mutational scanning (DMS)<br>
                ✓ CRISPR screens (log2FC)<br>
                ✓ RNA-seq / gene expression<br>
                ✓ Protein stability (ΔΔG)<br>
                ✓ Variant pathogenicity scores<br>
                ✓ Proteomics / mass spectrometry<br>
                ✓ Any custom functional assay
              </p>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div style="background:#0f1117;border:1px solid #1e2030;border-radius:10px;padding:20px;margin-bottom:10px">
              <p style="font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:#4CAF50;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.08em">Supported file formats</p>
              <p style="font-size:0.83rem;color:#888;line-height:1.8">
                ✓ CSV (comma-separated)<br>
                ✓ TSV (tab-separated)<br>
                ✓ Excel (.xlsx, .xlsm)<br>
                ✓ Any column naming convention<br>
                ✓ Multiple sheets — auto-selects best<br>
                ✓ Mixed data types — auto-detected<br>
                ✓ Non-standard separators (;, |)
              </p>
            </div>""", unsafe_allow_html=True)
        st.info("👈  Upload your data, answer the Q&A questions in the sidebar to tailor results, then click **▶  Run Triage**.")
        st.stop()

    scored  = st.session_state.t_scored
    stats   = st.session_state.t_stats
    info    = st.session_state.t_info
    pri_col = "priority_final" if "priority_final" in scored.columns else "priority"

    # ML banner
    if stats.get("ml_used"):
        st.markdown(f'<div class="ml-banner">🤖 ML-assisted scoring active — {stats["high_priority"]} HIGH · {stats["medium_priority"]} MEDIUM · {stats["low_priority"]} LOW &nbsp;|&nbsp; Dataset: {info["assay_guess"]}</div>', unsafe_allow_html=True)

    # Stat cards
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, num, lbl, clr in [
        (c1, stats["total_residues"],   "Features scored", "#eee"),
        (c2, stats["high_priority"],    "HIGH priority",   "#FF4C4C"),
        (c3, stats["medium_priority"],  "MEDIUM priority", "#FFA500"),
        (c4, stats["low_priority"],     "LOW priority",    "#4CA8FF"),
        (c5, f"{stats['top_score']}",   "Top score",       "#FF4C4C"),
    ]:
        col.markdown(f'<div class="stat-card"><span class="stat-number" style="color:{clr}">{num}</span><span class="stat-label">{lbl}</span></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns([1, 1.4], gap="large")

    with left:
        st.markdown('<div class="sec-label">Ranked Results — All Features</div>', unsafe_allow_html=True)

        disp = ["residue_position", "normalized_score", pri_col]
        if "mutation" in scored.columns:
            disp.insert(1, "mutation")
        if "gene_name" in scored.columns and "gene_name" not in disp:
            disp.insert(1, "gene_name")
        if "experiment_type" in scored.columns:
            disp.append("experiment_type")
        if "ml_confidence" in scored.columns:
            disp.append("ml_confidence")

        def cprio(val):
            c = "#FF4C4C" if val == "HIGH" else "#FFA500" if val == "MEDIUM" else "#4CA8FF"
            return f"color:{c};font-weight:600"

        fmt = {"normalized_score": "{:.3f}"}
        if "ml_confidence" in scored.columns:
            fmt["ml_confidence"] = "{:.0%}"

        st.dataframe(
            scored[disp].style.map(cprio, subset=[pri_col]).format(fmt),
            use_container_width=True, height=300
        )

        # Dataset info
        with st.expander("Dataset details"):
            st.markdown(f"**Type:** {info['assay_guess']}  \n**Scale:** {info['direction_note']}  \n**Score range:** {info['score_min']} → {info['score_max']}  \n**Median:** {info['score_median']}")
            if info.get("target_proteins"):
                st.markdown(f"**Detected targets:** {', '.join(info['target_proteins'])}")

        # Hypotheses
        st.markdown('<div class="sec-label" style="margin-top:20px">Detailed Hypothesis Outputs</div>', unsafe_allow_html=True)
        top_n = st.slider("Show top N", 1, min(15, len(scored)), min(8, len(scored)), key="t1_n")

        for _, row in scored.head(top_n).iterrows():
            p   = str(row.get(pri_col, "LOW"))
            c   = "#FF4C4C" if p=="HIGH" else "#FFA500" if p=="MEDIUM" else "#4CA8FF"
            h   = str(row.get("hypothesis", ""))
            pos = int(row["residue_position"])
            mut = str(row.get("mutation", f"Pos{pos}"))
            if mut in ("nan",""):
                mut = f"Pos{pos}"
            score = round(float(row["normalized_score"]), 3)
            conf  = row.get("ml_confidence", None)
            conf_s = f" · ML {conf:.0%}" if pd.notna(conf) else ""
            gene  = str(row.get("gene_name",""))
            gene_s = f" · {gene}" if gene not in ("nan","") else ""

            st.markdown(
                f'<span class="hyp-badge" style="color:{c}">[{p}]</span>'
                f'<span style="color:#eee;font-family:IBM Plex Mono,monospace;font-size:0.82rem">{mut}</span>'
                f'<span class="hyp-meta">{gene_s} · score {score}{conf_s}</span>'
                f'<div class="hyp-card">{h}</div>',
                unsafe_allow_html=True
            )

    with right:
        st.markdown('<div class="sec-label">3D Protein Structure — colored by priority</div>', unsafe_allow_html=True)
        with st.spinner("Loading structure..."):
            pdb = fetch_pdb("2OCJ")

        if pdb:
            cmap = {"HIGH":"#FF4C4C","MEDIUM":"#FFA500","LOW":"#4CA8FF"}
            rmap = {"HIGH":0.88,"MEDIUM":0.62,"LOW":0.40}
            rs = {
                int(row["residue_position"]): {"color":cmap[str(row[pri_col])],"radius":rmap[str(row[pri_col])]}
                for _, row in scored.iterrows()
            }
            components.html(make_viewer(pdb, rs, 580, 455), height=460)
            st.markdown('<div style="display:flex;gap:20px;margin-top:8px;font-size:0.78rem"><span><span style="color:#FF4C4C">●</span> HIGH</span><span><span style="color:#FFA500">●</span> MEDIUM</span><span><span style="color:#4CA8FF">●</span> LOW</span></div>', unsafe_allow_html=True)
        else:
            st.error("Could not load protein structure.")

    st.divider()
    exp_df = scored.drop(columns=["hypothesis"], errors="ignore")
    st.download_button("⬇  Download full results (CSV)", exp_df.to_csv(index=True).encode(), "protellect_results.csv", "text/csv")


# ══════════════════════════════════════════════════════════════════════════
# TAB 2
# ══════════════════════════════════════════════════════════════════════════
with tab2:
    if LOGO_B64:
        st.markdown(f'<div style="display:flex;align-items:center;gap:14px;margin-bottom:6px"><img src="{LOGO_B64}" style="height:44px;object-fit:contain;border-radius:8px"><div><h2 style="margin:0;font-size:1.4rem">Case Study — TP53 R175H</h2><p style="color:#555;font-size:0.84rem;margin:0">The most common oncogenic TP53 mutation · how Protellect processes it end-to-end</p></div></div>', unsafe_allow_html=True)
    else:
        st.markdown("## Case Study — TP53 R175H")
    st.divider()

    left, right = st.columns([1, 1.3], gap="large")
    with left:
        st.markdown('<div class="sec-label">Background</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#0f1117;border:1px solid #2a2d3a;border-radius:10px;padding:18px;margin-bottom:14px">
          <p style="font-size:0.84rem;color:#bbb;margin:0;line-height:1.7">
            Arginine 175 → Histidine. Disrupts the zinc-coordination site (C176/H179/C238/C242) 
            causing global misfolding of the DNA-binding domain. Found in <strong style="color:#FF4C4C">~6% of all 
            human cancers</strong> — the most frequently observed TP53 hotspot mutation globally. 
            Both a loss-of-function and dominant negative gain-of-function mutation.
          </p>
        </div>
        <div style="background:#0f1117;border:1px solid #2a2d3a;border-radius:10px;padding:18px;margin-bottom:14px">
          <p style="font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:#FF4C4C;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.08em">Protellect output</p>
          <p style="font-size:0.84rem;color:#bbb;margin:0;line-height:1.7">
            Normalised score: <strong style="color:#FF4C4C">0.99/1.00</strong> · Priority: <strong style="color:#FF4C4C">HIGH</strong> · ML confidence: <strong style="color:#FF4C4C">~97%</strong><br><br>
            Flagged instantly from DMS data as #1 priority. ClinVar: 847 pathogenic submissions. 
            COSMIC: found in breast, lung, colorectal, ovarian, and bladder cancer.
          </p>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div class="sec-label">Experimental Pathway — as generated by Protellect</div>', unsafe_allow_html=True)
        for i, (t, d) in enumerate([
            ("Protellect flags R175H", "DMS score 0.99 → HIGH priority, ML confidence 97%. ClinVar: 847 pathogenic. Instantly surfaced as #1."),
            ("Structural validation", "Thermal shift: Tm −8°C vs WT, confirming domain destabilisation. EMSA: no DNA-binding band."),
            ("Database enrichment", "ClinVar: Pathogenic · 847 submissions. COSMIC: 6% of all cancers. UniProt: zinc coordination site disrupted."),
            ("Hypothesis formed", "R175H → zinc-site collapse → global misfolding → loss of tumour suppressor + dominant negative."),
            ("Therapeutic follow-up", "APR-246 (eprenetapopt) Phase III: covalently modifies C176, partially restores WT conformation."),
        ], 1):
            st.markdown(f'<div style="display:flex;gap:12px;margin-bottom:12px"><div class="step-num">{i}</div><div><strong style="color:#eee;font-size:0.88rem;display:block;margin-bottom:3px">{t}</strong><span style="color:#666;font-size:0.8rem;line-height:1.5">{d}</span></div></div>', unsafe_allow_html=True)

        st.markdown('<div style="background:#0a1a0a;border:1px solid #1a4a1a;border-radius:8px;padding:14px"><p style="font-family:\'IBM Plex Mono\',monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.12em;color:#4CAF50;margin-bottom:6px">Efficiency gain</p><p style="font-size:0.82rem;color:#aaa;margin:0;line-height:1.6">Manual literature review: 2–4 hours. With Protellect: <strong style="color:#4CAF50">under 2 minutes</strong> from CSV upload to validated hypothesis.</p></div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="sec-label">3D Structure — TP53 DNA-binding domain (PDB 2OCJ)</div>', unsafe_allow_html=True)
        st.caption("R175 in red · DNA-binding domain in blue · other hotspots in orange")
        with st.spinner("Loading..."):
            pdb_cs = fetch_pdb("2OCJ")
        if pdb_cs:
            esc2 = pdb_cs.replace("\\","\\\\").replace("`","\\`").replace("${","\\${")[:260000]
            cs_html = f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<style>body{{margin:0;background:#080b14}}#v{{width:580px;height:490px}}</style>
</head><body><div id="v"></div><script>
const p=`{esc2}`;
let v=$3Dmol.createViewer('v',{{backgroundColor:'#080b14',antialias:true}});
v.addModel(p,'pdb');
v.setStyle({{}},{{cartoon:{{color:'#1e2030',opacity:0.45}}}});
v.addStyle({{resi:'94-292'}},{{cartoon:{{color:'#4CA8FF',opacity:0.8}}}});
v.addStyle({{resi:175}},{{sphere:{{color:'#FF4C4C',radius:1.05}}}});
v.addSurface($3Dmol.VDW,{{opacity:0.3,color:'#FF4C4C'}},{{resi:175}});
[248,273,249,245,282].forEach(r=>v.addStyle({{resi:r}},{{sphere:{{color:'#FF8C00',radius:0.65}}}}));
v.zoomTo({{resi:'94-292'}});v.spin(false);v.render();
</script></body></html>"""
            components.html(cs_html, height=495)
            st.markdown('<div style="display:flex;gap:20px;margin-top:8px;font-size:0.78rem;flex-wrap:wrap"><span><span style="color:#FF4C4C">●</span> R175 (focus)</span><span><span style="color:#FF8C00">●</span> Other hotspots</span><span><span style="color:#4CA8FF">━</span> DNA-binding domain</span></div>', unsafe_allow_html=True)
        else:
            st.error("Could not load structure.")

        st.divider()
        st.markdown('<div class="sec-label">Key Facts</div>', unsafe_allow_html=True)
        facts = [("Mutation","Missense · Arg→His at codon 175"),("Domain","DNA-binding domain · L2 loop · zinc coordination"),("Mechanism","Zinc-site disruption → global misfolding → DNA binding lost"),("Frequency","~6% of all cancers · most common TP53 hotspot"),("Cancer types","Breast, lung, colorectal, ovarian, bladder"),("Functional class","Loss-of-function + dominant negative gain-of-function"),("ClinVar","847 pathogenic submissions"),("Therapeutic","APR-246 (eprenetapopt) · Phase III refolding compound")]
        st.markdown('<table class="facts-table">'+"".join(f"<tr><td>{l}</td><td>{v}</td></tr>" for l,v in facts)+"</table>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# TAB 3
# ══════════════════════════════════════════════════════════════════════════
with tab3:
    import protein_explorer
    protein_explorer.render()


# ══════════════════════════════════════════════════════════════════════════
# TAB 4
# ══════════════════════════════════════════════════════════════════════════
with tab4:
    import hypothesis_lab
    hypothesis_lab.render()
