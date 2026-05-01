"""protein_explorer.py — Tab 3: interactive 3D viewer with click-to-annotate"""

import streamlit as st
import streamlit.components.v1 as components
import json, requests, base64
from pathlib import Path

_lp = Path("/mnt/user-data/uploads/1777622887238_image.png")
LOGO_B64 = ("data:image/png;base64," + base64.b64encode(_lp.read_bytes()).decode()) if _lp.exists() else None

HOTSPOTS = {
    175: {"clinvar":"Pathogenic · 847 submissions","cosmic":"~6% of all cancers","cancer":"Breast, lung, colorectal, ovarian","mechanism":"Disrupts zinc coordination at C176/H179/C238/C242. Global misfolding of DNA-binding domain.","therapeutic":"APR-246 (eprenetapopt) — Phase III","domain":"DNA-binding domain (L2 loop) — zinc coordination"},
    248: {"clinvar":"Pathogenic · 623 submissions","cosmic":"~3% of all cancers","cancer":"Colorectal, lung, pancreatic","mechanism":"Direct DNA contact residue. Abolishes sequence-specific DNA binding.","therapeutic":"Synthetic lethality under investigation","domain":"DNA-binding domain (L3 loop) — DNA contact"},
    273: {"clinvar":"Pathogenic · 512 submissions","cosmic":"~3% of all cancers","cancer":"Colorectal, lung, brain","mechanism":"DNA backbone phosphate contact. Loss reduces affinity >100-fold.","therapeutic":"Small molecule stabilizers experimental","domain":"DNA-binding domain (S10 strand) — backbone contact"},
    249: {"clinvar":"Pathogenic · 298 submissions","cosmic":"~1.5% — HCC enriched","cancer":"Liver (HCC), lung, esophageal","mechanism":"H2 helix structural mutation. Aflatoxin B1 mutational signature.","therapeutic":"No specific therapy","domain":"DNA-binding domain (H2 helix)"},
    245: {"clinvar":"Pathogenic · 187 submissions","cosmic":"~1.5% of cancers","cancer":"Breast, lung, sarcoma","mechanism":"Glycine essential for L3 loop geometry. Any side chain disrupts DNA approach.","therapeutic":"Structural correctors under investigation","domain":"DNA-binding domain (L3 loop)"},
    282: {"clinvar":"Pathogenic · 156 submissions","cosmic":"~1% of cancers","cancer":"Breast, colorectal, lung","mechanism":"R282 salt bridge with E271 stabilises H2 helix. Tryptophan disrupts this.","therapeutic":"No approved targeted therapy","domain":"DNA-binding domain (H2 helix)"},
    220: {"clinvar":"Pathogenic · 89 submissions","cosmic":"~1% of cancers","cancer":"Breast, lung, ovarian","mechanism":"Creates druggable hydrophobic cavity. Thermodynamic destabilisation.","therapeutic":"PC14586 (rezatapopt) — Phase II","domain":"DNA-binding domain (S7-S8 loop)"},
    176: {"clinvar":"Not directly pathogenic","cosmic":"Secondary effect","cancer":"Affected by R175H","mechanism":"Zinc ligand adjacent to R175. Geometry disrupted by R175H propagation.","therapeutic":"APR-246 binds C176 as scaffold","domain":"DNA-binding domain — zinc coordination"},
}

