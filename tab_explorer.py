from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import json, math
from api import get_sequence, parse_bfactors, AA_HYDRO, AA_CHG
from styles import section_header, cite_block

AA_NAMES = {"A":"Alanine","R":"Arginine","N":"Asparagine","D":"Aspartate","C":"Cysteine",
            "Q":"Glutamine","E":"Glutamate","G":"Glycine","H":"Histidine","I":"Isoleucine",
            "L":"Leucine","K":"Lysine","M":"Methionine","F":"Phenylalanine","P":"Proline",
            "S":"Serine","T":"Threonine","W":"Tryptophan","Y":"Tyrosine","V":"Valine"}

def render(pdata, pdb_text, cv, scored, papers, gene_name):
    section_header("🔬","Protein Explorer")
    st.caption("Click any residue to inspect it. Use the mutation panel below to simulate substitutions.")

    _render_large_viewer(pdb_text, scored)
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    _render_mutation_panel(pdata, pdb_text, scored)
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    _render_disease_map(cv, scored, gene_name)
    if papers:
        st.markdown(cite_block(papers,4), unsafe_allow_html=True)


def _render_large_viewer(pdb_text, scored):
    if not pdb_text:
        st.info("No AlphaFold structure — search by UniProt accession for 3D view.")
        return

    path_pos = {}
    for v in scored[:50]:
        pos = v.get("start") or v.get("position")
        try:
            p = int(pos)
            path_pos[p] = {"rank":v.get("ml_rank","NEUTRAL"),"ml":v.get("ml",0),
                           "cond":v.get("condition","")[:60],"sig":v.get("sig",""),
                           "var":v.get("variant_name","")[:40]}
        except: pass

    pp_js  = json.dumps({str(k):v for k,v in path_pos.items()})
    pdb_esc = pdb_text.replace("`","\\`").replace("\\","\\\\")

    html = f"""<!DOCTYPE html><html><head>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.1.0/3Dmol-min.js"></script>
    <style>
    *{{margin:0;padding:0;box-sizing:border-box;}}
    body{{background:#04080f;font-family:'Inter',sans-serif;display:flex;flex-direction:column;height:680px;}}
    #ctrl{{display:flex;gap:5px;padding:8px 10px;background:#060e1c;border-bottom:1px solid #0d2545;flex-wrap:wrap;flex-shrink:0;}}
    .btn{{background:#07111f;color:#3a6080;border:1px solid #0d2545;padding:4px 12px;
          border-radius:16px;cursor:pointer;font-size:11px;transition:all 0.2s;white-space:nowrap;}}
    .btn:hover,.btn.on{{background:#00e5ff;color:#000;font-weight:700;border-color:#00e5ff;box-shadow:0 0 12px rgba(0,229,255,0.3);}}
    #main{{position:relative;flex:1;}}
    #v{{width:100%;height:100%;}}
    #panel{{position:absolute;top:10px;right:10px;width:240px;background:rgba(4,8,15,0.93);
             border:1px solid #0d2545;border-radius:10px;padding:14px;display:none;
             backdrop-filter:blur(8px);max-height:90%;overflow-y:auto;}}
    #panel h3{{color:#00e5ff;font-size:13px;margin:0 0 10px;border-bottom:1px solid #0d2545;padding-bottom:6px;}}
    .pr{{display:flex;justify-content:space-between;margin:5px 0;font-size:12px;}}
    .pk{{color:#2a5070;}} .pv{{color:#8ab0d0;font-weight:600;}}
    .rank-tag{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:10px;font-weight:800;margin-bottom:8px;}}
    #close{{position:absolute;top:8px;right:10px;color:#2a5070;cursor:pointer;font-size:16px;}}
    #leg{{position:absolute;bottom:8px;left:8px;background:rgba(4,8,15,0.88);border:1px solid #0d2545;
          border-radius:8px;padding:9px 12px;font-size:11px;color:#3a6080;backdrop-filter:blur(4px);}}
    .li{{display:flex;align-items:center;gap:6px;margin:3px 0;}}
    .ld{{width:10px;height:10px;border-radius:50%;flex-shrink:0;}}
    </style></head><body>
    <div id="ctrl">
      <button class="btn on" onclick="ss('cartoon',this)">🎀 Ribbon</button>
      <button class="btn" onclick="ss('stick',this)">🦴 Stick</button>
      <button class="btn" onclick="ss('sphere',this)">⬤ Sphere</button>
      <button class="btn" onclick="ss('surface',this)">🌊 Surface</button>
      <button class="btn" id="spbtn" onclick="toggleSpin()">▶ Spin</button>
      <button class="btn" onclick="v.zoomTo();v.render()">🎯 Reset</button>
      <button class="btn" onclick="toggleVars()">🔴 Variants</button>
      <button class="btn" onclick="toggleLabels()">🏷 Labels</button>
    </div>
    <div id="main">
      <div id="v"></div>
      <div id="panel">
        <span id="close" onclick="document.getElementById('panel').style.display='none'">✕</span>
        <h3 id="pt">Residue Info</h3>
        <div id="pc"></div>
      </div>
      <div id="leg">
        <div class="li"><div class="ld" style="background:#1565C0"></div>pLDDT ≥90</div>
        <div class="li"><div class="ld" style="background:#29B6F6"></div>pLDDT 70–90</div>
        <div class="li"><div class="ld" style="background:#FDD835"></div>pLDDT 50–70</div>
        <div class="li"><div class="ld" style="background:#FF7043"></div>pLDDT &lt;50</div>
        <div class="li"><div class="ld" style="background:#ff2d55;border:1px solid #fff8;"></div>Pathogenic</div>
      </div>
    </div>
    <script>
    const pp={pp_js};const pdb=`{pdb_esc}`;
    const an={{"ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C","GLN":"Q","GLU":"E","GLY":"G","HIS":"H","ILE":"I","LEU":"L","LYS":"K","MET":"M","PHE":"F","PRO":"P","SER":"S","THR":"T","TRP":"W","TYR":"Y","VAL":"V"}};
    const fn={{"A":"Alanine","R":"Arginine","N":"Asparagine","D":"Aspartate","C":"Cysteine","Q":"Glutamine","E":"Glutamate","G":"Glycine","H":"Histidine","I":"Isoleucine","L":"Leucine","K":"Lysine","M":"Methionine","F":"Phenylalanine","P":"Proline","S":"Serine","T":"Threonine","W":"Tryptophan","Y":"Tyrosine","V":"Valine"}};
    const hy={{"A":1.8,"R":-4.5,"N":-3.5,"D":-3.5,"C":2.5,"Q":-3.5,"E":-3.5,"G":-0.4,"H":-3.2,"I":4.5,"L":3.8,"K":-3.9,"M":1.9,"F":2.8,"P":-1.6,"S":-0.8,"T":-0.7,"W":-0.9,"Y":-1.3,"V":4.2}};
    let spinning=false,showVars=true,showLbls=false,curStyle='cartoon';
    const v=$3Dmol.createViewer(document.getElementById('v'),{{backgroundColor:'0x04080f'}});
    v.addModel(pdb,'pdb');
    function cf(a){{const b=a.b;if(b>=90)return'#1565C0';if(b>=70)return'#29B6F6';if(b>=50)return'#FDD835';return'#FF7043';}}
    function ap(){{
      v.removeAllSurfaces();
      if(curStyle==='surface'){{v.addSurface($3Dmol.SurfaceType.VDW,{{colorfunc:cf,opacity:0.78}});}}
      else if(curStyle==='sphere'){{v.setStyle({{}},{{sphere:{{colorfunc:cf,radius:0.7}}}});}}
      else if(curStyle==='stick'){{v.setStyle({{}},{{cartoon:{{colorfunc:cf,thickness:0.2}},stick:{{colorscheme:'chainHetatm',radius:0.12}}}});}}
      else{{v.setStyle({{}},{{cartoon:{{colorfunc:cf,thickness:0.45}}}});}}
      if(showVars)addV();
      v.render();
    }}
    function addV(){{
      Object.entries(pp).forEach(([pos,info])=>{{
        const rk=info.rank;
        const c=rk==='CRITICAL'?'#ff2d55':rk==='HIGH'?'#ff8c42':rk==='MEDIUM'?'#ffd60a':'#3a5a7a';
        v.addStyle({{resi:parseInt(pos),atom:'CA'}},{{sphere:{{radius:1.4,color:c,opacity:0.95}}}});
      }});
    }}
    ap();v.zoomTo();v.render();
    v.setClickable({{}},true,function(atom){{
      const pos=atom.resi,r3=(atom.resn||'').toUpperCase(),r1=an[r3]||'?';
      const full=fn[r1]||r3,pl=atom.b||0;
      const cl=pl>=90?'Very High':pl>=70?'Confident':pl>=50?'Low':'Very Low';
      const hv=hy[r1]!==undefined?hy[r1].toFixed(1):'?';
      const inf=pp[String(pos)];
      let html='';
      if(inf){{
        const rc={{CRITICAL:'#ff2d55',HIGH:'#ff8c42',MEDIUM:'#ffd60a',NEUTRAL:'#3a5a7a'}};
        const rb={{CRITICAL:'rgba(255,45,85,0.15)',HIGH:'rgba(255,140,66,0.15)',MEDIUM:'rgba(255,214,10,0.1)',NEUTRAL:'rgba(58,90,122,0.2)'}};
        html+=`<span class="rank-tag" style="background:${{rb[inf.rank]}};color:${{rc[inf.rank]}};border:1px solid ${{rc[inf.rank]}}44;">${{inf.rank}}</span><br>`;
      }}
      html+=`<div class="pr"><span class="pk">Residue</span><span class="pv">${{r1}} (${{full}})</span></div>`;
      html+=`<div class="pr"><span class="pk">Position</span><span class="pv">${{pos}}</span></div>`;
      html+=`<div class="pr"><span class="pk">pLDDT</span><span class="pv">${{pl.toFixed(1)}} (${{cl}})</span></div>`;
      html+=`<div class="pr"><span class="pk">Hydropathy</span><span class="pv">${{hv}}</span></div>`;
      if(inf){{
        html+=`<hr style="border-color:#0d2545;margin:8px 0;">`;
        html+=`<div class="pr"><span class="pk">Variant</span><span class="pv" style="font-size:11px;">${{inf.var||'—'}}</span></div>`;
        html+=`<div class="pr"><span class="pk">Significance</span><span class="pv" style="font-size:11px;">${{inf.sig||'—'}}</span></div>`;
        html+=`<div class="pr"><span class="pk">ML score</span><span class="pv" style="color:#00e5ff;">${{(inf.ml*100).toFixed(0)}}%</span></div>`;
        if(inf.cond)html+=`<div style="margin-top:6px;color:#2a5070;font-size:11px;line-height:1.4;">${{inf.cond}}</div>`;
      }}
      document.getElementById('pt').textContent=r3+pos;
      document.getElementById('pc').innerHTML=html;
      document.getElementById('panel').style.display='block';
    }});
    function ss(style,btn){{curStyle=style;document.querySelectorAll('.btn').forEach(b=>b.classList.remove('on'));btn.classList.add('on');ap();}}
    function toggleSpin(){{spinning=!spinning;v.spin(spinning?'y':false,0.6);const b=document.getElementById('spbtn');b.textContent=spinning?'⏸ Stop':'▶ Spin';b.classList.toggle('on',spinning);}}
    function toggleVars(){{showVars=!showVars;ap();}}
    function toggleLabels(){{showLbls=!showLbls;v.removeAllLabels();if(showLbls){{Object.entries(pp).forEach(([pos,info])=>{{if(info.rank==='CRITICAL'||info.rank==='HIGH'){{v.addLabel('P'+pos,{{position:{{resi:parseInt(pos),atom:'CA'}},backgroundColor:'#ff2d55',backgroundOpacity:0.8,fontSize:10,fontColor:'white',borderRadius:4}});}}}});}};v.render();}}
    </script></body></html>
    """.replace("{pp_js}", pp_js)

    components.html(html, height=690, scrolling=False)


