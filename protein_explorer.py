"""
protein_explorer.py — Protellect Protein Explorer v2
- Live UniProt API integration
- CSV upload → auto-fetch structure
- Mutation fluctuation animation
- Cell impact diagram on residue click
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import requests
from uniprot_api import (
    get_protein_name, get_gene_name, get_organism,
    get_sequence_length, get_residue_annotations,
    get_protein_function, get_disease_associations,
    get_clinvar_count, get_structure_for_uniprot,
)

TP53_ENRICHMENT = {
    175: {"status":"critical","clinvar":"Pathogenic · 847 submissions","cosmic":"~6% of all cancers","cancer_types":"Breast, lung, colorectal, ovarian","mechanism":"Disrupts zinc coordination at C176/H179/C238/C242 tetrahedral site. Causes global domain misfolding.","therapeutic":"APR-246 (eprenetapopt) — Phase III","cell_impact":"apoptosis_loss"},
    248: {"status":"critical","clinvar":"Pathogenic · 623 submissions","cosmic":"~3% of all cancers","cancer_types":"Colorectal, lung, pancreatic","mechanism":"Direct DNA contact residue. Abolishes sequence-specific DNA binding entirely.","therapeutic":"Synthetic lethality under investigation","cell_impact":"dna_damage_bypass"},
    273: {"status":"critical","clinvar":"Pathogenic · 512 submissions","cosmic":"~3% of all cancers","cancer_types":"Colorectal, lung, brain","mechanism":"DNA backbone phosphate contact. Loss reduces DNA-binding affinity >100-fold.","therapeutic":"Small molecule stabilizers experimental","cell_impact":"dna_damage_bypass"},
    249: {"status":"critical","clinvar":"Pathogenic · 298 submissions","cosmic":"~1.5% — enriched in liver cancer","cancer_types":"Liver (HCC), lung, esophageal","mechanism":"H2 helix structural mutation. Aflatoxin B1 mutational signature.","therapeutic":"No specific therapy","cell_impact":"proliferation"},
    245: {"status":"critical","clinvar":"Pathogenic · 187 submissions","cosmic":"~1.5% of cancers","cancer_types":"Breast, lung, sarcoma","mechanism":"Glycine essential for L3 loop geometry. Any side chain disrupts DNA approach.","therapeutic":"Structural correctors under investigation","cell_impact":"apoptosis_loss"},
    282: {"status":"critical","clinvar":"Pathogenic · 156 submissions","cosmic":"~1% of cancers","cancer_types":"Breast, colorectal, lung","mechanism":"R282 salt bridge with E271 stabilizes H2 helix. Tryptophan disrupts this.","therapeutic":"No approved targeted therapy","cell_impact":"apoptosis_loss"},
    176: {"status":"affected","clinvar":"Not directly pathogenic","cosmic":"N/A","cancer_types":"Secondary effect of R175H","mechanism":"Zinc ligand directly adjacent to R175. Geometry disrupted by R175H mutation propagation.","therapeutic":"APR-246 binds C176 directly as scaffold","cell_impact":"structural"},
    179: {"status":"affected","clinvar":"Uncertain significance","cosmic":"N/A","cancer_types":"N/A","mechanism":"Zinc-coordinating histidine. Indirectly destabilized by R175H through L2 loop changes.","therapeutic":"N/A","cell_impact":"structural"},
    220: {"status":"affected","clinvar":"Pathogenic · 89 submissions","cosmic":"~1% of cancers","cancer_types":"Breast, lung, ovarian","mechanism":"Creates druggable hydrophobic cavity. Thermodynamic destabilization without direct DNA contact loss.","therapeutic":"PC14586 (rezatapopt) — fills Y220C cavity, Phase II","cell_impact":"apoptosis_loss"},
}

CELL_IMPACT_DATA = {
    "apoptosis_loss": {
        "title": "Loss of Apoptosis Signaling",
        "description": "TP53 normally activates BAX, PUMA, and NOXA to trigger programmed cell death when DNA damage is detected. R175H abolishes this — damaged cells survive and accumulate further mutations.",
        "pathway": ["DNA damage detected", "R175H TP53 cannot bind BAX/PUMA promoters", "Apoptosis blocked", "Damaged cell survives", "Clonal expansion", "Tumour formation"],
        "color": "#FF4C4C",
        "cell_state": "cancer",
    },
    "dna_damage_bypass": {
        "title": "DNA Damage Checkpoint Bypass",
        "description": "TP53 normally halts the cell cycle at G1/S checkpoint via p21 activation, allowing DNA repair. Contact mutants like R248W cannot activate p21 — cells divide with unrepaired DNA.",
        "pathway": ["DNA double-strand break", "ATM/ATR activate mutant TP53", "p21 not activated (no DNA binding)", "G1/S checkpoint fails", "Cell divides with damaged DNA", "Genomic instability"],
        "color": "#FF8C00",
        "cell_state": "dividing",
    },
    "proliferation": {
        "title": "Uncontrolled Proliferation",
        "description": "Gain-of-function mutants like R249S actively promote cell growth by inhibiting tumour suppressors p63 and p73, while activating oncogenic transcription programs.",
        "pathway": ["R249S gains new protein interactions", "Inhibits p63/p73 tumour suppressors", "Activates MYC/VEGF oncogenes", "Cell proliferation accelerated", "Angiogenesis promoted", "Metastasis potential increased"],
        "color": "#CC44CC",
        "cell_state": "proliferating",
    },
    "structural": {
        "title": "Structural Propagation Effect",
        "description": "This residue is not mutated directly but its function is compromised by nearby critical mutations propagating through the protein fold.",
        "pathway": ["Adjacent critical mutation occurs", "Local geometry disrupted", "Structural propagation", "This residue function impaired", "Partial domain destabilization"],
        "color": "#FFA500",
        "cell_state": "stressed",
    },
}

EXPERIMENTS = [
    {"id":"thermal","name":"Thermal Shift","category":"Structural","duration":"2–3 days","cost":"~$300","affected_note":"Shows domain destabilization — R175H reduces Tm by ~8°C","affected":[175,176,179,220],"color":"#FF4C4C"},
    {"id":"emsa","name":"EMSA","category":"Functional","duration":"1–2 days","cost":"~$200","affected_note":"Shows loss of DNA binding — contact residues highlighted","affected":[175,248,273,245],"color":"#FF8C00"},
    {"id":"reporter","name":"Reporter Assay","category":"Functional","duration":"3–5 days","cost":"~$400","affected_note":"Shows transcriptional silence across all DNA-contact residues","affected":[175,176,248,273,249],"color":"#CC44CC"},
    {"id":"apr246","name":"APR-246 Rescue","category":"Therapeutic","duration":"5–7 days","cost":"~$800","affected_note":"Partial rescue — drug binds C176/C238, partially restores conformation","affected":[175,176,179,248],"color":"#4CA8FF"},
    {"id":"coip","name":"Co-IP Dom. Neg.","category":"Mechanistic","duration":"3–4 days","cost":"~$600","affected_note":"Dominant negative — R175H poisons WT p53 tetramers","affected":[175,248,273],"color":"#4CAF50"},
]


def build_cell_diagram_html(impact_key):
    impact = CELL_IMPACT_DATA.get(impact_key, CELL_IMPACT_DATA["apoptosis_loss"])
    color = impact["color"]
    pathway = impact["pathway"]
    state = impact["cell_state"]

    steps_html = ""
    for i, step in enumerate(pathway):
        steps_html += f"""
        <div style="display:flex;flex-wrap:wrap;align-items:center;margin-bottom:4px;opacity:0;animation:fadeIn 0.4s {i*0.25}s forwards">
            <div style="width:20px;height:20px;border-radius:50%;background:{color}22;color:{color};border:1px solid {color}44;display:flex;align-items:center;justify-content:center;font-size:9px;font-family:'IBM Plex Mono',monospace;font-weight:700;flex-shrink:0;margin-right:8px">{i+1}</div>
            <div style="font-size:11px;color:#ccc">{step}</div>
            {"<div style='width:100%;padding-left:28px;color:#333;font-size:14px;line-height:1'>↓</div>" if i < len(pathway)-1 else ""}
        </div>"""

    cell_anim = {"cancer":"cancer-pulse","dividing":"dividing-spin","proliferating":"proliferating-grow","stressed":"stressed-shake"}.get(state,"cancer-pulse")
    nucleus_color = {"cancer":"#FF4C4C","dividing":"#FF8C00","proliferating":"#CC44CC","stressed":"#FFA500"}.get(state,"#FF4C4C")

    return f"""
    <div style="background:#080b14;border-radius:10px;padding:16px;font-family:'IBM Plex Sans',sans-serif;">
    <style>
        @keyframes fadeIn {{ to {{ opacity:1; }} }}
        @keyframes cancer-pulse {{ 0%,100%{{transform:scale(1);}} 50%{{transform:scale(1.08);}} }}
        @keyframes dividing-spin {{ 0%{{transform:rotate(0deg);}} 100%{{transform:rotate(360deg);}} }}
        @keyframes proliferating-grow {{ 0%,100%{{transform:scale(1);}} 50%{{transform:scale(1.15);}} }}
        @keyframes stressed-shake {{ 0%,100%{{transform:translateX(0);}} 25%{{transform:translateX(-3px);}} 75%{{transform:translateX(3px);}} }}
    </style>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#444;margin-bottom:12px;padding-bottom:6px;border-bottom:1px solid #1a1d2e;">Cell-Level Impact</div>
    <div style="display:flex;gap:20px;align-items:flex-start">
        <div style="flex-shrink:0">
            <div style="text-align:center;margin-bottom:8px">
                <svg width="80" height="80" viewBox="0 0 80 80">
                    <ellipse cx="40" cy="40" rx="36" ry="32" fill="#0a2a0a" stroke="#2a4a2a" stroke-width="1.5"/>
                    <ellipse cx="40" cy="40" rx="14" ry="12" fill="#1a4a1a" stroke="#4CAF50" stroke-width="1.5"/>
                    <text x="40" y="44" text-anchor="middle" font-size="7" fill="#4CAF50" font-family="monospace">WT</text>
                </svg>
                <div style="font-size:9px;font-family:'IBM Plex Mono',monospace;color:#555;text-align:center;margin-top:4px">Normal Cell</div>
            </div>
            <div style="text-align:center;color:{color};font-size:18px;line-height:1;margin:4px 0">↓</div>
            <div style="text-align:center;font-size:9px;color:{color};font-family:'IBM Plex Mono',monospace;margin-bottom:8px">mutation</div>
            <div style="text-align:center">
                <svg width="80" height="80" viewBox="0 0 80 80" style="animation:{cell_anim} 2s ease-in-out infinite;transform-origin:center">
                    <ellipse cx="40" cy="40" rx="36" ry="32" fill="#2a0a0a" stroke="{color}" stroke-width="1.5" stroke-dasharray="4,2"/>
                    <ellipse cx="40" cy="40" rx="16" ry="14" fill="#3a0a0a" stroke="{color}" stroke-width="1.5"/>
                    <circle cx="22" cy="28" r="3" fill="{color}" opacity="0.6"/>
                    <circle cx="58" cy="52" r="2" fill="{color}" opacity="0.4"/>
                    <circle cx="30" cy="55" r="2.5" fill="{color}" opacity="0.5"/>
                    <text x="40" y="43" text-anchor="middle" font-size="7" fill="{color}" font-family="monospace">MUT</text>
                </svg>
                <div style="font-size:9px;font-family:'IBM Plex Mono',monospace;color:{color};text-align:center;margin-top:4px">Affected Cell</div>
            </div>
        </div>
        <div style="flex:1">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:{color};margin-bottom:8px">{impact["title"]}</div>
            <div style="font-size:11px;color:#888;line-height:1.7;margin-bottom:14px">{impact["description"]}</div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.12em;color:#444;margin-bottom:8px">Molecular Pathway</div>
            {steps_html}
        </div>
    </div>
    </div>"""


def build_explorer_html(pdb_data, residue_annotations, scored_df=None):
    residue_db = {}

    for pos, ann in residue_annotations.items():
        residue_db[pos] = {
            "label": f"Res{pos}", "status": "normal",
            "domain": ann.get("domain","Unknown region"),
            "features": ann.get("features",[]),
            "active_site": ann.get("active_site",False),
            "binding_site": ann.get("binding_site",False),
            "ptm": ann.get("ptm",""),
            "natural_variant": ann.get("natural_variant",[]),
            "source": ann.get("source","UniProt"),
            "mechanism": "", "clinvar": "No data", "cosmic": "No data",
            "cancer_types": "Not specifically associated",
            "therapeutic": "N/A", "effect_score": 0.0, "cell_impact": "structural",
        }

    if scored_df is not None:
        for _, row in scored_df.iterrows():
            pos = int(row["residue_position"])
            score = float(row.get("normalized_score", row.get("effect_score",0)))
            mutation = row.get("mutation", f"Res{pos}")
            priority = row.get("priority","LOW")
            status = {"HIGH":"critical","MEDIUM":"affected","LOW":"normal"}.get(priority,"normal")
            if pos not in residue_db:
                residue_db[pos] = {"domain":"Unknown","features":[],"active_site":False,"binding_site":False,"ptm":"","natural_variant":[],"source":"Experimental CSV","mechanism":"","clinvar":"Not queried","cosmic":"Not queried","cancer_types":"Not queried","therapeutic":"N/A","cell_impact":"apoptosis_loss" if status=="critical" else "structural"}
            residue_db[pos].update({"label":mutation,"status":status,"effect_score":round(score,3)})

    for pos, enrich in TP53_ENRICHMENT.items():
        if pos in residue_db:
            residue_db[pos].update(enrich)
        else:
            residue_db[pos] = {"label":f"R{pos}","domain":"DNA-binding domain","features":[],"active_site":False,"binding_site":False,"ptm":"","natural_variant":[],"source":"UniProt P04637 + ClinVar + COSMIC","effect_score":0.5,**enrich}

    residue_json = json.dumps(residue_db, default=str)
    exp_json = json.dumps(EXPERIMENTS)
    pdb_escaped = pdb_data.replace("\\","\\\\").replace("`","\\`").replace("${","\\${")[:300000]

    return f"""<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#080b14;font-family:'IBM Plex Sans',sans-serif;color:#ccc;font-size:13px;overflow-x:hidden}}
