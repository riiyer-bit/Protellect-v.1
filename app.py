"""
app.py — Protellect MVP
Run with: streamlit run app.py

All 3D viewers use pure 3Dmol.js via HTML components — no py3Dmol or stmol needed.
Everything is driven from the uploaded CSV. No protein type selection required.
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import json

from scorer import score_residues, get_summary_stats, validate_dataframe, detect_dataset_info

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Protellect",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Logo SVG (inline, matches uploaded brand mark) ───────────────────────────
LOGO_SVG = """<svg width="36" height="36" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="lg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#2d6a4f"/>
      <stop offset="100%" style="stop-color:#1b4332"/>
    </linearGradient>
  </defs>
  <!-- Left helix strand -->
  <path d="M45 10 C35 30, 65 45, 55 60 C45 75, 25 85, 35 105" stroke="url(#lg)" stroke-width="7" fill="none" stroke-linecap="round"/>
  <!-- Right helix strand -->
  <path d="M75 10 C85 30, 55 45, 65 60 C75 75, 95 85, 85 105" stroke="url(#lg)" stroke-width="7" fill="none" stroke-linecap="round"/>
  <!-- Crossbars -->
  <line x1="48" y1="22" x2="72" y2="22" stroke="#52b788" stroke-width="4.5" stroke-linecap="round"/>
  <line x1="42" y1="38" x2="78" y2="38" stroke="#52b788" stroke-width="4.5" stroke-linecap="round"/>
  <line x1="52" y1="53" x2="68" y2="53" stroke="#52b788" stroke-width="4" stroke-linecap="round"/>
  <line x1="55" y1="67" x2="65" y2="67" stroke="#52b788" stroke-width="4" stroke-linecap="round"/>
  <line x1="51" y1="82" x2="69" y2="82" stroke="#52b788" stroke-width="4" stroke-linecap="round"/>
  <line x1="45" y1="96" x2="75" y2="96" stroke="#52b788" stroke-width="4.5" stroke-linecap="round"/>
  <!-- Neural branches top right -->
  <path d="M72 22 L90 12" stroke="#74c69d" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M90 12 L100 6" stroke="#74c69d" stroke-width="2" stroke-linecap="round"/>
  <path d="M90 12 L102 15" stroke="#74c69d" stroke-width="2" stroke-linecap="round"/>
  <circle cx="100" cy="6" r="2.5" fill="#74c69d"/>
  <circle cx="102" cy="15" r="2.5" fill="#74c69d"/>
  <!-- Neural branches bottom left -->
  <path d="M48 82 L28 92" stroke="#74c69d" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M28 92 L16 86" stroke="#74c69d" stroke-width="2" stroke-linecap="round"/>
  <path d="M28 92 L18 100" stroke="#74c69d" stroke-width="2" stroke-linecap="round"/>
  <circle cx="16" cy="86" r="2.5" fill="#74c69d"/>
  <circle cx="18" cy="100" r="2.5" fill="#74c69d"/>
</svg>"""

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
h1, h2, h3 { font-family: 'IBM Plex Mono', monospace; }
.section-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem; text-transform: uppercase;
    letter-spacing: 0.15em; color: #555;
    margin-bottom: 12px; padding-bottom: 6px;
    border-bottom: 1px solid #1e2030;
}
.stat-card {
    background: #0f1117; border: 1px solid #2a2d3a;
    border-radius: 8px; padding: 16px 20px; text-align: center;
}
.stat-number { font-size: 2rem; font-weight: 600; font-family: 'IBM Plex Mono', monospace; }
.stat-label  { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: #888; margin-top: 4px; }
.high-badge   { color: #FF4C4C; font-weight: 600; }
.medium-badge { color: #FFA500; font-weight: 600; }
.low-badge    { color: #4CA8FF; font-weight: 600; }
.hypothesis-box {
    background: #0f1117; border-left: 3px solid #2a2d3a;
    padding: 10px 14px; border-radius: 0 6px 6px 0;
    font-size: 0.85rem; color: #aaa; margin: 4px 0;
}
</style>
""", unsafe_allow_html=True)


