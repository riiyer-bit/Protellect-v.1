"""
hypothesis_lab.py — Protellect Hypothesis Lab (Tab 4)
Expandable hypothesis cards with:
- WT vs mutant chain animation
- Sliding mutation rate bar
- Cell impact diagram
- Experiment recommendations
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import requests

HOTSPOT_DATA = {
    175: {"mechanism":"Disrupts zinc coordination at C176/H179/C238/C242. Causes global misfolding of the DNA-binding domain — the most common TP53 hotspot.","clinvar":"Pathogenic · 847 submissions","cosmic":"~6% of all cancers","cancer":"Breast, lung, colorectal, ovarian","therapeutic":"APR-246 (eprenetapopt) — Phase III clinical trials","cell":"apoptosis","domain":"DNA-binding domain (L2 loop) — zinc coordination site","experiment":"Thermal shift assay (confirm Tm reduction ~8–10°C), then EMSA to confirm loss of DNA binding, then reporter assay for p21/MDM2 activation."},
    248: {"mechanism":"Direct DNA contact residue in L3 loop. Makes hydrogen bonds to minor groove at CATG sequences. Abolishes sequence-specific DNA binding.","clinvar":"Pathogenic · 623 submissions","cosmic":"~3% of all cancers","cancer":"Colorectal, lung, pancreatic","therapeutic":"Synthetic lethality under investigation","cell":"checkpoint","domain":"DNA-binding domain (L3 loop) — direct DNA contact","experiment":"EMSA to confirm loss of DNA binding. Luciferase reporter assay for transcriptional activity."},
    273: {"mechanism":"DNA backbone phosphate contact. Loss reduces DNA-binding affinity >100-fold. R273C retains partial structure unlike R273H.","clinvar":"Pathogenic · 512 submissions","cosmic":"~3% of all cancers","cancer":"Colorectal, lung, brain","therapeutic":"Small molecule stabilizers experimental","cell":"checkpoint","domain":"DNA-binding domain (S10 strand) — DNA backbone contact","experiment":"EMSA. Note: test R273C and R273H separately if both present — different severity."},
    249: {"mechanism":"H2 helix structural mutation. Characteristic aflatoxin B1 mutational signature. Disrupts HIPK2 interaction.","clinvar":"Pathogenic · 298 submissions","cosmic":"~1.5% — enriched in liver cancer","cancer":"Liver (HCC), lung, esophageal","therapeutic":"No specific therapy — aflatoxin avoidance in endemic regions","cell":"proliferation","domain":"DNA-binding domain (H2 helix)","experiment":"Reporter assay for transactivation. Co-IP to assess dominant negative tetramer formation."},
    245: {"mechanism":"Glycine essential for L3 loop geometry. Any side chain sterically clashes with the DNA backbone.","clinvar":"Pathogenic · 187 submissions","cosmic":"~1.5% of cancers","cancer":"Breast, lung, sarcoma","therapeutic":"Structural correctors under investigation","cell":"apoptosis","domain":"DNA-binding domain (L3 loop)","experiment":"Thermal shift + EMSA. Test APR-246 rescue if structural mutant is confirmed."},
    282: {"mechanism":"R282 salt bridge with E271 stabilises H2 helix. Tryptophan disrupts this, causing partial helix unfolding.","clinvar":"Pathogenic · 156 submissions","cosmic":"~1% of cancers","cancer":"Breast, colorectal, lung","therapeutic":"No approved targeted therapy","cell":"apoptosis","domain":"DNA-binding domain (H2 helix)","experiment":"Thermal shift assay. Luciferase reporter for p21/MDM2 activation."},
    220: {"mechanism":"Creates a surface hydrophobic cavity that destabilises the domain thermodynamically. Not a direct DNA contact — the cavity is a druggable pocket.","clinvar":"Pathogenic · 89 submissions","cosmic":"~1% of cancers","cancer":"Breast, lung, ovarian","therapeutic":"PC14586 (rezatapopt) specifically fills the Y220C cavity — Phase II trials.","cell":"apoptosis","domain":"DNA-binding domain (S7-S8 loop)","experiment":"Thermal shift. Both APR-246 and PC14586 rescue experiments — Y220C is prime candidate for cavity-filling compounds."},
}

CELL_DATA = {
    "apoptosis":    {"title":"Loss of apoptosis signalling","color":"#FF4C4C","anim":"cpulse","desc":"TP53 normally activates BAX, PUMA, and NOXA to trigger programmed cell death when DNA damage is detected. This mutation abolishes that signal — damaged cells survive and accumulate further mutations."},
    "checkpoint":   {"title":"DNA damage checkpoint bypass","color":"#FFA500","anim":"cspin", "desc":"TP53 normally halts the cell cycle at G1/S via p21, giving time for DNA repair. This contact mutation prevents p21 activation — cells divide with unrepaired DNA every cycle, accumulating genomic instability."},
    "proliferation":{"title":"Gain-of-function proliferation","color":"#CC44CC","anim":"cgrow","desc":"This gain-of-function mutation inhibits p63 and p73, and activates MYC/VEGF programmes — actively driving oncogenic proliferation rather than merely losing tumour suppression."},
    "structural":   {"title":"Structural propagation effect","color":"#FFA500","anim":"cshake","desc":"This residue is not directly mutated but its function is compromised by structural changes propagating from nearby critical mutations."},
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
    res_json  = json.dumps(residues_data)
    cell_json = json.dumps(CELL_DATA)
    pdb_esc   = pdb_data.replace("\\","\\\\").replace("`","\\`").replace("${","\\${")[:280000]

    n_high = sum(1 for r in residues_data if r["priority"]=="HIGH")
    n_med  = sum(1 for r in residues_data if r["priority"]=="MEDIUM")
    n_low  = sum(1 for r in residues_data if r["priority"]=="LOW")
    top    = residues_data[0] if residues_data else {}

    return f"""<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#080b14;font-family:'IBM Plex Sans',sans-serif;color:#ccc;font-size:13px;padding:14px;line-height:1.5}}
