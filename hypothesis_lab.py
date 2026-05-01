"""
hypothesis_lab.py — Protellect Hypothesis Lab (Tab 4)
- Logo embedded in header
- Per-hypothesis expandable cards
- WT vs mutant chain animation
- Protein structural animation (DNA binding, helix breaking) alongside slider
- Mutation timeline slider
- Cell impact diagram
- Works with any dataset
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import requests

LOGO_SVG = """<svg width="28" height="28" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" style="vertical-align:middle">
  <defs><linearGradient id="lg2" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#2d6a4f"/><stop offset="100%" style="stop-color:#1b4332"/></linearGradient></defs>
  <path d="M45 10 C35 30, 65 45, 55 60 C45 75, 25 85, 35 105" stroke="url(#lg2)" stroke-width="7" fill="none" stroke-linecap="round"/>
  <path d="M75 10 C85 30, 55 45, 65 60 C75 75, 95 85, 85 105" stroke="url(#lg2)" stroke-width="7" fill="none" stroke-linecap="round"/>
  <line x1="48" y1="22" x2="72" y2="22" stroke="#52b788" stroke-width="4.5" stroke-linecap="round"/>
  <line x1="42" y1="38" x2="78" y2="38" stroke="#52b788" stroke-width="4.5" stroke-linecap="round"/>
  <line x1="52" y1="53" x2="68" y2="53" stroke="#52b788" stroke-width="4" stroke-linecap="round"/>
  <line x1="55" y1="67" x2="65" y2="67" stroke="#52b788" stroke-width="4" stroke-linecap="round"/>
  <line x1="51" y1="82" x2="69" y2="82" stroke="#52b788" stroke-width="4" stroke-linecap="round"/>
  <line x1="45" y1="96" x2="75" y2="96" stroke="#52b788" stroke-width="4.5" stroke-linecap="round"/>
  <path d="M72 22 L90 12" stroke="#74c69d" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M90 12 L100 6" stroke="#74c69d" stroke-width="2" stroke-linecap="round"/>
  <path d="M90 12 L102 15" stroke="#74c69d" stroke-width="2" stroke-linecap="round"/>
  <circle cx="100" cy="6" r="2.5" fill="#74c69d"/>
  <circle cx="102" cy="15" r="2.5" fill="#74c69d"/>
  <path d="M48 82 L28 92" stroke="#74c69d" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M28 92 L16 86" stroke="#74c69d" stroke-width="2" stroke-linecap="round"/>
  <path d="M28 92 L18 100" stroke="#74c69d" stroke-width="2" stroke-linecap="round"/>
  <circle cx="16" cy="86" r="2.5" fill="#74c69d"/>
  <circle cx="18" cy="100" r="2.5" fill="#74c69d"/>
