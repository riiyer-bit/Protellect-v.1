"""
hypothesis_lab.py — Protellect Hypothesis Lab (Tab 4)
IMPORTANT: HTML is built with string substitution NOT f-strings.
This avoids all {{ }} escaping issues with JavaScript inside Python f-strings.
"""

import streamlit as st
try:
    from protein_data import get_protein_info as _get_pdata
except ImportError:
    def _get_pdata(g): return {}
import streamlit.components.v1 as components
import json
import base64
import requests
from pathlib import Path

# ── Logo ──────────────────────────────────────────────────────────────────────
try:
    from logo import LOGO_DATA_URL as LOGO_B64
except Exception:
    _lp = Path("/mnt/user-data/uploads/1777622887238_image.png")
    LOGO_B64 = ("data:image/png;base64," + base64.b64encode(_lp.read_bytes()).decode()) if _lp.exists() else None

# ── Hotspot data ──────────────────────────────────────────────────────────────
HOTSPOT_DATA = {
    175: {"mechanism":"Disrupts zinc coordination at C176/H179/C238/C242. Global misfolding of DNA-binding domain — the most common TP53 hotspot.","clinvar":"Pathogenic · 847 submissions","cosmic":"~6% of all cancers","cancer":"Breast, lung, colorectal, ovarian, bladder","therapeutic":"APR-246 (eprenetapopt) — Phase III","cell":"apoptosis","domain":"DNA-binding domain (L2 loop) — zinc coordination site","experiment":"Thermal shift assay (Tm −8–10°C) → EMSA → luciferase reporter (p21/MDM2).","struct_effect":"zinc_collapse"},
    248: {"mechanism":"Direct DNA contact residue in L3 loop. Makes H-bonds to minor groove at CATG sequences. Abolishes sequence-specific binding.","clinvar":"Pathogenic · 623 submissions","cosmic":"~3% of all cancers","cancer":"Colorectal, lung, pancreatic, ovarian","therapeutic":"Synthetic lethality under investigation","cell":"checkpoint","domain":"DNA-binding domain (L3 loop) — direct DNA contact","experiment":"EMSA to confirm loss of DNA binding. Luciferase reporter assay.","struct_effect":"dna_contact_loss"},
    273: {"mechanism":"DNA backbone phosphate contact. Loss reduces affinity >100-fold. R273C retains partial structure unlike R273H.","clinvar":"Pathogenic · 512 submissions","cosmic":"~3% of all cancers","cancer":"Colorectal, lung, brain, pancreatic","therapeutic":"Small molecule stabilizers experimental","cell":"checkpoint","domain":"DNA-binding domain (S10 strand) — backbone contact","experiment":"EMSA. Test R273C and R273H separately.","struct_effect":"dna_contact_loss"},
    249: {"mechanism":"H2 helix structural mutation. Characteristic aflatoxin B1 mutational signature. Disrupts HIPK2 interaction.","clinvar":"Pathogenic · 298 submissions","cosmic":"~1.5% — enriched in liver cancer","cancer":"Liver (HCC), lung, esophageal","therapeutic":"No specific therapy","cell":"proliferation","domain":"DNA-binding domain (H2 helix)","experiment":"Reporter assay. Co-IP for dominant negative tetramer.","struct_effect":"helix_break"},
    245: {"mechanism":"Glycine essential for L3 loop geometry. Any side chain sterically clashes with DNA backbone.","clinvar":"Pathogenic · 187 submissions","cosmic":"~1.5% of cancers","cancer":"Breast, lung, sarcoma","therapeutic":"Structural correctors under investigation","cell":"apoptosis","domain":"DNA-binding domain (L3 loop)","experiment":"Thermal shift + EMSA. APR-246 rescue if structural mutant confirmed.","struct_effect":"loop_distortion"},
    282: {"mechanism":"R282 salt bridge with E271 stabilises H2 helix. Tryptophan disrupts this causing partial helix unfolding.","clinvar":"Pathogenic · 156 submissions","cosmic":"~1% of cancers","cancer":"Breast, colorectal, lung","therapeutic":"No approved targeted therapy","cell":"apoptosis","domain":"DNA-binding domain (H2 helix)","experiment":"Thermal shift assay. Luciferase reporter for p21/MDM2.","struct_effect":"helix_break"},
    220: {"mechanism":"Creates a surface hydrophobic cavity that destabilises domain thermodynamically. Not a direct DNA contact — the cavity is a druggable pocket.","clinvar":"Pathogenic · 89 submissions","cosmic":"~1% of cancers","cancer":"Breast, lung, ovarian","therapeutic":"PC14586 (rezatapopt) — fills Y220C cavity, Phase II","cell":"apoptosis","domain":"DNA-binding domain (S7-S8 loop)","experiment":"Thermal shift. APR-246 and PC14586 rescue — prime cavity-filling candidate.","struct_effect":"surface_cavity"},
}

# Per-protein structural effect descriptions (for any protein, not just TP53)
PROTEIN_STRUCT_EFFECTS = {
    "FLNA": {
        "default_struct": "loop_distortion",
        "description": "Filamin A repeat domain distortion. The Ig-like fold loses its topology when key residues mutate, preventing GPCR intracellular loop docking.",
        "struct_stages": ["WT: Ig-like repeat domain stable","Variant introduced in repeat domain","Local beta-strand separation","GPCR docking surface disrupted","Actin crosslinking reduced","Signalling hub disorganised"],
        "experiments": "Co-IP with GPCR partner → actin sedimentation → patient fibroblast cytoskeletal staining",
        "cell_effect": "cytoskeletal",
    },
    "FLNC": {
        "default_struct": "helix_break",
        "description": "Filamin C Z-disc anchor helix disruption. Mutations break the sarcomere coupling between cardiac GPCRs and myofilaments.",
        "struct_stages": ["WT: Z-disc anchoring helix stable","Pathogenic variant disrupts helix","Sarcomere coupling loosens","GPCR-sarcomere signalling impaired","Protein aggregation begins","Cardiomyopathy-driving aggregate"],
        "experiments": "iPSC-CM Ca²⁺ transients → EM Z-disc analysis → desmin co-localisation",
        "cell_effect": "proliferation",
    },
    "ARRB1": {
        "default_struct": "default",
        "description": "β-Arrestin 1 structural variants. Note: zero ClinVar pathogenic variants — most structural changes are tolerated due to β-arrestin 2 redundancy and distributed recognition surface.",
        "struct_stages": ["WT: Phospho-sensing cage intact","Variant in recognition surface","Partial GPCR binding reduced","β-Arrestin 2 compensates","No net disease phenotype","Variant tolerated in human population"],
        "experiments": "BRET recruitment assay → biased agonism screen (NanoBiT) → NOT thermal shift (not the relevant function)",
        "cell_effect": "checkpoint",
    },
    "CHRM2": {
        "default_struct": "loop_distortion",
        "description": "CHRM2 7-TM helix bundle disruption. Dominant variants alter intracellular loop 3 (ICL3) geometry, disrupting Gi/o coupling and Filamin C docking.",
        "struct_stages": ["WT: ICL3 in correct geometry for Gαi","Dominant CHRM2 variant in ICL3","Gi/o coupling surface distorted","cAMP dysregulation begins","GIRK channel function impaired","Dilated cardiomyopathy progression"],
        "experiments": "Patch clamp IKACh → cAMP BRET → cardiac organoid contractility",
        "cell_effect": "apoptosis",
    },
    "CHRM3": {
        "default_struct": "loop_distortion",
        "description": "CHRM3 ICL3 frameshift. p.Pro392AlafsTer43 removes the entire distal ICL3 — the Filamin A docking site and Gq/11 coupling region.",
        "struct_stages": ["WT: ICL3 enables Gq/11 coupling","Frameshift truncates ICL3","Gq/11 cannot engage","PLCβ not activated","No Ca²⁺ release in smooth muscle","Bladder contraction impossible → PBS"],
        "experiments": "Ca²⁺ imaging (Fura-2) → IP-One HTRF → CHRM3-FLNA Co-IP (loss of interaction)",
        "cell_effect": "apoptosis",
    },
}