def _render_mutation_panel(pdata, pdb_text, scored):
    section_header("🧫","Residue Mutation Analysis")

    seq = get_sequence(pdata)
    if not seq:
        st.info("No sequence available."); return

    bfactors = parse_bfactors(pdb_text) if pdb_text else {}
    pos_to_v  = {}
    for v in scored:
        pos = v.get("start") or v.get("position")
        try: pos_to_v[int(pos)] = v
        except: pass

    col_sel, col_mut = st.columns([1,2], gap="large")
    with col_sel:
        position = st.number_input("Residue position", 1, max(len(seq),1), 1, 1, key="res_pos")
        position = int(position)
        aa = seq[position-1] if position <= len(seq) else "?"
        pl = bfactors.get(position)
        vd = pos_to_v.get(position)
        conf = ("Very High" if pl and pl>=90 else "Confident" if pl and pl>=70 else "Low" if pl and pl>=50 else "Very Low") if pl else "—"
        st.markdown(
            f"<div class='card'>"
            f"<h4>Residue {position} — {aa}</h4>"
            f"<p>{AA_NAMES.get(aa,'Unknown')}<br>"
            f"pLDDT: <b style='color:#00e5ff;'>{f'{pl:.1f}' if pl else '—'}</b><br>"
            f"Confidence: <b>{conf}</b><br>"
            f"Hydropathy: <b>{AA_HYDRO.get(aa,0):+.1f}</b></p>"
            f"</div>", unsafe_allow_html=True)

        if vd:
            rk = vd.get('ml_rank','NEUTRAL')
            rk_clr = {'CRITICAL':'#ff2d55','HIGH':'#ff8c42','MEDIUM':'#ffd60a','NEUTRAL':'#3a5a7a'}.get(rk,'#0d2545')
            st.markdown(
                "<div class='card' style='border-color:"+rk_clr+";'>"
                "<h4 style='color:"+rk_clr+";'>\u26a0\ufe0f ClinVar Variant</h4>"
                f"<p>{vd.get('sig','\u2014')}<br><small style='color:#2a5070;'>{vd.get('condition','')[:80]}</small></p>"
                "</div>", unsafe_allow_html=True)
        else:
            st.success("No ClinVar variant at this position", icon="✅")

    with col_mut:
        t1, t2 = st.tabs(["Properties","If Mutated →"])
        with t1:
            _show_aa_props(aa)
        with t2:
            alts = [a for a in AA_NAMES.keys() if a != aa]
            alt  = st.selectbox("Substitute with:", alts, key="alt_aa")
            sev  = st.slider("Perturbation magnitude", 0.0, 1.0, 0.5, 0.05, key="sev_slider")
            if bfactors:
                _mutation_chart(position, aa, alt, sev, bfactors)
            _mutation_implications(position, aa, alt)


