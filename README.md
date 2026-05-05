from __future__ import annotations
"""
Sidebar — protein search, assay input, disease ranking, experiment list.
"""

import streamlit as st
import pandas as pd


def _severity_badge(level: str) -> str:
    return f"<span class='badge-{level.lower()}'>{level.upper()}</span>"


def render_sidebar(clients: dict) -> dict:
    """Render full sidebar; returns dict of search parameters."""

    st.sidebar.markdown("""
    <div style='text-align:center; padding:1rem 0 0.5rem;'>
      <span style='font-size:2rem;'>🧬</span>
      <h2 style='color:#00d4ff; margin:0; font-size:1.4rem;'>Protellect</h2>
      <p style='color:#5a7a9a; font-size:0.78rem; margin:0;'>Protein Intelligence Platform</p>
    </div>
    <hr style='border-color:#1e3a5f; margin:0.8rem 0;'>
    """, unsafe_allow_html=True)

    # ── Tutorial toggle ──────────────────────────────────────────────────────
    st.session_state["tutorial_mode"] = st.sidebar.toggle(
        "📖 Tutorial Mode", value=st.session_state.get("tutorial_mode", False)
    )

    # ── Protein search ───────────────────────────────────────────────────────
    st.sidebar.markdown("### 🔍 Protein Search")
    protein_query = st.sidebar.text_input(
        "Gene / Protein / UniProt ID",
        value=st.session_state.get("protein_id", ""),
        placeholder="e.g. TP53 · BRCA1 · P04637",
        help="Enter a gene symbol, protein name, or UniProt accession.",
    )

    search_clicked = st.sidebar.button("🔬 Analyse Protein", use_container_width=True)

    # ── Wet-lab assay input ──────────────────────────────────────────────────
    st.sidebar.markdown("### 🧫 Wet-Lab Assay Results *(optional)*")
    assay_text = st.sidebar.text_area(
        "Paste assay description / results",
        height=120,
        placeholder="e.g. Western blot shows reduced expression in HEK293T upon CRISPR knockout…",
    )

    # ── Data size preference ─────────────────────────────────────────────────
    st.sidebar.markdown("### ⚙️ Analysis Settings")
    data_depth = st.sidebar.selectbox(
        "Data depth",
        ["Standard (fast)", "Comprehensive (all variants)", "Deep — ML enriched"],
        index=0,
    )
    max_variants = {"Standard (fast)": 50, "Comprehensive (all variants)": 500, "Deep — ML enriched": 500}[data_depth]

    # ── Sidebar summary (shown after data is loaded) ─────────────────────────
    pdata = st.session_state.get("protein_data")
    cv    = st.session_state.get("clinvar_data")
    ml    = st.session_state.get("ml_scores")

    if pdata:
        gene  = st.session_state.get("gene_name", "—")
        uid   = pdata.get("primaryAccession", "—")
        fname = pdata.get("proteinDescription", {}) \
                     .get("recommendedName", {}) \
                     .get("fullName", {}).get("value", "—")

        st.sidebar.markdown(f"""
        <hr style='border-color:#1e3a5f; margin:1rem 0 0.5rem;'>
        <div style='background:#0a1929; border:1px solid #1e3a5f; border-radius:8px; padding:1rem;'>
          <p style='color:#00d4ff; font-weight:700; margin:0 0 4px;'>{gene}</p>
          <p style='color:#8ab4d4; font-size:0.78rem; margin:0 0 2px;'>{fname}</p>
          <p style='color:#5a7a9a; font-size:0.74rem; margin:0;'>UniProt: {uid}</p>
        </div>
        """, unsafe_allow_html=True)

        # Disease breakdown with ranking
        _render_disease_ranking(pdata, cv, ml)

        # Assay interpretation
        if assay_text and assay_text.strip():
            _render_assay_interpretation(assay_text)

        # Experiment quick-list
        _render_experiment_quicklist(pdata, cv, ml)

    return {
        "protein_query": protein_query if search_clicked else st.session_state.get("last_searched", ""),
        "assay_text":    assay_text,
        "max_variants":  max_variants,
    }


