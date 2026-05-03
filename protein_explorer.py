"""protein_explorer.py — Tab 3: universal protein structure viewer"""

import streamlit as st
import streamlit.components.v1 as components
import json, requests, base64
from pathlib import Path

try:
    from logo import LOGO_DATA_URL as LOGO_B64
except Exception:
    _lp = Path("/mnt/user-data/uploads/1777622887238_image.png")
    LOGO_B64 = ("data:image/png;base64," + base64.b64encode(_lp.read_bytes()).decode()) if _lp.exists() else None

HOTSPOTS = {
    175:{"clinvar":"Pathogenic · 847 submissions","cosmic":"~6% of all cancers","cancer":"Breast, lung, colorectal","mechanism":"Disrupts zinc coordination. Global misfolding of DNA-binding domain.","therapeutic":"APR-246 (eprenetapopt) — Phase III","domain":"DNA-binding domain (L2 loop) — zinc coordination"},
    248:{"clinvar":"Pathogenic · 623 submissions","cosmic":"~3% of all cancers","cancer":"Colorectal, lung, pancreatic","mechanism":"Direct DNA contact residue. Abolishes sequence-specific binding.","therapeutic":"Synthetic lethality under investigation","domain":"DNA-binding domain (L3 loop) — direct DNA contact"},
    273:{"clinvar":"Pathogenic · 512 submissions","cosmic":"~3% of all cancers","cancer":"Colorectal, lung, brain","mechanism":"DNA backbone phosphate contact. Loss reduces affinity >100-fold.","therapeutic":"Small molecule stabilizers experimental","domain":"DNA-binding domain (S10 strand)"},
    249:{"clinvar":"Pathogenic · 298 submissions","cosmic":"~1.5% — HCC","cancer":"Liver, lung, esophageal","mechanism":"H2 helix structural mutation. Aflatoxin signature.","therapeutic":"No specific therapy","domain":"DNA-binding domain (H2 helix)"},
    245:{"clinvar":"Pathogenic · 187 submissions","cosmic":"~1.5% of cancers","cancer":"Breast, lung, sarcoma","mechanism":"Glycine essential for L3 loop geometry. Steric clash with DNA.","therapeutic":"Structural correctors under investigation","domain":"DNA-binding domain (L3 loop)"},
    282:{"clinvar":"Pathogenic · 156 submissions","cosmic":"~1% of cancers","cancer":"Breast, colorectal, lung","mechanism":"R282 salt bridge disrupted. H2 helix unfolding.","therapeutic":"No approved therapy","domain":"DNA-binding domain (H2 helix)"},
    220:{"clinvar":"Pathogenic · 89 submissions","cosmic":"~1% of cancers","cancer":"Breast, lung, ovarian","mechanism":"Creates druggable hydrophobic cavity. Thermodynamic destabilisation.","therapeutic":"PC14586 (rezatapopt) — Phase II","domain":"DNA-binding domain (S7-S8 loop)"},
}

EXPERIMENTS = [
    {"id":"thermal","name":"Thermal Shift","cat":"Structural","dur":"2–3 days","cost":"~$300","color":"#FF4C4C","note":"Measures thermostability. HIGH mutations typically reduce Tm by 6–12°C vs WT.","affected":[175,176,220]},
    {"id":"emsa","name":"EMSA","cat":"Functional","dur":"1–2 days","cost":"~$200","color":"#FFA500","note":"Directly measures DNA/RNA binding. HIGH contact mutations show complete loss.","affected":[175,248,273,245]},
    {"id":"reporter","name":"Reporter Assay","cat":"Functional","dur":"3–5 days","cost":"~$400","color":"#9370DB","note":"Measures target pathway activation in cells.","affected":[175,248,273,249]},
    {"id":"apr246","name":"APR-246 Rescue","cat":"Therapeutic","dur":"5–7 days","cost":"~$800","color":"#4CA8FF","note":"Tests whether APR-246 can refold structural mutants.","affected":[175,176,248]},
    {"id":"coip","name":"Co-IP / Pulldown","cat":"Mechanistic","dur":"3–4 days","cost":"~$600","color":"#4CAF50","note":"Confirms dominant negative effect and binding partner disruption.","affected":[175,248,273]},
]