def get_struct_effect_for_protein(gene, position, priority, domain_name=""):
    """Get structural effect type based on protein + position context."""
    gu = gene.upper()
    pse = PROTEIN_STRUCT_EFFECTS.get(gu, {})
    default = pse.get("default_struct","default")
    # Map domain types to structural effects
    dname_lower = domain_name.lower()
    if "zinc" in dname_lower or "coordination" in dname_lower: return "zinc_collapse"
    if "dna" in dname_lower or "binding" in dname_lower: return "dna_contact_loss"
    if "helix" in dname_lower or "alpha" in dname_lower: return "helix_break"
    if "loop" in dname_lower or "glycine" in dname_lower: return "loop_distortion"
    if "surface" in dname_lower or "cavity" in dname_lower: return "surface_cavity"
    # Priority-based fallback
    if priority == "HIGH": return default if default != "default" else "helix_break"
    return "default"

def get_residue_annotation_for_protein(gene, position, domains, priority, clinvar_variants, pdata):
    """Build residue annotation dict for ANY protein."""
    gu = gene.upper()
    # Check if it's in HOTSPOT_DATA (TP53 specific)
    if gu == "TP53" and position in HOTSPOT_DATA:
        return HOTSPOT_DATA[position]
    
    pse = PROTEIN_STRUCT_EFFECTS.get(gu, {})
    domain_name = ""
    for d in (domains or []):
        if d.get("start",0) <= position <= d.get("end",0):
            domain_name = d.get("name","")
            break
    
    # Find ClinVar info for this position
    cv_info = ""
    cv_disease = ""
    for v in (clinvar_variants or []):
        if v.get("pos",0) == position:
            cv_info = v.get("germline","") or v.get("sig","")
            cv_disease = (v.get("conditions",[""])[0] if v.get("conditions") else "")[:60]
            break
    
    struct_e = get_struct_effect_for_protein(gu, position, priority, domain_name)
    
    # Get protein-specific experiment
    exp_str = pse.get("experiments","Thermal shift DSF → ITC binding → patient cell validation")
    
    # Build mechanism from protein_data
    real_bio = pdata.get("real_biology","")
    mechanism = f"Position {position} in {domain_name or gu} domain. {real_bio[:120] if real_bio else ''} Structural effect: {pse.get('description',''[:80])}"
    
    return {
        "mechanism": mechanism[:200],
        "clinvar": cv_info or "Check ClinVar directly for this position",
        "cosmic": "—",
        "cancer": cv_disease or "See ClinVar for associated diseases",
        "therapeutic": "See Tab 4 — Therapy",
        "cell": pse.get("cell_effect","apoptosis"),
        "domain": domain_name or f"Position {position}",
        "experiment": exp_str,
        "struct_effect": struct_e,
        "struct_stages": pse.get("struct_stages", STRUCT_STAGES_FALLBACK.get(struct_e,[])),
    }

STRUCT_STAGES_FALLBACK = {
    "zinc_collapse":    ["WT: zinc stably coordinated","Mutation distorts coordination","Zinc coordination weakening","Zinc ion released","Loop unfolds","Full domain misfolding"],
    "dna_contact_loss": ["WT: contact residue present","Mutation removes contact","Binding weakens","H-bonds breaking","Target molecule separating","Loss of recognition"],
    "helix_break":      ["WT: helix stable","Key residue mutated","Salt bridge removed","Helix begins unwinding","Unwinding propagates","Loss of activity"],
    "loop_distortion":  ["WT: loop geometry correct","Mutation adds/removes side chain","Steric clash","Loop forced away","Interface blocked","Recognition abolished"],
    "surface_cavity":   ["WT: hydrophobic pocket filled","Mutation removes side chain","Surface pocket opens","Hydrophobic exposure","Destabilisation","Druggable cavity"],
    "default":          ["Wild-type conformation","Mutation introduced","Local perturbation","Propagation","Interface altered","Reduced activity"],
}


