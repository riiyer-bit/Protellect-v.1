"""
Mol Cell Bio module — Chemical structures, phosphorylation networks,
kinase/phosphatase analysis, GPCR signalling, genetic basis.
"""
import streamlit as st, requests, json, re
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# ─── Chemical structure display ────────────────────────────────────────────────

def render_chemical_structure(compound_name: str, smiles: str = "", cid: str = ""):
    """Display chemical structure from PubChem with properties."""
    from apis import api_pubchem_structure
    if not smiles and not cid:
        data = api_pubchem_structure(compound_name)
    else:
        data = {"cid": cid, "smiles": smiles, "formula": "", "mw": "", "logp": "", "img_url": f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/PNG" if cid else ""}

    if not data:
        st.info(f"No structure found for {compound_name}")
        return

    c1, c2 = st.columns([1, 2])
    with c1:
        if data.get("img_url"):
            try:
                st.image(data["img_url"], caption=compound_name, width=200)
            except: pass
        if data.get("cid"):
            st.markdown(f"<a href='https://pubchem.ncbi.nlm.nih.gov/compound/{data['cid']}' target='_blank' style='font-size:.75rem;color:#00e5ff'>PubChem {data['cid']} ↗</a>", unsafe_allow_html=True)
    with c2:
        props = []
        if data.get("formula"): props.append(("Molecular formula", data["formula"]))
        if data.get("mw"): props.append(("Molecular weight", f"{data['mw']} Da"))
        if data.get("logp"): props.append(("LogP (lipophilicity)", str(data["logp"])))
        if data.get("smiles"): props.append(("SMILES", f"`{data['smiles'][:60]}{'...' if len(data.get('smiles',''))>60 else ''}`"))
        for label, val in props:
            st.markdown(f"<div style='display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #0d2545;font-size:.8rem'><span style='color:#5a8090'>{label}</span><span style='color:#d0e8ff'>{val}</span></div>", unsafe_allow_html=True)

# ─── Phosphorylation network visualisation ─────────────────────────────────────

def render_phospho_network(gene: str, ptm_data: list, cv_variants: list):
    """
    Visualise phosphorylation network with signal vs noise classification.
    KEY INSIGHT: Only phospho sites where residue mutation causes disease = true signal.
    """
    # Classify phospho sites
    disease_positions = set()
    for v in cv_variants:
        title = v.get("title", "")
        # Extract amino acid position from ClinVar title
        positions = re.findall(r'p\.[A-Za-z]+(\d+)[A-Za-z]', title)
        disease_positions.update(int(p) for p in positions)

    # Build phospho site data
    phdata = []
    for ptm_text in ptm_data[:5]:
        # Extract phospho positions from text
        positions = re.findall(r'[Ss]er-?(\d+)|[Ss]erine.?(\d+)|[Tt]hr-?(\d+)|[Tt]yrosine.?(\d+)|[Tt]yr-?(\d+)', ptm_text)
        for pos_group in positions:
            pos = int(next(p for p in pos_group if p))
            is_signal = pos in disease_positions
            is_flna_s2152 = gene.upper() in ("FLNA", "FLN1") and pos == 2152
            phdata.append({"position": pos, "residue": "Ser/Thr/Tyr",
                          "classification": "VALIDATED SIGNAL" if is_flna_s2152 else ("PROBABLE SIGNAL" if is_signal else "LIKELY NOISE"),
                          "color": "#00c896" if is_flna_s2152 else ("#ffd60a" if is_signal else "#ff2d55")})

    if not phdata:
        st.info("No phosphorylation sites extracted from UniProt data.")
        return

    # Create bar chart
    df = pd.DataFrame(phdata)
    fig = go.Figure()
    for cls, clr in [("VALIDATED SIGNAL","#00c896"),("PROBABLE SIGNAL","#ffd60a"),("LIKELY NOISE","#ff2d55")]:
        mask = df["classification"]==cls
        if mask.any():
            fig.add_trace(go.Bar(x=df[mask]["position"], y=[1]*mask.sum(), name=cls,
                                  marker_color=clr, hovertemplate=f"Position %{{x}}<br>{cls}<extra></extra>"))
    fig.update_layout(barmode="stack", height=200, plot_bgcolor="#010306", paper_bgcolor="#010306",
                      font=dict(color="#d0e8ff",size=11), margin=dict(l=40,r=20,t=30,b=40),
                      title=dict(text=f"{gene} Phosphorylation Sites — Signal vs Noise",font=dict(color="#00e5ff",size=12)),
                      xaxis=dict(title="Residue position",gridcolor="#0d2545"),
                      yaxis=dict(visible=False), showlegend=True,
                      legend=dict(bgcolor="#040c14",bordercolor="#0d2545"))
    st.plotly_chart(fig, use_container_width=True)

    # Rule explanation
    st.markdown("<div style='background:#020d18;border:1px solid #00e5ff22;border-radius:8px;padding:.7rem 1rem;font-size:.78rem;color:#5a8090'>"
                "<b style='color:#00e5ff'>Signal vs Noise Rule:</b> A phosphorylation site is only a validated signal if "
                "its specific residue mutation causes human disease (ClinVar P/LP). "
                "FLNA Ser2152 is the canonical example — PhosphoSite highest peak, conformationally gated by GPCR H8 binding. "
                "Background kinase activity (EGFR, cancer cell lines) phosphorylates thousands of substrates non-specifically — this is noise.</div>",
                unsafe_allow_html=True)

# ─── Kinase/Phosphatase interaction map ────────────────────────────────────────

KINASE_SUBSTRATE_MAP = {
    "PKA": {"substrates": ["FLNA Ser2152", "CREB Ser133", "HSL Ser563", "RYR2 Ser2808"], "activators": ["cAMP"], "inhibitors": ["PKI", "H89"], "disease": "Carney complex (PRKAR1A mutations)"},
    "PKC": {"substrates": ["RasGRP Ser316", "MARCKS Ser152", "EGFR Thr654"], "activators": ["DAG", "Ca2+", "phorbol esters"], "inhibitors": ["staurosporine", "Gö6976"], "disease": "Multiple cancers"},
    "CaMKII": {"substrates": ["RYR2 Ser2814", "PLN Thr17", "eNOS Ser617"], "activators": ["Ca2+/Calmodulin"], "inhibitors": ["KN-93", "autocamtide-2"], "disease": "Cardiac arrhythmia, Long QT"},
    "GSK3β": {"substrates": ["Tau Ser396", "β-catenin Ser33", "GYS Ser641"], "activators": ["Inactive state (default)"], "inhibitors": ["Lithium", "SB216763", "CHIR99021"], "disease": "Alzheimer's, bipolar disorder"},
    "CDK5": {"substrates": ["Tau Ser202", "DARPP-32 Thr75", "Synapsin Ser553"], "activators": ["p35", "p25 (aberrant)"], "inhibitors": ["roscovitine", "dinaciclib"], "disease": "Alzheimer's, neurodegeneration"},
    "LRRK2": {"substrates": ["Rab8A Thr72", "Rab10 Thr73", "ezrin Thr567"], "activators": ["GTP binding", "G2019S GOF"], "inhibitors": ["BIIB122", "DNL151", "MLi-2"], "disease": "Parkinson's disease (G2019S)"},
    "GRK2": {"substrates": ["ADRB2 Ser355/356", "AGTR1 Ser332", "RHODOPSIN Ser338"], "activators": ["Free Gβγ subunit", "agonist-occupied GPCR"], "inhibitors": ["paroxetine scaffold", "compound 101"], "disease": "Heart failure (elevated GRK2)"},
    "PP2A": {"substrates": ["Tau (dephosphorylation)", "AKT", "ERK"], "activators": ["PR55 regulatory subunit"], "inhibitors": ["Okadaic acid", "calyculin A"], "disease": "Cancer (PP2A inactivation common)"},
    "PP1": {"substrates": ["GYS Ser641 (activation)", "PLN Ser16 (activation)", "eIF2α"], "activators": ["Spinophilin", "neurabin"], "inhibitors": ["Okadaic acid", "tautomycin"], "disease": "Cardiac dysfunction (PLN dephosphorylation)"},
}

def render_kinase_phosphatase_panel(gene: str, color: str):
    """Show kinases and phosphatases relevant to this protein."""
    st.markdown("<div style='color:#5a8090;font-size:.8rem;margin-bottom:.6rem'>Kinases phosphorylate (activate/inactivate) and phosphatases reverse this modification. Understanding which enzymes regulate your protein of interest is essential for drug target selection — you may need to target the kinase, not the protein itself.</div>", unsafe_allow_html=True)

    # Check if this gene IS a kinase or phosphatase
    is_kinase = any(x in gene.upper() for x in ["GRK","CDK","PKA","PKC","LRRK","BRAF","EGFR","ALK","JAK","SRC","ABL","FGFR","MET","RET"])
    is_phosphatase = any(x in gene.upper() for x in ["PP1","PP2A","PP2B","PTEN","PTPN","CDC14","PTP"])

    if is_kinase and gene.upper() in KINASE_SUBSTRATE_MAP:
        info = KINASE_SUBSTRATE_MAP[gene.upper()]
        st.markdown(f"<div style='background:#040c14;border:1px solid {color}44;border-radius:10px;padding:.8rem 1rem;margin-bottom:.5rem'>", unsafe_allow_html=True)
        st.markdown(f"**{gene} is a kinase** — it phosphorylates these substrates:", unsafe_allow_html=False)
        for sub in info["substrates"]:
            validated = gene.upper() == "PKA" and "2152" in sub
            icon = "✅" if validated else "◉"
            signal_note = " ← VALIDATED SIGNAL (disease variant confirmed)" if validated else ""
            st.markdown(f"<div style='padding:3px 0;font-size:.82rem;color:#d0e8ff'>{icon} {sub}{signal_note}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color:#5a8090;font-size:.78rem;margin-top:.4rem'>Disease: {info['disease']}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Show relevant kinases from the map
    with st.expander("📊 Kinase/Phosphatase Reference Map", expanded=False):
        for kin_name, kin_data in KINASE_SUBSTRATE_MAP.items():
            relevant = any(gene.upper() in sub for sub in kin_data["substrates"])
            if relevant or kin_name == gene.upper():
                st.markdown(f"**{kin_name}** → substrates: {', '.join(kin_data['substrates'][:2])}", unsafe_allow_html=False)
                st.markdown(f"<div style='color:#3a6080;font-size:.76rem'>Inhibitors: {', '.join(kin_data['inhibitors'][:2])} · Disease: {kin_data['disease']}</div>", unsafe_allow_html=True)
                st.markdown("---")

# ─── GPCR signalling diagram ──────────────────────────────────────────────────

GPCR_SIGNALLING = {
    "Gs": {"effector": "Adenylyl cyclase", "second_messenger": "cAMP ↑", "PKA_activated": True, "downstream": ["PKA → CREB", "PKA → FLNA Ser2152 (via H8-FBM)", "PKA → HSL (lipolysis)", "PKA → RYR2 (Ca2+ release)"], "drugs": ["Forskolin (activator)", "Gs-coupled GPCR agonists"]},
    "Gi": {"effector": "Adenylyl cyclase (inhibition)", "second_messenger": "cAMP ↓", "PKA_activated": False, "downstream": ["MAPK activation", "PI3K activation", "K+ channel opening (IKACh)"], "drugs": ["Pertussis toxin (Gi inhibitor)", "Gi-coupled agonists"]},
    "Gq": {"effector": "PLCβ", "second_messenger": "IP3 + DAG", "PKA_activated": False, "downstream": ["IP3 → Ca2+ release (ER)", "DAG → PKC activation", "Ca2+ → CaMKII", "Ca2+ → Calcineurin/NFAT"], "drugs": ["YM-254890 (Gq inhibitor)", "Angiotensin II (AT1R/Gq)"]},
    "G12/13": {"effector": "RhoGEF", "second_messenger": "Rho GTPase ↑", "PKA_activated": False, "downstream": ["RhoA → ROCK → cytoskeletal remodelling", "Actin stress fibres", "Gene transcription (SRF)"], "drugs": ["Y-27632 (ROCK inhibitor)"]},
    "β-arrestin": {"effector": "GPCR desensitisation", "second_messenger": "Receptor internalisation", "PKA_activated": False, "downstream": ["Receptor endocytosis (clathrin)", "ERK1/2 (arrestin-dependent)", "β-arrestin scaffold complex"], "drugs": ["⚠️ ZERO confirmed Mendelian disease variants in ARRB1/ARRB2. Do not use as primary readout."]},
    "H8-Filamin (PRIMARY)": {"effector": "Filamin A Ig21", "second_messenger": "FLNA Ser2152 phosphorylation", "PKA_activated": True, "downstream": ["Actin cytoskeletal coupling", "Cell migration/shape", "GPCR-cytoskeletal axis"], "drugs": ["Nakamura et al. JBC 2015 — IP-protected readout. More proximal than cAMP/IP3/arrestin."]},
}

def render_gpcr_signalling_diagram(gene: str, color: str):
    """Render an interactive GPCR signalling pathway diagram."""
    is_gpcr = any(x in gene for x in ["ADRB","AGTR","MAS","CHRM","ADRA","DRD","HTR","CCR","CXCR"])
    is_arrb = gene in ("ARRB1","ARRB2")

    if is_arrb:
        st.markdown("<div style='background:#0a0205;border:1px solid #ff2d5533;border-radius:10px;padding:.8rem 1rem;margin:.4rem 0'><div style='color:#ff2d55;font-weight:600;font-size:.85rem'>⛔ Beta-arrestin — deprioritise</div><div style='color:#5a3040;font-size:.8rem;line-height:1.6'>ARRB1/ARRB2 double KO mice are viable. Zero Mendelian disease-causing variants in ClinVar. Beta-arrestin phosphorylation codes are kinase noise — no disease variant validates any phospho-site. Do NOT use as primary GPCR signalling readout or drug target. Use Filamin A Ser2152-P instead.</div></div>", unsafe_allow_html=True)
        return

    for pathway_name, pathway_data in GPCR_SIGNALLING.items():
        is_primary = "H8" in pathway_name
        border = "#00e5ff" if is_primary else "#0d2545"
        bg = "#020d18" if is_primary else "#040c14"
        with st.expander(f"{'⭐ PRIMARY — ' if is_primary else ''}{pathway_name} pathway", expanded=is_primary):
            st.markdown(f"<div style='background:{bg};border-left:3px solid {border};padding:.7rem 1rem;border-radius:0 8px 8px 0'>", unsafe_allow_html=True)
            st.markdown(f"<div style='color:{border};font-weight:600;font-size:.85rem;margin-bottom:.3rem'>Effector: {pathway_data['effector']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='color:#5a8090;font-size:.8rem;margin-bottom:.3rem'>Second messenger: {pathway_data['second_messenger']}</div>", unsafe_allow_html=True)
            st.markdown("<div style='color:#3a6080;font-size:.78rem;font-weight:600;margin-bottom:.2rem'>Downstream effects:</div>", unsafe_allow_html=True)
            for ds in pathway_data["downstream"]:
                st.markdown(f"<div style='color:#6a9ab0;font-size:.78rem;padding:2px 0'>→ {ds}</div>", unsafe_allow_html=True)
            if pathway_data.get("drugs"):
                st.markdown(f"<div style='color:#3a5060;font-size:.76rem;margin-top:.3rem'>{'⚠️ ' if 'ZERO' in str(pathway_data['drugs'][0]) else ''}{pathway_data['drugs'][0]}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ─── AlphaMissense visualisation ───────────────────────────────────────────────

def render_alphamissense_chart(am_data: dict, cv_variants: list, color: str):
    """Render AlphaMissense per-residue pathogenicity with ClinVar overlay."""
    if not am_data or not am_data.get("pos_max_scores"):
        st.info("AlphaMissense data not available for this protein.")
        return

    pos_scores = am_data["pos_max_scores"]
    positions = sorted(pos_scores.keys())
    scores = [pos_scores[p] for p in positions]

    # Extract ClinVar variant positions
    cv_positions = {}
    for v in cv_variants:
        m = re.findall(r'p\.[A-Za-z]+(\d+)[A-Za-z]', v.get("title",""))
        for pos in m:
            cv_positions[int(pos)] = v.get("ml_rank","")

    # Create figure
    fig = go.Figure()

    # AlphaMissense scores
    fig.add_trace(go.Scatter(
        x=positions, y=scores,
        mode="lines", name="AlphaMissense score",
        line=dict(color="#5a8090", width=1),
        fill="tozeroy", fillcolor="rgba(90,128,144,0.1)"
    ))

    # Pathogenic threshold line
    fig.add_hline(y=0.564, line_dash="dash", line_color="#ff8c42",
                  annotation_text="Pathogenic threshold (0.564)", annotation_position="top right",
                  annotation_font_color="#ff8c42")

    # ClinVar variants overlay
    for pos, rank in cv_positions.items():
        if pos in pos_scores:
            rank_colors = {"CRITICAL":"#ff2d55","HIGH":"#ff8c42","MODERATE":"#ffd60a","LOW":"#5a8090"}
            rc = rank_colors.get(rank,"#5a8090")
            fig.add_trace(go.Scatter(
                x=[pos], y=[pos_scores[pos]],
                mode="markers", name=f"ClinVar {rank} at {pos}",
                marker=dict(color=rc, size=10, symbol="diamond"),
                showlegend=False,
                hovertemplate=f"Position {pos}<br>ClinVar: {rank}<br>AM score: {pos_scores[pos]:.3f}<extra></extra>"
            ))

    fig.update_layout(
        height=300, plot_bgcolor="#010306", paper_bgcolor="#010306",
        font=dict(color="#d0e8ff",size=11), margin=dict(l=40,r=20,t=40,b=40),
        title=dict(text="AlphaMissense Pathogenicity (DeepMind) + ClinVar Variants",font=dict(color=color,size=12)),
        xaxis=dict(title="Residue position",gridcolor="#0d2545"),
        yaxis=dict(title="Pathogenicity score",gridcolor="#0d2545",range=[0,1]),
        showlegend=True, legend=dict(bgcolor="#040c14",bordercolor="#0d2545")
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary metrics
    cc = st.columns(4)
    with cc[0]: st.metric("AlphaMissense pathogenic", am_data.get("pathogenic_count",0))
    with cc[1]: st.metric("Ambiguous", am_data.get("ambiguous_count",0))
    with cc[2]: st.metric("Benign predicted", am_data.get("benign_count",0))
    with cc[3]: st.metric("Mean AM score", am_data.get("mean_score","—"))

    # Concordance analysis
    if cv_variants:
        concordant = sum(1 for pos,_ in cv_positions.items() if pos in pos_scores and pos_scores[pos]>=0.564)
        discordant = sum(1 for pos,_ in cv_positions.items() if pos in pos_scores and pos_scores[pos]<0.564)
        if concordant or discordant:
            st.markdown(f"<div style='background:#020d18;border:1px solid #00e5ff33;border-radius:8px;padding:.6rem 1rem;margin-top:.4rem;font-size:.8rem'>"
                        f"<b style='color:#00e5ff'>ClinVar × AlphaMissense concordance:</b> "
                        f"<span style='color:#00c896'>{concordant} concordant</span> (ClinVar P/LP AND AM ≥0.564 = structural mechanism — TSA/chaperone screen) · "
                        f"<span style='color:#ffd60a'>{discordant} discordant</span> (ClinVar P/LP but AM <0.564 = non-structural mechanism — Co-IP/functional assay instead)"
                        f"</div>", unsafe_allow_html=True)