# ─── Disease ranking ─────────────────────────────────────────────────────────
def _render_disease_ranking(pdata: dict, cv: dict | None, ml: dict | None):
    st.sidebar.markdown("""
    <hr style='border-color:#1e3a5f; margin:0.8rem 0 0.4rem;'>
    <p style='color:#00d4ff; font-weight:600; margin:0 0 0.5rem; font-size:0.95rem;'>
      🏥 Disease Affiliations
    </p>
    """, unsafe_allow_html=True)

    diseases = _extract_diseases_from_uniprot(pdata)
    cv_diseases = _extract_cv_diseases(cv)
    all_diseases = {**diseases, **cv_diseases}

    if not all_diseases:
        st.sidebar.caption("No disease associations found.")
        return

    # Rank by ML pathogenicity score or ClinVar significance
    ranked = _rank_diseases(all_diseases, ml)

    for item in ranked:
        colour_map = {
            "CRITICAL": "#ff2d55", "HIGH": "#ff6b00",
            "MEDIUM": "#ffd60a",   "NEUTRAL": "#636e72",
        }
        clr   = colour_map.get(item["rank"], "#636e72")
        lbl   = item["rank"]
        txt   = item["label"]
        st.sidebar.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;margin:4px 0;'>"
            f"<span style='background:{clr};color:{'#000' if lbl=='MEDIUM' else '#fff'};"
            f"padding:2px 8px;border-radius:12px;font-size:0.7rem;font-weight:700;"
            f"white-space:nowrap;'>{lbl}</span>"
            f"<span style='color:#c9d8e8;font-size:0.8rem;'>{txt}</span></div>",
            unsafe_allow_html=True,
        )


def _extract_diseases_from_uniprot(pdata: dict) -> dict:
    out = {}
    for comment in pdata.get("comments", []):
        if comment.get("commentType") == "DISEASE":
            d = comment.get("disease", {})
            name = d.get("diseaseId", d.get("diseaseAcronym", "Unknown disease"))
            desc = d.get("description", "")
            out[name] = desc
    return out


def _extract_cv_diseases(cv: dict | None) -> dict:
    if not cv:
        return {}
    out = {}
    for v in cv.get("variants", []):
        cond = v.get("condition", "")
        sig  = v.get("clinical_significance", "")
        if cond and cond not in out:
            out[cond] = sig
    return out


def _rank_diseases(diseases: dict, ml: dict | None) -> list:
    path_scores = (ml or {}).get("disease_scores", {})
    ranked = []
    for name, desc in diseases.items():
        score = path_scores.get(name, 0.5)
        if score >= 0.85:
            rank = "CRITICAL"
        elif score >= 0.65:
            rank = "HIGH"
        elif score >= 0.40:
            rank = "MEDIUM"
        else:
            rank = "NEUTRAL"
        # Keyword boost
        low = (name + " " + desc).lower()
        if any(k in low for k in ["carcinoma", "cancer", "leukemia", "sarcoma", "glioma"]):
            if rank == "MEDIUM":
                rank = "HIGH"
        ranked.append({"label": name, "rank": rank, "score": score})

    order = ["CRITICAL", "HIGH", "MEDIUM", "NEUTRAL"]
    ranked.sort(key=lambda x: (order.index(x["rank"]), -x["score"]))
    return ranked


# ─── Assay interpretation ─────────────────────────────────────────────────────
def _render_assay_interpretation(assay_text: str):
    st.sidebar.markdown("""
    <hr style='border-color:#1e3a5f; margin:0.8rem 0 0.4rem;'>
    <p style='color:#00c896; font-weight:600; margin:0 0 0.5rem; font-size:0.95rem;'>
      🧫 Assay Interpretation
    </p>
    """, unsafe_allow_html=True)

    text_lower = assay_text.lower()
    findings = []

    kw_map = [
        (["western blot", "wb", "expression"],  "Expression change detected via Western blot"),
        (["knockout", "crispr", "cas9"],         "Loss-of-function model via CRISPR"),
        (["knockdown", "shrna", "sirna"],         "Partial knockdown — consider dosage effects"),
        (["overexpression", "overexpress"],       "Gain-of-function overexpression model"),
        (["binding", "pull-down", "co-ip"],       "Protein–protein interaction data present"),
        (["phosphorylation", "phospho"],          "Post-translational modification (phospho) detected"),
        (["apoptosis", "caspase"],                "Apoptotic pathway involvement"),
        (["cell viability", "mtt", "proliferation"], "Cell viability / proliferation assay"),
        (["flow cytometry", "facs"],              "Flow cytometry — cell population data"),
        (["sequencing", "seq", "mutation"],       "Sequencing / mutation data embedded"),
        (["in vivo", "mouse", "xenograft"],       "In vivo model data present"),
    ]

    for kws, label in kw_map:
        if any(k in text_lower for k in kws):
            findings.append(label)

    if not findings:
        findings = ["Free-text assay entered — manual review advised"]

    for f in findings:
        st.sidebar.markdown(
            f"<div style='display:flex;align-items:center;gap:6px;margin:3px 0;'>"
            f"<span style='color:#00c896;font-size:1rem;'>✓</span>"
            f"<span style='color:#c9d8e8;font-size:0.82rem;'>{f}</span></div>",
            unsafe_allow_html=True,
        )


