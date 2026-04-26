"""
protein_explorer.py — Protellect Protein Explorer v3
Fixes:
- Info panel now scrollable and full height
- Animation renders inline below viewer on click
- Cell diagram embedded in same HTML component (no iframe issues)
- All in one self-contained HTML component to avoid Streamlit iframe communication limits
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import requests

try:
    from uniprot_api import (
        get_protein_name, get_gene_name, get_organism,
        get_sequence_length, get_residue_annotations,
        get_protein_function, get_disease_associations,
        get_clinvar_count, get_structure_for_uniprot,
    )
    HAS_UNIPROT = True
except ImportError:
    HAS_UNIPROT = False

# ── Static enrichment data ────────────────────────────────────────────────────
TP53_ENRICHMENT = {
    175: {"status":"critical","label":"R175H","clinvar":"Pathogenic · 847 submissions","cosmic":"~6% of all cancers","cancer_types":"Breast, lung, colorectal, ovarian, bladder","mechanism":"Disrupts zinc coordination at C176/H179/C238/C242. Causes global misfolding of the DNA-binding domain. Most common TP53 hotspot globally.","therapeutic":"APR-246 (eprenetapopt) — Phase III clinical trials","cell_impact":"apoptosis_loss","effect_score":0.99},
    248: {"status":"critical","label":"R248W/Q","clinvar":"Pathogenic · 623 submissions","cosmic":"~3% of all cancers","cancer_types":"Colorectal, lung, pancreatic, ovarian","mechanism":"Direct DNA contact residue in L3 loop. Makes hydrogen bonds to minor groove at CATG sequences. Substitution abolishes sequence-specific DNA binding.","therapeutic":"Synthetic lethality approaches under investigation","cell_impact":"dna_damage_bypass","effect_score":0.97},
    273: {"status":"critical","label":"R273H/C","clinvar":"Pathogenic · 512 submissions","cosmic":"~3% of all cancers","cancer_types":"Colorectal, lung, brain, pancreatic","mechanism":"DNA backbone phosphate contact residue. Loss reduces DNA-binding affinity >100-fold. R273C retains partial structure unlike R273H.","therapeutic":"Small molecule stabilizers in experimental stage","cell_impact":"dna_damage_bypass","effect_score":0.96},
    249: {"status":"critical","label":"R249S","clinvar":"Pathogenic · 298 submissions","cosmic":"~1.5% — enriched in liver cancer","cancer_types":"Liver (HCC), lung, esophageal","mechanism":"H2 helix structural mutation. Highly enriched in HCC — characteristic aflatoxin B1 mutational signature. Disrupts HIPK2 interaction.","therapeutic":"No specific therapy; aflatoxin avoidance in endemic regions","cell_impact":"proliferation","effect_score":0.91},
    245: {"status":"critical","label":"G245S/D","clinvar":"Pathogenic · 187 submissions","cosmic":"~1.5% of cancers","cancer_types":"Breast, lung, sarcoma, hematologic","mechanism":"Glycine at this position is essential — any side chain sterically clashes with the DNA backbone, disrupting L3 loop geometry entirely.","therapeutic":"Structural correctors under investigation","cell_impact":"apoptosis_loss","effect_score":0.88},
    282: {"status":"critical","label":"R282W","clinvar":"Pathogenic · 156 submissions","cosmic":"~1% of cancers","cancer_types":"Breast, colorectal, lung","mechanism":"R282 forms a salt bridge with E271 stabilizing the H2 helix. Tryptophan disrupts this causing partial helix unfolding.","therapeutic":"No approved targeted therapy","cell_impact":"apoptosis_loss","effect_score":0.85},
    176: {"status":"affected","label":"C176","clinvar":"Not directly pathogenic","cosmic":"N/A — secondary effect","cancer_types":"Affected by R175H","mechanism":"Zinc ligand (one of four: C176, H179, C238, C242). Directly adjacent to R175. R175H disrupts local geometry around C176, loosening zinc coordination without directly mutating it.","therapeutic":"APR-246 covalently binds C176 as a refolding scaffold","cell_impact":"structural","effect_score":0.60},
    179: {"status":"affected","label":"H179","clinvar":"Uncertain significance","cosmic":"N/A — secondary effect","cancer_types":"Affected by R175H propagation","mechanism":"Second zinc-coordinating histidine. Indirectly destabilized by R175H through propagated structural changes in the L2 loop. Zinc ion becomes mobile.","therapeutic":"N/A","cell_impact":"structural","effect_score":0.55},
    220: {"status":"affected","label":"Y220C","clinvar":"Pathogenic · 89 submissions","cosmic":"~1% of cancers","cancer_types":"Breast, lung, ovarian","mechanism":"Creates a surface hydrophobic cavity that destabilizes the domain thermodynamically. Not a DNA contact but reduces fold stability. The cavity is a druggable pocket.","therapeutic":"PC14586 (rezatapopt) — specifically designed to fill Y220C cavity. Phase II trials.","cell_impact":"apoptosis_loss","effect_score":0.78},
    100: {"status":"normal","label":"P100","clinvar":"Benign / likely benign","cosmic":"Not associated","cancer_types":"Not specifically associated","mechanism":"Structural proline in the flexible linker region. Located far from the DNA-binding domain. Mutations here are generally tolerated.","therapeutic":"N/A","cell_impact":"structural","effect_score":0.08},
    150: {"status":"normal","label":"V150","clinvar":"Likely benign","cosmic":"Not associated","cancer_types":"Not specifically associated","mechanism":"Interior beta-sheet residue contributing to hydrophobic core. Not involved in DNA binding or zinc coordination. Conservative substitutions tolerated.","therapeutic":"N/A","cell_impact":"structural","effect_score":0.12},
}

CELL_IMPACT = {
    "apoptosis_loss": {
        "title":"Loss of Apoptosis Signaling",
        "color":"#FF4C4C",
        "description":"TP53 normally activates BAX, PUMA, and NOXA to trigger programmed cell death when DNA damage is detected. This mutation abolishes that ability — damaged cells survive and accumulate further mutations, driving tumour development.",
        "pathway":["DNA damage detected by ATM/ATR","Mutant TP53 accumulates but cannot bind target promoters","BAX / PUMA / NOXA not activated","Apoptosis programme blocked","Damaged cell survives and divides","Clonal expansion → tumour formation"],
        "wt_bars":{"Apoptosis activation":100,"p21 induction":100,"MDM2 feedback":100,"BAX transcription":100},
        "mut_bars":{"Apoptosis activation":2,"p21 induction":4,"MDM2 feedback":10,"BAX transcription":3},
    },
    "dna_damage_bypass": {
        "title":"DNA Damage Checkpoint Bypass",
        "color":"#FF8C00",
        "description":"TP53 normally halts the cell cycle at the G1/S checkpoint via p21 activation, allowing time for DNA repair. Contact mutants cannot activate p21 — cells divide carrying unrepaired DNA, accumulating mutations with every cycle.",
        "pathway":["DNA double-strand break detected","ATM/ATR phosphorylate mutant TP53","Mutant TP53 cannot bind p21 promoter","G1/S checkpoint fails to activate","Cell divides with unrepaired DNA","Genomic instability → cancer progression"],
        "wt_bars":{"G1/S checkpoint":100,"p21 activation":100,"DNA repair time":100,"Genomic stability":100},
        "mut_bars":{"G1/S checkpoint":5,"p21 activation":3,"DNA repair time":15,"Genomic stability":20},
    },
    "proliferation": {
        "title":"Gain-of-Function Proliferation",
        "color":"#CC44CC",
        "description":"Gain-of-function mutants like R249S actively promote cell growth by gaining new protein interactions. They inhibit tumour suppressors p63 and p73 while activating oncogenic transcription programs including MYC and VEGF.",
        "pathway":["R249S gains new binding partners","Inhibits p63 and p73 tumour suppressors","Activates MYC / VEGF transcription programs","Cell proliferation rate accelerated","Angiogenesis promoted (VEGF)","Metastatic potential increased"],
        "wt_bars":{"p63/p73 activity":100,"MYC suppression":100,"Proliferation control":100,"Angiogenesis control":100},
        "mut_bars":{"p63/p73 activity":15,"MYC suppression":10,"Proliferation control":20,"Angiogenesis control":25},
    },
    "structural": {
        "title":"Structural Propagation Effect",
        "color":"#FFA500",
        "description":"This residue is not the primary mutation site but its function is compromised by nearby critical mutations propagating structural changes through the protein fold. A secondary but measurable functional loss.",
        "pathway":["Adjacent critical mutation occurs","Local protein geometry disrupted","Structural changes propagate through fold","This residue loses functional geometry","Partial domain destabilization","Reduced but not abolished activity"],
        "wt_bars":{"Local geometry":100,"Zinc coordination":100,"Domain stability":100,"Residue function":100},
        "mut_bars":{"Local geometry":45,"Zinc coordination":50,"Domain stability":60,"Residue function":40},
    },
}

EXPERIMENTS = [
    {"id":"thermal","name":"Thermal Shift Assay","category":"Structural","duration":"2–3 days","cost":"~$200–500","purpose":"Measures protein thermostability. R175H reduces Tm by ~8–10°C vs WT, directly confirming domain destabilization.","readout":"Melting temperature (Tm). WT TP53 DBD: ~42°C. R175H: ~32–34°C.","controls":"WT TP53 DBD, R248W control, stabilizing compound panel","affected":[175,176,179,220],"color":"#FF4C4C","outcome":"Global destabilization — zinc coordination cluster collapses, L2 loop unfolds, domain loses compact globular fold."},
    {"id":"emsa","name":"EMSA","category":"Functional","duration":"1–2 days","cost":"~$100–300","purpose":"Directly measures DNA binding. R175H shows complete loss of sequence-specific DNA binding due to misfolding.","readout":"Band shift on gel. WT: retarded band. R175H: no shift — free DNA only.","controls":"WT TP53, consensus p53RE oligo, non-specific oligo, supershift antibody","affected":[175,248,273,245],"color":"#FF8C00","outcome":"DNA contact interface lost — R248 and R273 physically present but structurally displaced by upstream R175H misfolding."},
    {"id":"reporter","name":"Luciferase Reporter","category":"Functional","duration":"3–5 days","cost":"~$300–600","purpose":"Measures transcriptional transactivation in cells. R175H completely abrogates p21, MDM2, and PUMA activation.","readout":"Relative luminescence (RLU). R175H: <5% of WT activity on p21/MDM2/PUMA reporters.","controls":"WT p53, empty vector, p53-null H1299 cells, p21-luc / MDM2-luc reporters","affected":[175,176,248,273,249],"color":"#CC44CC","outcome":"Complete transcriptional silence — NLS intact, protein accumulates in nucleus but cannot activate any target genes."},
    {"id":"apr246","name":"APR-246 Rescue","category":"Therapeutic","duration":"5–7 days","cost":"~$500–1200","purpose":"Tests whether APR-246 (eprenetapopt) can refold R175H and restore WT-like function via covalent cysteine modification.","readout":"Tm increase (+4–6°C), partial EMSA band, reporter recovery ~20–40% WT, cell viability reduction in R175H lines.","controls":"DMSO vehicle, WT p53, R175H without drug, full dose-response curve","affected":[175,176,179,248],"color":"#4CA8FF","outcome":"Partial structural rescue — APR-246 active form (MQ) covalently binds C176/C238, acting as zinc-independent scaffold restoring partial DNA-binding geometry."},
    {"id":"coip","name":"Co-IP Dom. Neg.","category":"Mechanistic","duration":"3–4 days","cost":"~$400–800","purpose":"Confirms R175H forms mixed tetramers with WT p53, exerting dominant negative suppression even when one WT allele is retained.","readout":"Pull-down of WT p53 by anti-mutant antibody. Western blot confirmation of mixed tetramer complex.","controls":"IgG isotype, WT-only cells, R175H-only cells, mixed transfection titration","affected":[175,248,273],"color":"#4CAF50","outcome":"Dominant negative confirmed — mixed tetramers (2x R175H + 2x WT) show dramatically reduced DNA binding vs pure WT. Explains aggressive heterozygous phenotype."},
]


def fetch_pdb(pdb_id="2OCJ"):
    try:
        r = requests.get(f"https://files.rcsb.org/download/{pdb_id}.pdb", timeout=15)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def build_full_html(pdb_data, extra_residues=None):
    """One giant self-contained HTML: viewer + info panel + animation + cell diagram + experiments."""

    residues = dict(TP53_ENRICHMENT)
    if extra_residues:
        for pos, d in extra_residues.items():
            if pos in residues:
                residues[pos].update(d)
            else:
                residues[pos] = d

    res_json  = json.dumps(residues, default=str)
    exp_json  = json.dumps(EXPERIMENTS)
    cell_json = json.dumps(CELL_IMPACT)
    pdb_esc   = pdb_data.replace("\\","\\\\").replace("`","\\`").replace("${","\\${")[:300000]

    return f"""<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#080b14;font-family:'IBM Plex Sans',sans-serif;color:#ccc;font-size:13px;padding:12px}}

