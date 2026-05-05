"""protein_deep_dive.py — Tab 5: Deep Dive (standalone protein query)"""
import streamlit as st, requests, time, re, pandas as pd, base64
from pathlib import Path

try:
    from logo import LOGO_DATA_URL as LOGO_B64
except Exception:
    _lp = Path("/mnt/user-data/uploads/1777622887238_image.png")
    LOGO_B64 = ("data:image/png;base64,"+base64.b64encode(_lp.read_bytes()).decode()) if _lp.exists() else None

from evidence_layer import calculate_dbr, assign_genomic_tier
try:
    from evidence_layer import classify_protein_role, EXPERIMENT_LADDER
except ImportError:
    def classify_protein_role(g, n, **kw):
        if n==0: return {"role":"unvalidated","label":"No ClinVar evidence","icon":"⚪","color":"#555","note":"Zero pathogenic variants."}
        elif n<10: return {"role":"rare_mendelian","label":"Rare Mendelian disease gene","icon":"🟡","color":"#FFD700","note":f"{n} pathogenic variant(s)."}
        elif n<500: return {"role":"validated","label":"Genomically validated","icon":"🟠","color":"#FFA500","note":f"{n} pathogenic variants."}
        else: return {"role":"critical_driver","label":"Critical disease driver","icon":"🔴","color":"#FF4C4C","note":f"{n} pathogenic variants."}
    EXPERIMENT_LADDER = {}

SESSION = requests.Session()
SESSION.headers.update({"User-Agent":"Protellect/4.0","Accept":"application/json"})

def _get(url, params=None, timeout=14):
    try:
        r = SESSION.get(url, params=params, timeout=timeout)
        if r.status_code == 200: return r.json()
    except Exception: pass
    return None

@st.cache_data(show_spinner=False, ttl=3600)
def _uniprot(gene):
    result = {"found":False,"uid":"","protein_name":"","length":0,"function":"","subcellular":[],"tissue":"","domains":[],"is_gpcr":False,"g_protein":"","natural_variants":[],"disease_comments":[],"keywords":[],"pdb_ids":[],"ensembl_id":"","omim":"","n_tm":0}
    for q in [f'gene_exact:{gene} AND organism_id:9606 AND reviewed:true', f'gene:{gene} AND organism_id:9606 AND reviewed:true']:
        d = _get("https://rest.uniprot.org/uniprotkb/search",{"query":q,"format":"json","size":1})
        if d and d.get("results"):
            result["uid"] = d["results"][0]["primaryAccession"]; result["found"] = True; break
    if not result["found"]: return result
    e = _get(f"https://rest.uniprot.org/uniprotkb/{result['uid']}",{"format":"json"},20)
    if not e: return result
    result["protein_name"] = e.get("proteinDescription",{}).get("recommendedName",{}).get("fullName",{}).get("value","")
    result["length"] = e.get("sequence",{}).get("length",0)
    for c in e.get("comments",[]):
        ct=c.get("commentType","")
        if ct=="FUNCTION": result["function"]=c.get("texts",[{}])[0].get("value","")[:600]
        elif ct=="SUBCELLULAR LOCATION":
            for loc in c.get("subcellularLocations",[]):
                v=loc.get("location",{}).get("value","")
                if v and v not in result["subcellular"]: result["subcellular"].append(v)
        elif ct=="TISSUE SPECIFICITY": result["tissue"]=c.get("texts",[{}])[0].get("value","")[:400]
        elif ct=="DISEASE":
            for d2 in c.get("diseases",[]): result["disease_comments"].append(d2.get("disease",{}).get("diseaseName",{}).get("value",""))
    for f in e.get("features",[]):
        ft=f.get("type",""); loc=f.get("location",{})
        s=loc.get("start",{}).get("value"); en=loc.get("end",{}).get("value",s)
        if s is None: continue
        s,en=int(s),int(en); desc=f.get("description","")
        if ft in ("Domain","Region","Zinc finger","Transmembrane","Repeat","Motif"): result["domains"].append({"start":s,"end":en,"name":desc,"type":ft})
        if ft=="Transmembrane": result["n_tm"]+=1
        elif ft=="Natural variant":
            orig=f.get("alternativeSequence",{}).get("originalSequence",""); var=f.get("alternativeSequence",{}).get("alternativeSequences",[""])[0]
            is_d=any(x in desc.lower() for x in ("disease","pathogenic","disorder","syndrome"))
            result["natural_variants"].append({"pos":s,"orig":orig,"var":var,"note":desc,"disease":is_d})
    for xr in e.get("uniProtKBCrossReferences",[]):
        db=xr.get("database",""); xid=xr.get("id","")
        if db=="PDB": result["pdb_ids"].append(xid)
        elif db=="OMIM": result["omim"]=xid
        elif db=="Ensembl" and not result["ensembl_id"]: result["ensembl_id"]=xid
    kws=[kw.get("value","").lower() for kw in e.get("keywords",[])]
    result["is_gpcr"]=any(k in " ".join(kws) for k in ["g protein-coupled","gpcr","muscarinic","adrenergic"]) or result["n_tm"]==7
    if result["is_gpcr"]:
        gmap={"CHRM1":"Gq/11","CHRM2":"Gi/o","CHRM3":"Gq/11","ADRB1":"Gs","ADRB2":"Gs","DRD1":"Gs","DRD2":"Gi/o","HTR1A":"Gi/o","HTR2A":"Gq/11"}
        result["g_protein"]=gmap.get(gene.upper(),"")
    return result