def _show_aa_props(aa):
    props = {
        "A":{"polar":False,"charged":False,"aromatic":False,"special":"Smallest AA, helix-forming"},
        "G":{"polar":False,"charged":False,"aromatic":False,"special":"Most flexible, helix-breaker"},
        "P":{"polar":False,"charged":False,"aromatic":False,"special":"Rigid ring, helix-breaker"},
        "C":{"polar":True,"charged":False,"aromatic":False,"special":"Disulfide bonds, metal-binding"},
        "H":{"polar":True,"charged":True,"aromatic":True,"special":"pH-sensitive charge (pKa≈6)"},
        "W":{"polar":True,"charged":False,"aromatic":True,"special":"Largest AA, UV-absorbing"},
        "Y":{"polar":True,"charged":False,"aromatic":True,"special":"Phosphorylation target"},
        "F":{"polar":False,"charged":False,"aromatic":True,"special":"Stacking interactions"},
        "R":{"polar":True,"charged":True,"aromatic":False,"special":"DNA/RNA binding, +1 charge"},
        "K":{"polar":True,"charged":True,"aromatic":False,"special":"Ubiquitination, acetylation target"},
        "D":{"polar":True,"charged":True,"aromatic":False,"special":"Catalytic acid, −1 charge"},
        "E":{"polar":True,"charged":True,"aromatic":False,"special":"Catalytic acid, −1 charge"},
    }
    p = props.get(aa,{})
    items = [
        ("Amino Acid", f"{aa} — {AA_NAMES.get(aa,'?')}"),
        ("Hydropathy", f"{AA_HYDRO.get(aa,0):+.1f}"),
        ("Charge",     f"{AA_CHG.get(aa,0):+.1f}"),
        ("Polar",      "Yes" if p.get("polar") else "No"),
        ("Aromatic",   "Yes" if p.get("aromatic") else "No"),
        ("Note",       p.get("special","—")),
    ]
    for k,val in items:
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;padding:5px 0;"
            f"border-bottom:1px solid #070f1e;'>"
            f"<span style='color:#2a5070;font-size:0.82rem;'>{k}</span>"
            f"<span style='color:#8ab0d0;font-size:0.82rem;font-weight:600;'>{val}</span>"
            f"</div>", unsafe_allow_html=True)