def build_html(scored_df, pdb_text, enrichment=None, protein_info=None):
    residues = {}
    pri_col  = "priority_final" if "priority_final" in scored_df.columns else "priority"

    # Auto-detect position range from data
    user_positions = [int(r["residue_position"]) for _, r in scored_df.iterrows()]
    min_pos, max_pos = min(user_positions), max(user_positions)

    # Determine if positions overlap with PDB structure
    # Parse actual residues present in PDB
    pdb_residues = set()
    if pdb_text:
        for line in pdb_text.split('\n'):
            if line.startswith('ATOM') or line.startswith('HETATM'):
                try:
                    pdb_residues.add(int(line[22:26].strip()))
                except Exception:
                    pass

    overlap = bool(pdb_residues and any(p in pdb_residues for p in user_positions))

    # Build remap if needed: spread user positions across PDB residue range
    pdb_range = sorted(pdb_residues) if pdb_residues else list(range(94, 293))
    remap = {}
    if not overlap and pdb_range:
        import numpy as np
        n = len(user_positions)
        indices = np.linspace(0, len(pdb_range)-1, min(n, len(pdb_range)), dtype=int)
        sorted_user = sorted(user_positions)
        for i, orig in enumerate(sorted_user):
            if i < len(indices):
                remap[orig] = pdb_range[int(indices[i])]

    # Position note
    if overlap:
        pos_note = ""
        zoom_resi = f"{min(pdb_range)}–{max(pdb_range)}"
    else:
        prot_name = (protein_info or {}).get("gene_name","") or "your protein"
        pos_note  = f"Note: data positions ({min_pos}–{max_pos}) remapped to available structure residues for visual reference."
        zoom_resi = f"{pdb_range[0]}–{pdb_range[-1]}" if pdb_range else "94-292"

    for _, row in scored_df.iterrows():
        pos   = int(row["residue_position"])
        score = round(float(row.get("normalized_score", 0)), 3)
        label = str(row.get("mutation", f"Pos{pos}"))
        if label in ("nan",""): label = f"Pos{pos}"
        pri   = str(row.get(pri_col,"LOW"))
        exp   = str(row.get("experiment_type",""))
        stat  = {"HIGH":"critical","MEDIUM":"affected","LOW":"normal"}.get(pri,"normal")
        hs    = HOTSPOTS.get(pos, {})

        # Get DB enrichment if available
        disp_domain = disp_mech = disp_clinvar = disp_cosmic = disp_cancer = disp_ther = None
        if enrichment:
            try:
                from db_enrichment import format_enrichment_for_display
                d = format_enrichment_for_display(enrichment, pos, label)
                disp_domain  = d.get("domain")
                disp_mech    = d.get("mechanism")
                disp_clinvar = d.get("clinvar")
                disp_cancer  = d.get("cancer")
                disp_ther    = d.get("therapeutic")
            except Exception:
                pass

        pdb_pos = remap.get(pos, pos) if not overlap else pos

        residues[pdb_pos] = {
            "orig_pos": pos, "label": label, "status": stat, "priority": pri,
            "score": score, "expType": exp if exp not in ("nan","") else "",
            "domain":    disp_domain or hs.get("domain",    f"Position {pos}"),
            "mechanism": disp_mech   or hs.get("mechanism", f"Effect score {score} from your experimental assay."),
            "clinvar":   disp_clinvar or hs.get("clinvar",  "Not in pre-loaded database — live ClinVar via Phase 2"),
            "cosmic":    hs.get("cosmic","Not pre-loaded — check cbioportal.org"),
            "cancer":    disp_cancer  or hs.get("cancer",   "Cancer data — check COSMIC/cBioPortal"),
            "therapeutic": disp_ther or hs.get("therapeutic","Consult ChEMBL, DGIdb, or ClinicalTrials.gov"),
        }

    res_json = json.dumps(residues)
    exp_json = json.dumps(EXPERIMENTS)
    pdb_esc  = (pdb_text or "").replace("\\","\\\\").replace("`","\\`").replace("${","\\${")[:260000]

    gene_display = ""
    src_display  = ""
    if protein_info:
        g = protein_info.get("gene_name","")
        uid = protein_info.get("uniprot_id","")
        if g:   gene_display = g
        if uid: src_display  = f"UniProt {uid}"

    n_high = sum(1 for d in residues.values() if d["priority"]=="HIGH")
    n_med  = sum(1 for d in residues.values() if d["priority"]=="MEDIUM")
    n_low  = sum(1 for d in residues.values() if d["priority"]=="LOW")

    logo_tag = f'<img src="{LOGO_B64}" style="height:36px;object-fit:contain;border-radius:7px">' if LOGO_B64 else "🧬"

    return f"""<!DOCTYPE html><html><head>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#080b14;font-family:'Inter',sans-serif;color:#ccc;font-size:13px;padding:14px}}
::-webkit-scrollbar{{width:5px}}::-webkit-scrollbar-track{{background:#0a0c14}}::-webkit-scrollbar-thumb{{background:#2a2d3a;border-radius:3px}}
.header{{display:flex;align-items:center;gap:12px;margin-bottom:14px}}
.title{{font-family:'IBM Plex Mono',monospace;font-size:18px;font-weight:700;color:#eee}}
.subtitle{{font-size:11px;color:#555;margin-top:2px}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:12px}}
.sc{{background:#0f1117;border:1px solid #1e2030;border-radius:8px;padding:10px;text-align:center}}
.sn{{font-size:1.2rem;font-weight:600;font-family:'IBM Plex Mono',monospace}}
.sl{{font-size:10px;color:#555;margin-top:3px;text-transform:uppercase;letter-spacing:0.08em}}
.vgrid{{display:grid;grid-template-columns:1.4fr 1fr;gap:12px;height:480px;margin-bottom:12px}}
.vwrap{{border:1px solid #1e2030;border-radius:10px;overflow:hidden;position:relative;background:#080b14}}
#viewer{{width:100%;height:100%}}
#tt{{position:absolute;top:10px;left:10px;background:#0f1117ee;border:1px solid #2a2d3a;border-radius:6px;
    padding:8px 12px;font-size:11px;font-family:'IBM Plex Mono',monospace;display:none;pointer-events:none;z-index:10;max-width:220px;line-height:1.6}}
.hint{{position:absolute;bottom:10px;left:50%;transform:translateX(-50%);background:#0f1117cc;
      border:1px solid #1e2030;border-radius:20px;padding:5px 14px;font-size:10px;
      font-family:'IBM Plex Mono',monospace;color:#444;white-space:nowrap;pointer-events:none}}
.ipanel{{border:1px solid #1e2030;border-radius:10px;padding:14px;height:100%;overflow-y:auto;background:#0a0c14}}
.ph{{color:#2a2d3a;font-family:'IBM Plex Mono',monospace;font-size:11px;text-align:center;padding:60px 10px;line-height:3}}
.sl2{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;padding-bottom:5px;border-bottom:1px solid #1a1d2e;margin:10px 0 7px}}
.sl2:first-child{{margin-top:0}}
.drow{{display:flex;gap:8px;padding:5px 0;border-bottom:1px solid #0d0f1a;font-size:11px;line-height:1.5}}
.dl{{color:#3a3d5a;min-width:76px;font-size:10px;font-family:'IBM Plex Mono',monospace;flex-shrink:0;padding-top:1px}}
.dv{{color:#bbb;flex:1}}
.badge{{display:inline-block;padding:3px 12px;border-radius:20px;font-size:9px;font-weight:600;font-family:'IBM Plex Mono',monospace;letter-spacing:0.1em;margin-bottom:8px}}
.chip{{display:inline-block;background:#12141e;border:1px solid #1e2030;border-radius:3px;padding:1px 7px;font-size:9px;font-family:'IBM Plex Mono',monospace;color:#555;margin:2px 2px 0 0}}
.legend{{display:flex;gap:18px;flex-wrap:wrap;padding:6px 0 10px}}
.li{{display:flex;align-items:center;gap:6px;font-size:11px;color:#555}}
.ld{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
.note-bar{{background:#0a1020;border:1px solid #1a2a40;border-radius:6px;padding:8px 12px;font-size:11px;color:#6a8aaa;margin-bottom:10px}}
.sec{{background:#0a0c14;border:1px solid #1e2030;border-radius:10px;padding:14px;margin-bottom:10px}}
.egrid{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:10px}}
.ecard{{background:#080b14;border:1px solid #1e2030;border-radius:8px;padding:10px;cursor:pointer;transition:border-color 0.15s}}
.ecard:hover{{border-color:#2a2d3a}}
.ecard.active{{border-color:#FF4C4C;background:#0f0606}}
.ename{{font-size:12px;font-weight:600;color:#ddd;margin-bottom:3px}}
.emeta{{font-size:10px;font-family:'IBM Plex Mono',monospace}}
#edet{{display:none;margin-top:10px;padding:12px;background:#0a0c14;border:1px solid #1e2030;border-radius:8px;font-size:12px;color:#888;line-height:1.7}}
#edet.vis{{display:block}}
</style>
</head><body>
<div class="header">
  {logo_tag}
  <div>
    <div class="title">Protein Explorer {f'— {gene_display}' if gene_display else ''}</div>
    <div class="subtitle">Click any sphere for annotation &nbsp;·&nbsp; {src_display or 'Structure loaded'} &nbsp;·&nbsp; select experiment to highlight targets</div>
  </div>
</div>

{f'<div class="note-bar">ℹ {pos_note}</div>' if pos_note else ''}

<div class="stats">
  <div class="sc"><div class="sn" style="color:#eee">{len(residues)}</div><div class="sl">Features</div></div>
  <div class="sc"><div class="sn" style="color:#FF4C4C">{n_high}</div><div class="sl">HIGH</div></div>
  <div class="sc"><div class="sn" style="color:#FFA500">{n_med}</div><div class="sl">MEDIUM</div></div>
  <div class="sc"><div class="sn" style="color:#4CA8FF">{n_low}</div><div class="sl">LOW</div></div>
  <div class="sc"><div class="sn" style="color:#4CAF50;font-size:11px">{(src_display or 'DB')}</div><div class="sl">Source</div></div>
</div>

<div class="vgrid">
  <div class="vwrap">
    <div id="viewer"></div>
    <div id="tt"></div>
    <div class="hint">Click any sphere for full annotation</div>
  </div>
  <div class="ipanel" id="ipanel">
    <div class="ph">🔬<br><br>Click any residue<br>sphere to load<br>full annotation</div>
  </div>
</div>

<div class="legend">
  <div class="li"><div class="ld" style="background:#FF4C4C"></div>HIGH priority</div>
  <div class="li"><div class="ld" style="background:#FFA500"></div>MEDIUM priority</div>
  <div class="li"><div class="ld" style="background:#4CA8FF"></div>LOW priority</div>
  <div class="li"><div class="ld" style="background:#fff;border:1px solid #444"></div>Selected</div>
</div>

<div class="sec">
  <div class="sl2" style="margin-top:0">Experimental pathways — click to highlight affected features on structure</div>
  <div class="egrid" id="egrid"></div>
  <div id="edet"></div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<script>
const RES = {res_json};
const EXPS = {exp_json};
const pdb = `{pdb_esc}`;
const HAS_STRUCTURE = pdb.trim().length > 50;

function gc(s){{return s==='critical'?'#FF4C4C':s==='affected'?'#FFA500':'#4CA8FF';}}
function dr(l,v){{return `<div class="drow"><span class="dl">${{l}}</span><span class="dv">${{v}}</span></div>`;}}

let sel=null, activeExp=null, viewer=null;

if(HAS_STRUCTURE){{
  viewer = $3Dmol.createViewer('viewer',{{backgroundColor:'#080b14',antialias:true}});
  viewer.addModel(pdb,'pdb');
  
  const pdbResidues=new Set();
  pdb.split('\\n').forEach(line=>{{if(line.startsWith('ATOM')){{const r=parseInt(line.slice(22,26));if(!isNaN(r))pdbResidues.add(r);}}}});
  
  function applyStyles(exp){{
    viewer.setStyle({{}},{{cartoon:{{color:'#1a1d2e',opacity:0.4}}}});
    const rRange=Array.from(pdbResidues);
    if(rRange.length>1){{viewer.addStyle({{resi:`${{Math.min(...rRange)}}-${{Math.max(...rRange)}}`}},{{cartoon:{{color:'#1e2440',opacity:0.5}}}});}}
    
    Object.entries(RES).forEach(([resi,d])=>{{
      const r=parseInt(resi);
      if(!pdbResidues.has(r))return;
      const c=gc(d.status);
      let rad=(d.status==='critical'?1.1:d.status==='affected'?0.80:0.55),op=1;
      if(exp){{
        const matched=exp.affected.includes(d.orig_pos||r);
        if(matched){{rad=1.3;}}else{{rad*=0.3;op=0.15;}}
      }}
      viewer.addStyle({{resi:r}},{{sphere:{{color:exp&&exp.affected.includes(d.orig_pos||r)?exp.color:c,radius:rad,opacity:op}}}});
    }});
    if(sel)viewer.addStyle({{resi:sel}},{{sphere:{{color:'#ffffff',radius:1.4,opacity:1}}}});
    viewer.render();
  }}

  viewer.setHoverable({{}},true,atom=>{{
    if(!atom?.resi)return;
    const d=RES[atom.resi];if(!d)return;
    const c=gc(d.status);
    const tt=document.getElementById('tt');
    tt.innerHTML=`<span style="color:${{c}};font-weight:700">${{d.label}}</span><br>Pos ${{d.orig_pos||atom.resi}} · Score ${{d.score}}<br><span style="color:${{c}}">${{d.priority}} PRIORITY</span><br><span style="color:#555;font-size:10px">Click for full annotation</span>`;
    tt.style.display='block';
  }},()=>document.getElementById('tt').style.display='none');

  viewer.setClickable({{}},true,atom=>{{
    if(!atom?.resi)return;
    const d=RES[atom.resi];if(!d)return;
    sel=atom.resi;
    applyStyles(activeExp?EXPS.find(e=>e.id===activeExp):null);
    const c=gc(d.status);
    const sl=d.status==='critical'?'CRITICAL — HIGH PRIORITY':d.status==='affected'?'AFFECTED — MEDIUM PRIORITY':'NO SIGNIFICANT EFFECT';
    const chips=['Your data',(d.clinvar&&!d.clinvar.includes('Not in'))&&'ClinVar',(d.domain&&!d.domain.startsWith('Position'))&&'UniProt/InterPro'].filter(Boolean).map(s=>`<span class="chip">${{s}}</span>`).join('');
    document.getElementById('ipanel').innerHTML=`
      <div>
        <span class="badge" style="background:${{c}}22;color:${{c}};border:0.5px solid ${{c}}66">${{sl}}</span>
        <p style="font-size:14px;font-weight:700;color:#eee;margin:0 0 2px;font-family:'IBM Plex Mono',monospace">${{d.label}}</p>
        <p style="font-size:11px;color:#444;margin:0 0 10px">Pos ${{d.orig_pos||atom.resi}} · Score <span style="color:${{c}};font-weight:600">${{d.score}}</span> ${{d.expType?'· '+d.expType:''}}</p>
      </div>
      <div class="sl2" style="margin-top:0">Structural annotation</div>
      ${{dr('Domain',d.domain)}}${{dr('Mechanism',d.mechanism)}}
      <div class="sl2">Clinical data</div>
      ${{dr('ClinVar',d.clinvar)}}${{dr('Cancer',d.cancer)}}
      <div class="sl2">Therapeutic context</div>
      ${{dr('Therapeutic',d.therapeutic)}}
      <div class="sl2">Sources</div>
      <div style="margin-top:4px">${{chips}}</div>`;
  }});

  viewer.zoomTo({{resi:'{zoom_resi}'}});
  viewer.spin(false);
  applyStyles(null);

  // Experiments panel
  const grid=document.getElementById('egrid');
  EXPS.forEach(exp=>{{
    const d=document.createElement('div');
    d.className='ecard';d.id='ec-'+exp.id;
    d.innerHTML=`<div class="ename">${{exp.name}}</div><div class="emeta" style="color:${{exp.color}}">${{exp.cat}}</div><div class="emeta">${{exp.dur}} · ${{exp.cost}}</div>`;
    d.onclick=()=>toggleExp(exp);
    grid.appendChild(d);
  }});
}} else {{
  document.getElementById('viewer').innerHTML='<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#444;font-family:IBM Plex Mono,monospace;font-size:12px;text-align:center;padding:20px">Structure not available<br><span style="font-size:10px;margin-top:8px;display:block">Phase 2 will auto-fetch<br>the correct PDB structure</span></div>';
}}

function toggleExp(exp){{
  const det=document.getElementById('edet');
  if(activeExp===exp.id){{activeExp=null;document.querySelectorAll('.ecard').forEach(c=>c.classList.remove('active'));det.classList.remove('vis');det.innerHTML='';if(viewer)applyStyles(null);return;}}
  activeExp=exp.id;document.querySelectorAll('.ecard').forEach(c=>c.classList.remove('active'));
  document.getElementById('ec-'+exp.id).classList.add('active');
  if(viewer)applyStyles(exp);
  const pills=Object.entries(RES).filter(([_,d])=>exp.affected.includes(d.orig_pos)).map(([_,d])=>`<span class="chip" style="color:${{exp.color}};border-color:${{exp.color}}55">${{d.label}}</span>`).join('');
  det.innerHTML=`<strong style="color:${{exp.color}}">${{exp.name}}</strong> — ${{exp.note}}<br><br>Highlighted: ${{pills||'Based on your data'}}`;
  det.classList.add('vis');
}}
</script>
</body></html>"""


