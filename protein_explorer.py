"""
protein_explorer.py — Protellect Protein Explorer (Tab 3)
Simple, working version: CSV upload → 3D viewer with click-to-annotate,
residue info panel, experiment cards. No UniProt ID required.
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import requests

HOTSPOTS = {
    175:{"clinvar":"Pathogenic · 847 submissions","cosmic":"~6% of all cancers","cancer":"Breast, lung, colorectal, ovarian","mechanism":"Disrupts zinc coordination at C176/H179/C238/C242. Global misfolding of DNA-binding domain.","therapeutic":"APR-246 (eprenetapopt) — Phase III","cell":"apoptosis","domain":"DNA-binding domain (L2 loop) — zinc coordination"},
    248:{"clinvar":"Pathogenic · 623 submissions","cosmic":"~3% of all cancers","cancer":"Colorectal, lung, pancreatic","mechanism":"Direct DNA contact residue. Abolishes sequence-specific DNA binding.","therapeutic":"Synthetic lethality under investigation","cell":"checkpoint","domain":"DNA-binding domain (L3 loop) — DNA contact"},
    273:{"clinvar":"Pathogenic · 512 submissions","cosmic":"~3% of all cancers","cancer":"Colorectal, lung, brain","mechanism":"DNA backbone phosphate contact. Loss reduces affinity >100-fold.","therapeutic":"Small molecule stabilizers experimental","cell":"checkpoint","domain":"DNA-binding domain (S10 strand) — backbone contact"},
    249:{"clinvar":"Pathogenic · 298 submissions","cosmic":"~1.5% — liver cancer enriched","cancer":"Liver (HCC), lung, esophageal","mechanism":"H2 helix structural mutation. Aflatoxin B1 mutational signature.","therapeutic":"No specific therapy","cell":"proliferation","domain":"DNA-binding domain (H2 helix)"},
    245:{"clinvar":"Pathogenic · 187 submissions","cosmic":"~1.5% of cancers","cancer":"Breast, lung, sarcoma","mechanism":"Glycine essential for L3 loop geometry. Any side chain disrupts DNA approach.","therapeutic":"Structural correctors under investigation","cell":"apoptosis","domain":"DNA-binding domain (L3 loop)"},
    282:{"clinvar":"Pathogenic · 156 submissions","cosmic":"~1% of cancers","cancer":"Breast, colorectal, lung","mechanism":"R282 salt bridge with E271 stabilises H2 helix. Tryptophan disrupts this.","therapeutic":"No approved targeted therapy","cell":"apoptosis","domain":"DNA-binding domain (H2 helix)"},
    220:{"clinvar":"Pathogenic · 89 submissions","cosmic":"~1% of cancers","cancer":"Breast, lung, ovarian","mechanism":"Creates druggable hydrophobic cavity. Thermodynamic destabilisation.","therapeutic":"PC14586 (rezatapopt) — Phase II","cell":"apoptosis","domain":"DNA-binding domain (S7-S8 loop)"},
    176:{"clinvar":"Not directly pathogenic","cosmic":"Secondary effect","cancer":"Affected by R175H","mechanism":"Zinc ligand adjacent to R175. Geometry disrupted by R175H propagation.","therapeutic":"APR-246 binds C176 as scaffold","cell":"structural","domain":"DNA-binding domain — zinc coordination"},
    179:{"clinvar":"Uncertain significance","cosmic":"Secondary effect","cancer":"Affected by R175H","mechanism":"Zinc-coordinating histidine. Indirectly destabilised by R175H.","therapeutic":"N/A","cell":"structural","domain":"DNA-binding domain — zinc coordination"},
}

EXPERIMENTS = [
    {"id":"thermal","name":"Thermal Shift Assay","cat":"Structural","dur":"2–3 days","cost":"~$300","color":"#e24b4a","note":"Measures thermostability. HIGH mutations typically reduce Tm by 6–12°C vs WT.","affected":[175,176,179,220]},
    {"id":"emsa","name":"EMSA","cat":"Functional","dur":"1–2 days","cost":"~$200","color":"#ef9f27","note":"Directly measures DNA binding. HIGH mutations show complete loss of binding.","affected":[175,248,273,245]},
    {"id":"reporter","name":"Reporter Assay","cat":"Functional","dur":"3–5 days","cost":"~$400","color":"#9370DB","note":"Measures transactivation in cells. Confirms p21/MDM2/PUMA activation loss.","affected":[175,248,273,249]},
    {"id":"apr246","name":"APR-246 Rescue","cat":"Therapeutic","dur":"5–7 days","cost":"~$800","color":"#378add","note":"Tests whether APR-246 can refold structural mutants and restore WT-like function.","affected":[175,176,179,248]},
    {"id":"coip","name":"Co-IP Dom. Neg.","cat":"Mechanistic","dur":"3–4 days","cost":"~$600","color":"#1d9e75","note":"Confirms dominant negative suppression — mutant poisoning WT p53 tetramers.","affected":[175,248,273]},
]


def fetch_pdb(pdb_id="2OCJ"):
    try:
        r = requests.get(f"https://files.rcsb.org/download/{pdb_id}.pdb", timeout=15)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def build_html(scored_df, pdb_data):
    residues = {}
    for _, row in scored_df.iterrows():
        pos = int(row["residue_position"])
        score = round(float(row.get("normalized_score", row.get("effect_score", 0))), 3)
        label = str(row.get("mutation", f"Res{pos}"))
        priority = str(row.get("priority", "LOW"))
        exp_type = str(row.get("experiment_type", "DMS"))
        status = {"HIGH":"critical","MEDIUM":"affected","LOW":"normal"}[priority]
        hs = HOTSPOTS.get(pos, {})
        residues[pos] = {
            "label":label,"status":status,"priority":priority,"score":score,"expType":exp_type,"pos":pos,
            "domain":hs.get("domain","Unknown — Phase 2 annotation pending"),
            "mechanism":hs.get("mechanism","Effect score from your experimental data."),
            "clinvar":hs.get("clinvar","Not queried"),
            "cosmic":hs.get("cosmic","Not queried"),
            "cancer":hs.get("cancer","Not queried"),
            "therapeutic":hs.get("therapeutic","Consult clinical database"),
            "cell":hs.get("cell","apoptosis" if status=="critical" else "structural"),
        }

    res_json = json.dumps(residues, default=str)
    exp_json = json.dumps(EXPERIMENTS)
    total = len(scored_df)
    n_high = int((scored_df["priority"]=="HIGH").sum())
    n_med  = int((scored_df["priority"]=="MEDIUM").sum())
    n_low  = total - n_high - n_med
    top = scored_df.iloc[0]
    top_label = str(top.get("mutation", f"Res{int(top['residue_position'])}"))
    pdb_esc = pdb_data.replace("\\","\\\\").replace("`","\\`").replace("${","\\${")[:300000]

    return f"""<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#080b14;font-family:'IBM Plex Sans',sans-serif;color:#ccc;font-size:13px;padding:12px}}
