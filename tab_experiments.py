from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
from styles import section_header, cite_block, metric_card

EXPERIMENTS = {
    "🧬 Functional / Biochemical": [
        {"name":"In vitro Kinase / Enzyme Activity (ADP-Glo™)",
         "purpose":"Directly measure gain or loss of enzymatic activity for variant proteins.",
         "protocol":["Express WT & variant proteins in E. coli or baculovirus system.",
                     "Purify via His-tag affinity + size-exclusion chromatography.",
                     "Run kinase reaction with ADP-Glo™ luminescent system (Promega).",
                     "Compare Km and Vmax: WT vs each prioritised variant.",
                     "Run triplicate; SEM ≤ 10%."],
         "focus":"Variants at catalytic residues — D-loop, activation loop, P-loop.",
         "neglect":"Variants in disordered linkers or regions with pLDDT < 50.",
         "cost":"$$","time":"3–6 weeks",
         "outcome":"Quantitative activity ratio WT vs mutant — direct functional evidence."},

        {"name":"Co-Immunoprecipitation / AP-MS",
         "purpose":"Map protein–protein interaction network changes per variant.",
         "protocol":["Tag protein (3×FLAG or GFP) in HEK293T cells.",
                     "Lyse under native conditions (NP-40 buffer).",
                     "Pull down with anti-tag antibody + Protein A/G beads.",
                     "Run SDS-PAGE or submit to TMT-labelled mass spectrometry.",
                     "Validate top hits by reverse Co-IP."],
         "focus":"Interface residues predicted by AlphaFold-Multimer.",
         "neglect":"Splice variants with identical binding domains.",
         "cost":"$$$","time":"4–8 weeks",
         "outcome":"Interaction network rewiring per mutation."},

        {"name":"Thermal Shift Assay (TSA / DSF)",
         "purpose":"Screen small-molecule binders and assess variant folding stability.",
         "protocol":["Purify WT and variant proteins (0.5 mg/mL).",
                     "96-well plate with SYPRO Orange dye (5×) in buffer.",
                     "Ramp temperature 25→95°C at 1°C/min in qPCR machine.",
                     "Compute Tm via Boltzmann sigmoidal fit.",
                     "Flag ΔTm ≥ 1°C hits for follow-up compound profiling."],
         "focus":"Pathogenic missense variants that destabilise the core fold.",
         "neglect":"IDRs — no Tm signal expected from disordered segments.",
         "cost":"$","time":"1–2 weeks",
         "outcome":"ΔTm per variant; leads for stabilising therapeutic compounds."},
    ],
    "🔬 Cell-Based": [
        {"name":"CRISPR-Cas9 Knock-in",
         "purpose":"Introduce exact patient-like variants into the endogenous locus.",
         "protocol":["Design sgRNAs via CRISPOR flanking variant site.",
                     "Co-transfect sgRNA + SpCas9 RNP + ssODN HDR donor.",
                     "Screen ≥50 colonies by Sanger / NGS.",
                     "Validate by Western blot and immunofluorescence.",
                     "Run phenotypic assays on confirmed clones."],
         "focus":"Variants with ClinVar P/LP + ML score ≥ 0.75.",
         "neglect":"VUS with <2 star review — too uncertain for resource-intensive knock-in.",
         "cost":"$$$","time":"6–12 weeks",
         "outcome":"Isogenic cell lines; gold-standard functional evidence."},

        {"name":"Reporter / Luciferase Assay",
         "purpose":"Quantify transcriptional activity changes driven by TF variants.",
         "protocol":["Clone target promoter (1 kb) into pGL4 luciferase vector.",
                     "Transfect with WT or mutant TF + Renilla control.",
                     "Measure firefly:Renilla ratio at 48 h.",
                     "Run ≥ 3 independent experiments in triplicate."],
         "focus":"Variants in DNA-binding domain or transactivation domain.",
         "neglect":"N-terminal disordered segments not in DNA contact.",
         "cost":"$","time":"1–3 weeks",
         "outcome":"Fold-change in target gene activation / repression."},

        {"name":"Cell Viability / Proliferation (CellTiter-Glo)",
         "purpose":"Assess oncogenic or tumour-suppressive phenotype of variants.",
         "protocol":["Seed 5,000 cells / well in 96-well plates.",
                     "Express WT or variant protein for 72 h.",
                     "Add CellTiter-Glo; read luminescence.",
                     "Normalise to vehicle control; compute IC₅₀ where applicable."],
         "focus":"Gain-of-function oncogenic variants; CRITICAL tier hotspots.",
         "neglect":"Benign / likely benign variants — no wet-lab validation warranted.",
         "cost":"$","time":"1–2 weeks",
         "outcome":"Viability % vs WT; GO/NO-GO for animal models."},
    ],
    "🧫 Structural": [
        {"name":"AlphaFold2 + Rosetta ΔΔG Stability",
         "purpose":"Rank all missense variants by in silico stability before wet lab.",
         "protocol":["Download AF2 PDB from AlphaFold DB.",
                     "Run Rosetta FastRelax on WT.",
                     "Introduce each variant with MutateResidue mover.",
                     "Compute ΔΔG = G(mutant) − G(WT); flag ≥ 2 REU as destabilising.",
                     "Cross-reference with ML scores for orthogonal prioritisation."],
         "focus":"All missense in structured domains (pLDDT ≥ 70).",
         "neglect":"IDR variants (pLDDT < 50) — Rosetta FF unreliable here.",
         "cost":"Free","time":"1–3 days (compute only)",
         "outcome":"Pre-ranked variant list — eliminates ~50% of candidates before any wet lab."},

        {"name":"Surface Plasmon Resonance (SPR / Biacore)",
         "purpose":"Measure binding kinetics WT vs mutant to ligand / drug / partner.",
         "protocol":["Immobilise ligand on CM5 chip via amine coupling.",
                     "Flow analyte at 5 concentrations.",
                     "Fit 1:1 Langmuir model → KD, kon, koff.",
                     "Compare KD shifts across variants."],
         "focus":"Variants predicted to alter binding interface (charge, hydrophobicity change).",
         "neglect":"Variants > 15 Å from binding site in AF2 structure.",
         "cost":"$$$","time":"2–4 weeks",
         "outcome":"Binding affinity shift per variant; structural drug design input."},
    ],
    "🐭 In Vivo / Translational": [
        {"name":"Xenograft Mouse Model",
         "purpose":"Test tumorigenic potential of gain-of-function variants in vivo.",
         "protocol":["Inject 1×10⁶ cells (CRISPR knock-in) SC into NSG mice.",
                     "Monitor tumour volume twice weekly (caliper).",
                     "At endpoint harvest and perform H&E + IHC.",
                     "Compare WT vs mutant growth curves (log-rank test)."],
         "focus":"Variants with in vitro proliferation data already supporting oncogenicity.",
         "neglect":"VUS without prior in vitro validation — too costly.",
         "cost":"$$$$","time":"8–16 weeks",
         "outcome":"In vivo tumour growth curves; histological characterisation."},
    ],
    "💊 Therapeutic": [
        {"name":"Small Molecule HTS",
         "purpose":"Identify compounds that rescue or inhibit mutant protein function.",
         "protocol":["Establish HTS-compatible biochemical or cell-based assay.",
                     "Screen compound library at 10 µM (10K–1M compounds).",
                     "Counter-screen for cytotoxicity.",
                     "Confirm dose-response (IC₅₀) for top 50 hits.",
                     "Advance top 5 for SAR."],
         "focus":"CRITICAL/HIGH variants with druggable pockets.",
         "neglect":"IDPs or nuclear lamins without well-defined binding pockets.",
         "cost":"$$$$","time":"6–12 months",
         "outcome":"Lead compound series for medicinal chemistry."},

        {"name":"PROTAC / Targeted Protein Degradation",
         "purpose":"Degrade undruggable gain-of-function mutant proteins.",
         "protocol":["Design PROTAC: warhead (target ligand) + E3-recruiter (CRBN/VHL).",
                     "Synthesise 10–20 candidates.",
                     "Assess DC₅₀ in target cell line.",
                     "Quantify degradation by WB / mass spec.",
                     "Check selectivity by proteome-wide TMT-MS."],
         "focus":"Gain-of-function mutations resistant to catalytic inhibition.",
         "neglect":"Tumour suppressor loss-of-function — degradation worsens phenotype.",
         "cost":"$$$$","time":"6–12 months",
         "outcome":"Selective degrader DC₅₀ < 100 nM."},
    ],
}

