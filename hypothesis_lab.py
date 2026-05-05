"""hypothesis_lab.py — Tab 4: Therapy & Treatment"""
import streamlit as st
import re
from diagrams import GPCR_ASSOC
try:
    from protein_data import get_protein_info
except ImportError:
    def get_protein_info(gene):
        return {"real_biology":"","gpcr_interaction":{},"experiments_specific":[],"timeline_stages":[],"piggyback_relationship":{}}

DRUG_DB = {
    "FLNA": {"strategy":"Gene/mRNA therapy justified by 847 ClinVar pathogenic variants (DBR 0.320, CRITICAL).","approved":[],"investigational":[{"name":"AAV-FLNA gene therapy","stage":"Preclinical","mechanism":"Replace loss-of-function allele in neurons/smooth muscle","evidence":"X-linked disease models"},{"name":"mRNA replacement therapy","stage":"Preclinical","mechanism":"Restore FLNA in deficient tissues","evidence":"Proof of concept in other X-linked conditions"}],"warning":False},
    "FLNC": {"strategy":"Cardiac gene therapy justified by DBR 1.39 — most constrained cardiac protein known.","approved":[],"investigational":[{"name":"AAV9-FLNC (cardiac-specific)","stage":"Phase I planning","mechanism":"Restore FLNC in cardiomyocytes","evidence":"FLNC KO cardiomyopathy mouse models"},{"name":"siRNA for aggregate-forming variants","stage":"Preclinical","mechanism":"Reduce toxic GOF aggregation","evidence":"Myofibrillar myopathy variants"}],"warning":False},
    "CHRM2": {"strategy":"102 dominant pathogenic variants — standard HF therapy manages symptoms. CHRM2-specific approaches unexplored.","approved":[{"name":"Standard heart failure pharmacotherapy","stage":"Approved","mechanism":"ACE inhibitors, beta-blockers, diuretics manage DCM consequences","evidence":"Major HF trials"}],"investigational":[{"name":"CHRM2-selective modulator","stage":"Research","mechanism":"Correct constitutively signalling dominant variants","evidence":"102 ClinVar pathogenic variants confirm target validity"}],"warning":False},
    "CHRM3": {"strategy":"Confirmed Prune belly syndrome gene. Orphan drug pathway. 8 ClinVar pathogenic variants.","approved":[{"name":"Surgical management (PBS)","stage":"Standard care","mechanism":"Urological reconstruction for bladder malformation","evidence":"PBS clinical guidelines"}],"investigational":[{"name":"CHRM3 agonist (LOF variants)","stage":"Research","mechanism":"Compensate for bladder smooth muscle dysfunction","evidence":"8 ClinVar pathogenic variants including frameshift p.Pro392AlafsTer43"}],"warning":False},
    "ARRB1": {"strategy":"DO NOT PURSUE as drug target. Zero germline pathogenic variants. β-arrestin trap risk.","approved":[],"investigational":[],"warning":True},
    "ARRB2": {"strategy":"DO NOT PURSUE as drug target. Zero germline pathogenic variants. Same as β-arrestin 1.","approved":[],"investigational":[],"warning":True},
    "TALN1": {"strategy":"Zero germline pathogenic variants. Mouse KO lethal but human variants tolerated. Do not pursue without genetic validation.","approved":[],"investigational":[],"warning":True},
}

PAPERS = {"king":"King et al., Nature 2024","minikel":"Minikel et al., Nature 2021","plenge":"Plenge et al., Nat Rev Drug Discov 2016","cook":"Cook et al., Nat Rev Drug Discov 2014"}
URLS   = {"king":"https://www.nature.com/articles/s41586-024-07316-0","minikel":"https://www.nature.com/articles/s41586-020-2267-z","plenge":"https://www.nature.com/articles/nrd.2016.29","cook":"https://www.nature.com/articles/nrd4309"}

def chip(key):
    return f'<a href="{URLS[key]}" target="_blank" style="background:#0a0c1a;border:1px solid #1e2030;color:#4CA8FF;font-family:IBM Plex Mono,monospace;font-size:0.63rem;padding:2px 9px;border-radius:10px;text-decoration:none;margin:2px;display:inline-block">📄 {PAPERS[key]}</a>'

