"""
protein_explorer.py — Protellect Advanced Protein Explorer
Self-contained: residue click info panel lives inside the HTML component,
no Streamlit round-trip needed.
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import requests

RESIDUE_DATA = {
    175: {
        "label": "R175H", "status": "critical",
        "name": "Arginine → Histidine",
        "domain": "DNA-binding domain (L2 loop)",
        "mechanism": "Disrupts zinc ion coordination at the C176/H179/C238/C242 tetrahedral site. Causes global misfolding of the DNA-binding domain — the most common TP53 hotspot.",
        "frequency": "~6% of all human cancers",
        "cancer_types": "Breast, lung, colorectal, ovarian, bladder, sarcoma",
        "functional_class": "Loss-of-function + dominant negative",
        "clinvar": "Pathogenic · 847 submissions",
        "uniprot": "Disrupts zinc binding; thermodynamic destabilization",
        "conservation": "100% conserved across vertebrates",
        "effect_score": 0.99,
        "sources": ["UniProt P04637", "ClinVar VCV000012375", "COSMIC v97"],
        "therapeutic": "APR-246 (eprenetapopt) — refolding compound, Phase III",
    },
    248: {
        "label": "R248W/Q", "status": "critical",
        "name": "Arginine → Tryptophan / Glutamine",
        "domain": "DNA-binding domain (L3 loop)",
        "mechanism": "Direct DNA contact residue. R248 makes hydrogen bonds to the minor groove at CATG sequences. Substitution abolishes sequence-specific DNA binding entirely.",
        "frequency": "~3% of all cancers",
        "cancer_types": "Colorectal, lung, pancreatic, ovarian",
        "functional_class": "Loss-of-function (contact mutation)",
        "clinvar": "Pathogenic · 623 submissions",
        "uniprot": "Critical DNA contact; mutation eliminates sequence-specific binding",
        "conservation": "100% conserved",
        "effect_score": 0.97,
        "sources": ["UniProt P04637", "ClinVar VCV000012376", "IARC TP53 DB"],
        "therapeutic": "No approved targeted therapy; synthetic lethality under investigation",
    },
    273: {
        "label": "R273H/C", "status": "critical",
        "name": "Arginine → Histidine / Cysteine",
        "domain": "DNA-binding domain (S10 strand)",
        "mechanism": "DNA backbone phosphate contact. Loss of R273 reduces DNA-binding affinity >100-fold. R273C retains partial structure; R273H is completely non-functional.",
        "frequency": "~3% of all cancers",
        "cancer_types": "Colorectal, lung, brain, pancreatic",
        "functional_class": "Loss-of-function (contact mutation)",
        "clinvar": "Pathogenic · 512 submissions",
        "uniprot": "DNA backbone phosphate contact residue",
        "conservation": "100% conserved",
        "effect_score": 0.96,
        "sources": ["UniProt P04637", "ClinVar VCV000012377", "COSMIC v97"],
        "therapeutic": "Experimental: small molecule stabilizers for contact mutants",
    },
    249: {
        "label": "R249S", "status": "critical",
        "name": "Arginine → Serine",
        "domain": "DNA-binding domain (H2 helix)",
        "mechanism": "Structural mutation disrupting H2 helix. Highly enriched in hepatocellular carcinoma — characteristic aflatoxin B1 mutational signature. Also disrupts HIPK2 interaction.",
        "frequency": "~1.5% of cancers; prevalent in liver cancer",
        "cancer_types": "Liver (HCC), lung, esophageal",
        "functional_class": "Loss-of-function + gain-of-function",
        "clinvar": "Pathogenic · 298 submissions",
        "uniprot": "H2 helix structural mutation; aflatoxin B1 signature",
        "conservation": "100% conserved",
        "effect_score": 0.91,
        "sources": ["UniProt P04637", "ClinVar VCV000012378", "IARC TP53 DB"],
        "therapeutic": "No specific therapy; aflatoxin avoidance in endemic regions",
    },
    245: {
        "label": "G245S/D", "status": "critical",
        "name": "Glycine → Serine / Aspartate",
        "domain": "DNA-binding domain (L3 loop)",
        "mechanism": "Glycine is essential at this position — any side chain clashes sterically with the DNA backbone, disrupting L3 loop geometry and preventing proper DNA approach.",
        "frequency": "~1.5% of cancers",
        "cancer_types": "Breast, lung, sarcoma, hematologic malignancies",
        "functional_class": "Loss-of-function (structural)",
        "clinvar": "Pathogenic · 187 submissions",
        "uniprot": "L3 loop glycine; essential for loop geometry",
        "conservation": "100% conserved",
        "effect_score": 0.88,
        "sources": ["UniProt P04637", "ClinVar VCV000012379", "COSMIC v97"],
        "therapeutic": "Under investigation — structural correctors for L3 loop mutants",
    },
    282: {
        "label": "R282W", "status": "critical",
        "name": "Arginine → Tryptophan",
        "domain": "DNA-binding domain (H2 helix)",
        "mechanism": "R282 forms a salt bridge with E271 stabilizing the H2 helix. Tryptophan disrupts this interaction causing partial helix unfolding and secondary effects on DNA binding.",
        "frequency": "~1% of cancers",
        "cancer_types": "Breast, colorectal, lung",
        "functional_class": "Loss-of-function (structural)",
        "clinvar": "Pathogenic · 156 submissions",
        "uniprot": "H2 helix salt bridge with E271",
        "conservation": "99% conserved",
        "effect_score": 0.85,
        "sources": ["UniProt P04637", "ClinVar VCV000012380"],
        "therapeutic": "No approved targeted therapy",
    },
    176: {
        "label": "C176", "status": "affected",
        "name": "Cysteine 176 — zinc ligand",
        "domain": "DNA-binding domain — zinc coordination",
        "mechanism": "One of four zinc-coordinating residues (C176, H179, C238, C242). Directly adjacent to R175. The R175H mutation disrupts local geometry around C176, loosening zinc coordination without directly mutating it.",
        "frequency": "Rarely mutated directly; affected by R175H",
        "cancer_types": "N/A — secondary structural effect",
        "functional_class": "Zinc ligand — indirectly disrupted",
        "clinvar": "Not directly pathogenic",
        "uniprot": "Zinc ligand (Cys-176); tetrahedral coordination site",
        "conservation": "100% conserved",
        "effect_score": 0.60,
        "sources": ["UniProt P04637", "PDB 2OCJ structural analysis"],
        "therapeutic": "APR-246 targets C176 directly as a refolding scaffold",
    },
    179: {
        "label": "H179", "status": "affected",
        "name": "Histidine 179 — zinc ligand",
        "domain": "DNA-binding domain — zinc coordination",
        "mechanism": "Second zinc-coordinating histidine. Indirectly destabilized by R175H through propagated structural changes in the L2 loop. The zinc ion becomes mobile, increasing protein dynamics.",
        "frequency": "Rarely mutated directly",
        "cancer_types": "N/A — secondary structural effect",
        "functional_class": "Zinc ligand — indirectly affected",
        "clinvar": "Uncertain significance when directly mutated",
        "uniprot": "Zinc ligand (His-179); part of tetrahedral coordination",
        "conservation": "100% conserved",
        "effect_score": 0.55,
        "sources": ["UniProt P04637", "PDB 2OCJ"],
        "therapeutic": "N/A",
    },
    220: {
        "label": "Y220C", "status": "affected",
        "name": "Tyrosine → Cysteine",
        "domain": "DNA-binding domain (S7-S8 loop)",
        "mechanism": "Creates a surface hydrophobic cavity that destabilizes the domain thermodynamically. Not a DNA contact but reduces overall fold stability. Notably, the cavity is a druggable pocket targeted by PC14586.",
        "frequency": "~1% of cancers",
        "cancer_types": "Breast, lung, ovarian",
        "functional_class": "Loss-of-function (thermodynamic destabilization)",
        "clinvar": "Pathogenic · 89 submissions",
        "uniprot": "Surface residue; Y220C creates druggable hydrophobic cavity",
        "conservation": "98% conserved",
        "effect_score": 0.78,
        "sources": ["UniProt P04637", "ClinVar VCV000012381", "COSMIC v97"],
        "therapeutic": "PC14586 (rezatapopt) — specifically fills Y220C cavity, Phase II trials",
    },
    100: {
        "label": "P100", "status": "normal",
        "name": "Proline 100",
        "domain": "Proline-rich region (transactivation domain II)",
        "mechanism": "Structural proline in the flexible linker region. Located far from the DNA-binding domain. Mutations here are generally tolerated and do not affect transcriptional activity significantly.",
        "frequency": "Rarely mutated; tolerated when mutated",
        "cancer_types": "Not specifically associated",
        "functional_class": "Structural / neutral",
        "clinvar": "Benign / likely benign",
        "uniprot": "PXXP motif for SH3-domain interactions",
        "conservation": "Moderately conserved",
        "effect_score": 0.08,
        "sources": ["UniProt P04637"],
        "therapeutic": "N/A",
    },
    150: {
        "label": "V150", "status": "normal",
        "name": "Valine 150",
        "domain": "DNA-binding domain (beta-sheet core)",
        "mechanism": "Interior beta-sheet residue contributing to hydrophobic core stability. Not involved in DNA binding or zinc coordination. Conservative substitutions are generally tolerated.",
        "frequency": "Rarely mutated in cancer",
        "cancer_types": "Not specifically associated",
        "functional_class": "Structural — tolerated variation",
        "clinvar": "Likely benign",
        "uniprot": "Core beta-sheet residue; conservative substitutions tolerated",
        "conservation": "Moderately conserved",
        "effect_score": 0.12,
        "sources": ["UniProt P04637", "ProtaBank DMS dataset"],
        "therapeutic": "N/A",
    },
}

EXPERIMENTS = [
    {
        "id": "thermal_shift",
        "name": "Thermal Shift Assay",
        "category": "Structural",
        "duration": "2–3 days", "cost": "~$200–500",
        "purpose": "Measures thermostability. R175H reduces Tm by ~8–10°C vs WT, directly confirming domain destabilization.",
        "readout": "Melting temperature (Tm). WT TP53 DBD: ~42°C. R175H: ~32–34°C.",
        "controls": "WT TP53 DBD, R248W, known stabilizing compounds",
        "outcome_title": "Global Destabilization",
        "outcome": "R175H causes the entire DNA-binding domain to partially unfold at physiological temperature. The zinc coordination site collapses, propagating structural disorder through the L2 loop and destabilizing residues C176, H179, and the surrounding beta-sheet core.",
        "affected": [175, 176, 179, 220],
        "effect_color": "#FF4C4C",
    },
    {
        "id": "emsa",
        "name": "EMSA",
        "category": "Functional",
        "duration": "1–2 days", "cost": "~$100–300",
        "purpose": "Directly measures DNA binding. R175H shows complete loss of sequence-specific DNA binding due to misfolding of the contact interface.",
        "readout": "Band shift on gel. WT: retarded band (protein-DNA complex). R175H: no shift (free DNA only).",
        "controls": "WT TP53, consensus p53RE oligo, non-specific oligo, supershift antibody",
        "outcome_title": "Loss of DNA Binding Interface",
        "outcome": "The DNA-binding interface becomes inaccessible because R175H-induced misfolding repositions the L3 loop. R248 and R273 are physically present but structurally displaced — they cannot reach DNA. The protein accumulates but is transcriptionally inert.",
        "affected": [175, 248, 273, 245],
        "effect_color": "#FF8C00",
    },
    {
        "id": "reporter",
        "name": "Luciferase Reporter",
        "category": "Functional",
        "duration": "3–5 days", "cost": "~$300–600",
        "purpose": "Measures transcriptional transactivation in cells. R175H completely abrogates p21, MDM2, and PUMA promoter activation.",
        "readout": "Relative luminescence (RLU). R175H: <5% of WT activity on p21/MDM2/PUMA reporters.",
        "controls": "WT p53, empty vector, p53-null H1299 cells, p21-luc / MDM2-luc reporters",
        "outcome_title": "Complete Transcriptional Silence",
        "outcome": "R175H protein accumulates in the nucleus (NLS intact) but fails to activate any canonical p53 target genes. Additionally exerts dominant negative effects on remaining WT p53 allele by forming mixed tetramers that poison the complex.",
        "affected": [175, 176, 179, 248, 273],
        "effect_color": "#CC44CC",
    },
    {
        "id": "apr246",
        "name": "APR-246 Rescue",
        "category": "Therapeutic",
        "duration": "5–7 days", "cost": "~$500–1200",
        "purpose": "Tests whether APR-246 (eprenetapopt) can refold R175H and restore WT-like function via covalent modification of cysteines.",
        "readout": "Tm increase (+4–6°C), partial EMSA band shift, reporter recovery to ~20–40% WT, cell viability reduction in R175H lines.",
        "controls": "DMSO vehicle, WT p53, R175H without drug, dose-response curve",
        "outcome_title": "Partial Structural Rescue",
        "outcome": "APR-246 active form (MQ) covalently binds C176 and C238, acting as a zinc-independent scaffold that partially restores DNA-binding conformation. R248 and R273 are repositioned toward WT geometry. Rescue is partial — not complete restoration.",
        "affected": [175, 176, 179, 248],
        "effect_color": "#4CA8FF",
    },
    {
        "id": "coip",
        "name": "Co-IP Dominant Negative",
        "category": "Mechanistic",
        "duration": "3–4 days", "cost": "~$400–800",
        "purpose": "Confirms R175H forms mixed tetramers with WT p53, exerting dominant negative suppression even when one WT allele is retained.",
        "readout": "Pull-down of WT p53 by anti-mutant antibody. Western blot confirmation of mixed tetramer.",
        "controls": "IgG isotype, WT-only cells, R175H-only cells, mixed transfection",
        "outcome_title": "Dominant Negative Tetramerization",
        "outcome": "R175H co-precipitates with WT p53. Mixed tetramers (2x R175H + 2x WT) show dramatically reduced DNA-binding vs pure WT tetramer. This explains why heterozygous R175H still drives aggressive cancer — the mutant poisons the remaining WT copies.",
        "affected": [175, 248, 273],
        "effect_color": "#FF4C4C",
    },
]


def fetch_pdb_structure(pdb_id="2OCJ"):
    try:
        r = requests.get(f"https://files.rcsb.org/download/{pdb_id}.pdb", timeout=15)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def build_full_viewer_html(pdb_data):
    """
    Single self-contained HTML component.
    - 3D viewer on the left
    - Info panel on the right, populated by JS on residue click
    - Experiment list below, clicking updates the 3D view highlighting
    """
    residue_json = json.dumps(RESIDUE_DATA, default=str)
    experiment_json = json.dumps(EXPERIMENTS, default=str)
    pdb_escaped = pdb_data.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")[:300000]

    return f"""<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #080b14; font-family: 'IBM Plex Sans', sans-serif; color: #ccc; font-size: 13px; }}

  #top {{ display: flex; gap: 16px; height: 500px; }}
  #viewer-wrap {{ flex: 1.4; position: relative; border: 1px solid #1e2030; border-radius: 8px; overflow: hidden; }}
  #viewer {{ width: 100%; height: 100%; }}

  #tooltip {{
    position: absolute; top: 10px; left: 10px;
    background: #0f1117ee; border: 1px solid #2a2d3a;
    border-radius: 6px; padding: 8px 12px;
    font-size: 11px; font-family: 'IBM Plex Mono', monospace;
    color: #ccc; pointer-events: none;
    display: none; z-index: 100; max-width: 200px; line-height: 1.5;
  }}

  #click-hint {{
    position: absolute; bottom: 10px; left: 50%; transform: translateX(-50%);
    background: #0f1117cc; border: 1px solid #2a2d3a; border-radius: 20px;
    padding: 5px 14px; font-size: 10px; font-family: 'IBM Plex Mono', monospace;
    color: #555; white-space: nowrap;
  }}

  #info-panel {{
    flex: 1;
    background: #0a0c14;
    border: 1px solid #1e2030;
    border-radius: 8px;
    padding: 16px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}

  .panel-placeholder {{
    color: #333;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    text-align: center;
    margin: auto;
    line-height: 2;
  }}

  .section-label {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #444;
    padding-bottom: 5px;
    border-bottom: 1px solid #1a1d2e;
    margin-bottom: 4px;
  }}

  .residue-header {{
    border-left: 3px solid #ccc;
    padding-left: 10px;
  }}
  .residue-title {{ font-size: 16px; font-weight: 700; color: #eee; }}
  .residue-sub {{ font-size: 11px; color: #666; margin-top: 2px; }}
  .status-badge {{
    display: inline-block;
    padding: 2px 10px; border-radius: 20px;
    font-size: 9px; font-family: 'IBM Plex Mono', monospace;
    font-weight: 600; letter-spacing: 0.1em;
    margin-bottom: 8px;
  }}

  .info-row {{ display: flex; gap: 8px; padding: 5px 0; border-bottom: 1px solid #12141e; font-size: 11px; }}
  .info-lbl {{ color: #444; min-width: 100px; font-family: 'IBM Plex Mono', monospace; font-size: 10px; padding-top: 1px; flex-shrink: 0; }}
  .info-val {{ color: #aaa; line-height: 1.5; }}

  .source-chip {{
    display: inline-block; background: #12141e; border: 1px solid #1e2030;
    border-radius: 3px; padding: 1px 6px;
    font-size: 9px; font-family: 'IBM Plex Mono', monospace; color: #555; margin: 2px 2px 2px 0;
  }}

  /* Legend */
  #legend {{ display: flex; gap: 16px; padding: 10px 0; flex-wrap: wrap; }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 11px; color: #666; }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}

  /* Experiments */
  #experiments {{ margin-top: 16px; }}
  .exp-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-top: 10px; }}
  .exp-card {{
    background: #0a0c14; border: 1px solid #1e2030; border-radius: 8px;
    padding: 12px; cursor: pointer; transition: all 0.2s;
  }}
  .exp-card:hover {{ border-color: #3a3d5a; background: #0f1117; }}
  .exp-card.active {{ border-color: #FF4C4C; background: #150808; }}
  .exp-name {{ font-size: 12px; font-weight: 600; color: #ddd; margin-bottom: 4px; }}
  .exp-meta {{ font-size: 10px; font-family: 'IBM Plex Mono', monospace; }}
  .cat-Structural {{ color: #4CA8FF; }}
  .cat-Functional {{ color: #FFA500; }}
  .cat-Therapeutic {{ color: #4CAF50; }}
  .cat-Mechanistic {{ color: #CC88FF; }}

  /* Experiment detail */
  #exp-detail {{
    display: none; margin-top: 14px;
    background: #0a0c14; border: 1px solid #1e2030; border-radius: 8px; padding: 16px;
  }}
  #exp-detail.visible {{ display: block; }}
  .exp-detail-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 12px; }}
  .outcome-box {{
    background: #080b10; border: 1px solid #1a2a1a; border-radius: 6px; padding: 12px;
    font-size: 11px; color: #999; line-height: 1.7; margin-top: 10px;
  }}
  .outcome-label {{ font-family: 'IBM Plex Mono', monospace; font-size: 9px; text-transform: uppercase; letter-spacing: 0.12em; color: #4CAF50; margin-bottom: 6px; }}
  .affected-pills {{ margin-top: 8px; }}
  .a-pill {{
    display: inline-block; padding: 2px 8px; border-radius: 12px;
    font-size: 10px; font-family: 'IBM Plex Mono', monospace; font-weight: 600;
    background: #FF4C4C22; color: #FF4C4C; border: 1px solid #FF4C4C44;
    margin: 2px;
  }}
</style>
</head>
<body>

<div id="top">
  <div id="viewer-wrap">
    <div id="viewer"></div>
    <div id="tooltip"></div>
    <div id="click-hint">● Click any residue sphere for details</div>
  </div>

  <div id="info-panel">
    <div class="panel-placeholder">
      Click any residue sphere<br>on the structure<br>to load its details here
    </div>
  </div>
</div>

<div id="legend">
  <div class="legend-item"><div class="legend-dot" style="background:#FF4C4C;"></div> Critical — direct mutation / hotspot</div>
  <div class="legend-item"><div class="legend-dot" style="background:#FFA500;"></div> Affected — downstream structural impact</div>
  <div class="legend-item"><div class="legend-dot" style="background:#4CA8FF;"></div> No significant effect</div>
  <div class="legend-item"><div class="legend-dot" style="background:#ffffff;"></div> Selected residue</div>
</div>

<div id="experiments">
  <div class="section-label">Experimental Pathways — click to visualize structural change</div>
  <div class="exp-grid" id="exp-grid"></div>
  <div id="exp-detail"></div>
</div>

<script>
const RESIDUES = {residue_json};
const EXPERIMENTS = {experiment_json};
const pdbData = `{pdb_escaped}`;

let viewer;
let selectedResi = null;
let activeExp = null;

// ── Build viewer ──────────────────────────────────────────────────────────
viewer = $3Dmol.createViewer('viewer', {{ backgroundColor: '#080b14', antialias: true }});
viewer.addModel(pdbData, 'pdb');

function applyBaseStyles(highlightExp) {{
  viewer.setStyle({{}}, {{cartoon: {{color: '#1a1d2e', opacity: 0.45}}}});
  viewer.addStyle({{resi: '94-292'}}, {{cartoon: {{color: '#1e2440', opacity: 0.65}}}});

  for (const [resi, data] of Object.entries(RESIDUES)) {{
    const r = parseInt(resi);
    let color, radius, opacity;

    if (highlightExp) {{
      // Dim everything not in the experiment
      if (highlightExp.affected.includes(r)) {{
        color = highlightExp.effect_color;
        radius = 1.0;
        opacity = 1.0;
      }} else {{
        color = data.status === 'critical' ? '#FF4C4C' : data.status === 'affected' ? '#FFA500' : '#4CA8FF';
        radius = 0.35;
        opacity = 0.2;
      }}
    }} else {{
      color = data.status === 'critical' ? '#FF4C4C' : data.status === 'affected' ? '#FFA500' : '#4CA8FF';
      radius = data.status === 'critical' ? 0.85 : data.status === 'affected' ? 0.65 : 0.42;
      opacity = 1.0;
    }}

    viewer.addStyle({{resi: r}}, {{sphere: {{color, radius, opacity}}}});
  }}

  // Selected residue highlight
  if (selectedResi) {{
    viewer.addStyle({{resi: selectedResi}}, {{sphere: {{color: '#ffffff', radius: 1.1, opacity: 1.0}}}});
  }}

  viewer.render();
}}

// ── Residue click / hover ─────────────────────────────────────────────────
viewer.setHoverable({{}}, true,
  function(atom) {{
    if (!atom || !atom.resi) return;
    const data = RESIDUES[atom.resi];
    const tt = document.getElementById('tooltip');
    if (data) {{
      const c = data.status === 'critical' ? '#FF4C4C' : data.status === 'affected' ? '#FFA500' : '#4CA8FF';
      tt.innerHTML = '<span style="color:' + c + ';font-weight:700">' + data.label + '</span><br><span style="color:#888;font-size:10px">Residue ' + atom.resi + ' · Score: ' + data.effect_score + '</span><br><span style="color:#555;font-size:10px">Click for full info →</span>';
      tt.style.display = 'block';
    }}
  }},
  function() {{ document.getElementById('tooltip').style.display = 'none'; }}
);

viewer.setClickable({{}}, true, function(atom) {{
  if (!atom || !atom.resi) return;
  const resi = atom.resi;
  const data = RESIDUES[resi];
  if (!data) return;
  selectedResi = resi;
  applyBaseStyles(activeExp ? EXPERIMENTS.find(e => e.id === activeExp) : null);
  showResiduePanel(resi, data);
}});

viewer.zoomTo({{resi: '94-292'}});
applyBaseStyles(null);

// ── Info panel ────────────────────────────────────────────────────────────
function showResiduePanel(resi, data) {{
  const statusColor = data.status === 'critical' ? '#FF4C4C' : data.status === 'affected' ? '#FFA500' : '#4CA8FF';
  const statusLabel = data.status === 'critical' ? 'CRITICAL' : data.status === 'affected' ? 'AFFECTED BY CRITICAL' : 'NO SIGNIFICANT EFFECT';
  const sourcesHtml = data.sources.map(s => '<span class="source-chip">' + s + '</span>').join('');

  document.getElementById('info-panel').innerHTML = `
    <div>
      <div class="status-badge" style="background:${{statusColor}}22;color:${{statusColor}};border:1px solid ${{statusColor}}55;">${{statusLabel}}</div>
      <div class="residue-header" style="border-left-color:${{statusColor}}">
        <div class="residue-title">Residue ${{resi}} — ${{data.label}}</div>
        <div class="residue-sub">${{data.name}}</div>
      </div>
    </div>

    <div>
      <div class="section-label">Biological Details</div>
      ${{infoRow('Domain', data.domain)}}
      ${{infoRow('Mechanism', data.mechanism)}}
      ${{infoRow('Frequency', data.frequency)}}
      ${{infoRow('Cancer types', data.cancer_types)}}
      ${{infoRow('Function', data.functional_class)}}
      ${{infoRow('ClinVar', data.clinvar)}}
      ${{infoRow('UniProt', data.uniprot)}}
      ${{infoRow('Conservation', data.conservation)}}
      ${{infoRow('Effect score', data.effect_score + ' / 1.00')}}
      ${{infoRow('Therapeutic', data.therapeutic)}}
    </div>

    <div>
      <div class="section-label">Data Sources</div>
      <div style="margin-top:4px">${{sourcesHtml}}</div>
    </div>
  `;
}}

function infoRow(label, val) {{
  return '<div class="info-row"><span class="info-lbl">' + label + '</span><span class="info-val">' + val + '</span></div>';
}}

// ── Experiments ───────────────────────────────────────────────────────────
const grid = document.getElementById('exp-grid');
EXPERIMENTS.forEach(exp => {{
  const card = document.createElement('div');
  card.className = 'exp-card';
  card.id = 'exp-' + exp.id;
  card.innerHTML = '<div class="exp-name">' + exp.name + '</div><div class="exp-meta"><span class="cat-' + exp.category + '">' + exp.category + '</span> · ' + exp.duration + '<br>' + exp.cost + '</div>';
  card.onclick = () => toggleExperiment(exp);
  grid.appendChild(card);
}});

function toggleExperiment(exp) {{
  const detail = document.getElementById('exp-detail');

  if (activeExp === exp.id) {{
    activeExp = null;
    document.querySelectorAll('.exp-card').forEach(c => c.classList.remove('active'));
    detail.classList.remove('visible');
    detail.innerHTML = '';
    applyBaseStyles(null);
    return;
  }}

  activeExp = exp.id;
  document.querySelectorAll('.exp-card').forEach(c => c.classList.remove('active'));
  document.getElementById('exp-' + exp.id).classList.add('active');
  applyBaseStyles(exp);

  const affectedPills = exp.affected.map(r => {{
    const d = RESIDUES[r];
    return '<span class="a-pill">' + (d ? d.label : 'R' + r) + '</span>';
  }}).join('');

  detail.innerHTML = `
    <div class="section-label">${{exp.name}} — ${{exp.category}}</div>
    <div class="exp-detail-grid">
      <div>
        ${{infoRow('Purpose', exp.purpose)}}
        ${{infoRow('Readout', exp.readout)}}
        ${{infoRow('Controls', exp.controls)}}
        ${{infoRow('Duration', exp.duration)}}
        ${{infoRow('Cost', exp.cost)}}
        <div class="outcome-box">
          <div class="outcome-label">Expected Structural Outcome — ${{exp.outcome_title}}</div>
          ${{exp.outcome}}
        </div>
      </div>
      <div>
        <div class="section-label">Highlighted residues in viewer</div>
        <div class="affected-pills">${{affectedPills}}</div>
        <div style="margin-top:12px;font-size:11px;color:#555;line-height:1.8;">
          The 3D viewer on the left now highlights these residues in
          <span style="color:${{exp.effect_color}};font-weight:600">${{exp.effect_color}}</span>
          to show which sites are structurally impacted by this experiment's outcome.
          Other residues are dimmed for clarity.<br><br>
          Click any sphere on the structure to load its full annotation data.
        </div>
      </div>
    </div>
  `;
  detail.classList.add('visible');
}}
</script>
</body>
</html>"""


def render():
    st.markdown("## ⚗️ Protein Explorer — TP53 R175H")
    st.markdown("Click any residue on the 3D structure for full annotation data. Select an experiment below to visualize its structural impact.")
    st.divider()

    with st.spinner("Loading TP53 structure from PDB..."):
        pdb_data = fetch_pdb_structure("2OCJ")

    if not pdb_data:
        st.error("Could not load TP53 structure. Check your internet connection.")
        return

    html = build_full_viewer_html(pdb_data)
    components.html(html, height=920, scrolling=False)