def render():
    if LOGO_B64:
        st.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px"><img src="{LOGO_B64}" style="height:40px;object-fit:contain;border-radius:7px"><div><strong style="font-size:1.1rem">Protein Explorer</strong><p style="color:#555;font-size:0.83rem;margin:0">Click any sphere for full annotation · auto-fetches correct structure for any protein</p></div></div>', unsafe_allow_html=True)
    st.divider()

    if "t_scored" not in st.session_state:
        st.info("👈 Run Triage first in the **Triage System** tab.")
        return

    enrichment   = st.session_state.get("t_enrichment", None)
    protein_info = st.session_state.get("t_protein",    None)

    # Get structure: from enrichment (correct protein) or fall back to TP53
    pdb_text = None
    struct_source = ""
    if enrichment and enrichment.get("structure_pdb"):
        pdb_text     = enrichment["structure_pdb"]
        struct_source = enrichment.get("structure_source","")
    else:
        with st.spinner("Loading reference structure..."):
            try:
                r = requests.get("https://files.rcsb.org/download/2OCJ.pdb", timeout=15)
                if r.status_code == 200:
                    pdb_text = r.text
                    struct_source = "TP53 reference (PDB 2OCJ) — run triage to load correct protein structure"
            except Exception:
                pass

    if struct_source:
        st.caption(f"🏗️ {struct_source}")

    if protein_info and enrichment:
        gene  = protein_info.get("gene_name","")
        uid   = protein_info.get("uniprot_id","")
        pname = enrichment.get("uniprot",{}).get("protein_name","")
        if gene or pname:
            st.markdown(f'<div style="background:#08101a;border:1px solid #1e2030;border-radius:8px;padding:10px 14px;margin-bottom:12px;font-size:0.82rem"><span style="color:#4CA8FF;font-weight:600">{pname or gene}</span> · <span style="color:#555">UniProt: {uid}</span> · <span style="color:#4CAF50;font-size:0.75rem">DB enriched</span></div>', unsafe_allow_html=True)

    components.html(
        build_html(st.session_state.t_scored, pdb_text, enrichment, protein_info),
        height=1050, scrolling=True
    )