def _mutation_chart(pos, orig, alt, severity, bfactors):
    positions = sorted(bfactors.keys())
    window    = 35
    center    = min(max(pos, window+1), max(positions)-window)
    dp = [p for p in positions if abs(p-center) <= window]
    wt = [bfactors.get(p,70) for p in dp]
    mt = [max(0, wt[i] - severity*28*math.exp(-0.5*((p-pos)/6)**2)) for i,p in enumerate(dp)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dp,y=wt,mode="lines",name="Wild-type",
                             line=dict(color="#00e5ff",width=2),fill=None))
    fig.add_trace(go.Scatter(x=dp,y=mt,mode="lines",name=f"{orig}{pos}{alt}",
                             line=dict(color="#ff2d55",width=2,dash="dash"),fill=None))
    fig.add_trace(go.Scatter(x=dp+dp[::-1],y=mt+wt[::-1],fill="toself",
                             fillcolor="rgba(255,45,85,0.08)",line=dict(color="rgba(0,0,0,0)"),showlegend=False))
    fig.add_vline(x=pos,line_color="#ffd60a",line_dash="dot",
                  annotation_text=f"p.{orig}{pos}{alt}",annotation_font_color="#ffd60a",annotation_font_size=11)
    fig.update_layout(
        paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#4a7fa5",
        xaxis=dict(title="Position",gridcolor="#070f1e",color="#2a5070"),
        yaxis=dict(title="pLDDT",range=[0,100],gridcolor="#070f1e",color="#2a5070"),
        legend=dict(bgcolor="#04080f",font_size=11),
        margin=dict(t=10,b=30,l=30,r=10),height=240,
    )
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
    st.caption(f"Simulated structural perturbation · severity {severity:.0%}")