::-webkit-scrollbar{{width:5px}}::-webkit-scrollbar-track{{background:#0a0c14}}::-webkit-scrollbar-thumb{{background:#2a2d3a;border-radius:3px}}

.page-title{{font-family:'IBM Plex Mono',monospace;font-size:18px;font-weight:700;color:#eee;margin-bottom:4px}}
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
.fbtn-right{{margin-left:auto}}

/* Cards */
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

/* Animation section */
.anim-box{{background:#080b14;border:1px solid #1e2030;border-radius:8px;padding:12px;margin-bottom:12px}}
.clabel{{font-size:10px;font-family:'IBM Plex Mono',monospace;color:#555;margin-bottom:5px}}
.csvg{{width:100%;height:46px;border:1px solid #1e2030;border-radius:5px;background:#040608;display:block}}
.brow{{margin-bottom:7px}}
.blbl{{display:flex;justify-content:space-between;font-size:10px;color:#555;margin-bottom:2px;font-family:'IBM Plex Mono',monospace}}
.btrack{{background:#1a1d2e;border-radius:3px;height:6px;overflow:hidden;position:relative}}
.bfill{{height:100%;border-radius:3px;transition:width 0.3s ease;position:absolute;top:0;left:0}}
.bwt{{height:100%;background:#4CAF5022;width:100%;border-radius:3px}}

/* Slider section */
.slider-section{{margin-top:12px;padding-top:12px;border-top:1px solid #1a1d2e}}
.slider-title{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:10px}}
.slider-row{{display:flex;align-items:center;gap:10px;margin-bottom:8px}}
.slider-lbl{{font-size:11px;font-family:'IBM Plex Mono',monospace;color:#555;min-width:100px}}
input[type=range]{{flex:1;accent-color:#FF4C4C;cursor:pointer;height:4px}}
.slider-val{{font-size:12px;font-family:'IBM Plex Mono',monospace;min-width:50px;text-align:right}}
.phase-display{{background:#080b14;border:1px solid #1e2030;border-radius:8px;padding:12px;margin-top:8px}}
.phase-bar{{height:16px;background:#1a1d2e;border-radius:8px;position:relative;overflow:hidden;margin:8px 0}}
.phase-fill{{height:100%;border-radius:8px;transition:width 0.3s ease;display:flex;align-items:center;padding-left:8px;font-size:9px;font-family:'IBM Plex Mono',monospace;color:white;white-space:nowrap;overflow:hidden}}
.marker{{position:absolute;top:0;height:100%;width:2px;background:white;transition:left 0.3s ease;z-index:5}}
.phase-events{{margin-top:10px}}
.pevt{{display:flex;align-items:flex-start;gap:8px;margin-bottom:6px;transition:opacity 0.3s}}
.pevt.inactive{{opacity:0.2}}
.pdotev{{width:8px;height:8px;border-radius:50%;flex-shrink:0;margin-top:3px}}
.pevt strong{{display:block;font-size:11px;color:#eee;margin-bottom:2px}}
.pevt span{{font-size:10px;color:#666;line-height:1.5}}

/* Cell diagram */
.cell-section{{margin-top:12px;padding-top:12px;border-top:1px solid #1a1d2e}}
.cell-layout{{display:flex;gap:14px;align-items:flex-start}}
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

<div class="page-title">💡 Hypothesis Lab</div>
<div class="page-sub">All ranked hypotheses from your triage run. Click any card to expand the full analysis, animation, mutation timeline, and cell impact.</div>

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
  <button class="fbtn fbtn-right" onclick="expandAll()">Expand all</button>
  <button class="fbtn" onclick="collapseAll()">Collapse all</button>
</div>

<div id="cards"></div>

<script>
const RESIDUES = {res_json};
const CELLD = {cell_json};
const pdbData = `{pdb_esc}`;

function gc(s){{ return s==='critical'?'#FF4C4C':s==='affected'?'#FFA500':'#4CA8FF'; }}

function buildChain(pos, status, score) {{
  const c = gc(status);
  const isH = status==='critical', isM = status==='affected';
  const W=380, total=16, mutI=7, sp=W/(total+1);
  let wt='', mut='';
  for(let i=0;i<total;i++){{
    const x=(i+1)*sp, isMut=i===mutI, r=isMut?10:5;
    wt+=`<circle cx="${{x}}" cy="23" r="5" fill="#0a1f0a" stroke="#4CAF50" stroke-width="1"/>`;
    if(i<total-1) wt+=`<line x1="${{x+5}}" y1="23" x2="${{(i+2)*sp-5}}" y2="23" stroke="#1a3a1a" stroke-width="1.2"/>`;
    const anim = isMut?`style="transform-origin:${{x}}px 23px;animation:wobble-${{status}} 1.4s ease-in-out infinite"` :'';
    mut+=`<circle cx="${{x}}" cy="23" r="${{r}}" fill="${{isMut?c+'22':'#040608'}}" stroke="${{isMut?c:'#1e2030'}}" stroke-width="${{isMut?2.5:0.8}}" ${{anim}}/>`;
    if(i<total-1) mut+=`<line x1="${{x+(isMut?r:5)}}" y1="23" x2="${{(i+2)*sp-5}}" y2="23" stroke="${{isMut?c:'#1a1d2e'}}" stroke-width="1.2"/>`;
  }}
  const pcts = isH?[8,3,28,2]:isM?[50,45,72,55]:[88,90,92,88];
  const lbls = ['Zinc coordination','DNA binding','Thermal stability','Transcription'];
  const bars = lbls.map((l,i)=>`<div class="brow">
    <div class="blbl"><span>${{l}}</span><span style="color:${{c}}">${{pcts[i]}}% of WT</span></div>
    <div class="btrack">
      <div class="bwt"></div>
      <div class="bfill" style="width:${{pcts[i]}}%;background:${{c}}"></div>
    </div></div>`).join('');
  return `<div class="anim-box">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      <div>
        <div class="clabel" style="color:#4CAF50">Wild-type protein chain</div>
        <svg class="csvg" viewBox="0 0 ${{W}} 46">${{wt}}</svg>
        <div class="clabel" style="color:${{c}};margin-top:8px">Mutant chain — position ${{pos}} (animated sphere = instability)</div>
        <svg class="csvg" viewBox="0 0 ${{W}} 46">${{mut}}</svg>
        <div style="font-size:10px;color:#3a3d5a;margin-top:6px;line-height:1.5">${{isH?'Critical mutation — near-complete functional collapse.':isM?'Medium impact — partial functional reduction.':'Low impact — likely tolerated substitution.'}}</div>
      </div>
      <div>
        <div class="clabel">Functional parameters vs wild-type</div>
        ${{bars}}
      </div>
    </div>
  </div>`;
}}

function buildSlider(d, idx) {{
  const c = gc(d.status);
  const isH = d.status==='critical';
  const isBen = d.score < 0.3;

  if(isBen) {{
    return `<div class="slider-section">
      <div class="slider-title">Mutation Timeline</div>
      <div style="background:#0a1a0a;border:1px solid #1a3a1a;border-radius:6px;padding:12px;font-size:11px;color:#888;line-height:1.7">
        This residue has a LOW effect score (${{d.score}}). Low-scoring variants may represent tolerated substitutions, normal population variation, or positions that are not critical for the assayed function.
        A pathological timeline is not applicable — further characterisation needed before clinical interpretation.
      </div>
    </div>`;
  }}

  const events = [
    {{day:1, label:"Single-cell mutation event", desc:"One cell acquires this mutation. Immune surveillance may clear it — single mutations occur constantly and are usually eliminated.", c:'#555'}},
    {{day:Math.round(isH?60:120), label:"Clonal expansion begins", desc:"If the mutant cell escapes clearance, it divides. The mutation passes to daughter cells. Still completely undetectable by any clinical test.", c:c}},
    {{day:Math.round(isH?180:365), label:"Microscopically detectable population", desc:"Sensitive liquid biopsy sequencing might detect mutant fragments in blood. Still asymptomatic. Extremely variable in real patients.", c:c}},
    {{day:Math.round(isH?365:730), label:"Neighbouring cell microenvironment effects", desc:"Tumour microenvironment signalling begins — VEGF, TGF-β influence surrounding cells. This is paracrine signalling, not direct mutation spread.", c:'#e24b4a'}},
    {{day:Math.round(isH?730:1460), label:"Clinically detectable — detection window", desc:"At typical detection sizes (~0.5–1cm), billions of cell divisions have occurred. This illustrates why early detection matters enormously.", c:'#e24b4a'}},
  ];
  const maxDay = events[events.length-1].day + 200;

  window._sliderEvents = window._sliderEvents || {{}};
  window._sliderEvents[idx] = events;
  window._sliderMax = window._sliderMax || {{}};
  window._sliderMax[idx] = maxDay;

  const evHTML = events.map((e,i)=>`
    <div class="pevt inactive" id="ev-${{idx}}-${{i}}">
      <div class="pdotev" style="background:${{e.c}}"></div>
      <div><strong>Day ~${{e.day}}: ${{e.label}}</strong><span>${{e.desc}}</span></div>
    </div>`).join('');

  return `<div class="slider-section">
    <div class="slider-title">Mutation timeline — drag slider to explore (population-level estimates, not individual predictions)</div>
    <div style="background:#0a0c1a;border:1px solid #1a1d3a;border-radius:6px;padding:10px;margin-bottom:10px;font-size:10px;color:#555;line-height:1.6">
      ⚠ These timelines are rough population-level estimates from published TP53 tumour kinetics literature. Actual timelines vary enormously by cell type, co-occurring mutations, immune function, and environment. Not clinical guidance.
    </div>
    <div class="slider-row">
      <span class="slider-lbl">Day (drag)</span>
      <input type="range" id="sl-${{idx}}" min="0" max="${{maxDay}}" value="0" oninput="updateSlider(${{idx}}, parseInt(this.value))">
      <span class="slider-val" id="sv-${{idx}}">Day 0</span>
    </div>
    <div class="phase-display">
      <div style="font-size:10px;color:#3a3d5a;font-family:'IBM Plex Mono',monospace;margin-bottom:6px">Timeline progression</div>
      <div class="phase-bar">
        <div class="phase-fill" id="pf-${{idx}}" style="width:0%;background:${{c}}">subclinical</div>
        <div class="marker" id="mk-${{idx}}" style="left:0%"></div>
      </div>
      <div class="phase-events">${{evHTML}}</div>
    </div>
  </div>`;
}}

function updateSlider(idx, day) {{
  day = parseInt(day);
  const events = (window._sliderEvents||{{}})[idx] || [];
  const maxDay = (window._sliderMax||{{}})[idx] || 2000;
  const sv = document.getElementById('sv-'+idx);
  if(sv) sv.textContent = day===0 ? 'Day 0 — pre-mutation' : day>365 ? `Day ${{day}} (~${{(day/365).toFixed(1)}} yr)` : `Day ${{day}}`;
  const pct = (day/maxDay*100).toFixed(1);
  const pf = document.getElementById('pf-'+idx);
  const mk = document.getElementById('mk-'+idx);
  if(pf) {{ pf.style.width=pct+'%'; pf.textContent=day<(events[2]&&events[2].day||180)?'subclinical':day<(events[4]&&events[4].day||730)?'detectable':'clinical'; }}
  if(mk) mk.style.left=pct+'%';
  events.forEach((e,i)=>{{
    const el=document.getElementById('ev-'+idx+'-'+i);
    if(el) el.classList.toggle('inactive', day<e.day);
  }});
}}

function buildCell(d) {{
  const imp = CELLD[d.cell] || CELLD['structural'];
  const c = imp.color;
  const anim = imp.anim;
  return `<div class="cell-section">
    <div class="sl2" style="margin-top:0">Cell-level impact</div>
    <div class="cell-layout">
      <div class="cell-anim-col">
        <svg width="56" height="56" viewBox="0 0 56 56">
          <ellipse cx="28" cy="28" rx="24" ry="22" fill="#0a1f0a" stroke="#2a5a2a" stroke-width="1.5"/>
          <ellipse cx="28" cy="28" rx="9" ry="8" fill="#1a4a1a" stroke="#4CAF50" stroke-width="1.5"/>
          <text x="28" y="31" text-anchor="middle" font-size="5" fill="#4CAF50" font-family="monospace">WT</text>
        </svg>
        <span style="font-size:9px;color:#4CAF50;font-family:'IBM Plex Mono',monospace">Normal</span>
        <span style="color:${{c}};font-size:14px;line-height:1">↓</span>
        <svg width="56" height="56" viewBox="0 0 56 56" style="animation:${{anim}} 2s ease-in-out infinite;transform-origin:center">
          <ellipse cx="28" cy="28" rx="24" ry="22" fill="#1f0808" stroke="${{c}}" stroke-width="1.5" stroke-dasharray="4,2"/>
          <ellipse cx="28" cy="28" rx="11" ry="9" fill="#2a0808" stroke="${{c}}" stroke-width="1.5"/>
          <circle cx="13" cy="18" r="2.5" fill="${{c}}" opacity="0.7"/>
          <circle cx="43" cy="38" r="2" fill="${{c}}" opacity="0.5"/>
          <text x="28" y="31" text-anchor="middle" font-size="5" fill="${{c}}" font-family="monospace">MUT</text>
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

function buildCard(d, idx) {{
  const c = gc(d.status);
  const hyp = d.hypothesis || `Residue ${{d.pos}} (${{d.label}}) shows ${{d.priority.toLowerCase()}} priority functional effect (score ${{d.score}}). ${{d.status==='critical'?'Strong candidate for immediate experimental validation.':d.status==='affected'?'Moderate effect — investigate in context of nearby high-priority hits.':'Low effect — likely tolerated. Validate before fully deprioritising.'}}`;

  return `<div class="hcard" id="card-${{idx}}" data-priority="${{d.priority}}">
    <div class="hheader" onclick="toggle(${{idx}})">
      <span class="hrank">#${{idx+1}}</span>
      <div class="pdot" style="background:${{c}}"></div>
      <span class="hlabel">${{d.label}}</span>
      <span class="badge" style="background:${{c}}22;color:${{c}};border:0.5px solid ${{c}}55">${{d.priority}}</span>
      <span class="hscore" style="color:${{c}}">${{d.score}}</span>
      <span style="color:#3a3d5a;font-size:11px;margin-left:6px">${{d.expType}}</span>
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
            <div class="al">Recommended next experiment</div>
            <div class="at">${{d.experiment}}</div>
          </div>
          ${{buildSlider(d, idx)}}
        </div>
        <div class="bright">
          <div class="sl2" style="margin-top:0">Structural fluctuation — WT vs mutant</div>
          ${{buildChain(d.pos, d.status, d.score)}}
          ${{buildCell(d)}}
        </div>
      </div>
    </div>
  </div>`;
}}

// Render cards
const wrap = document.getElementById('cards');
RESIDUES.forEach((d,i) => {{ wrap.innerHTML += buildCard(d,i); }});

function toggle(idx) {{
  const body = document.getElementById('body-'+idx);
  const chev = document.getElementById('chev-'+idx);
  const open = body.classList.contains('open');
  body.classList.toggle('open',!open);
  chev.classList.toggle('open',!open);
}}

function filter(priority, btn) {{
  document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.hcard').forEach(c=>{{
    c.style.display = (priority==='ALL'||c.dataset.priority===priority)?'block':'none';
  }});
}}

function expandAll(){{
  document.querySelectorAll('.hbody').forEach(b=>b.classList.add('open'));
  document.querySelectorAll('.chev').forEach(c=>c.classList.add('open'));
}}

function collapseAll(){{
  document.querySelectorAll('.hbody').forEach(b=>b.classList.remove('open'));
  document.querySelectorAll('.chev').forEach(c=>c.classList.remove('open'));
}}

// Auto-open first HIGH card
const firstHigh = document.querySelector('[data-priority="HIGH"] .hbody');
const firstHighChev = document.querySelector('[data-priority="HIGH"] .chev');
if(firstHigh){{ firstHigh.classList.add('open'); firstHighChev.classList.add('open'); }}

// Init all sliders to active events at day 0
document.querySelectorAll('.pevt').forEach(e=>e.classList.add('inactive'));
</script>
</body>
</html>"""


def render():
    st.markdown("## 💡 Hypothesis Lab")
    st.markdown("Click any hypothesis card to expand the full analysis, structural animation, timeline slider, and cell impact.")
    st.divider()

    if "t_scored" not in st.session_state:
        st.info("👈 Run Triage first in the **Triage System** tab — all hypotheses will appear here automatically.")
        return

    scored_df = st.session_state.t_scored

    with st.spinner("Loading structure and building hypothesis lab..."):
        pdb_data = fetch_pdb()

    if not pdb_data:
        st.error("Could not load protein structure. Check your internet connection.")
        return

    # Build residue list
    residues = []
    for _, row in scored_df.iterrows():
        pos = int(row["residue_position"])
        score = round(float(row.get("normalized_score", row.get("effect_score", 0))), 3)
        label = str(row.get("mutation", f"Res{pos}"))
        priority = str(row.get("priority", "LOW"))
        exp_type = str(row.get("experiment_type", "DMS"))
        hypothesis = str(row.get("hypothesis", ""))
        status = {"HIGH": "critical", "MEDIUM": "affected", "LOW": "normal"}[priority]
        hs = HOTSPOT_DATA.get(pos, {})
        residues.append({
            "pos": pos, "label": label, "score": score,
            "priority": priority, "expType": exp_type,
            "status": status, "hypothesis": hypothesis,
            "mechanism":   hs.get("mechanism",   "Effect score from experimental data. Phase 2 database integration will add mechanistic annotation."),
            "clinvar":     hs.get("clinvar",     "Not queried — Phase 2 integrates live ClinVar"),
            "cosmic":      hs.get("cosmic",      "Not queried"),
            "cancer":      hs.get("cancer",      "Not queried"),
            "therapeutic": hs.get("therapeutic", "Consult clinical database"),
            "domain":      hs.get("domain",      "Unknown — Phase 2 annotation pending"),
            "experiment":  hs.get("experiment",  "Run thermal shift assay and EMSA as first-line validation."),
            "cell":        hs.get("cell",        "apoptosis" if status == "critical" else "structural"),
        })

    html = build_lab_html(residues, pdb_data)
    components.html(html, height=3000, scrolling=True)