COST_MAP = {
    "Free":  ("#00c896","rgba(0,200,150,0.1)"),
    "$":     ("#4a90d9","rgba(74,144,217,0.1)"),
    "$$":    ("#ffd60a","rgba(255,214,10,0.1)"),
    "$$$":   ("#ff8c42","rgba(255,140,66,0.1)"),
    "$$$$":  ("#ff2d55","rgba(255,45,85,0.1)"),
    "$$$$$": ("#a855f7","rgba(168,85,247,0.1)"),
}

def render(pdata, cv, scored, assay_text, papers, gene_name):
    section_header("🧪","Further Experimentation & Therapy")

    _scorecard(pdata, scored)
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    if assay_text and assay_text.strip():
        _assay_guidance(assay_text)
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    _cost_legend()
    for cat, exps in EXPERIMENTS.items():
        st.markdown(f"### {cat}")
        for exp in exps:
            _exp_card(exp, scored)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    _decision_funnel(scored)

    if papers:
        st.markdown(cite_block(papers, 6), unsafe_allow_html=True)


def _scorecard(pdata, scored):
    kws      = [k.get("value","").lower() for k in pdata.get("keywords",[])]
    ptype    = ("kinase" if any("kinase" in k for k in kws) else
                "gpcr"  if any("gpcr" in k or "g protein" in k for k in kws) else
                "transcription_factor" if any("transcription" in k for k in kws) else "general")
    drugg    = {"kinase":0.90,"gpcr":0.95,"transcription_factor":0.35,"general":0.50}.get(ptype,0.5)
    n_crit   = sum(1 for v in scored if v.get("ml_rank")=="CRITICAL")
    n_high   = sum(1 for v in scored if v.get("ml_rank")=="HIGH")
    priority = min(100, n_crit*15 + n_high*8 + len(scored)*0.5 + drugg*20)

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(metric_card(n_crit,"CRITICAL Variants","#ff2d55","linear-gradient(90deg,#ff2d55,#ff6b8a)"), unsafe_allow_html=True)
    with c2: st.markdown(metric_card(n_high,"HIGH Variants","#ff8c42","linear-gradient(90deg,#ff8c42,#ffb380)"), unsafe_allow_html=True)
    with c3: st.markdown(metric_card(f"{drugg:.0%}","Druggability Est.","#00c896"), unsafe_allow_html=True)
    with c4: st.markdown(metric_card(int(priority),"Priority Score / 100","#00e5ff"), unsafe_allow_html=True)

    if priority >= 70:
        msg = "⚡ High experimental priority. Multiple pathogenic variants confirmed. Recommend immediate CRISPR knock-in + biochemical validation, followed by in vivo studies if phenotype confirmed."
        clr = "#ff2d55"
    elif priority >= 40:
        msg = "🟡 Moderate priority. Some pathogenic evidence. Start with in silico stability (Rosetta ΔΔG) and low-cost cell assays before committing to animal experiments."
        clr = "#ffd60a"
    else:
        msg = "🟢 Low current priority. Insufficient pathogenic evidence. Monitor ClinVar reclassifications. Do not commit wet-lab resources at this stage."
        clr = "#00c896"

    st.markdown(
        f"<div style='background:#06101e;border-left:3px solid {clr};border-radius:0 10px 10px 0;"
        f"padding:1rem 1.4rem;margin-top:0.8rem;'><p style='color:#8ab0d0;margin:0;font-size:0.9rem;'>{msg}</p></div>",
        unsafe_allow_html=True)


