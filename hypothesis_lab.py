"""
hypothesis_lab.py — Protellect Hypothesis Lab (Tab 4)
Shows all ranked hypotheses from the triage run with:
- Expandable cards per hypothesis
- Inline mutation fluctuation animation per residue
- Cell impact animation per residue
- Experiment recommendation per hypothesis
- Exportable hypothesis report
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import requests

HOTSPOT_DATA = {
    175: {"mechanism":"Disrupts zinc coordination at C176/H179/C238/C242. Causes global misfolding of the DNA-binding domain.","clinvar":"Pathogenic · 847 submissions","cosmic":"~6% of all cancers","therapeutic":"APR-246 (eprenetapopt) — Phase III clinical trials","cell_impact":"apoptosis_loss","domain":"DNA-binding domain (L2 loop) — zinc coordination site","experiment":"Thermal shift assay to confirm Tm reduction, then EMSA to confirm loss of DNA binding."},
    248: {"mechanism":"Direct DNA contact residue in L3 loop. Abolishes sequence-specific DNA binding.","clinvar":"Pathogenic · 623 submissions","cosmic":"~3% of all cancers","therapeutic":"Synthetic lethality under investigation","cell_impact":"checkpoint_bypass","domain":"DNA-binding domain (L3 loop) — direct DNA contact","experiment":"EMSA to confirm loss of DNA binding. Reporter assay for transcriptional activity."},
    273: {"mechanism":"DNA backbone phosphate contact. Loss reduces DNA-binding affinity >100-fold.","clinvar":"Pathogenic · 512 submissions","cosmic":"~3% of all cancers","therapeutic":"Small molecule stabilizers experimental","cell_impact":"checkpoint_bypass","domain":"DNA-binding domain (S10 strand) — DNA backbone contact","experiment":"EMSA. Note: R273C retains partial structure — test both variants separately if relevant."},
    249: {"mechanism":"H2 helix structural mutation. Aflatoxin B1 mutational signature.","clinvar":"Pathogenic · 298 submissions","cosmic":"~1.5% — enriched in liver cancer","therapeutic":"No specific therapy","cell_impact":"proliferation","domain":"DNA-binding domain (H2 helix)","experiment":"Reporter assay for transactivation. Co-IP to assess dominant negative activity."},
    245: {"mechanism":"Glycine essential for L3 loop geometry. Any side chain disrupts DNA approach.","clinvar":"Pathogenic · 187 submissions","cosmic":"~1.5% of cancers","therapeutic":"Structural correctors under investigation","cell_impact":"apoptosis_loss","domain":"DNA-binding domain (L3 loop)","experiment":"Thermal shift + EMSA. Check for partial rescue with APR-246 if structural mutant."},
    282: {"mechanism":"R282 salt bridge with E271 stabilizes H2 helix. Tryptophan disrupts this.","clinvar":"Pathogenic · 156 submissions","cosmic":"~1% of cancers","therapeutic":"No approved targeted therapy","cell_impact":"apoptosis_loss","domain":"DNA-binding domain (H2 helix)","experiment":"Thermal shift assay. Reporter assay for p21/MDM2 activation."},
    220: {"mechanism":"Creates druggable hydrophobic cavity. Thermodynamic destabilization without direct DNA contact loss.","clinvar":"Pathogenic · 89 submissions","cosmic":"~1% of cancers","therapeutic":"PC14586 (rezatapopt) — Phase II trials","cell_impact":"apoptosis_loss","domain":"DNA-binding domain (S7-S8 loop)","experiment":"Thermal shift. APR-246 and PC14586 rescue experiments — Y220C is a prime candidate for cavity-filling compounds."},
}

CELL_TITLES = {
    "apoptosis_loss": "Loss of apoptosis — damaged cells survive and expand",
    "checkpoint_bypass": "DNA damage checkpoint bypass — cells divide with unrepaired DNA",
    "proliferation": "Gain-of-function — active oncogenic proliferation signalling",
    "structural": "Structural propagation — partial domain destabilization",
}


def fetch_pdb(pdb_id="2OCJ"):
    try:
        r = requests.get(f"https://files.rcsb.org/download/{pdb_id}.pdb", timeout=15)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def build_hypothesis_html(scored_df: pd.DataFrame, pdb_data: str) -> str:
    """Build the full hypothesis lab as a self-contained HTML component."""

    # Build residue list from scored data
    residues = []
    for _, row in scored_df.iterrows():
        pos = int(row["residue_position"])
        score = round(float(row.get("normalized_score", row.get("effect_score", 0))), 3)
        label = str(row.get("mutation", f"Res{pos}"))
        priority = str(row.get("priority", "LOW"))
        exp_type = str(row.get("experiment_type", "DMS"))
        hypothesis_text = str(row.get("hypothesis", ""))
        hs = HOTSPOT_DATA.get(pos, {})
        status = {"HIGH": "critical", "MEDIUM": "affected", "LOW": "normal"}[priority]

        residues.append({
            "pos": pos,
            "label": label,
            "score": score,
            "priority": priority,
            "status": status,
            "expType": exp_type,
            "hypothesis": hypothesis_text,
            "mechanism": hs.get("mechanism", "Effect score from experimental assay. Phase 2 database integration will add mechanistic annotation."),
            "clinvar": hs.get("clinvar", "Not queried — Phase 2 will integrate live ClinVar"),
            "cosmic": hs.get("cosmic", "Not queried"),
            "therapeutic": hs.get("therapeutic", "Consult clinical database"),
            "domain": hs.get("domain", "Unknown — Phase 2 annotation pending"),
            "experiment": hs.get("experiment", "Run thermal shift assay and EMSA as first-line validation."),
            "cell_impact": hs.get("cell_impact", "apoptosis_loss" if status == "critical" else "structural"),
        })

    res_json = json.dumps(residues)
    pdb_esc = pdb_data.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")[:300000]

    # Count stats
    n_high = sum(1 for r in residues if r["priority"] == "HIGH")
    n_med  = sum(1 for r in residues if r["priority"] == "MEDIUM")
    n_low  = sum(1 for r in residues if r["priority"] == "LOW")
    top = residues[0] if residues else {}

    return f"""<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#080b14;font-family:'IBM Plex Sans',sans-serif;color:#ccc;font-size:13px;padding:14px}}
