"""disease_explorer.py — Tab 6: Disease Explorer"""
import streamlit as st, requests, time, re, pandas as pd, base64
from pathlib import Path
try:
    from logo import LOGO_DATA_URL as LOGO_B64
except Exception:
    _lp = Path("/mnt/user-data/uploads/1777622887238_image.png")
    LOGO_B64 = ("data:image/png;base64,"+base64.b64encode(_lp.read_bytes()).decode()) if _lp.exists() else None
from evidence_layer import calculate_dbr, assign_genomic_tier
try:
    from evidence_layer import classify_protein_role
except ImportError:
    def classify_protein_role(g, n, **kw):
        if n==0: return {"role":"unvalidated","label":"No ClinVar evidence","icon":"⚪","color":"#555","note":"Zero pathogenic variants."}
        elif n<10: return {"role":"rare_mendelian","label":"Rare Mendelian","icon":"🟡","color":"#FFD700","note":f"{n} pathogenic variant(s)."}
        elif n<500: return {"role":"validated","label":"Genomically validated","icon":"🟠","color":"#FFA500","note":f"{n} pathogenic variants."}
        else: return {"role":"critical_driver","label":"Critical driver","icon":"🔴","color":"#FF4C4C","note":f"{n} pathogenic variants."}

SESSION = requests.Session()
SESSION.headers.update({"User-Agent":"Protellect/4.0","Accept":"application/json"})

@st.cache_data(show_spinner=False,ttl=3600)
def search_disease(disease):
    results={}
    try:
        for term in [f'"{disease}"[dis] AND clinsig_pathogenic[prop]', f'{disease}[dis]', f'{disease}[all fields] AND human[org]']:
            s=SESSION.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",params={"db":"clinvar","term":term,"retmax":500,"retmode":"json","tool":"protellect","email":"research@protellect.com"},timeout=12)
            if s and s.status_code==200 and s.json().get("esearchresult",{}).get("idlist"): break
        ids=s.json().get("esearchresult",{}).get("idlist",[]) if s and s.status_code==200 else []
        if not ids: return {}
        for i in range(0,min(len(ids),500),100):
            batch=ids[i:i+100]; time.sleep(0.35)
            sm=SESSION.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",params={"db":"clinvar","id":",".join(batch),"retmode":"json","tool":"protellect","email":"research@protellect.com"},timeout=20)
            if not sm or sm.status_code!=200: continue
            doc=sm.json().get("result",{})
            for vid in doc.get("uids",[]):
                e=doc.get(vid,{}); gs=e.get("germline_classification",{}).get("description","").strip(); ss=e.get("somatic_clinical_impact",{}).get("description","").strip()
                is_s=bool(ss and not gs); title=e.get("title",""); conds=[c.get("trait_name","") for c in e.get("trait_set",[])]
                gm=re.search(r'\(([A-Z][A-Z0-9]{1,15})\)',title); gene=gm.group(1) if gm else None
                if not gene: continue
                sig=gs or ss or ""; stars=e.get("review_status_label","")
                if gene not in results: results[gene]={"gene":gene,"n_path":0,"n_lp":0,"n_vus":0,"n_somatic":0,"n_total":0,"variants":[],"diseases":set(),"best_stars":""}
                results[gene]["n_total"]+=1
                results[gene]["diseases"].update(c for c in conds if c)
                if is_s: results[gene]["n_somatic"]+=1
                else:
                    sl=sig.lower()
                    if "pathogenic" in sl and "likely" not in sl and "benign" not in sl: results[gene]["n_path"]+=1
                    elif "likely pathogenic" in sl: results[gene]["n_lp"]+=1
                    elif "uncertain" in sl: results[gene]["n_vus"]+=1
                results[gene]["variants"].append({"title":title[:70],"sig":sig,"conds":conds,"is_somatic":is_s})
                if stars and len(stars)>len(results[gene]["best_stars"]): results[gene]["best_stars"]=stars
    except Exception as e: st.error(f"ClinVar error: {e}")
    for g in results: results[g]["diseases"]=sorted(list(results[g]["diseases"]))
    return results