@st.cache_data(show_spinner=False, ttl=3600)
def _clinvar_full(gene):
    result={"pathogenic":[],"likely_pathogenic":[],"benign":[],"vus":[],"somatic":[],"all":[],"diseases":set()}
    try:
        s=SESSION.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",params={"db":"clinvar","term":f"{gene}[gene] AND single_gene[prop]","retmax":500,"retmode":"json","tool":"protellect","email":"research@protellect.com"},timeout=12)
        if not s or s.status_code!=200: return result
        ids=s.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return result
        time.sleep(0.35)
        for i in range(0,min(len(ids),500),100):
            batch=ids[i:i+100]; time.sleep(0.35)
            sm=SESSION.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",params={"db":"clinvar","id":",".join(batch),"retmode":"json","tool":"protellect","email":"research@protellect.com"},timeout=20)
            if not sm or sm.status_code!=200: continue
            doc=sm.json().get("result",{})
            for vid in doc.get("uids",[]):
                e=doc.get(vid,{})
                gs=e.get("germline_classification",{}).get("description","").strip()
                ss=e.get("somatic_clinical_impact",{}).get("description","").strip()
                is_s=bool(ss and not gs)
                title=e.get("title",""); conds=[c.get("trait_name","") for c in e.get("trait_set",[])]
                stars=e.get("review_status_label",""); sig=gs or ss or ""; m=re.search(r'[A-Z\*](\d+)[A-Za-z\*=]',title); pos=int(m.group(1)) if m else 0
                var={"id":vid,"title":title,"sig":sig,"germline":gs,"somatic":ss,"is_somatic":is_s,"conditions":[c for c in conds if c],"stars":stars,"pos":pos}
                result["all"].append(var)
                for c in conds:
                    if c: result["diseases"].add(c)
                if is_s: result["somatic"].append(var)
                else:
                    sl=sig.lower()
                    if "pathogenic" in sl and "likely" not in sl and "benign" not in sl: result["pathogenic"].append(var)
                    elif "likely pathogenic" in sl: result["likely_pathogenic"].append(var)
                    elif "benign" in sl: result["benign"].append(var)
                    elif "uncertain" in sl: result["vus"].append(var)
    except Exception: pass
    result["diseases"]=sorted(list(result["diseases"]))
    return result