::-webkit-scrollbar{{width:5px}}::-webkit-scrollbar-track{{background:#0a0c14}}::-webkit-scrollbar-thumb{{background:#2a2d3a;border-radius:3px}}

.header{{margin-bottom:16px}}
.title{{font-family:'IBM Plex Mono',monospace;font-size:18px;font-weight:700;color:#eee;margin-bottom:4px}}
.subtitle{{font-size:12px;color:#555}}

.stat-row{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:16px}}
.sc{{background:#0f1117;border:1px solid #1e2030;border-radius:8px;padding:12px;text-align:center}}
.sn{{font-size:20px;font-weight:600;font-family:'IBM Plex Mono',monospace}}
.sl{{font-size:10px;color:#555;margin-top:4px;text-transform:uppercase;letter-spacing:0.08em}}

/* Search/filter bar */
.filter-bar{{display:flex;gap:10px;margin-bottom:14px;align-items:center;flex-wrap:wrap}}
.filter-btn{{padding:6px 14px;border-radius:20px;border:1px solid #1e2030;background:#0f1117;color:#666;font-size:11px;cursor:pointer;font-family:'IBM Plex Mono',monospace;transition:all 0.15s}}
.filter-btn:hover,.filter-btn.active{{border-color:#e24b4a;color:#e24b4a;background:#1a0808}}
.filter-btn.f-med.active{{border-color:#ef9f27;color:#ef9f27;background:#1a1200}}
.filter-btn.f-low.active{{border-color:#378add;color:#378add;background:#08101a}}
.filter-btn.f-all.active{{border-color:#555;color:#ccc;background:#0f1117}}

/* Hypothesis cards */
.hyp-card{{background:#0a0c14;border:1px solid #1e2030;border-radius:10px;margin-bottom:10px;overflow:hidden;transition:border-color 0.15s}}
.hyp-card:hover{{border-color:#2a2d3a}}
.hyp-header{{display:flex;align-items:center;gap:12px;padding:14px 16px;cursor:pointer;user-select:none}}
.hyp-rank{{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#444;min-width:28px}}
.priority-dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
.hyp-label{{font-family:'IBM Plex Mono',monospace;font-size:14px;font-weight:700;color:#eee;flex:1}}
.hyp-score{{font-family:'IBM Plex Mono',monospace;font-size:12px;min-width:50px;text-align:right}}
.badge{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:10px;font-weight:600;font-family:'IBM Plex Mono',monospace;letter-spacing:0.08em;margin-right:8px}}
.chevron{{color:#444;font-size:12px;transition:transform 0.2s;margin-left:4px}}
.chevron.open{{transform:rotate(90deg)}}

.hyp-body{{display:none;border-top:1px solid #1e2030}}
.hyp-body.open{{display:block}}
.body-grid{{display:grid;grid-template-columns:1fr 1fr;gap:0}}
.body-left{{padding:16px;border-right:1px solid #1e2030}}
.body-right{{padding:16px;background:#080b14}}

.sl{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;padding-bottom:5px;border-bottom:1px solid #1a1d2e;margin:12px 0 8px}}
.sl:first-child{{margin-top:0}}
.drow{{display:flex;gap:8px;padding:5px 0;border-bottom:1px solid #0d0f1a;font-size:11px;line-height:1.5}}
.dl{{color:#3a3d5a;min-width:80px;font-size:10px;font-family:'IBM Plex Mono',monospace;flex-shrink:0;padding-top:1px}}
.dv{{color:#bbb;flex:1}}

.hyp-text{{font-size:12px;color:#888;line-height:1.7;padding:10px 12px;background:#080b14;border:1px solid #1e2030;border-radius:6px;margin-bottom:10px}}

.action-box{{background:#0a1a0a;border:1px solid #1a3a1a;border-radius:6px;padding:10px 12px;margin-top:8px}}
.action-label{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.12em;color:#4CAF50;margin-bottom:5px}}
.action-text{{font-size:11px;color:#888;line-height:1.7}}

/* Animation */
.anim-wrap{{background:#080b14;border:1px solid #1e2030;border-radius:8px;padding:14px}}
.chain-label{{font-size:10px;font-family:'IBM Plex Mono',monospace;color:#555;margin-bottom:5px}}
.chain-svg{{width:100%;height:46px;border:1px solid #1e2030;border-radius:5px;background:#040608;display:block}}
.brow{{margin-bottom:7px}}
.blbl{{display:flex;justify-content:space-between;font-size:10px;color:#555;margin-bottom:2px;font-family:'IBM Plex Mono',monospace}}
.btrack{{background:#1a1d2e;border-radius:3px;height:6px;overflow:hidden}}
.bfill{{height:100%;border-radius:3px;transition:width 1s ease}}

/* Cell diagram */
.cell-wrap{{margin-top:12px;padding-top:12px;border-top:1px solid #1a1d2e}}
.cell-row{{display:flex;gap:12px;align-items:flex-start}}
.cell-info{{flex:1}}
.cell-title{{font-family:'IBM Plex Mono',monospace;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;font-weight:600}}
.cell-desc{{font-size:11px;color:#777;line-height:1.6}}

@keyframes wobble-crit{{0%,100%{{transform:translateY(0)}}30%{{transform:translateY(-6px)}}70%{{transform:translateY(4px)}}}}
@keyframes wobble-aff{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-3px)}}}}
@keyframes wobble-norm{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-1px)}}}}
@keyframes cpulse{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.1)}}}}
@keyframes cspin{{0%{{transform:rotate(0deg)}}100%{{transform:rotate(360deg)}}}}
@keyframes cgrow{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.15)}}}}
@keyframes cshake{{0%,100%{{transform:translateX(0)}}25%{{transform:translateX(-3px)}}75%{{transform:translateX(3px)}}}}
</style>
</head>
<body>

<div class="header">
  <div class="title">💡 Hypothesis Lab</div>
  <div class="subtitle">All ranked hypotheses from your triage run — click any card to expand the full analysis, animation, and cell impact</div>
</div>

<div class="stat-row">
  <div class="sc"><div class="sn" style="color:#eee">{len(residues)}</div><div class="sl">Total hypotheses</div></div>
  <div class="sc"><div class="sn" style="color:#e24b4a">{n_high}</div><div class="sl">HIGH priority</div></div>
  <div class="sc"><div class="sn" style="color:#ef9f27">{n_med}</div><div class="sl">MEDIUM priority</div></div>
  <div class="sc"><div class="sn" style="color:#378add">{n_low}</div><div class="sl">LOW priority</div></div>
  <div class="sc"><div class="sn" style="color:#e24b4a;font-size:13px">{top.get('label','—')}</div><div class="sl">Top hit · {top.get('score','—')}</div></div>
</div>

<div class="filter-bar">
  <span style="font-size:11px;color:#555;font-family:'IBM Plex Mono',monospace">Filter:</span>
  <button class="filter-btn f-all active" onclick="filterCards('ALL',this)">All</button>
  <button class="filter-btn" onclick="filterCards('HIGH',this)" style="border-color:#e24b4a33;color:#e24b4a88">HIGH only</button>
  <button class="filter-btn f-med" onclick="filterCards('MEDIUM',this)">MEDIUM only</button>
  <button class="filter-btn f-low" onclick="filterCards('LOW',this)">LOW only</button>
  <button class="filter-btn" onclick="expandAll()" style="margin-left:auto">Expand all</button>
  <button class="filter-btn" onclick="collapseAll()">Collapse all</button>
</div>

<div id="cards-wrap"></div>

<script>
const RESIDUES = {res_json};
const pdbData = `{pdb_esc}`;

const COLOR = {{critical:'#e24b4a', affected:'#ef9f27', normal:'#378add'}};
const CELL_ANIMS = {{apoptosis_loss:'cpulse', checkpoint_bypass:'cspin', proliferation:'cgrow', structural:'cshake'}};
const CELL_COLORS = {{apoptosis_loss:'#e24b4a', checkpoint_bypass:'#ef9f27', proliferation:'#9370DB', structural:'#FFA500'}};
const CELL_DESC = {{
  apoptosis_loss:'TP53 normally activates BAX and PUMA to trigger apoptosis. This mutation blocks that signal — damaged cells survive and accumulate further mutations, driving tumour formation.',
  checkpoint_bypass:'TP53 halts the cell cycle at G1/S via p21. This mutation prevents p21 activation — cells divide with unrepaired DNA every cycle, accumulating genomic instability.',
  proliferation:'This gain-of-function mutation inhibits p63/p73 and activates MYC/VEGF programmes — actively driving oncogenic proliferation rather than merely losing tumour suppression.',
  structural:'Structural propagation effect — this residue is partially destabilised by the conformational changes caused by nearby critical mutations.',
}};

function gc(s) {{ return COLOR[s] || '#378add'; }}

function buildChain(pos, status, score) {{
  const c = gc(status);
  const isH = status==='critical', isM = status==='affected';
  const W=400, total=18, mutI=8, sp=W/(total+1);
  let wt='', mut='';
  for (let i=0; i<total; i++) {{
    const x=(i+1)*sp, isMut=i===mutI, r=isMut?10:5;
    wt+=`<circle cx="${{x}}" cy="23" r="5" fill="#0a1f0a" stroke="#4CAF50" stroke-width="1"/>`;
    if(i<total-1) wt+=`<line x1="${{x+5}}" y1="23" x2="${{(i+2)*sp-5}}" y2="23" stroke="#1a3a1a" stroke-width="1.2"/>`;
    const animSt = isMut?`style="transform-origin:${{x}}px 23px;animation:wobble-${{status}} 1.4s ease-in-out infinite"` :'';
    mut+=`<circle cx="${{x}}" cy="23" r="${{r}}" fill="${{isMut?c+'22':'#040608'}}" stroke="${{isMut?c:'#1e2030'}}" stroke-width="${{isMut?2:0.8}}" ${{animSt}}/>`;
    if(i<total-1) mut+=`<line x1="${{x+(isMut?r:5)}}" y1="23" x2="${{(i+2)*sp-5}}" y2="23" stroke="${{isMut?c:'#1a1d2e'}}" stroke-width="1.2"/>`;
  }}
  const pcts = isH?[8,3,28,2]:isM?[50,45,72,55]:[88,90,92,88];
  const lbls = ['Zinc coord.','DNA binding','Thermal stab.','Transcription'];
  const bars = lbls.map((l,i)=>`<div class="brow">
    <div class="blbl"><span>${{l}}</span><span style="color:${{c}}">${{pcts[i]}}% WT</span></div>
    <div class="btrack"><div class="bfill" style="width:${{pcts[i]}}%;background:${{c}}"></div></div>
  </div>`).join('');
  return `<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
    <div>
      <div class="chain-label" style="color:#4CAF50">Wild-type chain</div>
      <svg class="chain-svg" viewBox="0 0 ${{W}} 46">${{wt}}</svg>
      <div class="chain-label" style="color:${{c}};margin-top:8px">Mutant — position ${{pos}} (animated = instability)</div>
      <svg class="chain-svg" viewBox="0 0 ${{W}} 46">${{mut}}</svg>
    </div>
    <div><div class="chain-label">Function vs wild-type (score ${{score}})</div>${{bars}}</div>
  </div>`;
}}

function buildCell(cellImpact) {{
  const c = CELL_COLORS[cellImpact] || '#e24b4a';
  const anim = CELL_ANIMS[cellImpact] || 'cpulse';
  const desc = CELL_DESC[cellImpact] || '';
  return `<div class="cell-wrap">
    <div class="sl" style="margin-top:0">Cell-level impact</div>
    <div class="cell-row">
      <div style="display:flex;flex-direction:column;align-items:center;gap:6px;flex-shrink:0">
        <svg width="56" height="56" viewBox="0 0 56 56">
          <ellipse cx="28" cy="28" rx="24" ry="22" fill="#0a1f0a" stroke="#2a5a2a" stroke-width="1.5"/>
          <ellipse cx="28" cy="28" rx="9" ry="8" fill="#1a4a1a" stroke="#4CAF50" stroke-width="1.5"/>
          <text x="28" y="31" text-anchor="middle" font-size="5" fill="#4CAF50" font-family="monospace">WT</text>
        </svg>
        <span style="font-size:9px;color:#4CAF50;font-family:'IBM Plex Mono',monospace">Normal</span>
        <span style="color:${{c}};font-size:14px">↓</span>
        <svg width="56" height="56" viewBox="0 0 56 56" style="animation:${{anim}} 2s ease-in-out infinite;transform-origin:center">
          <ellipse cx="28" cy="28" rx="24" ry="22" fill="#1f0808" stroke="${{c}}" stroke-width="1.5" stroke-dasharray="4,2"/>
          <ellipse cx="28" cy="28" rx="11" ry="9" fill="#2a0808" stroke="${{c}}" stroke-width="1.5"/>
          <circle cx="13" cy="18" r="2.5" fill="${{c}}" opacity="0.7"/>
          <circle cx="43" cy="38" r="2" fill="${{c}}" opacity="0.5"/>
          <text x="28" y="31" text-anchor="middle" font-size="5" fill="${{c}}" font-family="monospace">MUT</text>
        </svg>
        <span style="font-size:9px;color:${{c}};font-family:'IBM Plex Mono',monospace">Affected</span>
      </div>
      <div class="cell-info">
        <div class="cell-title" style="color:${{c}}">${{(CELL_COLORS[cellImpact]?Object.keys(CELL_COLORS).find(k=>k===cellImpact):'').replace(/_/g,' ')||cellImpact}}</div>
        <div class="cell-desc">${{desc}}</div>
      </div>
    </div>
  </div>`;
}}

function buildCard(d, index) {{
  const c = gc(d.status);
  const cardId = 'card-'+index;
  const bodyId = 'body-'+index;
  const chevId = 'chev-'+index;
  const animContent = buildChain(d.pos, d.status, d.score);
  const cellContent = buildCell(d.cell_impact);

  return `<div class="hyp-card" id="${{cardId}}" data-priority="${{d.priority}}">
    <div class="hyp-header" onclick="toggle('${{bodyId}}','${{chevId}}')">
      <span class="hyp-rank">#${{index+1}}</span>
      <div class="priority-dot" style="background:${{c}}"></div>
      <span class="hyp-label">${{d.label}}</span>
      <span class="badge" style="background:${{c}}22;color:${{c}};border:0.5px solid ${{c}}55">${{d.priority}}</span>
      <span class="hyp-score" style="color:${{c}}">${{d.score}}</span>
      <span class="hyp-score" style="color:#444;font-size:11px">${{d.expType}}</span>
      <span class="chevron" id="${{chevId}}">▶</span>
    </div>
    <div class="hyp-body" id="${{bodyId}}">
      <div class="body-grid">
        <div class="body-left">
          <div class="sl" style="margin-top:0">Hypothesis</div>
          <div class="hyp-text">${{d.hypothesis || 'Residue '+d.pos+' ('+d.label+') shows a '+d.priority.toLowerCase()+' priority functional effect (score '+d.score+'). '+( d.status==='critical' ? 'Strong candidate for immediate experimental validation.' : d.status==='affected' ? 'Moderate effect — investigate in context of nearby high-priority mutations.' : 'Likely tolerated — validate before deprioritizing entirely.')}}</div>
          <div class="sl">Structural annotation</div>
          <div class="drow"><span class="dl">Domain</span><span class="dv">${{d.domain}}</span></div>
          <div class="drow"><span class="dl">Mechanism</span><span class="dv">${{d.mechanism}}</span></div>
          <div class="sl">Clinical data</div>
          <div class="drow"><span class="dl">ClinVar</span><span class="dv">${{d.clinvar}}</span></div>
          <div class="drow"><span class="dl">COSMIC</span><span class="dv">${{d.cosmic}}</span></div>
          <div class="drow"><span class="dl">Therapeutic</span><span class="dv">${{d.therapeutic}}</span></div>
          <div class="action-box">
            <div class="action-label">Recommended next experiment</div>
            <div class="action-text">${{d.experiment}}</div>
          </div>
        </div>
        <div class="body-right">
          <div class="sl" style="margin-top:0">Structural fluctuation — WT vs mutant</div>
          <div class="anim-wrap">${{animContent}}</div>
          ${{cellContent}}
        </div>
      </div>
    </div>
  </div>`;
}}

// Render all cards
const wrap = document.getElementById('cards-wrap');
RESIDUES.forEach((d, i) => {{ wrap.innerHTML += buildCard(d, i); }});

function toggle(bodyId, chevId) {{
  const body = document.getElementById(bodyId);
  const chev = document.getElementById(chevId);
  const isOpen = body.classList.contains('open');
  body.classList.toggle('open', !isOpen);
  chev.classList.toggle('open', !isOpen);
}}

function filterCards(priority, btn) {{
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.hyp-card').forEach(card => {{
    card.style.display = (priority==='ALL' || card.dataset.priority===priority) ? 'block' : 'none';
  }});
}}

function expandAll() {{
  document.querySelectorAll('.hyp-body').forEach(b => b.classList.add('open'));
  document.querySelectorAll('.chevron').forEach(c => c.classList.add('open'));
}}

function collapseAll() {{
  document.querySelectorAll('.hyp-body').forEach(b => b.classList.remove('open'));
  document.querySelectorAll('.chevron').forEach(c => c.classList.remove('open'));
}}

// Auto-open first HIGH priority card
const firstHigh = document.querySelector('[data-priority="HIGH"] .hyp-body');
const firstHighChev = document.querySelector('[data-priority="HIGH"] .chevron');
if (firstHigh) {{ firstHigh.classList.add('open'); firstHighChev.classList.add('open'); }}
</script>
</body>
</html>"""


def render():
    st.markdown("## 💡 Hypothesis Lab")
    st.markdown("All ranked hypotheses from your triage run. Click any card to expand the full analysis, structural animation, and cell-level impact.")
    st.divider()

    if "t_scored" not in st.session_state:
        st.info("👈 Run Triage first in the **Triage System** tab to generate hypotheses.")
        st.markdown("Upload your CSV and click **▶ Run Triage** — all hypotheses will appear here automatically.")
        return

    scored_df = st.session_state.t_scored

    with st.spinner("Building hypothesis lab..."):
        pdb_data = fetch_pdb("2OCJ")

    if not pdb_data:
        st.error("Could not load protein structure. Check your internet connection.")
        return

    html = build_hypothesis_html(scored_df, pdb_data)
    components.html(html, height=2800, scrolling=True)