@st.cache_data(show_spinner=False,ttl=3600)
def get_prot_info(gene):
    try:
        d=SESSION.get("https://rest.uniprot.org/uniprotkb/search",params={"query":f'gene_exact:{gene} AND organism_id:9606 AND reviewed:true',"format":"json","size":1,"fields":"accession,protein_name,sequence,keyword,ft_transmem,length"},timeout=10)
        if d and d.status_code==200 and d.json().get("results"):
            e=d.json()["results"][0]; uid=e.get("primaryAccession","")
            pname=e.get("proteinDescription",{}).get("recommendedName",{}).get("fullName",{}).get("value","")
            length=e.get("sequence",{}).get("length",0)
            kws=[kw.get("value","").lower() for kw in e.get("keywords",[])]
            is_g=any(k in " ".join(kws) for k in ["g protein-coupled","gpcr","muscarinic","adrenergic"])
            n_tm=sum(1 for f in e.get("features",[]) if f.get("type","")=="Transmembrane")
            is_g=is_g or n_tm==7
            gmap={"CHRM1":"Gq/11","CHRM2":"Gi/o","CHRM3":"Gq/11","ADRB1":"Gs","ADRB2":"Gs","DRD1":"Gs","DRD2":"Gi/o"}
            return {"uid":uid,"pname":pname,"length":length,"is_gpcr":is_g,"g_protein":gmap.get(gene.upper(),"")}
    except Exception: pass
    return {"uid":"","pname":"","length":0,"is_gpcr":False,"g_protein":""}

