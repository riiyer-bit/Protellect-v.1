"""
Tab 3 — Protein Explorer
• Large interactive 3D structure (backbone + ribbon + residue spheres)
• Clickable residues → detailed breakdown + "If Mutated" section with slider
• Mutation animation (conformational fluctuation simulation)
• Disease–mutation–genomic implication table
"""

import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json
import math
import numpy as np
from utils.alphafold import AlphaFoldClient
from utils.uniprot import UniProtClient
from utils.pubmed import render_citations


def render_explorer_tab(
    protein_data:  dict,
    alphafold_pdb: str | None,
    clinvar_data:  dict | None,
    ml_scores:     dict | None,
    papers:        list | None,
    gene_name:     str,
):
    st.markdown("#### 🔬 Protein Explorer")
    st.caption("Click any residue sphere to inspect its properties and predicted mutational consequences.")

    # ── Large 3D explorer ─────────────────────────────────────────────────────
    _render_large_structure(alphafold_pdb, clinvar_data, ml_scores, protein_data)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── Residue detail panel ──────────────────────────────────────────────────
    _render_residue_detail_panel(protein_data, clinvar_data, ml_scores, alphafold_pdb)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── Disease–mutation–genomic implication list ─────────────────────────────
    _render_disease_mutation_map(protein_data, clinvar_data, ml_scores, gene_name)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    render_citations(papers or [], max_show=4)


