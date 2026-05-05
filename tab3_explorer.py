# 🧬 Protellect

> **AI-powered protein triage platform** — eliminate wasted experiments, follow the science.

Protellect integrates UniProt, ClinVar, AlphaFold, PubMed, NCBI Gene, and ML to give researchers a complete decision engine for protein/variant prioritisation.

---

## 🚀 Features

| Feature | Details |
|---|---|
| **Triage (Tab 1)** | AlphaFold 3D structure coloured by pLDDT · Pathogenic residues as bright spheres · ClinVar triage list ranked CRITICAL / HIGH / MEDIUM / NEUTRAL |
| **Case Study (Tab 2)** | Tissue associations · Genomic data (chromosome, exons, RefSeq) · GPCR classification · Disease somatic vs germline (UniProt + ClinVar) |
| **Protein Explorer (Tab 3)** | Full interactive 3D viewer (cartoon/stick/sphere/surface) · Click any residue → detailed breakdown · "If Mutated" slider with structural perturbation animation · Disease → Mutation → Genomic implication map |
| **Experimentation & Therapy (Tab 4)** | Full protocol cards for 12+ assay types · Cost tiers ($–$$$$$) · Mutation focus / deprioritise guidance · Decision funnel |
| **ML Engine** | Gradient Boosting pathogenicity scorer trained on live ClinVar labels · AA physicochemical features · Review status weighting |
| **Citations** | Highly-cited PubMed papers fetched for every claim |
| **Tutorial Mode** | Step-by-step onboarding banner |
| **Sidebar** | Disease ranking (Critical/High/Medium/Neutral) · Assay interpretation · Suggested experiments |

---

## 📦 Installation

```bash
git clone https://github.com/YOUR_USERNAME/protellect.git
cd protellect
pip install -r requirements.txt
streamlit run app.py
```

---

## 🔑 API Keys

No API keys required. Protellect uses freely accessible public APIs:

- **UniProt REST API** — `https://rest.uniprot.org`
- **ClinVar / NCBI E-utilities** — `https://eutils.ncbi.nlm.nih.gov`
- **AlphaFold DB API** — `https://alphafold.ebi.ac.uk/api`
- **PubMed E-utilities** — `https://eutils.ncbi.nlm.nih.gov`

> For production use with high traffic, register an NCBI API key (free) and add to `.env` as `NCBI_API_KEY`.

---

## 🏗️ Project Structure

```
protellect/
├── app.py                   # Entry point
├── requirements.txt
├── README.md
├── components/
│   └── sidebar.py           # Disease ranking, assay interpretation, experiment quick-list
├── utils/
│   ├── uniprot.py           # UniProt REST client + helpers
│   ├── clinvar.py           # ClinVar E-utilities client (primary triage source)
│   ├── alphafold.py         # AlphaFold DB client + pLDDT parser
│   ├── pubmed.py            # PubMed highly-cited paper fetcher
│   ├── ncbi.py              # NCBI Gene genomic data
│   └── ml_model.py          # Gradient Boosting pathogenicity scorer
└── tabs/
    ├── tab1_triage.py       # 3D structure · disease panel · residue triage
    ├── tab2_case_study.py   # Tissue · genomics · GPCR · somatic/germline
    ├── tab3_explorer.py     # Interactive explorer · mutation analysis
    └── tab4_experiments.py  # Full protocol cards · decision framework
```

---

## 🧬 Quick Start

1. Run `streamlit run app.py`
2. In the sidebar, type a gene symbol (e.g. `TP53`, `BRCA1`, `EGFR`) or UniProt accession (e.g. `P04637`)
3. Click **Analyse Protein**
4. Navigate the four tabs

---

## 🎯 Design Philosophy

> *"Eliminate the cost and resources of bio-experimentation by creating a triage system — showing which hypotheses to follow, which proteins and genes to work with, and which ones to neglect."*

- **ClinVar** is the primary triage source
- **ML scoring** supplements with physicochemical variant features
- Every claim is backed by **PubMed citations**
- The decision funnel guides CRITICAL → HIGH → MEDIUM → NEUTRAL sequencing

---

## 📄 Disclaimer

Protellect is a research tool. It is not a substitute for expert clinical or scientific judgment. Always validate computational predictions with appropriate experimental methods.

---

## 🛠 Contributing

PRs welcome. Open an issue for feature requests.

---

*Built with Streamlit · Data: UniProt · ClinVar · AlphaFold · PubMed · NCBI*
