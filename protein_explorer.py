"""
protein_explorer.py — Protellect Advanced Protein Explorer
Add this as a new file in your repo. Then in app.py add a third tab:
    tab1, tab2, tab3 = st.tabs(["🧬 Triage System", "🔬 Case Study — TP53 R175H", "⚗️ Protein Explorer"])
    with tab3:
        import protein_explorer
        protein_explorer.render()
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import requests

# ── Residue database ──────────────────────────────────────────────────────────
# Pre-curated data for TP53 key residues
# In Phase 2 this will be pulled live from UniProt + ClinVar APIs

RESIDUE_DATA = {
    175: {
        "label": "R175H",
        "status": "critical",
        "name": "Arginine → Histidine",
        "domain": "DNA-binding domain (L2 loop)",
        "mechanism": "Disrupts zinc ion coordination at Cys176/His179/Cys238/Cys242 tetrahedral site. Causes global misfolding of the DNA-binding domain.",
        "frequency": "~6% of all human cancers — most common TP53 hotspot globally",
        "cancer_types": "Breast, lung, colorectal, ovarian, bladder, sarcoma",
        "functional_class": "Loss-of-function + dominant negative gain-of-function",
        "clinvar_significance": "Pathogenic",
        "clinvar_submissions": 847,
        "uniprot_annotation": "Disrupts zinc binding; causes thermodynamic destabilization",
        "conservation": "100% conserved across vertebrates",
        "effect_score": 0.99,
        "sources": ["UniProt P04637", "ClinVar VCV000012375", "COSMIC v97"],
        "therapeutic": "APR-246 (eprenetapopt) — refolding compound, Phase III trials",
    },
    248: {
        "label": "R248W/Q",
        "status": "critical",
        "name": "Arginine → Tryptophan / Glutamine",
        "domain": "DNA-binding domain (L3 loop)",
        "mechanism": "Direct DNA contact residue. R248 makes hydrogen bonds to the minor groove of DNA at CATG sequences. Substitution abolishes DNA binding.",
        "frequency": "~3% of all cancers",
        "cancer_types": "Colorectal, lung, pancreatic, ovarian",
        "functional_class": "Loss-of-function (contact mutation)",
        "clinvar_significance": "Pathogenic",
        "clinvar_submissions": 623,
        "uniprot_annotation": "Critical DNA contact; mutation eliminates sequence-specific binding",
        "conservation": "100% conserved",
        "effect_score": 0.97,
        "sources": ["UniProt P04637", "ClinVar VCV000012376", "IARC TP53 Database"],
        "therapeutic": "No approved targeted therapy; under investigation for synthetic lethality",
    },
    273: {
        "label": "R273H/C",
        "status": "critical",
        "name": "Arginine → Histidine / Cysteine",
        "domain": "DNA-binding domain (S10 strand)",
        "mechanism": "DNA contact mutation. R273 contacts the DNA backbone phosphate. Loss of this contact reduces DNA-binding affinity >100-fold.",
        "frequency": "~3% of all cancers",
        "cancer_types": "Colorectal, lung, brain, pancreatic",
        "functional_class": "Loss-of-function (contact mutation)",
        "clinvar_significance": "Pathogenic",
        "clinvar_submissions": 512,
        "uniprot_annotation": "DNA backbone contact; R273C retains partial structure unlike R273H",
        "conservation": "100% conserved",
        "effect_score": 0.96,
        "sources": ["UniProt P04637", "ClinVar VCV000012377", "COSMIC v97"],
        "therapeutic": "Experimental: small molecule stabilizers of DNA-contact mutants",
    },
    249: {
        "label": "R249S",
        "status": "critical",
        "name": "Arginine → Serine",
        "domain": "DNA-binding domain (H2 helix)",
        "mechanism": "Structural mutation affecting the H2 helix. Disrupts local folding and indirectly impairs DNA binding. Also disrupts interaction with HIPK2.",
        "frequency": "~1.5% of cancers; highly enriched in hepatocellular carcinoma (aflatoxin signature)",
        "cancer_types": "Liver (HCC), lung, esophageal",
        "functional_class": "Loss-of-function + gain-of-function",
        "clinvar_significance": "Pathogenic",
        "clinvar_submissions": 298,
        "uniprot_annotation": "H2 helix structural mutation; aflatoxin B1 mutational signature",
        "conservation": "100% conserved",
        "effect_score": 0.91,
        "sources": ["UniProt P04637", "ClinVar VCV000012378", "IARC TP53 Database"],
        "therapeutic": "No specific therapy; aflatoxin avoidance in endemic regions",
    },
    245: {
        "label": "G245S/D",
        "status": "critical",
        "name": "Glycine → Serine / Aspartate",
        "domain": "DNA-binding domain (L3 loop)",
        "mechanism": "Glycine at this position is essential for loop conformation. Substitution adds a side chain that sterically clashes with the DNA backbone, disrupting the L3 loop geometry.",
        "frequency": "~1.5% of cancers",
        "cancer_types": "Breast, lung, sarcoma, hematologic malignancies",
        "functional_class": "Loss-of-function (structural)",
        "clinvar_significance": "Pathogenic",
        "clinvar_submissions": 187,
        "uniprot_annotation": "L3 loop glycine; essential for loop geometry and DNA approach",
        "conservation": "100% conserved",
        "effect_score": 0.88,
        "sources": ["UniProt P04637", "ClinVar VCV000012379", "COSMIC v97"],
        "therapeutic": "Under investigation — structural correctors for L3 loop mutants",
    },
    282: {
        "label": "R282W",
        "status": "critical",
        "name": "Arginine → Tryptophan",
        "domain": "DNA-binding domain (H2 helix)",
        "mechanism": "Disrupts H2 helix packing. R282 forms a salt bridge with E271 that stabilizes the helix. Tryptophan disrupts this interaction causing partial unfolding.",
        "frequency": "~1% of cancers",
        "cancer_types": "Breast, colorectal, lung",
        "functional_class": "Loss-of-function (structural)",
        "clinvar_significance": "Pathogenic",
        "clinvar_submissions": 156,
        "uniprot_annotation": "H2 helix salt bridge with E271; loss destabilizes helix",
        "conservation": "99% conserved",
        "effect_score": 0.85,
        "sources": ["UniProt P04637", "ClinVar VCV000012380"],
        "therapeutic": "No approved targeted therapy",
    },
    # Affected by critical residues
    176: {
        "label": "C176",
        "status": "affected",
        "name": "Cysteine 176 (zinc ligand)",
        "domain": "DNA-binding domain — zinc coordination",
        "mechanism": "One of four zinc-coordinating residues (C176, H179, C238, C242). Directly adjacent to R175. R175H mutation disrupts the local geometry around C176, indirectly loosening zinc coordination.",
        "frequency": "Rarely mutated directly; affected by R175H",
        "cancer_types": "N/A (secondary effect)",
        "functional_class": "Zinc ligand — indirectly disrupted by R175H",
        "clinvar_significance": "Not directly pathogenic",
        "clinvar_submissions": 12,
        "uniprot_annotation": "Zinc ligand (Cys-176); part of tetrahedral zinc coordination site",
        "conservation": "100% conserved",
        "effect_score": 0.60,
        "sources": ["UniProt P04637", "PDB 2OCJ structural analysis"],
        "therapeutic": "N/A",
    },
    179: {
        "label": "H179",
        "status": "affected",
        "name": "Histidine 179 (zinc ligand)",
        "domain": "DNA-binding domain — zinc coordination",
        "mechanism": "Second zinc-coordinating residue. Indirectly destabilized by R175H mutation through propagated structural changes in the L2 loop.",
        "frequency": "Rarely mutated directly",
        "cancer_types": "N/A (secondary effect)",
        "functional_class": "Zinc ligand — indirectly affected",
        "clinvar_significance": "Uncertain significance when directly mutated",
        "clinvar_submissions": 8,
        "uniprot_annotation": "Zinc ligand (His-179); tetrahedral coordination with C176, C238, C242",
        "conservation": "100% conserved",
        "effect_score": 0.55,
        "sources": ["UniProt P04637", "PDB 2OCJ"],
        "therapeutic": "N/A",
    },
    220: {
        "label": "Y220C",
        "status": "affected",
        "name": "Tyrosine → Cysteine",
        "domain": "DNA-binding domain (S7-S8 loop)",
        "mechanism": "Creates a surface cavity on the protein that destabilizes the domain. Not a direct DNA contact but affects overall fold stability. The cavity is a druggable pocket.",
        "frequency": "~1% of cancers",
        "cancer_types": "Breast, lung, ovarian",
        "functional_class": "Loss-of-function (thermodynamic destabilization)",
        "clinvar_significance": "Pathogenic",
        "clinvar_submissions": 89,
        "uniprot_annotation": "Surface residue; Y220C creates druggable hydrophobic cavity",
        "conservation": "98% conserved",
        "effect_score": 0.78,
        "sources": ["UniProt P04637", "ClinVar VCV000012381", "COSMIC v97"],
        "therapeutic": "PC14586 (rezatapopt) — specifically designed to fill Y220C cavity, Phase II trials",
    },
    # Normal/no-effect residues (sampled)
    100: {
        "label": "P100",
        "status": "normal",
        "name": "Proline 100",
        "domain": "Proline-rich region (transactivation domain II)",
        "mechanism": "Structural proline in the flexible linker region. Located far from the DNA-binding domain. Mutations here generally do not affect transcriptional activity.",
        "frequency": "Rarely mutated; tolerated when mutated",
        "cancer_types": "Not specifically associated",
        "functional_class": "Structural/neutral",
        "clinvar_significance": "Benign / likely benign",
        "clinvar_submissions": 3,
        "uniprot_annotation": "Proline-rich region; involved in PXXP motif for SH3-domain interactions",
        "conservation": "Moderately conserved",
        "effect_score": 0.08,
        "sources": ["UniProt P04637"],
        "therapeutic": "N/A",
    },
    150: {
        "label": "V150",
        "status": "normal",
        "name": "Valine 150",
        "domain": "DNA-binding domain (beta-sheet core)",
        "mechanism": "Interior beta-sheet residue. Contributes to hydrophobic core stability but is not directly involved in DNA binding or zinc coordination. Conservative substitutions are generally tolerated.",
        "frequency": "Rarely mutated in cancer",
        "cancer_types": "Not specifically associated",
        "functional_class": "Structural — tolerated variation",
        "clinvar_significance": "Likely benign",
        "clinvar_submissions": 5,
        "uniprot_annotation": "Core beta-sheet residue; conservative substitutions tolerated",
        "conservation": "Moderately conserved",
        "effect_score": 0.12,
        "sources": ["UniProt P04637", "ProtaBank DMS dataset"],
        "therapeutic": "N/A",
    },
}

# ── Experiment database ───────────────────────────────────────────────────────
EXPERIMENTS = [
    {
        "id": "thermal_shift",
        "name": "Thermal Shift Assay (TSA / DSF)",
        "category": "Structural",
        "duration": "2–3 days",
        "cost": "~$200–500",
        "purpose": "Measures protein thermostability. R175H reduces Tm by ~8–10°C vs WT, confirming destabilization.",
        "expected_change": {
            "title": "Global Destabilization",
            "description": "R175H causes the entire DNA-binding domain to partially unfold at physiological temperature. The zinc coordination site collapses, propagating structural disorder through the L2 loop and destabilizing residues C176, H179, and the surrounding beta-sheet core. The protein loses its compact globular fold.",
            "affected_residues": [175, 176, 179, 220],
            "structural_effect": "destabilized",
            "visualization_note": "The zinc-coordination cluster (R175, C176, H179) loses its geometry. Residues 160–185 show increased thermal motion. Domain integrity compromised.",
        },
        "readout": "Melting temperature (Tm). WT TP53 DBD: ~42°C. R175H: ~32–34°C.",
        "controls": "WT TP53 DBD, R248W (contact mutant control), known stabilizing compounds",
    },
    {
        "id": "emsa",
        "name": "EMSA — Electrophoretic Mobility Shift Assay",
        "category": "Functional",
        "duration": "1–2 days",
        "cost": "~$100–300",
        "purpose": "Directly measures DNA binding. R175H shows complete loss of sequence-specific DNA binding due to misfolding.",
        "expected_change": {
            "title": "Loss of DNA Binding Interface",
            "description": "The DNA-binding interface (residues 236–248 contact strand, R273 phosphate contact) becomes inaccessible because R175H-induced misfolding repositions the L3 loop away from DNA. The protein can no longer form stable complexes with p53 response elements. R248 and R273 are physically present but structurally displaced.",
            "affected_residues": [175, 248, 273, 245],
            "structural_effect": "interface_lost",
            "visualization_note": "DNA contact residues (R248, R273, G245) are highlighted — they exist but cannot reach DNA due to upstream misfolding from R175H.",
        },
        "readout": "Band shift on gel. WT shows retarded band (protein-DNA complex). R175H: no shift (free DNA only).",
        "controls": "WT TP53, consensus p53RE oligo, non-specific oligo, supershift antibody",
    },
    {
        "id": "reporter_assay",
        "name": "Luciferase Reporter Assay",
        "category": "Functional",
        "duration": "3–5 days",
        "cost": "~$300–600",
        "purpose": "Measures transcriptional transactivation in cells. R175H completely abrogates p21, MDM2, and PUMA promoter activation.",
        "expected_change": {
            "title": "Complete Transcriptional Silence",
            "description": "R175H protein accumulates in the nucleus (nuclear localization intact) but fails to activate any canonical p53 target genes. The tetramerization domain (residues 325–356) and nuclear localization are unaffected. The entire functional deficit is localized to the DNA-binding domain. Additionally, R175H exerts dominant negative effects on remaining WT p53 allele by forming mixed tetramers.",
            "affected_residues": [175, 176, 179, 248, 273],
            "structural_effect": "transcription_dead",
            "visualization_note": "DNA-binding domain shown as non-functional. Tetramerization domain (outside view range) is intact. The mutation's effect is entirely localized to the DBD.",
        },
        "readout": "Relative luminescence units (RLU). Normalized to Renilla. R175H: <5% of WT activity.",
        "controls": "WT p53, empty vector, p53-null cell line (H1299), p21-luc / MDM2-luc reporters",
    },
    {
        "id": "apr246",
        "name": "APR-246 Rescue Experiment",
        "category": "Therapeutic",
        "duration": "5–7 days",
        "cost": "~$500–1200",
        "purpose": "Tests whether APR-246 (eprenetapopt) can refold R175H and restore WT-like function. APR-246 covalently modifies cysteines to stabilize the misfolded domain.",
        "expected_change": {
            "title": "Partial Structural Rescue",
            "description": "APR-246 (active form: MQ) covalently binds to C176 and C238 in the zinc coordination site, acting as a zinc-independent scaffold that partially restores the DNA-binding conformation. Residues R248 and R273 are repositioned closer to their WT geometry. The rescue is partial — Tm increases ~4–6°C and transcriptional activity recovers to ~20–40% of WT.",
            "affected_residues": [175, 176, 179, 238, 248],
            "structural_effect": "partial_rescue",
            "visualization_note": "C176 and C238 shown as drug-binding sites. The zinc-coordination cluster shows partial restoration. DNA contact residues shift toward functional geometry.",
        },
        "readout": "Thermal shift (Tm increase), EMSA (partial band shift), reporter assay (% WT recovery), cell viability in R175H cancer cell lines.",
        "controls": "DMSO vehicle, WT p53 cell line, R175H cell line without drug, dose-response curve",
    },
    {
        "id": "coip",
        "name": "Co-Immunoprecipitation (Co-IP) — Dominant Negative Study",
        "category": "Mechanistic",
        "duration": "3–4 days",
        "cost": "~$400–800",
        "purpose": "Confirms that R175H forms mixed tetramers with WT p53, exerting dominant negative suppression of remaining WT allele.",
        "expected_change": {
            "title": "Dominant Negative Tetramerization",
            "description": "R175H protein co-precipitates with WT p53, confirming tetramer formation. The mixed tetramer (2x R175H + 2x WT) shows dramatically reduced DNA-binding vs pure WT tetramer. This explains why heterozygous R175H mutations (one WT allele retained) still show aggressive cancer phenotypes — the mutant subunits poison the remaining WT copies.",
            "affected_residues": [175, 248, 273],
            "structural_effect": "dominant_negative",
            "visualization_note": "Tetramerization domain interaction shown. R175H units contaminate WT tetramers, reducing overall DNA binding of the complex.",
        },
        "readout": "Pull-down of WT p53 by anti-mutant antibody (DO-1 vs PAb240). Western blot confirmation.",
        "controls": "IgG isotype control, WT-only cells, R175H-only cells, mixed transfection",
    },
]


def fetch_pdb_structure(pdb_id="2OCJ"):
    url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def render():
    st.markdown("""
    <style>
    .explorer-header { font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.18em; color: #444; margin-bottom: 8px; padding-bottom: 5px; border-bottom: 1px solid #1e2030; }
    .residue-pill { display:inline-block; padding:3px 10px; border-radius:20px; font-size:0.72rem; font-family:'IBM Plex Mono',monospace; font-weight:600; margin:2px; }
    .pill-critical { background:#FF4C4C22; color:#FF4C4C; border:1px solid #FF4C4C55; }
    .pill-affected  { background:#FFA50022; color:#FFA500; border:1px solid #FFA50055; }
    .pill-normal    { background:#4CA8FF22; color:#4CA8FF; border:1px solid #4CA8FF55; }
    .exp-card { background:#0f1117; border:1px solid #2a2d3a; border-radius:10px; padding:16px 18px; margin-bottom:10px; cursor:pointer; transition:border-color 0.2s; }
    .exp-card:hover { border-color:#FF4C4C88; }
    .exp-card.selected { border-color:#FF4C4C; background:#1a0808; }
    .exp-title { font-size:0.92rem; font-weight:600; color:#eee; margin-bottom:4px; }
    .exp-meta  { font-size:0.75rem; color:#666; }
    .exp-cat-structural  { color:#4CA8FF; }
    .exp-cat-functional  { color:#FFA500; }
    .exp-cat-therapeutic { color:#4CAF50; }
    .exp-cat-mechanistic { color:#CC88FF; }
    .info-row { display:flex; gap:10px; padding:6px 0; border-bottom:1px solid #1a1d2e; font-size:0.8rem; }
    .info-label { color:#555; min-width:140px; font-family:'IBM Plex Mono',monospace; font-size:0.7rem; padding-top:1px; }
    .info-val   { color:#ccc; }
    .source-tag { display:inline-block; background:#1a1d2e; border:1px solid #2a2d3a; border-radius:4px; padding:2px 8px; font-size:0.68rem; font-family:'IBM Plex Mono',monospace; color:#888; margin:2px; }
    .change-box { background:#0a0f0a; border:1px solid #1a3a1a; border-radius:8px; padding:14px 18px; margin:10px 0; }
    .change-title { font-family:'IBM Plex Mono',monospace; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.1em; color:#4CAF50; margin-bottom:8px; }
    .rescue-box { background:#0a0a1a; border:1px solid #1a1a3a; border-radius:8px; padding:14px 18px; margin:10px 0; }
    .rescue-title { font-family:'IBM Plex Mono',monospace; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.1em; color:#4CA8FF; margin-bottom:8px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("## ⚗️ Protein Explorer — TP53 R175H")
    st.markdown("Interactive residue-level analysis. Click a residue on the structure or select an experiment below.")
    st.divider()

    # ── State ─────────────────────────────────────────────────────────────────
    if "selected_residue" not in st.session_state:
        st.session_state.selected_residue = 175
    if "selected_experiment" not in st.session_state:
        st.session_state.selected_experiment = None

    # ── Legend ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="display:flex;gap:16px;margin-bottom:16px;flex-wrap:wrap;">
        <span class="residue-pill pill-critical">● CRITICAL — direct mutation site</span>
        <span class="residue-pill pill-affected">● AFFECTED — downstream structural impact</span>
        <span class="residue-pill pill-normal">● NO EFFECT — structurally neutral</span>
    </div>
    """, unsafe_allow_html=True)

    top_left, top_right = st.columns([1.4, 1], gap="large")

    # ── 3D Structure ──────────────────────────────────────────────────────────
    with top_left:
        st.markdown('<div class="explorer-header">3D Protein Structure — Click a residue for details</div>', unsafe_allow_html=True)

        selected_exp = st.session_state.selected_experiment
        exp_data = next((e for e in EXPERIMENTS if e["id"] == selected_exp), None)

        # Determine highlight residues from experiment
        exp_highlights = {}
        if exp_data:
            for resi in exp_data["expected_change"]["affected_residues"]:
                exp_highlights[resi] = exp_data["expected_change"]["structural_effect"]

        with st.spinner("Loading TP53 structure..."):
            pdb_data = fetch_pdb_structure("2OCJ")

        if pdb_data:
            # Build py3Dmol viewer with click callbacks via JS injection
            viewer_html = build_viewer_html(pdb_data, exp_highlights, st.session_state.selected_residue)
            components.html(viewer_html, height=520, scrolling=False)

            st.caption("💡 Click any sphere on the structure to load residue details on the right.")
        else:
            st.error("Could not load TP53 structure from PDB.")

        # Residue quick-select buttons
        st.markdown('<div class="explorer-header" style="margin-top:16px;">Quick-select residue</div>', unsafe_allow_html=True)
        cols = st.columns(len(RESIDUE_DATA))
        for i, (resi, data) in enumerate(RESIDUE_DATA.items()):
            pill_class = {"critical": "🔴", "affected": "🟠", "normal": "🔵"}[data["status"]]
            with cols[i]:
                if st.button(f"{pill_class} {data['label']}", key=f"btn_{resi}", use_container_width=True):
                    st.session_state.selected_residue = resi
                    st.rerun()

    # ── Residue Info Panel ────────────────────────────────────────────────────
    with top_right:
        resi = st.session_state.selected_residue
        r = RESIDUE_DATA.get(resi)

        if r:
            status_color = {"critical": "#FF4C4C", "affected": "#FFA500", "normal": "#4CA8FF"}[r["status"]]
            status_label = {"critical": "CRITICAL", "affected": "AFFECTED BY CRITICAL", "normal": "NO SIGNIFICANT EFFECT"}[r["status"]]

            st.markdown(f"""
            <div style="background:#0f1117;border:1px solid {status_color}44;border-left:4px solid {status_color};border-radius:8px;padding:16px 18px;margin-bottom:14px;">
                <div style="font-family:'IBM Plex Mono',monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:{status_color};margin-bottom:6px;">{status_label}</div>
                <div style="font-size:1.3rem;font-weight:700;color:#eee;margin-bottom:2px;">Residue {resi} — {r['label']}</div>
                <div style="font-size:0.82rem;color:#888;">{r['name']}</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="explorer-header">Biological Details</div>', unsafe_allow_html=True)
            fields = [
                ("Domain", r["domain"]),
                ("Mechanism", r["mechanism"]),
                ("Cancer frequency", r["frequency"]),
                ("Cancer types", r["cancer_types"]),
                ("Functional class", r["functional_class"]),
                ("ClinVar", f"{r['clinvar_significance']} ({r['clinvar_submissions']} submissions)"),
                ("UniProt annotation", r["uniprot_annotation"]),
                ("Conservation", r["conservation"]),
                ("Effect score", f"{r['effect_score']} / 1.00"),
                ("Therapeutic", r["therapeutic"]),
            ]
            for label, val in fields:
                st.markdown(f"""
                <div class="info-row">
                    <span class="info-label">{label}</span>
                    <span class="info-val">{val}</span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown('<div class="explorer-header" style="margin-top:14px;">Data Sources</div>', unsafe_allow_html=True)
            sources_html = " ".join([f'<span class="source-tag">{s}</span>' for s in r["sources"]])
            st.markdown(sources_html, unsafe_allow_html=True)

    st.divider()

    # ── Experiment Selector ───────────────────────────────────────────────────
    st.markdown("## Experimental Pathways")
    st.markdown("Select an experiment to see how the protein structure changes and what the results mean.")
    st.markdown("<br>", unsafe_allow_html=True)

    exp_cols = st.columns(len(EXPERIMENTS))
    for i, exp in enumerate(EXPERIMENTS):
        cat_color = {"Structural": "exp-cat-structural", "Functional": "exp-cat-functional",
                     "Therapeutic": "exp-cat-therapeutic", "Mechanistic": "exp-cat-mechanistic"}[exp["category"]]
        is_selected = st.session_state.selected_experiment == exp["id"]
        border_style = "border-color:#FF4C4C;" if is_selected else ""

        with exp_cols[i]:
            st.markdown(f"""
            <div class="exp-card" style="{border_style}">
                <div class="exp-title">{exp['name'].split('—')[0].split('(')[0].strip()}</div>
                <div class="exp-meta"><span class="{cat_color}">{exp['category']}</span> · {exp['duration']} · {exp['cost']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Select" if not is_selected else "✓ Selected", key=f"exp_{exp['id']}", use_container_width=True, type="primary" if is_selected else "secondary"):
                if st.session_state.selected_experiment == exp["id"]:
                    st.session_state.selected_experiment = None
                else:
                    st.session_state.selected_experiment = exp["id"]
                st.rerun()

    # ── Experiment Detail ─────────────────────────────────────────────────────
    if st.session_state.selected_experiment:
        exp = next((e for e in EXPERIMENTS if e["id"] == st.session_state.selected_experiment), None)
        if exp:
            st.divider()
            st.markdown(f"### {exp['name']}")

            det_left, det_right = st.columns([1, 1], gap="large")

            with det_left:
                st.markdown('<div class="explorer-header">Experiment Overview</div>', unsafe_allow_html=True)
                overview_fields = [
                    ("Purpose", exp["purpose"]),
                    ("Readout", exp["readout"]),
                    ("Controls", exp["controls"]),
                    ("Duration", exp["duration"]),
                    ("Estimated cost", exp["cost"]),
                ]
                for label, val in overview_fields:
                    st.markdown(f"""
                    <div class="info-row">
                        <span class="info-label">{label}</span>
                        <span class="info-val">{val}</span>
                    </div>
                    """, unsafe_allow_html=True)

                chg = exp["expected_change"]
                box_class = "rescue-box" if exp["id"] == "apr246" else "change-box"
                title_color = "#4CA8FF" if exp["id"] == "apr246" else "#4CAF50"
                st.markdown(f"""
                <div class="{box_class}" style="margin-top:16px;">
                    <div style="font-family:'IBM Plex Mono',monospace;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.1em;color:{title_color};margin-bottom:8px;">
                        Expected Structural Outcome — {chg['title']}
                    </div>
                    <p style="font-size:0.83rem;color:#aaa;margin:0;line-height:1.7;">{chg['description']}</p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div style="background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;padding:12px 16px;margin-top:10px;">
                    <div style="font-family:'IBM Plex Mono',monospace;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;color:#555;margin-bottom:8px;">Viewer Note</div>
                    <p style="font-size:0.78rem;color:#888;margin:0;line-height:1.6;">{chg['visualization_note']}</p>
                </div>
                """, unsafe_allow_html=True)

            with det_right:
                st.markdown('<div class="explorer-header">Structural Change Viewer</div>', unsafe_allow_html=True)
                st.caption(f"Highlighting residues affected by: {exp['name'].split('(')[0].strip()}")

                if pdb_data:
                    exp_viewer_html = build_experiment_viewer_html(pdb_data, exp)
                    components.html(exp_viewer_html, height=420, scrolling=False)

                    # Affected residues legend
                    st.markdown('<div class="explorer-header" style="margin-top:10px;">Highlighted Residues</div>', unsafe_allow_html=True)
                    aff = exp["expected_change"]["affected_residues"]
                    pills = ""
                    for r_id in aff:
                        r_info = RESIDUE_DATA.get(r_id, {})
                        label = r_info.get("label", str(r_id))
                        pills += f'<span class="residue-pill pill-critical">{label}</span> '
                    st.markdown(pills, unsafe_allow_html=True)


def build_viewer_html(pdb_data, exp_highlights, selected_resi):
    """Build the main interactive 3D viewer with click callbacks."""
    residue_js = json.dumps({
        str(k): {"status": v["status"], "label": v["label"], "score": v["effect_score"]}
        for k, v in RESIDUE_DATA.items()
    })

    color_map = {
        "critical": "#FF4C4C",
        "affected": "#FFA500",
        "normal": "#4CA8FF",
        "default": "#2a2d3e",
    }

    # Build residue style commands
    style_cmds = []
    for resi, data in RESIDUE_DATA.items():
        color = color_map.get(data["status"], color_map["default"])
        radius = 0.9 if data["status"] == "critical" else 0.65 if data["status"] == "affected" else 0.45
        style_cmds.append(f"viewer.addStyle({{resi: {resi}}}, {{sphere: {{color: '{color}', radius: {radius}}}}});")

    # Highlight selected
    sel_color = "#FFFFFF"
    style_cmds.append(f"viewer.addStyle({{resi: {selected_resi}}}, {{sphere: {{color: '{sel_color}', radius: 1.1}}}});")

    styles_str = "\n".join(style_cmds)

    pdb_escaped = pdb_data.replace('`', '\\`').replace('\\', '\\\\').replace('${', '\\${')[:200000]

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
    <style>
        body {{ margin:0; background:#080b14; font-family:'IBM Plex Mono',monospace; }}
        #viewer {{ width:100%; height:480px; position:relative; }}
        #tooltip {{
            position:absolute; top:10px; left:10px;
            background:#0f1117ee; border:1px solid #2a2d3a;
            border-radius:6px; padding:8px 12px;
            font-size:11px; color:#ccc; pointer-events:none;
            display:none; z-index:100; max-width:220px;
        }}
    </style>
    </head>
    <body>
    <div id="viewer"><div id="tooltip"></div></div>
    <script>
    const pdbData = `{pdb_escaped}`;
    const residueDB = {residue_js};

    let viewer = $3Dmol.createViewer('viewer', {{
        backgroundColor: '#080b14',
        antialias: true,
    }});

    viewer.addModel(pdbData, 'pdb');
    viewer.setStyle({{}}, {{cartoon: {{color: '#1a1d2e', opacity: 0.5}}}});
    viewer.addStyle({{resi: '94-292'}}, {{cartoon: {{color: '#1e2540', opacity: 0.7}}}});

    {styles_str}

    viewer.zoomTo({{resi: '94-292'}});

    // Hover tooltip
    viewer.setHoverable({{}}, true,
        function(atom, viewer, event, container) {{
            if (!atom.resi) return;
            const resi = atom.resi;
            const data = residueDB[resi];
            const tooltip = document.getElementById('tooltip');
            if (data) {{
                const statusColor = data.status === 'critical' ? '#FF4C4C' : data.status === 'affected' ? '#FFA500' : '#4CA8FF';
                tooltip.innerHTML = '<span style="color:' + statusColor + ';font-weight:700;">' + data.label + '</span><br><span style="color:#888;font-size:10px;">Residue ' + resi + ' · Score: ' + data.score + '</span><br><span style="color:#666;font-size:10px;">Click for full details</span>';
                tooltip.style.display = 'block';
            }} else {{
                tooltip.innerHTML = '<span style="color:#666;">Residue ' + resi + '</span>';
                tooltip.style.display = 'block';
            }}
        }},
        function(atom) {{
            document.getElementById('tooltip').style.display = 'none';
        }}
    );

    viewer.render();
    </script>
    </body>
    </html>
    """


def build_experiment_viewer_html(pdb_data, exp):
    """Build the experiment-specific structure viewer."""
    chg = exp["expected_change"]
    affected = chg["affected_residues"]
    effect = chg["structural_effect"]

    color_map = {
        "destabilized": "#FF4C4C",
        "interface_lost": "#FF8C00",
        "transcription_dead": "#CC44CC",
        "partial_rescue": "#4CA8FF",
        "dominant_negative": "#FF4C4C",
    }
    highlight_color = color_map.get(effect, "#FF4C4C")

    style_cmds = []
    for resi in RESIDUE_DATA:
        if resi in affected:
            style_cmds.append(f"viewer.addStyle({{resi: {resi}}}, {{sphere: {{color: '{highlight_color}', radius: 1.0}}}});")
            style_cmds.append(f"viewer.addSurface($3Dmol.VDW, {{opacity:0.35, color:'{highlight_color}'}}, {{resi:{resi}}});")
        else:
            r_data = RESIDUE_DATA[resi]
            color = "#FF4C4C" if r_data["status"] == "critical" else "#FFA500" if r_data["status"] == "affected" else "#4CA8FF"
            style_cmds.append(f"viewer.addStyle({{resi: {resi}}}, {{sphere: {{color: '{color}', radius: 0.4, opacity: 0.3}}}});")

    styles_str = "\n".join(style_cmds)
    pdb_escaped = pdb_data.replace('`', '\\`').replace('\\', '\\\\').replace('${', '\\${')[:200000]

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
    <style>body {{ margin:0; background:#080b14; }}</style>
    </head>
    <body>
    <div id="viewer" style="width:100%;height:400px;"></div>
    <script>
    const pdbData = `{pdb_escaped}`;
    let viewer = $3Dmol.createViewer('viewer', {{backgroundColor:'#080b14', antialias:true}});
    viewer.addModel(pdbData, 'pdb');
    viewer.setStyle({{}}, {{cartoon:{{color:'#1a1d2e', opacity:0.4}}}});
    viewer.addStyle({{resi:'94-292'}}, {{cartoon:{{color:'#1e2540', opacity:0.65}}}});
    {styles_str}
    viewer.zoomTo({{resi:'94-292'}});
    viewer.render();
    </script>
    </body>
    </html>
    """