::-webkit-scrollbar{{width:5px}}::-webkit-scrollbar-track{{background:#0a0c14}}::-webkit-scrollbar-thumb{{background:#2a2d3a;border-radius:3px}}
.stat-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:14px}}
.sc{{background:#0f1117;border:1px solid #1e2030;border-radius:8px;padding:12px;text-align:center}}
.sn{{font-size:20px;font-weight:600;font-family:'IBM Plex Mono',monospace}}
.sl2{{font-size:10px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.08em}}
.top-grid{{display:grid;grid-template-columns:1.3fr 1fr;gap:12px;height:460px;margin-bottom:12px}}
.vwrap{{border:1px solid #1e2030;border-radius:10px;overflow:hidden;position:relative;background:#080b14}}
#viewer{{width:100%;height:100%}}
.vhint{{position:absolute;bottom:10px;left:50%;transform:translateX(-50%);background:#0f1117cc;border:1px solid #1e2030;border-radius:20px;padding:5px 14px;font-size:10px;font-family:'IBM Plex Mono',monospace;color:#444;white-space:nowrap;pointer-events:none}}
.vtt{{position:absolute;top:10px;left:10px;background:#0f1117ee;border:1px solid #2a2d3a;border-radius:6px;padding:8px 12px;font-size:11px;display:none;pointer-events:none;z-index:10;max-width:200px;line-height:1.6;font-family:'IBM Plex Mono',monospace}}
.ipanel{{border:1px solid #1e2030;border-radius:10px;padding:14px;height:100%;overflow-y:auto;background:#0a0c14}}
.ph{{color:#2a2d3a;font-family:'IBM Plex Mono',monospace;font-size:11px;text-align:center;padding:60px 20px;line-height:3}}
.legend{{display:flex;gap:16px;flex-wrap:wrap;padding:8px 0 12px}}
.li{{display:flex;align-items:center;gap:6px;font-size:11px;color:#555}}
.ld{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
.section{{background:#0a0c14;border:1px solid #1e2030;border-radius:10px;padding:14px;margin-bottom:12px}}
.sl{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;padding-bottom:5px;border-bottom:1px solid #1a1d2e;margin:10px 0 7px}}
.sl:first-child{{margin-top:0}}
.drow{{display:flex;gap:8px;padding:5px 0;border-bottom:1px solid #0d0f1a;font-size:11px;line-height:1.5}}
.dl{{color:#3a3d5a;min-width:80px;font-size:10px;font-family:'IBM Plex Mono',monospace;flex-shrink:0;padding-top:1px}}
.dv{{color:#bbb;flex:1}}
.badge{{display:inline-block;padding:3px 12px;border-radius:20px;font-size:9px;font-weight:600;letter-spacing:0.1em;margin-bottom:8px;font-family:'IBM Plex Mono',monospace}}
.chip{{display:inline-block;background:#12141e;border:1px solid #1e2030;border-radius:3px;padding:1px 7px;font-size:9px;font-family:'IBM Plex Mono',monospace;color:#555;margin:2px 2px 0 0}}
.egrid{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:10px}}
.ecard{{background:#080b14;border:1px solid #1e2030;border-radius:8px;padding:10px;cursor:pointer;transition:border-color 0.15s}}
.ecard:hover{{border-color:#2a2d3a}}
.ecard.active{{border-color:#e24b4a;background:#0f0606}}
.ename{{font-size:12px;font-weight:600;color:#ddd;margin-bottom:3px}}
.emeta{{font-size:10px;font-family:'IBM Plex Mono',monospace}}
#edetail{{display:none;margin-top:12px;padding-top:12px;border-top:1px solid #1e2030;font-size:12px;color:#888;line-height:1.7}}
#edetail.vis{{display:block}}
</style>
</head>
<body>

<div class="stat-grid">
  <div class="sc"><div class="sn" style="color:#eee">{total}</div><div class="sl2">Residues</div></div>
  <div class="sc"><div class="sn" style="color:#e24b4a">{n_high}</div><div class="sl2">HIGH</div></div>
  <div class="sc"><div class="sn" style="color:#ef9f27">{n_med}</div><div class="sl2">MEDIUM</div></div>
  <div class="sc"><div class="sn" style="color:#378add">{n_low}</div><div class="sl2">LOW</div></div>
  <div class="sc"><div class="sn" style="color:#e24b4a;font-size:13px">{top_label}</div><div class="sl2">Top hit</div></div>
</div>

<div class="top-grid">
  <div class="vwrap">
    <div id="viewer"></div>
    <div class="vtt" id="vtt"></div>
    <div class="vhint">● Click any residue sphere for annotation</div>
  </div>
  <div class="ipanel" id="ipanel">
    <div class="ph">🔬<br><br>Click any residue<br>sphere on the structure<br>to load full annotation</div>
  </div>
</div>

<div class="legend">
  <div class="li"><div class="ld" style="background:#e24b4a"></div>Critical / HIGH</div>
  <div class="li"><div class="ld" style="background:#ef9f27"></div>Affected / MEDIUM</div>
  <div class="li"><div class="ld" style="background:#378add"></div>No effect / LOW</div>
  <div class="li"><div class="ld" style="background:#fff;border:1px solid #555"></div>Selected</div>
</div>

<div class="section">
  <div class="sl" style="margin-top:0">Experimental pathways — click to highlight affected residues</div>
  <div class="egrid" id="egrid"></div>
  <div id="edetail"></div>
</div>

<script>
const RESIDUES={res_json};
const EXPERIMENTS={exp_json};
const pdbData=`{pdb_esc}`;
let viewer,selResi=null,activeExp=null;

function gc(s){{return s==='critical'?'#e24b4a':s==='affected'?'#ef9f27':'#378add';}}
function dr(l,v){{return `<div class="drow"><span class="dl">${{l}}</span><span class="dv">${{v}}</span></div>`;}}

viewer=$3Dmol.createViewer('viewer',{{backgroundColor:'#080b14',antialias:true}});
viewer.addModel(pdbData,'pdb');

function applyStyles(exp){{
  viewer.setStyle({{}},{{cartoon:{{color:'#1a1d2e',opacity:0.4}}}});
  viewer.addStyle({{resi:'94-292'}},{{cartoon:{{color:'#1e2440',opacity:0.6}}}});
  Object.entries(RESIDUES).forEach(([resi,d])=>{{
    const r=parseInt(resi);
    let color=gc(d.status),radius=d.status==='critical'?0.9:d.status==='affected'?0.65:0.42,opacity=1;
    if(exp&&exp.affected){{
      if(exp.affected.includes(r)){{color=exp.color;radius=1.05;}}
      else{{radius*=0.3;opacity=0.1;}}
    }}
    viewer.addStyle({{resi:r}},{{sphere:{{color,radius,opacity}}}});
  }});
  if(selResi)viewer.addStyle({{resi:selResi}},{{sphere:{{color:'#ffffff',radius:1.2,opacity:1}}}});
  viewer.render();
}}

viewer.setHoverable({{}},true,
  atom=>{{
    if(!atom?.resi)return;
    const d=RESIDUES[atom.resi];if(!d)return;
    const c=gc(d.status);
    const tt=document.getElementById('vtt');
    tt.innerHTML=`<span style="color:${{c}};font-weight:700">${{d.label}}</span><br><span style="font-size:10px;color:#888">Pos ${{atom.resi}} · Score: ${{d.score}}</span><br><span style="font-size:10px;color:${{c}}">${{d.priority}}</span><br><span style="font-size:10px;color:#555">Click for details →</span>`;
    tt.style.display='block';
  }},
  ()=>{{document.getElementById('vtt').style.display='none';}}
);

viewer.setClickable({{}},true,atom=>{{
  if(!atom?.resi)return;
  const d=RESIDUES[atom.resi];if(!d)return;
  selResi=atom.resi;
  applyStyles(activeExp?EXPERIMENTS.find(e=>e.id===activeExp):null);
  showInfo(atom.resi,d);
}});

viewer.zoomTo({{resi:'94-292'}});
applyStyles(null);

function showInfo(resi,d){{
  const c=gc(d.status);
  const sl=d.status==='critical'?'CRITICAL — HIGH PRIORITY':d.status==='affected'?'AFFECTED BY CRITICAL':'NO SIGNIFICANT EFFECT';
  document.getElementById('ipanel').innerHTML=`
    <div>
      <span class="badge" style="background:${{c}}22;color:${{c}};border:0.5px solid ${{c}}66">${{sl}}</span>
      <p style="font-size:15px;font-weight:700;color:#eee;margin:0 0 2px;font-family:'IBM Plex Mono',monospace">Residue ${{resi}} — ${{d.label}}</p>
      <p style="font-size:11px;color:#444;margin:0 0 10px">${{d.expType}} · Score: <span style="color:${{c}};font-weight:600">${{d.score}}/1.00</span></p>
    </div>
    <div class="sl" style="margin-top:0">Structural annotation</div>
    ${{dr('Domain',d.domain)}}${{dr('Mechanism',d.mechanism)}}
    <div class="sl">Clinical database</div>
    ${{dr('ClinVar',d.clinvar)}}${{dr('COSMIC',d.cosmic)}}${{dr('Cancer types',d.cancer)}}
    <div class="sl">Therapeutic</div>
    ${{dr('Therapy',d.therapeutic)}}
    <div class="sl">Data sources</div>
    <span class="chip">Your CSV</span>
    ${{d.clinvar.includes('Pathogenic')?'<span class="chip">ClinVar</span>':''}}
    ${{d.cosmic.includes('%')?'<span class="chip">COSMIC v97</span>':''}}
    <span class="chip">PDB 2OCJ</span>`;
}}

const grid=document.getElementById('egrid');
EXPERIMENTS.forEach(exp=>{{
  const div=document.createElement('div');
  div.className='ecard';div.id='ec-'+exp.id;
  div.innerHTML=`<div class="ename">${{exp.name}}</div><div class="emeta" style="color:${{exp.color}}">${{exp.cat}}</div><div class="emeta">${{exp.dur}} · ${{exp.cost}}</div>`;
  div.onclick=()=>toggleExp(exp);
  grid.appendChild(div);
}});

function toggleExp(exp){{
  const det=document.getElementById('edetail');
  if(activeExp===exp.id){{
    activeExp=null;document.querySelectorAll('.ecard').forEach(c=>c.classList.remove('active'));
    det.classList.remove('vis');det.innerHTML='';applyStyles(null);return;
  }}
  activeExp=exp.id;
  document.querySelectorAll('.ecard').forEach(c=>c.classList.remove('active'));
  document.getElementById('ec-'+exp.id).classList.add('active');
  applyStyles(exp);
  const pills=(exp.affected||[]).map(r=>{{const d=RESIDUES[r];return`<span class="chip" style="color:${{exp.color}};border-color:${{exp.color}}55">${{d?d.label:'R'+r}}</span>`;}}).join('');
  det.innerHTML=`<strong style="color:${{exp.color}}">${{exp.name}}</strong> — ${{exp.note}}<br><br>Highlighted residues: ${{pills||'Based on your data'}}`;
  det.classList.add('vis');
}}
</script>
</body>
</html>"""


def render():
    st.markdown("## ⚗️ Protein Explorer")
    st.markdown("3D structure loaded from your triage run. Click any residue for full annotation.")
    st.divider()

    if "t_scored" not in st.session_state:
        st.info("👈 Run Triage first in the **Triage System** tab — the protein explorer will populate automatically.")
        return

    scored_df = st.session_state.t_scored

    with st.spinner("Loading protein structure..."):
        pdb_data = fetch_pdb("2OCJ")

    if not pdb_data:
        st.error("Could not load protein structure. Check your internet connection.")
        return

    html = build_html(scored_df, pdb_data)
    components.html(html, height=1100, scrolling=True)