@st.cache_data(show_spinner=False, ttl=3600)
def _pubmed(gene, disease="", n=6):
    papers=[]; seen=set()
    for q in ([f'{gene}[gene] AND "{disease}"[tiab] AND ("mutation" OR "variant")[tiab]'] if disease else []) + [f'{gene}[gene] AND "pathogenic variant" AND "human"[tiab]']:
        if len(papers)>=n: break
        try:
            s=SESSION.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",params={"db":"pubmed","term":q,"retmax":4,"retmode":"json","sort":"relevance","tool":"protellect","email":"research@protellect.com"},timeout=10)
            if not s or s.status_code!=200: continue
            ids=[i for i in s.json().get("esearchresult",{}).get("idlist",[]) if i not in seen]; seen.update(ids)
            if not ids: continue
            time.sleep(0.3)
            sm=SESSION.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",params={"db":"pubmed","id":",".join(ids),"retmode":"json","tool":"protellect","email":"research@protellect.com"},timeout=10)
            if not sm or sm.status_code!=200: continue
            rd=sm.json().get("result",{})
            for pid in rd.get("uids",[]):
                en=rd.get(pid,{}); papers.append({"pmid":pid,"title":en.get("title","")[:100],"journal":en.get("fulljournalname",""),"year":en.get("pubdate","")[:4],"url":f"https://pubmed.ncbi.nlm.nih.gov/{pid}/"})
        except Exception: pass
    return papers[:n]

CHIP_URLS={"king":"https://www.nature.com/articles/s41586-024-07316-0","minikel":"https://www.nature.com/articles/s41586-020-2267-z","plenge":"https://www.nature.com/articles/nrd.2016.29","cook":"https://www.nature.com/articles/nrd4309"}
CHIP_LABELS={"king":"King et al. Nature 2024","minikel":"Minikel et al. Nature 2021","plenge":"Plenge et al. NRD 2016","cook":"Cook et al. NRD 2014"}
def chip(k): return f'<a href="{CHIP_URLS[k]}" target="_blank" style="background:#0a0c1a;border:1px solid #1e2030;color:#4CA8FF;font-family:IBM Plex Mono,monospace;font-size:0.63rem;padding:2px 9px;border-radius:10px;text-decoration:none;margin:2px;display:inline-block">📄 {CHIP_LABELS[k]}</a>'