# ── Tutorial popup ─────────────────────────────────────────────────────────────
@st.dialog("🧬 Welcome to Protellect")
def show_tutorial():
    st.markdown("**Experimental Intelligence Layer for Biomedical Research**")
    st.divider()
    steps = [
        ("1", "Upload your CSV in the sidebar", "Required: `residue_position`, `effect_score`. Optional: `mutation`, `experiment_type`. The system scores every residue automatically — no protein ID needed."),
        ("2", "Click Run Triage", "Scores all residues, generates ranked hypotheses, and maps everything onto the 3D protein structure. Results persist — no need to re-run when clicking around."),
        ("3", "Explore the 4 tabs", "**Tab 1 — Triage System:** ranked table + 3D structure.  \n**Tab 2 — Case Study:** TP53 R175H worked example.  \n**Tab 3 — Protein Explorer:** click residue spheres for full annotation.  \n**Tab 4 — Hypothesis Lab:** every hypothesis with animation, timeline slider, and cell impact."),
        ("4", "Priority colours", "🔴 **RED** = HIGH priority (score ≥ 0.75) — investigate first.  \n🟠 **ORANGE** = MEDIUM (score ≥ 0.40) — worth investigating.  \n🔵 **BLUE** = LOW — likely tolerated. Thresholds adjustable in sidebar."),
        ("5", "Access tutorial anytime", "Click the **❓ Tutorial** button in the sidebar to reopen this guide."),
    ]
    for num, title, detail in steps:
        col_n, col_body = st.columns([0.08, 0.92])
        with col_n:
            st.markdown(f'<div style="width:26px;height:26px;border-radius:50%;background:#FF4C4C22;color:#FF4C4C;border:1px solid #FF4C4C55;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;margin-top:4px">{num}</div>', unsafe_allow_html=True)
        with col_body:
            st.markdown(f"**{title}**")
            st.markdown(detail)
        st.markdown("")
    if st.button("Start exploring →", type="primary", use_container_width=True):
        st.session_state.tutorial_shown = True
        st.rerun()

if "tutorial_shown" not in st.session_state:
    st.session_state.tutorial_shown = False

if not st.session_state.tutorial_shown:
    show_tutorial()


# ── Helper: fetch PDB ─────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def fetch_pdb(pdb_id="2OCJ"):
    try:
        r = requests.get(f"https://files.rcsb.org/download/{pdb_id}.pdb", timeout=15)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