def _assay_guidance(text):
    section_header("🧫","Assay-Specific Next Steps")
    tl  = text.lower()
    recs = []
    if any(k in tl for k in ["western","wb","blot","expression"]):
        recs.append(("Western Blot → Follow Up",
                     "Quantify in ≥2 cell lines. If expression change detected: ubiquitination assay + cycloheximide chase (protein half-life). Validate with SILAC or TMT-MS proteomics."))
    if any(k in tl for k in ["crispr","knockout","ko"]):
        recs.append(("CRISPR KO → Follow Up",
                     "Rescue experiment: re-introduce WT and each variant to confirm specificity. RNA-seq on KO vs WT. If oncogene: assess xenograft tumour burden."))
    if any(k in tl for k in ["flow","facs","cytometry"]):
        recs.append(("Flow Cytometry → Follow Up",
                     "Apoptosis: WB for caspase 3/7 + Bcl-2 family. Cell cycle arrest: add CDK inhibitor comparison. Consider scRNA-seq to resolve heterogeneous populations."))
    if any(k in tl for k in ["binding","co-ip","pulldown","interaction"]):
        recs.append(("Interaction Data → Follow Up",
                     "Map interface by HDX-MS or crosslinking MS. Target for cryo-EM structure. Design peptide/small-molecule disruptors of the identified interface."))
    if not recs:
        recs.append(("General → Next Steps",
                     "Characterise dose–response. Validate in ≥2 independent cell lines. Integrate with ClinVar variant triage for mechanistic hypotheses."))
    for title, body in recs:
        st.markdown(f"<div class='card'><h4>{title}</h4><p>{body}</p></div>", unsafe_allow_html=True)