/* ── Top layout ── */
#top{{display:grid;grid-template-columns:1.3fr 1fr;gap:14px;height:480px;margin-bottom:12px}}
#vwrap{{position:relative;border:1px solid #1e2030;border-radius:10px;overflow:hidden}}
#viewer{{width:100%;height:100%}}
#tooltip{{position:absolute;top:10px;left:10px;background:#0f1117ee;border:1px solid #2a2d3a;border-radius:6px;padding:8px 12px;font-size:11px;font-family:'IBM Plex Mono',monospace;display:none;z-index:100;max-width:200px;line-height:1.5;pointer-events:none}}
#hint{{position:absolute;bottom:10px;left:50%;transform:translateX(-50%);background:#0f1117cc;border:1px solid #1e2030;border-radius:20px;padding:5px 14px;font-size:10px;font-family:'IBM Plex Mono',monospace;color:#444;white-space:nowrap}}

/* ── Info panel ── */
#ipanel{{background:#0a0c14;border:1px solid #1e2030;border-radius:10px;padding:14px;overflow-y:auto;height:100%;display:flex;flex-direction:column;gap:8px}}
.placeholder{{color:#2a2d3a;font-family:'IBM Plex Mono',monospace;font-size:11px;text-align:center;margin:auto;line-height:3}}
.slabel{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#444;padding-bottom:5px;border-bottom:1px solid #1a1d2e;margin-bottom:6px;margin-top:4px}}
.irow{{display:flex;gap:8px;padding:5px 0;border-bottom:1px solid #0d0f1a;font-size:11px;line-height:1.5}}
.ilbl{{color:#3a3d5a;min-width:86px;font-family:'IBM Plex Mono',monospace;font-size:10px;flex-shrink:0;padding-top:1px}}
.ival{{color:#bbb}}
.chip{{display:inline-block;background:#12141e;border:1px solid #1e2030;border-radius:3px;padding:1px 7px;font-size:9px;font-family:'IBM Plex Mono',monospace;color:#556;margin:2px 2px 0 0}}
.badge{{display:inline-block;padding:3px 12px;border-radius:20px;font-size:9px;font-family:'IBM Plex Mono',monospace;font-weight:600;letter-spacing:0.1em;margin-bottom:10px}}
.res-title{{font-size:17px;font-weight:700;color:#eee;margin-bottom:2px;font-family:'IBM Plex Mono',monospace}}
.res-sub{{font-size:11px;color:#555;margin-bottom:10px}}

/* ── Legend ── */
#legend{{display:flex;gap:18px;padding:8px 0 12px 0;flex-wrap:wrap}}
.li{{display:flex;align-items:center;gap:6px;font-size:11px;color:#555}}
.ld{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}

/* ── Animation section ── */
#anim-wrap{{background:#0a0c14;border:1px solid #1e2030;border-radius:10px;padding:16px;margin-bottom:12px}}
#anim-inner{{color:#2a2d3a;font-family:'IBM Plex Mono',monospace;font-size:11px;text-align:center;padding:24px 0}}

/* ── Cell section ── */
#cell-wrap{{background:#0a0c14;border:1px solid #1e2030;border-radius:10px;padding:16px;margin-bottom:12px}}
#cell-inner{{color:#2a2d3a;font-family:'IBM Plex Mono',monospace;font-size:11px;text-align:center;padding:24px 0}}

/* ── Experiments ── */
#exp-wrap{{background:#0a0c14;border:1px solid #1e2030;border-radius:10px;padding:16px}}
.egrid{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:10px}}
.ecard{{background:#080b14;border:1px solid #1e2030;border-radius:8px;padding:10px;cursor:pointer;transition:border-color 0.15s}}
.ecard:hover{{border-color:#3a3d5a}}
.ecard.active{{border-color:#FF4C4C;background:#0f0606}}
.ename{{font-size:11px;font-weight:600;color:#ddd;margin-bottom:3px}}
.emeta{{font-size:10px;font-family:'IBM Plex Mono',monospace}}
.cat-Structural{{color:#4CA8FF}}.cat-Functional{{color:#FFA500}}.cat-Therapeutic{{color:#4CAF50}}.cat-Mechanistic{{color:#CC88FF}}
#edetail{{display:none;margin-top:12px;border-top:1px solid #1e2030;padding-top:12px}}
#edetail.vis{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}

/* ── Bars ── */
.bar-row{{margin-bottom:8px}}
.bar-labels{{display:flex;justify-content:space-between;font-size:10px;font-family:'IBM Plex Mono',monospace;color:#555;margin-bottom:3px}}
.bar-track{{background:#1a1d2e;border-radius:3px;height:7px;position:relative}}
.bar-wt{{position:absolute;top:0;left:0;height:100%;background:#4CAF5033;border-radius:3px}}
.bar-mut{{position:absolute;top:0;left:0;height:100%;border-radius:3px;transition:width 1.2s ease}}

/* ── Protein chain animation ── */
.chain-label{{font-family:'IBM Plex Mono',monospace;font-size:10px;margin-bottom:5px}}
.chain-svg{{width:100%;height:55px;background:#080b14;border-radius:6px;display:block}}
@keyframes wobble{{0%,100%{{transform:translateY(0)}}30%{{transform:translateY(-5px)}}70%{{transform:translateY(4px)}}}}
@keyframes glow{{0%,100%{{filter:drop-shadow(0 0 2px currentColor)}}50%{{filter:drop-shadow(0 0 12px currentColor)}}}}
.mut-circle{{animation:wobble 1.4s ease-in-out infinite,glow 1.4s ease-in-out infinite}}

/* ── Cell diagram ── */
.cell-grid{{display:grid;grid-template-columns:100px 1fr;gap:16px;align-items:start}}
.cell-anim{{display:flex;flex-direction:column;align-items:center;gap:6px}}
@keyframes cancer-pulse{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.1)}}}}
@keyframes div-spin{{0%{{transform:rotate(0deg)}}100%{{transform:rotate(360deg)}}}}
@keyframes grow-pulse{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.18)}}}}
@keyframes stress-shake{{0%,100%{{transform:translateX(0)}}25%{{transform:translateX(-3px)}}75%{{transform:translateX(3px)}}}}
.anim-cancer{{animation:cancer-pulse 2s ease-in-out infinite;transform-origin:center}}
.anim-dividing{{animation:div-spin 4s linear infinite;transform-origin:center}}
.anim-proliferating{{animation:grow-pulse 1.8s ease-in-out infinite;transform-origin:center}}
.anim-stressed{{animation:stress-shake 1.5s ease-in-out infinite}}
</style>
</head>
<body>

<!-- TOP: viewer + info panel -->
<div id="top">
  <div id="vwrap">
    <div id="viewer"></div>
    <div id="tooltip"></div>
    <div id="hint">● Click any residue sphere for details</div>
  </div>
  <div id="ipanel">
    <div class="placeholder">🔬<br><br>Click any residue<br>sphere on the structure<br>to load full annotation</div>
  </div>
</div>

<!-- Legend -->
<div id="legend">
  <div class="li"><div class="ld" style="background:#FF4C4C"></div>Critical hotspot</div>
  <div class="li"><div class="ld" style="background:#FFA500"></div>Affected by critical</div>
  <div class="li"><div class="ld" style="background:#4CA8FF"></div>No significant effect</div>
  <div class="li"><div class="ld" style="background:#ffffff"></div>Selected residue</div>
</div>

<!-- Mutation Fluctuation Animation -->
<div id="anim-wrap">
  <div class="slabel" style="margin-top:0">Mutation Fluctuation Model</div>
  <div id="anim-inner">Click a residue on the structure above to see the structural fluctuation animation</div>
</div>

<!-- Cell Impact -->
<div id="cell-wrap">
  <div class="slabel" style="margin-top:0">Cell-Level Impact</div>
  <div id="cell-inner">Click a residue on the structure above to see the cell-level consequence</div>
</div>

<!-- Experiments -->
<div id="exp-wrap">
  <div class="slabel" style="margin-top:0">Experimental Pathways — click to visualize structural change</div>
  <div class="egrid" id="egrid"></div>
  <div id="edetail"></div>
</div>

<script>
const RESIDUES = {res_json};
const EXPERIMENTS = {exp_json};
const CELL = {cell_json};
const pdbData = `{pdb_esc}`;

let viewer, selResi = null, activeExp = null;

// ── Build viewer ──────────────────────────────────────────────────────────
viewer = $3Dmol.createViewer('viewer', {{backgroundColor:'#080b14', antialias:true}});
viewer.addModel(pdbData, 'pdb');

function gc(status) {{
  return status === 'critical' ? '#FF4C4C' : status === 'affected' ? '#FFA500' : '#4CA8FF';
}}

function applyStyles(exp) {{
  viewer.setStyle({{}}, {{cartoon:{{color:'#1a1d2e', opacity:0.4}}}});
  viewer.addStyle({{resi:'94-292'}}, {{cartoon:{{color:'#1e2440', opacity:0.6}}}});
  for (const [resi, d] of Object.entries(RESIDUES)) {{
    const r = parseInt(resi);
    let color = gc(d.status);
    let radius = d.status==='critical' ? 0.85 : d.status==='affected' ? 0.65 : 0.42;
    let opacity = 1.0;
    if (exp) {{
      if (exp.affected.includes(r)) {{ color = exp.color; radius = 1.0; }}
      else {{ radius *= 0.35; opacity = 0.12; }}
    }}
    viewer.addStyle({{resi:r}}, {{sphere:{{color, radius, opacity}}}});
  }}
  if (selResi) viewer.addStyle({{resi:selResi}}, {{sphere:{{color:'#ffffff', radius:1.15, opacity:1}}}});
  viewer.render();
}}

viewer.setHoverable({{}}, true,
  function(atom) {{
    if (!atom?.resi) return;
    const d = RESIDUES[atom.resi];
    const tt = document.getElementById('tooltip');
    if (d) {{
      const c = gc(d.status);
      tt.innerHTML = `<span style="color:${{c}};font-weight:700">${{d.label||'Res'+atom.resi}}</span><br><span style="color:#888;font-size:10px">Residue ${{atom.resi}} · Score: ${{d.effect_score||'—'}}</span><br><span style="color:#555;font-size:10px">Click for full annotation →</span>`;
      tt.style.display = 'block';
    }}
  }},
  function() {{ document.getElementById('tooltip').style.display = 'none'; }}
);

viewer.setClickable({{}}, true, function(atom) {{
  if (!atom?.resi) return;
  const d = RESIDUES[atom.resi];
  if (!d) return;
  selResi = atom.resi;
  applyStyles(activeExp ? EXPERIMENTS.find(e => e.id === activeExp) : null);
  showInfo(atom.resi, d);
  showAnim(atom.resi, d);
  showCell(d);
}});

viewer.zoomTo({{resi:'94-292'}});
applyStyles(null);

// ── Info panel ────────────────────────────────────────────────────────────
function ir(l, v) {{
  return `<div class="irow"><span class="ilbl">${{l}}</span><span class="ival">${{v}}</span></div>`;
}}

function showInfo(resi, d) {{
  const c = gc(d.status);
  const sl = d.status==='critical' ? 'CRITICAL' : d.status==='affected' ? 'AFFECTED BY CRITICAL' : 'NO SIGNIFICANT EFFECT';
  const sources = ['UniProt P04637','ClinVar','COSMIC v97'].map(s=>`<span class="chip">${{s}}</span>`).join('');
  document.getElementById('ipanel').innerHTML = `
    <div>
      <div class="badge" style="background:${{c}}22;color:${{c}};border:1px solid ${{c}}44">${{sl}}</div>
      <div class="res-title">Residue ${{resi}} — ${{d.label}}</div>
    </div>
    <div>
      <div class="slabel">Structural Annotation</div>
      ${{ir('Domain', d.domain || 'DNA-binding domain')}}
      ${{ir('Mechanism', d.mechanism || '—')}}
    </div>
    <div>
      <div class="slabel">Clinical Data</div>
      ${{ir('ClinVar', d.clinvar || '—')}}
      ${{ir('COSMIC freq.', d.cosmic || '—')}}
      ${{ir('Cancer types', d.cancer_types || '—')}}
      ${{ir('Functional class', d.status==='critical'?'Loss-of-function / dominant negative':d.status==='affected'?'Indirectly disrupted':'Structurally neutral')}}
    </div>
    <div>
      <div class="slabel">Therapeutic</div>
      ${{ir('Therapy', d.therapeutic || 'N/A')}}
      ${{ir('Effect score', (d.effect_score||0) + ' / 1.00')}}
    </div>
    <div>
      <div class="slabel">Data Sources</div>
      <div style="margin-top:4px">${{sources}}</div>
    </div>
  `;
}}

// ── Animation ─────────────────────────────────────────────────────────────
function showAnim(resi, d) {{
  const c = gc(d.status);
  const isHigh = d.status === 'critical';
  const W = 500, total = 20, mutI = 9, sp = W/(total+1);
  
  let wtSVG = '', mutSVG = '';
  for (let i = 0; i < total; i++) {{
    const x = (i+1)*sp;
    const isMut = i === mutI;
    const cr = isMut ? 11 : 6;
    const col = isMut ? c : '#2a2d3a';
    // WT chain
    wtSVG += `<circle cx="${{x}}" cy="27" r="6" fill="#0a2010" stroke="#4CAF50" stroke-width="1.2"/>`;
    if (i < total-1) wtSVG += `<line x1="${{x+6}}" y1="27" x2="${{(i+2)*sp-6}}" y2="27" stroke="#2a4a2a" stroke-width="1.5"/>`;
    // Mutant chain
    const cls = isMut ? ' class="mut-circle"' : '';
    mutSVG += `<circle cx="${{x}}" cy="27" r="${{cr}}" fill="${{isMut?c+'22':'#0a0c14'}}" stroke="${{col}}" stroke-width="${{isMut?2.5:1}}"${{cls}} style="${{isMut?'color:'+c:''}}"/>`;
    if (i < total-1) mutSVG += `<line x1="${{x+(isMut?cr:6)}}" y1="27" x2="${{(i+2)*sp-6}}" y2="27" stroke="${{isMut?c:'#1a1d2e'}}" stroke-width="1.5"/>`;
  }}

  const effects = [
    {{l:'Zinc coordination', wt:100, mut:isHigh?8:65}},
    {{l:'DNA binding affinity', wt:100, mut:isHigh?3:50}},
    {{l:'Thermal stability (Tm)', wt:100, mut:isHigh?28:72}},
    {{l:'Transcriptional activity', wt:100, mut:isHigh?2:58}},
  ];

  const barHTML = effects.map(e => `
    <div class="bar-row">
      <div class="bar-labels"><span>${{e.l}}</span><span style="color:${{c}}">${{e.mut}}% of WT</span></div>
      <div class="bar-track">
        <div class="bar-wt" style="width:100%"></div>
        <div class="bar-mut" style="width:${{e.mut}}%;background:${{c}}"></div>
      </div>
    </div>`).join('');

  document.getElementById('anim-inner').innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
      <div>
        <div class="chain-label" style="color:#4CAF50">▸ WT protein chain (normal)</div>
        <svg class="chain-svg" viewBox="0 0 ${{W}} 54">${{wtSVG}}</svg>
        <div class="chain-label" style="color:${{c}};margin-top:12px">▸ Mutant chain — ${{d.label}} (pulsing sphere = instability)</div>
        <svg class="chain-svg" viewBox="0 0 ${{W}} 54">${{mutSVG}}</svg>
        <div style="font-size:10px;color:#444;margin-top:6px">Position ${{resi}} highlighted · wobble = structural instability · glow = energetic cost</div>
      </div>
      <div>
        <div class="chain-label" style="color:#444;margin-bottom:10px">Functional parameters vs wild-type</div>
        ${{barHTML}}
        <div style="font-size:10px;color:#444;margin-top:10px;line-height:1.6">
          ${{isHigh ? 'CRITICAL mutation: near-complete loss of function across all parameters. Protein structurally compromised.' : 'PARTIAL impact: function reduced but not abolished. Structural effect propagated from nearby critical mutation.'}}
        </div>
      </div>
    </div>`;
}}

// ── Cell diagram ──────────────────────────────────────────────────────────
function showCell(d) {{
  const impactKey = d.cell_impact || 'structural';
  const imp = CELL[impactKey];
  if (!imp) return;
  const c = imp.color;
  
  const animClass = {{apoptosis_loss:'anim-cancer', dna_damage_bypass:'anim-dividing', proliferation:'anim-proliferating', structural:'anim-stressed'}}[impactKey] || 'anim-cancer';

  const stepsHTML = imp.pathway.map((step, i) => `
    <div style="display:flex;flex-wrap:wrap;align-items:center;margin-bottom:5px;opacity:0;animation:fadeIn 0.4s ${{i*0.2}}s forwards">
      <div style="width:20px;height:20px;border-radius:50%;background:${{c}}22;color:${{c}};border:1px solid ${{c}}44;display:flex;align-items:center;justify-content:center;font-size:9px;font-family:'IBM Plex Mono',monospace;font-weight:700;flex-shrink:0;margin-right:8px">${{i+1}}</div>
      <div style="font-size:11px;color:#ccc;flex:1">${{step}}</div>
      ${{i<imp.pathway.length-1?'<div style="width:100%;padding-left:28px;color:#2a2d3a;font-size:13px;line-height:1.2">↓</div>':''}}
    </div>`).join('');

  const wtBars = Object.entries(imp.wt_bars||{{}}).map(([k,v]) => `
    <div class="bar-row">
      <div class="bar-labels"><span>${{k}}</span><span style="color:#4CAF50">WT: 100%</span></div>
      <div class="bar-track"><div class="bar-wt" style="width:100%"></div><div class="bar-mut" style="width:${{imp.mut_bars?.[k]||10}}%;background:${{c}}"></div></div>
      <div style="font-size:9px;color:${{c}};text-align:right;margin-top:2px">Mutant: ${{imp.mut_bars?.[k]||10}}%</div>
    </div>`).join('');

  document.getElementById('cell-inner').innerHTML = `
    <div style="display:grid;grid-template-columns:90px 1fr 1fr;gap:16px;align-items:start">
      <div style="display:flex;flex-direction:column;align-items:center;gap:6px">
        <svg width="70" height="70" viewBox="0 0 70 70">
          <ellipse cx="35" cy="35" rx="31" ry="28" fill="#0a2a0a" stroke="#2a5a2a" stroke-width="1.5"/>
          <ellipse cx="35" cy="35" rx="12" ry="10" fill="#1a4a1a" stroke="#4CAF50" stroke-width="1.5"/>
          <text x="35" y="38" text-anchor="middle" font-size="6" fill="#4CAF50" font-family="monospace">WT</text>
        </svg>
        <div style="font-size:9px;font-family:'IBM Plex Mono',monospace;color:#4CAF50;text-align:center">Normal</div>
        <div style="color:${{c}};font-size:16px">↓</div>
        <div style="font-size:9px;font-family:'IBM Plex Mono',monospace;color:${{c}};text-align:center">mutation</div>
        <svg width="70" height="70" viewBox="0 0 70 70" class="${{animClass}}">
          <ellipse cx="35" cy="35" rx="31" ry="28" fill="#2a0808" stroke="${{c}}" stroke-width="1.5" stroke-dasharray="4,2"/>
          <ellipse cx="35" cy="35" rx="14" ry="12" fill="#3a0a0a" stroke="${{c}}" stroke-width="1.5"/>
          <circle cx="18" cy="24" r="3" fill="${{c}}" opacity="0.6"/>
          <circle cx="52" cy="46" r="2" fill="${{c}}" opacity="0.4"/>
          <circle cx="26" cy="50" r="2.5" fill="${{c}}" opacity="0.5"/>
          <text x="35" y="38" text-anchor="middle" font-size="6" fill="${{c}}" font-family="monospace">MUT</text>
        </svg>
        <div style="font-size:9px;font-family:'IBM Plex Mono',monospace;color:${{c}};text-align:center">Affected</div>
      </div>

      <div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;color:${{c}};margin-bottom:8px">${{imp.title}}</div>
        <div style="font-size:11px;color:#888;line-height:1.7;margin-bottom:14px">${{imp.description}}</div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.12em;color:#444;margin-bottom:8px">Molecular Pathway</div>
        ${{stepsHTML}}
      </div>

      <div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.12em;color:#444;margin-bottom:10px">Functional parameters — WT vs Mutant</div>
        ${{wtBars}}
      </div>
    </div>`;
}}

// ── Experiments ───────────────────────────────────────────────────────────
const grid = document.getElementById('egrid');
EXPERIMENTS.forEach(exp => {{
  const card = document.createElement('div');
  card.className = 'ecard'; card.id = 'e-'+exp.id;
  card.innerHTML = `<div class="ename">${{exp.name}}</div><div class="emeta"><span class="cat-${{exp.category}}">${{exp.category}}</span><br>${{exp.duration}} · ${{exp.cost}}</div>`;
  card.onclick = () => toggleExp(exp);
  grid.appendChild(card);
}});

function ir2(l,v){{return `<div class="irow"><span class="ilbl">${{l}}</span><span class="ival">${{v}}</span></div>`;}}

function toggleExp(exp) {{
  const det = document.getElementById('edetail');
  if (activeExp === exp.id) {{
    activeExp = null;
    document.querySelectorAll('.ecard').forEach(c=>c.classList.remove('active'));
    det.classList.remove('vis'); det.innerHTML='';
    applyStyles(null); return;
  }}
  activeExp = exp.id;
  document.querySelectorAll('.ecard').forEach(c=>c.classList.remove('active'));
  document.getElementById('e-'+exp.id).classList.add('active');
  applyStyles(exp);

  const pills = exp.affected.map(r=>{{
    const d=RESIDUES[r];
    return `<span class="chip" style="color:${{exp.color}};border-color:${{exp.color}}44">${{d?d.label:'R'+r}}</span>`;
  }}).join('');

  det.innerHTML = `
    <div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:${{exp.color}};font-weight:700;margin-bottom:10px">${{exp.name}} — ${{exp.category}}</div>
      ${{ir2('Purpose',exp.purpose)}}${{ir2('Readout',exp.readout)}}${{ir2('Controls',exp.controls)}}${{ir2('Duration',exp.duration)}}${{ir2('Cost',exp.cost)}}
      <div style="background:#080b14;border:1px solid #1a3a1a;border-radius:6px;padding:12px;margin-top:10px">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.12em;color:#4CAF50;margin-bottom:6px">Expected Structural Outcome</div>
        <div style="font-size:11px;color:#888;line-height:1.7">${{exp.outcome}}</div>
      </div>
    </div>
    <div>
      <div class="slabel">Highlighted Residues in Viewer</div>
      <div style="margin:6px 0 12px 0">${{pills}}</div>
      <div style="font-size:11px;color:#444;line-height:1.7">The 3D viewer highlights these residues in <span style="color:${{exp.color}};font-weight:600">${{exp.color}}</span>. Other residues are dimmed. Click any sphere for full annotation.</div>
    </div>`;
  det.classList.add('vis');
}}

// ── Fade-in keyframe (needs to be in JS since it's dynamic) ───────────────
const style = document.createElement('style');
style.textContent = '@keyframes fadeIn {{ to {{ opacity:1 }} }}';
document.head.appendChild(style);
</script>
</body>
</html>"""


def render():
    st.markdown("## ⚗️ Protein Explorer — TP53 R175H")
    st.markdown("Click any residue sphere → full annotation loads on the right, animation and cell diagram update below.")
    st.divider()

    # Optional CSV overlay
    csv_file = st.file_uploader("Upload experimental CSV to overlay your own scores (optional)", type="csv")
    extra_residues = None
    if csv_file:
        from scorer import score_residues, validate_dataframe
        df_raw = pd.read_csv(csv_file)
        valid, err = validate_dataframe(df_raw)
        if valid:
            scored = score_residues(df_raw)
            extra_residues = {}
            for _, row in scored.iterrows():
                pos = int(row["residue_position"])
                priority = row.get("priority", "LOW")
                status = {"HIGH":"critical","MEDIUM":"affected","LOW":"normal"}.get(priority,"normal")
                extra_residues[pos] = {
                    "label": row.get("mutation", f"Res{pos}"),
                    "status": status,
                    "effect_score": round(float(row.get("normalized_score", 0)), 3),
                }
        else:
            st.error(f"CSV error: {err}")

    with st.spinner("Loading TP53 structure from PDB..."):
        pdb_data = fetch_pdb("2OCJ")

    if not pdb_data:
        st.error("Could not load TP53 structure. Check internet connection.")
        return

    html = build_full_html(pdb_data, extra_residues)
    components.html(html, height=1600, scrolling=True)