def _mutation_implications(pos, orig, alt):
    hdiff = abs(AA_HYDRO.get(orig,0) - AA_HYDRO.get(alt,0))
    cdiff = abs(AA_CHG.get(orig,0)   - AA_CHG.get(alt,0))
    imps  = []
    if alt == "*":
        imps.append(("🔴","Nonsense / stop-gain","Premature termination → likely NMD → loss-of-function"))
    if hdiff > 3:
        imps.append(("🟠","Large hydropathy shift",f"Δ{hdiff:.1f} — buried-residue polarity change may destabilise core"))
    if cdiff >= 1:
        imps.append(("⚡","Charge change",f"Δ{cdiff:+.0f} — disrupted electrostatic interactions; may affect binding"))
    if orig == "C":
        imps.append(("🔗","Cysteine lost","Potential disulfide bond or metal-chelation disruption"))
    if alt == "P":
        imps.append(("🔀","Proline introduced","Rigid backbone; helix/sheet secondary structure may break"))
    if orig == "G" or alt == "G":
        imps.append(("🔄","Glycine involved","Conformational flexibility altered at this hinge region"))
    if not imps:
        imps.append(("🟡","Conservative","Physicochemical change minimal; likely low functional impact"))

    for icon, title, body in imps:
        st.markdown(
            f"<div style='display:flex;gap:10px;background:#060e1c;border:1px solid #0d2545;"
            f"border-radius:8px;padding:10px 12px;margin:5px 0;'>"
            f"<span style='font-size:1.1rem;flex-shrink:0;'>{icon}</span>"
            f"<div><div style='color:#8ab0d0;font-size:0.82rem;font-weight:700;'>{title}</div>"
            f"<div style='color:#3a6080;font-size:0.78rem;margin-top:2px;'>{body}</div></div></div>",
            unsafe_allow_html=True)