def _cost_legend():
    st.markdown("<div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:1rem;'>", unsafe_allow_html=True)
    labels = [("Free","No direct cost"),("$","<$1K"),("$$","$1K–10K"),("$$$","$10K–50K"),("$$$$","$50K–200K"),("$$$$$",">$200K")]
    cols = st.columns(len(labels))
    for (sym, lbl), col in zip(labels, cols):
        clr, bg = COST_MAP.get(sym,("#4a7fa5","rgba(74,127,165,0.1)"))
        col.markdown(
            f"<div style='background:{bg};border:1px solid {clr}44;border-radius:8px;"
            f"padding:6px;text-align:center;'>"
            f"<div style='color:{clr};font-weight:800;font-size:1rem;'>{sym}</div>"
            f"<div style='color:{clr}99;font-size:0.7rem;'>{lbl}</div></div>",
            unsafe_allow_html=True)


def _exp_card(exp, scored):
    clr, bg = COST_MAP.get(exp["cost"],("#4a7fa5","rgba(0,0,0,0)"))
    with st.expander(f"{exp['name']}  ·  {exp['cost']}  ·  ⏱ {exp['time']}"):
        c1, c2 = st.columns([3,2])
        with c1:
            st.markdown(f"**Purpose:** {exp['purpose']}")
            st.markdown("**Protocol steps:**")
            for i,step in enumerate(exp["protocol"],1):
                st.markdown(f"{i}. {step}")
            st.markdown(f"**Expected outcome:** {exp['outcome']}")
        with c2:
            st.markdown(
                f"<div style='background:{bg};border:1px solid {clr}44;border-radius:10px;padding:1rem;'>"
                f"<div style='color:{clr};font-weight:800;font-size:1.1rem;'>{exp['cost']}</div>"
                f"<div style='color:{clr}88;font-size:0.8rem;margin-bottom:10px;'>⏱ {exp['time']}</div>"
                f"<div style='color:#00c896;font-size:0.8rem;font-weight:700;margin-bottom:3px;'>✅ Focus on:</div>"
                f"<div style='color:#3a7060;font-size:0.78rem;margin-bottom:10px;'>{exp['focus']}</div>"
                f"<div style='color:#ff8c42;font-size:0.8rem;font-weight:700;margin-bottom:3px;'>❌ Deprioritise:</div>"
                f"<div style='color:#7a4020;font-size:0.78rem;'>{exp['neglect']}</div>"
                f"</div>",
                unsafe_allow_html=True)


def _decision_funnel(scored):
    section_header("🗺️","Experimental Decision Framework")
    rc = {"CRITICAL":"#ff2d55","HIGH":"#ff8c42","MEDIUM":"#ffd60a","NEUTRAL":"#3a5a7a"}
    counts = {r: sum(1 for v in scored if v.get("ml_rank")==r) for r in rc}
    labels, values, colours = zip(*[(r,counts[r],c) for r,c in rc.items() if counts[r]>0]) if any(counts.values()) else ([],[],[])

    if labels:
        fig = go.Figure(go.Funnel(
            y=list(labels), x=list(values),
            textinfo="value+percent initial",
            marker=dict(color=list(colours)),
            textfont=dict(color="white",size=13),
        ))
        fig.update_layout(
            paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#4a7fa5",
            height=300,margin=dict(t=10,b=10,l=80,r=10),
            title=dict(text="Variant Triage Funnel",font_color="#00e5ff",font_size=13),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    decisions = [
        ("CRITICAL","#ff2d55","Immediate functional validation. CRISPR knock-in + biochemical assay now. In vivo if in vitro phenotype confirmed."),
        ("HIGH","#ff8c42","Functional assay + Rosetta ΔΔG. Proceed to in vivo only after clear in vitro phenotype."),
        ("MEDIUM","#ffd60a","In silico stability + low-cost cell assay (reporter / viability). Hold before any animal work."),
        ("NEUTRAL","#3a5a7a","Deprioritise. Monitor future ClinVar reclassifications. No wet-lab spend recommended."),
    ]
    for rank, clr, rec in decisions:
        st.markdown(
            f"<div style='display:flex;gap:12px;align-items:flex-start;background:#06101e;"
            f"border-left:3px solid {clr};border-radius:0 8px 8px 0;padding:10px 14px;margin:5px 0;'>"
            f"<span style='background:rgba(0,0,0,0.3);color:{clr};padding:2px 10px;border-radius:12px;"
            f"font-size:0.7rem;font-weight:800;white-space:nowrap;margin-top:1px;'>{rank}</span>"
            f"<span style='color:#7aa0c0;font-size:0.87rem;'>{rec}</span>"
            f"</div>",
            unsafe_allow_html=True)