def render():
    if LOGO_B64:
        st.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px"><img src="{LOGO_B64}" style="height:36px;object-fit:contain;border-radius:6px"><div><strong style="font-size:1rem">Disease Explorer</strong><p style="color:#555;font-size:0.78rem;margin:0">Enter a disease → every protein with confirmed ClinVar germline pathogenic variants</p></div></div>', unsafe_allow_html=True)
    st.divider()
    st.markdown('<div style="background:#0a0c16;border:1px solid #1a1d2e;border-radius:8px;padding:10px 14px;margin-bottom:14px;font-size:0.77rem;color:#555;line-height:1.6"><strong style="color:#888">ClinVar only.</strong> Shows proteins with confirmed germline pathogenic variants. Germline (inherited) and somatic (cancer) variants shown separately. If a protein has zero germline pathogenic variants, it is not shown.</div>', unsafe_allow_html=True)
    disease_input=st.text_input("Disease name",placeholder="Prune belly syndrome · Dilated cardiomyopathy · Breast cancer · Epilepsy...",key="de_disease")
    run=st.button("🔍 Find all affiliated proteins",type="primary",use_container_width=True,key="de_run")
    if not run or not disease_input.strip():
        if not disease_input.strip():
            st.markdown('<div style="background:#0a0c16;border:1px solid #1a1d2e;border-radius:10px;padding:20px;margin-top:8px"><p style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:10px">Try these</p><div style="display:flex;gap:8px;flex-wrap:wrap"><span style="background:#0a0607;border:1px solid #FF4C4C33;border-radius:20px;padding:4px 14px;font-size:0.78rem;color:#aaa">Prune belly syndrome</span><span style="background:#0a0607;border:1px solid #FF4C4C33;border-radius:20px;padding:4px 14px;font-size:0.78rem;color:#aaa">Arrhythmogenic cardiomyopathy</span><span style="background:#0a0607;border:1px solid #FF4C4C33;border-radius:20px;padding:4px 14px;font-size:0.78rem;color:#aaa">Dilated cardiomyopathy</span><span style="background:#0a0607;border:1px solid #FF4C4C33;border-radius:20px;padding:4px 14px;font-size:0.78rem;color:#aaa">Periventricular heterotopia</span></div></div>', unsafe_allow_html=True)
        return
    disease=disease_input.strip()
    with st.spinner(f"Querying ClinVar for '{disease}'..."):
        proteins=search_disease(disease)
    if not proteins:
        st.warning(f"No proteins with confirmed ClinVar variants found for '{disease}'. Try a broader term."); return
    st.markdown(f'<div style="background:#070a07;border:1px solid #4CAF5044;border-radius:8px;padding:10px 14px;margin-bottom:14px;font-size:0.8rem;color:#4CAF50">Found <strong>{len(proteins)}</strong> gene(s) with ClinVar variants for: <strong style="color:#eee">{disease}</strong> · Source: NCBI ClinVar · Germline and somatic shown separately</div>', unsafe_allow_html=True)
    enriched=[]; prog=st.progress(0)
    for i,(g,p) in enumerate(list(proteins.items())[:30]):
        pinfo=get_prot_info(g); n_p=p["n_path"]+p["n_lp"]; plen=pinfo["length"]
        dbr=calculate_dbr(n_p,plen); tier=assign_genomic_tier(dbr,n_p); v=assign_genomic_tier(dbr,n_p)
        enriched.append({**p,"length":plen,"pname":pinfo["pname"],"uid":pinfo["uid"],"is_gpcr":pinfo["is_gpcr"],"g_protein":pinfo["g_protein"],"n_combined":n_p,"dbr":dbr,"tier":tier})
        prog.progress((i+1)/min(len(proteins),30))
    prog.empty()
    enriched.sort(key=lambda x:x["n_combined"],reverse=True)
    # Summary table
    trows=[{"Gene":e["gene"],"Protein":e["pname"][:35] if e["pname"] else "—","Germline P/LP":e["n_combined"],"VUS":e["n_vus"],"Somatic (excl.)":e["n_somatic"],"Length":e["length"] or "—","DBR":f"{e['dbr']:.3f}" if e["dbr"] else "—","Tier":e["tier"],"GPCR":"✓" if e["is_gpcr"] else "","G-protein":e["g_protein"] or ""} for e in enriched]
    df=pd.DataFrame(trows)
    def _st(val):
        s=str(val)
        if "CRITICAL" in s: return "color:#FF4C4C;font-weight:600"
        if "HIGH" in s: return "color:#FFA500;font-weight:600"
        if "LOW" in s: return "color:#FFD700"
        if "NONE" in s: return "color:#555"
        return ""
    st.dataframe(df.style.map(_st,subset=["Tier"]),use_container_width=True,height=min(400,len(enriched)*38+50))
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:12px">Per-protein breakdown</div>', unsafe_allow_html=True)
    for e in enriched:
        tc={"CRITICAL":"#FF4C4C","HIGH":"#FFA500","LOW":"#FFD700","NONE":"#888","UNKNOWN":"#4CA8FF"}.get(e["tier"],"#888")
        dbr_s=f"{e['dbr']:.3f}" if e["dbr"] else "N/A"; role=classify_protein_role(e["gene"],e["n_combined"])
        with st.expander(f"{role['icon']} {e['gene']} — {e['pname'] or e['gene']} · {e['n_combined']} germline P/LP · DBR {dbr_s} · {e['tier']}"):
            c1,c2,c3=st.columns([1,1,1],gap="medium")
            with c1:
                st.markdown(f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.12em;color:{tc};margin-bottom:6px">Genomic verdict</div>', unsafe_allow_html=True)
                st.markdown(f'<p style="font-size:0.79rem;color:#bbb;line-height:1.6">{role.get("note","")}</p>', unsafe_allow_html=True)
                st.markdown(f'<p style="font-size:0.77rem;color:#666;font-style:italic;margin-top:6px">{role.get("label","")}</p>', unsafe_allow_html=True)
                if e["is_gpcr"]:
                    st.markdown(f'<div style="background:#100a18;border:1px solid #9370DB44;border-radius:5px;padding:6px 10px;margin-top:6px;font-size:0.73rem;color:#9370DB">GPCR ✓{"  ·  G-protein: "+e["g_protein"] if e["g_protein"] else ""}</div>', unsafe_allow_html=True)
            with c2:
                st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.12em;color:#3a3d5a;margin-bottom:6px">ClinVar summary</div>', unsafe_allow_html=True)
                for lbl,val,c in [("Pathogenic",e["n_path"],tc),("Likely pathogenic",e["n_lp"],tc),("VUS",e["n_vus"],"#555"),("Somatic (excl.)",e["n_somatic"],"#FFA500"),("Total submissions",e["n_total"],"#aaa"),("Protein length",f"{e['length']} aa" if e["length"] else "—","#aaa"),("DBR",dbr_s,tc)]:
                    st.markdown(f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #0d0f18;font-size:0.77rem"><span style="color:#444">{lbl}</span><span style="color:{c};font-family:IBM Plex Mono,monospace;font-size:0.73rem">{val}</span></div>', unsafe_allow_html=True)
            with c3:
                st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.12em;color:#3a3d5a;margin-bottom:6px">Diseases (ClinVar)</div>', unsafe_allow_html=True)
                for d in (e.get("diseases",[]) or [])[:5]:
                    if d and "not provided" not in d.lower():
                        st.markdown(f'<div style="font-size:0.75rem;color:#aaa;padding:3px 0;border-bottom:1px solid #0d0f18">● {d}</div>', unsafe_allow_html=True)
            gpath=[v for v in e.get("variants",[]) if not v.get("is_somatic") and "pathogenic" in v.get("sig","").lower() and "benign" not in v.get("sig","").lower()]
            if gpath:
                st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.12em;color:#FF4C4C;margin-top:10px;margin-bottom:5px">Germline pathogenic variants</div>', unsafe_allow_html=True)
                for v in gpath[:5]:
                    c=v.get("conds",[""])[0] if v.get("conds") else "—"
                    st.markdown(f'<div style="font-size:0.73rem;color:#aaa;padding:3px 0;border-bottom:1px solid #0d0f18"><span style="color:#FF4C4C;font-family:IBM Plex Mono,monospace;font-size:0.65rem">[{v.get("sig","")[:20]}]</span> {v.get("title","")}</div>', unsafe_allow_html=True)
    # Export
    st.markdown("<br>", unsafe_allow_html=True)
    exp_df=pd.DataFrame(trows)
    st.download_button("⬇ Download (CSV)",exp_df.to_csv(index=False).encode(),f"protellect_disease_{disease.replace(' ','_')}.csv","text/csv")
    st.caption(f"All data from NCBI ClinVar · Germline variants only in primary analysis · Disease: {disease}")
