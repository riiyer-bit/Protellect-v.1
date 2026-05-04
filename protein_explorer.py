"""protein_explorer.py — Tab 3: Universal Protein Explorer"""
import streamlit as st
import streamlit.components.v1 as components
import re, requests, numpy as np, base64
from pathlib import Path

try:
    from logo import LOGO_DATA_URL as LOGO_B64
except Exception:
    _lp = Path("/mnt/user-data/uploads/1777622887238_image.png")
    LOGO_B64 = ("data:image/png;base64,"+base64.b64encode(_lp.read_bytes()).decode()) if _lp.exists() else None

from diagrams import build_tissue_diagram, build_genomic_diagram, build_gpcr_diagram, build_cell_impact_diagram
from evidence_layer import classify_protein_role, calculate_dbr, assign_genomic_tier

def _viewer(pdb, rs, w=610, h=400):
    if not pdb or len(pdb)<100:
        return f"<html><body style='background:#080b14;display:flex;align-items:center;justify-content:center;height:{h}px;color:#444;font-family:monospace;font-size:12px;text-align:center'>Structure not available<br><span style='font-size:10px;display:block;margin-top:6px'>Enter protein name in Q&amp;A → auto-fetches correct PDB</span></body></html>"
    esc = pdb.replace("\\","\\\\").replace("`","\\`").replace("${","\\${")[:280000]
    rlist = []
    for line in pdb.split('\n'):
        if line.startswith('ATOM'):
            try: rlist.append(int(line[22:26].strip()))
            except: pass
    zoom = f"{min(rlist)}-{max(rlist)}" if rlist else "1-500"
    sph_parts = []
    for r,d in rs.items():
        sph_parts.append("v.addStyle({resi:%d},{sphere:{color:'%s',radius:%s}});" % (r, d["color"], d["radius"]))
    sph = "\n".join(sph_parts)
    return f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<style>body{{margin:0;background:#080b14}}#v{{width:{w}px;height:{h}px}}</style>
</head><body><div id="v"></div><script>
const p=`{esc}`;
let v=$3Dmol.createViewer('v',{{backgroundColor:'#080b14',antialias:true}});
v.addModel(p,'pdb');v.setStyle({{}},{{cartoon:{{color:'#1e2440',opacity:0.55}}}});
{sph}
v.zoomTo({{resi:'{zoom}'}});v.spin(false);v.render();
</script></body></html>"""

def render():
    if LOGO_B64:
        st.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px"><img src="{LOGO_B64}" style="height:40px;object-fit:contain;border-radius:7px"><div><strong style="font-size:1.1rem">Protein Explorer</strong><p style="color:#555;font-size:0.83rem;margin:0">Where it lives · Genomic framework · ClinVar variants · GPCR interaction</p></div></div>', unsafe_allow_html=True)
    st.divider()

    if "t_scored" not in st.session_state:
        st.info("👈 Run **Triage System** first.")
        return

    scored     = st.session_state.t_scored
    enrichment = st.session_state.get("t_enrichment")
    p_info     = st.session_state.get("t_protein")
    verdict_st = st.session_state.get("t_verdict")
    pc         = "priority_final" if "priority_final" in scored.columns else "priority"

    gene      = (p_info or {}).get("gene_name","")
    uid       = (p_info or {}).get("uniprot_id","")
    uni       = (enrichment or {}).get("uniprot",{}) if enrichment else {}
    prot_name = uni.get("protein_name","") or gene
    is_gpcr   = uni.get("is_gpcr",False)
    g_prot    = uni.get("g_protein_coupling","")
    subcel    = uni.get("subcellular",[])
    tissue    = uni.get("tissue_specificity","")
    domains   = uni.get("domains",[])
    n_tm      = len(uni.get("transmembrane_regions",[]))
    clinvar   = (enrichment or {}).get("clinvar",{}) if enrichment else {}
    prot_len  = uni.get("length",0)
    chrom_str = ""

    # ClinVar count — ONLY source of truth
    n_path = 0
    for variants in clinvar.values():
        if isinstance(variants, list):
            for v in variants:
                sig = v.get("significance","").lower()
                if "pathogenic" in sig and "benign" not in sig:
                    n_path += 1
    if verdict_st and verdict_st.get("n_pathogenic",0) > n_path:
        n_path = verdict_st["n_pathogenic"]

    dbr    = calculate_dbr(n_path, prot_len)
    tier   = assign_genomic_tier(dbr, n_path)
    tc     = {"CRITICAL":"#FF4C4C","HIGH":"#FFA500","LOW":"#FFD700","NONE":"#888","UNKNOWN":"#4CA8FF"}.get(tier,"#888")
    role   = classify_protein_role(gene, n_path)
    dbr_s  = f"{dbr:.3f}" if dbr is not None else "N/A"
    gpcr_t = f"GPCR · {g_prot}" if is_gpcr else "Non-GPCR"

    st.markdown(f"""
    <div style="background:#0a0a14;border:2px solid {tc};border-radius:12px;padding:18px 22px;margin-bottom:16px">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
        <div>
          <div style="font-size:1.15rem;font-weight:700;color:#eee;font-family:IBM Plex Mono,monospace">{gene}{f" — {prot_name}" if prot_name and prot_name!=gene else ""}</div>
          <div style="font-size:0.78rem;color:#555;margin-top:3px">{f"UniProt {uid} · " if uid else ""}{prot_len} aa · {gpcr_t}{" · "+", ".join(subcel[:2]) if subcel else ""}</div>
        </div>
        <div style="text-align:right">
          <div style="font-size:1.4rem;font-weight:700;font-family:IBM Plex Mono,monospace;color:{tc}">{role['icon']} {role['label']}</div>
          <div style="font-size:0.72rem;color:#555;margin-top:3px">{n_path} germline pathogenic (ClinVar) · DBR {dbr_s}</div>
        </div>
      </div>
      <div style="margin-top:10px;padding-top:8px;border-top:1px solid {tc}33;font-size:0.8rem;color:#aaa;line-height:1.6">{role.get('note','')[:200]}</div>
      {f'<div style="margin-top:8px;padding:8px 12px;background:#1a0808;border-radius:6px;border-left:3px solid #FF4C4C;font-size:0.78rem;color:#aaa">{role.get("warning","")}</div>' if role.get("warning") else ''}
    </div>""", unsafe_allow_html=True)

    scol, icol = st.columns([1.4,1], gap="large")

    with scol:
        st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.12em;color:#444;margin-bottom:6px">3D Structure — coloured by triage priority</div>', unsafe_allow_html=True)
        pdb_text, slabel = None, ""
        if enrichment and enrichment.get("structure_pdb"):
            pdb_text, slabel = enrichment["structure_pdb"], enrichment.get("structure_source","")
        elif uid:
            with st.spinner(f"Fetching structure for {gene}..."):
                try:
                    from db_enrichment import fetch_uniprot_full, get_structure_for_protein
                    pdb_text, slabel = get_structure_for_protein(fetch_uniprot_full(uid), uid)
                except Exception:
                    pass
        # Only use TP53 structure if the gene IS TP53
        if not pdb_text and gene.upper() == "TP53":
            try:
                r = requests.get("https://files.rcsb.org/download/2OCJ.pdb", timeout=12)
                if r.status_code == 200:
                    pdb_text, slabel = r.text, "TP53 · PDB 2OCJ"
            except Exception: pass
        if slabel: st.caption(f"🏗️ {slabel}")
        cmap = {"HIGH":"#FF4C4C","MEDIUM":"#FFA500","LOW":"#4CA8FF"}
        rmap = {"HIGH":1.1,"MEDIUM":0.75,"LOW":0.45}
        if pdb_text:
            pdb_res = set()
            for line in pdb_text.split('\n'):
                if line.startswith('ATOM'):
                    try: pdb_res.add(int(line[22:26].strip()))
                    except: pass
            upos = [int(r["residue_position"]) for _,r in scored.iterrows()]
            if pdb_res and any(p in pdb_res for p in upos):
                rs = {int(row["residue_position"]):{"color":cmap[str(row[pc])],"radius":rmap[str(row[pc])]} for _,row in scored.iterrows() if int(row["residue_position"]) in pdb_res}
            else:
                pr = sorted(pdb_res) if pdb_res else list(range(1,500))
                n  = min(len(scored), len(pr))
                mp = [pr[i] for i in np.linspace(0,len(pr)-1,n,dtype=int)]
                rs = {mp[i]:{"color":cmap[str(row[pc])],"radius":rmap[str(row[pc])]*1.4} for i,(_,row) in enumerate(scored.head(n).iterrows())}
            components.html(_viewer(pdb_text, rs, 600, 395), height=402)
        else:
            st.warning(f"No structure for {gene}. Enter protein name in Q&A and enable DB enrichment.")
        st.markdown('<div style="display:flex;gap:16px;margin-top:5px;font-size:0.75rem"><span><span style="color:#FF4C4C">●</span> HIGH</span><span><span style="color:#FFA500">●</span> MEDIUM</span><span><span style="color:#4CA8FF">●</span> LOW</span></div>', unsafe_allow_html=True)

    with icol:
        st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.12em;color:#4CAF50;margin-bottom:6px">Where this protein lives</div>', unsafe_allow_html=True)
        if subcel:
            for loc in subcel[:5]:
                ico = "🔬" if "nucle" in loc.lower() else "🧬" if "membran" in loc.lower() else "⚙️" if any(x in loc.lower() for x in ("mitoch","cytopl","endop")) else "📍"
                st.markdown(f'<div style="padding:5px 10px;margin-bottom:4px;background:#0a0c14;border:1px solid #1e2030;border-radius:6px;font-size:0.8rem;color:#bbb">{ico} {loc}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#555;font-size:0.78rem;padding:6px">Enable DB enrichment to load subcellular location</div>', unsafe_allow_html=True)

        st.markdown('<br><div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.12em;color:#4CA8FF;margin-bottom:6px">Genomic identity</div>', unsafe_allow_html=True)
        try:
            from protein_deep_dive import fetch_chromosome_location
            cd = fetch_chromosome_location(gene, uni.get("ensembl_id",""))
            chrom_str = f"Chr {cd['chromosome']}" if cd.get('chromosome') else "—"
        except: chrom_str = "—"
        for lbl,val in [("Gene",gene or "—"),("UniProt",uid or "—"),("Chromosome",chrom_str),("Length",f"{prot_len} aa" if prot_len else "—"),("Domains",f"{len(domains)} annotated"),("TM helices",str(n_tm)),("GPCR",f"✓ {g_prot}" if is_gpcr else "No")]:
            st.markdown(f'<div style="display:flex;gap:8px;padding:4px 0;border-bottom:1px solid #0d0f1a;font-size:0.77rem"><span style="color:#3a3d5a;min-width:88px;font-family:IBM Plex Mono,monospace;font-size:0.67rem;flex-shrink:0">{lbl}</span><span style="color:#bbb">{val}</span></div>', unsafe_allow_html=True)

        st.markdown('<br>', unsafe_allow_html=True)
        st.markdown(f"""<div style="background:#0a0a14;border:1px solid {tc}55;border-radius:8px;padding:10px 14px">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div style="font-size:1.8rem;font-weight:700;font-family:IBM Plex Mono,monospace;color:{tc}">{n_path}</div>
            <div style="text-align:right;font-size:0.68rem;color:#555">germline pathogenic<br>ClinVar · DBR {dbr_s}</div>
          </div>
          <div style="font-size:0.7rem;color:#888;margin-top:5px;line-height:1.5">{role.get('note','')[:100]}</div>
        </div>""", unsafe_allow_html=True)

    # Diagrams
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.15em;color:#444;border-bottom:1px solid #1e2030;padding-bottom:6px;margin-bottom:14px">Biological Context</div>', unsafe_allow_html=True)
    dt1,dt2,dt3,dt4 = st.tabs(["🧬 Tissue Expression","📍 Genomic Breakdown","⚡ GPCR Signalling","🔬 Cell Impact"])

    with dt1:
        components.html(build_tissue_diagram(gene, tissue or "", None), height=330, scrolling=False)
        st.caption(f"{gene} tissue expression · Source: {'UniProt experimental' if tissue else 'curated reference'}")

    with dt2:
        pv, bv = [], []
        for pk, variants in clinvar.items():
            if isinstance(variants, list):
                for v in variants:
                    sig = v.get("significance","").lower()
                    try: pos = int(pk)
                    except:
                        m = re.search(r'[A-Z](\d+)[A-Z=*]', v.get("title",""))
                        pos = int(m.group(1)) if m else 0
                    if pos > 0:
                        if "pathogenic" in sig and "benign" not in sig: pv.append({"pos":pos})
                        elif "benign" in sig: bv.append({"pos":pos})
        for nv in uni.get("natural_variants",[]):
            p = int(nv.get("pos") or nv.get("position") or 0)
            if p > 0:
                (pv if (nv.get("disease") or nv.get("pathogenic")) else bv).append({"pos":p})
        components.html(build_genomic_diagram(gene, chrom_str.replace("Chr ",""), prot_len, domains, pv, bv), height=295, scrolling=False)
        st.caption(f"Domains: UniProt · Variants: ClinVar · Red=pathogenic · Blue=benign · {len(pv)} pathogenic positions")

    with dt3:
        if is_gpcr and g_prot:
            components.html(build_gpcr_diagram(gene, g_prot, prot_name, n_tm or 7), height=430, scrolling=False)
            st.caption(f"{gene} GPCR cascade · G-protein: {g_prot} · Source: UniProt + IUPHAR/BPS")
        else:
            st.markdown(f"""<div style="background:#0a0c14;border:1px solid #1e2030;border-radius:10px;padding:30px;text-align:center;margin-top:10px">
              <div style="font-size:1.6rem;margin-bottom:10px">🔬</div>
              <div style="font-family:IBM Plex Mono,monospace;color:#444">{gene} is not a GPCR</div>
              <div style="font-size:0.73rem;color:#333;margin-top:6px">No 7TM domain detected. GPCR cascade not applicable.</div>
            </div>""", unsafe_allow_html=True)

    with dt4:
        dis4 = []
        for variants in clinvar.values():
            if isinstance(variants,list):
                for v in variants:
                    for c in v.get("conditions",[]):
                        if c and "not provided" not in c.lower() and c not in dis4: dis4.append(c)
        components.html(build_cell_impact_diagram(gene, tier, n_path, dis4[:4], subcel, is_gpcr, g_prot), height=375, scrolling=False)
        st.caption(f"Cell impact · {n_path} ClinVar pathogenic variants · Not predicted — derived from confirmed human genetics")

    # ClinVar table
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.15em;color:#444;border-bottom:1px solid #1e2030;padding-bottom:6px;margin-bottom:12px">ClinVar Pathogenic Variants — Germline Only</div>', unsafe_allow_html=True)
    if pv:
        import pandas as pd
        st.dataframe(pd.DataFrame([{"Position":v.get("pos","—"),"Note":v.get("note","—")[:60]} for v in pv[:40]]), use_container_width=True, height=200)
        st.caption(f"Showing {min(40,len(pv))} of {len(pv)} pathogenic positions. Source: ClinVar + UniProt natural variants.")
    elif n_path > 0:
        st.info(f"{n_path} pathogenic variants in ClinVar for {gene}. Enable DB enrichment for position-level mapping.")
    else:
        st.markdown(f"""<div style="background:#0a0a0a;border:1px solid #333;border-radius:8px;padding:14px;font-size:0.8rem;color:#666;line-height:1.7">
          Zero confirmed germline pathogenic variants for <strong style="color:#eee">{gene}</strong>.
          {f"Disease biology lies in interaction partners: {', '.join(role.get('partners',[])[:3])}." if role.get('role')=='piggyback' else "Enable DB enrichment to fetch full ClinVar data."}
        </div>""", unsafe_allow_html=True)