</svg>"""

HOTSPOT_DATA = {
    175: {"mechanism":"Disrupts zinc coordination at C176/H179/C238/C242. Global misfolding of DNA-binding domain.","clinvar":"Pathogenic · 847 submissions","cosmic":"~6% of all cancers","cancer":"Breast, lung, colorectal, ovarian","therapeutic":"APR-246 (eprenetapopt) — Phase III","cell":"apoptosis","domain":"DNA-binding domain (L2 loop) — zinc coordination","experiment":"Thermal shift assay → EMSA → luciferase reporter for p21/MDM2 activation.","struct_effect":"zinc_collapse"},
    248: {"mechanism":"Direct DNA contact in L3 loop. Abolishes sequence-specific DNA binding.","clinvar":"Pathogenic · 623 submissions","cosmic":"~3% of all cancers","cancer":"Colorectal, lung, pancreatic","therapeutic":"Synthetic lethality under investigation","cell":"checkpoint","domain":"DNA-binding domain (L3 loop) — DNA contact","experiment":"EMSA to confirm loss of DNA binding. Reporter assay for transcriptional activity.","struct_effect":"dna_contact_loss"},
    273: {"mechanism":"DNA backbone phosphate contact. Loss reduces affinity >100-fold.","clinvar":"Pathogenic · 512 submissions","cosmic":"~3% of all cancers","cancer":"Colorectal, lung, brain","therapeutic":"Small molecule stabilizers experimental","cell":"checkpoint","domain":"DNA-binding domain (S10 strand) — backbone contact","experiment":"EMSA. Note: R273C vs R273H differ in severity — test separately.","struct_effect":"dna_contact_loss"},
    249: {"mechanism":"H2 helix structural mutation. Aflatoxin B1 signature.","clinvar":"Pathogenic · 298 submissions","cosmic":"~1.5% — enriched in HCC","cancer":"Liver (HCC), lung, esophageal","therapeutic":"No specific therapy","cell":"proliferation","domain":"DNA-binding domain (H2 helix)","experiment":"Reporter assay. Co-IP for dominant negative tetramer formation.","struct_effect":"helix_break"},
    245: {"mechanism":"Glycine essential for L3 loop geometry. Any side chain disrupts DNA approach.","clinvar":"Pathogenic · 187 submissions","cosmic":"~1.5% of cancers","cancer":"Breast, lung, sarcoma","therapeutic":"Structural correctors under investigation","cell":"apoptosis","domain":"DNA-binding domain (L3 loop)","experiment":"Thermal shift + EMSA. APR-246 rescue if structural mutant confirmed.","struct_effect":"loop_distortion"},
    282: {"mechanism":"R282 salt bridge with E271 stabilises H2 helix. Tryptophan disrupts this.","clinvar":"Pathogenic · 156 submissions","cosmic":"~1% of cancers","cancer":"Breast, colorectal, lung","therapeutic":"No approved targeted therapy","cell":"apoptosis","domain":"DNA-binding domain (H2 helix)","experiment":"Thermal shift assay. Luciferase reporter for p21/MDM2.","struct_effect":"helix_break"},
    220: {"mechanism":"Creates druggable hydrophobic cavity. Thermodynamic destabilisation.","clinvar":"Pathogenic · 89 submissions","cosmic":"~1% of cancers","cancer":"Breast, lung, ovarian","therapeutic":"PC14586 (rezatapopt) — Phase II","cell":"apoptosis","domain":"DNA-binding domain (S7-S8 loop)","experiment":"Thermal shift. APR-246 and PC14586 rescue — prime cavity-filling candidate.","struct_effect":"surface_cavity"},
}

CELL_DATA = {
    "apoptosis":    {"title":"Loss of apoptosis signalling","color":"#FF4C4C","anim":"cpulse","desc":"TP53 normally activates BAX, PUMA, and NOXA to trigger programmed cell death. This mutation abolishes that signal — damaged cells survive and accumulate further mutations."},
    "checkpoint":   {"title":"DNA damage checkpoint bypass","color":"#FFA500","anim":"cspin", "desc":"TP53 normally halts the cell cycle at G1/S via p21. This contact mutation prevents p21 activation — cells divide with unrepaired DNA every cycle, accumulating genomic instability."},
    "proliferation":{"title":"Gain-of-function proliferation","color":"#CC44CC","anim":"cgrow","desc":"This gain-of-function mutation inhibits p63/p73 and activates MYC/VEGF programmes — actively driving oncogenic proliferation rather than merely losing tumour suppression."},
    "structural":   {"title":"Structural propagation effect","color":"#FFA500","anim":"cshake","desc":"This residue is not directly mutated but its function is compromised by structural changes propagating from nearby critical mutations."},
}

# Structural animation scripts per effect type
STRUCT_ANIMATIONS = {
    "zinc_collapse": {
        "label": "Zinc site collapse",
        "desc": "The mutation disrupts the tetrahedral zinc coordination site (C176/H179/C238/C242). The zinc ion is released, causing the L2 loop to unfold and the entire DNA-binding domain to lose its compact conformation.",
        "stages": ["Normal zinc coordination", "Zinc site geometry distorted", "Zinc ion released", "L2 loop unfolds", "Domain misfolding propagates", "Full domain collapse"],
        "colors": ["#4CAF50","#8BC34A","#FFC107","#FF9800","#FF5722","#FF4C4C"],
    },
    "dna_contact_loss": {
        "label": "DNA contact interface lost",
        "desc": "The mutation removes a critical amino acid that directly contacts DNA. The protein can still fold, but its DNA-binding interface is missing a key anchor — sequence-specific binding is abolished.",
        "stages": ["WT: protein-DNA contact intact", "Mutation disrupts contact residue", "DNA-binding interface weakened", "Sequence-specific recognition lost", "Protein-DNA complex unstable", "Complete dissociation from DNA"],
        "colors": ["#4CAF50","#8BC34A","#FFC107","#FF9800","#FF5722","#FF4C4C"],
    },
    "helix_break": {
        "label": "α-Helix disruption",
        "desc": "The mutation removes a stabilising interaction within the H2 helix (a salt bridge or structural contact). The helix locally unfolds, reshaping the DNA-binding domain and reducing its affinity for target sequences.",
        "stages": ["WT: helix intact", "Stabilising interaction removed", "Helix begins to unwind", "Local unfolding propagates", "DNA-binding domain reshaped", "Loss of transcriptional activity"],
        "colors": ["#4CAF50","#8BC34A","#FFC107","#FF9800","#FF5722","#FF4C4C"],
    },
    "loop_distortion": {
        "label": "Loop geometry distortion",
        "desc": "Glycine is uniquely flexible — no side chain means the L3 loop can adopt the tight geometry needed to approach DNA. Any substitution adds bulk that sterically clashes with the DNA backbone.",
        "stages": ["WT: loop adopts correct geometry", "Side chain addition creates steric clash", "Loop repositioned away from DNA", "DNA approach blocked", "Binding affinity dramatically reduced", "Loss of sequence-specific recognition"],
        "colors": ["#4CAF50","#8BC34A","#FFC107","#FF9800","#FF5722","#FF4C4C"],
    },
    "surface_cavity": {
        "label": "Hydrophobic cavity formation",
        "desc": "The tyrosine → cysteine substitution removes a bulky aromatic side chain, creating a surface hydrophobic cavity. This cavity destabilises the domain thermodynamically. However, it is also a druggable pocket targeted by PC14586.",
        "stages": ["WT: Tyr fills surface pocket", "Cys substitution — pocket opens", "Hydrophobic cavity exposed", "Water molecules fill cavity", "Thermodynamic destabilisation", "Reduced fold stability (Tm -6°C)"],
        "colors": ["#4CAF50","#8BC34A","#378add","#4CA8FF","#FFA500","#FF9800"],
    },
    "default": {
        "label": "Functional disruption",
        "desc": "This mutation alters the protein's functional conformation. The normalised effect score from your assay reflects the degree of functional change relative to wild-type.",
        "stages": ["Wild-type conformation", "Mutation introduced", "Local structural change", "Conformational propagation", "Functional interface altered", "Reduced biological activity"],
        "colors": ["#4CAF50","#8BC34A","#FFC107","#FF9800","#FF5722","#FF4C4C"],
    },
}


@st.cache_data(show_spinner=False)
def fetch_pdb():
    try:
        r = requests.get("https://files.rcsb.org/download/2OCJ.pdb", timeout=15)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def build_lab_html(residues_data, pdb_data):
    res_json   = json.dumps(residues_data)
    cell_json  = json.dumps(CELL_DATA)
    struct_json = json.dumps(STRUCT_ANIMATIONS)
    pdb_esc    = pdb_data.replace("\\","\\\\").replace("`","\\`").replace("${","\\${")[:280000]

    n_high = sum(1 for r in residues_data if r["priority"]=="HIGH")
    n_med  = sum(1 for r in residues_data if r["priority"]=="MEDIUM")
    n_low  = sum(1 for r in residues_data if r["priority"]=="LOW")
    top    = residues_data[0] if residues_data else {}

    # Build logo SVG inline string for JS
    logo_svg_escaped = LOGO_SVG.replace('"', '\\"').replace('\n', '')

    return f"""<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#080b14;font-family:'IBM Plex Sans',sans-serif;color:#ccc;font-size:13px;padding:14px;line-height:1.5}}
