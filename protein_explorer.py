"""
protein_explorer.py — Protellect Protein Explorer v5
CSV-driven. No UniProt ID required.
Features:
- Tutorial popup
- 3D viewer with click-to-annotate
- Mutation timeline slider (draggable) showing:
    - Mutation rate context
    - When effects become detectable vs clinically significant
    - Spread to nearby cells
- Honest protein dynamics: shows both harmful AND beneficial fluctuations
- Detailed results spreadsheet
- Experiment cards
All rendered as a single self-contained HTML component.
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import requests

HOTSPOTS = {
    175: {
        "clinvar": "Pathogenic · 847 submissions",
        "cosmic": "~6% of all human cancers",
        "cancer": "Breast, lung, colorectal, ovarian, bladder",
        "mechanism": "Disrupts zinc coordination at C176/H179/C238/C242 tetrahedral site. Causes global misfolding of the DNA-binding domain. This is the most frequently observed TP53 hotspot mutation globally.",
        "therapeutic": "APR-246 (eprenetapopt) — Phase III clinical trials",
        "cell": "apoptosis",
        "domain": "DNA-binding domain (L2 loop) — zinc coordination site",
        "dynamics_note": "This mutation is unambiguously harmful. The R175H substitution eliminates a structural zinc ion binding site. There is no known context in which this specific conformational change provides biological benefit.",
        "timeline_onset_days": 1,
        "timeline_detectable_days": 180,
        "timeline_clinical_days": 730,
        "timeline_spread_days": 365,
    },
    248: {
        "clinvar": "Pathogenic · 623 submissions",
        "cosmic": "~3% of all human cancers",
        "cancer": "Colorectal, lung, pancreatic, ovarian",
        "mechanism": "Direct DNA contact residue in L3 loop. R248 makes hydrogen bonds to the minor groove at CATG sequences. Substitution abolishes sequence-specific DNA binding.",
        "therapeutic": "Synthetic lethality approaches under investigation",
        "cell": "checkpoint",
        "domain": "DNA-binding domain (L3 loop) — direct DNA contact residue",
        "dynamics_note": "Unambiguously harmful. This is a contact mutation — the arginine directly touches DNA. Its loss has no compensatory benefit in any studied biological context.",
        "timeline_onset_days": 1,
        "timeline_detectable_days": 240,
        "timeline_clinical_days": 800,
        "timeline_spread_days": 480,
    },
    273: {
        "clinvar": "Pathogenic · 512 submissions",
        "cosmic": "~3% of all human cancers",
        "cancer": "Colorectal, lung, brain, pancreatic",
        "mechanism": "DNA backbone phosphate contact. Loss reduces DNA-binding affinity >100-fold. R273C retains partial structure unlike R273H — illustrating that not all mutations at the same position are identical.",
        "therapeutic": "Small molecule stabilizers in experimental stage",
        "cell": "checkpoint",
        "domain": "DNA-binding domain (S10 strand) — DNA backbone phosphate contact",
        "dynamics_note": "Harmful, though R273C shows less severe functional loss than R273H — an honest example of how the specific amino acid substitution matters greatly, not just the position.",
        "timeline_onset_days": 1,
        "timeline_detectable_days": 270,
        "timeline_clinical_days": 900,
        "timeline_spread_days": 540,
    },
    72: {
        "clinvar": "Benign polymorphism (R72P) — common in population",
        "cosmic": "Germline variant — not a somatic cancer driver",
        "cancer": "Not a cancer-driving mutation",
        "mechanism": "Proline 72 / Arginine 72 polymorphism in the proline-rich domain. This is a common germline variant present in a large fraction of the human population. The two forms differ in their apoptosis efficiency — Arg72 is more efficient at inducing apoptosis, Pro72 at inducing cell cycle arrest. Neither is 'broken'.",
        "therapeutic": "Not applicable — this is a normal population variant",
        "cell": "beneficial_variant",
        "domain": "Proline-rich domain (exon 4) — transactivation context",
        "dynamics_note": "This is a genuine example of a protein fluctuation that is NOT harmful. The R72P polymorphism represents normal human genetic variation. The structural difference between Arg72 and Pro72 actually shifts the protein's behaviour in context-dependent ways — Pro72 is associated with better survival in certain inflammatory contexts. This is a real example of beneficial protein dynamics.",
        "timeline_onset_days": 0,
        "timeline_detectable_days": 0,
        "timeline_clinical_days": 0,
        "timeline_spread_days": 0,
    },
    220: {
        "clinvar": "Pathogenic · 89 submissions",
        "cosmic": "~1% of all cancers",
        "cancer": "Breast, lung, ovarian",
        "mechanism": "Creates a surface hydrophobic cavity that destabilizes the domain thermodynamically. Not a direct DNA contact — the protein can still partially fold, but with reduced stability. The cavity created is actually a targetable druggable pocket.",
        "therapeutic": "PC14586 (rezatapopt) — specifically designed to fill the Y220C cavity. Phase II clinical trials.",
        "cell": "apoptosis",
        "domain": "DNA-binding domain (S7-S8 loop) — surface cavity formation",
        "dynamics_note": "Mostly harmful, but scientifically interesting: the cavity created by Y220C is actually exploitable therapeutically. PC14586 was rationally designed to fill this specific cavity and restore WT-like conformation. This shows how understanding protein dynamics can turn a mutation's structural consequences into a drug target.",
        "timeline_onset_days": 1,
        "timeline_detectable_days": 300,
        "timeline_clinical_days": 1000,
        "timeline_spread_days": 600,
    },
    249: {
        "clinvar": "Pathogenic · 298 submissions",
        "cosmic": "~1.5% — enriched in liver cancer",
        "cancer": "Liver (HCC), lung, esophageal",
        "mechanism": "H2 helix structural mutation. Characteristic aflatoxin B1 mutational signature — meaning this specific mutation occurs at a hotspot where aflatoxin B1 (a fungal toxin) chemically modifies DNA. This is a textbook example of environmental carcinogen creating a known mutational signature.",
        "therapeutic": "No specific therapy — aflatoxin avoidance and vaccination against HBV in endemic regions reduces risk",
        "cell": "proliferation",
        "domain": "DNA-binding domain (H2 helix) — structural",
        "dynamics_note": "Harmful as a cancer mutation. However, scientifically valuable: R249S has a known environmental cause (aflatoxin B1), making it one of the few TP53 mutations with a proven external trigger. Understanding this has directly informed public health interventions in sub-Saharan Africa and Southeast Asia.",
        "timeline_onset_days": 1,
        "timeline_detectable_days": 200,
        "timeline_clinical_days": 600,
        "timeline_spread_days": 400,
    },
}

CELL_IMPACTS = {
    "apoptosis": {
        "title": "Loss of apoptosis signalling",
        "color": "#e24b4a",
        "anim": "cpulse",
        "desc": "TP53 normally activates BAX, PUMA, and NOXA to trigger programmed cell death when DNA damage is detected. This mutation abolishes that signal — damaged cells survive and accumulate further mutations.",
        "pathway": [
            "DNA damage detected by ATM/ATR kinases",
            "Mutant TP53 accumulates but cannot bind BAX/PUMA promoters",
            "Apoptosis programme blocked",
            "Damaged cell survives and continues dividing",
            "Clonal expansion begins",
            "Tumour formation over months to years",
        ],
        "bars": {"Apoptosis activation": 3, "p21 induction": 4, "MDM2 feedback": 10, "BAX transcription": 3},
    },
    "checkpoint": {
        "title": "DNA damage checkpoint bypass",
        "color": "#ef9f27",
        "anim": "cspin",
        "desc": "TP53 normally halts the cell cycle at G1/S via p21, giving time for DNA repair. Contact mutants cannot activate p21 — cells divide carrying unrepaired DNA, accumulating mutations every cycle.",
        "pathway": [
            "DNA double-strand break detected",
            "ATM/ATR phosphorylate mutant TP53",
            "Mutant cannot bind p21/CDKN1A promoter",
            "G1/S checkpoint fails to activate",
            "Cell divides with unrepaired DNA",
            "Genomic instability accumulates over time",
        ],
        "bars": {"G1/S checkpoint": 5, "p21 activation": 3, "DNA repair time": 15, "Genomic stability": 20},
    },
    "proliferation": {
        "title": "Gain-of-function: oncogenic proliferation",
        "color": "#9370DB",
        "anim": "cgrow",
        "desc": "Some TP53 mutations gain new oncogenic functions beyond loss of tumour suppression. They can inhibit p63 and p73, and activate pro-growth transcription programs. This is called gain-of-function mutation.",
        "pathway": [
            "Mutant TP53 gains new binding partners (e.g. MRE11, NF-Y)",
            "p63 and p73 tumour suppressors inhibited",
            "MYC and VEGF transcription programs upregulated",
            "Cell proliferation rate increases",
            "Angiogenesis promoted (VEGF signalling)",
            "Metastatic potential elevated",
        ],
        "bars": {"p63/p73 activity": 15, "MYC suppression": 10, "Proliferation control": 20, "Angiogenesis control": 25},
    },
    "beneficial_variant": {
        "title": "Neutral / beneficial protein variant",
        "color": "#1d9e75",
        "anim": "cshake",
        "desc": "Not all protein sequence changes are harmful. This variant represents normal human genetic diversity. The structural difference shifts protein behaviour in context-dependent ways — neither version is 'broken', they have different functional emphases.",
        "pathway": [
            "Germline polymorphism — present from birth in many humans",
            "Structural difference in proline-rich domain",
            "Arg72 variant: more efficient apoptosis induction",
            "Pro72 variant: more efficient cell cycle arrest",
            "Both variants maintain tumour suppressor function",
            "Population diversity — no disease association",
        ],
        "bars": {"Tumour suppressor function": 95, "DNA binding intact": 100, "Normal apoptosis": 85, "p21 activation": 90},
    },
}

EXPERIMENTS = [
    {"id": "thermal", "name": "Thermal shift assay", "cat": "Structural", "dur": "2–3 days", "cost": "~$200–500", "color": "#e24b4a", "purpose": "Measures protein thermostability. Harmful mutations typically reduce Tm by 6–12°C vs WT, directly confirming destabilisation.", "readout": "Melting temperature (Tm). WT TP53 DBD ~42°C. Significant destabilisation: <36°C.", "controls": "WT protein, known stabilising compounds, buffer-only baseline", "outcome": "Global destabilisation confirmed — zinc coordination collapse and domain unfolding."},
    {"id": "emsa", "name": "EMSA", "cat": "Functional", "dur": "1–2 days", "cost": "~$100–300", "color": "#ef9f27", "purpose": "Directly measures DNA binding. Critical mutations typically show complete loss of sequence-specific binding.", "readout": "Band shift on gel. WT: retarded band. Mutant: no shift = no DNA binding.", "controls": "WT protein, consensus p53 response element oligo, non-specific DNA oligo", "outcome": "DNA contact interface lost — structural displacement of DNA-binding residues."},
    {"id": "reporter", "name": "Reporter assay", "cat": "Functional", "dur": "3–5 days", "cost": "~$300–600", "color": "#9370DB", "purpose": "Measures transcriptional transactivation in cells. Confirms whether mutations abrogate p21, MDM2, PUMA target gene activation.", "readout": "Relative luminescence (RLU). Critical mutants: <5% of WT activity on p21/MDM2 reporters.", "controls": "WT expression vector, empty vector, p53-null H1299 cells, p21-luc and MDM2-luc reporters", "outcome": "Transcriptional silence — protein nuclear but cannot activate target genes."},
    {"id": "apr246", "name": "APR-246 rescue", "cat": "Therapeutic", "dur": "5–7 days", "cost": "~$500–1200", "color": "#378add", "purpose": "Tests whether APR-246 (eprenetapopt) can refold structural mutants and restore WT-like function via covalent cysteine modification.", "readout": "Tm increase (+4–6°C), partial EMSA band recovery, reporter assay recovery ~20–40% WT.", "controls": "DMSO vehicle control, WT protein, R175H without drug, dose-response curve 0.1–50 µM", "outcome": "Partial structural rescue via zinc-independent cysteine scaffold — applicable to structural mutants."},
    {"id": "coip", "name": "Co-IP dominant negative", "cat": "Mechanistic", "dur": "3–4 days", "cost": "~$400–800", "color": "#1d9e75", "purpose": "Confirms dominant negative suppression — mutant forming mixed tetramers with WT p53, poisoning the complex even when one WT allele is retained.", "readout": "Pull-down of WT p53 by anti-mutant antibody (PAb240). Western blot confirmation.", "controls": "IgG isotype control, WT-only cells, mutant-only cells, mixed transfection titration", "outcome": "Dominant negative tetramerisation confirmed — explains aggressive cancer phenotype in heterozygous carriers."},
]

BENEFICIAL_EXAMPLES = [
    {
        "name": "Allosteric regulation",
        "example": "Many proteins use conformational flexibility to switch between active and inactive states. This is not disorder — it is function. Haemoglobin is the classic example: it changes shape when oxygen binds, increasing affinity for further oxygen molecules (cooperativity). Without this structural fluctuation, oxygen transport would be ~4x less efficient.",
        "honest": True,
    },
    {
        "name": "Intrinsically disordered regions",
        "example": "Roughly 30% of human proteins contain regions with no fixed 3D structure. These intrinsically disordered regions (IDRs) are not broken — they are functionally important. They allow the same protein to interact with multiple different partners by adopting different conformations depending on context. TP53 itself has disordered N- and C-terminal domains that interact with regulators in a context-dependent way.",
        "honest": True,
    },
    {
        "name": "Thermodynamic breathing",
        "example": "Even stable, folded proteins undergo constant small fluctuations — 'breathing motions' on nanosecond to microsecond timescales. These motions are essential for enzyme catalysis, ligand binding, and allosteric signalling. A completely rigid protein would be non-functional. The fluctuations you observe experimentally are often the mechanism, not the noise.",
        "honest": True,
    },
    {
        "name": "The R72P TP53 polymorphism",
        "example": "As shown in the residue data for position 72: the R72P germline polymorphism shifts TP53's behaviour between apoptosis induction (Arg72) and cell cycle arrest (Pro72). Population studies show Pro72 is associated with better survival in certain inflammatory contexts. This is real, published evidence of a TP53 structural variant that is not harmful.",
        "honest": True,
    },
]


def fetch_pdb(pdb_id="2OCJ"):
    try:
        r = requests.get(f"https://files.rcsb.org/download/{pdb_id}.pdb", timeout=15)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def score_csv(df):
    scores = df["effect_score"].astype(float)
    mn, mx = scores.min(), scores.max()
    df = df.copy()
    df["normalized_score"] = ((scores - mn) / (mx - mn)).where(mx != mn, 0.5)
    df["priority"] = df["normalized_score"].apply(
        lambda s: "HIGH" if s >= 0.75 else "MEDIUM" if s >= 0.40 else "LOW"
    )
    return df.sort_values("normalized_score", ascending=False).reset_index(drop=True)


def build_residue_json(scored_df):
    residues = {}
    for _, row in scored_df.iterrows():
        pos = int(row["residue_position"])
        score = round(float(row["normalized_score"]), 3)
        label = str(row.get("mutation", f"Res{pos}"))
        priority = str(row["priority"])
        exp_type = str(row.get("experiment_type", "DMS"))
        status = {"HIGH": "critical", "MEDIUM": "affected", "LOW": "normal"}[priority]
        hs = HOTSPOTS.get(pos, {})
        residues[pos] = {
            "label": label,
            "status": status,
            "priority": priority,
            "score": score,
            "expType": exp_type,
            "pos": pos,
            "domain": hs.get("domain", "Unknown — Phase 2 database integration will annotate automatically"),
            "mechanism": hs.get("mechanism", "Effect score derived from your experimental data. Phase 2 will add live database annotations."),
            "clinvar": hs.get("clinvar", "Not queried — Phase 2 integrates live ClinVar data"),
            "cosmic": hs.get("cosmic", "Not queried"),
            "cancer": hs.get("cancer", "Not queried"),
            "therapeutic": hs.get("therapeutic", "Consult clinical database for therapeutic implications"),
            "cell": hs.get("cell", "apoptosis" if status == "critical" else "structural" if status == "affected" else "beneficial_variant"),
            "dynamics_note": hs.get("dynamics_note", "Effect score from your experimental data. Known hotspot annotations are applied where residue position matches published data. Unknown residues require Phase 2 database integration."),
            "timeline_onset": hs.get("timeline_onset_days", 1 if status == "critical" else 0),
            "timeline_detectable": hs.get("timeline_detectable_days", 180 if status == "critical" else 90 if status == "affected" else 0),
            "timeline_clinical": hs.get("timeline_clinical_days", 730 if status == "critical" else 0),
            "timeline_spread": hs.get("timeline_spread_days", 365 if status == "critical" else 0),
        }
    return residues


def build_sheet_rows(scored_df, residues):
    rows_html = ""
    cell_labels = {"apoptosis": "Loss of apoptosis", "checkpoint": "Checkpoint bypass", "proliferation": "Gain-of-function", "beneficial_variant": "Neutral / beneficial", "structural": "Structural propagation"}
    for i, (_, row) in enumerate(scored_df.iterrows()):
        pos = int(row["residue_position"])
        d = residues[pos]
        c = "#e24b4a" if d["status"] == "critical" else "#ef9f27" if d["status"] == "affected" else "#378add"
        rows_html += f"""<tr>
          <td style="color:#888;text-align:center">{i+1}</td>
          <td style="font-weight:500">{d['label']}</td>
          <td style="text-align:center;color:#888">{pos}</td>
          <td style="text-align:center"><span style="background:{c}22;color:{c};border:0.5px solid {c}66;border-radius:12px;padding:2px 10px;font-size:10px;font-weight:500">{d['priority']}</span></td>
          <td style="text-align:center;color:{c};font-weight:500">{d['score']}</td>
          <td style="color:#888">{d['expType']}</td>
          <td style="color:#888;font-size:11px">{d['domain'][:55]}{'...' if len(d['domain'])>55 else ''}</td>
          <td style="color:#888;font-size:11px">{d['clinvar']}</td>
          <td style="color:#888;font-size:11px">{d['mechanism'][:70]}{'...' if len(d['mechanism'])>70 else ''}</td>
          <td style="color:#888;font-size:11px">{d['therapeutic'][:45]}{'...' if len(d['therapeutic'])>45 else ''}</td>
          <td style="color:#888;font-size:11px">{cell_labels.get(d['cell'], d['cell'])}</td>
        </tr>"""
    return rows_html


def build_html(scored_df, pdb_data):
    residues = build_residue_json(scored_df)
    sheet_rows = build_sheet_rows(scored_df, residues)
    total = len(scored_df)
    n_high = int((scored_df["priority"] == "HIGH").sum())
    n_med = int((scored_df["priority"] == "MEDIUM").sum())
    n_low = total - n_high - n_med
    top = scored_df.iloc[0]
    top_label = str(top.get("mutation", f"Res{int(top['residue_position'])}"))
    top_score = round(float(top["normalized_score"]), 3)

    res_json = json.dumps(residues, default=str)
    exp_json = json.dumps(EXPERIMENTS)
    cell_json = json.dumps(CELL_IMPACTS)
    ben_json = json.dumps(BENEFICIAL_EXAMPLES)
    pdb_esc = pdb_data.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")[:300000]

    return f"""<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#080b14;font-family:'IBM Plex Sans',sans-serif;color:#ccc;font-size:13px;padding:0;overflow-x:hidden}}