# ─── Experiment quick-list ────────────────────────────────────────────────────
def _render_experiment_quicklist(pdata: dict, cv: dict | None, ml: dict | None):
    st.sidebar.markdown("""
    <hr style='border-color:#1e3a5f; margin:0.8rem 0 0.4rem;'>
    <p style='color:#ffd60a; font-weight:600; margin:0 0 0.5rem; font-size:0.95rem;'>
      🔭 Suggested Pathways & Experiments
    </p>
    """, unsafe_allow_html=True)

    protein_type = _infer_protein_type(pdata)
    suggestions  = _suggest_experiments(protein_type, cv, ml)

    for s in suggestions[:6]:
        st.sidebar.markdown(
            f"<div style='display:flex;align-items:flex-start;gap:6px;margin:4px 0;'>"
            f"<span style='color:#ffd60a;margin-top:2px;'>▸</span>"
            f"<span style='color:#c9d8e8;font-size:0.8rem;'>{s}</span></div>",
            unsafe_allow_html=True,
        )


def _infer_protein_type(pdata: dict) -> str:
    keywords = [kw.get("value", "").lower() for kw in pdata.get("keywords", [])]
    if any("kinase" in k for k in keywords):       return "kinase"
    if any("transcription" in k for k in keywords): return "transcription_factor"
    if any("receptor" in k for k in keywords):      return "receptor"
    if any("gpcr" in k or "g-protein" in k for k in keywords): return "gpcr"
    if any("protease" in k for k in keywords):      return "protease"
    if any("dna" in k for k in keywords):           return "dna_binding"
    return "general"


def _suggest_experiments(ptype: str, cv: dict | None, ml: dict | None) -> list:
    base = {
        "kinase": [
            "Kinase activity assay (ADP-Glo™)",
            "In vitro phosphorylation screen with substrate panel",
            "Co-immunoprecipitation for upstream activators",
            "AlphaFold-guided ATP-pocket mutagenesis",
            "CDK inhibitor sensitivity profiling",
            "FRET-based conformational dynamics",
        ],
        "transcription_factor": [
            "ChIP-seq for genome-wide binding sites",
            "EMSA for DNA-binding domain variants",
            "Luciferase reporter assay (target promoters)",
            "CRISPR activation / inhibition screen",
            "RNA-seq post-knockdown for target gene set",
            "Domain-swap experiments with AF2 guidance",
        ],
        "receptor": [
            "Ligand-binding assay (SPR / ITC)",
            "Calcium flux assay for receptor activation",
            "β-arrestin recruitment (HTRF / BRET)",
            "Receptor trafficking & internalisation imaging",
            "Mutant receptor functional rescue assay",
            "Proximity ligation assay for signalling complex",
        ],
        "gpcr": [
            "cAMP accumulation assay (HTRF)",
            "β-arrestin recruitment (BRET2)",
            "Radioligand binding (competitive displacement)",
            "FACS-based cell surface expression",
            "Biased agonism profiling",
            "Cryo-EM structure of active vs inactive state",
        ],
        "dna_binding": [
            "EMSA for wild-type vs mutant binding affinity",
            "ChIP-qPCR for target loci",
            "Comet assay for DNA damage role",
            "Proximity ligation with repair machinery",
            "ATAC-seq for chromatin accessibility changes",
            "Structural modelling of DNA-contact residues",
        ],
        "general": [
            "Co-immunoprecipitation proteomics (AP-MS)",
            "Subcellular localisation (confocal immunofluorescence)",
            "CRISPR knockout viability screen",
            "Mass-spec post-translational modification mapping",
            "Thermal shift assay for small-molecule screening",
            "RNA-seq for transcriptional response",
        ],
    }
    return base.get(ptype, base["general"])
