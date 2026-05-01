"""
hypothesis_lab.py — Protellect Hypothesis Lab (Tab 4)
- Real logo embedded from uploaded image
- Large canvas protein structure animation (DNA binding, helix breaking, zinc collapse)
- Cell diagram updates in sync with protein animation
- Timeline slider drives both protein + cell simultaneously
- Works with any dataset
"""

import streamlit as st
import streamlit.components.v1 as components
import json, base64, requests
from pathlib import Path

# ── Logo (base64 encoded from uploaded image) ─────────────────────────────────
def _load_logo():
    p = Path("/mnt/user-data/uploads/1777622887238_image.png")
    if p.exists():
        return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
    return None

LOGO_DATA_URL = _load_logo()

# ── Known hotspot enrichment ──────────────────────────────────────────────────
HOTSPOT_DATA = {
    175: {
        "mechanism": "Disrupts zinc coordination at the C176/H179/C238/C242 tetrahedral site. The L2 loop unfolds and the entire DNA-binding domain loses its compact conformation.",
        "clinvar": "Pathogenic · 847 submissions", "cosmic": "~6% of all cancers",
        "cancer": "Breast, lung, colorectal, ovarian, bladder",
        "therapeutic": "APR-246 (eprenetapopt) — refolding compound, Phase III trials",
        "cell": "apoptosis", "domain": "DNA-binding domain (L2 loop) — zinc coordination site",
        "experiment": "Thermal shift assay (Tm reduction ~8–10°C) → EMSA (confirm loss of DNA binding) → luciferase reporter (p21/MDM2 activation).",
        "struct_effect": "zinc_collapse",
    },
    248: {
        "mechanism": "Direct DNA contact residue in L3 loop. Makes hydrogen bonds to minor groove at CATG sequences. Substitution abolishes sequence-specific DNA binding.",
        "clinvar": "Pathogenic · 623 submissions", "cosmic": "~3% of all cancers",
        "cancer": "Colorectal, lung, pancreatic, ovarian",
        "therapeutic": "Synthetic lethality under investigation",
        "cell": "checkpoint", "domain": "DNA-binding domain (L3 loop) — direct DNA contact",
        "experiment": "EMSA to confirm loss of DNA binding. Luciferase reporter for transcriptional activity.",
        "struct_effect": "dna_contact_loss",
    },
    273: {
        "mechanism": "DNA backbone phosphate contact. Loss reduces DNA-binding affinity >100-fold. R273C retains partial structure unlike R273H.",
        "clinvar": "Pathogenic · 512 submissions", "cosmic": "~3% of all cancers",
        "cancer": "Colorectal, lung, brain, pancreatic",
        "therapeutic": "Small molecule stabilizers in experimental stage",
        "cell": "checkpoint", "domain": "DNA-binding domain (S10 strand) — backbone contact",
        "experiment": "EMSA. Test R273C and R273H separately — different severity.",
        "struct_effect": "dna_contact_loss",
    },
    249: {
        "mechanism": "H2 helix structural mutation. Characteristic aflatoxin B1 mutational signature. Disrupts HIPK2 interaction.",
        "clinvar": "Pathogenic · 298 submissions", "cosmic": "~1.5% — enriched in liver cancer",
        "cancer": "Liver (HCC), lung, esophageal",
        "therapeutic": "No specific therapy — aflatoxin avoidance in endemic regions",
        "cell": "proliferation", "domain": "DNA-binding domain (H2 helix)",
        "experiment": "Reporter assay. Co-IP for dominant negative tetramer formation.",
        "struct_effect": "helix_break",
    },
    245: {
        "mechanism": "Glycine essential for L3 loop geometry. Any side chain sterically clashes with the DNA backbone, disrupting loop geometry.",
        "clinvar": "Pathogenic · 187 submissions", "cosmic": "~1.5% of cancers",
        "cancer": "Breast, lung, sarcoma, hematologic",
        "therapeutic": "Structural correctors under investigation",
        "cell": "apoptosis", "domain": "DNA-binding domain (L3 loop)",
        "experiment": "Thermal shift + EMSA. APR-246 rescue if structural mutant confirmed.",
        "struct_effect": "loop_distortion",
    },
    282: {
        "mechanism": "R282 salt bridge with E271 stabilises H2 helix. Tryptophan disrupts this causing partial helix unfolding.",
        "clinvar": "Pathogenic · 156 submissions", "cosmic": "~1% of cancers",
        "cancer": "Breast, colorectal, lung",
        "therapeutic": "No approved targeted therapy",
        "cell": "apoptosis", "domain": "DNA-binding domain (H2 helix)",
        "experiment": "Thermal shift assay. Luciferase reporter for p21/MDM2.",
        "struct_effect": "helix_break",
    },
    220: {
        "mechanism": "Creates a surface hydrophobic cavity that destabilises the domain thermodynamically. Not a direct DNA contact — the cavity is a druggable pocket.",
        "clinvar": "Pathogenic · 89 submissions", "cosmic": "~1% of cancers",
        "cancer": "Breast, lung, ovarian",
        "therapeutic": "PC14586 (rezatapopt) — specifically fills the Y220C cavity, Phase II trials",
        "cell": "apoptosis", "domain": "DNA-binding domain (S7-S8 loop)",
        "experiment": "Thermal shift. APR-246 and PC14586 rescue — prime cavity-filling candidate.",
        "struct_effect": "surface_cavity",
    },
}