EXPERIMENTS = [
    {"id":"thermal","name":"Thermal Shift","cat":"Structural","dur":"2–3 days","cost":"~$300","color":"#FF4C4C","note":"Measures thermostability. HIGH mutations reduce Tm by 6–12°C vs WT.","affected":[175,176,220]},
    {"id":"emsa","name":"EMSA","cat":"Functional","dur":"1–2 days","cost":"~$200","color":"#FFA500","note":"Directly measures DNA binding. HIGH mutations show complete loss of binding.","affected":[175,248,273,245]},
    {"id":"reporter","name":"Reporter Assay","cat":"Functional","dur":"3–5 days","cost":"~$400","color":"#9370DB","note":"Measures p21/MDM2/PUMA transactivation in cells.","affected":[175,248,273,249]},
    {"id":"apr246","name":"APR-246 Rescue","cat":"Therapeutic","dur":"5–7 days","cost":"~$800","color":"#4CA8FF","note":"Tests whether APR-246 can refold structural mutants.","affected":[175,176,248]},
    {"id":"coip","name":"Co-IP Dom. Neg.","cat":"Mechanistic","dur":"3–4 days","cost":"~$600","color":"#4CAF50","note":"Confirms dominant negative suppression — mutant poisoning WT p53.","affected":[175,248,273]},
]


