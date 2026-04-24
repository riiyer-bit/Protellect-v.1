"""
app.py — Protellect MVP
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd

from scorer import score_residues, get_color_for_priority, get_summary_stats, validate_dataframe
from structure_loader import fetch_structure, EXAMPLE_PROTEINS

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Protellect",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
    h1, h2, h3 { font-family: 'IBM Plex Mono', monospace; }

    .stat-card {
        background: #0f1117;
        border: 1px solid #2a2d3a;
        border-radius: 8px;
        padding: 16px 20px;
        text-align: center;
    }
    .stat-number { font-size: 2rem; font-weight: 600; font-family: 'IBM Plex Mono', monospace; }
    .stat-label  { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: #888; margin-top: 4px; }

    .high-badge   { color: #FF4C4C; font-weight: 600; }
    .medium-badge { color: #FFA500; font-weight: 600; }
    .low-badge    { color: #4CA8FF; font-weight: 600; }

    .hypothesis-box {
        background: #0f1117;
        border-left: 3px solid #2a2d3a;
        padding: 10px 14px;
        border-radius: 0 6px 6px 0;
        font-size: 0.85rem;
        color: #aaa;
        margin: 4px 0;
    }

    .section-header {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        color: #555;
        margin-bottom: 12px;
        padding-bottom: 6px;
        border-bottom: 1px solid #1e2030;
    }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 🧬 Protellect")
    st.markdown("*Experimental Triage System — MVP*")
    st.divider()

    # --- Structure source ---
    st.markdown('<div class="section-header">Protein Structure</div>', unsafe_allow_html=True)

    use_example = st.checkbox("Use an example protein", value=True)

    if use_example:
        example_choice = st.selectbox("Select protein", list(EXAMPLE_PROTEINS.keys()))
        structure_source = EXAMPLE_PROTEINS[example_choice]["source"]
        structure_id     = EXAMPLE_PROTEINS[example_choice]["id"]
        st.caption(f"Source: {structure_source} · ID: `{structure_id}`")
    else:
        structure_source = st.radio("Source", ["AlphaFold", "PDB"], horizontal=True)
        if structure_source == "AlphaFold":
            structure_id = st.text_input("UniProt ID", placeholder="e.g. P04637")
            st.caption("[Find your UniProt ID →](https://www.uniprot.org/)")
        else:
            structure_id = st.text_input("PDB ID", placeholder="e.g. 1TUP")
            st.caption("[Find your PDB ID →](https://www.rcsb.org/)")

    st.divider()

    # --- Data upload ---
    st.markdown('<div class="section-header">Experimental Data</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload CSV", type="csv")
    st.caption("Required columns: `residue_position`, `effect_score`")
    st.caption("Optional: `mutation`, `experiment_type`")

    with st.expander("CSV format example"):
        st.code("""residue_position,effect_score,mutation,experiment_type
