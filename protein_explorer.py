"""
hypothesis_lab.py — Protellect Hypothesis Lab (Tab 4)
Professional layout. Real logo. Canvas-based protein animation driven by slider.
Cell diagram updates in sync.
"""

import streamlit as st
import streamlit.components.v1 as components
import json, base64, requests
from pathlib import Path

_lp = Path("/mnt/user-data/uploads/1777622887238_image.png")
LOGO_B64 = ("data:image/png;base64," + base64.b64encode(_lp.read_bytes()).decode()) if _lp.exists() else None

HOTSPOT_DATA = {
    175: {"mechanism":"Disrupts zinc coordination at C176/H179/C238/C242 tetrahedral site. L2 loop unfolds — entire DNA-binding domain loses compact conformation.","clinvar":"Pathogenic · 847 submissions","cosmic":"~6% of all cancers","cancer":"Breast, lung, colorectal, ovarian, bladder","therapeutic":"APR-246 (eprenetapopt) — Phase III","cell":"apoptosis","domain":"DNA-binding domain (L2 loop) — zinc coordination site","experiment":"Thermal shift assay (Tm −8–10°C) → EMSA → luciferase reporter (p21/MDM2).","struct_effect":"zinc_collapse"},
    248: {"mechanism":"Direct DNA contact residue in L3 loop. Makes H-bonds to minor groove at CATG sequences. Substitution abolishes sequence-specific DNA binding.","clinvar":"Pathogenic · 623 submissions","cosmic":"~3% of all cancers","cancer":"Colorectal, lung, pancreatic, ovarian","therapeutic":"Synthetic lethality under investigation","cell":"checkpoint","domain":"DNA-binding domain (L3 loop) — direct DNA contact","experiment":"EMSA to confirm loss of DNA binding. Luciferase reporter assay.","struct_effect":"dna_contact_loss"},
    273: {"mechanism":"DNA backbone phosphate contact. Loss reduces DNA-binding affinity >100-fold. R273C retains partial structure unlike R273H.","clinvar":"Pathogenic · 512 submissions","cosmic":"~3% of all cancers","cancer":"Colorectal, lung, brain, pancreatic","therapeutic":"Small molecule stabilizers experimental","cell":"checkpoint","domain":"DNA-binding domain (S10 strand) — backbone contact","experiment":"EMSA. Test R273C and R273H separately — different severity.","struct_effect":"dna_contact_loss"},
    249: {"mechanism":"H2 helix structural mutation. Characteristic aflatoxin B1 mutational signature. Disrupts HIPK2 interaction.","clinvar":"Pathogenic · 298 submissions","cosmic":"~1.5% — enriched in liver cancer","cancer":"Liver (HCC), lung, esophageal","therapeutic":"No specific therapy","cell":"proliferation","domain":"DNA-binding domain (H2 helix)","experiment":"Reporter assay. Co-IP for dominant negative tetramer.","struct_effect":"helix_break"},
    245: {"mechanism":"Glycine essential for L3 loop geometry. Any side chain sterically clashes with DNA backbone — loop cannot approach DNA.","clinvar":"Pathogenic · 187 submissions","cosmic":"~1.5% of cancers","cancer":"Breast, lung, sarcoma, hematologic","therapeutic":"Structural correctors under investigation","cell":"apoptosis","domain":"DNA-binding domain (L3 loop)","experiment":"Thermal shift + EMSA. APR-246 rescue if structural mutant confirmed.","struct_effect":"loop_distortion"},
    282: {"mechanism":"R282 salt bridge with E271 stabilises H2 helix. Tryptophan disrupts this causing partial helix unfolding.","clinvar":"Pathogenic · 156 submissions","cosmic":"~1% of cancers","cancer":"Breast, colorectal, lung","therapeutic":"No approved targeted therapy","cell":"apoptosis","domain":"DNA-binding domain (H2 helix)","experiment":"Thermal shift assay. Luciferase reporter for p21/MDM2.","struct_effect":"helix_break"},
    220: {"mechanism":"Creates a surface hydrophobic cavity that destabilises domain thermodynamically. Not a direct DNA contact — the cavity is a druggable pocket.","clinvar":"Pathogenic · 89 submissions","cosmic":"~1% of cancers","cancer":"Breast, lung, ovarian","therapeutic":"PC14586 (rezatapopt) — fills Y220C cavity, Phase II","cell":"apoptosis","domain":"DNA-binding domain (S7-S8 loop)","experiment":"Thermal shift. APR-246 and PC14586 rescue — prime cavity-filling candidate.","struct_effect":"surface_cavity"},
}