def _render_disease_map(cv, scored, gene_name):
    section_header("🗺️","Disease → Mutation → Genomic Implication")
    top = scored[:30]
    if not top:
        st.info("No variant data."); return

    from collections import defaultdict
    cond_map = defaultdict(list)
    for v in top:
        for c in v.get("condition","Not specified").split(";"):
            cond_map[c.strip()].append(v)

    for cond, vlist in list(cond_map.items())[:12]:
        if cond == "Not specified": continue
        vlist_s = sorted(vlist, key=lambda x:-x.get("ml",0))
        best_rank = vlist_s[0].get("ml_rank","NEUTRAL")
        rc = {"CRITICAL":"#ff2d55","HIGH":"#ff8c42","MEDIUM":"#ffd60a","NEUTRAL":"#3a5a7a"}

        with st.expander(f"{cond[:80]}  ({len(vlist_s)} variants)", expanded=(best_rank in ("CRITICAL","HIGH"))):
            cv_col, mech_col = st.columns([2,3])
            with cv_col:
                st.markdown("**Top variants:**")
                for v in vlist_s[:5]:
                    ml  = v.get("ml",0)
                    sig = v.get("sig","—")
                    vn  = (v.get("variant_name") or v.get("title","—"))[:50]
                    url = v.get("url","")
                    lnk = f" [↗]({url})" if url else ""
                    clr = rc.get(v.get("ml_rank","NEUTRAL"),"#3a5a7a")
                    st.markdown(
                        f"<div style='font-size:0.81rem;margin:4px 0;color:#5a8090;'>"
                        f"<span style='color:{clr};font-weight:700;'>{ml:.2f}</span> "
                        f"<span style='color:#8ab0d0;'>{vn}</span><br>"
                        f"<span style='color:#2a5070;'>{sig}</span>{lnk}"
                        f"</div>", unsafe_allow_html=True)
            with mech_col:
                st.markdown("**Likely mechanism:**")
                _disease_mechanism(cond, vlist_s)

            if len(vlist_s) >= 3:
                pos_l, ml_l = [], []
                for v in vlist_s[:20]:
                    try:
                        pos_l.append(int(v.get("start") or 0))
                        ml_l.append(v.get("ml",0))
                    except: pass
                if pos_l:
                    fig = go.Figure(go.Scatter(
                        x=pos_l,y=ml_l,mode="markers",
                        marker=dict(size=10,color=ml_l,colorscale=[[0,"#0a1e32"],[0.5,"#ffd60a"],[1,"#ff2d55"]],
                                    cmin=0,cmax=1,showscale=True,colorbar=dict(title="ML",thickness=10,len=0.7)),
                        text=[(v.get("variant_name","")[:30]) for v in vlist_s[:20]],
                        hovertemplate="%{text}<br>Pos:%{x} · Score:%{y:.2f}<extra></extra>",
                    ))
                    fig.update_layout(
                        paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#4a7fa5",
                        xaxis=dict(title="Residue Position",gridcolor="#070f1e"),
                        yaxis=dict(title="ML Pathogenicity",range=[0,1],gridcolor="#070f1e"),
                        height=200,margin=dict(t=5,b=30,l=30,r=10))
                    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})


def _disease_mechanism(cond, variants):
    cl  = cond.lower()
    vn  = " ".join(v.get("variant_name","") for v in variants).lower()
    imps = []
    if any(k in cl for k in ["cancer","carcinoma","tumor","leukemia","lymphoma","glioma"]):
        imps.append("Oncogenic transformation via gain-of-function or dominant-negative effect.")
        imps.append("Somatic acquisition → clonal expansion → tumorigenesis.")
    if "stop" in vn or "nonsense" in vn or "ter" in vn:
        imps.append("Premature stop codon → truncated/unstable protein → haploinsufficiency.")
    if "frameshift" in vn or "del" in vn or "ins" in vn:
        imps.append("Reading-frame disruption → aberrant protein isoform → loss-of-function.")
    if "splice" in vn:
        imps.append("Splice-site mutation → exon skipping or intron retention → mRNA instability.")
    if "missense" in vn:
        imps.append("Missense → altered conformation or binding affinity → partial or full dysfunction.")
    if any(k in cl for k in ["syndrome","developmental","congenital"]):
        imps.append("Germline variant disrupts critical developmental signalling pathway.")
    if not imps:
        imps.append("Mechanism not fully characterised — functional assays recommended.")
    for m in imps:
        st.markdown(f"<div style='color:#3a6080;font-size:0.82rem;margin:3px 0;'>• {m}</div>", unsafe_allow_html=True)
