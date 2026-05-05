from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
from api import (get_diseases, get_subcellular, get_tissue, get_function,
                 get_gpcr, get_xref, fetch_ncbi_gene)
from styles import section_header, cite_block, badge

TISSUE_KW = {
    "Brain":["brain","neuron","cerebral","cortex","hippocampus"],
    "Liver":["liver","hepatic","hepatocyte"],"Heart":["heart","cardiac","myocardium"],
    "Kidney":["kidney","renal","nephron"],"Lung":["lung","pulmonary","alveolar"],
    "Blood":["blood","erythrocyte","leukocyte","platelet"],
    "Breast":["breast","mammary"],"Colon":["colon","colorectal","intestine"],
    "Prostate":["prostate"],"Skin":["skin","keratinocyte","melanocyte"],
    "Muscle":["muscle","skeletal","myoblast"],"Pancreas":["pancreas","islet"],
    "Thyroid":["thyroid"],"Testis":["testis","sperm"],"Ovary":["ovary","oocyte"],
}

def render(pdata, cv, papers, gene_name):
    variants = cv.get("variants",[])

    # ── Tissue + subcellular ─────────────────────────────────────────────────
    c1, c2 = st.columns([1,1], gap="large")
    with c1:
        section_header("🫀","Tissue Associations")
        _tissue(pdata)
    with c2:
        section_header("📍","Subcellular & PTM")
        _subcellular_ptm(pdata)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ── Genomic data ─────────────────────────────────────────────────────────
    section_header("🧬","Genomic Data")
    _genomic(pdata, gene_name)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ── GPCR ─────────────────────────────────────────────────────────────────
    section_header("📡","GPCR Association")
    _gpcr(pdata)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ── Disease somatic/germline ──────────────────────────────────────────────
    section_header("🔬","Disease Classification — Somatic vs Germline")
    _disease_classification(pdata, variants)

    if papers:
        st.markdown(cite_block(papers,4), unsafe_allow_html=True)


def _tissue(pdata):
    text = get_tissue(pdata)
    if text:
        st.markdown(f"<div class='card'><p>{text[:500]}</p></div>", unsafe_allow_html=True)

    fn   = get_function(pdata)
    kws  = [k.get("value","") for k in pdata.get("keywords",[])]
    blob = (text+" "+fn+" "+" ".join(kws)).lower()
    scores = {t: sum(1 for k in ks if k in blob) for t,ks in TISSUE_KW.items()}
    scores = {t:s for t,s in scores.items() if s>0}
    if not scores:
        st.caption("No specific tissue data inferred."); return

    scores = dict(sorted(scores.items(), key=lambda x:-x[1])[:10])
    fig = go.Figure(go.Bar(
        y=list(scores.keys()), x=list(scores.values()), orientation="h",
        marker=dict(color=list(scores.values()),
                    colorscale=[[0,"#0d2545"],[0.5,"#0d4a8a"],[1,"#00e5ff"]],
                    cmin=0, cmax=max(scores.values())),
    ))
    fig.update_layout(
        paper_bgcolor="#04080f", plot_bgcolor="#04080f", font_color="#4a7fa5",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(tickfont=dict(size=11, color="#7aa0c0")),
        margin=dict(l=0,r=0,t=10,b=0), height=180+len(scores)*16,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})


def _subcellular_ptm(pdata):
    locs = get_subcellular(pdata)
    if locs:
        for loc in locs:
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:8px;margin:5px 0;'>"
                f"<span style='color:#00e5ff;font-size:0.8rem;'>◆</span>"
                f"<span style='color:#8ab0d0;font-size:0.86rem;'>{loc}</span></div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No subcellular data.")

    ptm = next((c.get("texts",[{}])[0].get("value","")
                for c in pdata.get("comments",[]) if c.get("commentType")=="PTM"), "")
    if ptm:
        st.markdown("**Post-Translational Modifications**")
        st.markdown(f"<div class='card'><p>{ptm[:400]}</p></div>", unsafe_allow_html=True)


def _genomic(pdata, gene_name):
    uid  = pdata.get("primaryAccession","—")
    omim = get_xref(pdata,"MIM")
    hgnc = get_xref(pdata,"HGNC")
    ens  = get_xref(pdata,"Ensembl")
    gene_d = {}
    try: gene_d = fetch_ncbi_gene(gene_name)
    except: pass

    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown(
            f"<div class='card'><h4>Protein</h4><p>"
            f"UniProt: <b style='color:#00e5ff;'>{uid}</b><br>"
            f"Length: <b>{pdata.get('sequence',{}).get('length','—')} aa</b><br>"
            f"HGNC: {hgnc or '—'}</p></div>",
            unsafe_allow_html=True)
    with c2:
        st.markdown(
            f"<div class='card'><h4>Genomic Location</h4><p>"
            f"Chr: <b style='color:#00e5ff;'>{gene_d.get('chr','—')}</b><br>"
            f"Cytoband: <b>{gene_d.get('map','—')}</b><br>"
            f"Exons: <b>{gene_d.get('exons','—')}</b></p></div>",
            unsafe_allow_html=True)
    with c3:
        st.markdown(
            f"<div class='card'><h4>Cross-References</h4><p>"
            f"OMIM: {f'<a href=\"https://omim.org/entry/{omim}\" target=\"_blank\" style=\"color:#4aa0d4;\">{omim}</a>' if omim else '—'}<br>"
            f"Ensembl: {ens[:20] if ens else '—'}<br>"
            f"<a href='https://www.uniprot.org/uniprotkb/{uid}' target='_blank' style='color:#4aa0d4;'>UniProt ↗</a>"
            f"{'&nbsp;·&nbsp;<a href=\"https://www.ncbi.nlm.nih.gov/gene/'+gene_d['id']+'\" target=\"_blank\" style=\"color:#4aa0d4;\">NCBI Gene ↗</a>' if gene_d.get('id') else ''}"
            f"</p></div>",
            unsafe_allow_html=True)

    if gene_d.get("summary"):
        with st.expander("📖 NCBI Gene Summary"):
            st.write(gene_d["summary"])