@st.cache_data(show_spinner=False)
def fetch_pdb():
    try:
        r = requests.get("https://files.rcsb.org/download/2OCJ.pdb", timeout=15)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def build_html(scored_df, pdb_data):
    residues = {}
    for _, row in scored_df.iterrows():
        pos   = int(row["residue_position"])
        score = round(float(row.get("normalized_score", row.get("effect_score", 0))), 3)
        label = str(row.get("mutation", f"Res{pos}"))
        if label in ("nan", ""):
            label = f"Res{pos}"
        pri   = str(row.get("priority", "LOW"))
        exp   = str(row.get("experiment_type", ""))
        stat  = {"HIGH":"critical","MEDIUM":"affected","LOW":"normal"}[pri]
        hs    = HOTSPOTS.get(pos, {})
        residues[pos] = {
            "label":label,"status":stat,"priority":pri,"score":score,
            "expType":exp if exp not in ("nan","") else "",
            "domain":      hs.get("domain",      "Unknown — Phase 2 will annotate"),
            "mechanism":   hs.get("mechanism",   "From experimental data."),
            "clinvar":     hs.get("clinvar",      "Not queried"),
            "cosmic":      hs.get("cosmic",       "Not queried"),
            "cancer":      hs.get("cancer",       "Not queried"),
            "therapeutic": hs.get("therapeutic",  "Consult clinical database"),
        }

    res_json = json.dumps(residues, default=str)
    exp_json = json.dumps(EXPERIMENTS)
    esc = pdb_data.replace("\\","\\\\").replace("`","\\`").replace("${","\\${")[:270000]

    n_high = sum(1 for d in residues.values() if d["priority"]=="HIGH")
    n_med  = sum(1 for d in residues.values() if d["priority"]=="MEDIUM")
    n_low  = sum(1 for d in residues.values() if d["priority"]=="LOW")
    top    = max(residues.items(), key=lambda x: x[1]["score"], default=(0,{"label":"—","score":"—"}))

    logo_tag = f'<img src="{LOGO_B64}" style="height:40px;object-fit:contain;border-radius:7px">' if LOGO_B64 else "🧬"

    return f"""<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#080b14;font-family:'Inter',sans-serif;color:#ccc;font-size:13px;padding:14px}}
::-webkit-scrollbar{{width:5px}}::-webkit-scrollbar-track{{background:#0a0c14}}::-webkit-scrollbar-thumb{{background:#2a2d3a;border-radius:3px}}

.header{{display:flex;align-items:center;gap:12px;margin-bottom:16px}}
.title{{font-family:'IBM Plex Mono',monospace;font-size:18px;font-weight:700;color:#eee}}
.sub{{font-size:12px;color:#555}}

.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:14px}}
.sc{{background:#0f1117;border:1px solid #1e2030;border-radius:8px;padding:12px;text-align:center}}
.sn{{font-size:1.3rem;font-weight:600;font-family:'IBM Plex Mono',monospace}}
.sl{{font-size:10px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.08em}}

.viewer-grid{{display:grid;grid-template-columns:1.4fr 1fr;gap:14px;height:480px;margin-bottom:14px}}
.vwrap{{border:1px solid #1e2030;border-radius:10px;overflow:hidden;position:relative;background:#080b14}}
#viewer{{width:100%;height:100%}}
#tt{{position:absolute;top:10px;left:10px;background:#0f1117ee;border:1px solid #2a2d3a;border-radius:6px;
    padding:8px 12px;font-size:11px;font-family:'IBM Plex Mono',monospace;display:none;pointer-events:none;
    z-index:10;max-width:200px;line-height:1.6}}
.hint{{position:absolute;bottom:10px;left:50%;transform:translateX(-50%);background:#0f1117cc;
      border:1px solid #1e2030;border-radius:20px;padding:5px 14px;font-size:10px;
      font-family:'IBM Plex Mono',monospace;color:#444;white-space:nowrap;pointer-events:none}}

.ipanel{{border:1px solid #1e2030;border-radius:10px;padding:14px;height:100%;overflow-y:auto;background:#0a0c14}}
.ph{{color:#2a2d3a;font-family:'IBM Plex Mono',monospace;font-size:11px;text-align:center;padding:60px 10px;line-height:3}}
.sl2{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;
     color:#3a3d5a;padding-bottom:5px;border-bottom:1px solid #1a1d2e;margin:10px 0 7px}}
.sl2:first-child{{margin-top:0}}
.drow{{display:flex;gap:8px;padding:5px 0;border-bottom:1px solid #0d0f1a;font-size:11px;line-height:1.5}}
.dl{{color:#3a3d5a;min-width:76px;font-size:10px;font-family:'IBM Plex Mono',monospace;flex-shrink:0;padding-top:1px}}
.dv{{color:#bbb;flex:1}}
.badge{{display:inline-block;padding:3px 12px;border-radius:20px;font-size:9px;font-weight:600;
       font-family:'IBM Plex Mono',monospace;letter-spacing:0.1em;margin-bottom:8px}}
.chip{{display:inline-block;background:#12141e;border:1px solid #1e2030;border-radius:3px;
      padding:1px 7px;font-size:9px;font-family:'IBM Plex Mono',monospace;color:#555;margin:2px 2px 0 0}}

.legend{{display:flex;gap:18px;flex-wrap:wrap;padding:6px 0 12px}}
.li{{display:flex;align-items:center;gap:6px;font-size:11px;color:#555}}
.ld{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}

.sec{{background:#0a0c14;border:1px solid #1e2030;border-radius:10px;padding:14px;margin-bottom:12px}}
.egrid{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:10px}}
.ecard{{background:#080b14;border:1px solid #1e2030;border-radius:8px;padding:10px;cursor:pointer;transition:border-color 0.15s}}
.ecard:hover{{border-color:#2a2d3a}}
.ecard.active{{border-color:#FF4C4C;background:#0f0606}}
.ename{{font-size:12px;font-weight:600;color:#ddd;margin-bottom:3px}}
.emeta{{font-size:10px;font-family:'IBM Plex Mono',monospace}}
#edet{{display:none;margin-top:10px;padding:12px;background:#0a0c14;border:1px solid #1e2030;border-radius:8px;font-size:12px;color:#888;line-height:1.7}}
#edet.vis{{display:block}}
</style>
</head>
<body>

<div class="header">
  {logo_tag}
  <div>
    <div class="title">Protein Explorer</div>
    <div class="sub">Click any residue sphere for full annotation · select an experiment to highlight targets</div>
  </div>
</div>

<div class="stats">
  <div class="sc"><div class="sn" style="color:#eee">{len(residues)}</div><div class="sl">Residues</div></div>
  <div class="sc"><div class="sn" style="color:#FF4C4C">{n_high}</div><div class="sl">HIGH</div></div>
  <div class="sc"><div class="sn" style="color:#FFA500">{n_med}</div><div class="sl">MEDIUM</div></div>
  <div class="sc"><div class="sn" style="color:#4CA8FF">{n_low}</div><div class="sl">LOW</div></div>
  <div class="sc"><div class="sn" style="color:#FF4C4C;font-size:13px">{top[1]["label"]}</div><div class="sl">Top hit</div></div>
</div>

<div class="viewer-grid">
  <div class="vwrap">
    <div id="viewer"></div>
    <div id="tt"></div>
    <div class="hint">● Click any sphere for full annotation</div>
  </div>
  <div class="ipanel" id="ipanel">
    <div class="ph">🔬<br><br>Click any residue<br>sphere on the structure<br>to load full annotation</div>
  </div>
</div>

<div class="legend">
  <div class="li"><div class="ld" style="background:#FF4C4C"></div>Critical / HIGH priority</div>
  <div class="li"><div class="ld" style="background:#FFA500"></div>Affected / MEDIUM priority</div>
  <div class="li"><div class="ld" style="background:#4CA8FF"></div>No effect / LOW priority</div>
  <div class="li"><div class="ld" style="background:#fff;border:1px solid #444"></div>Selected</div>
</div>

<div class="sec">
  <div class="sl2" style="margin-top:0">Experimental Pathways — click to highlight affected residues on structure</div>
  <div class="egrid" id="egrid"></div>
  <div id="edet"></div>
</div>

<script>
const RES={res_json};
const EXPS={exp_json};
const pdb=`{esc}`;
let viewer,sel=null,activeExp=null;

function gc(s){{return s==='critical'?'#FF4C4C':s==='affected'?'#FFA500':'#4CA8FF';}}
function dr(l,v){{return `<div class="drow"><span class="dl">${{l}}</span><span class="dv">${{v}}</span></div>`;}}

viewer=$3Dmol.createViewer('viewer',{{backgroundColor:'#080b14',antialias:true}});
viewer.addModel(pdb,'pdb');

function applyStyles(exp){{
  viewer.setStyle({{}},{{cartoon:{{color:'#1a1d2e',opacity:0.4}}}});
  viewer.addStyle({{resi:'94-292'}},{{cartoon:{{color:'#1e2440',opacity:0.6}}}});
  Object.entries(RES).forEach(([resi,d])=>{{
    const r=parseInt(resi),c=gc(d.status);
    let rad=d.status==='critical'?0.88:d.status==='affected'?0.62:0.40,op=1;
    if(exp){{
      if(exp.affected.includes(r)){{rad=1.05;}}
      else{{rad*=0.3;op=0.1;}}
    }}
    viewer.addStyle({{resi:r}},{{sphere:{{color:exp&&exp.affected.includes(r)?exp.color:c,radius:rad,opacity:op}}}});
  }});
  if(sel) viewer.addStyle({{resi:sel}},{{sphere:{{color:'#ffffff',radius:1.2,opacity:1}}}});
  viewer.render();
}}

viewer.setHoverable({{}},true,
  atom=>{{
    if(!atom?.resi)return;
    const d=RES[atom.resi];if(!d)return;
    const c=gc(d.status);
    const tt=document.getElementById('tt');
    tt.innerHTML=`<span style="color:${{c}};font-weight:700">${{d.label}}</span><br><span style="font-size:10px;color:#888">Pos ${{atom.resi}} · Score ${{d.score}}</span><br><span style="font-size:10px;color:${{c}}">${{d.priority}} PRIORITY</span><br><span style="font-size:10px;color:#555">Click for full annotation →</span>`;
    tt.style.display='block';
  }},
  ()=>document.getElementById('tt').style.display='none'
);

viewer.setClickable({{}},true,atom=>{{
  if(!atom?.resi)return;
  const d=RES[atom.resi];if(!d)return;
  sel=atom.resi;
  applyStyles(activeExp?EXPS.find(e=>e.id===activeExp):null);
  const c=gc(d.status);
  const sl=d.status==='critical'?'CRITICAL — HIGH PRIORITY':d.status==='affected'?'AFFECTED BY CRITICAL':'NO SIGNIFICANT EFFECT';
  const src='<span class="chip">Your CSV</span>'+(d.clinvar.includes('Pathogenic')?'<span class="chip">ClinVar</span>':'')+(d.cosmic.includes('%')?'<span class="chip">COSMIC v97</span>':'')+'<span class="chip">PDB 2OCJ</span>';
  document.getElementById('ipanel').innerHTML=`
    <div>
      <span class="badge" style="background:${{c}}22;color:${{c}};border:0.5px solid ${{c}}66">${{sl}}</span>
      <p style="font-size:15px;font-weight:700;color:#eee;margin:0 0 2px;font-family:'IBM Plex Mono',monospace">Res ${{atom.resi}} — ${{d.label}}</p>
      <p style="font-size:11px;color:#444;margin:0 0 10px">${{d.expType||'DMS'}} · Score: <span style="color:${{c}};font-weight:600">${{d.score}}/1.00</span></p>
    </div>
    <div class="sl2" style="margin-top:0">Structural</div>
    ${{dr('Domain',d.domain)}}${{dr('Mechanism',d.mechanism)}}
    <div class="sl2">Clinical</div>
    ${{dr('ClinVar',d.clinvar)}}${{dr('COSMIC',d.cosmic)}}${{dr('Cancer',d.cancer)}}
    <div class="sl2">Therapeutic</div>
    ${{dr('Therapy',d.therapeutic)}}
    <div class="sl2">Sources</div>
    <div style="margin-top:4px">${{src}}</div>`;
}});

viewer.zoomTo({{resi:'94-292'}});
applyStyles(null);

// Experiments
const grid=document.getElementById('egrid');
EXPS.forEach(exp=>{{
  const d=document.createElement('div');
  d.className='ecard';d.id='ec-'+exp.id;
  d.innerHTML=`<div class="ename">${{exp.name}}</div><div class="emeta" style="color:${{exp.color}}">${{exp.cat}}</div><div class="emeta">${{exp.dur}} · ${{exp.cost}}</div>`;
  d.onclick=()=>toggleExp(exp);
  grid.appendChild(d);
}});

function toggleExp(exp){{
  const det=document.getElementById('edet');
  if(activeExp===exp.id){{
    activeExp=null;document.querySelectorAll('.ecard').forEach(c=>c.classList.remove('active'));
    det.classList.remove('vis');det.innerHTML='';applyStyles(null);return;
  }}
  activeExp=exp.id;
  document.querySelectorAll('.ecard').forEach(c=>c.classList.remove('active'));
  document.getElementById('ec-'+exp.id).classList.add('active');
  applyStyles(exp);
  const pills=(exp.affected||[]).map(r=>{{const d=RES[r];return`<span class="chip" style="color:${{exp.color}};border-color:${{exp.color}}55">${{d?d.label:'R'+r}}</span>`;}}).join('');
  det.innerHTML=`<strong style="color:${{exp.color}}">${{exp.name}}</strong> — ${{exp.note}}<br><br>Highlighted residues: ${{pills||'Based on your data'}}`;
  det.classList.add('vis');
}}
</script>
</body>
</html>"""


def render():
    if LOGO_B64:
        st.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px"><img src="{LOGO_B64}" style="height:40px;object-fit:contain;border-radius:7px"><div><strong style="font-size:1.1rem">Protein Explorer</strong><p style="color:#555;font-size:0.83rem;margin:0">Click any residue for annotation · select experiments to highlight targets</p></div></div>', unsafe_allow_html=True)
    else:
        st.markdown("## ⚗️ Protein Explorer")
    st.divider()

    if "t_scored" not in st.session_state:
        st.info("👈 Run Triage first in the **Triage System** tab.")
        return

    with st.spinner("Loading structure..."):
        pdb = fetch_pdb()

    if not pdb:
        st.error("Could not load protein structure. Check internet connection.")
        return

    components.html(build_html(st.session_state.t_scored, pdb), height=1000, scrolling=True)