# ── Helper: build 3D viewer HTML (pure 3Dmol.js, no py3Dmol/stmol) ───────────
def build_3d_viewer(pdb_data, residue_scores=None, highlight_resi=None,
                    width=560, height=440, zoom_resi="94-292",
                    special_residues=None):
    """
    residue_scores: dict {resi: {"color": hex, "radius": float}}
    highlight_resi: single residue to show white sphere
    special_residues: list of {resi, color, radius, surface}
    """
    pdb_esc = pdb_data.replace("\\","\\\\").replace("`","\\`").replace("${","\\${")[:280000]

    style_cmds = []
    if residue_scores:
        for resi, opts in residue_scores.items():
            c = opts.get("color", "#4CA8FF")
            r = opts.get("radius", 0.5)
            style_cmds.append(f"v.addStyle({{resi:{resi}}},{{sphere:{{color:'{c}',radius:{r}}}}});")

    if special_residues:
        for sr in special_residues:
            r = sr.get("resi", 175)
            c = sr.get("color", "#FF4C4C")
            rad = sr.get("radius", 1.0)
            style_cmds.append(f"v.addStyle({{resi:{r}}},{{sphere:{{color:'{c}',radius:{rad}}}}});")
            if sr.get("surface"):
                style_cmds.append(f"v.addSurface($3Dmol.VDW,{{opacity:0.35,color:'{c}'}},{{resi:{r}}});")

    if highlight_resi:
        style_cmds.append(f"v.addStyle({{resi:{highlight_resi}}},{{sphere:{{color:'#ffffff',radius:1.2}}}});")

    styles_str = "\n".join(style_cmds)
    zoom_str = f"v.zoomTo({{resi:'{zoom_resi}'}})" if zoom_resi else "v.zoomTo()"

    return f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<style>body{{margin:0;background:#080b14}}#v{{width:{width}px;height:{height}px}}</style>
</head><body>
<div id="v"></div>
<script>
const pdb=`{pdb_esc}`;
let v=$3Dmol.createViewer('v',{{backgroundColor:'#080b14',antialias:true}});
v.addModel(pdb,'pdb');
v.setStyle({{}},{{cartoon:{{color:'#1e2030',opacity:0.6}}}});
{styles_str}
{zoom_str};
v.spin(false);v.render();
</script></body></html>"""


# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    # Tutorial help button
    col_title, col_help = st.columns([5, 1])
    with col_title:
        st.markdown(f'{LOGO_SVG} &nbsp;<span style="font-size:1.2rem;font-weight:700;font-family:IBM Plex Mono,monospace;vertical-align:middle">Protellect</span>', unsafe_allow_html=True)
    with col_help:
        if st.button("❓", help="Open tutorial"):
            st.session_state.tutorial_shown = False
            show_tutorial()

    st.markdown("*Experimental Triage System — MVP*")
    st.divider()

    st.markdown('<div class="section-header">Experimental Data</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload CSV", type="csv")
    st.caption("Required: `residue_position`, `effect_score`")
    st.caption("Optional: `mutation`, `experiment_type`")

    with st.expander("CSV format example"):
        st.code("""residue_position,effect_score,mutation,experiment_type
175,0.99,R175H,DMS
248,0.97,R248W,DMS
103,0.45,R103W,CRISPR""")

    use_sample = st.checkbox(
        "Use built-in sample data (TP53 DMS)",
        value=not bool(uploaded_file)
    )

    st.divider()
    st.markdown('<div class="section-header">Triage Thresholds</div>', unsafe_allow_html=True)
    high_thresh   = st.slider("HIGH priority cutoff",   0.5, 1.0, 0.75, 0.01)
    medium_thresh = st.slider("MEDIUM priority cutoff", 0.1, 0.7, 0.40, 0.01)
    st.caption("Residues above HIGH are flagged for immediate follow-up.")

    run_button = st.button("▶ Run Triage", type="primary", use_container_width=True)

    # ── Assay summary (shown after triage runs) ───────────────────────────────
    if "t_scored" in st.session_state and "t_dataset_info" in st.session_state:
        st.divider()
        info = st.session_state.t_dataset_info
        st.markdown("""
        <div style="background:#0a1a0a;border:1px solid #1a3a1a;border-radius:8px;padding:12px 14px">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#4CAF50;margin-bottom:8px">📋 Assay Summary</div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
          <div style="font-size:11px;color:#888;line-height:1.8">
            <b style="color:#ccc">Dataset:</b> {info['n_rows']} residues<br>
            <b style="color:#ccc">Assay type:</b> {info['assay_guess']}<br>
            <b style="color:#ccc">Score range:</b> {info['score_min']} → {info['score_max']}<br>
            <b style="color:#ccc">Scale detected:</b> {info['direction_note']}<br>
            {'<b style="color:#ccc">Experiments:</b> ' + ", ".join(str(e) for e in info["exp_types"][:4]) + "<br>" if info["exp_types"] else ""}
            {'<b style="color:#ccc">Mutations:</b> Provided in data<br>' if info["has_mutations"] else ""}
          </div>
        </div>""", unsafe_allow_html=True)

    st.divider()
    st.caption("Protein structure: TP53 (PDB 2OCJ)")
    st.caption("Phase 2 will auto-identify protein from sequence data.")


# ── TABS ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🧬 Triage System",
    "🔬 Case Study — TP53 R175H",
    "⚗️ Protein Explorer",
    "💡 Hypothesis Lab",
])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — Triage System
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("## Protellect — Experimental Intelligence Layer")
    st.markdown("Upload residue-level experimental data → score it → visualize on 3D structure.")
    st.divider()

    # ── Run triage and store in session state ─────────────────────────────────
    if run_button:
        if uploaded_file:
            df_raw = pd.read_csv(uploaded_file)
        elif use_sample:
            df_raw = pd.read_csv("sample_data/example.csv")
        else:
            st.error("Please upload a CSV file or enable sample data.")
            st.stop()

        df_raw.columns = df_raw.columns.str.lower().str.strip()
        valid, err = validate_dataframe(df_raw)
        if not valid:
            st.error(f"❌ Data error: {err}")
            st.stop()

        import scorer as _scorer
        _scorer.assign_priority = lambda score: (
            "HIGH"   if score >= high_thresh   else
            "MEDIUM" if score >= medium_thresh else
            "LOW"
        )
        with st.spinner("Scoring residues..."):
            st.session_state.t_scored      = score_residues(df_raw)
            st.session_state.t_stats       = get_summary_stats(st.session_state.t_scored)
            st.session_state.t_dataset_info = detect_dataset_info(df_raw)

    if "t_scored" not in st.session_state:
        st.info("👈 Upload your CSV and click **▶ Run Triage** to begin.")
        st.stop()

    scored_df = st.session_state.t_scored
    stats     = st.session_state.t_stats

    # ── Stat cards ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f'<div class="stat-card"><div class="stat-number">{stats["total_residues"]}</div><div class="stat-label">Total Residues</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card"><div class="stat-number high-badge">{stats["high_priority"]}</div><div class="stat-label">High Priority</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card"><div class="stat-number medium-badge">{stats["medium_priority"]}</div><div class="stat-label">Medium Priority</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card"><div class="stat-number low-badge">{stats["low_priority"]}</div><div class="stat-label">Low Priority</div></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="stat-card"><div class="stat-number">R{stats["top_residue"]}</div><div class="stat-label">Top Residue</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    left, right = st.columns([1, 1.4], gap="large")

    # ── Ranked table ────────────────────────────────────────────────────────────
    with left:
        st.markdown('<div class="section-header">Ranked Hypotheses</div>', unsafe_allow_html=True)
        display_cols = ["residue_position", "normalized_score", "priority"]
        if "mutation" in scored_df.columns:
            display_cols.insert(1, "mutation")
        if "experiment_type" in scored_df.columns:
            display_cols.append("experiment_type")

        def color_priority(val):
            colors = {"HIGH": "#FF4C4C", "MEDIUM": "#FFA500", "LOW": "#4CA8FF"}
            return f"color: {colors.get(val, 'white')}; font-weight: 600"

        styled = (
            scored_df[display_cols]
            .style
            .map(color_priority, subset=["priority"])
            .format({"normalized_score": "{:.3f}"})
            .set_properties(**{"font-size": "0.82rem"})
        )
        st.dataframe(styled, use_container_width=True, height=340)

        st.markdown('<div class="section-header" style="margin-top:20px">Hypothesis Text</div>', unsafe_allow_html=True)
        top_n = st.slider("Show top N hypotheses", 1, min(10, len(scored_df)), 5, key="tab1_slider")
        for _, row in scored_df.head(top_n).iterrows():
            priority = str(row.get("priority", "LOW"))
            badge_class = f"{priority.lower()}-badge"
            hypothesis = str(row.get("hypothesis", ""))
            st.markdown(
                f'<span class="{badge_class}">[{priority}]</span>'
                f'<div class="hypothesis-box">{hypothesis}</div>',
                unsafe_allow_html=True
            )

    # ── 3D Viewer ───────────────────────────────────────────────────────────────
    with right:
        st.markdown('<div class="section-header">3D Protein Structure</div>', unsafe_allow_html=True)
        st.caption("Residues colored by priority · TP53 DNA-binding domain · PDB 2OCJ")

        with st.spinner("Loading structure..."):
            pdb_data = fetch_pdb("2OCJ")

        if pdb_data:
            color_map = {"HIGH": "#FF4C4C", "MEDIUM": "#FFA500", "LOW": "#4CA8FF"}
            radius_map = {"HIGH": 0.85, "MEDIUM": 0.60, "LOW": 0.40}
            res_scores = {}
            for _, row in scored_df.iterrows():
                p = str(row.get("priority", "LOW"))
                res_scores[int(row["residue_position"])] = {
                    "color": color_map[p],
                    "radius": radius_map[p],
                }
            viewer_html = build_3d_viewer(pdb_data, residue_scores=res_scores, width=580, height=460)
            components.html(viewer_html, height=465)

            st.markdown("""
            <div style="display:flex;gap:20px;margin-top:8px;font-size:0.78rem;">
                <span><span style="color:#FF4C4C">●</span> HIGH priority</span>
                <span><span style="color:#FFA500">●</span> MEDIUM priority</span>
                <span><span style="color:#4CA8FF">●</span> LOW priority</span>
            </div>""", unsafe_allow_html=True)
        else:
            st.error("Could not load protein structure. Check your internet connection.")

    # ── Export ──────────────────────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-header">Export</div>', unsafe_allow_html=True)
    export_df = scored_df.drop(columns=["hypothesis"], errors="ignore")
    st.download_button(
        label="⬇ Download scored results (CSV)",
        data=export_df.to_csv(index=True).encode("utf-8"),
        file_name="protellect_results.csv",
        mime="text/csv",
    )


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — TP53 R175H Case Study
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("## 🔬 Case Study — TP53 R175H")
    st.markdown("A walkthrough of how Protellect processes a real hypothesis: the most common oncogenic TP53 mutation.")
    st.divider()

    left, right = st.columns([1, 1.3], gap="large")

    with left:
        st.markdown('<div class="section-header">The Mutation</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#0f1117;border:1px solid #2a2d3a;border-radius:10px;padding:18px 22px;margin-bottom:14px">
            <h4 style="font-family:'IBM Plex Mono',monospace;font-size:0.85rem;color:#FF4C4C;margin:0 0 8px;text-transform:uppercase;letter-spacing:0.08em">TP53 R175H — Background</h4>
            <p style="font-size:0.84rem;color:#bbb;margin:0;line-height:1.6">
                Arginine at position 175 is mutated to Histidine. This disrupts the zinc-coordination site
                in TP53's DNA-binding domain, causing global misfolding.
                R175H is found in <strong style="color:#FF4C4C">~6% of all human cancers</strong> — the most
                frequently observed TP53 hotspot mutation globally.
            </p>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">Protellect Triage Output</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#0f1117;border:1px solid #2a2d3a;border-radius:10px;padding:18px 22px;margin-bottom:14px">
            <h4 style="font-family:'IBM Plex Mono',monospace;font-size:0.85rem;color:#FF4C4C;margin:0 0 8px;text-transform:uppercase">Scoring</h4>
            <p style="font-size:0.84rem;color:#bbb;margin:0;line-height:1.6">
                Effect score: <strong style="color:#FF4C4C">0.99 / 1.00</strong> · Priority: <strong style="color:#FF4C4C">HIGH</strong><br><br>
                R175H shows near-complete loss of transcriptional activity across DMS datasets.
                Protellect flags this residue in the top tier instantly.
            </p>
        </div>
        <div style="background:#0f1117;border:1px solid #2a2d3a;border-radius:10px;padding:18px 22px;margin-bottom:14px">
            <h4 style="font-family:'IBM Plex Mono',monospace;font-size:0.85rem;color:#FF4C4C;margin:0 0 8px;text-transform:uppercase">Structural Context</h4>
            <p style="font-size:0.84rem;color:#bbb;margin:0;line-height:1.6">
                Residue 175 sits inside the <strong style="color:#eee">L2 loop</strong> of the DNA-binding domain,
                directly coordinating a structural zinc ion at the C176/H179/C238/C242 tetrahedral site.
                Mutation destabilises the entire domain fold.
            </p>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">Experimental Pathway</div>', unsafe_allow_html=True)
        steps = [
            ("Protellect flags R175H", "DMS score 0.99 → HIGH priority assigned automatically."),
            ("Structural validation", "Load PDB structure. Confirm R175 in zinc-binding L2 loop."),
            ("Database enrichment", "ClinVar: 847 pathogenic submissions. UniProt: disrupts zinc binding."),
            ("Hypothesis formed", "R175H → zinc-site disruption → misfolding → loss of tumour suppression."),
            ("Experimental validation", "Thermal shift assay → EMSA → reporter assay for p21/MDM2."),
            ("Therapeutic angle", "APR-246 (eprenetapopt) — refolding compound, Phase III trials."),
        ]
        for i, (title, detail) in enumerate(steps, 1):
            st.markdown(f"""
            <div style="display:flex;align-items:flex-start;gap:14px;margin-bottom:14px">
                <div style="width:28px;height:28px;border-radius:50%;background:#FF4C4C22;color:#FF4C4C;border:1px solid #FF4C4C55;display:flex;align-items:center;justify-content:center;font-family:'IBM Plex Mono',monospace;font-size:0.75rem;font-weight:600;flex-shrink:0;margin-top:2px">{i}</div>
                <div><strong style="color:#eee;font-size:0.88rem;display:block;margin-bottom:3px">{title}</strong><span style="color:#888;font-size:0.8rem;line-height:1.5">{detail}</span></div>
            </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#0a1a0a;border:1px solid #1a4a1a;border-radius:8px;padding:14px 18px;margin-top:10px">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.12em;color:#4CAF50;margin-bottom:6px">✓ Expected Outcome</div>
            <p style="font-size:0.83rem;color:#aaa;margin:0;line-height:1.6">
                Without Protellect: 2–4 hours to manually reach a validated hypothesis.<br>
                With Protellect: <strong style="color:#4CAF50">same conclusion in minutes.</strong>
            </p>
        </div>""", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section-header">3D Structure — TP53 (PDB 2OCJ)</div>', unsafe_allow_html=True)
        st.caption("R175 in red · DNA-binding domain in blue · other hotspots in orange")

        with st.spinner("Loading TP53 structure from PDB..."):
            pdb_cs = fetch_pdb("2OCJ")

        if pdb_cs:
            # Build a detailed viewer for the case study
            pdb_esc = pdb_cs.replace("\\","\\\\").replace("`","\\`").replace("${","\\${")[:280000]
            cs_html = f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<style>body{{margin:0;background:#080b14}}#v{{width:580px;height:500px}}</style>
</head><body><div id="v"></div><script>
const pdb=`{pdb_esc}`;
let v=$3Dmol.createViewer('v',{{backgroundColor:'#080b14',antialias:true}});
v.addModel(pdb,'pdb');
v.setStyle({{}},{{cartoon:{{color:'#2a2d3e',opacity:0.5}}}});
v.addStyle({{resi:'94-292'}},{{cartoon:{{color:'#4CA8FF',opacity:0.85}}}});
v.addStyle({{resi:175}},{{sphere:{{color:'#FF4C4C',radius:1.0}}}});
v.addSurface($3Dmol.VDW,{{opacity:0.35,color:'#FF4C4C'}},{{resi:175}});
[248,273,249,245,282].forEach(r=>v.addStyle({{resi:r}},{{sphere:{{color:'#FF8C00',radius:0.65}}}}));
v.zoomTo({{resi:'94-292'}});v.spin(false);v.render();
</script></body></html>"""
            components.html(cs_html, height=505)
            st.markdown("""
            <div style="display:flex;gap:24px;margin-top:10px;font-size:0.78rem;flex-wrap:wrap">
                <span><span style="color:#FF4C4C;font-size:1rem">●</span> R175 (focus)</span>
                <span><span style="color:#FF8C00;font-size:1rem">●</span> Other hotspots</span>
                <span><span style="color:#4CA8FF;font-size:1rem">━</span> DNA-binding domain</span>
                <span style="color:#555"><span style="font-size:1rem">━</span> Full protein</span>
            </div>""", unsafe_allow_html=True)
        else:
            st.error("Could not load TP53 structure from PDB. Check your internet connection.")

        st.divider()
        st.markdown('<div class="section-header">Key Facts — R175H</div>', unsafe_allow_html=True)
        facts = [
            ("Mutation type",    "Missense · Arg → His at codon 175"),
            ("Domain",           "DNA-binding domain · L2 loop · zinc coordination site"),
            ("Mechanism",        "Zinc-site disruption → misfolding → loss of DNA binding"),
            ("Frequency",        "~6% of all cancers · most common TP53 hotspot"),
            ("Cancer types",     "Breast, lung, colorectal, ovarian, bladder"),
            ("Functional class", "Loss-of-function + dominant negative"),
            ("ClinVar",          "847 pathogenic submissions"),
            ("Therapeutic",      "APR-246 (eprenetapopt) — refolding compound, Phase III"),
        ]
        for label, value in facts:
            st.markdown(f"""
            <div style="display:flex;gap:12px;padding:7px 0;border-bottom:1px solid #1a1d2e;font-size:0.82rem">
                <span style="color:#555;min-width:130px;font-family:'IBM Plex Mono',monospace;font-size:0.72rem;padding-top:2px">{label}</span>
                <span style="color:#ccc">{value}</span>
            </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — Protein Explorer
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    import protein_explorer
    protein_explorer.render()


# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — Hypothesis Lab
# ════════════════════════════════════════════════════════════════════════════
with tab4:
    import hypothesis_lab
    hypothesis_lab.render()