42,0.87,A42V,DMS
103,0.94,R103W,CRISPR
175,0.99,R175H,DMS""")

    use_sample = st.checkbox("Use built-in sample data (TP53 DMS)", value=not bool(uploaded_file))

    st.divider()

    # --- Scoring thresholds ---
    st.markdown('<div class="section-header">Triage Thresholds</div>', unsafe_allow_html=True)
    high_thresh   = st.slider("HIGH priority cutoff",   0.5, 1.0, 0.75, 0.01)
    medium_thresh = st.slider("MEDIUM priority cutoff", 0.1, 0.7, 0.40, 0.01)
    st.caption("Residues ≥ HIGH are flagged for immediate follow-up.")

    run_button = st.button("▶ Run Triage", type="primary", use_container_width=True)


# ── Main area ─────────────────────────────────────────────────────────────────
st.markdown("## Protellect — Experimental Intelligence Layer")
st.markdown("Upload residue-level experimental data → score it → visualize on 3D structure.")
st.divider()

if not run_button:
    st.info("👈  Configure your protein and data in the sidebar, then click **Run Triage**.")
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────
if uploaded_file:
    df_raw = pd.read_csv(uploaded_file)
elif use_sample:
    df_raw = pd.read_csv("sample_data/example.csv")
else:
    st.error("Please upload a CSV file or enable sample data.")
    st.stop()

if not structure_id:
    st.error("Please enter a protein ID in the sidebar.")
    st.stop()

# ── Validate ──────────────────────────────────────────────────────────────────
valid, err = validate_dataframe(df_raw)
if not valid:
    st.error(f"❌ Data error: {err}")
    st.stop()

# ── Score ─────────────────────────────────────────────────────────────────────
# Patch in custom thresholds from the sidebar sliders
import scorer as _scorer
_scorer.assign_priority = lambda score: (
    "HIGH" if score >= high_thresh else
    "MEDIUM" if score >= medium_thresh else
    "LOW"
)

with st.spinner("Scoring residues..."):
    scored_df = score_residues(df_raw)
    stats     = get_summary_stats(scored_df)

# ── Summary stats row ─────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown(f"""<div class="stat-card">
        <div class="stat-number">{stats['total_residues']}</div>
        <div class="stat-label">Total Residues</div>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""<div class="stat-card">
        <div class="stat-number high-badge">{stats['high_priority']}</div>
        <div class="stat-label">High Priority</div>
    </div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""<div class="stat-card">
        <div class="stat-number medium-badge">{stats['medium_priority']}</div>
        <div class="stat-label">Medium Priority</div>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""<div class="stat-card">
        <div class="stat-number low-badge">{stats['low_priority']}</div>
        <div class="stat-label">Low Priority</div>
    </div>""", unsafe_allow_html=True)

with c5:
    st.markdown(f"""<div class="stat-card">
        <div class="stat-number">R{stats['top_residue']}</div>
        <div class="stat-label">Top Residue</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Two-column layout: table left, 3D right ───────────────────────────────────
left, right = st.columns([1, 1.4], gap="large")

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

    st.markdown('<div class="section-header" style="margin-top:20px">Hypothesis Output</div>', unsafe_allow_html=True)
    top_n = st.slider("Show top N hypotheses", 1, min(10, len(scored_df)), 5)
    for _, row in scored_df.head(top_n).iterrows():
        badge_class = f"{row['priority'].lower()}-badge"
        st.markdown(
            f'<span class="{badge_class}">[{row["priority"]}]</span> '
            f'<div class="hypothesis-box">{row["hypothesis"]}</div>',
            unsafe_allow_html=True
        )

with right:
    st.markdown('<div class="section-header">3D Protein Structure</div>', unsafe_allow_html=True)

    with st.spinner(f"Fetching structure from {structure_source}..."):
        pdb_data, fetch_error = fetch_structure(structure_source, structure_id)

    if fetch_error:
        st.error(f"❌ {fetch_error}")
    elif pdb_data:
        try:
            import py3Dmol
            from stmol import showmol

            view = py3Dmol.view(width=560, height=460)
            view.addModel(pdb_data, "pdb")

            # Base style: light cartoon backbone
            view.setStyle({"cartoon": {"color": "#1e2030", "opacity": 0.7}})

            # Color each scored residue as a sphere
            for _, row in scored_df.iterrows():
                color = get_color_for_priority(row["priority"])
                view.addStyle(
                    {"resi": int(row["residue_position"])},
                    {"sphere": {"color": color, "radius": 0.55}},
                )

            view.zoomTo()
            view.spin(False)
            showmol(view, height=460, width=560)

            # Legend
            st.markdown("""
            <div style="display:flex; gap:20px; margin-top:10px; font-size:0.78rem;">
                <span><span style="color:#FF4C4C">●</span> HIGH priority</span>
                <span><span style="color:#FFA500">●</span> MEDIUM priority</span>
                <span><span style="color:#4CA8FF">●</span> LOW priority</span>
                <span style="color:#555">● backbone</span>
            </div>
            """, unsafe_allow_html=True)

        except ImportError:
            st.warning("3D viewer not available. Install with: `pip install py3Dmol stmol`")
            st.info("Scored data is still available in the table on the left.")

# ── Export ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown('<div class="section-header">Export</div>', unsafe_allow_html=True)

export_df = scored_df.drop(columns=["hypothesis"], errors="ignore")
csv_out = export_df.to_csv(index=True).encode("utf-8")

st.download_button(
    label="⬇ Download scored results (CSV)",
    data=csv_out,
    file_name="protellect_results.csv",
    mime="text/csv",
)