#layout{{display:grid;grid-template-columns:1.3fr 1fr;gap:14px;height:500px}}
#viewer-wrap{{position:relative;border:1px solid #1e2030;border-radius:10px;overflow:hidden}}
#viewer{{width:100%;height:100%}}
#tooltip{{position:absolute;top:10px;left:10px;background:#0f1117ee;border:1px solid #2a2d3a;border-radius:6px;padding:8px 12px;font-size:11px;font-family:'IBM Plex Mono',monospace;color:#ccc;pointer-events:none;display:none;z-index:100;max-width:210px;line-height:1.5}}
#click-hint{{position:absolute;bottom:10px;left:50%;transform:translateX(-50%);background:#0f1117cc;border:1px solid #2a2d3a;border-radius:20px;padding:5px 14px;font-size:10px;font-family:'IBM Plex Mono',monospace;color:#444;white-space:nowrap}}
#info-panel{{background:#0a0c14;border:1px solid #1e2030;border-radius:10px;padding:14px;overflow-y:auto;display:flex;flex-direction:column;gap:8px}}
.placeholder{{color:#2a2d3a;font-family:'IBM Plex Mono',monospace;font-size:11px;text-align:center;margin:auto;line-height:2.5}}
.slabel{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#444;padding-bottom:5px;border-bottom:1px solid #1a1d2e;margin-bottom:4px}}
.irow{{display:flex;gap:8px;padding:4px 0;border-bottom:1px solid #0f1020;font-size:11px}}
.ilbl{{color:#444;min-width:90px;font-family:'IBM Plex Mono',monospace;font-size:10px;flex-shrink:0;padding-top:1px}}
.ival{{color:#aaa;line-height:1.5}}
.chip{{display:inline-block;background:#12141e;border:1px solid #1e2030;border-radius:3px;padding:1px 6px;font-size:9px;font-family:'IBM Plex Mono',monospace;color:#555;margin:2px 2px 2px 0}}
.badge{{display:inline-block;padding:2px 10px;border-radius:20px;font-size:9px;font-family:'IBM Plex Mono',monospace;font-weight:600;letter-spacing:0.1em}}
#legend{{display:flex;gap:20px;padding:8px 0;flex-wrap:wrap}}
.li{{display:flex;align-items:center;gap:6px;font-size:11px;color:#555}}
.ld{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
#anim-section{{margin-top:12px}}
#anim-container{{background:#0a0c14;border:1px solid #1e2030;border-radius:8px;padding:14px}}
.exp-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:8px}}
.ecard{{background:#0a0c14;border:1px solid #1e2030;border-radius:8px;padding:10px;cursor:pointer;transition:all 0.15s}}
.ecard:hover{{border-color:#3a3d5a}}
.ecard.active{{border-color:#FF4C4C;background:#120808}}
.ename{{font-size:11px;font-weight:600;color:#ddd;margin-bottom:3px}}
.emeta{{font-size:10px;font-family:'IBM Plex Mono',monospace}}
.cat-Structural{{color:#4CA8FF}}.cat-Functional{{color:#FFA500}}.cat-Therapeutic{{color:#4CAF50}}.cat-Mechanistic{{color:#CC88FF}}
#exp-detail{{display:none;margin-top:10px;background:#0a0c14;border:1px solid #1e2030;border-radius:8px;padding:14px}}
#exp-detail.vis{{display:block}}
.exp-detail-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:10px}}
@keyframes wobble{{0%,100%{{transform:translateY(0)}}25%{{transform:translateY(-4px)}}75%{{transform:translateY(3px)}}}}
@keyframes glow-red{{0%,100%{{filter:drop-shadow(0 0 3px #FF4C4C)}}50%{{filter:drop-shadow(0 0 10px #FF4C4C)}}}}
.mutant-wobble{{animation:wobble 1.5s ease-in-out infinite,glow-red 1.5s ease-in-out infinite}}
</style>
</head>
<body>
<div id="layout">
  <div id="viewer-wrap">
    <div id="viewer"></div>
    <div id="tooltip"></div>
    <div id="click-hint">● Click any residue sphere for full annotation</div>
  </div>
  <div id="info-panel"><div class="placeholder">🔬<br>Click any residue<br>on the structure<br>to load details</div></div>
</div>
<div id="legend">
  <div class="li"><div class="ld" style="background:#FF4C4C"></div>Critical hotspot</div>
  <div class="li"><div class="ld" style="background:#FFA500"></div>Affected by critical</div>
  <div class="li"><div class="ld" style="background:#4CA8FF"></div>No significant effect</div>
  <div class="li"><div class="ld" style="background:#fff"></div>Selected</div>
</div>
<div id="anim-section">
  <div id="anim-container">
    <div class="slabel">Mutation Fluctuation Model</div>
    <div id="anim-content"><div style="color:#2a2d3a;font-size:11px;font-family:'IBM Plex Mono',monospace;text-align:center;padding:20px 0">Click a residue to see structural fluctuation animation</div></div>
  </div>
</div>
<div style="margin-top:12px">
  <div class="slabel">Experimental Pathways</div>
  <div class="exp-grid" id="exp-grid"></div>
  <div id="exp-detail"></div>
</div>
<script>
const RESIDUES={residue_json};
const EXPERIMENTS={exp_json};
const pdbData=`{pdb_escaped}`;
let viewer,selectedResi=null,activeExp=null;
viewer=$3Dmol.createViewer('viewer',{{backgroundColor:'#080b14',antialias:true}});
viewer.addModel(pdbData,'pdb');
function getColor(s){{return s==='critical'?'#FF4C4C':s==='affected'?'#FFA500':'#4CA8FF'}}
function applyStyles(exp){{
  viewer.setStyle({{}},{{cartoon:{{color:'#1a1d2e',opacity:0.4}}}});
  viewer.addStyle({{resi:'94-292'}},{{cartoon:{{color:'#1e2440',opacity:0.6}}}});
  for(const[resi,d] of Object.entries(RESIDUES)){{
    const r=parseInt(resi);
    let color=getColor(d.status),radius=d.status==='critical'?0.85:d.status==='affected'?0.65:0.42,opacity=1.0;
    if(exp){{if(exp.affected.includes(r)){{color=exp.color;radius=1.0}}else{{radius*=0.4;opacity=0.15}}}}
    viewer.addStyle({{resi:r}},{{sphere:{{color,radius,opacity}}}});
  }}
  if(selectedResi)viewer.addStyle({{resi:selectedResi}},{{sphere:{{color:'#ffffff',radius:1.1,opacity:1.0}}}});
  viewer.render();
}}
viewer.setHoverable({{}},true,function(atom){{
  if(!atom?.resi)return;
  const d=RESIDUES[atom.resi];const tt=document.getElementById('tooltip');
  if(d){{const c=getColor(d.status);tt.innerHTML='<span style="color:'+c+';font-weight:700">'+d.label+'</span><br><span style="color:#888;font-size:10px">Residue '+atom.resi+' · Score: '+d.effect_score+'</span><br><span style="color:#555;font-size:10px">Click for details →</span>';tt.style.display='block';}}
}},function(){{document.getElementById('tooltip').style.display='none';}});
viewer.setClickable({{}},true,function(atom){{
  if(!atom?.resi)return;const d=RESIDUES[atom.resi];if(!d)return;
  selectedResi=atom.resi;
  applyStyles(activeExp?EXPERIMENTS.find(e=>e.id===activeExp):null);
  showInfo(atom.resi,d);showAnim(atom.resi,d);
}});
viewer.zoomTo({{resi:'94-292'}});applyStyles(null);
function row(l,v){{return '<div class="irow"><span class="ilbl">'+l+'</span><span class="ival">'+v+'</span></div>';}}
function showInfo(resi,d){{
  const c=getColor(d.status);
  const sLabel=d.status==='critical'?'CRITICAL':d.status==='affected'?'AFFECTED BY CRITICAL':'NO SIGNIFICANT EFFECT';
  const feats=(d.features||[]).slice(0,4).map(f=>'<span class="chip">'+f+'</span>').join('');
  const sources=[d.source].flat().map(s=>'<span class="chip">'+s+'</span>').join('');
  const variants=(d.natural_variant||[]).slice(0,2).join(', ')||'None documented';
  document.getElementById('info-panel').innerHTML=`
    <div><div class="badge" style="background:${{c}}22;color:${{c}};border:1px solid ${{c}}44;margin-bottom:8px">${{sLabel}}</div>
    <div style="font-size:16px;font-weight:700;color:#eee;margin-bottom:2px">Residue ${{resi}} — ${{d.label}}</div></div>
    <div><div class="slabel">Annotation</div>
    ${{row('Domain',d.domain)}}${{row('Mechanism',d.mechanism||'—')}}${{row('ClinVar',d.clinvar||'—')}}
    ${{row('COSMIC',d.cosmic||'—')}}${{row('Cancer types',d.cancer_types||'—')}}
    ${{row('Therapeutic',d.therapeutic||'N/A')}}${{row('Effect score',d.effect_score+' / 1.00')}}
    ${{row('Active site',d.active_site?'✓ Yes':'No')}}${{row('Binding site',d.binding_site?'✓ Yes':'No')}}
    ${{row('Natural variants',variants)}}</div>
    ${{feats?'<div><div class="slabel">Features</div><div style="margin-top:4px">'+feats+'</div></div>':''}}
    <div><div class="slabel">Data Sources</div><div style="margin-top:4px">${{sources}}</div></div>`;
}}
function showAnim(resi,d){{
  const c=getColor(d.status);const isHigh=d.status==='critical';
  const svgW=540;const total=20;const mutPos=10;const spacing=svgW/(total+1);
  let wt='',mut='';
  for(let i=0;i<total;i++){{
    const x=(i+1)*spacing;const isMut=(i===mutPos);
    const col=isMut?c:'#2a2d3a';const r=isMut?10:6;
    wt+=`<circle cx="${{x}}" cy="30" r="6" fill="#0a2a0a" stroke="#4CAF50" stroke-width="1"/>`;
    if(i<total-1)wt+=`<line x1="${{x+6}}" y1="30" x2="${{(i+2)*spacing-6}}" y2="30" stroke="#2a4a2a" stroke-width="1.5"/>`;
    mut+=`<circle cx="${{x}}" cy="30" r="${{r}}" fill="${{isMut?c+'22':'#0a0c14'}}" stroke="${{col}}" stroke-width="${{isMut?2:1}}"${{isMut?' class="mutant-wobble"':''}}/>`;
    if(i<total-1)mut+=`<line x1="${{x+(isMut?10:6)}}" y1="30" x2="${{(i+2)*spacing-6}}" y2="30" stroke="${{isMut?c:'#2a2d3a'}}" stroke-width="1.5"/>`;
  }}
  const effects=[
    {{label:'Zinc coordination',wt:100,mut:isHigh?8:70}},
    {{label:'DNA binding affinity',wt:100,mut:isHigh?3:55}},
    {{label:'Thermal stability',wt:100,mut:isHigh?30:75}},
    {{label:'Transcriptional activity',wt:100,mut:isHigh?2:60}},
  ];
  const bars=effects.map(e=>`<div style="margin-bottom:10px">
    <div style="display:flex;justify-content:space-between;font-size:10px;font-family:'IBM Plex Mono',monospace;color:#666;margin-bottom:4px">
      <span>${{e.label}}</span><span style="color:${{c}}">${{e.mut}}% of WT</span></div>
    <div style="background:#1a1d2e;border-radius:3px;height:6px;overflow:hidden">
      <div style="height:100%;width:${{e.mut}}%;background:${{c}};border-radius:3px;transition:width 1s ease"></div>
    </div></div>`).join('');
  document.getElementById('anim-content').innerHTML=`
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
      <div>
        <div style="font-size:10px;font-family:'IBM Plex Mono',monospace;color:#4CAF50;margin-bottom:6px">WT PROTEIN CHAIN</div>
        <svg width="100%" height="60" viewBox="0 0 ${{svgW}} 60" style="background:#0a0c14;border-radius:6px">${{wt}}</svg>
        <div style="font-size:10px;font-family:'IBM Plex Mono',monospace;color:${{c}};margin-top:12px;margin-bottom:6px">MUTANT — ${{d.label}} (pulsing = instability)</div>
        <svg width="100%" height="60" viewBox="0 0 ${{svgW}} 60" style="background:#0a0c14;border-radius:6px">${{mut}}</svg>
      </div>
      <div>
        <div style="font-size:10px;font-family:'IBM Plex Mono',monospace;color:#444;margin-bottom:10px">FUNCTIONAL IMPACT vs WILD-TYPE</div>
        ${{bars}}
      </div>
    </div>`;
}}
const grid=document.getElementById('exp-grid');
EXPERIMENTS.forEach(exp=>{{
  const c=document.createElement('div');c.className='ecard';c.id='exp-'+exp.id;
  c.innerHTML='<div class="ename">'+exp.name+'</div><div class="emeta"><span class="cat-'+exp.category+'">'+exp.category+'</span><br>'+exp.duration+' · '+exp.cost+'</div>';
  c.onclick=()=>toggleExp(exp);grid.appendChild(c);
}});
function toggleExp(exp){{
  const det=document.getElementById('exp-detail');
  if(activeExp===exp.id){{activeExp=null;document.querySelectorAll('.ecard').forEach(c=>c.classList.remove('active'));det.classList.remove('vis');det.innerHTML='';applyStyles(null);return;}}
  activeExp=exp.id;document.querySelectorAll('.ecard').forEach(c=>c.classList.remove('active'));
  document.getElementById('exp-'+exp.id).classList.add('active');applyStyles(exp);
  const pills=exp.affected.map(r=>{{const d=RESIDUES[r];return'<span class="chip" style="color:'+exp.color+';border-color:'+exp.color+'44">'+(d?d.label:'R'+r)+'</span>';}}).join('');
  det.innerHTML=`<div class="slabel">${{exp.name}} — ${{exp.category}}</div>
    <div class="exp-detail-grid"><div>${{row('Note',exp.affected_note)}}${{row('Duration',exp.duration)}}${{row('Cost',exp.cost)}}</div>
    <div><div style="font-size:10px;color:#555;margin-bottom:6px">Highlighted residues:</div>${{pills}}</div></div>`;
  det.classList.add('vis');
}}
</script></body></html>"""


def render(uploaded_csv=None):
    st.markdown("## ⚗️ Protein Explorer")
    st.markdown("Enter any UniProt ID — live API fetches structure, annotations, ClinVar variants, and disease associations automatically.")
    st.divider()

    col1, col2 = st.columns([1,1], gap="large")
    with col1:
        st.markdown("##### UniProt ID")
        uniprot_id = st.text_input("UniProt ID", value="P04637", placeholder="e.g. P04637", label_visibility="collapsed")
        st.caption("Fetches from UniProt + AlphaFold/PDB automatically")
    with col2:
        st.markdown("##### Upload Experimental CSV (optional)")
        csv_file = st.file_uploader("CSV", type="csv", label_visibility="collapsed")
        st.caption("Columns: residue_position, effect_score, mutation")

    run = st.button("🔬 Load Protein", type="primary")

    if not run and "explorer_data" not in st.session_state:
        st.info("Enter a UniProt ID and click Load to fetch live data.")
        return

    if run:
        with st.spinner(f"Fetching live data for {uniprot_id} from UniProt, AlphaFold, PDB..."):
            protein_name  = get_protein_name(uniprot_id)
            gene_name     = get_gene_name(uniprot_id)
            organism      = get_organism(uniprot_id)
            seq_len       = get_sequence_length(uniprot_id)
            function_txt  = get_protein_function(uniprot_id)
            diseases      = get_disease_associations(uniprot_id)
            annotations   = get_residue_annotations(uniprot_id)
            clinvar_count = get_clinvar_count(gene_name) if gene_name else 0
            pdb_data, pdb_src = get_structure_for_uniprot(uniprot_id)

        scored_df = None
        if csv_file:
            from scorer import score_residues, validate_dataframe
            df_raw = pd.read_csv(csv_file)
            valid, err = validate_dataframe(df_raw)
            if valid:
                scored_df = score_residues(df_raw)
            else:
                st.error(f"CSV error: {err}")

        st.session_state.explorer_data = dict(
            protein_name=protein_name, gene_name=gene_name, organism=organism,
            seq_len=seq_len, function_txt=function_txt, diseases=diseases,
            annotations=annotations, clinvar_count=clinvar_count,
            pdb_data=pdb_data, pdb_src=pdb_src, scored_df=scored_df, uniprot_id=uniprot_id,
        )

    d = st.session_state.get("explorer_data", {})
    if not d:
        return

    pdb_data    = d.get("pdb_data")
    scored_df   = d.get("scored_df")
    annotations = d.get("annotations", {})

    # ── Stat cards ─────────────────────────────────────────────────────────────
    c1,c2,c3,c4,c5 = st.columns(5)
    def card(col, val, label, color="#eee"):
        col.markdown(f"""<div style="background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;padding:14px;text-align:center">
            <div style="font-size:1.3rem;font-weight:700;font-family:'IBM Plex Mono',monospace;color:{color}">{val}</div>
            <div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;color:#555;margin-top:4px">{label}</div>
        </div>""", unsafe_allow_html=True)

    card(c1, d.get("gene_name","—"), "Gene", "#FF4C4C")
    card(c2, d.get("seq_len","—"), "Residues")
    card(c3, len(annotations), "Annotated Sites", "#4CA8FF")
    card(c4, d.get("clinvar_count","—"), "ClinVar Variants", "#FFA500")
    card(c5, d.get("pdb_src","—"), "Structure Source", "#4CAF50")

    if d.get("function_txt"):
        st.markdown(f"""<div style="background:#0a0c14;border:1px solid #1e2030;border-radius:8px;padding:12px 16px;margin:12px 0;font-size:0.82rem;color:#888;line-height:1.7">
            <span style="font-family:'IBM Plex Mono',monospace;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.12em;color:#444;">UniProt Function — </span>
            {d["function_txt"][:400]}{'...' if len(d.get("function_txt",""))>400 else ''}
        </div>""", unsafe_allow_html=True)

    if d.get("diseases"):
        names = ", ".join([x["name"] for x in d["diseases"][:5]])
        st.markdown(f"""<div style="background:#150a0a;border:1px solid #3a1a1a;border-radius:8px;padding:10px 16px;font-size:0.8rem;color:#888">
            <span style="color:#FF4C4C;font-family:'IBM Plex Mono',monospace;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.12em;">Disease Associations — </span>{names}
        </div>""", unsafe_allow_html=True)

    st.divider()

    if pdb_data:
        html = build_explorer_html(pdb_data, annotations, scored_df)
        components.html(html, height=980, scrolling=True)
    else:
        st.error("Could not fetch protein structure. Check the UniProt ID.")

    # ── Cell Impact ─────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 🔬 Cell-Level Impact — What Happens to the Cell")
    st.markdown("Select a mutation type to see the downstream cellular consequence:")

    impact_cols = st.columns(4)
    impact_keys = list(CELL_IMPACT_DATA.keys())
    impact_labels = ["Apoptosis Loss (R175H)", "DNA Checkpoint Bypass (R273H)", "Gain of Function (R249S)", "Structural Propagation"]

    if "selected_impact" not in st.session_state:
        st.session_state.selected_impact = "apoptosis_loss"

    for col, key, label in zip(impact_cols, impact_keys, impact_labels):
        with col:
            is_sel = st.session_state.selected_impact == key
            if st.button(label, key=f"impact_{key}", type="primary" if is_sel else "secondary", use_container_width=True):
                st.session_state.selected_impact = key
                st.rerun()

    components.html(build_cell_diagram_html(st.session_state.selected_impact), height=340, scrolling=False)