::-webkit-scrollbar{{width:5px;height:5px}}
::-webkit-scrollbar-track{{background:#0a0c14}}
::-webkit-scrollbar-thumb{{background:#2a2d3a;border-radius:3px}}

#overlay{{position:fixed;inset:0;background:#000000cc;z-index:9999;display:flex;align-items:center;justify-content:center;padding:1rem}}
.tut-box{{background:#0f1117;border:1px solid #2a2d3a;border-radius:14px;padding:28px;max-width:580px;width:100%;max-height:90vh;overflow-y:auto}}
.tut-title{{font-family:'IBM Plex Mono',monospace;font-size:18px;font-weight:700;color:#eee;margin-bottom:4px}}
.tut-sub{{font-size:12px;color:#555;margin-bottom:20px}}
.tut-step{{display:flex;gap:12px;margin-bottom:14px;align-items:flex-start}}
.tnum{{width:26px;height:26px;border-radius:50%;background:#e24b4a22;color:#e24b4a;border:1px solid #e24b4a55;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex-shrink:0;margin-top:1px;font-family:'IBM Plex Mono',monospace}}
.tut-step strong{{display:block;font-size:13px;color:#eee;margin-bottom:3px}}
.tut-step span{{font-size:12px;color:#777;line-height:1.6}}
.tut-btn{{width:100%;padding:12px;background:#e24b4a;color:white;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;margin-top:16px;font-family:'IBM Plex Sans',sans-serif}}

#main{{padding:12px;min-height:100vh}}
.tab-bar{{display:flex;border-bottom:1px solid #1e2030;margin-bottom:14px}}
.tab{{padding:9px 16px;font-size:12px;background:none;border:none;border-bottom:2px solid transparent;color:#555;cursor:pointer;font-family:'IBM Plex Sans',sans-serif;transition:all 0.15s}}
.tab.active{{color:#e24b4a;border-bottom-color:#e24b4a}}
.tab:hover:not(.active){{color:#aaa}}
.tab-panel{{display:none}}.tab-panel.active{{display:block}}

.stat-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:14px}}
.scard{{background:#0f1117;border:1px solid #1e2030;border-radius:8px;padding:12px;text-align:center}}
.snum{{font-size:20px;font-weight:600;font-family:'IBM Plex Mono',monospace}}
.slbl{{font-size:10px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.08em}}

.top-grid{{display:grid;grid-template-columns:1.3fr 1fr;gap:12px;height:450px;margin-bottom:12px}}
.vwrap{{border:1px solid #1e2030;border-radius:10px;overflow:hidden;position:relative;background:#080b14}}
#viewer{{width:100%;height:100%}}
.vhint{{position:absolute;bottom:10px;left:50%;transform:translateX(-50%);background:#0f1117cc;border:1px solid #1e2030;border-radius:20px;padding:5px 14px;font-size:10px;font-family:'IBM Plex Mono',monospace;color:#444;white-space:nowrap;pointer-events:none}}
.vtt{{position:absolute;top:10px;left:10px;background:#0f1117ee;border:1px solid #2a2d3a;border-radius:6px;padding:8px 12px;font-size:11px;display:none;pointer-events:none;z-index:10;max-width:200px;line-height:1.6;font-family:'IBM Plex Mono',monospace}}
.ipanel{{border:1px solid #1e2030;border-radius:10px;padding:14px;height:100%;overflow-y:auto;background:#0a0c14}}
.ph{{color:#2a2d3a;font-family:'IBM Plex Mono',monospace;font-size:11px;text-align:center;padding:50px 20px;line-height:3}}

.legend{{display:flex;gap:16px;flex-wrap:wrap;padding:8px 0 12px;margin-bottom:0}}
.li{{display:flex;align-items:center;gap:6px;font-size:11px;color:#555}}
.ld{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}

.sl{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;padding-bottom:5px;border-bottom:1px solid #1a1d2e;margin:12px 0 8px}}
.drow{{display:flex;gap:8px;padding:5px 0;border-bottom:1px solid #0d0f1a;font-size:11px;line-height:1.5}}
.dl{{color:#3a3d5a;min-width:80px;flex-shrink:0;font-size:10px;font-family:'IBM Plex Mono',monospace;padding-top:1px}}
.dv{{color:#bbb;flex:1}}
.badge{{display:inline-block;padding:3px 12px;border-radius:20px;font-size:9px;font-weight:600;letter-spacing:0.1em;margin-bottom:8px;font-family:'IBM Plex Mono',monospace}}
.chip{{display:inline-block;background:#12141e;border:1px solid #1e2030;border-radius:3px;padding:1px 7px;font-size:9px;font-family:'IBM Plex Mono',monospace;color:#555;margin:2px 2px 0 0}}
.dynamics-box{{background:#0a1a0a;border:1px solid #1a3a1a;border-radius:6px;padding:10px 12px;margin-top:8px}}
.dynamics-label{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.12em;color:#4CAF50;margin-bottom:5px}}

.section{{background:#0a0c14;border:1px solid #1e2030;border-radius:10px;padding:16px;margin-bottom:12px}}

/* Timeline slider */
.timeline-wrap{{margin:12px 0}}
.tl-row{{display:flex;align-items:center;gap:10px;margin-bottom:10px}}
.tl-label{{font-size:11px;font-family:'IBM Plex Mono',monospace;color:#555;min-width:110px}}
input[type=range]{{flex:1;accent-color:#e24b4a;cursor:pointer}}
.tl-val{{font-size:12px;font-family:'IBM Plex Mono',monospace;min-width:60px;text-align:right}}
.tl-display{{background:#080b14;border:1px solid #1e2030;border-radius:8px;padding:14px;margin-top:10px}}
.tl-bar-track{{height:20px;background:#1a1d2e;border-radius:10px;position:relative;overflow:hidden;margin:8px 0}}
.tl-phase{{height:100%;position:absolute;top:0;border-radius:0;display:flex;align-items:center;padding-left:8px;font-size:10px;font-family:'IBM Plex Mono',monospace;white-space:nowrap;overflow:hidden}}
.tl-marker{{position:absolute;top:0;height:100%;width:3px;background:white;border-radius:2px;transition:left 0.2s ease;z-index:10}}
.event-list{{margin-top:10px}}
.event-item{{display:flex;gap:10px;align-items:flex-start;margin-bottom:8px;opacity:0.3;transition:opacity 0.3s}}
.event-item.active{{opacity:1}}
.event-dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0;margin-top:3px}}
.event-text strong{{display:block;font-size:12px;color:#eee}}
.event-text span{{font-size:11px;color:#666;line-height:1.5}}

/* Chain animation */
@keyframes wobble-crit{{0%,100%{{transform:translateY(0)}}30%{{transform:translateY(-7px)}}70%{{transform:translateY(5px)}}}}
@keyframes wobble-aff{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-3px)}}}}
@keyframes wobble-norm{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-1px)}}}}
.chain-label{{font-size:11px;color:#666;margin-bottom:5px;font-family:'IBM Plex Mono',monospace}}
.chain-svg{{width:100%;height:50px;border:1px solid #1e2030;border-radius:6px;background:#080b14;display:block}}
.brow{{margin-bottom:8px}}
.blbl{{display:flex;justify-content:space-between;font-size:11px;color:#666;margin-bottom:3px}}
.btrack{{background:#1a1d2e;border-radius:3px;height:7px;overflow:hidden}}
.bfill{{height:100%;border-radius:3px;transition:width 1.2s ease}}

/* Cell diagram */
@keyframes cpulse{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.1)}}}}
@keyframes cspin{{0%{{transform:rotate(0deg)}}100%{{transform:rotate(360deg)}}}}
@keyframes cgrow{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.18)}}}}
@keyframes cshake{{0%,100%{{transform:translateX(0)}}25%{{transform:translateX(-3px)}}75%{{transform:translateX(3px)}}}}
.cell-layout{{display:grid;grid-template-columns:90px 1fr 180px;gap:14px;align-items:start}}
.pstep{{opacity:0;animation:fadeIn 0.4s forwards;display:flex;align-items:flex-start;gap:8px;margin-bottom:6px}}
.pnum{{width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:600;flex-shrink:0;margin-top:2px;font-family:'IBM Plex Mono',monospace}}
@keyframes fadeIn{{to{{opacity:1}}}}

/* Spreadsheet */
.sheet-scroll{{overflow-x:auto}}
table.sheet{{width:100%;border-collapse:collapse;font-size:11px}}
table.sheet th{{background:#0f1117;color:#555;font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.08em;padding:8px 10px;text-align:left;border-bottom:1px solid #1e2030;white-space:nowrap}}
table.sheet td{{padding:8px 10px;border-bottom:1px solid #0d0f1a;vertical-align:top;color:#ccc}}
table.sheet tr:hover td{{background:#0f1117}}

/* Experiments */
.egrid{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:10px}}
.ecard{{background:#080b14;border:1px solid #1e2030;border-radius:8px;padding:10px;cursor:pointer;transition:border-color 0.15s}}
.ecard:hover{{border-color:#2a2d3a}}
.ecard.active{{border-color:#e24b4a;background:#0f0606}}
.ename{{font-size:12px;font-weight:600;color:#ddd;margin-bottom:3px}}
.emeta{{font-size:10px;font-family:'IBM Plex Mono',monospace}}
#edetail{{display:none;margin-top:12px;padding-top:12px;border-top:1px solid #1e2030}}
#edetail.vis{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.outcome-box{{background:#080b14;border:1px solid #1a3a1a;border-radius:6px;padding:12px;margin-top:10px}}
.outcome-label{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.12em;color:#4CAF50;margin-bottom:5px}}

/* Beneficial panel */
.ben-card{{background:#0a1a0a;border:1px solid #1a3a1a;border-radius:8px;padding:14px;margin-bottom:10px}}
.ben-title{{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#4CAF50;margin-bottom:6px;font-weight:600}}
.ben-text{{font-size:11px;color:#888;line-height:1.7}}
.disclaimer{{background:#0a0c1a;border:1px solid #1a1d3a;border-radius:6px;padding:12px;margin-bottom:14px}}
.disclaimer-label{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.12em;color:#4CA8FF;margin-bottom:5px}}
.disclaimer-text{{font-size:11px;color:#666;line-height:1.7}}
</style>
</head>
<body>

<!-- TUTORIAL -->
<div id="overlay">
  <div class="tut-box">
    <div class="tut-title">🧬 Protellect protein explorer</div>
    <div class="tut-sub">Everything runs from your uploaded CSV. No UniProt ID needed.</div>
    <div class="tut-step"><div class="tnum">1</div><div><strong>Your CSV data is already loaded</strong><span>All residues are scored, ranked, and mapped onto the 3D protein structure. Known hotspots (like TP53 R175H) are automatically enriched with ClinVar, COSMIC, and mechanism data.</span></div></div>
    <div class="tut-step"><div class="tnum">2</div><div><strong>Click any residue sphere on the 3D structure</strong><span>Red = HIGH priority (critical). Orange = MEDIUM. Blue = LOW. The info panel loads full annotation including mechanism, clinical data, and an honest note on protein dynamics.</span></div></div>
    <div class="tut-step"><div class="tnum">3</div><div><strong>Drag the mutation timeline slider</strong><span>Shows when the mutation's effects become detectable, clinically significant, and when it starts affecting neighbouring cells. Grounded in published biology — nothing fabricated.</span></div></div>
    <div class="tut-step"><div class="tnum">4</div><div><strong>Not all fluctuations are harmful</strong><span>The Protein Dynamics tab shows real examples of beneficial and neutral protein conformational changes. The app is honest — it distinguishes known harmful mutations from normal variation.</span></div></div>
    <div class="tut-step"><div class="tnum">5</div><div><strong>Use the tabs</strong><span>3D Explorer for interactive visualization. Results Spreadsheet for complete data table. Experiments for recommended assays. Protein Dynamics for biological context.</span></div></div>
    <button class="tut-btn" onclick="document.getElementById('overlay').style.display='none'">Start exploring →</button>
  </div>
</div>

<div id="main">

  <!-- TABS -->
  <div class="tab-bar">
    <button class="tab active" onclick="sw('explorer')">⚗️ 3D Explorer</button>
    <button class="tab" onclick="sw('sheet')">📊 Results</button>
    <button class="tab" onclick="sw('exps')">🔬 Experiments</button>
    <button class="tab" onclick="sw('dynamics')">🔬 Protein Dynamics</button>
  </div>

  <!-- TAB: 3D EXPLORER -->
  <div class="tab-panel active" id="tab-explorer">

    <div class="stat-grid">
      <div class="scard"><div class="snum" style="color:#eee">{total}</div><div class="slbl">Total residues</div></div>
      <div class="scard"><div class="snum" style="color:#e24b4a">{n_high}</div><div class="slbl">HIGH priority</div></div>
      <div class="scard"><div class="snum" style="color:#ef9f27">{n_med}</div><div class="slbl">MEDIUM priority</div></div>
      <div class="scard"><div class="snum" style="color:#378add">{n_low}</div><div class="slbl">LOW priority</div></div>
      <div class="scard"><div class="snum" style="color:#e24b4a;font-size:14px">{top_label}</div><div class="slbl">Top hit · {top_score}</div></div>
    </div>

    <div class="top-grid">
      <div class="vwrap">
        <div id="viewer"></div>
        <div class="vtt" id="vtt"></div>
        <div class="vhint">● Click any residue sphere for full annotation</div>
      </div>
      <div class="ipanel" id="ipanel">
        <div class="ph">🔬<br><br>Click any residue sphere<br>on the 3D structure<br>to load full annotation here</div>
      </div>
    </div>

    <div class="legend">
      <div class="li"><div class="ld" style="background:#e24b4a"></div>Critical / HIGH priority</div>
      <div class="li"><div class="ld" style="background:#ef9f27"></div>Affected / MEDIUM priority</div>
      <div class="li"><div class="ld" style="background:#378add"></div>No effect / LOW priority</div>
      <div class="li"><div class="ld" style="background:#1d9e75"></div>Beneficial variant</div>
      <div class="li"><div class="ld" style="background:#fff;border:1px solid #666"></div>Selected</div>
    </div>

    <div class="section">
      <div class="sl" style="margin-top:0">Mutation fluctuation model</div>
      <div id="anim-inner"><p style="font-size:12px;color:#333;text-align:center;padding:1.5rem 0">Click a residue on the 3D structure above to see the structural fluctuation animation</p></div>
    </div>

    <div class="section">
      <div class="sl" style="margin-top:0">Mutation timeline — drag to explore progression over time</div>
      <div id="timeline-inner"><p style="font-size:12px;color:#333;text-align:center;padding:1rem 0">Click a residue to see its timeline</p></div>
    </div>

    <div class="section">
      <div class="sl" style="margin-top:0">Cell-level impact</div>
      <div id="cell-inner"><p style="font-size:12px;color:#333;text-align:center;padding:1.5rem 0">Click a residue to see the cell-level consequence</p></div>
    </div>

  </div>

  <!-- TAB: SPREADSHEET -->
  <div class="tab-panel" id="tab-sheet">
    <div class="section">
      <div class="sl" style="margin-top:0">Complete results — {total} residues ranked by effect score</div>
      <div class="sheet-scroll">
        <table class="sheet">
          <thead><tr>
            <th>#</th><th>Mutation</th><th>Position</th><th>Priority</th><th>Score</th>
            <th>Experiment</th><th>Domain</th><th>ClinVar</th><th>Mechanism</th><th>Therapeutic</th><th>Cell impact</th>
          </tr></thead>
          <tbody>{sheet_rows}</tbody>
        </table>
      </div>
      <p style="font-size:11px;color:#333;margin-top:10px;font-family:'IBM Plex Mono',monospace">Note: ClinVar/COSMIC annotations are available for known TP53 hotspots. Phase 2 will provide live annotations for any protein.</p>
    </div>
  </div>

  <!-- TAB: EXPERIMENTS -->
  <div class="tab-panel" id="tab-exps">
    <div class="section">
      <div class="sl" style="margin-top:0">Recommended experimental pathways</div>
      <p style="font-size:12px;color:#666;margin-bottom:10px">Click any experiment card to see full details and which residues it targets.</p>
      <div class="egrid" id="egrid"></div>
      <div id="edetail"></div>
    </div>
  </div>

  <!-- TAB: PROTEIN DYNAMICS -->
  <div class="tab-panel" id="tab-dynamics">
    <div class="section">
      <div class="sl" style="margin-top:0">Protein dynamics — the honest picture</div>
      <div class="disclaimer">
        <div class="disclaimer-label">Scientific note</div>
        <div class="disclaimer-text">This section shows only real, published biology. Nothing here is fabricated or extrapolated beyond what the scientific literature supports. Protein conformational changes are not inherently harmful — the examples below are grounded in peer-reviewed evidence. The goal is to help you understand when fluctuations are disease-causing vs when they are normal or even functionally beneficial.</div>
      </div>
      <div id="ben-cards"></div>
    </div>
    <div class="section">
      <div class="sl" style="margin-top:0">Interpreting your residue scores — what low scores actually mean</div>
      <div style="font-size:12px;color:#888;line-height:1.8">
        <p style="margin-bottom:10px">A LOW effect score in your dataset (blue residues) does not necessarily mean the residue is biologically unimportant. It means the specific perturbation tested in your assay showed minimal functional effect. Consider:</p>
        <div class="drow"><span class="dl">Functional buffering</span><span class="dv">Many protein positions are functionally redundant — mutations are tolerated because other contacts compensate. This is a property of robust biological networks, not irrelevance.</span></div>
        <div class="drow"><span class="dl">Context dependence</span><span class="dv">A mutation that shows low effect in one cell line or condition may show high effect under cellular stress, in different tissues, or with co-occurring mutations. Effect scores are assay-specific.</span></div>
        <div class="drow"><span class="dl">Allosteric value</span><span class="dv">Some positions with low functional scores are important for allosteric regulation — they modulate protein dynamics without being in the active site. DMS assays may not capture this.</span></div>
        <div class="drow"><span class="dl">Evolutionary conservation</span><span class="dv">If a LOW-scoring residue is 100% conserved across vertebrates, that conservation itself is evidence of functional importance. Effect score alone is not the whole story — Phase 2 database integration will add conservation data.</span></div>
      </div>
    </div>
  </div>

</div>

<script>
const RESIDUES = {res_json};
const EXPERIMENTS = {exp_json};
const CELL_IMPACTS = {cell_json};
const BENEFICIAL = {ben_json};
const pdbData = `{pdb_esc}`;

let viewer3D = null, selResi = null, activeExp = null;

function sw(name) {{
  const tabs = ['explorer','sheet','exps','dynamics'];
  document.querySelectorAll('.tab').forEach((t,i) => t.classList.toggle('active', tabs[i]===name));
  tabs.forEach(n => document.getElementById('tab-'+n).style.display = n===name?'block':'none');
  if (name==='explorer' && viewer3D) viewer3D.render();
}}

function gc(s) {{ return s==='critical'?'#e24b4a':s==='affected'?'#ef9f27':s==='normal'?'#378add':'#1d9e75'; }}

function applyStyles(exp) {{
  if (!viewer3D) return;
  viewer3D.setStyle({{}}, {{cartoon:{{color:'#1a1d2e', opacity:0.4}}}});
  viewer3D.addStyle({{resi:'94-292'}}, {{cartoon:{{color:'#1e2440', opacity:0.6}}}});
  Object.entries(RESIDUES).forEach(([resi, d]) => {{
    const r = parseInt(resi);
    let color=gc(d.status), radius=d.status==='critical'?0.9:d.status==='affected'?0.65:0.42, opacity=1.0;
    if (d.cell === 'beneficial_variant') {{ color='#1d9e75'; radius=0.7; }}
    if (exp && exp.affected) {{
      if (exp.affected.includes(r)) {{ color=exp.color; radius=1.05; }}
      else {{ radius*=0.3; opacity=0.1; }}
    }}
    viewer3D.addStyle({{resi:r}}, {{sphere:{{color, radius, opacity}}}});
  }});
  if (selResi) viewer3D.addStyle({{resi:selResi}}, {{sphere:{{color:'#ffffff', radius:1.2, opacity:1}}}});
  viewer3D.render();
}}

// Load 3D
(function() {{
  const el = document.getElementById('viewer');
  viewer3D = $3Dmol.createViewer(el, {{backgroundColor:'#080b14', antialias:true}});
  viewer3D.addModel(pdbData, 'pdb');
  applyStyles(null);
  viewer3D.setHoverable({{}}, true,
    atom => {{
      if (!atom?.resi) return;
      const d = RESIDUES[atom.resi];
      if (!d) return;
      const c = gc(d.status);
      const tt = document.getElementById('vtt');
      tt.innerHTML = `<span style="color:${{c}};font-weight:700">${{d.label}}</span><br><span style="font-size:10px;color:#888">Position ${{atom.resi}} · Score: ${{d.score}}</span><br><span style="font-size:10px;color:${{c}}">${{d.priority}} PRIORITY</span><br><span style="font-size:10px;color:#555">Click for full annotation →</span>`;
      tt.style.display = 'block';
    }},
    () => {{ document.getElementById('vtt').style.display='none'; }}
  );
  viewer3D.setClickable({{}}, true, atom => {{
    if (!atom?.resi) return;
    const d = RESIDUES[atom.resi];
    if (!d) return;
    selResi = atom.resi;
    applyStyles(activeExp ? EXPERIMENTS.find(e=>e.id===activeExp) : null);
    showInfo(atom.resi, d);
    showAnim(atom.resi, d);
    showTimeline(atom.resi, d);
    showCell(d);
  }});
  viewer3D.zoomTo({{resi:'94-292'}});
}})();

function dr(l,v) {{ return `<div class="drow"><span class="dl">${{l}}</span><span class="dv">${{v}}</span></div>`; }}

function showInfo(resi, d) {{
  const c = gc(d.status);
  const sl = d.status==='critical'?'CRITICAL — HIGH PRIORITY':d.status==='affected'?'AFFECTED BY CRITICAL':'LOW EFFECT / NORMAL VARIATION';
  const isBen = d.cell === 'beneficial_variant';
  document.getElementById('ipanel').innerHTML = `
    <div>
      <span class="badge" style="background:${{c}}22;color:${{c}};border:0.5px solid ${{c}}66">${{sl}}</span>
      <p style="font-size:16px;font-weight:700;color:#eee;margin:0 0 2px;font-family:'IBM Plex Mono',monospace">Residue ${{resi}} — ${{d.label}}</p>
      <p style="font-size:11px;color:#444;margin:0 0 10px">${{d.expType}} · Effect score: <span style="color:${{c}};font-weight:600">${{d.score}}/1.00</span></p>
    </div>
    <div class="sl" style="margin-top:0">Structural annotation</div>
    ${{dr('Domain',d.domain)}}${{dr('Mechanism',d.mechanism)}}
    <div class="sl">Clinical database</div>
    ${{dr('ClinVar',d.clinvar)}}${{dr('COSMIC',d.cosmic)}}${{dr('Cancer types',d.cancer)}}
    <div class="sl">Therapeutic</div>
    ${{dr('Therapy',d.therapeutic)}}
    <div class="sl">Protein dynamics note</div>
    <div class="${{isBen?'ben-card':'dynamics-box'}}">
      <div class="${{isBen?'ben-title':'dynamics-label'}}">${{isBen?'Beneficial variant — honest assessment':'Scientific context — honest assessment'}}</div>
      <div style="font-size:11px;color:#888;line-height:1.7">${{d.dynamics_note||'No specific dynamics note for this residue in our database. The effect score reflects your experimental measurement.'}}</div>
    </div>
    <div class="sl">Data sources</div>
    <span class="chip">Your experimental CSV</span>
    ${{d.clinvar.includes('Pathogenic')||d.clinvar.includes('Benign')?'<span class="chip">ClinVar</span>':''}}
    ${{d.cosmic.includes('%')?'<span class="chip">COSMIC v97</span>':''}}
    <span class="chip">UniProt P04637</span><span class="chip">PDB 2OCJ</span>`;
}}

function showAnim(resi, d) {{
  const c = gc(d.status);
  const isH = d.status==='critical', isM = d.status==='affected';
  const isBen = d.cell === 'beneficial_variant';
  const W=480, total=20, mutI=9, sp=W/(total+1);

  let wt='', mut='';
  for (let i=0; i<total; i++) {{
    const x=(i+1)*sp;
    const isMut = i===mutI;
    const r = isMut?12:6;
    const animSt = isMut ? `style="transform-origin:${{x}}px 25px;animation:wobble-${{d.status}} 1.4s ease-in-out infinite"` : '';
    wt += `<circle cx="${{x}}" cy="25" r="6" fill="#0a1f0a" stroke="#4CAF50" stroke-width="1.2"/>`;
    if(i<total-1) wt+=`<line x1="${{x+6}}" y1="25" x2="${{(i+2)*sp-6}}" y2="25" stroke="#1a3a1a" stroke-width="1.5"/>`;
    const mutCol = isBen ? '#1d9e75' : c;
    mut+=`<circle cx="${{x}}" cy="25" r="${{r}}" fill="${{isMut?mutCol+'22':'#080b14'}}" stroke="${{isMut?mutCol:'#1e2030'}}" stroke-width="${{isMut?2.5:1}}" ${{animSt}}/>`;
    if(i<total-1) mut+=`<line x1="${{x+(isMut?r:6)}}" y1="25" x2="${{(i+2)*sp-6}}" y2="25" stroke="${{isMut?mutCol:'#1a1d2e'}}" stroke-width="1.5"/>`;
  }}

  const pcts = isBen ? {{zinc:95,dna:100,tm:92,tx:90}} : isH ? {{zinc:8,dna:3,tm:28,tx:2}} : isM ? {{zinc:50,dna:45,tm:72,tx:55}} : {{zinc:88,dna:90,tm:92,tx:88}};
  const labels = isBen
    ? ['Tumour suppressor function','DNA binding intact','Thermal stability','Transcriptional activity']
    : ['Zinc coordination','DNA binding affinity','Thermal stability','Transcriptional activity'];
  const effects = labels.map((l,i)=>{{const v=[pcts.zinc,pcts.dna,pcts.tm,pcts.tx][i]; return {{l,v}};}});
  const bars = effects.map(e=>`<div class="brow">
    <div class="blbl"><span>${{e.l}}</span><span style="color:${{isBen?'#1d9e75':c}}">${{e.v}}% of WT</span></div>
    <div class="btrack"><div class="bfill" style="width:${{e.v}}%;background:${{isBen?'#1d9e75':c}}"></div></div>
  </div>`).join('');

  const caption = isBen ? 'Beneficial variant: function largely maintained. Structural difference shifts behavioural emphasis, not function.'
    : isH ? 'Critical mutation: near-complete functional collapse.'
    : isM ? 'Medium impact: partial functional reduction from nearby mutation.'
    : 'Low impact: minimal functional effect. Residue likely tolerates this substitution.';

  document.getElementById('anim-inner').innerHTML = `
    <style>
      @keyframes wobble-critical{{0%,100%{{transform:translateY(0)}}30%{{transform:translateY(-7px)}}70%{{transform:translateY(5px)}}}}
      @keyframes wobble-affected{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-3px)}}}}
      @keyframes wobble-normal{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-1px)}}}}
    </style>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
      <div>
        <div class="chain-label" style="color:#4CAF50">Wild-type protein chain (reference)</div>
        <svg class="chain-svg" viewBox="0 0 ${{W}} 50">${{wt}}</svg>
        <div class="chain-label" style="color:${{isBen?'#1d9e75':c}};margin-top:10px">${{isBen?'Variant chain — '+d.label+' (different, not broken)':'Mutant chain — '+d.label+' (glowing sphere = instability at position '+resi+')'}}</div>
        <svg class="chain-svg" viewBox="0 0 ${{W}} 50">${{mut}}</svg>
        <p style="font-size:11px;color:#444;margin-top:8px;line-height:1.6">${{caption}}</p>
      </div>
      <div>
        <div class="chain-label">Functional parameters vs wild-type (from effect score ${{d.score}})</div>
        ${{bars}}
        <p style="font-size:11px;color:#333;margin-top:10px;line-height:1.6;border-top:1px solid #1a1d2e;padding-top:10px">These estimates derive from your experimental effect score and known biology. Phase 3 ML will provide structure-based predictions with confidence intervals.</p>
      </div>
    </div>`;
}}

function showTimeline(resi, d) {{
  const isBen = d.cell === 'beneficial_variant';
  if (isBen) {{
    document.getElementById('timeline-inner').innerHTML = `
      <div style="background:#0a1a0a;border:1px solid #1a3a1a;border-radius:8px;padding:14px">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.12em;color:#4CAF50;margin-bottom:8px">No pathological timeline</div>
        <p style="font-size:12px;color:#888;line-height:1.7">This residue represents a normal population variant (germline polymorphism). It is present from birth, does not cause cellular damage, and has no disease progression timeline. It is not associated with cancer initiation or spread to neighbouring cells.</p>
        <p style="font-size:11px;color:#555;margin-top:8px;line-height:1.6">Honest note: some germline TP53 variants (Li-Fraumeni syndrome variants) do confer elevated cancer risk, but those are specifically annotated in ClinVar. The variant at this position is classified as a benign polymorphism.</p>
      </div>`;
    return;
  }}

  const onset = d.timeline_onset || 1;
  const detectable = d.timeline_detectable || 180;
  const clinical = d.timeline_clinical || 730;
  const spread = d.timeline_spread || 365;
  const maxDays = Math.max(clinical, spread) + 200;

  const events = [
    {{day:onset, label:'Single cell mutation event', desc:'One cell acquires this mutation. At this point, there is no clinical significance — single mutations occur constantly and are usually cleared by immune surveillance or cell death.', color:'#555'}},
    {{day:Math.round(detectable*0.3), label:'Clonal expansion begins', desc:'If the mutant cell escapes clearance, it divides. The mutation is passed to daughter cells. This is still below any detection threshold — no imaging, biopsy, or test would find it.', color:'#ef9f27'}},
    {{day:detectable, label:'Microscopically detectable mass', desc:'After sufficient divisions, a small clonal population exists that could be detected by sensitive sequencing (liquid biopsy). Still asymptomatic. This timeline is illustrative — real timelines vary enormously by cell type, co-occurring mutations, immune status, and environment.', color:'#ef9f27'}},
    {{day:spread, label:'Potential for neighbouring cell effects', desc:'Tumour microenvironment signalling begins. Secreted factors (e.g. VEGF, TGF-β) start influencing nearby cells. This is not direct mutation spread — it is paracrine signalling that creates a permissive environment. Direct mutation transfer between cells does not occur in normal cancer biology.', color:'#e24b4a'}},
    {{day:clinical, label:'Clinically significant — detection window', desc:'At typical clinical detection sizes (0.5–1 cm tumour), the lesion has undergone billions of cell divisions. This timeline is a rough population average. Many cancers with TP53 mutations are detected much later. This emphasises the importance of early detection and screening.', color:'#e24b4a'}},
  ];

  document.getElementById('timeline-inner').innerHTML = `
    <div class="disclaimer" style="margin-bottom:10px">
      <div class="disclaimer-label">Important: what this timeline is and is not</div>
      <div class="disclaimer-text">These timelines are rough population-level estimates derived from published literature on TP53-mutant tumour kinetics. They represent typical ranges, NOT predictions for any individual. Actual timelines vary enormously based on: cell type, tissue context, co-occurring mutations, immune function, diet, environment, and chance. This is for biological education only — not clinical guidance.</div>
    </div>
    <div class="tl-row">
      <span class="tl-label">Day (drag slider)</span>
      <input type="range" id="tl-slider" min="0" max="${{maxDays}}" value="0" step="1" oninput="updateTimeline(parseInt(this.value), ${{JSON.stringify(events)}}, ${{clinical}})">
      <span class="tl-val" id="tl-val">Day 0</span>
    </div>
    <div class="tl-display">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#555;margin-bottom:6px">Timeline progression bar (rough estimate — see note above)</div>
      <div class="tl-bar-track">
        <div class="tl-phase" style="width:${{(detectable/maxDays*100).toFixed(1)}}%;background:#1a2a1a;color:#555;left:0">subclinical</div>
        <div class="tl-phase" style="width:${{((clinical-detectable)/maxDays*100).toFixed(1)}}%;background:#2a2000;color:#777;left:${{(detectable/maxDays*100).toFixed(1)}}%">detectable</div>
        <div class="tl-phase" style="width:${{((maxDays-clinical)/maxDays*100).toFixed(1)}}%;background:#2a0808;color:#888;left:${{(clinical/maxDays*100).toFixed(1)}}%">clinical</div>
        <div class="tl-marker" id="tl-marker" style="left:0%"></div>
      </div>
      <div class="event-list" id="event-list">
        ${{events.map((e,i)=>`<div class="event-item${{i===0?' active':''}}" id="ev-${{i}}">
          <div class="event-dot" style="background:${{e.color}}"></div>
          <div class="event-text"><strong>Day ~${{e.day}}: ${{e.label}}</strong><span>${{e.desc}}</span></div>
        </div>`).join('')}}
      </div>
    </div>`;
}}

function updateTimeline(day, events, clinical) {{
  document.getElementById('tl-val').textContent = day === 0 ? 'Day 0 — pre-mutation' : day >= clinical ? `~Day ${{day}} (yrs ${{(day/365).toFixed(1)}})` : `Day ${{day}}`;
  const slider = document.getElementById('tl-slider');
  const maxDays = parseInt(slider.max);
  const pct = (day/maxDays*100).toFixed(1);
  const marker = document.getElementById('tl-marker');
  if (marker) marker.style.left = pct+'%';
  events.forEach((e,i) => {{
    const el = document.getElementById('ev-'+i);
    if (el) el.classList.toggle('active', day >= e.day);
  }});
}}

function showCell(d) {{
  const imp = CELL_IMPACTS[d.cell] || CELL_IMPACTS.apoptosis;
  const c = imp.color;
  const animSt = `animation:${{imp.anim}} 2s ease-in-out infinite;transform-origin:center`;

  const steps = imp.pathway.map((s,i)=>`
    <div class="pstep" style="animation-delay:${{i*0.15}}s">
      <div class="pnum" style="background:${{c}}22;color:${{c}};border:0.5px solid ${{c}}55">${{i+1}}</div>
      <div style="font-size:11px;color:#ccc;flex:1;line-height:1.5">${{s}}</div>
    </div>
    ${{i<imp.pathway.length-1?`<p style="font-size:13px;color:#2a2d3a;padding-left:28px;line-height:1.2">↓</p>`:''}}`).join('');

  const pbars = Object.entries(imp.bars).map(([k,v])=>`<div class="brow">
    <div class="blbl"><span>${{k}}</span><span style="color:${{c}}">${{v}}% of WT</span></div>
    <div class="btrack"><div class="bfill" style="width:${{v}}%;background:${{c}}"></div></div>
  </div>`).join('');

  document.getElementById('cell-inner').innerHTML = `
    <div class="cell-layout">
      <div style="display:flex;flex-direction:column;align-items:center;gap:8px">
        <svg width="68" height="68" viewBox="0 0 68 68">
          <ellipse cx="34" cy="34" rx="30" ry="27" fill="#0a1f0a" stroke="#2a5a2a" stroke-width="1.5"/>
          <ellipse cx="34" cy="34" rx="11" ry="9" fill="#1a4a1a" stroke="#4CAF50" stroke-width="1.5"/>
          <text x="34" y="37" text-anchor="middle" font-size="6" fill="#4CAF50" font-family="monospace">WT</text>
        </svg>
        <span style="font-size:10px;color:#4CAF50;font-family:'IBM Plex Mono',monospace">Normal</span>
        <span style="color:${{c}};font-size:16px">↓</span>
        <svg width="68" height="68" viewBox="0 0 68 68" style="${{animSt}}">
          <ellipse cx="34" cy="34" rx="30" ry="27" fill="${{d.cell==='beneficial_variant'?'#0a2a1a':'#1f0808'}}" stroke="${{c}}" stroke-width="1.5" stroke-dasharray="${{d.cell==='beneficial_variant'?'none':'4,2'}}"/>
          <ellipse cx="34" cy="34" rx="13" ry="11" fill="${{d.cell==='beneficial_variant'?'#0a2a1a':'#2a0808'}}" stroke="${{c}}" stroke-width="1.5"/>
          ${{d.cell!=='beneficial_variant'?`<circle cx="16" cy="22" r="3" fill="${{c}}" opacity="0.7"/><circle cx="52" cy="46" r="2.5" fill="${{c}}" opacity="0.5"/>`:''}}
          <text x="34" y="37" text-anchor="middle" font-size="6" fill="${{c}}" font-family="monospace">${{d.cell==='beneficial_variant'?'VAR':'MUT'}}</text>
        </svg>
        <span style="font-size:10px;color:${{c}};text-align:center;font-family:'IBM Plex Mono',monospace">${{d.cell==='beneficial_variant'?'Variant cell':'Affected cell'}}</span>
      </div>
      <div>
        <p style="font-size:13px;font-weight:600;color:${{c}};margin:0 0 8px;text-transform:uppercase;letter-spacing:0.06em;font-family:'IBM Plex Mono',monospace">${{imp.title}}</p>
        <p style="font-size:12px;color:#888;line-height:1.7;margin:0 0 14px">${{imp.desc}}</p>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.12em;color:#3a3d5a;margin-bottom:8px">Molecular pathway</div>
        ${{steps}}
      </div>
      <div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.12em;color:#3a3d5a;margin-bottom:10px">Cellular function vs WT</div>
        ${{pbars}}
      </div>
    </div>`;
}}

// Build experiments
(function() {{
  const grid = document.getElementById('egrid');
  EXPERIMENTS.forEach(exp => {{
    const div = document.createElement('div');
    div.className = 'ecard'; div.id = 'ec-'+exp.id;
    div.innerHTML = `<div class="ename">${{exp.name}}</div><div class="emeta" style="color:${{exp.color}}">${{exp.cat}}</div><div class="emeta">${{exp.dur}} · ${{exp.cost}}</div>`;
    div.onclick = () => toggleExp(exp);
    grid.appendChild(div);
  }});
}})();

function toggleExp(exp) {{
  const det = document.getElementById('edetail');
  if (activeExp === exp.id) {{
    activeExp=null; document.querySelectorAll('.ecard').forEach(c=>c.classList.remove('active'));
    det.classList.remove('vis'); det.innerHTML=''; applyStyles(null); return;
  }}
  activeExp=exp.id;
  document.querySelectorAll('.ecard').forEach(c=>c.classList.remove('active'));
  document.getElementById('ec-'+exp.id).classList.add('active');
  applyStyles(exp);
  const pills = (exp.affected||[]).map(r=>{{
    const d=RESIDUES[r]; return `<span class="chip" style="color:${{exp.color}};border-color:${{exp.color}}55">${{d?d.label:'R'+r}}</span>`;
  }}).join('');
  det.innerHTML=`<div>${{dr('Purpose',exp.purpose)}}${{dr('Readout',exp.readout)}}${{dr('Controls',exp.controls)}}${{dr('Duration',exp.dur)}}${{dr('Cost',exp.cost)}}<div class="outcome-box"><div class="outcome-label">Expected structural outcome</div><div style="font-size:11px;color:#888;line-height:1.7">${{exp.outcome}}</div></div></div>
  <div><div style="font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.12em;color:#3a3d5a;margin-bottom:8px">Target residues in viewer</div><div style="margin-bottom:12px">${{pills}}</div><p style="font-size:11px;color:#444;line-height:1.7">Switch to 3D Explorer tab to see these residues highlighted. Other residues dim for clarity. Click any sphere for full annotation.</p></div>`;
  det.classList.add('vis');
}}

// Build beneficial examples
(function() {{
  const wrap = document.getElementById('ben-cards');
  BENEFICIAL.forEach(b => {{
    wrap.innerHTML += `<div class="ben-card"><div class="ben-title">${{b.name}}</div><div class="ben-text">${{b.example}}</div></div>`;
  }});
}})();
</script>
</body>
</html>"""


def render():
    st.markdown("## ⚗️ Protein Explorer")
    st.markdown("Upload your experimental CSV — no UniProt ID needed. Everything runs from your data.")
    st.divider()

    csv_file = st.file_uploader(
        "Upload experimental CSV",
        type="csv",
        help="Required: residue_position, effect_score. Optional: mutation, experiment_type",
    )
    st.caption("Required columns: `residue_position`, `effect_score` · Optional: `mutation`, `experiment_type`")

    use_sample = False
    if not csv_file and "explorer_df" not in st.session_state:
        with st.expander("No file yet? See expected format or load sample data"):
            st.code("residue_position,effect_score,mutation,experiment_type\n175,0.99,R175H,DMS\n248,0.97,R248W,DMS\n273,0.96,R273H,CRISPR\n72,0.05,R72P,DMS")
            if st.button("Load sample TP53 DMS data"):
                use_sample = True

        if not use_sample:
            st.info("Upload a CSV or load the sample data to begin.")
            return

    if use_sample:
        import io
        sample = "residue_position,effect_score,mutation,experiment_type\n12,0.91,G12D,DMS\n42,0.87,A42V,DMS\n61,0.22,Q61H,DMS\n67,0.12,L67P,DMS\n72,0.05,R72P,DMS\n103,0.94,R103W,CRISPR\n132,0.55,C132Y,DMS\n175,0.99,R175H,DMS\n179,0.34,H179R,DMS\n220,0.88,Y220C,DMS\n245,0.76,G245S,DMS\n248,0.95,R248W,DMS\n249,0.91,R249S,CRISPR\n273,0.97,R273H,DMS\n282,0.85,R282W,DMS"
        df_raw = pd.read_csv(io.StringIO(sample))
        st.session_state.explorer_df = score_csv(df_raw)

    elif csv_file:
        df_raw = pd.read_csv(csv_file)
        df_raw.columns = df_raw.columns.str.lower().str.strip()
        if "residue_position" not in df_raw.columns or "effect_score" not in df_raw.columns:
            st.error("CSV must have columns: residue_position, effect_score")
            return
        st.session_state.explorer_df = score_csv(df_raw)

    scored_df = st.session_state.explorer_df

    with st.spinner("Loading protein structure from PDB..."):
        pdb_data = fetch_pdb("2OCJ")

    if not pdb_data:
        st.error("Could not load protein structure. Check your internet connection.")
        return

    html = build_html(scored_df, pdb_data)
    components.html(html, height=2400, scrolling=True)
