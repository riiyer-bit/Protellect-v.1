"""
Tab 1 — Triage
• AlphaFold 3D structure (bright, coloured by pLDDT)
• Disease affiliation panel
• Residue triage list (ClinVar pathogenic variants → sphere positions)
• Supporting citations
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
import json
import math
from utils.alphafold import AlphaFoldClient
from utils.uniprot import UniProtClient
from utils.pubmed import render_citations


def render_triage_tab(
    protein_data:  dict,
    clinvar_data:  dict | None,
    alphafold_pdb: str | None,
    ml_scores:     dict | None,
    papers:        list | None,
    gene_name:     str,
):
    # ── Header metrics ────────────────────────────────────────────────────────
    diseases   = UniProtClient.extract_diseases(protein_data)
    variants   = (clinvar_data or {}).get("variants", [])
    summary    = (clinvar_data or {}).get("summary", {})
    path_count = summary.get("pathogenic_count", 0)
    total_cv   = summary.get("total", 0)
    top_vars   = (ml_scores or {}).get("top_variants", variants[:20])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"<div class='metric-box'><div class='val'>{len(diseases)}</div>"
            f"<div class='lbl'>Disease Associations</div></div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"<div class='metric-box'><div class='val'>{total_cv}</div>"
            f"<div class='lbl'>ClinVar Variants</div></div>",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"<div class='metric-box'>"
            f"<div class='val' style='color:#ff2d55;'>{path_count}</div>"
            f"<div class='lbl'>Pathogenic / Likely Path.</div></div>",
            unsafe_allow_html=True,
        )
    with col4:
        vus = summary.get("vus_count", 0)
        st.markdown(
            f"<div class='metric-box'>"
            f"<div class='val' style='color:#ffd60a;'>{vus}</div>"
            f"<div class='lbl'>Variants of Unc. Sig. (VUS)</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Two-column layout: Structure | Disease breakdown ──────────────────────
    col_struct, col_disease = st.columns([3, 2], gap="large")

    with col_struct:
        st.markdown("#### 🏗️ AlphaFold Structure")
        _render_structure(alphafold_pdb, protein_data, top_vars)

    with col_disease:
        st.markdown("#### 🔴 Disease & ClinVar Triage")
        _render_disease_panel(diseases, clinvar_data, ml_scores)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── Residue triage list ───────────────────────────────────────────────────
    st.markdown("#### 🔮 Residue Triage — Variant Hotspots")
    _render_residue_triage(top_vars, protein_data)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    render_citations(papers or [], max_show=4)


# ─── Structure viewer ─────────────────────────────────────────────────────────
def _render_structure(pdb_text: str | None, pdata: dict, top_vars: list):
    if not pdb_text:
        st.info("AlphaFold structure not available for this protein. "
                "Try searching by UniProt accession directly.")
        return

    # Parse pLDDT scores
    bfactors = AlphaFoldClient.parse_bfactors(pdb_text)
    avg_plddt = sum(bfactors.values()) / len(bfactors) if bfactors else 0

    # Collect pathogenic positions for highlighting
    path_positions = set()
    for v in top_vars[:30]:
        pos = v.get("start") or v.get("position")
        try:
            path_positions.add(int(pos))
        except (TypeError, ValueError):
            pass

    # Build py3Dmol viewer via HTML
    path_pos_js = json.dumps(list(path_positions))
    pdb_escaped  = pdb_text.replace("`", "\\`").replace("\\", "\\\\")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.1.0/3Dmol-min.js"></script>
      <style>
        body {{ margin:0; background:#060e18; }}
        #viewer {{ width:100%; height:520px; position:relative; }}
        #legend {{ position:absolute; bottom:10px; left:10px; background:rgba(0,0,0,0.7);
                   border-radius:8px; padding:8px 12px; font-family:Inter,sans-serif;
                   font-size:12px; color:#fff; }}
        .leg-item {{ display:flex; align-items:center; gap:6px; margin:3px 0; }}
        .leg-dot {{ width:12px; height:12px; border-radius:50%; }}
        #spinner {{ position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
                    color:#00d4ff; font-size:1rem; font-family:Inter,sans-serif; }}
      </style>
    </head>
    <body>
    <div id="viewer">
      <div id="spinner">Loading structure…</div>
      <div id="legend">
        <div class="leg-item"><div class="leg-dot" style="background:#0053D6;"></div> Very high (≥90)</div>
        <div class="leg-item"><div class="leg-dot" style="background:#65CBF3;"></div> Confident (70–90)</div>
        <div class="leg-item"><div class="leg-dot" style="background:#FFDB13;"></div> Low (50–70)</div>
        <div class="leg-item"><div class="leg-dot" style="background:#FF7D45;"></div> Very low (&lt;50)</div>
        <div class="leg-item"><div class="leg-dot" style="background:#ff2d55;border:2px solid white;"></div> Pathogenic variant site</div>
      </div>
    </div>
    <script>
    (function() {{
      const pdb = `{pdb_escaped}`;
      const pathPos = {path_pos_js};
      const spinner = document.getElementById('spinner');
      const viewer = $3Dmol.createViewer(document.getElementById('viewer'), {{
        backgroundColor: '0x060e18'
      }});
      viewer.addModel(pdb, 'pdb');
      // Colour by pLDDT (b-factor)
      viewer.setStyle({{}}, {{
        cartoon: {{
          colorfunc: function(atom) {{
            const b = atom.b;
            if (b >= 90) return '#0053D6';
            if (b >= 70) return '#65CBF3';
            if (b >= 50) return '#FFDB13';
            return '#FF7D45';
          }},
          thickness: 0.4,
        }}
      }});
      // Highlight pathogenic residues as bright red spheres
      pathPos.forEach(function(pos) {{
        viewer.addStyle(
          {{resi: pos, atom: 'CA'}},
          {{sphere: {{radius: 1.2, color: '#ff2d55', opacity: 0.95}}}}
        );
      }});
      viewer.zoomTo();
      viewer.spin('y', 0.5);
      viewer.render();
      spinner.style.display = 'none';
    }})();
    </script>
    </body>
    </html>
    """
    components.html(html, height=530, scrolling=False)

    # Confidence summary
    very_high = sum(1 for b in bfactors.values() if b >= 90)
    confident = sum(1 for b in bfactors.values() if 70 <= b < 90)
    pct_reliable = round((very_high + confident) / max(len(bfactors), 1) * 100, 1)
    st.caption(
        f"pLDDT avg: **{avg_plddt:.1f}** · "
        f"{pct_reliable}% of residues reliably modelled · "
        f"**{len(path_positions)}** pathogenic sites highlighted (red spheres)"
    )


