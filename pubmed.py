"""
Protellect — AI-powered protein triage & experimental guidance platform.
Entry point: run with `streamlit run app.py`
"""

import streamlit as st
import pandas as pd

from utils.uniprot import UniProtClient
from utils.clinvar import ClinVarClient
from utils.alphafold import AlphaFoldClient
from utils.pubmed import PubMedClient
from utils.ncbi import NCBIClient
from utils.ml_model import ProteinMLModel
from tabs.tab1_triage import render_triage_tab
from tabs.tab2_case_study import render_case_study_tab
from tabs.tab3_explorer import render_explorer_tab
from tabs.tab4_experiments import render_experiments_tab
from components.sidebar import render_sidebar

# ─── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Protellect",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .protellect-header {
    background: linear-gradient(135deg, #0d1117 0%, #0a2a4a 50%, #0d1117 100%);
    padding: 1.5rem 2rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    border: 1px solid #1e3a5f;
  }
  .protellect-header h1 {
    color: #00d4ff;
    font-size: 2.4rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.5px;
  }
  .protellect-header p {
    color: #8ab4d4;
    margin: 0.3rem 0 0;
    font-size: 1rem;
  }

  .badge-critical { background:#ff2d55; color:white; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:700; }
  .badge-high     { background:#ff6b00; color:white; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:700; }
  .badge-medium   { background:#ffd60a; color:#111; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:700; }
  .badge-neutral  { background:#636e72; color:white; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:700; }

  .card {
    background: #0f1923;
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
  }
  .card h4 { color: #00d4ff; margin: 0 0 0.5rem; }
  .card p  { color: #c9d8e8; margin: 0; font-size: 0.9rem; }

  .metric-box {
    background: linear-gradient(135deg, #0a2a4a, #0d1117);
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
  }
  .metric-box .val { font-size: 1.8rem; font-weight: 700; color: #00d4ff; }
  .metric-box .lbl { font-size: 0.78rem; color: #8ab4d4; margin-top: 4px; }

  .stTabs [data-baseweb="tab-list"] {
    background: #0d1117;
    border-bottom: 2px solid #1e3a5f;
  }
  .stTabs [data-baseweb="tab"] {
    color: #8ab4d4 !important;
    font-weight: 600;
    padding: 0.6rem 1.2rem;
  }
  .stTabs [aria-selected="true"] {
    color: #00d4ff !important;
    border-bottom: 2px solid #00d4ff;
  }

  div[data-testid="stSidebar"] {
    background: #080e16;
    border-right: 1px solid #1e3a5f;
  }

  .citation-box {
    background: #0a1929;
    border-left: 3px solid #00d4ff;
    padding: 0.7rem 1rem;
    border-radius: 0 8px 8px 0;
    margin: 0.5rem 0;
    font-size: 0.82rem;
    color: #8ab4d4;
  }
  .citation-box a { color: #00d4ff; text-decoration: none; }

  .tutorial-box {
    background: #0a2a1a;
    border: 1px solid #00c896;
    border-radius: 10px;
    padding: 1rem 1.5rem;
    margin-bottom: 1rem;
  }
  .tutorial-box h4 { color: #00c896; margin: 0 0 0.5rem; }
  .tutorial-box p  { color: #b2e4d0; font-size: 0.88rem; margin: 0; }

  .stButton>button {
    background: linear-gradient(90deg, #00d4ff, #0090ff);
    color: #000;
    border: none;
    font-weight: 700;
    border-radius: 8px;
    padding: 0.5rem 1.5rem;
    transition: opacity 0.2s;
  }
  .stButton>button:hover { opacity: 0.85; }

  hr.divider { border-color: #1e3a5f; margin: 1.5rem 0; }
</style>
""", unsafe_allow_html=True)

# ─── Header ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="protellect-header">
  <h1>🧬 Protellect</h1>
  <p>AI-powered protein triage · Eliminate wasted experiments · Follow the science</p>
</div>
""", unsafe_allow_html=True)

# ─── Session state initialisation ───────────────────────────────────────────
defaults = {
    "protein_data": None,
    "clinvar_data": None,
    "alphafold_pdb": None,
    "variants": None,
    "papers": None,
    "ml_scores": None,
    "protein_id": "",
    "gene_name": "",
    "assay_data": "",
    "tutorial_mode": False,
    "last_searched": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── Clients ────────────────────────────────────────────────────────────────
@st.cache_resource
def get_clients():
    return {
        "uniprot":   UniProtClient(),
        "clinvar":   ClinVarClient(),
        "alphafold": AlphaFoldClient(),
        "pubmed":    PubMedClient(),
        "ncbi":      NCBIClient(),
        "ml":        ProteinMLModel(),
    }

clients = get_clients()

# ─── Sidebar (returns search params) ────────────────────────────────────────
search_params = render_sidebar(clients)

# ─── Auto-load on new search ────────────────────────────────────────────────
query_key = search_params.get("protein_query", "")
if query_key and query_key != st.session_state["last_searched"]:
    with st.spinner("🔬 Fetching protein data from UniProt, ClinVar, AlphaFold & PubMed…"):
        try:
            # 1. UniProt
            pdata = clients["uniprot"].fetch(query_key)
            st.session_state["protein_data"] = pdata

            uniprot_id = pdata.get("primaryAccession", "")
            gene       = pdata.get("genes", [{}])[0].get("geneName", {}).get("value", query_key)
            st.session_state["gene_name"]   = gene
            st.session_state["protein_id"]  = uniprot_id

            # 2. ClinVar
            cv_data = clients["clinvar"].fetch_variants(gene)
            st.session_state["clinvar_data"] = cv_data

            # 3. AlphaFold
            pdb_str = clients["alphafold"].fetch_pdb(uniprot_id)
            st.session_state["alphafold_pdb"] = pdb_str

            # 4. PubMed citations
            papers = clients["pubmed"].fetch_cited_papers(gene, n=8)
            st.session_state["papers"] = papers

            # 5. ML scoring
            ml_scores = clients["ml"].score_variants(cv_data)
            st.session_state["ml_scores"] = ml_scores

            st.session_state["last_searched"] = query_key
            st.session_state["assay_data"] = search_params.get("assay_text", "")

        except Exception as exc:
            st.error(f"⚠️ Data fetch error: {exc}")

# ─── Tutorial banner ────────────────────────────────────────────────────────
if st.session_state.get("tutorial_mode"):
    st.markdown("""
    <div class="tutorial-box">
      <h4>📖 Tutorial Mode Active</h4>
      <p><b>Step 1 — Sidebar:</b> Enter a protein name or UniProt ID (e.g. <i>TP53</i>) and optionally paste wet-lab assay results.
      <b>Step 2 — Triage tab:</b> Review the 3D structure and prioritised residue triage.
      <b>Step 3 — Case Study:</b> Inspect tissue associations, genomic context, and disease classification.
      <b>Step 4 — Protein Explorer:</b> Click residues for mutation analysis.
      <b>Step 5 — Experiments tab:</b> Pick cost-effective validated assay paths.</p>
    </div>
    """, unsafe_allow_html=True)

# ─── Main tabs ───────────────────────────────────────────────────────────────
if st.session_state["protein_data"] is None:
    st.info("👈 Enter a protein or gene name in the sidebar to begin.", icon="🧬")
    st.markdown("""
    <div class="card">
      <h4>🚀 Quick Start</h4>
      <p>Try searching <b>TP53</b>, <b>BRCA1</b>, <b>EGFR</b>, or any UniProt accession (e.g. <i>P04637</i>).<br>
      Protellect will fetch live data from UniProt, ClinVar, AlphaFold, and PubMed and build your triage in seconds.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔴 Triage",
        "📋 Case Study",
        "🔬 Protein Explorer",
        "🧪 Further Experimentation & Therapy",
    ])
    with tab1:
        render_triage_tab(
            protein_data  = st.session_state["protein_data"],
            clinvar_data  = st.session_state["clinvar_data"],
            alphafold_pdb = st.session_state["alphafold_pdb"],
            ml_scores     = st.session_state["ml_scores"],
            papers        = st.session_state["papers"],
            gene_name     = st.session_state["gene_name"],
        )
    with tab2:
        render_case_study_tab(
            protein_data = st.session_state["protein_data"],
            clinvar_data = st.session_state["clinvar_data"],
            ncbi_client  = clients["ncbi"],
            papers       = st.session_state["papers"],
            gene_name    = st.session_state["gene_name"],
        )
    with tab3:
        render_explorer_tab(
            protein_data  = st.session_state["protein_data"],
            alphafold_pdb = st.session_state["alphafold_pdb"],
            clinvar_data  = st.session_state["clinvar_data"],
            ml_scores     = st.session_state["ml_scores"],
            papers        = st.session_state["papers"],
            gene_name     = st.session_state["gene_name"],
        )
    with tab4:
        render_experiments_tab(
            protein_data = st.session_state["protein_data"],
            clinvar_data = st.session_state["clinvar_data"],
            ml_scores    = st.session_state["ml_scores"],
            assay_text   = st.session_state["assay_data"],
            papers       = st.session_state["papers"],
            gene_name    = st.session_state["gene_name"],
        )

# ─── Footer ─────────────────────────────────────────────────────────────────
st.markdown("<hr class='divider'>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center;color:#2d4a6a;font-size:0.78rem;'>"
    "Protellect · Data: UniProt · ClinVar · AlphaFold · PubMed · NCBI · "
    "Not a substitute for expert clinical judgment.</p>",
    unsafe_allow_html=True,
)
