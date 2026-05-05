from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import json
from api import get_diseases, parse_bfactors, plddt_colour
from styles import metric_card, badge, disease_row, cite_block, section_header


RANK_COLOURS = {"CRITICAL":"#ff2d55","HIGH":"#ff8c42","MEDIUM":"#ffd60a","NEUTRAL":"#3a5a7a"}
RANK_BG      = {"CRITICAL":"#1a0510","HIGH":"#1a0f00","MEDIUM":"#1a1400","NEUTRAL":"#080f18"}


def render(pdata, cv, scored_variants, papers):
    diseases = get_diseases(pdata)
    summary  = cv.get("summary", {})
    top      = scored_variants[:50]

    # ── Metrics row ──────────────────────────────────────────────────────────
    c1,c2,c3,c4 = st.columns(4)
    total = summary.get("total", 0)
    path  = summary.get("pathogenic", 0)
    vus   = summary.get("vus", 0)
    crit  = sum(1 for v in scored_variants if v.get("ml_rank")=="CRITICAL")

    with c1: st.markdown(metric_card(len(diseases), "Disease Links", "#00e5ff"), unsafe_allow_html=True)
    with c2: st.markdown(metric_card(total, "ClinVar Variants", "#4a90d9"), unsafe_allow_html=True)
    with c3: st.markdown(metric_card(path, "Pathogenic", "#ff2d55", "linear-gradient(90deg,#ff2d55,#ff6b8a)"), unsafe_allow_html=True)
    with c4: st.markdown(metric_card(crit, "CRITICAL (ML)", "#ff8c42", "linear-gradient(90deg,#ff8c42,#ffb380)"), unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ── Structure + Disease ──────────────────────────────────────────────────
    col_s, col_d = st.columns([3, 2], gap="large")

    with col_s:
        section_header("🏗️", "AlphaFold Structure")
        _render_viewer(
            pdb_text      = st.session_state.get("pdb",""),
            scored_variants = top,
        )

    with col_d:
        section_header("🔴", "Disease Triage")
        _render_disease_panel(diseases, summary, scored_variants)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ── Residue triage table ─────────────────────────────────────────────────
    section_header("🔮", "Residue Hotspot Triage")
    _render_triage_table(top)

    if papers:
        st.markdown(cite_block(papers, 4), unsafe_allow_html=True)


def _render_viewer(pdb_text, scored_variants):
    if not pdb_text:
        st.markdown(
            "<div style='background:#060e1c;border:1px dashed #0d2545;border-radius:12px;"
            "height:420px;display:flex;align-items:center;justify-content:center;'>"
            "<div style='text-align:center;color:#1a3a5a;'>"
            "<div style='font-size:2rem;'>🧬</div>"
            "<div style='font-size:0.88rem;margin-top:6px;'>AlphaFold structure not available<br>Try a direct UniProt accession</div>"
            "</div></div>",
            unsafe_allow_html=True,
        )
        return

    path_pos = {}
    for v in scored_variants[:40]:
        pos = v.get("start") or v.get("position")
        try:
            p = int(pos)
            path_pos[p] = {"rank": v.get("ml_rank","NEUTRAL"), "ml": v.get("ml",0)}
        except: pass

    bfactors = parse_bfactors(pdb_text)
    avg_pl   = round(sum(bfactors.values())/max(len(bfactors),1), 1)
    high_conf = sum(1 for b in bfactors.values() if b >= 70)
    pct_conf  = round(high_conf / max(len(bfactors),1) * 100, 0)

    pp_js  = json.dumps({str(k): v for k,v in path_pos.items()})
    pdb_esc = pdb_text.replace("`","\\`").replace("\\","\\\\")

    html = f"""<!DOCTYPE html><html><head>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.1.0/3Dmol-min.js"></script>
    <style>
    *{{margin:0;padding:0;box-sizing:border-box;}}
    body{{background:#04080f;font-family:Inter,sans-serif;}}
    #wrap{{position:relative;}}
    #v{{width:100%;height:430px;}}
    #ctrl{{display:flex;gap:6px;padding:8px;background:#060e1c;border-bottom:1px solid #0d2545;flex-wrap:wrap;}}
    .btn{{background:#07111f;color:#4a7fa5;border:1px solid #0d2545;padding:4px 12px;
          border-radius:16px;cursor:pointer;font-size:11px;font-family:Inter,sans-serif;transition:all 0.2s;}}
    .btn:hover,.btn.on{{background:#00e5ff;color:#000;font-weight:700;border-color:#00e5ff;}}
    #leg{{position:absolute;bottom:8px;left:8px;background:rgba(4,8,15,0.88);border:1px solid #0d2545;
           border-radius:8px;padding:10px 12px;font-size:11px;color:#7aa0c0;backdrop-filter:blur(4px);}}
    .li{{display:flex;align-items:center;gap:6px;margin:3px 0;}}
    .ld{{width:10px;height:10px;border-radius:50%;flex-shrink:0;}}
    #spin{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);color:#1a4a6a;font-size:13px;}}
    </style></head><body>
    <div id="ctrl">
      <button class="btn on" onclick="ss('cartoon',this)">🎀 Ribbon</button>
      <button class="btn" onclick="ss('stick',this)">🦴 Stick</button>
      <button class="btn" onclick="ss('sphere',this)">⬤ Sphere</button>
      <button class="btn" onclick="ss('surface',this)">🌊 Surface</button>
      <button class="btn" id="spbtn" onclick="toggleSpin()">▶ Spin</button>
      <button class="btn" onclick="v.zoomTo();v.render()">🎯 Reset</button>
      <button class="btn" onclick="togglePth()">🔴 Variants</button>
    </div>
    <div id="wrap">
      <div id="v"></div>
      <div id="spin">Loading structure…</div>
      <div id="leg">
        <div class="li"><div class="ld" style="background:#1565C0"></div>pLDDT ≥90 Very High</div>
        <div class="li"><div class="ld" style="background:#29B6F6"></div>pLDDT 70–90 Confident</div>
        <div class="li"><div class="ld" style="background:#FDD835"></div>pLDDT 50–70 Low</div>
        <div class="li"><div class="ld" style="background:#FF7043"></div>pLDDT &lt;50 Very Low</div>
        <div class="li"><div class="ld" style="background:#ff2d55;border:1px solid white;"></div>Pathogenic site</div>
      </div>
    </div>
    <script>
    const pp={path_pos_js};const pdb=`{pdb_esc}`;
    let spinning=false,showPth=true,curStyle='cartoon';
    const v=$3Dmol.createViewer(document.getElementById('v'),{{backgroundColor:'0x04080f'}});
    v.addModel(pdb,'pdb');
    function colFn(atom){{const b=atom.b;if(b>=90)return'#1565C0';if(b>=70)return'#29B6F6';if(b>=50)return'#FDD835';return'#FF7043';}}
    function applyStyle(){{
      v.removeAllSurfaces();
      if(curStyle==='surface'){{v.addSurface($3Dmol.SurfaceType.VDW,{{colorfunc:colFn,opacity:0.78}});}}
      else if(curStyle==='sphere'){{v.setStyle({{}},{{sphere:{{colorfunc:colFn,radius:0.7}}}});}}
      else if(curStyle==='stick'){{v.setStyle({{}},{{cartoon:{{colorfunc:colFn,thickness:0.2}},stick:{{colorscheme:'chainHetatm',radius:0.1}}}});}}
      else{{v.setStyle({{}},{{cartoon:{{colorfunc:colFn,thickness:0.4}}}});}}
      if(showPth)addPth();
      v.render();
    }}
    function addPth(){{
      Object.entries(pp).forEach(([pos,info])=>{{
        const rk=info.rank;
        const c=rk==='CRITICAL'?'#ff2d55':rk==='HIGH'?'#ff8c42':rk==='MEDIUM'?'#ffd60a':'#3a5a7a';
        v.addStyle({{resi:parseInt(pos),atom:'CA'}},{{sphere:{{radius:1.3,color:c,opacity:0.95}}}});
      }});
    }}
    applyStyle();
    v.zoomTo();v.render();
    document.getElementById('spin').style.display='none';
    function ss(style,btn){{curStyle=style;document.querySelectorAll('.btn').forEach(b=>b.classList.remove('on'));btn.classList.add('on');applyStyle();}}
    function toggleSpin(){{spinning=!spinning;v.spin(spinning?'y':false,0.6);const b=document.getElementById('spbtn');b.textContent=spinning?'⏸ Stop':'▶ Spin';b.classList.toggle('on',spinning);}}
    function togglePth(){{showPth=!showPth;applyStyle();}}
    </script></body></html>
    """.replace("{path_pos_js}", pp_js)

    components.html(html, height=500, scrolling=False)
    st.markdown(
        f"<div style='display:flex;gap:16px;margin-top:6px;'>"
        f"<span style='color:#2a5070;font-size:0.76rem;'>pLDDT avg: <b style='color:#4a90d9;'>{avg_pl}</b></span>"
        f"<span style='color:#2a5070;font-size:0.76rem;'>{pct_conf:.0f}% reliably modelled</span>"
        f"<span style='color:#2a5070;font-size:0.76rem;'><b style='color:#ff2d55;'>{len(path_pos)}</b> variant sites shown</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_disease_panel(diseases, summary, scored):
    ds_scores = {}
    for v in scored:
        for c in v.get("condition","").split(";"):
            c = c.strip()
            if c and c != "Not specified":
                ds_scores[c] = max(ds_scores.get(c,0), v.get("ml",0))

    all_d = []
    for d in diseases:
        score = ds_scores.get(d["name"], 0.5)
        rank  = "CRITICAL" if score>=0.85 else "HIGH" if score>=0.65 else "MEDIUM" if score>=0.40 else "NEUTRAL"
        kw = (d["name"]+d.get("desc","")).lower()
        if any(k in kw for k in ["cancer","carcinoma","leukemia","glioma","sarcoma"]) and rank=="MEDIUM":
            rank = "HIGH"
        all_d.append({"name":d["name"],"desc":d.get("desc",""),"rank":rank,"score":score})

    for cond, cnt in summary.get("top_conds",{}).items():
        if cond not in [x["name"] for x in all_d]:
            score = ds_scores.get(cond, 0.3)
            rank  = "CRITICAL" if score>=0.85 else "HIGH" if score>=0.65 else "MEDIUM" if score>=0.40 else "NEUTRAL"
            all_d.append({"name":cond,"desc":f"{cnt} ClinVar submissions","rank":rank,"score":score})

    all_d.sort(key=lambda x:(["CRITICAL","HIGH","MEDIUM","NEUTRAL"].index(x["rank"]),-x["score"]))

    for d in all_d[:10]:
        st.markdown(disease_row(d["name"],d["desc"],d["rank"],d["score"]), unsafe_allow_html=True)

    if summary.get("by_sig"):
        sig_d = summary["by_sig"]
        clrs  = ["#ff2d55","#ff8c42","#ffd60a","#4a90d9","#00c896","#6478ff","#a855f7","#2a5070"]
        fig   = go.Figure(go.Pie(
            labels=list(sig_d.keys()), values=list(sig_d.values()),
            hole=0.6, marker_colors=clrs[:len(sig_d)], textfont_size=10,
        ))
        total = summary.get("total",0)
        fig.update_layout(
            paper_bgcolor="#04080f", plot_bgcolor="#04080f", font_color="#4a7fa5",
            showlegend=True, legend=dict(font_size=10, bgcolor="#04080f"),
            margin=dict(t=0,b=0,l=0,r=0), height=200,
            annotations=[dict(text=f"<b style='color:#00e5ff'>{total}</b><br><span style='font-size:10px;'>variants</span>",
                              x=0.5,y=0.5,font_size=13,font_color="#00e5ff",showarrow=False)]
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})


def _render_triage_table(top):
    if not top:
        st.info("No variant data available.")
        return

    rc  = {"CRITICAL":"#ff2d55","HIGH":"#ff8c42","MEDIUM":"#ffd60a","NEUTRAL":"#3a5a7a"}
    rbg = {"CRITICAL":"#1a0510","HIGH":"#1a0f00","MEDIUM":"#1a1400","NEUTRAL":"#060e18"}

    rows = ""
    for v in top[:50]:
        rank  = v.get("ml_rank","NEUTRAL")
        ml    = v.get("ml",0)
        clr   = rc.get(rank,"#3a5a7a")
        bg    = rbg.get(rank,"#060e18")
        url   = v.get("url","")
        name  = (v.get("variant_name") or v.get("title","—"))[:55]
        sig   = v.get("sig","—")[:35]
        cond  = v.get("condition","—")[:50]
        pos   = str(v.get("start","—"))
        link  = f"<a href='{url}' target='_blank' style='color:#2a7aaa;font-size:0.75rem;'>↗</a>" if url else "—"
        bar_w = int(ml*100)
        rows += (
            f"<tr style='background:{bg};'>"
            f"<td><span class='badge badge-{rank}'>{rank}</span></td>"
            f"<td style='color:#c0d8f0;font-size:0.82rem;'>{name}</td>"
            f"<td style='color:#4a7fa5;text-align:center;'>{pos}</td>"
            f"<td style='color:#7aa0c0;font-size:0.8rem;'>{sig}</td>"
            f"<td style='color:#5a8090;font-size:0.78rem;'>{cond}</td>"
            f"<td><div style='display:flex;align-items:center;gap:6px;'>"
            f"<div style='width:40px;height:4px;background:#0a1e32;border-radius:4px;overflow:hidden;'>"
            f"<div style='width:{bar_w}%;height:100%;background:{clr};'></div></div>"
            f"<span style='color:{clr};font-size:0.8rem;font-weight:700;'>{ml:.2f}</span></div></td>"
            f"<td style='text-align:center;'>{link}</td>"
            f"</tr>"
        )

    st.markdown(
        f"<div style='overflow-x:auto;border-radius:12px;border:1px solid #0d2545;'>"
        f"<table class='proto-table'><thead><tr>"
        f"<th>Rank</th><th>Variant</th><th>Position</th>"
        f"<th>ClinVar Sig.</th><th>Condition</th><th>ML Score</th><th>Link</th>"
        f"</tr></thead><tbody>{rows}</tbody></table></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='color:#1a3a5a;font-size:0.74rem;margin-top:6px;'>"
        f"Showing {min(50,len(top))} of {len(top)} variants · Ranked by ML pathogenicity · Source: ClinVar</div>",
        unsafe_allow_html=True,
    )