def render():
    if LOGO_B64:
        st.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px"><img src="{LOGO_B64}" style="height:36px;object-fit:contain;border-radius:6px"><div><strong style="font-size:1rem">Protein Deep Dive</strong><p style="color:#555;font-size:0.78rem;margin:0">Query any protein — ClinVar-first analysis with full breakdown</p></div></div>', unsafe_allow_html=True)
    st.divider()
    col_i, col_d = st.columns([1,1],gap="medium")
    with col_i: gene_q=st.text_input("Gene / protein",placeholder="FLNA, CHRM2, ARRB1, TP53...",key="dd_gene")
    with col_d: dis_q=st.text_input("Disease context (optional)",placeholder="cardiomyopathy, prune belly syndrome...",key="dd_dis")
    if not st.button("🔍 Analyse",type="primary",use_container_width=True,key="dd_run") or not gene_q.strip():
        if not gene_q.strip():
            st.markdown('<div style="background:#0a0c16;border:1px solid #1a1d2e;border-radius:10px;padding:20px;margin-top:8px"><p style="font-family:IBM Plex Mono,monospace;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:10px">Try these examples</p><div style="display:flex;gap:8px;flex-wrap:wrap"><span style="background:#0a0607;border:1px solid #FF4C4C33;border-radius:20px;padding:4px 14px;font-size:0.78rem;color:#aaa">FLNA + Periventricular heterotopia</span><span style="background:#0a0607;border:1px solid #FF4C4C33;border-radius:20px;padding:4px 14px;font-size:0.78rem;color:#aaa">FLNC + Cardiomyopathy</span><span style="background:#0a0c16;border:1px solid #1a1d2e;border-radius:20px;padding:4px 14px;font-size:0.78rem;color:#aaa">ARRB1</span><span style="background:#0a0c16;border:1px solid #1a1d2e;border-radius:20px;padding:4px 14px;font-size:0.78rem;color:#aaa">CHRM3 + Prune belly</span></div></div>', unsafe_allow_html=True)
        return
    gene=gene_q.strip().upper()
    with st.spinner(f"Fetching {gene} from UniProt, ClinVar, PubMed..."):
        uni=_uniprot(gene); cv=_clinvar_full(gene); papers=_pubmed(gene,dis_q)
    if not uni["found"]:
        st.error(f"Could not find {gene} in UniProt. Check the gene symbol."); return
    n_path=len(cv["pathogenic"])+len(cv["likely_pathogenic"]); n_som=len(cv["somatic"]); n_vus=len(cv["vus"])
    prot_len=uni["length"]; dbr=calculate_dbr(n_path,prot_len); tier=assign_genomic_tier(dbr,n_path)
    tc={"CRITICAL":"#FF4C4C","HIGH":"#FFA500","LOW":"#FFD700","NONE":"#888","UNKNOWN":"#4CA8FF"}.get(tier,"#888")
    role=classify_protein_role(gene,n_path); dbr_s=f"{dbr:.3f}" if dbr else "N/A"
    prot_name=uni.get("protein_name","") or gene
    # Header
    st.markdown(f"""<div style="background:#0a0a14;border:2px solid {tc};border-radius:12px;padding:18px 22px;margin-bottom:16px">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
        <div><div style="font-size:1.1rem;font-weight:700;color:#eee;font-family:IBM Plex Mono,monospace">{gene} — {prot_name}</div>
          <div style="font-size:0.75rem;color:#555;margin-top:2px">UniProt {uni['uid']} · {prot_len} aa · {'GPCR · '+uni['g_protein'] if uni['is_gpcr'] else 'Non-GPCR'} · {role['icon']} {role['label']}</div></div>
        <div style="text-align:right"><div style="font-size:1.8rem;font-weight:700;font-family:IBM Plex Mono,monospace;color:{tc}">{n_path}</div>
          <div style="font-size:0.62rem;color:#555;text-transform:uppercase">Germline pathogenic · DBR {dbr_s}</div></div>
      </div>
      <div style="margin-top:10px;padding-top:8px;border-top:1px solid {tc}33;font-size:0.8rem;color:#aaa;line-height:1.6">{role.get('note','')[:200]}</div>
      {'<div style="margin-top:6px;padding:6px 10px;background:#1a0808;border-radius:5px;font-size:0.75rem;color:#aaa;border-left:2px solid #FF4C4C">'+role.get("warning","")+"</div>" if role.get("warning") else ""}
    </div>""", unsafe_allow_html=True)
    # Stats
    c1,c2,c3,c4=st.columns(4)
    for col,n,lbl,c in [(c1,n_path,"Germline P/LP",tc),(c2,n_vus,"VUS","#555"),(c3,n_som,"Somatic (excl.)","#FFA500"),(c4,len(cv["all"]),"Total ClinVar","#aaa")]:
        col.markdown(f'<div style="background:#07080f;border:1px solid #12141e;border-radius:8px;padding:12px;text-align:center"><span style="font-size:1.4rem;font-weight:700;font-family:IBM Plex Mono,monospace;color:{c}">{n}</span><div style="font-size:0.62rem;color:#333;text-transform:uppercase;margin-top:2px">{lbl}</div></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    # Main cols
    mc1,mc2=st.columns([1,1],gap="medium")
    with mc1:
        st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:8px">Protein information</div>', unsafe_allow_html=True)
        for lbl,val in [("Gene",gene),("Protein",prot_name[:40] if prot_name else "—"),("UniProt",uni["uid"]),("Length",f"{prot_len} aa"),("Domains",f"{len(uni['domains'])} annotated"),("TM helices",str(uni["n_tm"])),("GPCR","✓ "+uni["g_protein"] if uni["is_gpcr"] else "No"),("OMIM",uni["omim"] or "—")]:
            st.markdown(f'<div style="display:flex;gap:8px;padding:4px 0;border-bottom:1px solid #0d0f18;font-size:0.79rem"><span style="color:#2a2d4a;min-width:88px;font-family:IBM Plex Mono,monospace;font-size:0.67rem;flex-shrink:0">{lbl}</span><span style="color:#bbb">{val}</span></div>', unsafe_allow_html=True)
        if uni.get("function"):
            st.markdown('<br><div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:6px">Function</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="background:#0a0c16;border:1px solid #1a1d2e;border-radius:6px;padding:10px 12px;font-size:0.79rem;color:#888;line-height:1.7">{uni["function"][:400]}</div>', unsafe_allow_html=True)
        if uni.get("subcellular"):
            st.markdown('<br><div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:6px">Subcellular location</div>', unsafe_allow_html=True)
            for loc in uni["subcellular"][:5]:
                st.markdown(f'<div style="padding:4px 0;font-size:0.78rem;color:#bbb;border-bottom:1px solid #0d0f18">📍 {loc}</div>', unsafe_allow_html=True)
    with mc2:
        st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:8px">ClinVar — germline vs somatic</div>', unsafe_allow_html=True)
        st.markdown(f"""<div style="background:#0a0607;border:1px solid {tc}44;border-radius:8px;padding:12px 14px;margin-bottom:10px">
          <div style="font-size:0.65rem;color:#555;margin-bottom:4px">WHY SEPARATION MATTERS</div>
          <p style="font-size:0.77rem;color:#888;line-height:1.6">Germline = inherited, proves essentiality. Somatic = cancer cell mutations, NOT inherited disease. A protein in COSMIC is not automatically a valid drug target. {chip('minikel')}</p>
        </div>""", unsafe_allow_html=True)
        gpath=cv["pathogenic"]+cv["likely_pathogenic"]
        if gpath:
            st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.15em;color:#FF4C4C;margin-bottom:6px">Germline P/LP variants</div>', unsafe_allow_html=True)
            rows=[{"Variant":v.get("title","")[:55],"AA":re.search(r'p\.([A-Za-z]{3}\d+[A-Za-z]{3}|[A-Za-z]\d+[A-Za-z=\*])',v.get("title","")).group(0) if re.search(r'p\.([A-Za-z]{3}\d+[A-Za-z]{3}|[A-Za-z]\d+[A-Za-z=\*])',v.get("title","")) else "—","Class":v.get("germline",""),"Disease":(v.get("conditions",["—"])[0] if v.get("conditions") else "—")[:40]} for v in gpath[:30]]
            df=pd.DataFrame(rows)
            def _s(val):
                if "Pathogenic" in str(val) and "Likely" not in str(val): return "color:#FF4C4C;font-weight:600"
                if "Likely" in str(val): return "color:#FFA500;font-weight:600"
                return ""
            st.dataframe(df.style.map(_s,subset=["Class"]),use_container_width=True,height=min(250,len(rows)*38+40))
            st.caption(f"Showing {min(30,len(gpath))} of {len(gpath)} germline P/LP. Source: NCBI ClinVar.")
        else:
            st.markdown(f'<div style="background:#0a0607;border:1px solid #FF4C4C33;border-radius:6px;padding:12px;font-size:0.8rem;color:#888">Zero confirmed germline pathogenic variants for {gene}. {"This is the β-arrestin pattern." if n_path==0 else ""}</div>', unsafe_allow_html=True)
        if cv.get("diseases"):
            st.markdown('<br><div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:6px">Associated diseases</div>', unsafe_allow_html=True)
            for d in list(cv["diseases"])[:6]:
                if d and "not provided" not in d.lower():
                    st.markdown(f'<div style="padding:4px 0;font-size:0.77rem;color:#bbb;border-bottom:1px solid #0d0f18">● {d}</div>', unsafe_allow_html=True)
    # Papers
    if papers:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.15em;color:#3a3d5a;margin-bottom:8px">PubMed papers — {gene} human disease evidence</div>', unsafe_allow_html=True)
        c1p,c2p=st.columns(2,gap="medium")
        for i,p in enumerate(papers):
            with (c1p if i%2==0 else c2p):
                st.markdown(f'<div style="background:#0a0c16;border:1px solid #1a1d2e;border-radius:8px;padding:10px 12px;margin-bottom:6px"><div style="font-size:0.78rem;font-weight:600;color:#eee;margin-bottom:3px;line-height:1.4">{p["title"]}</div><div style="font-size:0.68rem;color:#444;margin-bottom:4px">{p["journal"]} · {p["year"]}</div><a href="{p["url"]}" target="_blank" style="font-size:0.68rem;color:#4CA8FF;text-decoration:none">PubMed →</a></div>', unsafe_allow_html=True)