::-webkit-scrollbar{{width:5px}}::-webkit-scrollbar-track{{background:#0a0c14}}::-webkit-scrollbar-thumb{{background:#2a2d3a;border-radius:3px}}

.page-header{{display:flex;align-items:center;gap:12px;margin-bottom:6px}}
.page-title{{font-family:'IBM Plex Mono',monospace;font-size:18px;font-weight:700;color:#eee}}
.page-sub{{font-size:12px;color:#555;margin-bottom:16px}}

.stat-row{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:16px}}
.sc{{background:#0f1117;border:1px solid #1e2030;border-radius:8px;padding:12px;text-align:center}}
.sn{{font-size:1.4rem;font-weight:600;font-family:'IBM Plex Mono',monospace}}
.sl{{font-size:10px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.08em}}

.filter-bar{{display:flex;gap:8px;margin-bottom:14px;align-items:center;flex-wrap:wrap}}
.fbtn{{padding:6px 14px;border-radius:20px;border:1px solid #1e2030;background:#0f1117;color:#555;font-size:11px;cursor:pointer;font-family:'IBM Plex Mono',monospace;transition:all 0.15s}}
.fbtn.active{{border-color:#FF4C4C;color:#FF4C4C;background:#1a0808}}
.fbtn.am.active{{border-color:#FFA500;color:#FFA500;background:#1a1200}}
.fbtn.al.active{{border-color:#4CA8FF;color:#4CA8FF;background:#08101a}}
.fbtn.aa.active{{border-color:#555;color:#ccc;background:#0f1117}}

.hcard{{background:#0a0c14;border:1px solid #1e2030;border-radius:10px;margin-bottom:10px;overflow:hidden;transition:border-color 0.15s}}
.hcard:hover{{border-color:#2a2d3a}}
.hheader{{display:flex;align-items:center;gap:12px;padding:14px 16px;cursor:pointer;user-select:none}}
.hrank{{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#3a3d5a;min-width:28px}}
.pdot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
.hlabel{{font-family:'IBM Plex Mono',monospace;font-size:14px;font-weight:700;color:#eee;flex:1}}
.hscore{{font-family:'IBM Plex Mono',monospace;font-size:12px;min-width:50px;text-align:right}}
.badge{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:10px;font-weight:600;font-family:'IBM Plex Mono',monospace;margin-right:6px}}
.chev{{color:#444;font-size:12px;transition:transform 0.2s;margin-left:4px}}
.chev.open{{transform:rotate(90deg)}}

.hbody{{display:none;border-top:1px solid #1e2030}}
.hbody.open{{display:block}}
.bgrid{{display:grid;grid-template-columns:1fr 1fr;gap:0}}
.bleft{{padding:16px;border-right:1px solid #1e2030}}
.bright{{padding:16px;background:#080b14}}

.sl2{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;padding-bottom:5px;border-bottom:1px solid #1a1d2e;margin:12px 0 8px}}
.sl2:first-child{{margin-top:0}}
.drow{{display:flex;gap:8px;padding:5px 0;border-bottom:1px solid #0d0f1a;font-size:11px}}
.dl{{color:#3a3d5a;min-width:80px;font-size:10px;font-family:'IBM Plex Mono',monospace;flex-shrink:0;padding-top:1px}}
.dv{{color:#bbb;flex:1;line-height:1.5}}
.hyp-text{{font-size:12px;color:#888;line-height:1.7;padding:10px 12px;background:#080b14;border:1px solid #1e2030;border-radius:6px;margin-bottom:10px}}
.action-box{{background:#0a1a0a;border:1px solid #1a3a1a;border-radius:6px;padding:10px 12px;margin-top:8px}}
.al{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.12em;color:#4CAF50;margin-bottom:5px}}
.at{{font-size:11px;color:#888;line-height:1.7}}

/* Chain animation */
.anim-box{{background:#080b14;border:1px solid #1e2030;border-radius:8px;padding:12px;margin-bottom:12px}}
.clabel{{font-size:10px;font-family:'IBM Plex Mono',monospace;color:#555;margin-bottom:5px}}
.csvg{{width:100%;height:46px;border:1px solid #1e2030;border-radius:5px;background:#040608;display:block}}
.brow{{margin-bottom:7px}}
.blbl{{display:flex;justify-content:space-between;font-size:10px;color:#555;margin-bottom:2px;font-family:'IBM Plex Mono',monospace}}
.btrack{{background:#1a1d2e;border-radius:3px;height:6px;overflow:hidden;position:relative}}
.bfill{{height:100%;border-radius:3px;transition:width 0.3s ease;position:absolute;top:0;left:0}}
.bwt{{height:100%;background:#4CAF5022;width:100%;border-radius:3px}}

/* Slider + structural animation side by side */
.slider-struct-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:12px;padding-top:12px;border-top:1px solid #1a1d2e}}
.slider-section{{}}
.slider-title{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:10px}}
.slider-row{{display:flex;align-items:center;gap:8px;margin-bottom:8px}}
.slider-lbl{{font-size:10px;font-family:'IBM Plex Mono',monospace;color:#555;min-width:70px}}
input[type=range]{{flex:1;accent-color:#FF4C4C;cursor:pointer;height:4px}}
.slider-val{{font-size:11px;font-family:'IBM Plex Mono',monospace;min-width:40px;text-align:right;color:#aaa}}
.phase-bar{{height:14px;background:#1a1d2e;border-radius:7px;position:relative;overflow:hidden;margin:6px 0}}
.phase-fill{{height:100%;border-radius:7px;transition:width 0.3s ease;display:flex;align-items:center;padding-left:6px;font-size:9px;font-family:'IBM Plex Mono',monospace;color:rgba(255,255,255,0.8);white-space:nowrap;overflow:hidden;min-width:0}}
.marker{{position:absolute;top:0;height:100%;width:2px;background:white;opacity:0.8;transition:left 0.3s ease;z-index:5}}
.pevt{{display:flex;align-items:flex-start;gap:6px;margin-bottom:5px;transition:opacity 0.3s}}
.pevt.inactive{{opacity:0.15}}
.pdotev{{width:7px;height:7px;border-radius:50%;flex-shrink:0;margin-top:3px}}
.pevt strong{{display:block;font-size:10px;color:#eee;margin-bottom:1px}}
.pevt span{{font-size:9px;color:#555;line-height:1.4}}

/* Protein structural animation panel */
.struct-anim-section{{}}
.struct-title{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:10px}}
.struct-label{{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;margin-bottom:6px}}
.struct-desc{{font-size:10px;color:#666;line-height:1.6;margin-bottom:10px}}
.struct-stages{{display:flex;flex-direction:column;gap:4px}}
.stage-row{{display:flex;align-items:center;gap:8px;padding:4px 0;transition:all 0.3s}}
.stage-row.active .stage-dot{{box-shadow:0 0 8px currentColor}}
.stage-row.active .stage-text{{color:#eee}}
.stage-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0;transition:all 0.3s}}
.stage-text{{font-size:10px;color:#444;transition:color 0.3s;line-height:1.4}}

/* Protein SVG canvas */
.protein-canvas{{width:100%;height:120px;border:1px solid #1e2030;border-radius:6px;background:#040608;display:block;margin-bottom:8px}}

/* Cell diagram */
.cell-section{{margin-top:12px;padding-top:12px;border-top:1px solid #1a1d2e}}
.cell-layout{{display:flex;gap:12px;align-items:flex-start}}
.cell-anim-col{{display:flex;flex-direction:column;align-items:center;gap:6px;flex-shrink:0}}
.cell-info-col{{flex:1}}
.cell-title{{font-family:'IBM Plex Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin-bottom:6px}}
.cell-desc{{font-size:11px;color:#888;line-height:1.6}}
@keyframes cpulse{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.1)}}}}
@keyframes cspin{{0%{{transform:rotate(0deg)}}100%{{transform:rotate(360deg)}}}}
@keyframes cgrow{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.15)}}}}
@keyframes cshake{{0%,100%{{transform:translateX(0)}}25%{{transform:translateX(-2px)}}75%{{transform:translateX(2px)}}}}
@keyframes wobble-critical{{0%,100%{{transform:translateY(0)}}30%{{transform:translateY(-7px)}}70%{{transform:translateY(5px)}}}}
@keyframes wobble-affected{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-3px)}}}}
@keyframes wobble-normal{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-1px)}}}}
</style>
</head>
<body>

<div class="page-header">
  <svg width="32" height="32" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
    <defs><linearGradient id="lg3" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#2d6a4f"/><stop offset="100%" style="stop-color:#1b4332"/></linearGradient></defs>
    <path d="M45 10 C35 30, 65 45, 55 60 C45 75, 25 85, 35 105" stroke="url(#lg3)" stroke-width="7" fill="none" stroke-linecap="round"/>
    <path d="M75 10 C85 30, 55 45, 65 60 C75 75, 95 85, 85 105" stroke="url(#lg3)" stroke-width="7" fill="none" stroke-linecap="round"/>
    <line x1="48" y1="22" x2="72" y2="22" stroke="#52b788" stroke-width="4.5" stroke-linecap="round"/>
    <line x1="42" y1="38" x2="78" y2="38" stroke="#52b788" stroke-width="4.5" stroke-linecap="round"/>
    <line x1="52" y1="53" x2="68" y2="53" stroke="#52b788" stroke-width="4" stroke-linecap="round"/>
    <line x1="55" y1="67" x2="65" y2="67" stroke="#52b788" stroke-width="4" stroke-linecap="round"/>
    <line x1="51" y1="82" x2="69" y2="82" stroke="#52b788" stroke-width="4" stroke-linecap="round"/>
    <line x1="45" y1="96" x2="75" y2="96" stroke="#52b788" stroke-width="4.5" stroke-linecap="round"/>
    <path d="M72 22 L90 12" stroke="#74c69d" stroke-width="2.5" stroke-linecap="round"/>
    <circle cx="100" cy="6" r="2.5" fill="#74c69d"/>
    <circle cx="102" cy="15" r="2.5" fill="#74c69d"/>
    <path d="M48 82 L28 92" stroke="#74c69d" stroke-width="2.5" stroke-linecap="round"/>
    <circle cx="16" cy="86" r="2.5" fill="#74c69d"/>
    <circle cx="18" cy="100" r="2.5" fill="#74c69d"/>
  </svg>
  <div>
    <div class="page-title">Hypothesis Lab</div>
    <div class="page-sub">All ranked hypotheses · click any card to expand · {len(residues_data)} total</div>
  </div>
</div>

<div class="stat-row">
  <div class="sc"><div class="sn" style="color:#eee">{len(residues_data)}</div><div class="sl">Hypotheses</div></div>
  <div class="sc"><div class="sn" style="color:#FF4C4C">{n_high}</div><div class="sl">HIGH</div></div>
  <div class="sc"><div class="sn" style="color:#FFA500">{n_med}</div><div class="sl">MEDIUM</div></div>
  <div class="sc"><div class="sn" style="color:#4CA8FF">{n_low}</div><div class="sl">LOW</div></div>
  <div class="sc"><div class="sn" style="color:#FF4C4C;font-size:13px">{top.get('label','—')}</div><div class="sl">Top hit · {top.get('score','—')}</div></div>
</div>

<div class="filter-bar">
  <span style="font-size:11px;color:#3a3d5a;font-family:'IBM Plex Mono',monospace">Filter:</span>
  <button class="fbtn aa active" onclick="filter('ALL',this)">All</button>
  <button class="fbtn" onclick="filter('HIGH',this)" style="color:#FF4C4C88;border-color:#FF4C4C33">HIGH only</button>
  <button class="fbtn am" onclick="filter('MEDIUM',this)">MEDIUM only</button>
  <button class="fbtn al" onclick="filter('LOW',this)">LOW only</button>
  <button class="fbtn" onclick="expandAll()" style="margin-left:auto">Expand all</button>
  <button class="fbtn" onclick="collapseAll()">Collapse all</button>
</div>

<div id="cards"></div>

<script>
const RESIDUES = {res_json};
const CELLD = {cell_json};
const STRUCTANIMS = {struct_json};

function gc(s){{ return s==='critical'?'#FF4C4C':s==='affected'?'#FFA500':'#4CA8FF'; }}

// ── Chain animation ────────────────────────────────────────────────────────
function buildChain(pos, status, score) {{
  const c = gc(status);
  const isH=status==='critical', isM=status==='affected';
  const W=360, total=14, mutI=6, sp=W/(total+1);
  let wt='', mut='';
  for(let i=0;i<total;i++){{
    const x=(i+1)*sp, isMut=i===mutI, r=isMut?10:5;
    wt+=`<circle cx="${{x}}" cy="23" r="5" fill="#0a1f0a" stroke="#4CAF50" stroke-width="1"/>`;
    if(i<total-1) wt+=`<line x1="${{x+5}}" y1="23" x2="${{(i+2)*sp-5}}" y2="23" stroke="#1a3a1a" stroke-width="1.2"/>`;
    const anim=isMut?`style="transform-origin:${{x}}px 23px;animation:wobble-${{status}} 1.4s ease-in-out infinite"` :'';
    mut+=`<circle cx="${{x}}" cy="23" r="${{r}}" fill="${{isMut?c+'22':'#040608'}}" stroke="${{isMut?c:'#1e2030'}}" stroke-width="${{isMut?2.5:0.8}}" ${{anim}}/>`;
    if(i<total-1) mut+=`<line x1="${{x+(isMut?r:5)}}" y1="23" x2="${{(i+2)*sp-5}}" y2="23" stroke="${{isMut?c:'#1a1d2e'}}" stroke-width="1.2"/>`;
  }}
  const pcts=isH?[8,3,28,2]:isM?[50,45,72,55]:[88,90,92,88];
  const lbls=['Zinc coord.','DNA binding','Thermal stab.','Transcription'];
  const bars=lbls.map((l,i)=>`<div class="brow">
    <div class="blbl"><span>${{l}}</span><span style="color:${{c}}">${{pcts[i]}}% WT</span></div>
    <div class="btrack"><div class="bwt"></div><div class="bfill" style="width:${{pcts[i]}}%;background:${{c}}"></div></div>
  </div>`).join('');
  return `<div class="anim-box">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div>
        <div class="clabel" style="color:#4CAF50">Wild-type chain</div>
        <svg class="csvg" viewBox="0 0 ${{W}} 46">${{wt}}</svg>
        <div class="clabel" style="color:${{c}};margin-top:7px">Mutant — pos ${{pos}} (wobble = instability)</div>
        <svg class="csvg" viewBox="0 0 ${{W}} 46">${{mut}}</svg>
        <div style="font-size:9px;color:#3a3d5a;margin-top:5px;line-height:1.5">${{isH?'Critical — near-complete functional collapse.':isM?'Medium — partial reduction.':'Low — likely tolerated.'}}</div>
      </div>
      <div><div class="clabel">Function vs wild-type (score ${{score}})</div>${{bars}}</div>
    </div>
  </div>`;
}}

// ── Structural protein animation ───────────────────────────────────────────
function buildStructAnim(d, idx) {{
  const structKey = d.struct_effect || 'default';
  const sa = STRUCTANIMS[structKey] || STRUCTANIMS['default'];
  const c = gc(d.status);

  // Build stage rows
  const stageRows = sa.stages.map((s,i)=>`
    <div class="stage-row" id="stage-${{idx}}-${{i}}" style="color:${{sa.colors[i]}}">
      <div class="stage-dot" style="background:${{sa.colors[i]}}"></div>
      <div class="stage-text">${{s}}</div>
    </div>`).join('');

  return `<div class="struct-anim-section">
    <div class="struct-title">Structural mechanism — drag slider →</div>
    <div class="struct-label" style="color:${{c}}">${{sa.label}}</div>
    <div class="struct-desc">${{sa.desc}}</div>

    <!-- SVG protein sketch that animates with slider -->
    <svg class="protein-canvas" id="psvg-${{idx}}" viewBox="0 0 320 120" xmlns="http://www.w3.org/2000/svg">
      <!-- WT protein sketch - always shown faded -->
      <g id="prot-wt-${{idx}}" opacity="0.25">
        <!-- Helix backbone -->
        <path d="M20 60 Q50 40 80 60 Q110 80 140 60 Q170 40 200 60 Q230 80 260 60 Q285 45 300 55" stroke="#4CAF50" stroke-width="2.5" fill="none" stroke-linecap="round"/>
        <!-- DNA strand above -->
        <path d="M20 30 L300 30" stroke="#378add" stroke-width="1.5" stroke-dasharray="8,4" opacity="0.8"/>
        <!-- Connection lines (protein-DNA contacts) -->
        <line x1="80" y1="55" x2="80" y2="30" stroke="#4CAF50" stroke-width="1.5" opacity="0.8"/>
        <line x1="140" y1="55" x2="140" y2="30" stroke="#4CAF50" stroke-width="1.5" opacity="0.8"/>
        <line x1="200" y1="55" x2="200" y2="30" stroke="#4CAF50" stroke-width="1.5" opacity="0.8"/>
        <!-- Zinc ion -->
        <circle cx="160" cy="85" r="8" fill="none" stroke="#FFC107" stroke-width="2"/>
        <text x="160" y="89" text-anchor="middle" font-size="8" fill="#FFC107" font-family="monospace">Zn</text>
        <!-- Coord lines -->
        <line x1="120" y1="65" x2="153" y2="80" stroke="#FFC107" stroke-width="1" opacity="0.7"/>
        <line x1="140" y1="70" x2="154" y2="79" stroke="#FFC107" stroke-width="1" opacity="0.7"/>
        <line x1="180" y1="70" x2="167" y2="79" stroke="#FFC107" stroke-width="1" opacity="0.7"/>
        <line x1="200" y1="65" x2="167" y2="80" stroke="#FFC107" stroke-width="1" opacity="0.7"/>
      </g>
      <!-- Mutant protein - animated by JS -->
      <g id="prot-mut-${{idx}}">
        <path id="pm-helix-${{idx}}" d="M20 60 Q50 40 80 60 Q110 80 140 60 Q170 40 200 60 Q230 80 260 60 Q285 45 300 55" stroke="#4CAF50" stroke-width="2.5" fill="none" stroke-linecap="round"/>
        <path id="pm-dna-${{idx}}" d="M20 30 L300 30" stroke="#378add" stroke-width="1.5" stroke-dasharray="8,4" opacity="0.8"/>
        <line id="pm-c1-${{idx}}" x1="80" y1="55" x2="80" y2="30" stroke="#4CAF50" stroke-width="1.5"/>
        <line id="pm-c2-${{idx}}" x1="140" y1="55" x2="140" y2="30" stroke="#4CAF50" stroke-width="1.5"/>
        <line id="pm-c3-${{idx}}" x1="200" y1="55" x2="200" y2="30" stroke="#4CAF50" stroke-width="1.5"/>
        <circle id="pm-zn-${{idx}}" cx="160" cy="85" r="8" fill="none" stroke="#FFC107" stroke-width="2"/>
        <text id="pm-znl-${{idx}}" x="160" y="89" text-anchor="middle" font-size="8" fill="#FFC107" font-family="monospace">Zn</text>
        <!-- Mutation marker -->
        <circle id="pm-mut-${{idx}}" cx="140" cy="60" r="6" fill="${{c}}44" stroke="${{c}}" stroke-width="2"/>
        <text id="pm-mutl-${{idx}}" x="140" y="63" text-anchor="middle" font-size="7" fill="${{c}}" font-family="monospace">MUT</text>
      </g>
      <!-- Stage label -->
      <text id="psvg-label-${{idx}}" x="160" y="115" text-anchor="middle" font-size="9" fill="#555" font-family="monospace">Wild-type conformation</text>
    </svg>

    <div class="struct-stages" id="stages-${{idx}}">${{stageRows}}</div>
  </div>`;
}}

function updateStructAnim(idx, stage, structKey, c) {{
  const sa = STRUCTANIMS[structKey] || STRUCTANIMS['default'];
  const total = sa.stages.length;
  const progress = stage / (total - 1); // 0–1

  // Update stage highlights
  for(let i=0; i<total; i++) {{
    const el = document.getElementById('stage-'+idx+'-'+i);
    if(el) el.classList.toggle('active', i <= stage);
  }}

  // Animate SVG elements based on progress
  const helix = document.getElementById('pm-helix-'+idx);
  const dna   = document.getElementById('pm-dna-'+idx);
  const c1    = document.getElementById('pm-c1-'+idx);
  const c2    = document.getElementById('pm-c2-'+idx);
  const c3    = document.getElementById('pm-c3-'+idx);
  const zn    = document.getElementById('pm-zn-'+idx);
  const znl   = document.getElementById('pm-znl-'+idx);
  const lbl   = document.getElementById('psvg-label-'+idx);

  if(!helix) return;

  // Stage label
  if(lbl) lbl.textContent = sa.stages[Math.min(stage, total-1)] || '';

  if(structKey === 'zinc_collapse') {{
    // Helix distorts, zinc disappears, DNA separates
    const helixColor = progress < 0.3 ? '#4CAF50' : progress < 0.6 ? '#FFA500' : '#FF4C4C';
    helix.setAttribute('stroke', helixColor);
    const znOpacity = Math.max(0, 1 - progress * 1.5);
    if(zn) {{ zn.setAttribute('opacity', znOpacity); if(znl) znl.setAttribute('opacity', znOpacity); }}
    const dnaGap = 30 + progress * 35;
    if(dna) dna.setAttribute('d', `M20 ${{dnaGap}} L300 ${{dnaGap}}`);
    const cOpacity = Math.max(0, 1 - progress * 2);
    [c1,c2,c3].forEach(c => {{ if(c) c.setAttribute('opacity', cOpacity); }});
    // Distort helix path at high progress
    if(progress > 0.5) {{
      const wobble = (progress-0.5)*40;
      helix.setAttribute('d', `M20 60 Q50 ${{40+wobble}} 80 ${{60+wobble*0.5}} Q110 ${{80-wobble*0.3}} 140 ${{60+wobble*0.7}} Q170 ${{40+wobble*0.4}} 200 60 Q230 80 260 60 Q285 45 300 55`);
    }}
  }} else if(structKey === 'dna_contact_loss') {{
    // DNA floats away, contacts break
    const dnaY = 30 + progress * 40;
    if(dna) dna.setAttribute('d', `M20 ${{dnaY}} L300 ${{dnaY}}`);
    const c1Y2 = 30 + progress * 40;
    const c2Y2 = 30 + progress * 40;
    if(c1) {{ c1.setAttribute('y2', c1Y2); c1.setAttribute('opacity', Math.max(0, 1-progress*1.5)); }}
    if(c2) {{ c2.setAttribute('y2', c2Y2); c2.setAttribute('stroke', '#FF4C4C'); c2.setAttribute('opacity', Math.max(0.1, 1-progress)); }}
    if(c3) {{ c3.setAttribute('y2', c2Y2); c3.setAttribute('opacity', Math.max(0, 1-progress*1.2)); }}
    helix.setAttribute('stroke', progress > 0.5 ? '#FFA500' : '#4CAF50');
  }} else if(structKey === 'helix_break') {{
    // Helix unfolds at mutation site
    const breakAmt = progress * 30;
    helix.setAttribute('d', `M20 60 Q50 40 80 60 Q110 80 130 ${{60+breakAmt}} Q150 ${{40+breakAmt*1.5}} 170 ${{60+breakAmt*0.5}} Q200 ${{80-breakAmt*0.3}} 260 60 Q285 45 300 55`);
    helix.setAttribute('stroke', progress > 0.4 ? '#FFA500' : '#4CAF50');
    if(dna) dna.setAttribute('opacity', Math.max(0.2, 1-progress*0.8));
    [c1,c2,c3].forEach((cc,i) => {{ if(cc) cc.setAttribute('opacity', i===1 ? Math.max(0, 1-progress*2) : 0.6); }});
  }} else {{
    // Default: colour shift only
    const h = progress < 0.5 ? '#4CAF50' : progress < 0.8 ? '#FFA500' : '#FF4C4C';
    helix.setAttribute('stroke', h);
    if(dna) dna.setAttribute('opacity', Math.max(0.3, 1-progress*0.7));
    [c1,c2,c3].forEach(cc => {{ if(cc) cc.setAttribute('stroke', h).setAttribute('opacity', Math.max(0.2, 1-progress*0.8)); }});
  }}
}}

// ── Slider ────────────────────────────────────────────────────────────────
function buildSlider(d, idx) {{
  const c = gc(d.status);
  const isH = d.status==='critical';
  if(d.score < 0.3) {{
    return `<div class="slider-struct-grid">
      <div style="grid-column:1/-1;background:#0a1a0a;border:1px solid #1a3a1a;border-radius:6px;padding:10px;font-size:10px;color:#666;line-height:1.6">
        LOW effect score (${{d.score}}). No pathological progression timeline applicable — this variant likely represents tolerated substitution or normal variation in the assayed function.
      </div>
    </div>`;
  }}

  const events = [
    {{day:1, label:"Single-cell mutation", desc:"One cell acquires this mutation. Immune surveillance may clear it.", c:'#555'}},
    {{day:isH?60:120, label:"Clonal expansion", desc:"If the mutant cell escapes clearance, it divides and passes the mutation to daughter cells.", c:c}},
    {{day:isH?180:365, label:"Detectable population", desc:"Sensitive liquid biopsy might detect mutant fragments. Still asymptomatic.", c:c}},
    {{day:isH?365:730, label:"Microenvironment effects", desc:"VEGF/TGF-β signalling starts influencing neighbouring cells. Paracrine, not direct mutation spread.", c:'#e24b4a'}},
    {{day:isH?730:1460, label:"Clinical detection window", desc:"At typical detection sizes (~0.5–1cm). Billions of cell divisions have occurred.", c:'#e24b4a'}},
  ];
  const maxDay = events[events.length-1].day + 200;
  const structKey = d.struct_effect || 'default';
  const sa = STRUCTANIMS[structKey] || STRUCTANIMS['default'];
  const totalStages = sa.stages.length;

  window._sliderEvents = window._sliderEvents || {{}};
  window._sliderEvents[idx] = events;
  window._sliderMax = window._sliderMax || {{}};
  window._sliderMax[idx] = maxDay;
  window._structKeys = window._structKeys || {{}};
  window._structKeys[idx] = structKey;
  window._structColors = window._structColors || {{}};
  window._structColors[idx] = c;
  window._totalStages = window._totalStages || {{}};
  window._totalStages[idx] = totalStages;

  const evHTML = events.map((e,i)=>`
    <div class="pevt inactive" id="ev-${{idx}}-${{i}}">
      <div class="pdotev" style="background:${{e.c}}"></div>
      <div><strong>Day ~${{e.day}}: ${{e.label}}</strong><span>${{e.desc}}</span></div>
    </div>`).join('');

  return `<div class="slider-struct-grid">

    <!-- LEFT: Timeline slider -->
    <div class="slider-section">
      <div class="slider-title">Mutation timeline — drag to explore</div>
      <div style="background:#0a0c1a;border:1px solid #1a1d3a;border-radius:5px;padding:8px;margin-bottom:8px;font-size:9px;color:#444;line-height:1.5">
        ⚠ Population-level estimates. Not individual predictions. Timelines vary enormously by cell type, co-mutations, immune function.
      </div>
      <div class="slider-row">
        <span class="slider-lbl">Day (drag)</span>
        <input type="range" id="sl-${{idx}}" min="0" max="${{maxDay}}" value="0" oninput="updateSlider(${{idx}}, parseInt(this.value))">
        <span class="slider-val" id="sv-${{idx}}">Day 0</span>
      </div>
      <div class="phase-bar">
        <div class="phase-fill" id="pf-${{idx}}" style="width:0%;background:${{c}}"></div>
        <div class="marker" id="mk-${{idx}}" style="left:0%"></div>
      </div>
      <div style="margin-top:8px">${{evHTML}}</div>
    </div>

    <!-- RIGHT: Structural animation -->
    ${{buildStructAnim(d, idx)}}

  </div>`;
}}

function updateSlider(idx, day) {{
  const events  = (window._sliderEvents||{{}})[idx] || [];
  const maxDay  = (window._sliderMax||{{}})[idx] || 2000;
  const structKey = (window._structKeys||{{}})[idx] || 'default';
  const c       = (window._structColors||{{}})[idx] || '#FF4C4C';
  const totalStages = (window._totalStages||{{}})[idx] || 6;

  // Update day label
  const sv = document.getElementById('sv-'+idx);
  if(sv) sv.textContent = day===0 ? 'Day 0' : day>365 ? `Day ${{day}} (~${{(day/365).toFixed(1)}}yr)` : `Day ${{day}}`;

  // Update progress bar
  const pct = (day/maxDay*100).toFixed(1);
  const pf  = document.getElementById('pf-'+idx);
  const mk  = document.getElementById('mk-'+idx);
  if(pf) {{ pf.style.width=pct+'%'; pf.textContent=day<(events[2]?.day||180)?'subclinical':day<(events[4]?.day||730)?'detectable':'clinical'; }}
  if(mk) mk.style.left=pct+'%';

  // Update timeline events
  events.forEach((e,i) => {{
    const el = document.getElementById('ev-'+idx+'-'+i);
    if(el) el.classList.toggle('inactive', day<e.day);
  }});

  // Update structural animation — map day to stage
  const stage = Math.min(totalStages-1, Math.floor((day/maxDay) * totalStages));
  updateStructAnim(idx, stage, structKey, c);
}}

// ── Cell diagram ──────────────────────────────────────────────────────────
function buildCell(d) {{
  const imp = CELLD[d.cell] || CELLD['structural'];
  const c = imp.color;
  const anim = imp.anim;
  return `<div class="cell-section">
    <div class="sl2" style="margin-top:0">Cell-level impact</div>
    <div class="cell-layout">
      <div class="cell-anim-col">
        <svg width="52" height="52" viewBox="0 0 52 52">
          <ellipse cx="26" cy="26" rx="22" ry="20" fill="#0a1f0a" stroke="#2a5a2a" stroke-width="1.5"/>
          <ellipse cx="26" cy="26" rx="8" ry="7" fill="#1a4a1a" stroke="#4CAF50" stroke-width="1.5"/>
          <text x="26" y="29" text-anchor="middle" font-size="5" fill="#4CAF50" font-family="monospace">WT</text>
        </svg>
        <span style="font-size:9px;color:#4CAF50;font-family:'IBM Plex Mono',monospace">Normal</span>
        <span style="color:${{c}};font-size:13px;line-height:1">↓</span>
        <svg width="52" height="52" viewBox="0 0 52 52" style="animation:${{anim}} 2s ease-in-out infinite;transform-origin:center">
          <ellipse cx="26" cy="26" rx="22" ry="20" fill="#1f0808" stroke="${{c}}" stroke-width="1.5" stroke-dasharray="4,2"/>
          <ellipse cx="26" cy="26" rx="10" ry="8" fill="#2a0808" stroke="${{c}}" stroke-width="1.5"/>
          <circle cx="12" cy="16" r="2.5" fill="${{c}}" opacity="0.7"/>
          <circle cx="40" cy="36" r="2" fill="${{c}}" opacity="0.5"/>
          <text x="26" y="29" text-anchor="middle" font-size="5" fill="${{c}}" font-family="monospace">MUT</text>
        </svg>
        <span style="font-size:9px;color:${{c}};font-family:'IBM Plex Mono',monospace">Affected</span>
      </div>
      <div class="cell-info-col">
        <div class="cell-title" style="color:${{c}}">${{imp.title}}</div>
        <div class="cell-desc">${{imp.desc}}</div>
      </div>
    </div>
  </div>`;
}}

// ── Cards ─────────────────────────────────────────────────────────────────
function buildCard(d, idx) {{
  const c = gc(d.status);
  const hyp = d.hypothesis || `Residue ${{d.pos}} (${{d.label}}) — ${{d.priority}} priority (score ${{d.score}}).`;
  return `<div class="hcard" id="card-${{idx}}" data-priority="${{d.priority}}">
    <div class="hheader" onclick="toggle(${{idx}})">
      <span class="hrank">#${{idx+1}}</span>
      <div class="pdot" style="background:${{c}}"></div>
      <span class="hlabel">${{d.label}}</span>
      <span class="badge" style="background:${{c}}22;color:${{c}};border:0.5px solid ${{c}}55">${{d.priority}}</span>
      <span class="hscore" style="color:${{c}}">${{d.score}}</span>
      <span style="color:#3a3d5a;font-size:10px;margin-left:6px">${{d.expType||''}}</span>
      <span class="chev" id="chev-${{idx}}">▶</span>
    </div>
    <div class="hbody" id="body-${{idx}}">
      <div class="bgrid">
        <div class="bleft">
          <div class="sl2" style="margin-top:0">Hypothesis</div>
          <div class="hyp-text">${{hyp}}</div>
          <div class="sl2">Structural annotation</div>
          <div class="drow"><span class="dl">Domain</span><span class="dv">${{d.domain}}</span></div>
          <div class="drow"><span class="dl">Mechanism</span><span class="dv">${{d.mechanism}}</span></div>
          <div class="sl2">Clinical data</div>
          <div class="drow"><span class="dl">ClinVar</span><span class="dv">${{d.clinvar}}</span></div>
          <div class="drow"><span class="dl">COSMIC</span><span class="dv">${{d.cosmic}}</span></div>
          <div class="drow"><span class="dl">Cancer types</span><span class="dv">${{d.cancer}}</span></div>
          <div class="drow"><span class="dl">Therapeutic</span><span class="dv">${{d.therapeutic}}</span></div>
          <div class="action-box">
            <div class="al">Recommended experiment</div>
            <div class="at">${{d.experiment}}</div>
          </div>
        </div>
        <div class="bright">
          <div class="sl2" style="margin-top:0">Structural fluctuation — WT vs mutant</div>
          ${{buildChain(d.pos, d.status, d.score)}}
          ${{buildSlider(d, idx)}}
          ${{buildCell(d)}}
        </div>
      </div>
    </div>
  </div>`;
}}

const wrap = document.getElementById('cards');
RESIDUES.forEach((d,i) => {{ wrap.innerHTML += buildCard(d,i); }});

function toggle(idx) {{
  const body=document.getElementById('body-'+idx), chev=document.getElementById('chev-'+idx);
  const open=body.classList.contains('open');
  body.classList.toggle('open',!open);
  chev.classList.toggle('open',!open);
}}
function filter(p,btn) {{
  document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('active')); btn.classList.add('active');
  document.querySelectorAll('.hcard').forEach(c=>{{ c.style.display=(p==='ALL'||c.dataset.priority===p)?'block':'none'; }});
}}
function expandAll(){{document.querySelectorAll('.hbody').forEach(b=>b.classList.add('open'));document.querySelectorAll('.chev').forEach(c=>c.classList.add('open'));}}
function collapseAll(){{document.querySelectorAll('.hbody').forEach(b=>b.classList.remove('open'));document.querySelectorAll('.chev').forEach(c=>c.classList.remove('open'));}}

// Auto-open first HIGH
const fh=document.querySelector('[data-priority="HIGH"] .hbody'), fc=document.querySelector('[data-priority="HIGH"] .chev');
if(fh){{fh.classList.add('open');fc.classList.add('open');}}
</script>
</body>
</html>"""


def render():
    st.markdown(f'{LOGO_SVG} &nbsp;<span style="font-size:1.2rem;font-weight:700;font-family:IBM Plex Mono,monospace;vertical-align:middle">Hypothesis Lab</span>', unsafe_allow_html=True)
    st.markdown("Click any card to expand · structural animation + mutation timeline slide together on the right")
    st.divider()

    if "t_scored" not in st.session_state:
        st.info("👈 Run Triage first in the **Triage System** tab — all hypotheses appear here automatically.")
        return

    scored_df = st.session_state.t_scored

    with st.spinner("Building hypothesis lab..."):
        pdb_data = fetch_pdb()

    if not pdb_data:
        st.error("Could not load protein structure. Check your internet connection.")
        return

    residues = []
    for _, row in scored_df.iterrows():
        pos       = int(row["residue_position"])
        score     = round(float(row.get("normalized_score", row.get("effect_score", 0))), 3)
        label     = str(row.get("mutation", f"Res{pos}"))
        priority  = str(row.get("priority", "LOW"))
        exp_type  = str(row.get("experiment_type", ""))
        hypothesis = str(row.get("hypothesis", ""))
        status    = {"HIGH": "critical", "MEDIUM": "affected", "LOW": "normal"}[priority]
        hs        = HOTSPOT_DATA.get(pos, {})
        residues.append({
            "pos": pos, "label": label, "score": score,
            "priority": priority, "expType": exp_type if exp_type not in ("nan","") else "",
            "status": status, "hypothesis": hypothesis,
            "mechanism":    hs.get("mechanism",   "Effect score from your experimental data. Phase 2 database integration will add mechanistic annotation."),
            "clinvar":      hs.get("clinvar",      "Not queried — Phase 2 integrates live ClinVar"),
            "cosmic":       hs.get("cosmic",       "Not queried"),
            "cancer":       hs.get("cancer",       "Not queried"),
            "therapeutic":  hs.get("therapeutic",  "Consult clinical database"),
            "domain":       hs.get("domain",       "Unknown — Phase 2 annotation pending"),
            "experiment":   hs.get("experiment",   "Run thermal shift assay and EMSA as first-line validation."),
            "cell":         hs.get("cell",         "apoptosis" if status=="critical" else "structural"),
            "struct_effect":hs.get("struct_effect","default"),
        })

    html = build_lab_html(residues, pdb_data)
    components.html(html, height=3200, scrolling=True)