# ─── Large structure viewer ────────────────────────────────────────────────────
def _render_large_structure(pdb_text, clinvar_data, ml_scores, pdata):
    if not pdb_text:
        st.warning("No AlphaFold structure available. Enter a valid UniProt accession for 3D visualisation.")
        return

    top_vars   = (ml_scores or {}).get("top_variants", [])
    bfactors   = AlphaFoldClient.parse_bfactors(pdb_text)
    variants   = (clinvar_data or {}).get("variants", [])

    # Pathogenic positions
    path_positions = {}
    for v in top_vars[:40]:
        pos = v.get("start") or v.get("position")
        try:
            p = int(pos)
            score = v.get("ml_pathogenicity", 0)
            cond  = v.get("condition", "")
            sig   = v.get("clinical_significance", "")
            path_positions[p] = {"score": score, "condition": cond, "sig": sig,
                                  "variant": v.get("variant_name",""), "rank": v.get("ml_rank","NEUTRAL")}
        except (TypeError, ValueError):
            pass

    path_pos_js  = json.dumps({str(k): v for k, v in path_positions.items()})
    pdb_escaped  = pdb_text.replace("`", "\\`").replace("\\", "\\\\")

    # Sequence for residue list
    sequence = UniProtClient.extract_sequence(pdata)
    seq_js   = json.dumps(sequence)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.1.0/3Dmol-min.js"></script>
      <style>
        * {{ box-sizing: border-box; margin:0; padding:0; }}
        body {{ background:#060e18; font-family:Inter,sans-serif; display:flex; flex-direction:column; }}
        #controls {{ display:flex; gap:10px; padding:10px; background:#0a1929; border-bottom:1px solid #1e3a5f; flex-wrap:wrap; }}
        .ctrl-btn {{
          background:#0d2a4a; color:#8ab4d4; border:1px solid #1e3a5f;
          padding:5px 14px; border-radius:20px; cursor:pointer; font-size:12px;
          transition:all 0.2s;
        }}
        .ctrl-btn:hover, .ctrl-btn.active {{ background:#00d4ff; color:#000; font-weight:700; border-color:#00d4ff; }}
        #viewer-wrap {{ position:relative; }}
        #viewer {{ width:100%; height:600px; }}
        #info-panel {{
          position:absolute; top:10px; right:10px; width:260px;
          background:rgba(6,14,24,0.92); border:1px solid #1e3a5f;
          border-radius:10px; padding:14px; font-size:12px; color:#c9d8e8;
          display:none; max-height:580px; overflow-y:auto;
        }}
        #info-panel h3 {{ color:#00d4ff; font-size:14px; margin-bottom:8px; }}
        #info-panel .prop {{ margin:5px 0; }}
        #info-panel .prop span {{ color:#8ab4d4; }}
        #info-panel .rank-badge {{
          display:inline-block; padding:2px 10px; border-radius:12px;
          font-weight:700; font-size:11px; margin-bottom:6px;
        }}
        .legend {{
          display:flex; gap:14px; padding:8px 12px; background:#0a1929;
          border-top:1px solid #1e3a5f; flex-wrap:wrap;
        }}
        .leg-item {{ display:flex; align-items:center; gap:6px; font-size:11px; color:#8ab4d4; }}
        .leg-dot {{ width:10px; height:10px; border-radius:50%; flex-shrink:0; }}
        #spin-toggle {{ position:absolute; top:10px; left:10px; }}
      </style>
    </head>
    <body>
    <div id="controls">
      <button class="ctrl-btn active" onclick="setStyle('cartoon')">🎀 Cartoon</button>
      <button class="ctrl-btn" onclick="setStyle('stick')">🦴 Stick</button>
      <button class="ctrl-btn" onclick="setStyle('sphere')">⚬ Sphere</button>
      <button class="ctrl-btn" onclick="setStyle('surface')">🌊 Surface</button>
      <button class="ctrl-btn" onclick="toggleSpin()">🔄 Spin</button>
      <button class="ctrl-btn" onclick="resetView()">🎯 Reset</button>
      <button class="ctrl-btn" onclick="togglePathogenic()">🔴 Toggle Pathogenic</button>
      <button class="ctrl-btn" onclick="toggleLabels()">🏷️ Labels</button>
    </div>
    <div id="viewer-wrap">
      <div id="viewer"></div>
      <div id="info-panel">
        <h3 id="ip-title">Residue Info</h3>
        <div id="ip-content"></div>
      </div>
    </div>
    <div class="legend">
      <div class="leg-item"><div class="leg-dot" style="background:#0053D6;"></div>pLDDT ≥90 (very high)</div>
      <div class="leg-item"><div class="leg-dot" style="background:#65CBF3;"></div>pLDDT 70–90</div>
      <div class="leg-item"><div class="leg-dot" style="background:#FFDB13;"></div>pLDDT 50–70</div>
      <div class="leg-item"><div class="leg-dot" style="background:#FF7D45;"></div>pLDDT &lt;50</div>
      <div class="leg-item"><div class="leg-dot" style="background:#ff2d55;border:2px solid white;"></div>Pathogenic variant</div>
      <div class="leg-item"><div class="leg-dot" style="background:#ffd60a;border:2px solid white;"></div>VUS / Medium</div>
    </div>
    <script>
    const pathData = {path_pos_js};
    const sequence = {seq_js};
    let spinning = false;
    let showLabels = false;
    let showPathogenic = true;
    let currentStyle = 'cartoon';

    const viewer = $3Dmol.createViewer(document.getElementById('viewer'), {{
      backgroundColor: '0x060e18'
    }});

    const pdbText = `{pdb_escaped}`;
    viewer.addModel(pdbText, 'pdb');
    applyStyle();

    // Add pathogenic spheres
    function addPathogenicSpheres() {{
      Object.entries(pathData).forEach(([pos, info]) => {{
        const rk = info.rank;
        const col = rk === 'CRITICAL' ? '#ff2d55' : rk === 'HIGH' ? '#ff6b00' :
                    rk === 'MEDIUM'   ? '#ffd60a' : '#636e72';
        viewer.addStyle(
          {{resi: parseInt(pos), atom: 'CA'}},
          {{sphere: {{radius: 1.4, color: col, opacity: 0.9}}}}
        );
      }});
    }}
    addPathogenicSpheres();

    viewer.setClickable({{}}, true, function(atom) {{
      showResidueInfo(atom);
    }});

    viewer.zoomTo();
    viewer.render();

    function applyStyle() {{
      viewer.setStyle({{}}, {{
        cartoon: {{
          colorfunc: function(atom) {{
            const b = atom.b;
            if (b >= 90) return '#0053D6';
            if (b >= 70) return '#65CBF3';
            if (b >= 50) return '#FFDB13';
            return '#FF7D45';
          }},
          thickness: 0.5,
        }}
      }});
      if (currentStyle === 'stick') {{
        viewer.addStyle({{}}, {{stick: {{colorscheme: 'chainHetatm', radius: 0.15}}}});
      }} else if (currentStyle === 'sphere') {{
        viewer.setStyle({{}}, {{sphere: {{colorfunc: function(atom) {{
          const b = atom.b;
          if (b >= 90) return '#0053D6';
          if (b >= 70) return '#65CBF3';
          if (b >= 50) return '#FFDB13';
          return '#FF7D45';
        }}, radius: 0.8}}}});
      }} else if (currentStyle === 'surface') {{
        viewer.addSurface($3Dmol.SurfaceType.VDW, {{
          colorfunc: function(atom) {{
            const b = atom.b;
            if (b >= 90) return '#0053D6';
            if (b >= 70) return '#65CBF3';
            if (b >= 50) return '#FFDB13';
            return '#FF7D45';
          }}, opacity: 0.75
        }});
      }}
      addPathogenicSpheres();
      viewer.render();
    }}

    function setStyle(s) {{
      currentStyle = s;
      viewer.removeAllSurfaces();
      document.querySelectorAll('.ctrl-btn').forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');
      applyStyle();
    }}

    function toggleSpin() {{
      spinning = !spinning;
      viewer.spin(spinning ? 'y' : false, 0.5);
    }}

    function resetView() {{
      viewer.zoomTo(); viewer.render();
    }}

    function togglePathogenic() {{
      showPathogenic = !showPathogenic;
      applyStyle();
    }}

    function toggleLabels() {{
      showLabels = !showLabels;
      viewer.removeAllLabels();
      if (showLabels) {{
        Object.entries(pathData).forEach(([pos, info]) => {{
          if (info.rank === 'CRITICAL' || info.rank === 'HIGH') {{
            viewer.addLabel('P' + pos, {{
              position: {{resi: parseInt(pos), atom: 'CA'}},
              backgroundColor: '#ff2d55', backgroundOpacity: 0.8,
              fontSize: 10, fontColor: 'white', borderRadius: 4,
            }});
          }}
        }});
      }}
      viewer.render();
    }}

    const aa3to1 = {{ALA:'A',ARG:'R',ASN:'N',ASP:'D',CYS:'C',GLN:'Q',GLU:'E',
                     GLY:'G',HIS:'H',ILE:'I',LEU:'L',LYS:'K',MET:'M',PHE:'F',
                     PRO:'P',SER:'S',THR:'T',TRP:'W',TYR:'Y',VAL:'V'}};
    const aaFullName = {{A:'Alanine',R:'Arginine',N:'Asparagine',D:'Aspartate',
                         C:'Cysteine',Q:'Glutamine',E:'Glutamate',G:'Glycine',
                         H:'Histidine',I:'Isoleucine',L:'Leucine',K:'Lysine',
                         M:'Methionine',F:'Phenylalanine',P:'Proline',S:'Serine',
                         T:'Threonine',W:'Tryptophan',Y:'Tyrosine',V:'Valine'}};
    const hydropathy = {{A:1.8,R:-4.5,N:-3.5,D:-3.5,C:2.5,Q:-3.5,E:-3.5,
                         G:-0.4,H:-3.2,I:4.5,L:3.8,K:-3.9,M:1.9,F:2.8,
                         P:-1.6,S:-0.8,T:-0.7,W:-0.9,Y:-1.3,V:4.2}};

    function showResidueInfo(atom) {{
      const pos  = atom.resi;
      const res3 = atom.resn || '';
      const res1 = aa3to1[res3.toUpperCase()] || '?';
      const full = aaFullName[res1] || res3;
      const plddt = atom.b || 0;
      const conf  = plddt >= 90 ? 'Very High' : plddt >= 70 ? 'Confident' :
                    plddt >= 50 ? 'Low' : 'Very Low';
      const hydro = hydropathy[res1] !== undefined ? hydropathy[res1].toFixed(1) : '?';
      const varInfo = pathData[String(pos)];

      let html = '';
      if (varInfo) {{
        const rk = varInfo.rank;
        const rankCol = {{CRITICAL:'#ff2d55',HIGH:'#ff6b00',MEDIUM:'#ffd60a',NEUTRAL:'#636e72'}}[rk] || '#636e72';
        const rankBg  = {{CRITICAL:'#3d0010',HIGH:'#3d1a00',MEDIUM:'#3d3000',NEUTRAL:'#1a1a2e'}}[rk] || '#1a1a2e';
        html += `<span class="rank-badge" style="background:${{rankBg}};color:${{rankCol}};border:1px solid ${{rankCol}};">${{rk}}</span>`;
      }}

      html += `
        <div class="prop"><span>Residue:</span> <b>${{res1}} / ${{full}}</b></div>
        <div class="prop"><span>Position:</span> <b>${{pos}}</b></div>
        <div class="prop"><span>pLDDT:</span> <b>${{plddt.toFixed(1)}} (${{conf}})</b></div>
        <div class="prop"><span>Hydropathy:</span> <b>${{hydro}}</b></div>
      `;

      if (varInfo) {{
        html += `
          <hr style="border-color:#1e3a5f;margin:8px 0;">
          <div class="prop"><span>Variant:</span> ${{varInfo.variant || '—'}}</div>
          <div class="prop"><span>Significance:</span> ${{varInfo.sig || '—'}}</div>
          <div class="prop"><span>Condition:</span> ${{varInfo.condition || '—'}}</div>
          <div class="prop"><span>ML Score:</span> <b style="color:#00d4ff">${{(varInfo.score*100).toFixed(0)}}%</b></div>
        `;
      }}

      document.getElementById('ip-title').textContent = res3 + pos;
      document.getElementById('ip-content').innerHTML = html;
      document.getElementById('info-panel').style.display = 'block';
    }}
    </script>
    </body>
    </html>
    """
    components.html(html, height=720, scrolling=False)


# ─── Residue detail + mutation panel ──────────────────────────────────────────
def _render_residue_detail_panel(pdata, clinvar_data, ml_scores, pdb_text):
    st.markdown("#### 🔍 Residue Mutation Analysis")
    st.caption("Select a residue position to explore mutational consequences.")

    sequence = UniProtClient.extract_sequence(pdata)
    if not sequence:
        st.info("No sequence available.")
        return

    bfactors = AlphaFoldClient.parse_bfactors(pdb_text) if pdb_text else {}
    variants = (clinvar_data or {}).get("variants", [])

    # Map positions to variant data
    pos_to_variant = {}
    for v in variants:
        pos = v.get("start") or v.get("position")
        try:
            pos_to_variant[int(pos)] = v
        except (TypeError, ValueError):
            pass

    col_sel, col_res = st.columns([1, 2])

    with col_sel:
        max_pos  = len(sequence)
        position = st.number_input(
            "Residue position", min_value=1, max_value=max_pos, value=1, step=1,
            help="Enter a residue number (1-indexed)"
        )
        position = int(position)
        aa = sequence[position - 1] if position <= len(sequence) else "?"

        plddt = bfactors.get(position, None)
        vdata = pos_to_variant.get(position)

        st.markdown(f"""
        <div class='card'>
          <h4>Residue {position} — {aa}</h4>
          <p>pLDDT: <b style='color:#00d4ff;'>{f'{plddt:.1f}' if plddt else '—'}</b><br>
          Structural confidence: <b>{AlphaFoldClient.confidence_label(plddt) if plddt else '—'}</b></p>
        </div>
        """, unsafe_allow_html=True)

    with col_res:
        _render_mutation_panel(position, aa, vdata, sequence, bfactors)


def _render_mutation_panel(position, aa, vdata, sequence, bfactors):
    AA_NAMES = {
        "A":"Alanine","R":"Arginine","N":"Asparagine","D":"Aspartate","C":"Cysteine",
        "Q":"Glutamine","E":"Glutamate","G":"Glycine","H":"Histidine","I":"Isoleucine",
        "L":"Leucine","K":"Lysine","M":"Methionine","F":"Phenylalanine","P":"Proline",
        "S":"Serine","T":"Threonine","W":"Tryptophan","Y":"Tyrosine","V":"Valine",
    }
    AA_HYDRO = {
        "A":1.8,"R":-4.5,"N":-3.5,"D":-3.5,"C":2.5,"Q":-3.5,"E":-3.5,"G":-0.4,
        "H":-3.2,"I":4.5,"L":3.8,"K":-3.9,"M":1.9,"F":2.8,"P":-1.6,"S":-0.8,
        "T":-0.7,"W":-0.9,"Y":-1.3,"V":4.2,
    }
    AA_CHARGE = {"R":1,"H":0.5,"K":1,"D":-1,"E":-1}

    full_name = AA_NAMES.get(aa, "Unknown")
    hydro     = AA_HYDRO.get(aa, 0)
    charge    = AA_CHARGE.get(aa, 0)

    tab_props, tab_mutant = st.tabs(["Properties", "If Mutated →"])

    with tab_props:
        c1, c2 = st.columns(2)
        c1.metric("Amino Acid", aa)
        c1.metric("Full Name",  full_name)
        c2.metric("Hydropathy Index", f"{hydro:+.1f}")
        c2.metric("Charge",    f"{charge:+.0f}" if charge else "Neutral")

        if vdata:
            sig  = vdata.get("clinical_significance","—")
            cond = vdata.get("condition","—")
            rank = vdata.get("ml_rank") or vdata.get("triage_rank","—")
            rank_col = {"CRITICAL":"#ff2d55","HIGH":"#ff6b00","MEDIUM":"#ffd60a","NEUTRAL":"#636e72"}.get(rank,"#636e72")
            st.markdown(
                f"<div class='card' style='border-color:{rank_col};'>"
                f"<h4 style='color:{rank_col};'>⚠️ ClinVar Variant at This Position</h4>"
                f"<p>Significance: <b>{sig}</b><br>Condition: {cond}<br>"
                f"Variant: {vdata.get('variant_name','—')}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.success("No ClinVar variant reported at this position.", icon="✅")

    with tab_mutant:
        st.markdown("**Simulate amino acid substitution:**")
        all_aa   = list(AA_NAMES.keys())
        all_aa   = [a for a in all_aa if a != aa]
        alt_aa   = st.selectbox("Substitute with:", all_aa, key=f"alt_aa_{position}")

        severity_slider = st.slider(
            "Perturbation magnitude", 0.0, 1.0, 0.5, 0.05,
            key=f"slider_{position}",
            help="Simulates how structurally disruptive the mutation may be.",
        )

        _render_mutation_animation(position, aa, alt_aa, severity_slider, sequence, bfactors)
        _render_mutation_genomic_implications(position, aa, alt_aa)


def _render_mutation_animation(position, orig, alt, severity, sequence, bfactors):
    """Render a plotly animation of pLDDT profile perturbation."""
    if not bfactors:
        return

    positions = sorted(bfactors.keys())
    window    = 30
    center    = min(max(position, window+1), max(positions)-window)
    display_pos = [p for p in positions if abs(p - center) <= window]

    plddt_vals = [bfactors.get(p, 70) for p in display_pos]

    # Simulated mutant profile: dip around the mutation site
    import math
    mut_vals = []
    for i, p in enumerate(display_pos):
        dist = abs(p - position)
        drop = severity * 30 * math.exp(-0.5 * (dist / 5)**2)
        mut_vals.append(max(0, plddt_vals[i] - drop))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=display_pos, y=plddt_vals,
        mode="lines+markers",
        name="Wild-type",
        line=dict(color="#00d4ff", width=2),
        marker=dict(size=4),
    ))
    fig.add_trace(go.Scatter(
        x=display_pos, y=mut_vals,
        mode="lines+markers",
        name=f"Mutant {orig}{position}{alt}",
        line=dict(color="#ff2d55", width=2, dash="dash"),
        marker=dict(size=4),
    ))
    fig.add_vline(x=position, line_color="#ffd60a", line_dash="dot",
                  annotation_text=f"p.{orig}{position}{alt}", annotation_font_color="#ffd60a")

    # Shade difference
    fig.add_trace(go.Scatter(
        x=display_pos + display_pos[::-1],
        y=mut_vals + plddt_vals[::-1],
        fill="toself",
        fillcolor="rgba(255,45,85,0.1)",
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False,
    ))

    fig.update_layout(
        paper_bgcolor="#060e18", plot_bgcolor="#060e18",
        font_color="#8ab4d4",
        xaxis=dict(title="Residue Position", gridcolor="#1e3a5f"),
        yaxis=dict(title="pLDDT Score", range=[0,100], gridcolor="#1e3a5f"),
        legend=dict(bgcolor="#060e18"),
        margin=dict(t=10, b=30, l=30, r=10),
        height=260,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption(f"Simulated structural perturbation of **{orig}{position}{alt}** · severity: {severity:.0%}")


def _render_mutation_genomic_implications(position, orig, alt):
    """Rule-based genomic implication text."""
    AA_CHARGE = {"R":1,"H":0.5,"K":1,"D":-1,"E":-1}
    AA_HYDRO  = {"A":1.8,"R":-4.5,"N":-3.5,"D":-3.5,"C":2.5,"Q":-3.5,"E":-3.5,"G":-0.4,
                 "H":-3.2,"I":4.5,"L":3.8,"K":-3.9,"M":1.9,"F":2.8,"P":-1.6,"S":-0.8,
                 "T":-0.7,"W":-0.9,"Y":-1.3,"V":4.2}
    hydro_orig = AA_HYDRO.get(orig, 0)
    hydro_alt  = AA_HYDRO.get(alt, 0)
    chg_orig   = AA_CHARGE.get(orig, 0)
    chg_alt    = AA_CHARGE.get(alt, 0)
    hydro_diff = abs(hydro_orig - hydro_alt)
    chg_diff   = abs(chg_orig - chg_alt)

    implications = []
    if alt == "*":
        implications.append("🔴 **Nonsense / stop-gain mutation** — premature termination codon → likely NMD (Nonsense-Mediated Decay) → loss-of-function.")
    if hydro_diff > 3:
        implications.append(f"🔶 Large hydropathy shift ({hydro_diff:.1f}) — buried residue polarity change may destabilise core packing.")
    if chg_diff >= 1:
        implications.append(f"⚡ Charge reversal/loss — disrupted electrostatic interactions; may affect DNA/RNA binding or protein–protein contacts.")
    if orig == "C":
        implications.append("🔗 Loss of cysteine — potential disulfide bond disruption or metal-binding deficiency.")
    if alt == "P":
        implications.append("🔀 Proline introduction — rigid backbone; may disrupt helix/sheet secondary structure.")
    if orig == "G" or alt == "G":
        implications.append("🔄 Glycine involved — conformational flexibility altered; hinged regions may rigidify or gain flexibility.")
    if not implications:
        implications.append("🟡 Conservative substitution — physicochemical change minimal; functional impact likely low. Validate with structural modelling.")

    st.markdown("**Genomic & Structural Implications:**")
    for imp in implications:
        st.markdown(imp)


# ─── Disease–mutation–genomic map ─────────────────────────────────────────────
def _render_disease_mutation_map(pdata, clinvar_data, ml_scores, gene_name):
    st.markdown("#### 🗺️ Disease → Mutation → Genomic Implication")
    st.caption("Complete map of diseases caused by this protein, which mutations drive them, and the underlying genomic mechanism.")

    variants  = (clinvar_data or {}).get("variants", [])
    top_vars  = (ml_scores or {}).get("top_variants", variants[:30])
    diseases  = UniProtClient.extract_diseases(pdata)

    if not top_vars and not diseases:
        st.info("No variant or disease data to map.")
        return

    # Group by condition
    cond_map = {}
    for v in top_vars:
        cond = v.get("condition", "Not specified")
        if cond not in cond_map:
            cond_map[cond] = []
        cond_map[cond].append(v)

    for cond, vlist in list(cond_map.items())[:15]:
        vlist_sorted = sorted(vlist, key=lambda x: -x.get("ml_pathogenicity",0))
        rank    = vlist_sorted[0].get("ml_rank","NEUTRAL")
        rank_col = {"CRITICAL":"#ff2d55","HIGH":"#ff6b00","MEDIUM":"#ffd60a","NEUTRAL":"#636e72"}.get(rank,"#636e72")

        with st.expander(f"🔴 {cond[:80]}", expanded=(rank in ("CRITICAL","HIGH"))):
            col_v, col_mech = st.columns([2, 3])
            with col_v:
                st.markdown(f"**Top variants ({len(vlist_sorted)}):**")
                for v in vlist_sorted[:5]:
                    ml = v.get("ml_pathogenicity", 0)
                    sig = v.get("clinical_significance","—")
                    vname = v.get("variant_name") or v.get("title","—")
                    url  = v.get("clinvar_url","")
                    link = f"[↗]({url})" if url else ""
                    st.markdown(
                        f"- `{vname[:50]}` — **{sig}** · ML: {ml:.2f} {link}",
                    )
            with col_mech:
                st.markdown("**Genomic mechanism:**")
                _infer_disease_mechanism(cond, vlist_sorted)

            # Visual: variant position vs ML score
            if len(vlist_sorted) >= 3:
                pos_list  = []
                score_list = []
                for v in vlist_sorted[:20]:
                    pos = v.get("start") or v.get("position")
                    try:
                        pos_list.append(int(pos))
                        score_list.append(v.get("ml_pathogenicity",0))
                    except (TypeError, ValueError):
                        pass
                if pos_list:
                    fig = go.Figure(go.Scatter(
                        x=pos_list, y=score_list,
                        mode="markers",
                        marker=dict(
                            size=10,
                            color=score_list,
                            colorscale=[[0,"#636e72"],[0.5,"#ffd60a"],[1,"#ff2d55"]],
                            cmin=0, cmax=1,
                            showscale=True,
                            colorbar=dict(title="ML Score", thickness=10, len=0.6),
                        ),
                        text=[v.get("variant_name","")[:30] for v in vlist_sorted[:20]],
                        hovertemplate="%{text}<br>Pos: %{x}<br>Score: %{y:.2f}<extra></extra>",
                    ))
                    fig.update_layout(
                        paper_bgcolor="#060e18", plot_bgcolor="#060e18",
                        font_color="#8ab4d4",
                        xaxis=dict(title="Residue Position", gridcolor="#1e3a5f"),
                        yaxis=dict(title="ML Pathogenicity", range=[0,1], gridcolor="#1e3a5f"),
                        height=200, margin=dict(t=10,b=30,l=30,r=10),
                    )
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})


def _infer_disease_mechanism(condition: str, variants: list):
    """Rule-based mechanism inference from condition name + variant types."""
    cond_lower = condition.lower()
    v_names    = " ".join(v.get("variant_name","") for v in variants).lower()

    mechanisms = []
    if "cancer" in cond_lower or "carcinoma" in cond_lower or "tumor" in cond_lower:
        mechanisms.append("Oncogenic transformation via gain-of-function or dominant-negative mechanism.")
        mechanisms.append("Somatic acquisition leads to clonal expansion.")
    if "stop" in v_names or "nonsense" in v_names or "ter" in v_names:
        mechanisms.append("Premature stop codon → truncated protein → haploinsufficiency or NMD.")
    if "frameshift" in v_names or "del" in v_names:
        mechanisms.append("Reading frame disruption → nonfunctional protein isoform.")
    if "splice" in v_names:
        mechanisms.append("Splice-site mutation → exon skipping / intron retention → aberrant mRNA.")
    if "missense" in v_names:
        mechanisms.append("Missense substitution → altered protein conformation or binding affinity.")
    if "developmental" in cond_lower or "syndrome" in cond_lower:
        mechanisms.append("Germline variant disrupts developmental signalling pathway.")
    if not mechanisms:
        mechanisms.append("Mechanism not fully characterised — functional assays recommended.")

    for m in mechanisms:
        st.markdown(f"• {m}")