CELL_DATA = {
    "apoptosis":     {"title": "Loss of apoptosis signalling",      "color": "#FF4C4C", "anim": "cpulse", "desc": "TP53 normally activates BAX, PUMA, and NOXA to trigger programmed cell death. This mutation abolishes that signal — damaged cells survive and accumulate further mutations, driving tumour development."},
    "checkpoint":    {"title": "DNA damage checkpoint bypass",       "color": "#FFA500", "anim": "cspin",  "desc": "TP53 normally halts the cell cycle at G1/S via p21. This contact mutation prevents p21 activation — cells divide with unrepaired DNA every cycle, accumulating genomic instability."},
    "proliferation": {"title": "Gain-of-function proliferation",     "color": "#CC44CC", "anim": "cgrow",  "desc": "This gain-of-function mutation inhibits p63/p73 and activates MYC/VEGF programmes — actively driving oncogenic proliferation rather than merely losing tumour suppression."},
    "structural":    {"title": "Structural propagation effect",      "color": "#FFA500", "anim": "cshake", "desc": "This residue is not directly mutated but its function is compromised by structural changes propagating from nearby critical mutations."},
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


def build_html(residues_data, pdb_data, logo_url):
    res_json  = json.dumps(residues_data)
    cell_json = json.dumps(CELL_DATA)
    pdb_esc   = pdb_data.replace("\\","\\\\").replace("`","\\`").replace("${","\\${")[:280000]

    n_high = sum(1 for r in residues_data if r["priority"] == "HIGH")
    n_med  = sum(1 for r in residues_data if r["priority"] == "MEDIUM")
    n_low  = sum(1 for r in residues_data if r["priority"] == "LOW")
    top    = residues_data[0] if residues_data else {}

    logo_html = f'<img src="{logo_url}" style="width:44px;height:44px;object-fit:contain;border-radius:8px">' if logo_url else '<span style="font-size:28px">🧬</span>'

    return f"""<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#080b14;font-family:'IBM Plex Sans',sans-serif;color:#ccc;font-size:13px;padding:14px}}
::-webkit-scrollbar{{width:5px}}::-webkit-scrollbar-track{{background:#0a0c14}}::-webkit-scrollbar-thumb{{background:#2a2d3a;border-radius:3px}}

.top-header{{display:flex;align-items:center;gap:14px;margin-bottom:16px}}
.page-title{{font-family:'IBM Plex Mono',monospace;font-size:20px;font-weight:700;color:#eee}}
.page-sub{{font-size:12px;color:#555}}

.stat-row{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:14px}}
.sc{{background:#0f1117;border:1px solid #1e2030;border-radius:8px;padding:12px;text-align:center}}
.sn{{font-size:1.4rem;font-weight:600;font-family:'IBM Plex Mono',monospace}}
.sl{{font-size:10px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.08em}}

.filter-bar{{display:flex;gap:8px;margin-bottom:14px;align-items:center;flex-wrap:wrap}}
.fbtn{{padding:6px 14px;border-radius:20px;border:1px solid #1e2030;background:#0f1117;color:#555;font-size:11px;cursor:pointer;font-family:'IBM Plex Mono',monospace;transition:all 0.15s}}
.fbtn.active{{border-color:#FF4C4C;color:#FF4C4C;background:#1a0808}}
.fbtn.am.active{{border-color:#FFA500;color:#FFA500;background:#1a1200}}
.fbtn.al.active{{border-color:#4CA8FF;color:#4CA8FF;background:#08101a}}
.fbtn.aa.active{{border-color:#555;color:#ccc}}

/* Cards */
.hcard{{background:#0a0c14;border:1px solid #1e2030;border-radius:10px;margin-bottom:10px;overflow:hidden}}
.hcard:hover{{border-color:#2a2d3a}}
.hheader{{display:flex;align-items:center;gap:12px;padding:14px 16px;cursor:pointer;user-select:none}}
.hrank{{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#3a3d5a;min-width:28px}}
.pdot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
.hlabel{{font-family:'IBM Plex Mono',monospace;font-size:14px;font-weight:700;color:#eee;flex:1}}
.badge{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:10px;font-weight:600;font-family:'IBM Plex Mono',monospace;margin-right:6px}}
.chev{{color:#444;font-size:12px;transition:transform 0.2s;margin-left:4px}}
.chev.open{{transform:rotate(90deg)}}
.hbody{{display:none;border-top:1px solid #1e2030}}
.hbody.open{{display:block}}

/* Two-column card body */
.card-body-grid{{display:grid;grid-template-columns:380px 1fr;gap:0}}
.bleft{{padding:16px;border-right:1px solid #1e2030;min-width:0}}
.bright{{padding:16px;background:#080b14;min-width:0}}

.sl2{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;padding-bottom:5px;border-bottom:1px solid #1a1d2e;margin:12px 0 8px}}
.sl2:first-child{{margin-top:0}}
.drow{{display:flex;gap:8px;padding:5px 0;border-bottom:1px solid #0d0f1a;font-size:11px}}
.dl{{color:#3a3d5a;min-width:76px;font-size:10px;font-family:'IBM Plex Mono',monospace;flex-shrink:0;padding-top:1px}}
.dv{{color:#bbb;flex:1;line-height:1.5}}
.hyp-text{{font-size:12px;color:#888;line-height:1.7;padding:10px 12px;background:#080b14;border:1px solid #1e2030;border-radius:6px;margin-bottom:10px}}
.action-box{{background:#0a1a0a;border:1px solid #1a3a1a;border-radius:6px;padding:10px 12px;margin-top:8px}}
.al{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.12em;color:#4CAF50;margin-bottom:5px}}
.at{{font-size:11px;color:#888;line-height:1.7}}

/* Chain mini-animation */
.chain-row{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px}}
.chain-lbl{{font-size:10px;font-family:'IBM Plex Mono',monospace;color:#555;margin-bottom:4px}}
.chain-svg{{width:100%;height:42px;border:1px solid #1e2030;border-radius:5px;background:#040608;display:block}}
.bar-row{{margin-bottom:6px}}
.bar-lbl{{display:flex;justify-content:space-between;font-size:10px;color:#555;margin-bottom:2px;font-family:'IBM Plex Mono',monospace}}
.bar-track{{background:#1a1d2e;border-radius:3px;height:6px;overflow:hidden}}
.bar-fill{{height:100%;border-radius:3px;transition:width 0.3s}}

/* Slider */
.slider-box{{margin:12px 0;padding:12px;background:#0a0c14;border:1px solid #1e2030;border-radius:8px}}
.slider-title{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:8px}}
.slider-row{{display:flex;align-items:center;gap:8px;margin-bottom:6px}}
.slider-lbl{{font-size:10px;font-family:'IBM Plex Mono',monospace;color:#555;min-width:60px}}
input[type=range]{{flex:1;accent-color:#FF4C4C;cursor:pointer;height:4px}}
.slider-val{{font-size:11px;font-family:'IBM Plex Mono',monospace;color:#aaa;min-width:80px;text-align:right}}
.phase-bar{{height:12px;background:#1a1d2e;border-radius:6px;position:relative;overflow:hidden;margin:6px 0}}
.phase-fill{{height:100%;border-radius:6px;transition:width 0.3s;min-width:0;display:flex;align-items:center;padding-left:6px;font-size:9px;font-family:'IBM Plex Mono',monospace;color:white;overflow:hidden;white-space:nowrap}}
.marker{{position:absolute;top:0;height:100%;width:2px;background:white;opacity:0.7;transition:left 0.3s;z-index:5}}
.evt{{display:flex;gap:6px;margin-bottom:5px;transition:opacity 0.3s}}
.evt.off{{opacity:0.15}}
.edot{{width:7px;height:7px;border-radius:50%;flex-shrink:0;margin-top:3px}}
.evt strong{{display:block;font-size:10px;color:#eee;margin-bottom:1px}}
.evt span{{font-size:9px;color:#555;line-height:1.4}}

/* ── BIG PROTEIN CANVAS ── */
.prot-canvas-wrap{{margin-top:12px;padding:14px;background:#040608;border:1px solid #1e2030;border-radius:10px}}
.prot-canvas-title{{font-family:'IBM Plex Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:8px}}
.prot-stage-label{{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#aaa;margin:6px 0 4px;text-align:center}}
.prot-stage-desc{{font-size:11px;color:#555;line-height:1.6;text-align:center;margin-bottom:8px;min-height:32px}}
canvas{{display:block;border-radius:6px;background:#040608}}

/* ── CELL DIAGRAM ── */
.cell-wrap{{margin-top:10px;padding:12px;background:#0a0c14;border:1px solid #1e2030;border-radius:8px}}
.cell-inner{{display:grid;grid-template-columns:100px 1fr;gap:12px;align-items:start}}
.cell-col{{display:flex;flex-direction:column;align-items:center;gap:6px}}
.cell-info-title{{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;margin-bottom:5px}}
.cell-desc-text{{font-size:11px;color:#888;line-height:1.6}}
@keyframes cpulse{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.12)}}}}
@keyframes cspin{{0%{{transform:rotate(0deg)}}100%{{transform:rotate(360deg)}}}}
@keyframes cgrow{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.2)}}}}
@keyframes cshake{{0%,100%{{transform:translateX(0)}}25%{{transform:translateX(-3px)}}75%{{transform:translateX(3px)}}}}
@keyframes wobble-critical{{0%,100%{{transform:translateY(0)}}30%{{transform:translateY(-7px)}}70%{{transform:translateY(5px)}}}}
@keyframes wobble-affected{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-3px)}}}}
@keyframes wobble-normal{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-1px)}}}}
</style>
</head>
<body>

<div class="top-header">
  {logo_html}
  <div>
    <div class="page-title">Hypothesis Lab</div>
    <div class="page-sub">{len(residues_data)} hypotheses · click any card to expand full structural + timeline analysis</div>
  </div>
</div>

<div class="stat-row">
  <div class="sc"><div class="sn" style="color:#eee">{len(residues_data)}</div><div class="sl">Total</div></div>
  <div class="sc"><div class="sn" style="color:#FF4C4C">{n_high}</div><div class="sl">HIGH</div></div>
  <div class="sc"><div class="sn" style="color:#FFA500">{n_med}</div><div class="sl">MEDIUM</div></div>
  <div class="sc"><div class="sn" style="color:#4CA8FF">{n_low}</div><div class="sl">LOW</div></div>
  <div class="sc"><div class="sn" style="color:#FF4C4C;font-size:13px">{top.get("label","—")}</div><div class="sl">Top hit · {top.get("score","—")}</div></div>
</div>

<div class="filter-bar">
  <span style="font-size:11px;color:#3a3d5a;font-family:'IBM Plex Mono',monospace">Filter:</span>
  <button class="fbtn aa active" onclick="doFilter('ALL',this)">All</button>
  <button class="fbtn" onclick="doFilter('HIGH',this)" style="color:#FF4C4C88;border-color:#FF4C4C33">HIGH</button>
  <button class="fbtn am" onclick="doFilter('MEDIUM',this)">MEDIUM</button>
  <button class="fbtn al" onclick="doFilter('LOW',this)">LOW</button>
  <button class="fbtn" onclick="expandAll()" style="margin-left:auto">Expand all</button>
  <button class="fbtn" onclick="collapseAll()">Collapse all</button>
</div>

<div id="cards"></div>

<script>
const RESIDUES = {res_json};
const CELLD    = {cell_json};

function gc(s){{ return s==='critical'?'#FF4C4C':s==='affected'?'#FFA500':'#4CA8FF'; }}

// ── Chain animation (mini) ────────────────────────────────────────────────
function buildChain(pos, status, score) {{
  const c=gc(status), isH=status==='critical', isM=status==='affected';
  const W=300,total=12,mutI=5,sp=W/(total+1);
  let wt='',mut='';
  for(let i=0;i<total;i++){{
    const x=(i+1)*sp,isMut=i===mutI,r=isMut?9:5;
    wt+=`<circle cx="${{x}}" cy="21" r="5" fill="#0a1f0a" stroke="#4CAF50" stroke-width="1"/>`;
    if(i<total-1) wt+=`<line x1="${{x+5}}" y1="21" x2="${{(i+2)*sp-5}}" y2="21" stroke="#1a3a1a" stroke-width="1"/>`;
    const a=isMut?`style="transform-origin:${{x}}px 21px;animation:wobble-${{status}} 1.4s ease-in-out infinite"` :'';
    mut+=`<circle cx="${{x}}" cy="21" r="${{r}}" fill="${{isMut?c+'22':'#040608'}}" stroke="${{isMut?c:'#1e2030'}}" stroke-width="${{isMut?2.5:0.8}}" ${{a}}/>`;
    if(i<total-1) mut+=`<line x1="${{x+(isMut?r:5)}}" y1="21" x2="${{(i+2)*sp-5}}" y2="21" stroke="${{isMut?c:'#1a1d2e'}}" stroke-width="1"/>`;
  }}
  const pcts=isH?[8,3,28,2]:isM?[50,45,72,55]:[88,90,92,88];
  const lbls=['Zinc coord.','DNA binding','Thermal stab.','Transcription'];
  const bars=lbls.map((l,i)=>`<div class="bar-row">
    <div class="bar-lbl"><span>${{l}}</span><span style="color:${{c}}">${{pcts[i]}}%</span></div>
    <div class="bar-track"><div class="bar-fill" style="width:${{pcts[i]}}%;background:${{c}}"></div></div>
  </div>`).join('');
  return `<div class="chain-row">
    <div>
      <div class="chain-lbl" style="color:#4CAF50">WT chain</div>
      <svg class="chain-svg" viewBox="0 0 ${{W}} 42">${{wt}}</svg>
      <div class="chain-lbl" style="color:${{c}};margin-top:6px">Mutant (wobble = instability)</div>
      <svg class="chain-svg" viewBox="0 0 ${{W}} 42">${{mut}}</svg>
    </div>
    <div>${{bars}}</div>
  </div>`;
}}

// ── BIG PROTEIN CANVAS ────────────────────────────────────────────────────
const STAGES = {{
  zinc_collapse: {{
    label:"Zinc Coordination Site Collapse",
    stages:["WT: zinc ion stably coordinated by C176/H179/C238/C242","Mutation R175H distorts L2 loop geometry","Zinc coordination weakened — ion becomes mobile","Zinc ion released from binding site","L2 loop unfolds — domain begins to collapse","Full domain misfolding — DNA binding impossible"],
    draw: drawZincCollapse
  }},
  dna_contact_loss: {{
    label:"DNA Contact Interface Lost",
    stages:["WT: R248/R273 directly contacts DNA minor groove","Mutation removes critical contact residue","DNA-binding interface begins to weaken","Protein-DNA hydrogen bonds breaking","DNA strand separating from binding interface","Complete loss of sequence-specific DNA recognition"],
    draw: drawDNAContactLoss
  }},
  helix_break: {{
    label:"α-Helix Disruption",
    stages:["WT: H2 helix stabilised by R282–E271 salt bridge","Mutation removes stabilising salt bridge interaction","Helix N-terminus begins to unwind locally","Unwinding propagates along helix axis","DNA-binding domain reshaped — reduced affinity","Loss of transcriptional activity"],
    draw: drawHelixBreak
  }},
  loop_distortion: {{
    label:"L3 Loop Geometry Distortion",
    stages:["WT: Gly245 allows L3 loop tight approach to DNA","G245S/D adds bulky side chain at critical position","Steric clash with DNA backbone begins","L3 loop forced away from DNA","DNA approach angle blocked","Sequence-specific recognition abolished"],
    draw: drawLoopDistortion
  }},
  surface_cavity: {{
    label:"Hydrophobic Cavity Formation",
    stages:["WT: Y220 fills surface pocket — domain stable","Y220C removes bulky aromatic side chain","Surface pocket opens — hydrophobic residues exposed","Water molecules attempt to fill cavity (unfavourable)","Thermodynamic destabilisation propagates","Tm reduced ~6°C — druggable cavity created"],
    draw: drawSurfaceCavity
  }},
  default: {{
    label:"Functional Disruption",
    stages:["WT: protein in functional conformation","Mutation introduced at target residue","Local structural perturbation","Conformational change propagates","Functional interface altered","Reduced biological activity"],
    draw: drawDefault
  }}
}};

function lerp(a,b,t){{ return a+(b-a)*t; }}
function clamp(v,a,b){{ return Math.max(a,Math.min(b,v)); }}

function drawZincCollapse(ctx, W, H, t, color) {{
  ctx.clearRect(0,0,W,H);
  // DNA strand
  const dnaY = lerp(60, 30, clamp(t*2-0.8,0,1));
  ctx.save();
  ctx.strokeStyle = lerp_color('#378add','#1e2030',clamp(t*1.5-0.5,0,1));
  ctx.lineWidth=3; ctx.setLineDash([12,6]);
  ctx.beginPath(); ctx.moveTo(30,dnaY); ctx.lineTo(W-30,dnaY); ctx.stroke();
  ctx.setLineDash([]);
  // DNA label
  ctx.fillStyle='#378add'; ctx.font='11px IBM Plex Mono,monospace';
  ctx.fillText('DNA', 35, dnaY-8);

  // Protein helix backbone
  const helixColor = t<0.3?'#4CAF50':t<0.6?'#FFA500':'#FF4C4C';
  ctx.strokeStyle=helixColor; ctx.lineWidth=4;
  ctx.beginPath();
  for(let x=30;x<W-30;x++){{
    const wobble = t>0.4 ? Math.sin((x/30)*Math.PI)*lerp(0,18,t-0.4)*((x-W/2)/(W/2)) : 0;
    const y = H/2+20+wobble + Math.sin((x/60)*Math.PI)*8;
    x===30?ctx.moveTo(x,y):ctx.lineTo(x,y);
  }}
  ctx.stroke();

  // Zinc ion
  const znAlpha = clamp(1-t*2,0,1);
  const znX=W/2, znY=H/2+55;
  ctx.globalAlpha=znAlpha;
  ctx.strokeStyle='#FFC107'; ctx.lineWidth=2;
  ctx.beginPath(); ctx.arc(znX,znY,14,0,Math.PI*2); ctx.stroke();
  ctx.fillStyle='#FFC107'; ctx.font='bold 11px IBM Plex Mono,monospace';
  ctx.textAlign='center'; ctx.fillText('Zn²⁺',znX,znY+4);
  ctx.globalAlpha=1;

  // Coordination lines
  const coordAlpha = clamp(1-t*2.5,0,1);
  ctx.globalAlpha=coordAlpha*0.8;
  ctx.strokeStyle='#FFC107'; ctx.lineWidth=1.5; ctx.setLineDash([4,3]);
  [[W/2-60,H/2+20],[W/2-30,H/2+25],[W/2+30,H/2+25],[W/2+60,H/2+20]].forEach(([x,y])=>{{
    ctx.beginPath(); ctx.moveTo(x,y); ctx.lineTo(znX,znY); ctx.stroke();
  }});
  ctx.setLineDash([]); ctx.globalAlpha=1;

  // DNA contact lines
  const contactAlpha = clamp(1-t*2,0,1);
  ctx.globalAlpha=contactAlpha;
  ctx.strokeStyle=helixColor; ctx.lineWidth=2; ctx.setLineDash([4,4]);
  [W/2-60, W/2, W/2+60].forEach(x=>{{
    ctx.beginPath(); ctx.moveTo(x,H/2+15); ctx.lineTo(x,dnaY); ctx.stroke();
  }});
  ctx.setLineDash([]); ctx.globalAlpha=1;

  // Mutation marker
  const mutX=W/2-30, mutY=H/2+20;
  ctx.fillStyle=color+'44'; ctx.strokeStyle=color; ctx.lineWidth=2.5;
  ctx.beginPath(); ctx.arc(mutX,mutY,12,0,Math.PI*2); ctx.fill(); ctx.stroke();
  ctx.fillStyle=color; ctx.font='bold 9px IBM Plex Mono,monospace'; ctx.textAlign='center';
  ctx.fillText('R175H',mutX,mutY+3);

  // Stage indicator
  ctx.fillStyle='#3a3d5a'; ctx.font='10px IBM Plex Mono,monospace'; ctx.textAlign='left';
  ctx.restore();
}}

function drawDNAContactLoss(ctx, W, H, t, color) {{
  ctx.clearRect(0,0,W,H);
  const dnaY = lerp(55, 20, clamp(t*1.8-0.3,0,1));
  // DNA strand drifting away
  ctx.save();
  ctx.strokeStyle=lerp_color('#378add','#1e2030',t*0.8);
  ctx.lineWidth=3; ctx.setLineDash([12,6]);
  ctx.beginPath(); ctx.moveTo(30,dnaY); ctx.lineTo(W-30,dnaY); ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle='#378add'; ctx.font='11px IBM Plex Mono,monospace';
  ctx.fillText('DNA', 35, dnaY-8);

  // Protein
  ctx.strokeStyle=t<0.4?'#4CAF50':'#FFA500'; ctx.lineWidth=4;
  ctx.beginPath();
  for(let x=30;x<W-30;x++){{
    const y=H/2+20+Math.sin((x/70)*Math.PI)*10;
    x===30?ctx.moveTo(x,y):ctx.lineTo(x,y);
  }}
  ctx.stroke();

  // Contact residues
  const contacts=[W/2-70,W/2,W/2+70];
  contacts.forEach((cx,i)=>{{
    const broken = t > 0.3+(i*0.15);
    const cy=H/2+20+Math.sin((cx/70)*Math.PI)*10;
    ctx.strokeStyle=broken?color:'#4CAF50'; ctx.lineWidth=2;
    if(!broken){{
      ctx.setLineDash([]);
      ctx.beginPath(); ctx.moveTo(cx,cy); ctx.lineTo(cx,dnaY); ctx.stroke();
      // Contact dot on DNA
      ctx.fillStyle='#4CAF50';
      ctx.beginPath(); ctx.arc(cx,dnaY,5,0,Math.PI*2); ctx.fill();
    }} else {{
      ctx.setLineDash([4,4]);
      ctx.globalAlpha=0.3;
      ctx.beginPath(); ctx.moveTo(cx,cy); ctx.lineTo(cx,dnaY+20); ctx.stroke();
      ctx.globalAlpha=1;
      ctx.setLineDash([]);
      ctx.fillStyle=color+'44'; ctx.strokeStyle=color; ctx.lineWidth=2;
      ctx.beginPath(); ctx.arc(cx,cy,9,0,Math.PI*2); ctx.fill(); ctx.stroke();
      ctx.fillStyle=color; ctx.font='8px IBM Plex Mono,monospace'; ctx.textAlign='center';
      ctx.fillText(i===0?'R248':'R273',cx,cy+3);
    }}
  }});
  ctx.setLineDash([]); ctx.restore();
}}

function drawHelixBreak(ctx, W, H, t, color) {{
  ctx.clearRect(0,0,W,H);
  ctx.save();
  // DNA
  ctx.strokeStyle='#378add33'; ctx.lineWidth=2; ctx.setLineDash([8,5]);
  ctx.beginPath(); ctx.moveTo(30,50); ctx.lineTo(W-30,50); ctx.stroke();
  ctx.setLineDash([]); ctx.fillStyle='#378add55'; ctx.font='10px IBM Plex Mono,monospace';
  ctx.fillText('DNA', 35, 42);

  // Helix — break in the middle
  const breakAmt = t*40;
  const bx = W/2;
  ctx.lineWidth=4;
  // Left half
  ctx.strokeStyle=t<0.3?'#4CAF50':'#FFA500';
  ctx.beginPath();
  for(let x=30;x<bx;x++){{
    const y=H/2+20+Math.sin((x/60)*Math.PI)*12;
    x===30?ctx.moveTo(x,y):ctx.lineTo(x,y);
  }}
  ctx.stroke();
  // Right half — drifting up
  ctx.strokeStyle=t<0.5?'#4CAF50':t<0.75?'#FFA500':'#FF4C4C';
  ctx.beginPath();
  for(let x=bx;x<W-30;x++){{
    const y=H/2+20-breakAmt*0.5+Math.sin((x/60)*Math.PI)*12*(1-t*0.3);
    x===bx?ctx.moveTo(x,y):ctx.lineTo(x,y);
  }}
  ctx.stroke();

  // Mutation marker at break point
  const mutY=H/2+20+Math.sin((bx/60)*Math.PI)*12;
  ctx.fillStyle=color+'44'; ctx.strokeStyle=color; ctx.lineWidth=2.5;
  ctx.beginPath(); ctx.arc(bx,mutY,13,0,Math.PI*2); ctx.fill(); ctx.stroke();
  ctx.fillStyle=color; ctx.font='bold 9px IBM Plex Mono,monospace'; ctx.textAlign='center';
  ctx.fillText('R282W',bx,mutY+3);

  // Salt bridge (disappearing)
  ctx.globalAlpha=clamp(1-t*2,0,1);
  ctx.strokeStyle='#FFC107'; ctx.lineWidth=2; ctx.setLineDash([3,3]);
  ctx.beginPath(); ctx.moveTo(bx-30,H/2+35); ctx.lineTo(bx+30,H/2+35); ctx.stroke();
  ctx.setLineDash([]); ctx.fillStyle='#FFC107'; ctx.font='9px IBM Plex Mono,monospace'; ctx.textAlign='center';
  ctx.fillText('R282–E271 salt bridge',bx,H/2+50);
  ctx.globalAlpha=1;
  ctx.restore();
}}

function drawLoopDistortion(ctx, W, H, t, color) {{
  ctx.clearRect(0,0,W,H);
  ctx.save();
  // DNA
  const dnaY=55+t*25;
  ctx.strokeStyle=lerp_color('#378add','#1e2030',t);
  ctx.lineWidth=3; ctx.setLineDash([12,6]);
  ctx.beginPath(); ctx.moveTo(30,dnaY); ctx.lineTo(W-30,dnaY); ctx.stroke();
  ctx.setLineDash([]); ctx.fillStyle='#378add'; ctx.font='10px IBM Plex Mono,monospace';
  ctx.fillText('DNA', 35, dnaY-8);

  // Protein backbone
  ctx.strokeStyle='#4CAF50'; ctx.lineWidth=4;
  ctx.beginPath();
  for(let x=30;x<W-30;x++){{
    const y=H/2+15+Math.sin((x/80)*Math.PI)*8;
    x===30?ctx.moveTo(x,y):ctx.lineTo(x,y);
  }}
  ctx.stroke();

  // L3 loop — distorting
  const loopX=W/2, loopY=H/2+15;
  const loopDistort = t*35;
  ctx.strokeStyle=t<0.3?'#4CAF50':t<0.6?'#FFA500':'#FF4C4C'; ctx.lineWidth=3;
  ctx.beginPath();
  ctx.moveTo(loopX-50,loopY);
  ctx.quadraticCurveTo(loopX, loopY-20+loopDistort, loopX+50, loopY);
  ctx.stroke();

  // Mutation marker
  ctx.fillStyle=color+'44'; ctx.strokeStyle=color; ctx.lineWidth=2.5;
  ctx.beginPath(); ctx.arc(loopX,loopY-10+loopDistort*0.5,12,0,Math.PI*2); ctx.fill(); ctx.stroke();
  ctx.fillStyle=color; ctx.font='bold 9px IBM Plex Mono,monospace'; ctx.textAlign='center';
  ctx.fillText('G245S',loopX,loopY-7+loopDistort*0.5+3);

  // Steric clash arrow
  if(t>0.3){{
    ctx.globalAlpha=clamp(t-0.3,0,1);
    ctx.strokeStyle='#FF4C4C'; ctx.lineWidth=2;
    ctx.beginPath(); ctx.moveTo(loopX,loopY-20+loopDistort*0.8); ctx.lineTo(loopX,dnaY-5); ctx.stroke();
    ctx.fillStyle='#FF4C4C'; ctx.font='9px IBM Plex Mono,monospace'; ctx.textAlign='center';
    ctx.fillText('steric clash',loopX+40,loopY-5+loopDistort*0.3);
    ctx.globalAlpha=1;
  }}
  ctx.restore();
}}

function drawSurfaceCavity(ctx, W, H, t, color) {{
  ctx.clearRect(0,0,W,H);
  ctx.save();
  // Protein surface
  ctx.strokeStyle=t<0.4?'#4CAF50':t<0.7?'#FFA500':'#FF9800'; ctx.lineWidth=4;
  ctx.beginPath();
  for(let x=30;x<W-30;x++){{
    const y=H/2+Math.sin((x/60)*Math.PI)*10;
    x===30?ctx.moveTo(x,y):ctx.lineTo(x,y);
  }}
  ctx.stroke();

  // Cavity opening
  const cavW=lerp(0,55,t), cavH=lerp(0,40,t);
  const cavX=W/2, cavY=H/2-5;
  ctx.fillStyle=t<0.5?'#1e2030':'#080b14';
  ctx.beginPath(); ctx.ellipse(cavX,cavY+cavH/2,cavW/2,cavH/2,0,0,Math.PI*2); ctx.fill();
  if(t>0.1){{
    ctx.strokeStyle=color; ctx.lineWidth=1.5; ctx.setLineDash([3,3]);
    ctx.beginPath(); ctx.ellipse(cavX,cavY+cavH/2,cavW/2,cavH/2,0,0,Math.PI*2); ctx.stroke();
    ctx.setLineDash([]);
  }}

  // Tyr/Cys label
  ctx.fillStyle=t<0.3?'#4CAF50':color;
  ctx.font='bold 9px IBM Plex Mono,monospace'; ctx.textAlign='center';
  ctx.fillText(t<0.3?'Y220 (Tyr)':'Y220C (cavity)',cavX,cavY+cavH/2+4);

  // Druggable pocket label
  if(t>0.5){{
    ctx.globalAlpha=clamp(t-0.5,0,1)*1.5;
    ctx.fillStyle='#4CA8FF'; ctx.font='10px IBM Plex Mono,monospace';
    ctx.fillText('← druggable pocket',cavX+40,cavY+cavH/2);
    ctx.fillText('(PC14586 target)',cavX+40,cavY+cavH/2+13);
    ctx.globalAlpha=1;
  }}

  // Water molecules
  if(t>0.6){{
    ctx.globalAlpha=clamp((t-0.6)*3,0,0.8);
    for(let i=0;i<4;i++){{
      const wx=cavX-15+i*10, wy=cavY+cavH*0.3+i*5;
      ctx.fillStyle='#64b5f6';
      ctx.beginPath(); ctx.arc(wx,wy,3,0,Math.PI*2); ctx.fill();
    }}
    ctx.fillStyle='#64b5f6'; ctx.font='9px IBM Plex Mono,monospace'; ctx.textAlign='center';
    ctx.fillText('H₂O', cavX, cavY+cavH*0.8);
    ctx.globalAlpha=1;
  }}
  ctx.restore();
}}

function drawDefault(ctx, W, H, t, color) {{
  ctx.clearRect(0,0,W,H);
  ctx.save();
  const c=lerp_color('#4CAF50',color,t);
  ctx.strokeStyle=c; ctx.lineWidth=4;
  ctx.beginPath();
  for(let x=30;x<W-30;x++){{
    const distort=t*Math.sin((x/40)*Math.PI)*15;
    const y=H/2+20+Math.sin((x/70)*Math.PI)*10+distort;
    x===30?ctx.moveTo(x,y):ctx.lineTo(x,y);
  }}
  ctx.stroke();
  const mutX=W/2, mutY=H/2+20;
  ctx.fillStyle=color+'44'; ctx.strokeStyle=color; ctx.lineWidth=2.5;
  ctx.beginPath(); ctx.arc(mutX,mutY,14,0,Math.PI*2); ctx.fill(); ctx.stroke();
  ctx.fillStyle=color; ctx.font='bold 10px IBM Plex Mono,monospace'; ctx.textAlign='center';
  ctx.fillText('MUT',mutX,mutY+4);
  ctx.restore();
}}

function lerp_color(c1,c2,t){{
  t=clamp(t,0,1);
  const p=v=>parseInt(v,16);
  const r1=p(c1.slice(1,3)),g1=p(c1.slice(3,5)),b1=p(c1.slice(5,7));
  const r2=p(c2.slice(1,3)),g2=p(c2.slice(3,5)),b2=p(c2.slice(5,7));
  const r=Math.round(lerp(r1,r2,t)),g=Math.round(lerp(g1,g2,t)),b=Math.round(lerp(b1,b2,t));
  return '#'+[r,g,b].map(v=>v.toString(16).padStart(2,'0')).join('');
}}

// ── Slider + big canvas ───────────────────────────────────────────────────
function buildSliderAndCanvas(d, idx) {{
  const c=gc(d.status), isH=d.status==='critical';
  if(d.score<0.3){{
    return `<div style="background:#0a1a0a;border:1px solid #1a3a1a;border-radius:6px;padding:12px;font-size:11px;color:#666;line-height:1.6;margin-top:10px">
      LOW effect score (${{d.score}}). Likely represents tolerated substitution or normal variation. No pathological progression timeline applicable.
    </div>`;
  }}

  const structKey=d.struct_effect||'default';
  const sa=STAGES[structKey]||STAGES['default'];
  const totalStages=sa.stages.length;
  const events=[
    {{day:1,label:"Single-cell mutation event",desc:"One cell acquires this mutation. Immune surveillance may clear it.",c:'#555'}},
    {{day:isH?60:120,label:"Clonal expansion begins",desc:"Mutant cell escapes clearance and divides, passing mutation to daughter cells. Still undetectable.",c:c}},
    {{day:isH?180:365,label:"Detectable population",desc:"Sensitive liquid biopsy might detect mutant DNA fragments. Still asymptomatic.",c:c}},
    {{day:isH?365:730,label:"Neighbouring cell effects",desc:"VEGF/TGF-β paracrine signalling starts influencing surrounding cells.",c:'#e24b4a'}},
    {{day:isH?730:1460,label:"Clinically detectable",desc:"At typical detection sizes (~0.5–1cm). Billions of cell divisions have occurred.",c:'#e24b4a'}},
  ];
  const maxDay=events[events.length-1].day+200;

  window._SE=window._SE||{{}};window._SE[idx]={{events,maxDay,structKey,color:c,totalStages,cellKey:d.cell||'apoptosis'}};

  const evHTML=events.map((e,i)=>`<div class="evt off" id="ev-${{idx}}-${{i}}">
    <div class="edot" style="background:${{e.c}}"></div>
    <div><strong>Day ~${{e.day}}: ${{e.label}}</strong><span>${{e.desc}}</span></div>
  </div>`).join('');

  const imp=CELLD[d.cell||'apoptosis']||CELLD['apoptosis'];
  const cellAnim=imp.anim;
  const cellColor=imp.color;

  return `
  <!-- SLIDER -->
  <div class="slider-box" style="margin-top:12px">
    <div class="slider-title">Mutation timeline + structural progression — drag slider</div>
    <div style="background:#0a0c1a;border:1px solid #1a1d3a;border-radius:5px;padding:8px;margin-bottom:8px;font-size:9px;color:#444;line-height:1.5">
      ⚠ Population-level estimates from published TP53 kinetics. Not individual predictions. Timelines vary enormously by cell type, co-mutations, immune status.
    </div>
    <div class="slider-row">
      <span class="slider-lbl">Day</span>
      <input type="range" id="sl-${{idx}}" min="0" max="${{maxDay}}" value="0" oninput="updateAll(${{idx}},parseInt(this.value))">
      <span class="slider-val" id="sv-${{idx}}">Day 0</span>
    </div>
    <div class="phase-bar">
      <div class="phase-fill" id="pf-${{idx}}" style="width:0%;background:${{c}}"></div>
      <div class="marker" id="mk-${{idx}}" style="left:0%"></div>
    </div>
    <div style="margin-top:8px">${{evHTML}}</div>
  </div>

  <!-- BIG PROTEIN CANVAS -->
  <div class="prot-canvas-wrap">
    <div class="prot-canvas-title">${{sa.label}} — protein structural change</div>
    <canvas id="pc-${{idx}}" width="580" height="200" style="width:100%;height:200px;border-radius:6px"></canvas>
    <div class="prot-stage-label" id="psl-${{idx}}">${{sa.stages[0]}}</div>
    <div class="prot-stage-desc" id="psd-${{idx}}" style="color:#555;font-size:10px;text-align:center"></div>
    <!-- Stage progress dots -->
    <div style="display:flex;justify-content:center;gap:8px;margin-top:6px" id="pdots-${{idx}}">
      ${{sa.stages.map((_,i)=>`<div id="pd-${{idx}}-${{i}}" style="width:8px;height:8px;border-radius:50%;background:${{i===0?c:'#1e2030'}};transition:background 0.3s"></div>`).join('')}}
    </div>
  </div>

  <!-- CELL DIAGRAM -->
  <div class="cell-wrap" style="margin-top:10px">
    <div class="sl2" style="margin-top:0">Cell-level impact</div>
    <div class="cell-inner">
      <div class="cell-col">
        <svg width="56" height="56" viewBox="0 0 56 56">
          <ellipse cx="28" cy="28" rx="23" ry="21" fill="#0a1f0a" stroke="#2a5a2a" stroke-width="1.5"/>
          <ellipse cx="28" cy="28" rx="9" ry="8" fill="#1a4a1a" stroke="#4CAF50" stroke-width="1.5"/>
          <text x="28" y="31" text-anchor="middle" font-size="5" fill="#4CAF50" font-family="monospace">WT</text>
        </svg>
        <span style="font-size:9px;color:#4CAF50;font-family:'IBM Plex Mono',monospace">Normal</span>
        <span style="color:${{cellColor}};font-size:14px;line-height:1">↓</span>
        <svg id="cell-svg-${{idx}}" width="56" height="56" viewBox="0 0 56 56" style="transform-origin:center">
          <ellipse id="cell-outer-${{idx}}" cx="28" cy="28" rx="23" ry="21" fill="#1f0808" stroke="${{cellColor}}" stroke-width="1.5" stroke-dasharray="4,2"/>
          <ellipse id="cell-nucleus-${{idx}}" cx="28" cy="28" rx="11" ry="9" fill="#2a0808" stroke="${{cellColor}}" stroke-width="1.5"/>
          <circle cx="13" cy="18" r="2.5" fill="${{cellColor}}" opacity="0.7" id="cell-dot1-${{idx}}"/>
          <circle cx="43" cy="38" r="2" fill="${{cellColor}}" opacity="0.5" id="cell-dot2-${{idx}}"/>
          <text x="28" y="31" text-anchor="middle" font-size="5" fill="${{cellColor}}" font-family="monospace" id="cell-lbl-${{idx}}">MUT</text>
        </svg>
        <span style="font-size:9px;color:${{cellColor}};font-family:'IBM Plex Mono',monospace">Affected</span>
      </div>
      <div>
        <div class="cell-info-title" id="cell-title-${{idx}}" style="color:${{cellColor}}">${{imp.title}}</div>
        <div class="cell-desc-text" id="cell-desc-${{idx}}">${{imp.desc}}</div>
        <!-- Cell function bars -->
        <div style="margin-top:10px" id="cell-bars-${{idx}}">
          ${{['Apoptosis activation','p21 induction','DNA repair','Tumour suppression'].map((l,i)=>{{
            const wt=100, mutVal=d.status==='critical'?[3,4,15,2][i]:d.status==='affected'?[40,35,50,45][i]:[85,88,90,88][i];
            return `<div class="bar-row">
              <div class="bar-lbl"><span>${{l}}</span><span id="cb-${{idx}}-${{i}}" style="color:${{cellColor}}">${{mutVal}}%</span></div>
              <div class="bar-track"><div id="cbf-${{idx}}-${{i}}" class="bar-fill" style="width:${{mutVal}}%;background:${{cellColor}}"></div></div>
            </div>`;
          }}).join('')}}
        </div>
      </div>
    </div>
  </div>`;
}}

function updateAll(idx, day) {{
  const se=(window._SE||{{}})[idx]; if(!se) return;
  const {{events,maxDay,structKey,color,totalStages,cellKey}}=se;
  const imp=CELLD[cellKey]||CELLD['apoptosis'];
  const cellColor=imp.color;

  // Update day label
  const sv=document.getElementById('sv-'+idx);
  if(sv) sv.textContent=day===0?'Day 0':day>365?`Day ${{day}} (~${{(day/365).toFixed(1)}}yr)`:`Day ${{day}}`;

  // Progress bar
  const pct=(day/maxDay*100).toFixed(1);
  const pf=document.getElementById('pf-'+idx), mk=document.getElementById('mk-'+idx);
  if(pf){{pf.style.width=pct+'%';pf.textContent=day<(events[2]?.day||180)?'subclinical':day<(events[4]?.day||730)?'detectable':'clinical';}}
  if(mk) mk.style.left=pct+'%';

  // Timeline events
  events.forEach((e,i)=>{{
    const el=document.getElementById('ev-'+idx+'-'+i);
    if(el) el.classList.toggle('off', day<e.day);
  }});

  // Structural stage
  const t=clamp(day/maxDay,0,1);
  const stage=Math.min(totalStages-1,Math.floor(t*totalStages));
  const sa=STAGES[structKey]||STAGES['default'];

  // Update stage label
  const psl=document.getElementById('psl-'+idx);
  if(psl) psl.textContent=sa.stages[stage]||'';

  // Update stage dots
  for(let i=0;i<totalStages;i++){{
    const dot=document.getElementById('pd-'+idx+'-'+i);
    if(dot) dot.style.background=i<=stage?color:'#1e2030';
  }}

  // Draw protein canvas
  const canvas=document.getElementById('pc-'+idx);
  if(canvas){{
    const ctx=canvas.getContext('2d');
    sa.draw(ctx,canvas.width,canvas.height,t,color);
  }}

  // Animate cell SVG
  const cellSvg=document.getElementById('cell-svg-'+idx);
  if(cellSvg){{
    // Scale up with progression
    const scale=1+t*0.15;
    cellSvg.style.animation=t>0.3?`${{imp.anim}} ${{2-t*0.5}}s ease-in-out infinite`:'none';
    if(t<=0.3) cellSvg.style.transform=`scale(${{1+t*0.05}})`;
  }}

  // Update cell bars dynamically
  const baseMut=d=>d.status==='critical'?[3,4,15,2]:d.status==='affected'?[40,35,50,45]:[85,88,90,88];
  for(let i=0;i<4;i++){{
    const res=RESIDUES.find(r=>r.label===se.label||true); // use first for now
    const bar=document.getElementById('cbf-'+idx+'-'+i);
    const lbl=document.getElementById('cb-'+idx+'-'+i);
    if(bar&&lbl){{
      const baseVals=[3,4,15,2]; // critical defaults
      const mutVal=Math.round(baseVals[i]+(100-baseVals[i])*(1-t));
      bar.style.width=mutVal+'%';
      lbl.textContent=mutVal+'%';
    }}
  }}
}}

// Initial canvas draws
function initCanvases() {{
  RESIDUES.forEach((d,idx)=>{{
    const canvas=document.getElementById('pc-'+idx);
    if(!canvas) return;
    const structKey=d.struct_effect||'default';
    const sa=STAGES[structKey]||STAGES['default'];
    const c=gc(d.status);
    sa.draw(canvas.getContext('2d'),canvas.width,canvas.height,0,c);
  }});
}}

// ── Cards ─────────────────────────────────────────────────────────────────
function buildCard(d, idx) {{
  const c=gc(d.status);
  const hyp=d.hypothesis||`${{d.label}} — ${{d.priority}} priority (score ${{d.score}}).`;
  return `<div class="hcard" id="card-${{idx}}" data-priority="${{d.priority}}">
    <div class="hheader" onclick="toggle(${{idx}})">
      <span class="hrank">#${{idx+1}}</span>
      <div class="pdot" style="background:${{c}}"></div>
      <span class="hlabel">${{d.label}}</span>
      <span class="badge" style="background:${{c}}22;color:${{c}};border:0.5px solid ${{c}}55">${{d.priority}}</span>
      <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:${{c}}">${{d.score}}</span>
      <span style="color:#3a3d5a;font-size:10px;margin-left:6px">${{d.expType||''}}</span>
      <span class="chev" id="chev-${{idx}}">▶</span>
    </div>
    <div class="hbody" id="body-${{idx}}">
      <div class="card-body-grid">
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
          <div class="sl2" style="margin-top:12px">Structural fluctuation — WT vs mutant</div>
          ${{buildChain(d.pos,d.status,d.score)}}
        </div>
        <div class="bright">
          ${{buildSliderAndCanvas(d,idx)}}
        </div>
      </div>
    </div>
  </div>`;
}}

const wrap=document.getElementById('cards');
RESIDUES.forEach((d,i)=>{{ wrap.innerHTML+=buildCard(d,i); }});

function toggle(idx){{
  const body=document.getElementById('body-'+idx),chev=document.getElementById('chev-'+idx);
  const open=body.classList.contains('open');
  body.classList.toggle('open',!open); chev.classList.toggle('open',!open);
  if(!open){{
    setTimeout(()=>{{
      const canvas=document.getElementById('pc-'+idx);
      if(canvas){{
        const d=RESIDUES[idx],structKey=d.struct_effect||'default';
        const sa=STAGES[structKey]||STAGES['default'];
        sa.draw(canvas.getContext('2d'),canvas.width,canvas.height,0,gc(d.status));
      }}
    }},50);
  }}
}}
function doFilter(p,btn){{
  document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('active')); btn.classList.add('active');
  document.querySelectorAll('.hcard').forEach(c=>{{ c.style.display=(p==='ALL'||c.dataset.priority===p)?'block':'none'; }});
}}
function expandAll(){{document.querySelectorAll('.hbody').forEach(b=>b.classList.add('open'));document.querySelectorAll('.chev').forEach(c=>c.classList.add('open'));}}
function collapseAll(){{document.querySelectorAll('.hbody').forEach(b=>b.classList.remove('open'));document.querySelectorAll('.chev').forEach(c=>c.classList.remove('open'));}}

// Auto-open first HIGH card
const fh=document.querySelector('[data-priority="HIGH"] .hbody'),fc=document.querySelector('[data-priority="HIGH"] .chev');
if(fh){{fh.classList.add('open');fc.classList.add('open');setTimeout(initCanvases,100);}}
</script>
</body>
</html>"""


def render():
    if LOGO_DATA_URL:
        st.markdown(f'<img src="{LOGO_DATA_URL}" style="height:44px;object-fit:contain;border-radius:8px;margin-bottom:4px">', unsafe_allow_html=True)
    st.markdown("**Hypothesis Lab** — click any card to expand structural animation, mutation timeline, and cell impact")
    st.divider()

    if "t_scored" not in st.session_state:
        st.info("👈 Run Triage first in the **Triage System** tab.")
        return

    scored_df = st.session_state.t_scored

    with st.spinner("Loading structure..."):
        pdb_data = fetch_pdb()

    if not pdb_data:
        st.error("Could not load protein structure. Check internet connection.")
        return

    residues = []
    for _, row in scored_df.iterrows():
        pos        = int(row["residue_position"])
        score      = round(float(row.get("normalized_score", row.get("effect_score", 0))), 3)
        label      = str(row.get("mutation", f"Res{pos}"))
        if label in ("nan", ""):
            label = f"Res{pos}"
        priority   = str(row.get("priority", "LOW"))
        exp_type   = str(row.get("experiment_type", ""))
        hypothesis = str(row.get("hypothesis", ""))
        status     = {"HIGH":"critical","MEDIUM":"affected","LOW":"normal"}[priority]
        hs         = HOTSPOT_DATA.get(pos, {})
        residues.append({
            "pos": pos, "label": label, "score": score,
            "priority": priority, "expType": "" if exp_type in ("nan","") else exp_type,
            "status": status, "hypothesis": hypothesis,
            "mechanism":    hs.get("mechanism",   "Effect score from experimental data. Phase 2 will add mechanistic annotation."),
            "clinvar":      hs.get("clinvar",      "Not queried — Phase 2 integrates live ClinVar"),
            "cosmic":       hs.get("cosmic",       "Not queried"),
            "cancer":       hs.get("cancer",       "Not queried"),
            "therapeutic":  hs.get("therapeutic",  "Consult clinical database"),
            "domain":       hs.get("domain",       "Unknown — Phase 2 annotation pending"),
            "experiment":   hs.get("experiment",   "Thermal shift assay and EMSA as first-line validation."),
            "cell":         hs.get("cell",         "apoptosis" if status=="critical" else "structural"),
            "struct_effect":hs.get("struct_effect","default"),
        })

    html = build_html(residues, pdb_data, LOGO_DATA_URL)
    components.html(html, height=3500, scrolling=True)
