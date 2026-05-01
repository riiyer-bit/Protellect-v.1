"""
app.py — Protellect MVP  —  streamlit run app.py
Professional layout. No py3Dmol/stmol. All 3D via 3Dmol.js HTML components.
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import json
import base64
from pathlib import Path

from scorer import (
    score_residues, get_summary_stats, validate_dataframe,
    detect_dataset_info,
)

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Protellect",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Logo ───────────────────────────────────────────────────────────────────
_lp = Path("/mnt/user-data/uploads/1777622887238_image.png")
LOGO_B64 = ("data:image/png;base64," + base64.b64encode(_lp.read_bytes()).decode()) if _lp.exists() else None

# ── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Inter:wght@300;400;500;600&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif}
h1,h2,h3{font-family:'IBM Plex Mono',monospace}
[data-testid="stSidebar"]{background:#0a0c14;border-right:1px solid #1e2030}
[data-testid="stSidebar"] * {color:#ccc}

.stat-card{background:#0f1117;border:1px solid #1e2030;border-radius:10px;padding:18px;text-align:center;height:100%}
.stat-number{font-size:2rem;font-weight:600;font-family:'IBM Plex Mono',monospace;display:block;margin-bottom:4px}
.stat-label{font-size:0.7rem;text-transform:uppercase;letter-spacing:0.12em;color:#555}

.sec-label{font-family:'IBM Plex Mono',monospace;font-size:0.68rem;text-transform:uppercase;
           letter-spacing:0.18em;color:#444;border-bottom:1px solid #1e2030;
           padding-bottom:6px;margin-bottom:14px;margin-top:0}

.hyp-card{background:#0f1117;border-left:3px solid #1e2030;padding:12px 16px;
          border-radius:0 8px 8px 0;font-size:0.84rem;color:#999;margin-bottom:8px;line-height:1.7}
.hyp-badge{font-family:'IBM Plex Mono',monospace;font-size:0.72rem;font-weight:600;margin-right:8px}

.assay-box{background:#0a160a;border:1px solid #1a3a1a;border-radius:8px;padding:14px 16px;margin-top:8px}
.assay-title{font-family:'IBM Plex Mono',monospace;font-size:0.65rem;text-transform:uppercase;
             letter-spacing:0.15em;color:#4CAF50;margin-bottom:8px}
.assay-row{display:flex;gap:8px;padding:5px 0;font-size:0.78rem;border-bottom:1px solid #122012}
.assay-lbl{color:#3a5a3a;min-width:110px;font-size:0.72rem;font-family:'IBM Plex Mono',monospace;flex-shrink:0}
.assay-val{color:#aaa}

.facts-table{width:100%;border-collapse:collapse;font-size:0.82rem}
.facts-table td{padding:7px 10px;border-bottom:1px solid #1a1d2e;color:#bbb;vertical-align:top}
.facts-table td:first-child{color:#444;font-family:'IBM Plex Mono',monospace;font-size:0.7rem;width:130px}

.step-num{width:28px;height:28px;border-radius:50%;background:#FF4C4C22;color:#FF4C4C;
          border:1px solid #FF4C4C55;display:flex;align-items:center;justify-content:center;
          font-family:'IBM Plex Mono',monospace;font-size:0.75rem;font-weight:600;
          flex-shrink:0;margin-top:2px}

.page-header{display:flex;align-items:center;gap:14px;margin-bottom:6px}
.page-header h2{margin:0;font-size:1.5rem}
.page-header p{color:#555;font-size:0.85rem;margin:0}
</style>
""", unsafe_allow_html=True)


