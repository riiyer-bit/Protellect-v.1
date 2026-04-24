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

    .case-card {
        background: #0f1117;
        border: 1px solid #2a2d3a;
        border-radius: 10px;
        padding: 18px 22px;
        margin-bottom: 14px;
    }
    .case-card h4 {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        color: #FF4C4C;
        margin: 0 0 8px 0;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .case-card p { font-size: 0.84rem; color: #bbb; margin: 0; line-height: 1.6; }

    .arrow-step { display: flex; align-items: flex-start; gap: 14px; margin-bottom: 16px; }
    .arrow-step .step-num {
        background: #FF4C4C22;
        color: #FF4C4C;
        border: 1px solid #FF4C4C55;
        border-radius: 50%;
        width: 28px; height: 28px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem; font-weight: 600;
        flex-shrink: 0; margin-top: 2px;
    }
    .arrow-step .step-body strong { color: #eee; font-size: 0.88rem; display: block; margin-bottom: 3px; }
    .arrow-step .step-body span   { color: #888; font-size: 0.8rem; line-height: 1.5; }

    .outcome-box {
        background: #0a1a0a;
        border: 1px solid #1a4a1a;
        border-radius: 8px;
        padding: 14px 18px;
        margin-top: 10px;
    }
    .outcome-box .outcome-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #4CAF50;
        margin-bottom: 6px;
    }
    .outcome-box p { font-size: 0.83rem; color: #aaa; margin: 0; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🧬 Triage System", "🔬 Case Study — TP53 R175H", "⚗️ Protein Explorer"])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — Main triage app
# ════════════════════════════════════════════════════════════════════════════
with tab1:

    with st.sidebar:
        st.markdown("# 🧬 Protellect")
        st.markdown("*Experimental Triage System — MVP*")
        st.divider()

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

        st.markdown('<div class="section-header">Triage Thresholds</div>', unsafe_allow_html=True)
        high_thresh   = st.slider("HIGH priority cutoff",   0.5, 1.0, 0.75, 0.01)
        medium_thresh = st.slider("MEDIUM priority cutoff", 0.1, 0.7, 0.40, 0.01)
        st.caption("Residues ≥ HIGH are flagged for immediate follow-up.")
        run_button = st.button("▶ Run Triage", type="primary", use_container_width=True)

    st.markdown("## Protellect — Experimental Intelligence Layer")
    st.markdown("Upload residue-level experimental data → score it → visualize on 3D structure.")
    st.divider()

    if not run_button and "scored_df" not in st.session_state:
        st.info("Configure your protein and data in the sidebar, then click **Run Triage**.")
        st.stop()

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

    valid, err = validate_dataframe(df_raw)
    if not valid:
        st.error(f"❌ Data error: {err}")
        st.stop()

    import scorer as _scorer
    _scorer.assign_priority = lambda score: (
        "HIGH" if score >= high_thresh else
        "MEDIUM" if score >= medium_thresh else
        "LOW"
    )

    with st.spinner("Scoring residues..."):
    st.session_state.scored_df = score_residues(df_raw)
    st.session_state.stats = get_summary_stats(st.session_state.scored_df)

scored_df = st.session_state.scored_df
stats = st.session_state.stats

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
                view.setStyle({"cartoon": {"color": "#1e2030", "opacity": 0.7}})
                for _, row in scored_df.iterrows():
                    color = get_color_for_priority(row["priority"])
                    view.addStyle({"resi": int(row["residue_position"])}, {"sphere": {"color": color, "radius": 0.55}})
                view.zoomTo()
                view.spin(False)
                showmol(view, height=460, width=560)
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

    st.divider()
    st.markdown('<div class="section-header">Export</div>', unsafe_allow_html=True)
    export_df = scored_df.drop(columns=["hypothesis"], errors="ignore")
    csv_out = export_df.to_csv(index=True).encode("utf-8")
    st.download_button(label="⬇ Download scored results (CSV)", data=csv_out, file_name="protellect_results.csv", mime="text/csv")


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
        <div class="case-card">
            <h4>TP53 R175H — Background</h4>
            <p>
                Arginine at position 175 is mutated to Histidine. This single amino acid change
                disrupts the zinc-coordination site in TP53's DNA-binding domain, causing the
                protein to misfold and lose its ability to bind target gene promoters.
                R175H is found in <strong style="color:#FF4C4C">~6% of all human cancers</strong>
                — making it the most frequently observed TP53 hotspot mutation globally.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-header" style="margin-top:20px">Protellect Triage Output</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="case-card">
            <h4>Scoring</h4>
            <p>
                Effect score: <strong style="color:#FF4C4C">0.99 / 1.00</strong> &nbsp;·&nbsp;
                Priority: <strong style="color:#FF4C4C">HIGH</strong><br><br>
                R175H shows near-complete loss of transcriptional activity across DMS datasets.
                Protellect flags this residue in the top tier instantly — before any manual
                literature review is needed.
            </p>
        </div>
        <div class="case-card">
            <h4>Structural Context</h4>
            <p>
                Residue 175 sits inside the <strong style="color:#eee">L2 loop</strong> of the
                DNA-binding domain, directly coordinating a structural zinc ion. Mutation here
                doesn't just disrupt one contact — it destabilizes the entire domain fold,
                explaining the severe functional loss seen experimentally.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-header" style="margin-top:20px">Experimental Pathway</div>', unsafe_allow_html=True)
        st.markdown("<p style='font-size:0.82rem; color:#888; margin-bottom:16px'>How a researcher proceeds after Protellect flags R175H as HIGH priority:</p>", unsafe_allow_html=True)

        steps = [
            ("Protellect flags R175H",
             "DMS score 0.99, structural position in zinc-coordination loop → HIGH priority assigned automatically."),
            ("Structural validation",
             "Load AlphaFold structure. Confirm R175 is in zinc-binding L2 loop. Visualize coordination geometry — shown live in the viewer on the right."),
            ("Database enrichment",
             "Pull ClinVar entries → 847 pathogenic submissions. UniProt: 'disrupts zinc binding'. Conservation: 100% across vertebrates."),
            ("Hypothesis formed",
             "R175H causes misfolding of the DNA-binding domain via zinc-site disruption → loss of tumour suppressor activity → oncogenesis."),
            ("Experimental validation",
             "Prioritise: (1) thermal shift assay to confirm destabilisation, (2) EMSA for loss of DNA binding, (3) reporter assay for transcriptional activity."),
            ("Therapeutic angle",
             "R175H is a gain-of-function mutant — explore refolding compounds (e.g. APR-246 / eprenetapopt) that restore WT conformation. Currently in clinical trials."),
        ]

        for i, (title, detail) in enumerate(steps, 1):
            st.markdown(f"""
            <div class="arrow-step">
                <div class="step-num">{i}</div>
                <div class="step-body">
                    <strong>{title}</strong>
                    <span>{detail}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div class="outcome-box">
            <div class="outcome-label">✓ Expected Outcome</div>
            <p>
                Without Protellect: researcher manually reviews DMS tables, cross-references
                literature, looks up ClinVar —
                <strong style="color:#eee">2–4 hours</strong> to reach a validated hypothesis.<br><br>
                With Protellect: R175H surfaces as #1 hit instantly. Structural context,
                database annotations, and hypothesis text are pre-generated —
                <strong style="color:#4CAF50">same conclusion reached in minutes.</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section-header">3D Structure — TP53 (AlphaFold)</div>', unsafe_allow_html=True)
        st.caption("R175 highlighted in red · DNA-binding domain in blue · other hotspots in orange")

        with st.spinner("Loading TP53 structure from AlphaFold..."):
            pdb_data, fetch_err = fetch_structure("PDB", "2OCJ")

        if fetch_err:
            st.error(f"❌ {fetch_err}")
        elif pdb_data:
            try:
                import py3Dmol
                from stmol import showmol

                view = py3Dmol.view(width=580, height=500)
                view.addModel(pdb_data, "pdb")

                # Full protein — dark subtle backbone
                view.setStyle({"cartoon": {"color": "#2a2d3e", "opacity": 0.5}})

                # DNA-binding domain (residues 94–292) in blue
                view.addStyle(
                    {"resi": "94-292"},
                    {"cartoon": {"color": "#4CA8FF", "opacity": 0.8}},
                )

                # R175 — the focus mutation, large red sphere + surface
                view.addStyle({"resi": 175}, {"sphere": {"color": "#FF4C4C", "radius": 1.0}})
                view.addSurface(py3Dmol.VDW, {"opacity": 0.4, "color": "#FF4C4C"}, {"resi": 175})

                # Other common hotspots — orange spheres
                for resi in [248, 273, 249, 245, 282]:
                    view.addStyle({"resi": resi}, {"sphere": {"color": "#FF8C00", "radius": 0.65}})

                view.zoomTo({"resi": "94-292"})
                view.spin(False)
                showmol(view, height=500, width=580)

                st.markdown("""
                <div style="display:flex; gap:24px; margin-top:12px; font-size:0.78rem; flex-wrap:wrap;">
                    <span><span style="color:#FF4C4C; font-size:1.1rem;">●</span> R175 (focus)</span>
                    <span><span style="color:#FF8C00; font-size:1.1rem;">●</span> Other hotspots</span>
                    <span><span style="color:#4CA8FF; font-size:1.1rem;">━</span> DNA-binding domain</span>
                    <span style="color:#555;"><span style="font-size:1.1rem;">━</span> Full protein</span>
                </div>
                """, unsafe_allow_html=True)

            except ImportError:
                st.warning("3D viewer not available. Install with: `pip install py3Dmol stmol`")

        st.divider()
        st.markdown('<div class="section-header">Key Facts — R175H</div>', unsafe_allow_html=True)

        facts = [
            ("Mutation type",     "Missense · Arg → His at codon 175"),
            ("Domain",            "DNA-binding domain · L2 loop · zinc coordination site"),
            ("Mechanism",         "Zinc-site disruption → misfolding → loss of DNA binding"),
            ("Frequency",         "~6% of all cancers · most common TP53 hotspot"),
            ("Cancer types",      "Breast, lung, colorectal, ovarian, bladder"),
            ("Functional class",  "Loss-of-function + dominant negative gain-of-function"),
            ("ClinVar",           "847 pathogenic submissions"),
            ("Therapeutic angle", "APR-246 (eprenetapopt) — refolding compound, clinical trials"),
        ]

        for label, value in facts:
            st.markdown(f"""
            <div style="display:flex; gap:12px; padding:7px 0; border-bottom:1px solid #1a1d2e; font-size:0.82rem;">
                <span style="color:#555; min-width:130px; font-family:'IBM Plex Mono',monospace; font-size:0.72rem; padding-top:2px;">{label}</span>
                <span style="color:#ccc;">{value}</span>
            </div>
            """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — Protein Explorer
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    import protein_explorer
    protein_explorer.render()