def render():
    if "prot_data" not in st.session_state:
        st.info("👈 Enter a protein in the sidebar and click Analyse.")
        return

    pd_s    = st.session_state.prot_data
    gt      = st.session_state.get("gt",{})
    cv      = st.session_state.get("cv",{})
    scored  = st.session_state.get("scored")
    ctx     = st.session_state.get("ctx",{})
    gene    = st.session_state.get("gene","")
    n_path  = gt.get("n_path",0)
    tier    = gt.get("tier","UNKNOWN")
    dbr     = gt.get("dbr")
    tc      = {"CRITICAL":"#FF4C4C","HIGH":"#FFA500","LOW":"#FFD700","NONE":"#888","UNKNOWN":"#4CA8FF"}.get(tier,"#888")
    prot    = pd_s.get("protein_name","") or gene
    goal    = ctx.get("study_goal","")
    dis_ctx = ctx.get("disease_context","")
    is_gpcr = pd_s.get("is_gpcr",False)
    g_prot  = pd_s.get("g_protein","")
    domains = pd_s.get("domains",[])
    subcel  = pd_s.get("subcellular",[])
    assoc   = GPCR_ASSOC.get(gene.upper(),{})

    # Ground truth n_path
    GT_N = {"FLNA":847,"FLNB":412,"FLNC":3800,"CHRM2":102,"CHRM3":8,"ARRB1":0,"ARRB2":0,"TALN1":0}
    if gene.upper() in GT_N and n_path==0:
        n_path = GT_N[gene.upper()]

    drug = DRUG_DB.get(gene.upper())

    st.markdown(f'<h2 style="font-family:IBM Plex Mono,monospace;font-size:1.3rem;color:#eee;margin-bottom:4px">{gene} — Therapy, Treatment & Next Steps</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:#555;font-size:0.8rem;margin-bottom:16px">{n_path} ClinVar germline pathogenic variants · DBR {f"{dbr:.3f}" if dbr else "—"} · {tier} · Goal: {goal or "not specified"}</p>', unsafe_allow_html=True)

    if drug and drug.get("warning"):
        st.markdown(f"""<div style="background:#14060a;border:2px solid #FF4C4C;border-radius:12px;padding:20px 24px;margin-bottom:16px">
          <div style="font-family:IBM Plex Mono,monospace;font-size:0.85rem;font-weight:700;color:#FF4C4C;margin-bottom:8px">⚠ DO NOT PURSUE AS PRIMARY DRUG TARGET</div>
          <p style="font-size:0.83rem;color:#aaa;line-height:1.7;margin-bottom:10px">{drug['strategy']}</p>
          <div>{chip('minikel')} {chip('plenge')} {chip('cook')}</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("""<div style="background:#0a0c16;border:1px solid #1a1d2e;border-radius:10px;padding:16px 20px">
          <div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:10px">What to do instead</div>
          <p style="font-size:0.83rem;color:#888;line-height:1.7">Study the interaction partners that carry real disease burden. For arrestins: study Filamin A (847 pathogenic variants) and the GPCRs themselves. For Talin: study the integrins with confirmed ClinVar burden (ITB3, ITGA2B). The piggyback has no independent disease evidence.</p>
        </div>""", unsafe_allow_html=True)
        return

    t1,t2,t3,t4 = st.tabs(["💊 Drug & Strategy","🎯 Druggable Spots","📈 Mutation Progression","🧪 Experiments"])

    with t1:
        c1,c2 = st.columns([1,1],gap="medium")
        with c1:
            if drug:
                st.markdown(f"""<div style="background:#070a07;border:1px solid #4CAF5055;border-radius:10px;padding:16px 18px;margin-bottom:12px">
                  <div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:#4CAF50;margin-bottom:8px">Overall strategy</div>
                  <p style="font-size:0.83rem;color:#bbb;line-height:1.7">{drug['strategy']}</p>
                  <div style="margin-top:8px">{chip('king')}</div>
                </div>""", unsafe_allow_html=True)
                if drug.get("approved"):
                    st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.15em;color:#4CAF50;margin-bottom:6px">Approved therapies</div>', unsafe_allow_html=True)
                    for d in drug["approved"]:
                        st.markdown(f"""<div style="background:#0a0c16;border:1px solid #4CAF5033;border-radius:8px;padding:12px 14px;margin-bottom:6px">
                          <div style="display:flex;justify-content:space-between;margin-bottom:4px"><span style="font-weight:600;color:#eee;font-size:0.83rem">{d['name']}</span><span style="background:#4CAF5022;color:#4CAF50;font-family:IBM Plex Mono,monospace;font-size:0.62rem;padding:2px 8px;border-radius:8px">{d['stage']}</span></div>
                          <div style="font-size:0.78rem;color:#888;margin-bottom:3px"><strong>Mechanism:</strong> {d['mechanism']}</div>
                          <div style="font-size:0.73rem;color:#555"><strong>Evidence:</strong> {d['evidence']}</div>
                        </div>""", unsafe_allow_html=True)
                if drug.get("investigational"):
                    st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.15em;color:#FFA500;margin-bottom:6px;margin-top:10px">Investigational</div>', unsafe_allow_html=True)
                    for d in drug["investigational"]:
                        st.markdown(f"""<div style="background:#0a0c16;border:1px solid #FFA50033;border-radius:8px;padding:12px 14px;margin-bottom:6px">
                          <div style="display:flex;justify-content:space-between;margin-bottom:4px"><span style="font-weight:600;color:#eee;font-size:0.83rem">{d['name']}</span><span style="background:#FFA50022;color:#FFA500;font-family:IBM Plex Mono,monospace;font-size:0.62rem;padding:2px 8px;border-radius:8px">{d['stage']}</span></div>
                          <div style="font-size:0.78rem;color:#888;margin-bottom:3px"><strong>Mechanism:</strong> {d['mechanism']}</div>
                          <div style="font-size:0.73rem;color:#555"><strong>Evidence:</strong> {d['evidence']}</div>
                        </div>""", unsafe_allow_html=True)
            else:
                dbr_val = dbr or 0
                if n_path > 0:
                    if dbr_val > 0.5: strat="Strong genetic support justifies drug development. Proceed with target validation."
                    elif dbr_val > 0.1: strat="Solid genetic support. Validate mechanism before drug chemistry."
                    else: strat="Rare disease gene. Orphan drug pathway and gene therapy appropriate."
                else:
                    strat="Zero germline pathogenic variants. Validate genomic relevance before any therapeutic investment."
                st.markdown(f"""<div style="background:#070a07;border:1px solid #4CAF5055;border-radius:10px;padding:16px 18px">
                  <p style="font-size:0.83rem;color:#bbb;line-height:1.7">{strat}</p>
                  <div style="margin-top:8px">{chip('king')}{chip('cook')}</div>
                </div>""", unsafe_allow_html=True)

        with c2:
            st.markdown(f"""<div style="background:#0a0c16;border:1px solid #1a1d2e;border-radius:10px;padding:16px 18px">
              <div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:10px">The genomic validation — why this matters</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px">
                <div style="background:#07080f;border:1px solid #12141e;border-radius:6px;padding:10px;text-align:center"><span style="font-size:1.5rem;font-weight:700;font-family:IBM Plex Mono,monospace;color:{tc}">{n_path}</span><div style="font-size:0.62rem;color:#333;text-transform:uppercase;margin-top:2px">Germline pathogenic</div></div>
                <div style="background:#07080f;border:1px solid #12141e;border-radius:6px;padding:10px;text-align:center"><span style="font-size:1.5rem;font-weight:700;font-family:IBM Plex Mono,monospace;color:{tc}">{f"{dbr:.3f}" if dbr else "—"}</span><div style="font-size:0.62rem;color:#333;text-transform:uppercase;margin-top:2px">DBR</div></div>
              </div>
              <p style="font-size:0.78rem;color:#888;line-height:1.7">Drugs with genetic support are 2.6× more likely to succeed in clinical trials. {n_path} confirmed pathogenic variants provide the genetic foundation for this target.</p>
              <div style="margin-top:8px">{chip('king')}{chip('minikel')}</div>
            </div>""", unsafe_allow_html=True)

            # Wet lab HIGH hits
            if scored is not None:
                pc_col="priority_final" if "priority_final" in scored.columns else "priority"
                high_hits=scored[scored[pc_col]=="HIGH"].head(5)
                if len(high_hits)>0:
                    st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.15em;color:#FF4C4C;margin-bottom:6px;margin-top:12px">TOP HIGH PRIORITY HITS (your assay)</div>', unsafe_allow_html=True)
                    for _,row in high_hits.iterrows():
                        pos=int(row["residue_position"]); score=round(float(row["normalized_score"]),3)
                        mut=str(row.get("mutation",f"Pos{pos}")); mut=f"Pos{pos}" if mut in ("nan","") else mut
                        st.markdown(f'<div style="padding:5px 10px;margin-bottom:3px;background:#0a0607;border:1px solid #FF4C4C33;border-radius:5px;font-size:0.78rem;display:flex;justify-content:space-between"><span style="color:#eee;font-family:IBM Plex Mono,monospace">{mut}</span><span style="color:#FF4C4C;font-family:IBM Plex Mono,monospace">{score}</span></div>', unsafe_allow_html=True)

    with t2:
        st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:12px">Druggable spots — domain analysis + ClinVar hotspot clustering</div>', unsafe_allow_html=True)
        if domains:
            for i,d in enumerate(domains[:8]):
                dc=["#9370DB","#4CA8FF","#FFA500","#4CAF50","#FF6B9D","#00BCD4","#FF4C4C","#FFD700"][i%8]
                n_cv_in_domain=0
                for v in (cv.get("pathogenic",[])+cv.get("likely_pathogenic",[])):
                    pos=v.get("pos",0)
                    if d.get("start",0)<=pos<=d.get("end",0): n_cv_in_domain+=1
                druggable = n_cv_in_domain >= 3 or any(kw in d.get("name","").lower() for kw in ("bind","active","catalyt","atp","zinc","pocket","cleft","dna"))
                dg_badge=f'<span style="background:#4CAF5022;color:#4CAF50;font-size:0.63rem;font-family:IBM Plex Mono,monospace;padding:2px 8px;border-radius:8px;margin-left:8px">DRUGGABLE</span>' if druggable else ""
                st.markdown(f"""<div style="background:#0a0c16;border:1px solid {dc}44;border-radius:8px;padding:12px 14px;margin-bottom:8px">
                  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">
                    <div><span style="font-weight:600;color:{dc};font-family:IBM Plex Mono,monospace;font-size:0.82rem">{d.get('name','')[:40]}</span>{dg_badge}</div>
                    <span style="font-size:0.7rem;color:#444;font-family:IBM Plex Mono,monospace">{d.get('start',0)}–{d.get('end',0)}</span>
                  </div>
                  <div style="font-size:0.75rem;color:#555">ClinVar pathogenic variants in this domain: <span style="color:{'#FF4C4C' if n_cv_in_domain>0 else '#444'};font-weight:600">{n_cv_in_domain}</span></div>
                  {'<div style="font-size:0.72rem;color:#888;margin-top:3px">High variant density + known functional importance → prioritise for structure-based drug design</div>' if druggable else ''}
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="background:#0a0c16;border:1px solid #1a1d2e;border-radius:8px;padding:16px;font-size:0.82rem;color:#555">Domain data not loaded. Enable DB enrichment to identify druggable domains for {gene}.</div>', unsafe_allow_html=True)

        if assoc:
            gc=assoc.get("color","#9370DB")
            st.markdown(f"""<div style="background:#100a18;border:1px solid {gc}44;border-radius:8px;padding:14px;margin-top:8px">
              <div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;color:{gc};margin-bottom:6px">GPCR interaction interface — therapeutic opportunity</div>
              <p style="font-size:0.8rem;color:#aaa;line-height:1.7">The {assoc['type']} interaction creates a druggable interface. Disrupting the interaction of {gene} with {', '.join(assoc.get('partners',['—'])[:3])} could be therapeutic if pathogenic variants cluster at this interface.</p>
              <div style="font-size:0.7rem;color:#444;margin-top:6px">📄 {assoc.get('paper','')}</div>
            </div>""", unsafe_allow_html=True)

    with t3:
        pdata_t3 = get_protein_info(gene)
        timeline_stages = pdata_t3.get("timeline_stages", [])
        if timeline_stages:
            st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:#5a5d7a;margin-bottom:10px">Mutation progression timeline — move slider to see each stage</div>', unsafe_allow_html=True)
            max_s = max(1, len(timeline_stages)-1)
            sel_s = st.slider("Stage", 0, max_s, 0, key="tl_s")
            stg = timeline_stages[sel_s]
            stg_name, stg_desc = stg[1], stg[2]
            pct = int(sel_s/max_s*100) if max_s > 0 else 0
            bc = "#4CAF50" if pct==0 else "#FFA500" if pct<50 else "#FF8C00" if pct<80 else "#FF4C4C"
            # Stage display
            st.markdown(f'<div style="background:#0d1020;border:1px solid {bc}55;border-radius:10px;padding:14px 18px;margin-bottom:12px"><div style="background:#12141e;border-radius:3px;height:6px;overflow:hidden;margin-bottom:10px"><div style="width:{pct}%;height:100%;background:{bc};border-radius:3px"></div></div><div style="font-weight:700;color:{bc};font-family:IBM Plex Mono,monospace;font-size:0.88rem;margin-bottom:6px">{stg_name}</div><p style="font-size:0.82rem;color:#cccccc;line-height:1.8;margin:0">{stg_desc}</p></div>', unsafe_allow_html=True)
            # Roadmap pills
            pills = " ".join(f'<span style="background:{""+bc+"22" if i==sel_s else "#0d1020"};border:1px solid {""+bc if i==sel_s else "#252840"};border-radius:6px;padding:4px 10px;font-family:IBM Plex Mono,monospace;font-size:0.62rem;color:{""+bc if i==sel_s else "#666"};display:inline-block;margin:2px">{i+1}. {s[1][:16]}</span>' for i,s in enumerate(timeline_stages))
            st.markdown(pills, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:#5a5d7a;margin-bottom:12px">Mechanistic progression — how to stop it</div>', unsafe_allow_html=True)
        goal_lower=(goal+" "+dis_ctx).lower()

        PROGRESSION = {
            "FLNA": [("Germline FLNA variant inherited","The pathogenic variant is present in every cell from conception. Penetrance depends on variant type and sex (X-linked).","#FF4C4C"),("FLNA scaffold function disrupted","Specific GPCR docking is lost. The intracellular signalling hub for that tissue is disorganised.","#FF8C00"),("Tissue-specific manifestation","Brain: neurons migrate to wrong locations → periventricular heterotopia. Heart: valvular dysplasia. Vasculature: aortic wall weakness → aneurysm.","#FFA500"),("Secondary consequences","Epilepsy (from heterotopia). Intellectual disability (GPCR signalling disrupted in developing brain). Cardiac failure.","#FFD700"),("Intervention point","Gene therapy (AAV-FLNA) or mRNA replacement BEFORE symptom onset. Prenatal diagnosis via sequencing enables early planning.","#4CAF50")],
            "FLNC": [("Pathogenic FLNC variant in cardiomyocyte","Loss of Filamin C disrupts sarcomere anchoring of GPCR signals.","#FF4C4C"),("Sarcomere-GPCR coupling broken","Cardiac receptors (CHRM2, ADRB1) cannot properly transduce signals to myofilaments.","#FF8C00"),("Progressive cardiomyopathy","Either arrhythmogenic: abnormal electrical conduction → sudden cardiac death risk. Or dilated: progressive wall thinning → pump failure.","#FFA500"),("End-stage heart disease","Without intervention: heart failure, arrhythmia, transplantation required.","#FFD700"),("Intervention points","Early: genetic screening + ICD implantation. Future: AAV9-FLNC cardiac gene therapy before irreversible remodelling.","#4CAF50")],
            "CHRM2": [("Dominant CHRM2 variant expressed","Dominant variant in 50% of CHRM2 copies. Either constitutively active or dominant negative.","#FF4C4C"),("Gi/o signalling dysregulation","Abnormal cAMP levels in cardiomyocytes. PKA imbalance. GIRK channel dysfunction.","#FF8C00"),("Dilated cardiomyopathy progression","Ventricular wall dilation, reduced contractility. Progressive over years to decades.","#FFA500"),("Heart failure","If untreated: pump failure, arrhythmia, need for transplantation.","#FFD700"),("Intervention","Standard HF therapy (ACE-I, beta-blockers) manages symptoms. CHRM2-specific molecular therapy is the research frontier.","#4CAF50")],
            "CHRM3": [("CHRM3 frameshift in bladder smooth muscle","p.Pro392AlafsTer43: loss of 3rd intracellular loop, Gq/11 coupling abolished.","#FF4C4C"),("Bladder smooth muscle fails to contract","Gq/11 → PLCβ → Ca²⁺ → contraction pathway broken. Bladder wall cannot generate force.","#FF8C00"),("Prune belly syndrome at birth","Absent bladder musculature, urinary tract malformation, abdominal wall defects.","#FFA500"),("Secondary complications","Urinary tract infection, renal impairment, respiratory compromise.","#FFD700"),("Intervention","Surgical reconstruction. Future: in utero CHRM3 gene correction. CHRM3 agonist for residual receptor function.","#4CAF50")],
        }

        steps = PROGRESSION.get(gene.upper(),[])
        if not steps:
            # Generic progression
            if n_path>0:
                steps=[
                    ("Pathogenic variant inherited/acquired",f"{n_path} confirmed pathogenic variants for {gene}. Variant disrupts protein structure or function.","#FF4C4C"),
                    ("Molecular dysfunction",f"Loss or gain of {gene} function in affected tissue.","#FFA500"),
                    ("Disease manifestation",gt.get("diseases","Clinical disease as per ClinVar associations"),"#FFD700"),
                    ("Intervention point",f"Target {gene} with {'gene therapy (strong genetic justification)' if dbr and dbr>0.5 else 'mechanism-appropriate therapy'} before irreversible tissue damage.","#4CAF50"),
                ]
            else:
                steps=[("No confirmed disease progression","Zero germline pathogenic variants for "+gene+" — no confirmed human disease path documented in ClinVar.","#888"),("Study interaction partners instead","Check proteins that interact with "+gene+" for confirmed ClinVar burden.","#4CA8FF")]

        for i,(title,body,color) in enumerate(steps,1):
            st.markdown(f"""<div style="display:flex;gap:14px;margin-bottom:14px;align-items:flex-start">
              <div style="min-width:32px;height:32px;border-radius:50%;background:{color}22;color:{color};border:2px solid {color}55;display:flex;align-items:center;justify-content:center;font-family:IBM Plex Mono,monospace;font-size:0.75rem;font-weight:700;flex-shrink:0">{i}</div>
              <div style="flex:1;background:#0a0c16;border-left:3px solid {color}55;border-radius:0 8px 8px 0;padding:12px 14px">
                <div style="font-weight:600;color:#eee;font-size:0.85rem;margin-bottom:4px">{title}</div>
                <div style="font-size:0.8rem;color:#888;line-height:1.6">{body}</div>
              </div>
            </div>""", unsafe_allow_html=True)

    with t4:
        pdata_exp = get_protein_info(gene)
        specific_exps = pdata_exp.get("experiments_specific", [])
        note_txt = f"Experiments below are specific to {gene} — different proteins need different validation strategies."
        st.markdown(f'<div style="background:#0d1020;border:1px solid #252840;border-radius:8px;padding:10px 14px;margin-bottom:14px;font-size:0.79rem;color:#aaaaaa">{note_txt}</div>', unsafe_allow_html=True)
        if specific_exps:
            st.markdown(f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:#5a5d7a;margin-bottom:10px">Protein-specific experiments for {gene}</div>', unsafe_allow_html=True)
            lc_map = {1:"#4CAF50",2:"#FFA500",3:"#FF8C00",4:"#FF4C4C",5:"#FF0000"}
            for exp in specific_exps:
                lc = lc_map.get(exp.get("level",2),"#888")
                with st.expander(f"Level {exp.get('level','?')} — {exp['name']}"):
                    st.markdown(f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;color:{lc};margin-bottom:6px">Why this experiment for {gene} specifically</div>', unsafe_allow_html=True)
                    st.markdown(f'<p style="font-size:0.82rem;color:#cccccc;line-height:1.7;margin-bottom:8px">{exp.get("rationale","")}</p>', unsafe_allow_html=True)
                    if exp.get("protocol"):
                        st.code(exp["protocol"], language="text")
                    why_not = exp.get("why_this_not_dsf","")
                    if why_not:
                        st.markdown(f'<div style="font-size:0.73rem;color:#777;font-style:italic">Note: {why_not}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.12em;color:#5a5d7a;margin-bottom:8px">Universal validation hierarchy</div>', unsafe_allow_html=True)
        exps = [
            {"level":1,"name":"ClinVar + gnomAD database check","time":"<1 hour","cost":"Free","color":"#4CAF50","desc":f"Query ClinVar for all pathogenic variants in {gene}. Check gnomAD pLI score (>0.9 = highly constrained). Confirm DBR. This is the first step before any wet lab work.","validates":"Whether {gene} is worth pursuing at all","paper":chip("king")},
            {"level":2,"name":"OpenTargets target-disease association","time":"30 min","cost":"Free","color":"#4CAF50","desc":f"Search {gene} at platform.opentargets.org. Note genetic association score and ClinVar column weight. Compare to β-adrenergic receptors and arrestins to see the contrast.","validates":"Multi-disease relevance and comparison to known dispensable proteins","paper":""},
            {"level":3,"name":"Thermal shift assay (DSF)","time":"2–3 days","cost":"~$300","color":"#FFA500","desc":f"Express WT and top pathogenic {gene} variants. Run DSF with SYPRO Orange (25→95°C at 1°C/min). Expect ΔTm of 3–15°C for pathogenic variants vs WT.","validates":"Structural disruption — confirms the variant actually destabilises the protein","paper":chip("king")},
            {"level":4,"name":"ITC (Isothermal Titration Calorimetry)","time":"1–2 weeks","cost":"~$2,000","color":"#FF8C00","desc":f"Gold standard binding thermodynamics. Gives Kd, ΔH, ΔS, stoichiometry simultaneously. No fluorescent artefacts. Recommended by Sujay Ithychanda (Cleveland Clinic) as the most robust assay. Measure {gene} binding to key interaction partner.","validates":"Direct binding disruption — no false positives, quantitative","paper":""},
            {"level":5,"name":"Patient-derived cell validation","time":"1–3 months","cost":"~$5,000+","color":"#FF4C4C","desc":f"Obtain fibroblasts or iPSCs from confirmed {gene} variant carriers. Differentiate to relevant cell type. Measure native protein function. This is human evidence — more relevant than mouse models.","validates":"Human-relevant functional consequence. Required before any clinical claim.","paper":chip("minikel")},
        ]
        for exp in exps:
            with st.expander(f"Level {exp['level']} — {exp['name']} · {exp['time']} · {exp['cost']}"):
                st.markdown(f'<p style="font-size:0.82rem;color:#aaa;line-height:1.7;margin-bottom:6px">{exp["desc"]}</p>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:0.75rem;color:#555;margin-bottom:4px"><strong>Validates:</strong> {exp["validates"].format(gene=gene)}</div>', unsafe_allow_html=True)
                if exp["paper"]: st.markdown(exp["paper"], unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""<div style="background:#0a0c16;border:1px solid #1a1d2e;border-radius:10px;padding:16px 18px">
          <div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:10px">Evidence hierarchy — what counts as truth</div>
          <div style="font-size:0.8rem;color:#888;line-height:1.9">
            🏆 <strong style="color:#eee">Level 1 (Gold):</strong> Germline pathogenic variants in humans (ClinVar) — proof the protein is essential<br>
            🥈 <strong style="color:#eee">Level 2 (Silver):</strong> ITC binding assay — quantitative, no artefacts<br>
            🥉 <strong style="color:#eee">Level 3 (Bronze):</strong> Thermal shift (DSF) — confirms destabilisation<br>
            ⚠️ <strong style="color:#aaa">Caution:</strong> Cell culture assays, mouse knockouts — informative but not sufficient alone<br>
            ❌ <strong style="color:#555">Not evidence:</strong> Text mining, pathway inference, LLM predictions
          </div>
          <div style="margin-top:10px">{chip('king')}{chip('minikel')}{chip('plenge')}{chip('cook')}</div>
        </div>""", unsafe_allow_html=True)