# ─── Disease panel ─────────────────────────────────────────────────────────────
def _render_disease_panel(diseases: list, clinvar_data: dict | None, ml_scores: dict | None):
    if not diseases and not clinvar_data:
        st.info("No disease associations found in UniProt.")
        return

    summary     = (clinvar_data or {}).get("summary", {})
    ds_scores   = (ml_scores or {}).get("disease_scores", {})
    top_conds   = summary.get("top_conditions", {})

    all_diseases = []
    for d in diseases:
        name  = d["name"]
        score = ds_scores.get(name, 0.5)
        all_diseases.append({"name": name, "desc": d.get("desc", ""), "score": score, "source": "UniProt"})
    for cond, cnt in top_conds.items():
        if cond not in [x["name"] for x in all_diseases]:
            score = ds_scores.get(cond, 0.3)
            all_diseases.append({"name": cond, "desc": f"{cnt} ClinVar submissions", "score": score, "source": "ClinVar"})

    # Sort by score
    all_diseases.sort(key=lambda x: -x["score"])

    def rank_label(s):
        if s >= 0.85: return ("CRITICAL", "#ff2d55", "#fff")
        if s >= 0.65: return ("HIGH",     "#ff6b00", "#fff")
        if s >= 0.40: return ("MEDIUM",   "#ffd60a", "#111")
        return          ("NEUTRAL",   "#636e72", "#fff")

    for d in all_diseases[:12]:
        rl, bg, fg = rank_label(d["score"])
        st.markdown(
            f"<div style='background:#0a1929;border:1px solid #1e3a5f;border-radius:8px;"
            f"padding:10px 12px;margin:6px 0;'>"
            f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:4px;'>"
            f"<span style='background:{bg};color:{fg};padding:2px 10px;border-radius:12px;"
            f"font-size:0.72rem;font-weight:700;'>{rl}</span>"
            f"<span style='color:#e8f4fd;font-weight:600;font-size:0.88rem;'>{d['name']}</span>"
            f"</div>"
            f"<div style='color:#8ab4d4;font-size:0.78rem;'>{d.get('desc','')[:120]}</div>"
            f"<div style='margin-top:4px;'><progress value='{d['score']:.2f}' max='1' "
            f"style='width:100%;height:4px;accent-color:{bg};'></progress></div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Significance donut chart
    if summary.get("by_significance"):
        sig_data = summary["by_significance"]
        colours  = ["#ff2d55","#ff6b00","#ffd60a","#636e72","#00c896","#0090ff","#a855f7"]
        fig = go.Figure(go.Pie(
            labels=list(sig_data.keys()),
            values=list(sig_data.values()),
            hole=0.55,
            marker_colors=colours[:len(sig_data)],
            textfont_size=10,
        ))
        fig.update_layout(
            paper_bgcolor="#060e18", plot_bgcolor="#060e18",
            font_color="#8ab4d4", showlegend=True,
            legend=dict(font_size=10, bgcolor="#060e18"),
            margin=dict(t=0, b=0, l=0, r=0),
            height=220,
            annotations=[dict(text=f"<b>{summary['total']}</b><br>variants",
                              x=0.5, y=0.5, font_size=12, font_color="#00d4ff",
                              showarrow=False)]
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─── Residue triage list ───────────────────────────────────────────────────────
def _render_residue_triage(top_vars: list, pdata: dict):
    if not top_vars:
        st.info("No variant data to triage.")
        return

    # Table
    rows = []
    for v in top_vars[:50]:
        sig  = v.get("clinical_significance", "—")
        rank = v.get("ml_rank") or v.get("triage_rank", "—")
        rows.append({
            "Rank":       rank,
            "Variant":    v.get("variant_name") or v.get("title", "—"),
            "Position":   str(v.get("start", v.get("position", "—"))),
            "Significance": sig,
            "Condition":  v.get("condition", "—")[:60],
            "ML Path.":   f"{v.get('ml_pathogenicity', 0):.2f}" if "ml_pathogenicity" in v else "—",
            "ClinVar ↗":  v.get("clinvar_url", ""),
        })

    df = pd.DataFrame(rows)

    def colour_rank(val):
        colors = {
            "CRITICAL": "background-color:#3d0010; color:#ff2d55; font-weight:700;",
            "HIGH":     "background-color:#3d1a00; color:#ff6b00; font-weight:700;",
            "MEDIUM":   "background-color:#3d3000; color:#ffd60a; font-weight:700;",
            "NEUTRAL":  "background-color:#1a1a2e; color:#636e72;",
        }
        return colors.get(val, "")

    # Render as styled HTML table
    html_rows = ""
    for _, row in df.iterrows():
        rank  = row["Rank"]
        clr_map = {"CRITICAL":"#ff2d55","HIGH":"#ff6b00","MEDIUM":"#ffd60a","NEUTRAL":"#636e72"}
        bg_map  = {"CRITICAL":"#3d0010","HIGH":"#3d1a00","MEDIUM":"#3d3000","NEUTRAL":"#1a1a2e"}
        clr = clr_map.get(rank, "#636e72")
        bg  = bg_map.get(rank, "#0a1929")
        url = row["ClinVar ↗"]
        link = f"<a href='{url}' target='_blank' style='color:#00d4ff;font-size:0.75rem;'>↗ ClinVar</a>" if url else "—"
        html_rows += (
            f"<tr style='background:{bg};'>"
            f"<td><span style='background:{clr};color:{'#111' if rank=='MEDIUM' else '#fff'};"
            f"padding:2px 8px;border-radius:12px;font-size:0.72rem;font-weight:700;'>{rank}</span></td>"
            f"<td style='color:#e8f4fd;font-size:0.82rem;'>{row['Variant'][:60]}</td>"
            f"<td style='color:#8ab4d4;text-align:center;'>{row['Position']}</td>"
            f"<td style='color:#c9d8e8;font-size:0.8rem;'>{row['Significance']}</td>"
            f"<td style='color:#8ab4d4;font-size:0.78rem;'>{row['Condition']}</td>"
            f"<td style='color:#00d4ff;text-align:center;font-weight:600;'>{row['ML Path.']}</td>"
            f"<td>{link}</td>"
            f"</tr>"
        )

    table_html = f"""
    <div style='overflow-x:auto;'>
    <table style='width:100%;border-collapse:collapse;font-family:Inter,sans-serif;'>
      <thead>
        <tr style='background:#0d1b2a;'>
          <th style='color:#00d4ff;padding:8px 10px;text-align:left;font-size:0.8rem;'>Triage Rank</th>
          <th style='color:#00d4ff;padding:8px 10px;text-align:left;font-size:0.8rem;'>Variant</th>
          <th style='color:#00d4ff;padding:8px;text-align:center;font-size:0.8rem;'>Position</th>
          <th style='color:#00d4ff;padding:8px 10px;text-align:left;font-size:0.8rem;'>ClinVar Significance</th>
          <th style='color:#00d4ff;padding:8px 10px;text-align:left;font-size:0.8rem;'>Condition</th>
          <th style='color:#00d4ff;padding:8px;text-align:center;font-size:0.8rem;'>ML Score</th>
          <th style='color:#00d4ff;padding:8px;font-size:0.8rem;'>Link</th>
        </tr>
      </thead>
      <tbody>{html_rows}</tbody>
    </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)
    st.caption(f"Showing top {min(50, len(top_vars))} of {len(top_vars)} variants · Ranked by ML pathogenicity score · Source: ClinVar")