CELL_DATA = {
    "apoptosis":     {"title":"Loss of apoptosis signalling","color":"#FF4C4C","anim":"cpulse","desc":"TP53 normally activates BAX, PUMA, and NOXA to trigger programmed cell death. This mutation abolishes that signal — damaged cells survive and accumulate further mutations."},
    "checkpoint":    {"title":"DNA damage checkpoint bypass","color":"#FFA500","anim":"cspin", "desc":"TP53 normally halts the cell cycle at G1/S via p21. This contact mutation prevents p21 activation — cells divide with unrepaired DNA every cycle."},
    "proliferation": {"title":"Gain-of-function proliferation","color":"#CC44CC","anim":"cgrow","desc":"This gain-of-function mutation inhibits p63/p73 and activates MYC/VEGF programmes — actively driving oncogenic proliferation."},
    "structural":    {"title":"Structural propagation effect","color":"#FFA500","anim":"cshake","desc":"This residue is not directly mutated but its function is compromised by structural changes propagating from nearby critical mutations."},
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
    pdb_esc   = pdb_data.replace("\\","\\\\").replace("`","\\`").replace("${","\\${")[:270000]

    n_high = sum(1 for r in residues_data if r["priority"] == "HIGH")
    n_med  = sum(1 for r in residues_data if r["priority"] == "MEDIUM")
    n_low  = sum(1 for r in residues_data if r["priority"] == "LOW")
    top    = residues_data[0] if residues_data else {}

    logo_tag = f'<img src="{logo_url}" style="width:44px;height:44px;object-fit:contain;border-radius:8px">' if logo_url else '<span style="font-size:32px">🧬</span>'

    return f"""<!DOCTYPE html>
<html>
<head>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#080b14;font-family:'Inter',sans-serif;color:#ccc;font-size:13px;padding:14px;line-height:1.5}}
::-webkit-scrollbar{{width:5px}}::-webkit-scrollbar-track{{background:#0a0c14}}::-webkit-scrollbar-thumb{{background:#2a2d3a;border-radius:3px}}

.header{{display:flex;align-items:center;gap:14px;margin-bottom:16px}}
.title{{font-family:'IBM Plex Mono',monospace;font-size:20px;font-weight:700;color:#eee}}
.sub{{font-size:12px;color:#555;margin-top:2px}}

.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:16px}}
.sc{{background:#0f1117;border:1px solid #1e2030;border-radius:8px;padding:12px;text-align:center}}
.sn{{font-size:1.3rem;font-weight:600;font-family:'IBM Plex Mono',monospace}}
.sl{{font-size:10px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.08em}}

.filter-bar{{display:flex;gap:8px;margin-bottom:14px;align-items:center;flex-wrap:wrap}}
.fb{{padding:6px 14px;border-radius:20px;border:1px solid #1e2030;background:#0f1117;
    color:#555;font-size:11px;cursor:pointer;font-family:'IBM Plex Mono',monospace;transition:all 0.15s}}
.fb:hover{{border-color:#3a3d5a}}
.fb.active{{border-color:#FF4C4C;color:#FF4C4C;background:#1a0808}}
.fb.am.active{{border-color:#FFA500;color:#FFA500;background:#1a1200}}
.fb.al.active{{border-color:#4CA8FF;color:#4CA8FF;background:#08101a}}
.fb.aa.active{{border-color:#555;color:#ccc}}

/* Cards */
.card{{background:#0a0c14;border:1px solid #1e2030;border-radius:10px;margin-bottom:10px;overflow:hidden}}
.card:hover{{border-color:#2a2d3a}}
.chead{{display:flex;align-items:center;gap:12px;padding:16px;cursor:pointer;user-select:none}}
.crank{{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#3a3d5a;min-width:28px}}
.cdot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
.clabel{{font-family:'IBM Plex Mono',monospace;font-size:14px;font-weight:700;color:#eee;flex:1}}
.cbadge{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:10px;font-weight:600;
        font-family:'IBM Plex Mono',monospace;margin-right:6px}}
.chev{{color:#444;font-size:12px;transition:transform 0.2s;margin-left:4px}}
.chev.open{{transform:rotate(90deg)}}
.cbody{{display:none;border-top:1px solid #1e2030}}
.cbody.open{{display:block}}

/* Two-column layout inside card */
.cgrid{{display:grid;grid-template-columns:360px 1fr;min-height:500px}}
.cleft{{padding:16px;border-right:1px solid #1e2030;overflow-y:auto}}
.cright{{padding:16px;background:#080b14;overflow-y:auto}}

.sl2{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;
     letter-spacing:0.15em;color:#3a3d5a;padding-bottom:5px;border-bottom:1px solid #1a1d2e;margin:12px 0 8px}}
.sl2:first-child{{margin-top:0}}
.drow{{display:flex;gap:8px;padding:5px 0;border-bottom:1px solid #0d0f1a;font-size:11px;line-height:1.5}}
.dl{{color:#3a3d5a;min-width:76px;font-size:10px;font-family:'IBM Plex Mono',monospace;flex-shrink:0;padding-top:1px}}
.dv{{color:#bbb;flex:1}}

.hyp-text{{font-size:12px;color:#888;line-height:1.7;padding:10px 12px;background:#080b14;
          border:1px solid #1e2030;border-radius:6px;margin-bottom:10px}}
.action-box{{background:#0a1a0a;border:1px solid #1a3a1a;border-radius:6px;padding:10px 12px;margin-top:8px}}
.al{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;
    letter-spacing:0.12em;color:#4CAF50;margin-bottom:5px}}
.at{{font-size:11px;color:#888;line-height:1.7}}

/* Mini chain animation */
.chain-wrap{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}}
.chain-lbl{{font-size:10px;font-family:'IBM Plex Mono',monospace;color:#555;margin-bottom:4px}}
.chain-svg{{width:100%;height:42px;border:1px solid #1e2030;border-radius:5px;background:#040608;display:block}}
.bar-row{{margin-bottom:6px}}
.bar-lbl{{display:flex;justify-content:space-between;font-size:10px;color:#555;margin-bottom:2px;font-family:'IBM Plex Mono',monospace}}
.bar-track{{background:#1a1d2e;border-radius:3px;height:6px;overflow:hidden}}
.bar-fill{{height:100%;border-radius:3px;transition:width 0.3s}}

/* Slider */
.slider-box{{margin-bottom:12px;padding:12px;background:#0a0c14;border:1px solid #1e2030;border-radius:8px}}
.sltitle{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:8px}}
.slrow{{display:flex;align-items:center;gap:8px;margin-bottom:6px}}
.sllbl{{font-size:10px;font-family:'IBM Plex Mono',monospace;color:#555;min-width:55px}}
input[type=range]{{flex:1;cursor:pointer;height:4px;accent-color:#FF4C4C}}
.slval{{font-size:11px;font-family:'IBM Plex Mono',monospace;color:#aaa;min-width:90px;text-align:right}}
.phase-bar{{height:12px;background:#1a1d2e;border-radius:6px;position:relative;overflow:hidden;margin:6px 0}}
.phase-fill{{height:100%;border-radius:6px;transition:width 0.3s;display:flex;align-items:center;
           padding-left:6px;font-size:9px;font-family:'IBM Plex Mono',monospace;color:white;overflow:hidden;white-space:nowrap}}
.pmark{{position:absolute;top:0;height:100%;width:2px;background:white;opacity:0.7;transition:left 0.3s;z-index:5}}
.evt{{display:flex;gap:6px;margin-bottom:5px;transition:opacity 0.3s}}
.evt.off{{opacity:0.15}}
.edot{{width:7px;height:7px;border-radius:50%;flex-shrink:0;margin-top:3px}}
.evt strong{{display:block;font-size:10px;color:#eee;margin-bottom:1px}}
.evt span{{font-size:9px;color:#555;line-height:1.4}}

/* Big protein canvas */
.prot-wrap{{margin-bottom:12px;padding:12px;background:#040608;border:1px solid #1e2030;border-radius:10px}}
.prot-title{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:8px}}
.prot-stage{{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#aaa;text-align:center;margin:6px 0 3px}}
.prot-desc{{font-size:10px;color:#555;text-align:center;line-height:1.6;min-height:28px;margin-bottom:6px}}
canvas{{display:block;width:100%;border-radius:6px;background:#040608}}
.stage-dots{{display:flex;justify-content:center;gap:6px;margin-top:6px}}
.sdot{{width:7px;height:7px;border-radius:50%;transition:background 0.3s}}

/* Cell diagram */
.cell-box{{padding:12px;background:#0a0c14;border:1px solid #1e2030;border-radius:8px}}
.cell-grid{{display:grid;grid-template-columns:90px 1fr;gap:12px;align-items:start}}
.cell-col{{display:flex;flex-direction:column;align-items:center;gap:5px}}
.cell-title{{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;margin-bottom:5px}}
.cell-desc{{font-size:11px;color:#888;line-height:1.6}}

@keyframes cpulse{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.12)}}}}
@keyframes cspin{{0%{{transform:rotate(0deg)}}100%{{transform:rotate(360deg)}}}}
@keyframes cgrow{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.18)}}}}
@keyframes cshake{{0%,100%{{transform:translateX(0)}}25%{{transform:translateX(-3px)}}75%{{transform:translateX(3px)}}}}
@keyframes wobble-critical{{0%,100%{{transform:translateY(0)}}30%{{transform:translateY(-7px)}}70%{{transform:translateY(5px)}}}}
@keyframes wobble-affected{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-3px)}}}}
@keyframes wobble-normal{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-1px)}}}}
</style>
</head>
<body>

<div class="header">
  {logo_tag}
  <div>
    <div class="title">Hypothesis Lab</div>
    <div class="sub">{len(residues_data)} hypotheses — expand any card for structural animation, mutation timeline, and cell impact</div>
  </div>
</div>

<div class="stats">
  <div class="sc"><div class="sn" style="color:#eee">{len(residues_data)}</div><div class="sl">Total</div></div>
  <div class="sc"><div class="sn" style="color:#FF4C4C">{n_high}</div><div class="sl">HIGH</div></div>
  <div class="sc"><div class="sn" style="color:#FFA500">{n_med}</div><div class="sl">MEDIUM</div></div>
  <div class="sc"><div class="sn" style="color:#4CA8FF">{n_low}</div><div class="sl">LOW</div></div>
  <div class="sc"><div class="sn" style="color:#FF4C4C;font-size:13px">{top.get("label","—")}</div><div class="sl">Top · {top.get("score","—")}</div></div>
</div>

<div class="filter-bar">
  <span style="font-size:11px;color:#3a3d5a;font-family:'IBM Plex Mono',monospace">Filter:</span>
  <button class="fb aa active" onclick="doFilter('ALL',this)">All</button>
  <button class="fb" onclick="doFilter('HIGH',this)" style="color:#FF4C4C88;border-color:#FF4C4C33">HIGH</button>
  <button class="fb am" onclick="doFilter('MEDIUM',this)">MEDIUM</button>
  <button class="fb al" onclick="doFilter('LOW',this)">LOW</button>
  <button class="fb" onclick="expandAll()" style="margin-left:auto">Expand all</button>
  <button class="fb" onclick="collapseAll()">Collapse all</button>
</div>

<div id="cards"></div>

<script>
const RESIDUES={res_json};
const CELLD={cell_json};

function gc(s){{return s==='critical'?'#FF4C4C':s==='affected'?'#FFA500':'#4CA8FF';}}
function lerp(a,b,t){{return a+(b-a)*Math.max(0,Math.min(1,t));}}
function clamp(v,a,b){{return Math.max(a,Math.min(b,v));}}
function lerpColor(c1,c2,t){{
  t=clamp(t,0,1);
  const h=v=>parseInt(v,16);
  const r=Math.round(lerp(h(c1.slice(1,3)),h(c2.slice(1,3)),t));
  const g=Math.round(lerp(h(c1.slice(3,5)),h(c2.slice(3,5)),t));
  const b=Math.round(lerp(h(c1.slice(5,7)),h(c2.slice(5,7)),t));
  return '#'+[r,g,b].map(v=>v.toString(16).padStart(2,'0')).join('');
}}

// ── Mini chain ──────────────────────────────────────────────────────────
function buildChain(pos,status,score){{
  const c=gc(status),isH=status==='critical',isM=status==='affected';
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
  const bars=['Zinc coord.','DNA binding','Thermal stab.','Transcription'].map((l,i)=>`
    <div class="bar-row">
      <div class="bar-lbl"><span>${{l}}</span><span style="color:${{c}}">${{pcts[i]}}%</span></div>
      <div class="bar-track"><div class="bar-fill" style="width:${{pcts[i]}}%;background:${{c}}"></div></div>
    </div>`).join('');
  return `<div class="chain-wrap">
    <div>
      <div class="chain-lbl" style="color:#4CAF50">Wild-type chain</div>
      <svg class="chain-svg" viewBox="0 0 ${{W}} 42">${{wt}}</svg>
      <div class="chain-lbl" style="color:${{c}};margin-top:6px">Mutant — pos ${{pos}} (wobble = instability)</div>
      <svg class="chain-svg" viewBox="0 0 ${{W}} 42">${{mut}}</svg>
    </div>
    <div><div class="chain-lbl">Function vs wild-type</div>${{bars}}</div>
  </div>`;
}}

// ── Canvas protein drawings ─────────────────────────────────────────────
function drawZincCollapse(ctx,W,H,t,c){{
  ctx.clearRect(0,0,W,H);
  const dnaY=lerp(55,25,clamp((t-0.6)*2.5,0,1));
  ctx.save();
  ctx.strokeStyle=lerpColor('#378add','#1e2030',t);ctx.lineWidth=2.5;ctx.setLineDash([10,5]);
  ctx.beginPath();ctx.moveTo(25,dnaY);ctx.lineTo(W-25,dnaY);ctx.stroke();ctx.setLineDash([]);
  ctx.fillStyle='#378add99';ctx.font='11px IBM Plex Mono,monospace';ctx.fillText('DNA',28,dnaY-8);

  const hc=lerpColor('#4CAF50',c,t);
  ctx.strokeStyle=hc;ctx.lineWidth=4;
  ctx.beginPath();
  for(let x=25;x<W-25;x++){{
    const wobble=t>0.35?Math.sin((x/28)*Math.PI)*lerp(0,22,t-0.35)*Math.sin((x/(W/2))*Math.PI):0;
    const y=H/2+18+wobble+Math.sin((x/55)*Math.PI)*9;
    x===25?ctx.moveTo(x,y):ctx.lineTo(x,y);
  }}
  ctx.stroke();

  const za=clamp(1-t*2.2,0,1),znX=W/2,znY=H/2+52;
  ctx.globalAlpha=za;
  ctx.strokeStyle='#FFC107';ctx.lineWidth=2;
  ctx.beginPath();ctx.arc(znX,znY,13,0,Math.PI*2);ctx.stroke();
  ctx.fillStyle='#FFC107';ctx.font='bold 10px IBM Plex Mono,monospace';ctx.textAlign='center';ctx.fillText('Zn²⁺',znX,znY+4);
  ctx.globalAlpha=za*0.8;ctx.setLineDash([3,3]);
  [[W/2-55,H/2+18],[W/2-25,H/2+22],[W/2+25,H/2+22],[W/2+55,H/2+18]].forEach(([x,y])=>{{ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(znX,znY);ctx.stroke();}});
  ctx.setLineDash([]);ctx.globalAlpha=1;

  const ca=clamp(1-t*2,0,1);
  ctx.globalAlpha=ca;ctx.strokeStyle=hc;ctx.lineWidth=2;ctx.setLineDash([4,4]);
  [W/2-55,W/2,W/2+55].forEach(x=>{{ctx.beginPath();ctx.moveTo(x,H/2+15);ctx.lineTo(x,dnaY);ctx.stroke();}});
  ctx.setLineDash([]);ctx.globalAlpha=1;

  const mx=W/2-28,my=H/2+18;
  ctx.fillStyle=c+'55';ctx.strokeStyle=c;ctx.lineWidth=2.5;
  ctx.beginPath();ctx.arc(mx,my,12,0,Math.PI*2);ctx.fill();ctx.stroke();
  ctx.fillStyle=c;ctx.font='bold 9px IBM Plex Mono,monospace';ctx.textAlign='center';ctx.fillText('R175H',mx,my+3);
  ctx.restore();
}}

function drawDNAContactLoss(ctx,W,H,t,c){{
  ctx.clearRect(0,0,W,H);
  const dnaY=lerp(50,18,clamp(t*2-0.2,0,1));
  ctx.save();
  ctx.strokeStyle=lerpColor('#378add','#1e2030',t*0.8);ctx.lineWidth=2.5;ctx.setLineDash([10,5]);
  ctx.beginPath();ctx.moveTo(25,dnaY);ctx.lineTo(W-25,dnaY);ctx.stroke();ctx.setLineDash([]);
  ctx.fillStyle='#378add';ctx.font='11px IBM Plex Mono,monospace';ctx.fillText('DNA',28,dnaY-8);

  ctx.strokeStyle=t<0.4?'#4CAF50':'#FFA500';ctx.lineWidth=4;
  ctx.beginPath();
  for(let x=25;x<W-25;x++){{const y=H/2+20+Math.sin((x/65)*Math.PI)*10;x===25?ctx.moveTo(x,y):ctx.lineTo(x,y);}}
  ctx.stroke();

  [W/2-65,W/2,W/2+65].forEach((cx,i)=>{{
    const broken=t>0.25+i*0.18;
    const cy=H/2+20+Math.sin((cx/65)*Math.PI)*10;
    if(!broken){{
      ctx.strokeStyle='#4CAF50';ctx.lineWidth=2;ctx.setLineDash([]);
      ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(cx,dnaY);ctx.stroke();
      ctx.fillStyle='#4CAF50';ctx.beginPath();ctx.arc(cx,dnaY,5,0,Math.PI*2);ctx.fill();
    }} else {{
      ctx.strokeStyle=c;ctx.lineWidth=2;ctx.setLineDash([4,4]);ctx.globalAlpha=0.25;
      ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(cx,dnaY+15);ctx.stroke();
      ctx.globalAlpha=1;ctx.setLineDash([]);
      ctx.fillStyle=c+'55';ctx.strokeStyle=c;ctx.lineWidth=2.5;
      ctx.beginPath();ctx.arc(cx,cy,10,0,Math.PI*2);ctx.fill();ctx.stroke();
      ctx.fillStyle=c;ctx.font='8px IBM Plex Mono,monospace';ctx.textAlign='center';
      ctx.fillText(i===0?'R248':i===1?'R273':'',cx,cy+3);
    }}
  }});
  ctx.restore();
}}

function drawHelixBreak(ctx,W,H,t,c){{
  ctx.clearRect(0,0,W,H);ctx.save();
  ctx.strokeStyle='#378add33';ctx.lineWidth=2;ctx.setLineDash([8,5]);
  ctx.beginPath();ctx.moveTo(25,48);ctx.lineTo(W-25,48);ctx.stroke();ctx.setLineDash([]);
  const bx=W/2,ba=t*38;
  ctx.lineWidth=4;
  ctx.strokeStyle=t<0.3?'#4CAF50':'#FFA500';
  ctx.beginPath();
  for(let x=25;x<bx;x++){{const y=H/2+18+Math.sin((x/55)*Math.PI)*12;x===25?ctx.moveTo(x,y):ctx.lineTo(x,y);}}
  ctx.stroke();
  ctx.strokeStyle=t<0.55?'#4CAF50':t<0.8?'#FFA500':'#FF4C4C';
  ctx.beginPath();
  for(let x=bx;x<W-25;x++){{const y=H/2+18-ba*0.5+Math.sin((x/55)*Math.PI)*12*(1-t*0.25);x===bx?ctx.moveTo(x,y):ctx.lineTo(x,y);}}
  ctx.stroke();
  const my=H/2+18+Math.sin((bx/55)*Math.PI)*12;
  ctx.fillStyle=c+'55';ctx.strokeStyle=c;ctx.lineWidth=2.5;
  ctx.beginPath();ctx.arc(bx,my,13,0,Math.PI*2);ctx.fill();ctx.stroke();
  ctx.fillStyle=c;ctx.font='bold 9px IBM Plex Mono,monospace';ctx.textAlign='center';ctx.fillText('R282W',bx,my+3);
  ctx.globalAlpha=clamp(1-t*2.2,0,1);
  ctx.strokeStyle='#FFC107';ctx.lineWidth=2;ctx.setLineDash([3,3]);
  ctx.beginPath();ctx.moveTo(bx-30,H/2+35);ctx.lineTo(bx+30,H/2+35);ctx.stroke();
  ctx.setLineDash([]);ctx.fillStyle='#FFC107';ctx.font='9px IBM Plex Mono,monospace';ctx.fillText('salt bridge',bx,H/2+48);
  ctx.globalAlpha=1;ctx.restore();
}}

function drawLoopDistortion(ctx,W,H,t,c){{
  ctx.clearRect(0,0,W,H);ctx.save();
  const dnaY=50+t*28;
  ctx.strokeStyle=lerpColor('#378add','#1e2030',t);ctx.lineWidth=2.5;ctx.setLineDash([10,5]);
  ctx.beginPath();ctx.moveTo(25,dnaY);ctx.lineTo(W-25,dnaY);ctx.stroke();ctx.setLineDash([]);
  ctx.fillStyle='#378add';ctx.font='11px IBM Plex Mono,monospace';ctx.fillText('DNA',28,dnaY-8);
  ctx.strokeStyle='#4CAF50';ctx.lineWidth=4;
  ctx.beginPath();for(let x=25;x<W-25;x++){{const y=H/2+15+Math.sin((x/75)*Math.PI)*8;x===25?ctx.moveTo(x,y):ctx.lineTo(x,y);}}ctx.stroke();
  const lx=W/2,ly=H/2+15,ld=t*38;
  ctx.strokeStyle=t<0.3?'#4CAF50':t<0.6?'#FFA500':'#FF4C4C';ctx.lineWidth=3;
  ctx.beginPath();ctx.moveTo(lx-50,ly);ctx.quadraticCurveTo(lx,ly-18+ld,lx+50,ly);ctx.stroke();
  ctx.fillStyle=c+'55';ctx.strokeStyle=c;ctx.lineWidth=2.5;
  ctx.beginPath();ctx.arc(lx,ly-8+ld*0.5,12,0,Math.PI*2);ctx.fill();ctx.stroke();
  ctx.fillStyle=c;ctx.font='bold 9px IBM Plex Mono,monospace';ctx.textAlign='center';ctx.fillText('G245S',lx,ly-5+ld*0.5+3);
  if(t>0.3){{ctx.globalAlpha=clamp(t-0.3,0,1);ctx.strokeStyle='#FF4C4C';ctx.lineWidth=2;ctx.setLineDash([3,3]);ctx.beginPath();ctx.moveTo(lx,ly-15+ld*0.8);ctx.lineTo(lx,dnaY-5);ctx.stroke();ctx.setLineDash([]);ctx.globalAlpha=1;}}
  ctx.restore();
}}

function drawSurfaceCavity(ctx,W,H,t,c){{
  ctx.clearRect(0,0,W,H);ctx.save();
  ctx.strokeStyle=t<0.35?'#4CAF50':t<0.7?'#FFA500':'#FF9800';ctx.lineWidth=4;
  ctx.beginPath();for(let x=25;x<W-25;x++){{const y=H/2+Math.sin((x/55)*Math.PI)*10;x===25?ctx.moveTo(x,y):ctx.lineTo(x,y);}}ctx.stroke();
  const cW=lerp(0,58,t),cH=lerp(0,42,t),cX=W/2,cY=H/2-5;
  ctx.fillStyle=t<0.5?'#1e2030':'#080b14';
  ctx.beginPath();ctx.ellipse(cX,cY+cH/2,cW/2,cH/2,0,0,Math.PI*2);ctx.fill();
  if(t>0.08){{ctx.strokeStyle=c;ctx.lineWidth=1.5;ctx.setLineDash([3,3]);ctx.beginPath();ctx.ellipse(cX,cY+cH/2,cW/2,cH/2,0,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);}}
  ctx.fillStyle=t<0.3?'#4CAF50':c;ctx.font='bold 9px IBM Plex Mono,monospace';ctx.textAlign='center';ctx.fillText(t<0.25?'Y220 (Tyr)':'Y220C (cavity)',cX,cY+cH/2+4);
  if(t>0.55){{ctx.globalAlpha=clamp((t-0.55)*2.5,0,1);ctx.fillStyle='#4CA8FF';ctx.font='10px IBM Plex Mono,monospace';ctx.fillText('← druggable pocket',cX+38,cY+cH/2);ctx.fillText('target: PC14586',cX+38,cY+cH/2+13);ctx.globalAlpha=1;}}
  if(t>0.65){{ctx.globalAlpha=clamp((t-0.65)*3,0,0.9);for(let i=0;i<4;i++){{ctx.fillStyle='#64b5f6';ctx.beginPath();ctx.arc(cX-14+i*10,cY+cH*0.35+i*4,3,0,Math.PI*2);ctx.fill();}}ctx.globalAlpha=1;}}
  ctx.restore();
}}

function drawDefault(ctx,W,H,t,c){{
  ctx.clearRect(0,0,W,H);ctx.save();
  ctx.strokeStyle=lerpColor('#4CAF50',c,t);ctx.lineWidth=4;
  ctx.beginPath();for(let x=25;x<W-25;x++){{const d=t*Math.sin((x/35)*Math.PI)*18;const y=H/2+18+d+Math.sin((x/65)*Math.PI)*10;x===25?ctx.moveTo(x,y):ctx.lineTo(x,y);}}ctx.stroke();
  const mx=W/2,my=H/2+18;
  ctx.fillStyle=c+'55';ctx.strokeStyle=c;ctx.lineWidth=2.5;
  ctx.beginPath();ctx.arc(mx,my,13,0,Math.PI*2);ctx.fill();ctx.stroke();
  ctx.fillStyle=c;ctx.font='bold 10px IBM Plex Mono,monospace';ctx.textAlign='center';ctx.fillText('MUT',mx,my+4);
  ctx.restore();
}}

const DRAWS={zinc_collapse:drawZincCollapse,dna_contact_loss:drawDNAContactLoss,helix_break:drawHelixBreak,loop_distortion:drawLoopDistortion,surface_cavity:drawSurfaceCavity,default:drawDefault};

const STRUCT_STAGES={{
  zinc_collapse:["WT: zinc stably coordinated (C176/H179/C238/C242)","R175H distorts L2 loop geometry","Zinc coordination weakening","Zinc ion released from binding site","L2 loop unfolds — domain begins collapse","Full domain misfolding — DNA binding impossible"],
  dna_contact_loss:["WT: R248/R273 directly contacts DNA","Mutation removes contact residue","DNA-binding interface weakens","Protein-DNA H-bonds breaking","DNA strand separating","Complete loss of sequence-specific recognition"],
  helix_break:["WT: H2 helix stabilised by R282–E271 salt bridge","Mutation removes stabilising interaction","Helix N-terminus begins to unwind","Unwinding propagates along helix axis","DNA-binding domain reshaped","Loss of transcriptional activity"],
  loop_distortion:["WT: Gly allows L3 loop tight approach to DNA","G245S/D adds bulky side chain","Steric clash with DNA backbone","L3 loop forced away from DNA","DNA approach angle blocked","Recognition abolished"],
  surface_cavity:["WT: Y220 fills surface pocket — domain stable","Y220C removes aromatic side chain","Surface pocket opens","Hydrophobic residues exposed","Thermodynamic destabilisation","Tm −6°C — druggable cavity created"],
  default:["Wild-type conformation","Mutation introduced","Local structural change","Conformational propagation","Functional interface altered","Reduced biological activity"],
}};

// ── Global slider state ─────────────────────────────────────────────────
window._SD={{}};

function buildSliderCanvas(d,idx){{
  const c=gc(d.status),isH=d.status==='critical';
  if(d.score<0.25){{
    return `<div style="background:#0a1a0a;border:1px solid #1a3a1a;border-radius:6px;padding:12px;font-size:11px;color:#666;line-height:1.6;margin-bottom:12px">
      LOW effect score (${{d.score}}). This variant likely represents tolerated substitution or normal variation. No pathological timeline applicable.
    </div>`;
  }}
  const sk=d.struct_effect||'default';
  const stages=STRUCT_STAGES[sk]||STRUCT_STAGES['default'];
  const events=[
    {{day:1,label:"Single-cell mutation",desc:"One cell acquires this mutation. Immune surveillance may clear it.",ec:'#555'}},
    {{day:isH?55:110,label:"Clonal expansion begins",desc:"Mutant cell divides — mutation passes to daughter cells. Still undetectable.",ec:c}},
    {{day:isH?180:365,label:"Detectable population",desc:"Sensitive liquid biopsy might detect mutant fragments. Still asymptomatic.",ec:c}},
    {{day:isH?365:730,label:"Microenvironment effects",desc:"VEGF/TGF-β paracrine signalling starts influencing neighbouring cells.",ec:'#e24b4a'}},
    {{day:isH?730:1460,label:"Clinically detectable",desc:"At typical detection sizes (~0.5–1cm). Billions of cell divisions have occurred.",ec:'#e24b4a'}},
  ];
  const maxDay=events[events.length-1].day+200;
  window._SD[idx]={{events,maxDay,sk,c,stages,cellKey:d.cell||'apoptosis'}};
  const evHTML=events.map((e,i)=>`<div class="evt off" id="ev-${{idx}}-${{i}}"><div class="edot" style="background:${{e.ec}}"></div><div><strong>Day ~${{e.day}}: ${{e.label}}</strong><span>${{e.desc}}</span></div></div>`).join('');
  const dots=stages.map((_,i)=>`<div class="sdot" id="sd-${{idx}}-${{i}}" style="background:${{i===0?c:'#1e2030'}}"></div>`).join('');
  return `
  <div class="slider-box">
    <div class="sltitle">Mutation timeline — drag slider · protein animation updates in real time</div>
    <div style="background:#0a0c1a;border:1px solid #1a1d3a;border-radius:5px;padding:7px;margin-bottom:8px;font-size:9px;color:#444;line-height:1.5">
      ⚠ Population-level estimates from published TP53 kinetics literature. Not individual predictions.
    </div>
    <div class="slrow">
      <span class="sllbl">Day</span>
      <input type="range" id="sl-${{idx}}" min="0" max="${{maxDay}}" value="0" oninput="updateAll(${{idx}},parseInt(this.value))">
      <span class="slval" id="sv-${{idx}}">Day 0 — pre-mutation</span>
    </div>
    <div class="phase-bar"><div class="phase-fill" id="pf-${{idx}}" style="width:0%;background:${{c}}"></div><div class="pmark" id="pm-${{idx}}" style="left:0%"></div></div>
    <div style="margin-top:8px">${{evHTML}}</div>
  </div>
  <div class="prot-wrap">
    <div class="prot-title">Protein structural change — driven by slider above</div>
    <canvas id="pc-${{idx}}" height="200" style="height:200px"></canvas>
    <div class="prot-stage" id="psl-${{idx}}">${{stages[0]}}</div>
    <div class="stage-dots" id="sdots-${{idx}}">${{dots}}</div>
  </div>`;
}}

function buildCell(d,idx){{
  const imp=CELLD[d.cell||'apoptosis']||CELLD['apoptosis'];
  const c=imp.color;
  const bars=['Apoptosis activation','p21 induction','DNA repair','Tumour suppression'].map((l,i)=>{{
    const v=d.status==='critical'?[3,4,15,2][i]:d.status==='affected'?[42,38,52,48][i]:[88,90,92,88][i];
    return `<div class="bar-row"><div class="bar-lbl"><span>${{l}}</span><span id="cb-${{idx}}-${{i}}" style="color:${{c}}">${{v}}%</span></div><div class="bar-track"><div id="cbf-${{idx}}-${{i}}" class="bar-fill" style="width:${{v}}%;background:${{c}}"></div></div></div>`;
  }}).join('');
  return `<div class="cell-box">
    <div class="sl2" style="margin-top:0">Cell-level impact</div>
    <div class="cell-grid">
      <div class="cell-col">
        <svg width="56" height="56" viewBox="0 0 56 56">
          <ellipse cx="28" cy="28" rx="23" ry="21" fill="#0a1f0a" stroke="#2a5a2a" stroke-width="1.5"/>
          <ellipse cx="28" cy="28" rx="9" ry="8" fill="#1a4a1a" stroke="#4CAF50" stroke-width="1.5"/>
          <text x="28" y="31" text-anchor="middle" font-size="5" fill="#4CAF50" font-family="monospace">WT</text>
        </svg>
        <span style="font-size:9px;color:#4CAF50;font-family:'IBM Plex Mono',monospace">Normal</span>
        <span style="color:${{c}};font-size:14px;line-height:1">↓</span>
        <svg id="csq-${{idx}}" width="56" height="56" viewBox="0 0 56 56" style="transform-origin:center">
          <ellipse id="co-${{idx}}" cx="28" cy="28" rx="23" ry="21" fill="#1f0808" stroke="${{c}}" stroke-width="1.5" stroke-dasharray="4,2"/>
          <ellipse cx="28" cy="28" rx="11" ry="9" fill="#2a0808" stroke="${{c}}" stroke-width="1.5"/>
          <circle cx="13" cy="18" r="2.5" fill="${{c}}" opacity="0.7"/>
          <circle cx="43" cy="38" r="2" fill="${{c}}" opacity="0.5"/>
          <text x="28" y="31" text-anchor="middle" font-size="5" fill="${{c}}" font-family="monospace">MUT</text>
        </svg>
        <span style="font-size:9px;color:${{c}};font-family:'IBM Plex Mono',monospace">Affected</span>
      </div>
      <div>
        <div class="cell-title" id="ctit-${{idx}}" style="color:${{c}}">${{imp.title}}</div>
        <div class="cell-desc">${{imp.desc}}</div>
        <div style="margin-top:10px">${{bars}}</div>
      </div>
    </div>
  </div>`;
}}

function updateAll(idx,day){{
  const sd=window._SD[idx];if(!sd)return;
  const {{events,maxDay,sk,c,stages,cellKey}}=sd;
  const imp=CELLD[cellKey]||CELLD['apoptosis'];
  const t=clamp(day/maxDay,0,1);

  // Day label
  const sv=document.getElementById('sv-'+idx);
  if(sv) sv.textContent=day===0?'Day 0 — pre-mutation':day>365?`Day ${{day}} (~${{(day/365).toFixed(1)}}yr)`:`Day ${{day}}`;

  // Progress bar
  const pct=(t*100).toFixed(1);
  const pf=document.getElementById('pf-'+idx),pm=document.getElementById('pm-'+idx);
  if(pf){{pf.style.width=pct+'%';pf.textContent=day<(events[2]?.day||180)?'subclinical':day<(events[4]?.day||730)?'detectable':'clinical';}}
  if(pm) pm.style.left=pct+'%';

  // Events
  events.forEach((e,i)=>{{const el=document.getElementById('ev-'+idx+'-'+i);if(el)el.classList.toggle('off',day<e.day);}});

  // Canvas
  const canvas=document.getElementById('pc-'+idx);
  if(canvas){{const ctx=canvas.getContext('2d');(DRAWS[sk]||DRAWS['default'])(ctx,canvas.width,canvas.height,t,c);}}

  // Stage label + dots
  const stageIdx=Math.min(stages.length-1,Math.floor(t*stages.length));
  const psl=document.getElementById('psl-'+idx);
  if(psl) psl.textContent=stages[stageIdx]||'';
  for(let i=0;i<stages.length;i++){{const dot=document.getElementById('sd-'+idx+'-'+i);if(dot)dot.style.background=i<=stageIdx?c:'#1e2030';}}

  // Cell bars
  const baseCrit=[3,4,15,2],baseAff=[42,38,52,48],baseNorm=[88,90,92,88];
  const base=imp.color==='#FF4C4C'?baseCrit:imp.color==='#FFA500'?baseAff:baseNorm;
  for(let i=0;i<4;i++){{
    const wt=100,mut=base[i];
    const current=Math.round(mut+(wt-mut)*(1-t));
    const bf=document.getElementById('cbf-'+idx+'-'+i),cb=document.getElementById('cb-'+idx+'-'+i);
    if(bf) bf.style.width=current+'%';
    if(cb) cb.textContent=current+'%';
  }}

  // Cell animation
  const csq=document.getElementById('csq-'+idx);
  if(csq){{csq.style.animation=t>0.3?`${{imp.anim}} ${{2-t*0.5}}s ease-in-out infinite`:'none';}}
}}

// ── Build cards ─────────────────────────────────────────────────────────
function buildCard(d,idx){{
  const c=gc(d.status);
  const hyp=d.hypothesis||`Residue ${{d.pos}} (${{d.label}}) — ${{d.priority}} priority (score ${{d.score}}).`;
  return `<div class="card" id="card-${{idx}}" data-priority="${{d.priority}}">
    <div class="chead" onclick="toggle(${{idx}})">
      <span class="crank">#${{idx+1}}</span>
      <div class="cdot" style="background:${{c}}"></div>
      <span class="clabel">${{d.label}}</span>
      <span class="cbadge" style="background:${{c}}22;color:${{c}};border:0.5px solid ${{c}}55">${{d.priority}}</span>
      <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:${{c}}">${{d.score}}</span>
      <span style="color:#3a3d5a;font-size:10px;margin-left:6px">${{d.expType||''}}</span>
      <span class="chev" id="chev-${{idx}}">▶</span>
    </div>
    <div class="cbody" id="body-${{idx}}">
      <div class="cgrid">
        <div class="cleft">
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
          <div class="sl2" style="margin-top:14px">Structural fluctuation — WT vs mutant</div>
          ${{buildChain(d.pos,d.status,d.score)}}
        </div>
        <div class="cright">
          ${{buildSliderCanvas(d,idx)}}
          ${{buildCell(d,idx)}}
        </div>
      </div>
    </div>
  </div>`;
}}

const wrap=document.getElementById('cards');
RESIDUES.forEach((d,i)=>{{wrap.innerHTML+=buildCard(d,i);}});

function toggle(idx){{
  const body=document.getElementById('body-'+idx),chev=document.getElementById('chev-'+idx);
  const open=body.classList.contains('open');
  body.classList.toggle('open',!open);chev.classList.toggle('open',!open);
  if(!open){{
    setTimeout(()=>{{
      const canvas=document.getElementById('pc-'+idx);
      if(canvas){{
        const d=RESIDUES[idx],sk=d.struct_effect||'default';
        (DRAWS[sk]||DRAWS['default'])(canvas.getContext('2d'),canvas.width,canvas.height,0,gc(d.status));
      }}
    }},60);
  }}
}}

function doFilter(p,btn){{
  document.querySelectorAll('.fb').forEach(b=>b.classList.remove('active'));btn.classList.add('active');
  document.querySelectorAll('.card').forEach(c=>{{c.style.display=(p==='ALL'||c.dataset.priority===p)?'block':'none';}});
}}
function expandAll(){{document.querySelectorAll('.cbody').forEach(b=>b.classList.add('open'));document.querySelectorAll('.chev').forEach(c=>c.classList.add('open'));}}
function collapseAll(){{document.querySelectorAll('.cbody').forEach(b=>b.classList.remove('open'));document.querySelectorAll('.chev').forEach(c=>c.classList.remove('open'));}}

// Auto-open first HIGH card
const fh=document.querySelector('[data-priority="HIGH"] .cbody'),fc=document.querySelector('[data-priority="HIGH"] .chev');
if(fh){{fh.classList.add('open');fc.classList.add('open');setTimeout(()=>{{const c=document.querySelector('[data-priority="HIGH"] canvas');if(c){{const d=RESIDUES[0],sk=d.struct_effect||'default';(DRAWS[sk]||DRAWS['default'])(c.getContext('2d'),c.width,c.height,0,gc(d.status));}}}},80);}}
</script>
</body>
</html>"""


def render():
    if LOGO_B64:
        st.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px"><img src="{LOGO_B64}" style="height:42px;object-fit:contain;border-radius:7px"><div><strong style="font-size:1.15rem">Hypothesis Lab</strong><p style="color:#555;font-size:0.83rem;margin:0">Expand any card · drag slider → protein structure animates + cell diagram updates in sync</p></div></div>', unsafe_allow_html=True)
    else:
        st.markdown("## 💡 Hypothesis Lab")
    st.divider()

    if "t_scored" not in st.session_state:
        st.info("👈 Run Triage first in the **Triage System** tab.")
        return

    scored_df = st.session_state.t_scored

    with st.spinner("Building hypothesis lab..."):
        pdb_data = fetch_pdb()

    if not pdb_data:
        st.error("Could not load protein structure. Check internet connection.")
        return

    residues = []
    for _, row in scored_df.iterrows():
        pos       = int(row["residue_position"])
        score     = round(float(row.get("normalized_score", row.get("effect_score", 0))), 3)
        label     = str(row.get("mutation", f"Res{pos}"))
        if label in ("nan", ""):
            label = f"Res{pos}"
        priority  = str(row.get("priority", "LOW"))
        exp_type  = str(row.get("experiment_type", ""))
        hypothesis = str(row.get("hypothesis", ""))
        status    = {"HIGH": "critical", "MEDIUM": "affected", "LOW": "normal"}[priority]
        hs        = HOTSPOT_DATA.get(pos, {})
        residues.append({
            "pos": pos, "label": label, "score": score,
            "priority": priority, "expType": "" if exp_type in ("nan", "") else exp_type,
            "status": status, "hypothesis": hypothesis,
            "mechanism":    hs.get("mechanism",    "Effect score from your experimental data. Phase 2 will add mechanistic annotation."),
            "clinvar":      hs.get("clinvar",       "Not queried — Phase 2 integrates live ClinVar"),
            "cosmic":       hs.get("cosmic",        "Not queried"),
            "cancer":       hs.get("cancer",        "Not queried"),
            "therapeutic":  hs.get("therapeutic",   "Consult clinical database"),
            "domain":       hs.get("domain",        "Unknown — Phase 2 annotation pending"),
            "experiment":   hs.get("experiment",    "Thermal shift assay and EMSA as first-line validation."),
            "cell":         hs.get("cell",          "apoptosis" if status == "critical" else "structural"),
            "struct_effect":hs.get("struct_effect", "default"),
        })

    html = build_html(residues, pdb_data, LOGO_B64)
    components.html(html, height=3500, scrolling=True)