# ── Tutorial dialog ────────────────────────────────────────────────────────
@st.dialog("How to use Protellect")
def show_tutorial():
    if LOGO_B64:
        st.markdown(f'<img src="{LOGO_B64}" style="height:52px;object-fit:contain;border-radius:8px;margin-bottom:12px">', unsafe_allow_html=True)
    st.markdown("#### Experimental Intelligence Layer for Biomedical Research")
    st.markdown("Converts raw experimental data into ranked, annotated biological hypotheses in minutes.")
    st.divider()
    for i, (title, detail) in enumerate([
        ("Upload your CSV", "Sidebar → Upload CSV. Required: `residue_position`, `effect_score`. Optional: `mutation`, `experiment_type`. Works with DMS, CRISPR log2FC, ΔΔG stability, any numeric scale."),
        ("Click Run Triage", "Scores every residue, detects assay type automatically, normalises the scale, assigns HIGH/MEDIUM/LOW priority, generates hypothesis text, and maps to 3D protein structure."),
        ("Tab 1 — Triage System", "Ranked table + 3D structure coloured by priority. Download as CSV."),
        ("Tab 2 — Case Study", "Pre-built TP53 R175H walkthrough — how Protellect processes a known mutation."),
        ("Tab 3 — Protein Explorer", "Interactive 3D viewer. Click any residue → full annotation with ClinVar, COSMIC, mechanism, therapeutic context."),
        ("Tab 4 — Hypothesis Lab", "Every hypothesis as an expandable card. Drag the slider → protein structure animates showing the actual molecular mechanism + cell diagram updates in sync."),
    ], 1):
        c1, c2 = st.columns([0.06, 0.94])
        with c1:
            st.markdown(f'<div class="step-num">{i}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f"**{title}**  \n{detail}")
        st.markdown("")
    st.markdown("---")
    st.markdown("🔴 **HIGH** ≥0.75 · 🟠 **MEDIUM** ≥0.40 · 🔵 **LOW** — thresholds adjustable in sidebar  \nClick ❓ in the sidebar to reopen this tutorial anytime.")
    if st.button("Start exploring →", type="primary", use_container_width=True):
        st.session_state.tut_seen = True
        st.rerun()


if "tut_seen" not in st.session_state:
    st.session_state.tut_seen = False
if not st.session_state.tut_seen:
    show_tutorial()


# ── Helpers ────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def fetch_pdb(pdb_id="2OCJ"):
    try:
        r = requests.get(f"https://files.rcsb.org/download/{pdb_id}.pdb", timeout=15)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def make_viewer(pdb_data, residue_scores, width=580, height=455, zoom="94-292"):
    esc = pdb_data.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")[:260000]
    styles = ""
    for resi, opts in residue_scores.items():
        styles += f"v.addStyle({{resi:{resi}}},{{sphere:{{color:'{opts['color']}',radius:{opts['radius']}}}}});\n"
    return f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<style>body{{margin:0;background:#080b14}}#v{{width:{width}px;height:{height}px}}</style>
</head><body><div id="v"></div><script>
const p=`{esc}`;
let v=$3Dmol.createViewer('v',{{backgroundColor:'#080b14',antialias:true}});
v.addModel(p,'pdb');
v.setStyle({{}},{{cartoon:{{color:'#1e2030',opacity:0.55}}}});
{styles}
v.zoomTo({{resi:'{zoom}'}});v.spin(false);v.render();
</script></body></html>"""


# ── SIDEBAR ────────────────────────────────────────────────────────────────
with st.sidebar:
    cl, ct, ch = st.columns([1, 3.2, 1])
    with cl:
        if LOGO_B64:
            st.markdown(f'<img src="{LOGO_B64}" style="width:36px;height:36px;object-fit:contain;border-radius:6px;margin-top:6px">', unsafe_allow_html=True)
        else:
            st.write("🧬")
    with ct:
        st.markdown("### Protellect")
    with ch:
        if st.button("❓", help="Open tutorial"):
            show_tutorial()

    st.markdown('<p style="font-size:0.73rem;color:#444;margin:-6px 0 0;font-family:IBM Plex Mono,monospace">Experimental Intelligence Layer</p>', unsafe_allow_html=True)
    st.divider()

    st.markdown('<div class="sec-label">Experimental Data</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload CSV", type="csv", label_visibility="collapsed")
    st.caption("Required: `residue_position`, `effect_score`  \nOptional: `mutation`, `experiment_type`")
    with st.expander("View expected format"):
        st.code("residue_position,effect_score,mutation,experiment_type\n175,0.99,R175H,DMS\n248,0.97,R248W,DMS\n12,-1.42,G12D,CRISPR", language="text")
    use_sample = st.checkbox("Use built-in TP53 sample data", value=not bool(uploaded_file))

    st.divider()
    st.markdown('<div class="sec-label">Triage Thresholds</div>', unsafe_allow_html=True)
    high_thresh   = st.slider("HIGH cutoff",   0.5, 1.0, 0.75, 0.01)
    medium_thresh = st.slider("MEDIUM cutoff", 0.1, 0.7, 0.40, 0.01)
    st.caption("Residues at or above HIGH are flagged for immediate follow-up.")

    run_btn = st.button("▶  Run Triage", type="primary", use_container_width=True)

    # Assay summary after triage
    if "t_info" in st.session_state and "t_scored" in st.session_state:
        info   = st.session_state.t_info
        scored = st.session_state.t_scored
        n_high = int((scored["priority"] == "HIGH").sum())
        top    = scored.iloc[0]
        top_lbl = str(top.get("mutation", f"Res{int(top['residue_position'])}"))
        if str(top_lbl) in ("nan", ""):
            top_lbl = f"Res{int(top['residue_position'])}"
        exps = ", ".join(info["exp_types"][:3]) if info["exp_types"] else "Not specified"
        st.markdown(f"""
        <div class="assay-box">
          <div class="assay-title">📋 Assay Summary</div>
          <div class="assay-row"><span class="assay-lbl">Assay type</span><span class="assay-val">{info['assay_guess']}</span></div>
          <div class="assay-row"><span class="assay-lbl">Residues</span><span class="assay-val">{info['n_rows']}</span></div>
          <div class="assay-row"><span class="assay-lbl">Score range</span><span class="assay-val">{info['score_min']} → {info['score_max']}</span></div>
          <div class="assay-row"><span class="assay-lbl">Scale</span><span class="assay-val">{info['direction_note']}</span></div>
          <div class="assay-row"><span class="assay-lbl">Experiments</span><span class="assay-val">{exps}</span></div>
          <div class="assay-row"><span class="assay-lbl">HIGH hits</span><span class="assay-val" style="color:#FF4C4C;font-weight:600">{n_high} residues</span></div>
          <div class="assay-row" style="border:none"><span class="assay-lbl">Top hit</span><span class="assay-val" style="color:#FF4C4C;font-weight:600">{top_lbl} ({round(float(top['normalized_score']),3)})</span></div>
        </div>""", unsafe_allow_html=True)

    st.divider()
    st.caption("Structure: TP53 DNA-binding domain · PDB 2OCJ")
    st.caption("Phase 2 will auto-identify protein from sequence data")


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
        st.markdown(f'<div class="page-header"><img src="{LOGO_B64}" style="height:44px;object-fit:contain;border-radius:8px"><div><h2>Triage System</h2><p>Upload experimental data · score residues · visualize on 3D structure</p></div></div>', unsafe_allow_html=True)
    else:
        st.markdown("## Triage System")
    st.divider()

    if run_btn:
        if uploaded_file:
            df_raw = pd.read_csv(uploaded_file)
        elif use_sample:
            df_raw = pd.read_csv("sample_data/example.csv")
        else:
            st.error("Please upload a CSV or enable sample data.")
            st.stop()
        df_raw.columns = df_raw.columns.str.lower().str.strip()
        valid, err = validate_dataframe(df_raw)
        if not valid:
            st.error(f"❌ {err}")
            st.stop()
        import scorer as _sc
        _sc.assign_priority = lambda s: "HIGH" if s >= high_thresh else "MEDIUM" if s >= medium_thresh else "LOW"
        with st.spinner("Scoring residues..."):
            st.session_state.t_scored = score_residues(df_raw)
            st.session_state.t_stats  = get_summary_stats(st.session_state.t_scored)
            st.session_state.t_info   = detect_dataset_info(df_raw)

    if "t_scored" not in st.session_state:
        st.info("👈  Upload your data and click **▶  Run Triage** to begin.")
        st.stop()

    scored = st.session_state.t_scored
    stats  = st.session_state.t_stats

    c1, c2, c3, c4, c5 = st.columns(5)
    for col, num, lbl, clr in [
        (c1, stats["total_residues"],  "Total Residues", "#eee"),
        (c2, stats["high_priority"],   "HIGH Priority",  "#FF4C4C"),
        (c3, stats["medium_priority"], "MEDIUM Priority","#FFA500"),
        (c4, stats["low_priority"],    "LOW Priority",   "#4CA8FF"),
        (c5, f"R{stats['top_residue']}","Top Residue",   "#FF4C4C"),
    ]:
        col.markdown(f'<div class="stat-card"><span class="stat-number" style="color:{clr}">{num}</span><span class="stat-label">{lbl}</span></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns([1, 1.4], gap="large")

    with left:
        st.markdown('<div class="sec-label">Ranked Hypotheses</div>', unsafe_allow_html=True)
        disp = ["residue_position", "normalized_score", "priority"]
        if "mutation" in scored.columns:        disp.insert(1, "mutation")
        if "experiment_type" in scored.columns: disp.append("experiment_type")

        def cprio(val):
            c = "#FF4C4C" if val == "HIGH" else "#FFA500" if val == "MEDIUM" else "#4CA8FF"
            return f"color:{c};font-weight:600"

        st.dataframe(
            scored[disp].style.map(cprio, subset=["priority"]).format({"normalized_score": "{:.3f}"}),
            use_container_width=True, height=320
        )

        st.markdown('<div class="sec-label" style="margin-top:20px">Hypothesis Text</div>', unsafe_allow_html=True)
        top_n = st.slider("Show top N hypotheses", 1, min(10, len(scored)), 5, key="t1_n")
        for _, row in scored.head(top_n).iterrows():
            p = str(row.get("priority", "LOW"))
            c = "#FF4C4C" if p == "HIGH" else "#FFA500" if p == "MEDIUM" else "#4CA8FF"
            h = str(row.get("hypothesis", ""))
            st.markdown(f'<span class="hyp-badge" style="color:{c}">[{p}]</span><div class="hyp-card">{h}</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="sec-label">3D Protein Structure — colored by priority</div>', unsafe_allow_html=True)
        with st.spinner("Loading structure..."):
            pdb = fetch_pdb("2OCJ")
        if pdb:
            cmap = {"HIGH": "#FF4C4C", "MEDIUM": "#FFA500", "LOW": "#4CA8FF"}
            rmap = {"HIGH": 0.85,       "MEDIUM": 0.60,      "LOW": 0.40}
            rs = {
                int(r["residue_position"]): {"color": cmap[str(r["priority"])], "radius": rmap[str(r["priority"])]}
                for _, r in scored.iterrows()
            }
            components.html(make_viewer(pdb, rs, 580, 455), height=460)
            st.markdown('<div style="display:flex;gap:20px;margin-top:8px;font-size:0.78rem"><span><span style="color:#FF4C4C">●</span> HIGH</span><span><span style="color:#FFA500">●</span> MEDIUM</span><span><span style="color:#4CA8FF">●</span> LOW</span></div>', unsafe_allow_html=True)
        else:
            st.error("Could not load protein structure. Check your internet connection.")

    st.divider()
    exp_df = scored.drop(columns=["hypothesis"], errors="ignore")
    st.download_button("⬇  Download scored results (CSV)", exp_df.to_csv(index=True).encode(), "protellect_results.csv", "text/csv")


# ══════════════════════════════════════════════════════════════════════════
# TAB 2
# ══════════════════════════════════════════════════════════════════════════
with tab2:
    if LOGO_B64:
        st.markdown(f'<div class="page-header"><img src="{LOGO_B64}" style="height:44px;object-fit:contain;border-radius:8px"><div><h2>Case Study — TP53 R175H</h2><p>The most common oncogenic TP53 mutation · how Protellect processes it</p></div></div>', unsafe_allow_html=True)
    else:
        st.markdown("## Case Study — TP53 R175H")
    st.divider()

    left, right = st.columns([1, 1.3], gap="large")
    with left:
        st.markdown('<div class="sec-label">The Mutation</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#0f1117;border:1px solid #2a2d3a;border-radius:10px;padding:18px;margin-bottom:14px">
          <p style="font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:#FF4C4C;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.08em">Background</p>
          <p style="font-size:0.84rem;color:#bbb;margin:0;line-height:1.7">Arginine 175 → Histidine. Disrupts the zinc-coordination site (C176/H179/C238/C242) causing global misfolding of the DNA-binding domain. Found in <strong style="color:#FF4C4C">~6% of all human cancers</strong> — the most frequently observed TP53 hotspot globally.</p>
        </div>
        <div style="background:#0f1117;border:1px solid #2a2d3a;border-radius:10px;padding:18px;margin-bottom:14px">
          <p style="font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:#FF4C4C;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.08em">Protellect Output</p>
          <p style="font-size:0.84rem;color:#bbb;margin:0;line-height:1.7">Effect score: <strong style="color:#FF4C4C">0.99 / 1.00</strong> · Priority: <strong style="color:#FF4C4C">HIGH</strong><br><br>Flagged instantly from DMS data. No manual literature review required.</p>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div class="sec-label">Experimental Pathway</div>', unsafe_allow_html=True)
        for i, (title, detail) in enumerate([
            ("Protellect flags R175H", "DMS score 0.99 → HIGH priority assigned automatically."),
            ("Structural validation", "PDB 2OCJ loaded. R175 confirmed in zinc-binding L2 loop."),
            ("Database enrichment", "ClinVar: 847 pathogenic submissions. UniProt: zinc binding disrupted."),
            ("Hypothesis formed", "R175H → zinc-site collapse → misfolding → loss of tumour suppression."),
            ("Experimental validation", "Thermal shift (Tm −8°C) → EMSA → luciferase reporter assay."),
            ("Therapeutic angle", "APR-246 (eprenetapopt) — Phase III refolding compound."),
        ], 1):
            st.markdown(f'<div style="display:flex;gap:12px;margin-bottom:12px"><div class="step-num">{i}</div><div><strong style="color:#eee;font-size:0.88rem;display:block;margin-bottom:3px">{title}</strong><span style="color:#666;font-size:0.8rem;line-height:1.5">{detail}</span></div></div>', unsafe_allow_html=True)

        st.markdown('<div style="background:#0a1a0a;border:1px solid #1a4a1a;border-radius:8px;padding:14px"><p style="font-family:\'IBM Plex Mono\',monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.12em;color:#4CAF50;margin-bottom:6px">Result</p><p style="font-size:0.82rem;color:#aaa;margin:0;line-height:1.6">Manual review: 2–4 hours. With Protellect: <strong style="color:#4CAF50">minutes.</strong></p></div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="sec-label">3D Structure — TP53 DNA-binding domain</div>', unsafe_allow_html=True)
        st.caption("R175 highlighted in red · DNA-binding domain in blue · other hotspots in orange")
        with st.spinner("Loading..."):
            pdb_cs = fetch_pdb("2OCJ")
        if pdb_cs:
            esc2 = pdb_cs.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")[:260000]
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
            st.markdown('<div style="display:flex;gap:20px;margin-top:8px;font-size:0.78rem;flex-wrap:wrap"><span><span style="color:#FF4C4C;font-size:1rem">●</span> R175 focus</span><span><span style="color:#FF8C00;font-size:1rem">●</span> Other hotspots</span><span><span style="color:#4CA8FF;font-size:1rem">━</span> DNA-binding domain</span></div>', unsafe_allow_html=True)
        else:
            st.error("Could not load structure. Check your internet connection.")

        st.divider()
        st.markdown('<div class="sec-label">Key Facts</div>', unsafe_allow_html=True)
        facts = [
            ("Mutation",     "Missense · Arg→His at codon 175"),
            ("Domain",       "DNA-binding domain · L2 loop · zinc coordination site"),
            ("Mechanism",    "Zinc-site disruption → global misfolding → loss of DNA binding"),
            ("Frequency",    "~6% of all cancers · most common TP53 hotspot"),
            ("Cancer types", "Breast, lung, colorectal, ovarian, bladder"),
            ("ClinVar",      "847 pathogenic submissions"),
            ("Therapeutic",  "APR-246 (eprenetapopt) · Phase III clinical trials"),
        ]
        st.markdown('<table class="facts-table">' + "".join(f"<tr><td>{l}</td><td>{v}</td></tr>" for l, v in facts) + "</table>", unsafe_allow_html=True)


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
