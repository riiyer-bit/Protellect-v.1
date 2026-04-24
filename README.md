# 🧬 Protellect — MVP

Experimental triage system: upload residue-level data → score it → visualize on a 3D protein.

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the app
```bash
streamlit run app.py
```
The app opens automatically at http://localhost:8501

---

## What Each File Does

| File | What it is |
|---|---|
| `app.py` | The full web app. This is what you run. |
| `scorer.py` | Triage engine — normalizes scores, assigns HIGH/MEDIUM/LOW priority, generates hypothesis text. |
| `structure_loader.py` | Fetches protein PDB files from AlphaFold or RCSB PDB. No login needed. |
| `sample_data/example.csv` | TP53 DMS data to test with immediately. |
| `requirements.txt` | Python packages to install. |

---

## Input CSV Format

Required columns:
- `residue_position` — amino acid number (integer)
- `effect_score` — functional effect, any scale (will be normalized to 0–1)

Optional:
- `mutation` — e.g. R175H
- `experiment_type` — e.g. DMS, CRISPR, functional assay

```csv
residue_position,effect_score,mutation,experiment_type
175,0.99,R175H,DMS
248,0.95,R248W,DMS
42,0.87,A42V,DMS
```

---

## Good Test Proteins

| Protein | UniProt ID | Why |
|---|---|---|
| TP53 | P04637 | Most studied tumor suppressor, tons of DMS data available |
| EGFR | P00533 | Key oncology target, well-annotated |
| BRCA1 | P38398 | DNA repair, clinical variant data |
| KRAS | P01116 | Oncogene, hotspot mutations at G12/G13 |

Public experimental datasets: **MaveDB**, **ProtaBank**, DMS papers on bioRxiv.

---

## Tuning the Scoring

In the sidebar you can adjust two sliders:
- **HIGH priority cutoff** (default 0.75) — residues above this are flagged as critical
- **MEDIUM priority cutoff** (default 0.40) — residues above this are worth investigating

Adjust these based on your biological judgment about what constitutes a meaningful effect in your specific assay.

---

## Phase 2 (Next Steps)

- Integrate UniProt API for functional annotations per residue
- Add ClinVar variant disease associations
- Conservation scoring from sequence alignments
- Smarter hypothesis text using domain context

---

## Phase 3 (Later)

- ML model trained on biological features
- Clustering of high-impact structural regions
- Confidence scores and uncertainty estimates