def _gpcr(pdata):
    info = get_gpcr(pdata)
    if info["is_gpcr"]:
        st.markdown(
            "<div style='background:linear-gradient(135deg,#041525,#05101e);border:1px solid #00e5ff33;"
            "border-radius:12px;padding:1.2rem 1.5rem;display:flex;gap:14px;align-items:flex-start;'>"
            "<div style='font-size:2.2rem;'>📡</div>"
            "<div><p style='color:#00e5ff;font-weight:700;font-size:1rem;margin:0 0 4px;'>"
            "GPCR — Important / Piggybacked Target</p>"
            "<p style='color:#4a7fa5;font-size:0.86rem;margin:0;'>"
            "GPCRs represent ~34% of all FDA-approved drug targets. This protein's receptor nature "
            "makes it highly druggable. Consider biased agonism, allosteric modulation, and "
            "antibody-based approaches for therapeutic development.</p></div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='background:#060e1c;border:1px solid #0d2545;border-radius:10px;"
            "padding:0.9rem 1.2rem;color:#2a5070;font-size:0.86rem;'>"
            "Not classified as a GPCR in UniProt.</div>",
            unsafe_allow_html=True,
        )

    # Interactions
    inters = []
    for c in pdata.get("comments",[]):
        if c.get("commentType") == "INTERACTION":
            for i in c.get("interactions",[]):
                g = i.get("interactantTwo",{}).get("geneName","")
                if g: inters.append(g)
    if inters:
        st.markdown(
            "<div style='margin-top:0.8rem;color:#2a5070;font-size:0.8rem;'>Known interactors: "
            + " · ".join(f"<code style='background:#060e1c;color:#4a90d4;padding:1px 5px;border-radius:4px;'>{g}</code>" for g in inters[:12])
            + "</div>", unsafe_allow_html=True)


def _disease_classification(pdata, variants):
    somatic, germline = set(), set()
    for v in variants:
        origin = v.get("origin","").lower()
        cond   = v.get("condition","")
        if not cond or cond=="Not specified": continue
        if "somatic" in origin or v.get("somatic"): somatic.add(cond)
        elif any(x in origin for x in ["germline","inherited","de novo"]): germline.add(cond)
        elif v.get("score",0) >= 4: germline.add(cond)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"<div style='background:#04100a;border:1px solid #00c89633;border-radius:12px;padding:1.2rem;'>"
            f"<p style='color:#00c896;font-weight:700;font-size:0.95rem;margin:0 0 4px;'>🧬 Germline ({len(germline)})</p>"
            f"<p style='color:#2a6050;font-size:0.76rem;margin:0 0 8px;'>Heritable — present in all cells from birth</p>",
            unsafe_allow_html=True)
        if germline:
            for c in sorted(germline)[:8]:
                st.markdown(f"<div style='color:#4a9070;font-size:0.82rem;margin:3px 0;'>◆ {c[:70]}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='color:#1a4030;font-size:0.82rem;'>No germline classifications found.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown(
            f"<div style='background:#120408;border:1px solid #ff2d5533;border-radius:12px;padding:1.2rem;'>"
            f"<p style='color:#ff2d55;font-weight:700;font-size:0.95rem;margin:0 0 4px;'>🔴 Somatic ({len(somatic)})</p>"
            f"<p style='color:#5a2030;font-size:0.76rem;margin:0 0 8px;'>Acquired — arises in specific cell populations</p>",
            unsafe_allow_html=True)
        if somatic:
            for c in sorted(somatic)[:8]:
                st.markdown(f"<div style='color:#804050;font-size:0.82rem;margin:3px 0;'>◆ {c[:70]}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='color:#3a1020;font-size:0.82rem;'>No somatic classifications found.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # UniProt disease cards
    diseases = get_diseases(pdata)
    if diseases:
        st.markdown("<br>**UniProt Disease Annotations**", unsafe_allow_html=True)
        for d in diseases[:6]:
            omim = d.get("omim","")
            link = f" · <a href='https://omim.org/entry/{omim}' target='_blank' style='color:#4a90d4;font-size:0.76rem;'>OMIM {omim}</a>" if omim else ""
            note_html = f"<p style='color:#ffd60a;font-size:0.8rem;margin-top:4px;'>{d['note'][:160]}</p>" if d.get('note') else ""
            st.markdown(
                f"<div class='card'><h4>{d['name']}{link}</h4>"
                f"<p>{d.get('desc','')[:280]}</p>"
                f"{note_html}"
                f"</div>", unsafe_allow_html=True)