CELL_DATA = {
    "apoptosis":     {"title":"Loss of apoptosis signalling","color":"#FF4C4C","anim":"cpulse","desc":"TP53 normally activates BAX, PUMA, and NOXA to trigger programmed cell death. This mutation abolishes that signal — damaged cells survive and accumulate further mutations."},
    "checkpoint":    {"title":"DNA damage checkpoint bypass","color":"#FFA500","anim":"cspin","desc":"TP53 normally halts the cell cycle at G1/S via p21. This contact mutation prevents p21 activation — cells divide with unrepaired DNA every cycle."},
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
    """
    Build self-contained HTML. Uses string substitution (not f-strings)
    so JavaScript curly braces never conflict with Python f-string syntax.
    """
    # Serialize all Python data to JSON — injected as JS variables
    res_json  = json.dumps(residues_data)
    cell_json = json.dumps(CELL_DATA)
    pdb_esc   = (pdb_data or "")
    pdb_esc   = pdb_esc.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")[:270000]

    n_high = sum(1 for r in residues_data if r["priority"] == "HIGH")
    n_med  = sum(1 for r in residues_data if r["priority"] == "MEDIUM")
    n_low  = sum(1 for r in residues_data if r["priority"] == "LOW")
    top    = residues_data[0] if residues_data else {}

    logo_tag = '<img src="' + logo_url + '" style="width:44px;height:44px;object-fit:contain;border-radius:8px">' if logo_url else '<span style="font-size:32px">🧬</span>'

    # ── CSS (no f-string escaping needed — pure string) ──────────────────────
    CSS = """
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#080b14;font-family:'Inter',sans-serif;color:#ccc;font-size:13px;padding:14px;line-height:1.5}
::-webkit-scrollbar{width:5px}::-webkit-scrollbar-track{background:#0a0c14}::-webkit-scrollbar-thumb{background:#2a2d3a;border-radius:3px}
.header{display:flex;align-items:center;gap:14px;margin-bottom:16px}
.title{font-family:'IBM Plex Mono',monospace;font-size:20px;font-weight:700;color:#eee}
.sub{font-size:12px;color:#555;margin-top:2px}
.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:16px}
.sc{background:#0f1117;border:1px solid #1e2030;border-radius:8px;padding:12px;text-align:center}
.sn{font-size:1.3rem;font-weight:600;font-family:'IBM Plex Mono',monospace}
.sl{font-size:10px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.08em}
.filter-bar{display:flex;gap:8px;margin-bottom:14px;align-items:center;flex-wrap:wrap}
.fb{padding:6px 14px;border-radius:20px;border:1px solid #1e2030;background:#0f1117;color:#555;font-size:11px;cursor:pointer;font-family:'IBM Plex Mono',monospace;transition:all 0.15s}
.fb.active{border-color:#FF4C4C;color:#FF4C4C;background:#1a0808}
.fb.am.active{border-color:#FFA500;color:#FFA500;background:#1a1200}
.fb.al.active{border-color:#4CA8FF;color:#4CA8FF;background:#08101a}
.fb.aa.active{border-color:#555;color:#ccc}
.card{background:#0a0c14;border:1px solid #1e2030;border-radius:10px;margin-bottom:10px;overflow:hidden}
.card:hover{border-color:#2a2d3a}
.chead{display:flex;align-items:center;gap:12px;padding:16px;cursor:pointer;user-select:none}
.crank{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#3a3d5a;min-width:28px}
.cdot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.clabel{font-family:'IBM Plex Mono',monospace;font-size:14px;font-weight:700;color:#eee;flex:1}
.cbadge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:10px;font-weight:600;font-family:'IBM Plex Mono',monospace;margin-right:6px}
.chev{color:#444;font-size:12px;transition:transform 0.2s;margin-left:4px}
.chev.open{transform:rotate(90deg)}
.cbody{display:none;border-top:1px solid #1e2030}
.cbody.open{display:block}
.cgrid{display:grid;grid-template-columns:360px 1fr;min-height:500px}
.cleft{padding:16px;border-right:1px solid #1e2030;overflow-y:auto}
.cright{padding:16px;background:#080b14;overflow-y:auto}
.sl2{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;padding-bottom:5px;border-bottom:1px solid #1a1d2e;margin:12px 0 8px}
.sl2:first-child{margin-top:0}
.drow{display:flex;gap:8px;padding:5px 0;border-bottom:1px solid #0d0f1a;font-size:11px;line-height:1.5}
.dl{color:#3a3d5a;min-width:76px;font-size:10px;font-family:'IBM Plex Mono',monospace;flex-shrink:0;padding-top:1px}
.dv{color:#bbb;flex:1}
.hyp-text{font-size:12px;color:#888;line-height:1.7;padding:10px 12px;background:#080b14;border:1px solid #1e2030;border-radius:6px;margin-bottom:10px}
.action-box{background:#0a1a0a;border:1px solid #1a3a1a;border-radius:6px;padding:10px 12px;margin-top:8px}
.al{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.12em;color:#4CAF50;margin-bottom:5px}
.at{font-size:11px;color:#888;line-height:1.7}
.chain-wrap{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
.chain-lbl{font-size:10px;font-family:'IBM Plex Mono',monospace;color:#555;margin-bottom:4px}
.chain-svg{width:100%;height:42px;border:1px solid #1e2030;border-radius:5px;background:#040608;display:block}
.bar-row{margin-bottom:6px}
.bar-lbl{display:flex;justify-content:space-between;font-size:10px;color:#555;margin-bottom:2px;font-family:'IBM Plex Mono',monospace}
.bar-track{background:#1a1d2e;border-radius:3px;height:6px;overflow:hidden}
.bar-fill{height:100%;border-radius:3px;transition:width 0.3s}
.slider-box{margin-bottom:12px;padding:12px;background:#0a0c14;border:1px solid #1e2030;border-radius:8px}
.sltitle{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:8px}
.slrow{display:flex;align-items:center;gap:8px;margin-bottom:6px}
.sllbl{font-size:10px;font-family:'IBM Plex Mono',monospace;color:#555;min-width:55px}
input[type=range]{flex:1;cursor:pointer;height:4px;accent-color:#FF4C4C}
.slval{font-size:11px;font-family:'IBM Plex Mono',monospace;color:#aaa;min-width:90px;text-align:right}
.phase-bar{height:12px;background:#1a1d2e;border-radius:6px;position:relative;overflow:hidden;margin:6px 0}
.phase-fill{height:100%;border-radius:6px;transition:width 0.3s;display:flex;align-items:center;padding-left:6px;font-size:9px;font-family:'IBM Plex Mono',monospace;color:white;overflow:hidden;white-space:nowrap}
.pmark{position:absolute;top:0;height:100%;width:2px;background:white;opacity:0.7;transition:left 0.3s;z-index:5}
.evt{display:flex;gap:6px;margin-bottom:5px;transition:opacity 0.3s}
.evt.off{opacity:0.15}
.edot{width:7px;height:7px;border-radius:50%;flex-shrink:0;margin-top:3px}
.evt strong{display:block;font-size:10px;color:#eee;margin-bottom:1px}
.evt span{font-size:9px;color:#555;line-height:1.4}
.prot-wrap{margin-bottom:12px;padding:12px;background:#040608;border:1px solid #1e2030;border-radius:10px}
.prot-title{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:8px}
.prot-stage{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#aaa;text-align:center;margin:6px 0 3px}
canvas{display:block;width:100%;border-radius:6px;background:#040608}
.stage-dots{display:flex;justify-content:center;gap:6px;margin-top:6px}
.sdot{width:7px;height:7px;border-radius:50%;transition:background 0.3s}
.cell-box{padding:12px;background:#0a0c14;border:1px solid #1e2030;border-radius:8px}
.cell-grid{display:grid;grid-template-columns:90px 1fr;gap:12px;align-items:start}
.cell-col{display:flex;flex-direction:column;align-items:center;gap:5px}
.cell-title{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;margin-bottom:5px}
.cell-desc{font-size:11px;color:#888;line-height:1.6}
@keyframes cpulse{0%,100%{transform:scale(1)}50%{transform:scale(1.12)}}
@keyframes cspin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
@keyframes cgrow{0%,100%{transform:scale(1)}50%{transform:scale(1.18)}}
@keyframes cshake{0%,100%{transform:translateX(0)}25%{transform:translateX(-3px)}75%{transform:translateX(3px)}}
@keyframes wobble-critical{0%,100%{transform:translateY(0)}30%{transform:translateY(-7px)}70%{transform:translateY(5px)}}
@keyframes wobble-affected{0%,100%{transform:translateY(0)}50%{transform:translateY(-3px)}}
@keyframes wobble-normal{0%,100%{transform:translateY(0)}50%{transform:translateY(-1px)}}
</style>"""

    # ── JavaScript (pure string — no Python f-string escaping needed) ─────────
    JS = """
<script>
const RESIDUES = __RESIDUES_JSON__;
const CELLD    = __CELL_JSON__;
const pdbData  = `__PDB_DATA__`;

function gc(s){ return s==='critical'?'#FF4C4C':s==='affected'?'#FFA500':'#4CA8FF'; }
function lerp(a,b,t){ return a+(b-a)*Math.max(0,Math.min(1,t)); }
function clamp(v,a,b){ return Math.max(a,Math.min(b,v)); }
function lerpColor(c1,c2,t){
  t=clamp(t,0,1);
  const h=v=>parseInt(v,16);
  const r=Math.round(lerp(h(c1.slice(1,3)),h(c2.slice(1,3)),t));
  const g=Math.round(lerp(h(c1.slice(3,5)),h(c2.slice(3,5)),t));
  const b=Math.round(lerp(h(c1.slice(5,7)),h(c2.slice(5,7)),t));
  return '#'+[r,g,b].map(v=>v.toString(16).padStart(2,'0')).join('');
}

// ── Mini chain ──────────────────────────────────────────────────────────
function buildChain(pos,status,score){
  const c=gc(status),isH=status==='critical',isM=status==='affected';
  const W=300,total=12,mutI=5,sp=W/(total+1);
  let wt='',mut='';
  for(let i=0;i<total;i++){
    const x=(i+1)*sp,isMut=i===mutI,r=isMut?9:5;
    wt+=`<circle cx="${x}" cy="21" r="5" fill="#0a1f0a" stroke="#4CAF50" stroke-width="1"/>`;
    if(i<total-1) wt+=`<line x1="${x+5}" y1="21" x2="${(i+2)*sp-5}" y2="21" stroke="#1a3a1a" stroke-width="1"/>`;
    const a=isMut?`style="transform-origin:${x}px 21px;animation:wobble-${status} 1.4s ease-in-out infinite"` :'';
    mut+=`<circle cx="${x}" cy="21" r="${r}" fill="${isMut?c+'22':'#040608'}" stroke="${isMut?c:'#1e2030'}" stroke-width="${isMut?2.5:0.8}" ${a}/>`;
    if(i<total-1) mut+=`<line x1="${x+(isMut?r:5)}" y1="21" x2="${(i+2)*sp-5}" y2="21" stroke="${isMut?c:'#1a1d2e'}" stroke-width="1"/>`;
  }
  const pcts=isH?[8,3,28,2]:isM?[50,45,72,55]:[88,90,92,88];
  const bars=['Zinc coord.','DNA binding','Thermal stab.','Transcription'].map((l,i)=>
    `<div class="bar-row"><div class="bar-lbl"><span>${l}</span><span style="color:${c}">${pcts[i]}%</span></div><div class="bar-track"><div class="bar-fill" style="width:${pcts[i]}%;background:${c}"></div></div></div>`
  ).join('');
  return `<div class="chain-wrap"><div>
    <div class="chain-lbl" style="color:#4CAF50">Wild-type chain</div>
    <svg class="chain-svg" viewBox="0 0 ${W} 42">${wt}</svg>
    <div class="chain-lbl" style="color:${c};margin-top:6px">Mutant — pos ${pos} (wobble = instability)</div>
    <svg class="chain-svg" viewBox="0 0 ${W} 42">${mut}</svg>
  </div><div><div class="chain-lbl">Function vs wild-type</div>${bars}</div></div>`;
}

// ── Canvas drawings ──────────────────────────────────────────────────────
function drawZincCollapse(ctx,W,H,t,c){
  ctx.clearRect(0,0,W,H);
  const dnaY=lerp(55,25,clamp((t-0.6)*2.5,0,1));
  ctx.save();
  ctx.strokeStyle=lerpColor('#378add','#1e2030',t);ctx.lineWidth=2.5;ctx.setLineDash([10,5]);
  ctx.beginPath();ctx.moveTo(25,dnaY);ctx.lineTo(W-25,dnaY);ctx.stroke();ctx.setLineDash([]);
  ctx.fillStyle='#378add99';ctx.font='11px monospace';ctx.fillText('DNA',28,dnaY-8);
  const hc=lerpColor('#4CAF50',c,t);
  ctx.strokeStyle=hc;ctx.lineWidth=4;ctx.beginPath();
  for(let x=25;x<W-25;x++){
    const wobble=t>0.35?Math.sin((x/28)*Math.PI)*lerp(0,22,t-0.35)*Math.sin((x/(W/2))*Math.PI):0;
    const y=H/2+18+wobble+Math.sin((x/55)*Math.PI)*9;
    x===25?ctx.moveTo(x,y):ctx.lineTo(x,y);
  }
  ctx.stroke();
  const za=clamp(1-t*2.2,0,1),znX=W/2,znY=H/2+52;
  ctx.globalAlpha=za;ctx.strokeStyle='#FFC107';ctx.lineWidth=2;
  ctx.beginPath();ctx.arc(znX,znY,13,0,Math.PI*2);ctx.stroke();
  ctx.fillStyle='#FFC107';ctx.font='bold 10px monospace';ctx.textAlign='center';ctx.fillText('Zn2+',znX,znY+4);
  ctx.globalAlpha=za*0.8;ctx.setLineDash([3,3]);
  [[W/2-55,H/2+18],[W/2-25,H/2+22],[W/2+25,H/2+22],[W/2+55,H/2+18]].forEach(([x,y])=>{ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(znX,znY);ctx.stroke();});
  ctx.setLineDash([]);ctx.globalAlpha=clamp(1-t*2,0,1);ctx.strokeStyle=hc;ctx.lineWidth=2;ctx.setLineDash([4,4]);
  [W/2-55,W/2,W/2+55].forEach(x=>{ctx.beginPath();ctx.moveTo(x,H/2+15);ctx.lineTo(x,dnaY);ctx.stroke();});
  ctx.setLineDash([]);ctx.globalAlpha=1;
  ctx.fillStyle=c+'55';ctx.strokeStyle=c;ctx.lineWidth=2.5;
  ctx.beginPath();ctx.arc(W/2-28,H/2+18,12,0,Math.PI*2);ctx.fill();ctx.stroke();
  ctx.fillStyle=c;ctx.font='bold 9px monospace';ctx.textAlign='center';ctx.fillText('R175H',W/2-28,H/2+21);
  ctx.restore();
}

function drawDNAContactLoss(ctx,W,H,t,c){
  ctx.clearRect(0,0,W,H);
  const dnaY=lerp(50,18,clamp(t*2-0.2,0,1));
  ctx.save();
  ctx.strokeStyle=lerpColor('#378add','#1e2030',t*0.8);ctx.lineWidth=2.5;ctx.setLineDash([10,5]);
  ctx.beginPath();ctx.moveTo(25,dnaY);ctx.lineTo(W-25,dnaY);ctx.stroke();ctx.setLineDash([]);
  ctx.fillStyle='#378add';ctx.font='11px monospace';ctx.fillText('DNA',28,dnaY-8);
  ctx.strokeStyle=t<0.4?'#4CAF50':'#FFA500';ctx.lineWidth=4;ctx.beginPath();
  for(let x=25;x<W-25;x++){const y=H/2+20+Math.sin((x/65)*Math.PI)*10;x===25?ctx.moveTo(x,y):ctx.lineTo(x,y);}
  ctx.stroke();
  [W/2-65,W/2,W/2+65].forEach((cx,i)=>{
    const broken=t>0.25+i*0.18;
    const cy=H/2+20+Math.sin((cx/65)*Math.PI)*10;
    if(!broken){ctx.strokeStyle='#4CAF50';ctx.lineWidth=2;ctx.setLineDash([]);ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(cx,dnaY);ctx.stroke();ctx.fillStyle='#4CAF50';ctx.beginPath();ctx.arc(cx,dnaY,5,0,Math.PI*2);ctx.fill();}
    else{ctx.strokeStyle=c;ctx.lineWidth=2;ctx.setLineDash([4,4]);ctx.globalAlpha=0.25;ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(cx,dnaY+15);ctx.stroke();ctx.globalAlpha=1;ctx.setLineDash([]);ctx.fillStyle=c+'55';ctx.strokeStyle=c;ctx.lineWidth=2.5;ctx.beginPath();ctx.arc(cx,cy,10,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.fillStyle=c;ctx.font='8px monospace';ctx.textAlign='center';ctx.fillText(i===0?'R248':'R273',cx,cy+3);}
  });
  ctx.restore();
}

function drawHelixBreak(ctx,W,H,t,c){
  ctx.clearRect(0,0,W,H);ctx.save();
  ctx.strokeStyle='#378add33';ctx.lineWidth=2;ctx.setLineDash([8,5]);ctx.beginPath();ctx.moveTo(25,48);ctx.lineTo(W-25,48);ctx.stroke();ctx.setLineDash([]);
  const bx=W/2,ba=t*38;
  ctx.lineWidth=4;ctx.strokeStyle=t<0.3?'#4CAF50':'#FFA500';ctx.beginPath();
  for(let x=25;x<bx;x++){const y=H/2+18+Math.sin((x/55)*Math.PI)*12;x===25?ctx.moveTo(x,y):ctx.lineTo(x,y);}
  ctx.stroke();
  ctx.strokeStyle=t<0.55?'#4CAF50':t<0.8?'#FFA500':'#FF4C4C';ctx.beginPath();
  for(let x=bx;x<W-25;x++){const y=H/2+18-ba*0.5+Math.sin((x/55)*Math.PI)*12*(1-t*0.25);x===bx?ctx.moveTo(x,y):ctx.lineTo(x,y);}
  ctx.stroke();
  const my=H/2+18+Math.sin((bx/55)*Math.PI)*12;
  ctx.fillStyle=c+'55';ctx.strokeStyle=c;ctx.lineWidth=2.5;ctx.beginPath();ctx.arc(bx,my,13,0,Math.PI*2);ctx.fill();ctx.stroke();
  ctx.fillStyle=c;ctx.font='bold 9px monospace';ctx.textAlign='center';ctx.fillText('R282W',bx,my+3);
  ctx.globalAlpha=clamp(1-t*2.2,0,1);ctx.strokeStyle='#FFC107';ctx.lineWidth=2;ctx.setLineDash([3,3]);ctx.beginPath();ctx.moveTo(bx-30,H/2+35);ctx.lineTo(bx+30,H/2+35);ctx.stroke();ctx.setLineDash([]);ctx.fillStyle='#FFC107';ctx.font='9px monospace';ctx.fillText('salt bridge',bx,H/2+48);ctx.globalAlpha=1;
  ctx.restore();
}

function drawLoopDistortion(ctx,W,H,t,c){
  ctx.clearRect(0,0,W,H);ctx.save();
  const dnaY=50+t*28;
  ctx.strokeStyle=lerpColor('#378add','#1e2030',t);ctx.lineWidth=2.5;ctx.setLineDash([10,5]);ctx.beginPath();ctx.moveTo(25,dnaY);ctx.lineTo(W-25,dnaY);ctx.stroke();ctx.setLineDash([]);
  ctx.fillStyle='#378add';ctx.font='11px monospace';ctx.fillText('DNA',28,dnaY-8);
  ctx.strokeStyle='#4CAF50';ctx.lineWidth=4;ctx.beginPath();for(let x=25;x<W-25;x++){const y=H/2+15+Math.sin((x/75)*Math.PI)*8;x===25?ctx.moveTo(x,y):ctx.lineTo(x,y);}ctx.stroke();
  const lx=W/2,ly=H/2+15,ld=t*38;
  ctx.strokeStyle=t<0.3?'#4CAF50':t<0.6?'#FFA500':'#FF4C4C';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(lx-50,ly);ctx.quadraticCurveTo(lx,ly-18+ld,lx+50,ly);ctx.stroke();
  ctx.fillStyle=c+'55';ctx.strokeStyle=c;ctx.lineWidth=2.5;ctx.beginPath();ctx.arc(lx,ly-8+ld*0.5,12,0,Math.PI*2);ctx.fill();ctx.stroke();
  ctx.fillStyle=c;ctx.font='bold 9px monospace';ctx.textAlign='center';ctx.fillText('G245S',lx,ly-5+ld*0.5+3);
  if(t>0.3){ctx.globalAlpha=clamp(t-0.3,0,1);ctx.strokeStyle='#FF4C4C';ctx.lineWidth=2;ctx.setLineDash([3,3]);ctx.beginPath();ctx.moveTo(lx,ly-15+ld*0.8);ctx.lineTo(lx,dnaY-5);ctx.stroke();ctx.setLineDash([]);ctx.globalAlpha=1;}
  ctx.restore();
}

function drawSurfaceCavity(ctx,W,H,t,c){
  ctx.clearRect(0,0,W,H);ctx.save();
  ctx.strokeStyle=t<0.35?'#4CAF50':t<0.7?'#FFA500':'#FF9800';ctx.lineWidth=4;ctx.beginPath();for(let x=25;x<W-25;x++){const y=H/2+Math.sin((x/55)*Math.PI)*10;x===25?ctx.moveTo(x,y):ctx.lineTo(x,y);}ctx.stroke();
  const cW=lerp(0,58,t),cH=lerp(0,42,t),cX=W/2,cY=H/2-5;
  ctx.fillStyle=t<0.5?'#1e2030':'#080b14';ctx.beginPath();ctx.ellipse(cX,cY+cH/2,cW/2,cH/2,0,0,Math.PI*2);ctx.fill();
  if(t>0.08){ctx.strokeStyle=c;ctx.lineWidth=1.5;ctx.setLineDash([3,3]);ctx.beginPath();ctx.ellipse(cX,cY+cH/2,cW/2,cH/2,0,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);}
  ctx.fillStyle=t<0.3?'#4CAF50':c;ctx.font='bold 9px monospace';ctx.textAlign='center';ctx.fillText(t<0.25?'Y220 (Tyr)':'Y220C (cavity)',cX,cY+cH/2+4);
  if(t>0.55){ctx.globalAlpha=clamp((t-0.55)*2.5,0,1);ctx.fillStyle='#4CA8FF';ctx.font='10px monospace';ctx.fillText('druggable pocket',cX+38,cY+cH/2);ctx.fillText('target: PC14586',cX+38,cY+cH/2+13);ctx.globalAlpha=1;}
  ctx.restore();
}

function drawDefault(ctx,W,H,t,c){
  ctx.clearRect(0,0,W,H);ctx.save();
  ctx.strokeStyle=lerpColor('#4CAF50',c,t);ctx.lineWidth=4;ctx.beginPath();
  for(let x=25;x<W-25;x++){const d=t*Math.sin((x/35)*Math.PI)*18;const y=H/2+18+d+Math.sin((x/65)*Math.PI)*10;x===25?ctx.moveTo(x,y):ctx.lineTo(x,y);}
  ctx.stroke();ctx.fillStyle=c+'55';ctx.strokeStyle=c;ctx.lineWidth=2.5;ctx.beginPath();ctx.arc(W/2,H/2+18,13,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.fillStyle=c;ctx.font='bold 10px monospace';ctx.textAlign='center';ctx.fillText('MUT',W/2,H/2+22);ctx.restore();
}

const DRAWS = {
  zinc_collapse:    drawZincCollapse,
  dna_contact_loss: drawDNAContactLoss,
  helix_break:      drawHelixBreak,
  loop_distortion:  drawLoopDistortion,
  surface_cavity:   drawSurfaceCavity,
  default:          drawDefault
};

const STRUCT_STAGES = {
  zinc_collapse:    ["WT: zinc stably coordinated","R175H distorts L2 loop","Zinc coordination weakening","Zinc ion released","L2 loop unfolds","Full domain misfolding"],
  dna_contact_loss: ["WT: R248/R273 contacts DNA","Mutation removes contact residue","DNA-binding weakens","H-bonds breaking","DNA separating","Loss of recognition"],
  helix_break:      ["WT: H2 helix stable","Salt bridge removed","Helix begins unwinding","Unwinding propagates","Domain reshaped","Loss of activity"],
  loop_distortion:  ["WT: Gly245 loop geometry ok","G245S adds side chain","Steric clash begins","Loop forced away","DNA approach blocked","Recognition abolished"],
  surface_cavity:   ["WT: Y220 fills pocket","Y220C removes Tyr","Surface pocket opens","Hydrophobic exposure","Destabilisation","Tm -6C / druggable cavity"],
  default:          ["Wild-type conformation","Mutation introduced","Local perturbation","Propagation","Interface altered","Reduced activity"]
};

window._SD = {};

function buildSliderCanvas(d, idx){
  const c=gc(d.status), isH=d.status==='critical';
  if(d.score<0.25){
    return `<div style="background:#0a1a0a;border:1px solid #1a3a1a;border-radius:6px;padding:12px;font-size:11px;color:#666;line-height:1.6;margin-bottom:12px">
      LOW effect score (${d.score}). Likely represents tolerated substitution. No pathological timeline applicable.</div>`;
  }
  const sk = d.struct_effect||'default';
  const stages = STRUCT_STAGES[sk]||STRUCT_STAGES['default'];
  const events = [
    {day:1,         label:"Single-cell mutation event", desc:"One cell acquires this mutation. Immune surveillance may clear it.", ec:'#555'},
    {day:isH?55:110,label:"Clonal expansion begins",   desc:"Mutant cell divides — passes to daughter cells. Still undetectable.", ec:c},
    {day:isH?180:365,label:"Detectable population",    desc:"Sensitive liquid biopsy might detect mutant fragments. Still asymptomatic.", ec:c},
    {day:isH?365:730,label:"Microenvironment effects", desc:"VEGF/TGF-β paracrine signalling starts influencing neighbouring cells.", ec:'#e24b4a'},
    {day:isH?730:1460,label:"Clinically detectable",   desc:"At typical detection sizes (~0.5-1cm). Billions of cell divisions occurred.", ec:'#e24b4a'},
  ];
  const maxDay = events[events.length-1].day+200;
  window._SD[idx] = {events,maxDay,sk,c,stages,cellKey:d.cell||'apoptosis'};
  const evHTML = events.map((e,i)=>
    `<div class="evt off" id="ev-${idx}-${i}"><div class="edot" style="background:${e.ec}"></div><div><strong>Day ~${e.day}: ${e.label}</strong><span>${e.desc}</span></div></div>`
  ).join('');
  const dots = stages.map((_,i)=>
    `<div class="sdot" id="sd-${idx}-${i}" style="background:${i===0?c:'#1e2030'}"></div>`
  ).join('');
  return `
  <div class="slider-box">
    <div class="sltitle">Mutation timeline + structural progression — drag slider</div>
    <div style="background:#0a0c1a;border:1px solid #1a1d3a;border-radius:5px;padding:7px;margin-bottom:8px;font-size:9px;color:#444;line-height:1.5">
      Population-level estimates from published TP53 kinetics. Not individual predictions.
    </div>
    <div class="slrow">
      <span class="sllbl">Day</span>
      <input type="range" id="sl-${idx}" min="0" max="${maxDay}" value="0" oninput="updateAll(${idx},parseInt(this.value))">
      <span class="slval" id="sv-${idx}">Day 0</span>
    </div>
    <div class="phase-bar"><div class="phase-fill" id="pf-${idx}" style="width:0%;background:${c}"></div><div class="pmark" id="pm-${idx}" style="left:0%"></div></div>
    <div style="margin-top:8px">${evHTML}</div>
  </div>
  <div class="prot-wrap">
    <div class="prot-title">Protein structural change — driven by slider above</div>
    <canvas id="pc-${idx}" height="200" style="height:200px"></canvas>
    <div class="prot-stage" id="psl-${idx}">${stages[0]}</div>
    <div class="stage-dots">${dots}</div>
  </div>`;
}

function buildCell(d,idx){
  const imp = CELLD[d.cell||'apoptosis']||CELLD['apoptosis'];
  const c = imp.color;
  const bars = ['Apoptosis activation','p21 induction','DNA repair','Tumour suppression'].map((l,i)=>{
    const v = d.status==='critical'?[3,4,15,2][i]:d.status==='affected'?[42,38,52,48][i]:[88,90,92,88][i];
    return `<div class="bar-row"><div class="bar-lbl"><span>${l}</span><span id="cb-${idx}-${i}" style="color:${c}">${v}%</span></div><div class="bar-track"><div id="cbf-${idx}-${i}" class="bar-fill" style="width:${v}%;background:${c}"></div></div></div>`;
  }).join('');
  return `<div class="cell-box">
    <div class="sl2" style="margin-top:0">Cell-level impact</div>
    <div class="cell-grid">
      <div class="cell-col">
        <svg width="56" height="56" viewBox="0 0 56 56"><ellipse cx="28" cy="28" rx="23" ry="21" fill="#0a1f0a" stroke="#2a5a2a" stroke-width="1.5"/><ellipse cx="28" cy="28" rx="9" ry="8" fill="#1a4a1a" stroke="#4CAF50" stroke-width="1.5"/><text x="28" y="31" text-anchor="middle" font-size="5" fill="#4CAF50" font-family="monospace">WT</text></svg>
        <span style="font-size:9px;color:#4CAF50;font-family:monospace">Normal</span>
        <span style="color:${c};font-size:14px;line-height:1">&#x2193;</span>
        <svg id="csq-${idx}" width="56" height="56" viewBox="0 0 56 56" style="transform-origin:center"><ellipse cx="28" cy="28" rx="23" ry="21" fill="#1f0808" stroke="${c}" stroke-width="1.5" stroke-dasharray="4,2"/><ellipse cx="28" cy="28" rx="11" ry="9" fill="#2a0808" stroke="${c}" stroke-width="1.5"/><circle cx="13" cy="18" r="2.5" fill="${c}" opacity="0.7"/><circle cx="43" cy="38" r="2" fill="${c}" opacity="0.5"/><text x="28" y="31" text-anchor="middle" font-size="5" fill="${c}" font-family="monospace">MUT</text></svg>
        <span style="font-size:9px;color:${c};font-family:monospace">Affected</span>
      </div>
      <div>
        <div class="cell-title" style="color:${c}">${imp.title}</div>
        <div class="cell-desc">${imp.desc}</div>
        <div style="margin-top:10px">${bars}</div>
      </div>
    </div>
  </div>`;
}

function updateAll(idx,day){
  const sd=window._SD[idx]; if(!sd) return;
  const {events,maxDay,sk,c,stages,cellKey}=sd;
  const imp=CELLD[cellKey]||CELLD['apoptosis'];
  const t=Math.max(0,Math.min(1,day/maxDay));
  const sv=document.getElementById('sv-'+idx);
  if(sv) sv.textContent=day===0?'Day 0':day>365?`Day ${day} (~${(day/365).toFixed(1)}yr)`:`Day ${day}`;
  const pct=(t*100).toFixed(1);
  const pf=document.getElementById('pf-'+idx),pm=document.getElementById('pm-'+idx);
  if(pf){pf.style.width=pct+'%';pf.textContent=day<(events[2]?.day||180)?'subclinical':day<(events[4]?.day||730)?'detectable':'clinical';}
  if(pm) pm.style.left=pct+'%';
  events.forEach((e,i)=>{const el=document.getElementById('ev-'+idx+'-'+i);if(el)el.classList.toggle('off',day<e.day);});
  const canvas=document.getElementById('pc-'+idx);
  if(canvas){(DRAWS[sk]||DRAWS['default'])(canvas.getContext('2d'),canvas.width,canvas.height,t,c);}
  const stageIdx=Math.min(stages.length-1,Math.floor(t*stages.length));
  const psl=document.getElementById('psl-'+idx);if(psl)psl.textContent=stages[stageIdx]||'';
  for(let i=0;i<stages.length;i++){const dot=document.getElementById('sd-'+idx+'-'+i);if(dot)dot.style.background=i<=stageIdx?c:'#1e2030';}
  const baseCrit=[3,4,15,2],baseAff=[42,38,52,48],baseNorm=[88,90,92,88];
  const base=imp.color==='#FF4C4C'?baseCrit:imp.color==='#FFA500'?baseAff:baseNorm;
  for(let i=0;i<4;i++){
    const current=Math.round(base[i]+(100-base[i])*(1-t));
    const bf=document.getElementById('cbf-'+idx+'-'+i),cb=document.getElementById('cb-'+idx+'-'+i);
    if(bf)bf.style.width=current+'%';if(cb)cb.textContent=current+'%';
  }
  const csq=document.getElementById('csq-'+idx);
  if(csq) csq.style.animation=t>0.3?`${imp.anim} ${2-t*0.5}s ease-in-out infinite`:'none';
}

function buildCard(d,idx){
  const c=gc(d.status);
  const hyp=d.hypothesis||`${d.label} — ${d.priority} priority (score ${d.score}).`;
  return `<div class="card" id="card-${idx}" data-priority="${d.priority}">
    <div class="chead" onclick="toggle(${idx})">
      <span class="crank">#${idx+1}</span>
      <div class="cdot" style="background:${c}"></div>
      <span class="clabel">${d.label}</span>
      <span class="cbadge" style="background:${c}22;color:${c};border:0.5px solid ${c}55">${d.priority}</span>
      <span style="font-family:monospace;font-size:12px;color:${c}">${d.score}</span>
      <span style="color:#3a3d5a;font-size:10px;margin-left:6px">${d.expType||''}</span>
      <span class="chev" id="chev-${idx}">&#x25B6;</span>
    </div>
    <div class="cbody" id="body-${idx}">
      <div class="cgrid">
        <div class="cleft">
          <div class="sl2" style="margin-top:0">Hypothesis</div>
          <div class="hyp-text">${hyp}</div>
          <div class="sl2">Structural annotation</div>
          <div class="drow"><span class="dl">Domain</span><span class="dv">${d.domain}</span></div>
          <div class="drow"><span class="dl">Mechanism</span><span class="dv">${d.mechanism}</span></div>
          <div class="sl2">Clinical data</div>
          <div class="drow"><span class="dl">ClinVar</span><span class="dv">${d.clinvar}</span></div>
          <div class="drow"><span class="dl">COSMIC</span><span class="dv">${d.cosmic}</span></div>
          <div class="drow"><span class="dl">Cancer types</span><span class="dv">${d.cancer}</span></div>
          <div class="drow"><span class="dl">Therapeutic</span><span class="dv">${d.therapeutic}</span></div>
          <div class="action-box"><div class="al">Recommended experiment</div><div class="at">${d.experiment}</div></div>
          <div class="sl2" style="margin-top:14px">Structural fluctuation — WT vs mutant</div>
          ${buildChain(d.pos,d.status,d.score)}
        </div>
        <div class="cright">
          ${buildSliderCanvas(d,idx)}
          ${buildCell(d,idx)}
        </div>
      </div>
    </div>
  </div>`;
}

const wrap=document.getElementById('cards');
RESIDUES.forEach((d,i)=>{ wrap.innerHTML+=buildCard(d,i); });

function toggle(idx){
  const body=document.getElementById('body-'+idx),chev=document.getElementById('chev-'+idx);
  const open=body.classList.contains('open');
  body.classList.toggle('open',!open);chev.classList.toggle('open',!open);
  if(!open){
    setTimeout(()=>{
      const canvas=document.getElementById('pc-'+idx);
      if(canvas){const d=RESIDUES[idx],sk=d.struct_effect||'default';(DRAWS[sk]||DRAWS['default'])(canvas.getContext('2d'),canvas.width,canvas.height,0,gc(d.status));}
    },60);
  }
}
function doFilter(p,btn){
  document.querySelectorAll('.fb').forEach(b=>b.classList.remove('active'));btn.classList.add('active');
  document.querySelectorAll('.card').forEach(c=>{c.style.display=(p==='ALL'||c.dataset.priority===p)?'block':'none';});
}
function expandAll(){document.querySelectorAll('.cbody').forEach(b=>b.classList.add('open'));document.querySelectorAll('.chev').forEach(c=>c.classList.add('open'));}
function collapseAll(){document.querySelectorAll('.cbody').forEach(b=>b.classList.remove('open'));document.querySelectorAll('.chev').forEach(c=>c.classList.remove('open'));}

// Auto-open first HIGH card and draw its canvas
const fh=document.querySelector('[data-priority="HIGH"] .cbody'),fc=document.querySelector('[data-priority="HIGH"] .chev');
if(fh){fh.classList.add('open');fc.classList.add('open');setTimeout(()=>{const c=document.querySelector('[data-priority="HIGH"] canvas');if(c){const d=RESIDUES[0],sk=d.struct_effect||'default';(DRAWS[sk]||DRAWS['default'])(c.getContext('2d'),c.width,c.height,0,gc(d.status));}},80);}
</script>
"""

    # ── HTML body (pure string) ───────────────────────────────────────────────
    BODY = """
<div class="header">
  __LOGO_TAG__
  <div>
    <div class="title">Hypothesis Lab</div>
    <div class="sub">__N_RESIDUES__ hypotheses — expand any card for structural animation, mutation timeline and cell impact</div>
  </div>
</div>

<div class="stats">
  <div class="sc"><div class="sn" style="color:#eee">__TOTAL__</div><div class="sl">Total</div></div>
  <div class="sc"><div class="sn" style="color:#FF4C4C">__N_HIGH__</div><div class="sl">HIGH</div></div>
  <div class="sc"><div class="sn" style="color:#FFA500">__N_MED__</div><div class="sl">MEDIUM</div></div>
  <div class="sc"><div class="sn" style="color:#4CA8FF">__N_LOW__</div><div class="sl">LOW</div></div>
  <div class="sc"><div class="sn" style="color:#FF4C4C;font-size:13px">__TOP_LABEL__</div><div class="sl">Top hit &middot; __TOP_SCORE__</div></div>
</div>

<div class="filter-bar">
  <span style="font-size:11px;color:#3a3d5a;font-family:monospace">Filter:</span>
  <button class="fb aa active" onclick="doFilter('ALL',this)">All</button>
  <button class="fb" onclick="doFilter('HIGH',this)" style="color:#FF4C4C88;border-color:#FF4C4C33">HIGH</button>
  <button class="fb am" onclick="doFilter('MEDIUM',this)">MEDIUM</button>
  <button class="fb al" onclick="doFilter('LOW',this)">LOW</button>
  <button class="fb" onclick="expandAll()" style="margin-left:auto">Expand all</button>
  <button class="fb" onclick="collapseAll()">Collapse all</button>
</div>

<div id="cards"></div>
"""

    # ── Assemble final HTML (substitution only — no f-string) ─────────────────
    html = (
        "<!DOCTYPE html><html><head>"
        '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">'
        + CSS
        + "</head><body>"
        + BODY
        .replace("__LOGO_TAG__",  logo_tag)
        .replace("__N_RESIDUES__", str(len(residues_data)))
        .replace("__TOTAL__",     str(len(residues_data)))
        .replace("__N_HIGH__",    str(n_high))
        .replace("__N_MED__",     str(n_med))
        .replace("__N_LOW__",     str(n_low))
        .replace("__TOP_LABEL__", str(top.get("label","—")))
        .replace("__TOP_SCORE__", str(top.get("score","—")))
        + JS
        .replace("__RESIDUES_JSON__", res_json)
        .replace("__CELL_JSON__",     cell_json)
        .replace("__PDB_DATA__",      pdb_esc)
        + "</body></html>"
    )
    return html


def render():
    if LOGO_B64:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px">'
            f'<img src="{LOGO_B64}" style="height:42px;object-fit:contain;border-radius:7px">'
            f'<div><strong style="font-size:1.15rem">Hypothesis Lab</strong>'
            f'<p style="color:#555;font-size:0.83rem;margin:0">Expand any card · drag slider → protein structure animates + cell diagram updates in sync</p>'
            f'</div></div>',
            unsafe_allow_html=True
        )
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

    pri_col = "priority_final" if "priority_final" in scored_df.columns else "priority"
    residues = []
    for _, row in scored_df.iterrows():
        pos       = int(row["residue_position"])
        score     = round(float(row.get("normalized_score", row.get("effect_score", 0))), 3)
        label     = str(row.get("mutation", f"Pos{pos}"))
        if label in ("nan", ""):
            label = f"Pos{pos}"
        priority  = str(row.get(pri_col, "LOW"))
        exp_type  = str(row.get("experiment_type", ""))
        hypothesis = str(row.get("hypothesis", ""))
        status    = {"HIGH": "critical", "MEDIUM": "affected", "LOW": "normal"}.get(priority, "normal")
        # Protein-aware hotspot lookup — works for any protein, not just TP53
        # enrichment_state already set above
        if info and info.get("genes"): _gene_hl = info["genes"][0]
        if not _gene_hl and enrichment_state:
            _gene_hl = (enrichment_state.get("uniprot",{}) or {}).get("gene_name","")
        if _gene_hl.upper() == "TP53" and pos in HOTSPOT_DATA:
            hs = HOTSPOT_DATA[pos]
        else:
            _doms_hl = (enrichment_state.get("uniprot",{}) or {}).get("domains",[]) if enrichment_state else []
            _pd_hl   = _get_pdata(_gene_hl) if _gene_hl else {}
            _cv_hl   = [] 
            if enrichment_state:
                _cv_hl = (enrichment_state.get("clinvar",{}) or {}).get("pathogenic",[]) + (enrichment_state.get("clinvar",{}) or {}).get("likely_pathogenic",[])
            hs = get_residue_annotation_for_protein(_gene_hl, pos, _doms_hl, priority, _cv_hl, _pd_hl)
        residues.append({
            "pos": pos, "label": label, "score": score,
            "priority": priority,
            "expType": "" if exp_type in ("nan", "") else exp_type,
            "status": status, "hypothesis": hypothesis,
            "mechanism":    hs.get("mechanism",    f"Effect score {score} from experimental assay. Mechanistic annotation available for known TP53 hotspots — Phase 2 will add live UniProt/PDB annotations for any protein."),
            "clinvar":      hs.get("clinvar",       "Not in hotspot database — Phase 2 integrates live ClinVar for all variants"),
            "cosmic":       hs.get("cosmic",        "Not in hotspot database — Phase 2 integrates live COSMIC"),
            "cancer":       hs.get("cancer",        "Not queried — Phase 2 pulls cancer type data automatically"),
            "therapeutic":  hs.get("therapeutic",   "No known targeted therapy in database — consult ClinVar or ChEMBL"),
            "domain":       hs.get("domain",        f"Position {pos} — domain annotation available for known hotspots. Phase 2 covers all proteins."),
            "experiment":   hs.get("experiment",    "Thermal shift assay and EMSA as first-line validation."),
            "cell":         hs.get("cell",          "apoptosis" if status == "critical" else "structural"),
            "struct_effect":hs.get("struct_effect", "default"),
        })

    html = build_html(residues, pdb_data, LOGO_B64)
    components.html(html, height=3500, scrolling=True)
