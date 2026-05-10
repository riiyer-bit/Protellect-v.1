import streamlit as st
import requests, re, json, io, os, hashlib
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

# Anthropic — optional (required only for AI features)
try:
    import anthropic as _anthropic_lib
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

def _get_anthropic_client():
    if not ANTHROPIC_AVAILABLE:
        return None
    key = None
    try:
        import streamlit as st
        key = st.secrets.get("ANTHROPIC_API_KEY") or st.secrets.get("anthropic_api_key")
    except: pass
    if not key: key = os.environ.get("ANTHROPIC_API_KEY","")
    return _anthropic_lib.Anthropic(api_key=key) if key else None


# ============ AUTH ============

def _hash(pw): return hashlib.sha256(pw.encode()).hexdigest()

_DEFAULTS = {
    "demo@protellect.com":{"password":_hash("protellect2024"),"name":"Demo User","plan":"free","searches_used":0,"max_searches":10,"lab_profile":None,"onboarded":False},
    "pro@protellect.com":{"password":_hash("pro2024"),"name":"Dr. Researcher","plan":"pro","searches_used":0,"max_searches":500,"lab_profile":None,"onboarded":False},
}

def _db():
    if "users_db" not in st.session_state: st.session_state.users_db=_DEFAULTS.copy()
    return st.session_state.users_db

def current_user(): return st.session_state.get("current_user")
def is_logged_in(): return current_user() is not None

def login(email,password):
    db=_db()
    if email not in db: return False,"No account found."
    if db[email]["password"]!=_hash(password): return False,"Incorrect password."
    st.session_state.current_user={**db[email],"email":email}; return True,"ok"

def register(email,password,name):
    db=_db()
    if email in db: return False,"Email already registered."
    if len(password)<8: return False,"Password must be 8+ characters."
    db[email]={"password":_hash(password),"name":name,"plan":"free","searches_used":0,"max_searches":10,"lab_profile":None,"onboarded":False}
    st.session_state.current_user={**db[email],"email":email}; return True,"ok"

def logout():
    for k in ["current_user","domain","subdomain","lab_profile","onboarding_done","analysis_cache"]: st.session_state.pop(k,None)

def save_lab_profile(profile):
    u=current_user()
    if not u: return
    db=_db(); e=u["email"]; db[e]["lab_profile"]=profile; db[e]["onboarded"]=True
    st.session_state.current_user["lab_profile"]=profile; st.session_state.current_user["onboarded"]=True
    st.session_state.lab_profile=profile; st.session_state.onboarding_done=True

def can_search():
    u=current_user()
    if not u: return False
    if u.get("plan")=="pro": return True
    return u.get("searches_used",0)<u.get("max_searches",10)

def decrement_search():
    u=current_user()
    if not u or u.get("plan")=="pro": return
    db=_db(); e=u["email"]; db[e]["searches_used"]=db[e].get("searches_used",0)+1
    st.session_state.current_user["searches_used"]=db[e]["searches_used"]

# ============ APIs ============

ESEARCH="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
EFETCH="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

TIER_MAP={"Tier 1 — RCT":{"color":"#00c896","w":10},"Tier 2 — Cohort":{"color":"#4a90d9","w":8},"Tier 3 — Functional":{"color":"#ff8c42","w":7},"Tier 4 — Structural":{"color":"#a855f7","w":6},"Tier 5 — Animal":{"color":"#ffd60a","w":5},"Tier 6 — Computational":{"color":"#5a8090","w":4},"Tier 7 — Case report":{"color":"#3a5a7a","w":3},"Tier 8 — Review":{"color":"#2a4060","w":2},"Tier 9 — Preprint":{"color":"#ff2d55","w":1}}

def classify_tier(title,abstract=""):
    t=(title+" "+abstract).lower()
    if any(x in t for x in ["randomised","randomized","rct","placebo-controlled","double-blind"]): return "Tier 1 — RCT"
    if any(x in t for x in ["cohort","prospective","retrospective","patients with","case-control","multicentre"]): return "Tier 2 — Cohort"
    if any(x in t for x in ["crispr","knock-in","knock-out","functional assay","western blot","immunoprecipitation","luciferase","splicing"]): return "Tier 3 — Functional"
    if any(x in t for x in ["crystal structure","cryo-em","nmr structure","x-ray","alphafold","spr","itc","binding affinity"]): return "Tier 4 — Structural"
    if any(x in t for x in ["mouse model","zebrafish","xenograft","in vivo","murine","animal model"]): return "Tier 5 — Animal"
    if any(x in t for x in ["computational","in silico","machine learning","deep learning","algorithm"]): return "Tier 6 — Computational"
    if any(x in t for x in ["case report","case series","patient report"]): return "Tier 7 — Case report"
    if any(x in t for x in ["review","meta-analysis","systematic review","pooled analysis"]): return "Tier 8 — Review"
    return "Tier 9 — Preprint"

def detect_weaknesses(title,abstract=""):
    warnings=[]; t=(title+" "+abstract).lower()
    if any(x in t for x in ["beta-arrestin","arrestin"]):
        warnings.append(("⚠️ No ARRB disease variant evidence","Beta-arrestin used as readout/target. ARRB1/ARRB2 double KO mice viable. Zero Mendelian disease variants. Phospho-codes are kinase noise."))
    if any(x in t for x in ["hek293","hek 293","cos-7","cos7"]):
        warnings.append(("⚠️ Transformed cell line artefact risk","HEK293/COS cells have hyperactivated signalling. Results may not reflect primary cell biology."))
    if any(x in t for x in ["overexpressed","overexpression","transiently transfected","ectopic"]):
        warnings.append(("⚠️ Overexpression artefact","Non-physiological concentrations cause artefactual interactions. CRISPR endogenous tagging preferred."))
    if "n=3" in t or "n = 3" in t:
        warnings.append(("⚠️ Small sample (n=3)","Insufficient statistical power. Effect sizes overestimated. Seek independent replication."))
    if any(x in t for x in ["phosphorylation code","barcode","grk phosphorylation"]):
        warnings.append(("⚠️ Phospho 'code' claim","GRK/arrestin codes lack disease variant validation. Background kinase noise unless residue mutation causes disease."))
    if any(x in t for x in ["g93a","sod1 g93a"]):
        warnings.append(("⚠️ SOD1 G93A — poor translational record","100+ drugs effective in this model failed in human ALS. Does not represent C9ORF72 or TDP-43 pathology."))
    if any(x in t for x in ["candidate gene","haplotype"]) and "gwas" not in t:
        warnings.append(("⚠️ Pre-GWAS candidate gene study","High false-positive rate. Most pre-GWAS candidate gene findings did not replicate in large GWAS."))
    return warnings

@st.cache_data(ttl=3600,show_spinner=False)
def api_uniprot(gene):
    try:
        r=requests.get("https://rest.uniprot.org/uniprotkb/search",params={"query":f"gene:{gene} AND organism_id:9606 AND reviewed:true","format":"json","size":1},timeout=12)
        res=r.json().get("results",[])
        if not res: return {}
        p=res[0]; uid=p.get("primaryAccession","")
        name=(p.get("proteinDescription",{}).get("recommendedName",{}).get("fullName",{}).get("value",""))
        gene_sym=p.get("genes",[{}])[0].get("geneName",{}).get("value",gene)
        func=""; diseases=[]; tissues=[]; ptms=[]
        for c in p.get("comments",[]):
            ct=c.get("commentType","")
            if ct=="FUNCTION" and not func: func=" ".join(x.get("value","") for x in c.get("texts",[]))[:500]
            if ct=="DISEASE":
                d=c.get("disease",{}); diseases.append({"name":d.get("diseaseId",d.get("diseaseName","")),"desc":" ".join(x.get("value","") for x in c.get("texts",[]))[:200]})
            if ct=="TISSUE SPECIFICITY": tissues.append(" ".join(x.get("value","") for x in c.get("texts",[]))[:200])
            if ct=="PTM": ptms.append(" ".join(x.get("value","") for x in c.get("texts",[]))[:200])
        # Keywords for GO-like classification
        keywords=[kw.get("name","") for kw in p.get("keywords",[])[:15]]
        return{"uid":uid,"name":name,"gene":gene_sym,"function":func,"diseases":diseases[:8],"tissues":tissues[:3],"ptms":ptms[:3],"keywords":keywords,"length":p.get("sequence",{}).get("length",0),"taxon":p.get("organism",{}).get("taxonId",0),"human":p.get("organism",{}).get("taxonId",0)==9606}
    except: return {}

@st.cache_data(ttl=3600,show_spinner=False)
def api_clinvar(gene):
    try:
        r=requests.get(ESEARCH,params={"db":"clinvar","term":f"{gene}[gene] AND (pathogenic[clinsig] OR likely_pathogenic[clinsig])","retmax":50,"retmode":"json"},timeout=12)
        ids=r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return []
        r2=requests.get(EFETCH,params={"db":"clinvar","id":",".join(ids[:35]),"rettype":"vcv","retmode":"json"},timeout=15)
        variants=[]
        for uid,entry in r2.json().get("result",{}).items():
            if uid=="uids": continue
            title=entry.get("title",""); cs=entry.get("clinical_significance",{}).get("description","")
            stars=entry.get("review_status",{}).get("stars",0)
            cond="; ".join((entry.get("trait_set",[{}])[0].get("trait_name",[""]) if entry.get("trait_set") else [""]))
            score=(5 if "pathogenic" in cs.lower() and "likely" not in cs.lower() else 4 if "likely pathogenic" in cs.lower() else 0)+min(stars,2)
            rank="CRITICAL" if score>=6 else "HIGH" if score>=5 else "MODERATE" if score>=4 else "LOW"
            variants.append({"uid":uid,"title":title,"cs":cs,"stars":stars,"condition":cond,"score":score,"ml_rank":rank,"url":f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/"})
        return sorted(variants,key=lambda x:-x["score"])
    except: return []

@st.cache_data(ttl=3600,show_spinner=False)
def api_gnomad(gene):
    try:
        q='{ gene(gene_symbol: "%s", reference_genome: GRCh38) { gnomad_constraint { pli oe_lof oe_mis } } }' % gene
        r=requests.post("https://gnomad.broadinstitute.org/api",json={"query":q},timeout=12)
        c=r.json().get("data",{}).get("gene",{}).get("gnomad_constraint",{})
        return{"pLI":round(c.get("pli",0),3),"oe_lof":round(c.get("oe_lof",1),3),"oe_mis":round(c.get("oe_mis",1),3)}
    except: return {}

@st.cache_data(ttl=3600,show_spinner=False)
def api_string(gene):
    try:
        r=requests.get("https://string-db.org/api/json/network",params={"identifiers":gene,"species":9606,"required_score":700,"limit":12},timeout=12)
        seen=set(); partners=[]
        for item in r.json():
            a,b=item.get("preferredName_A",""),item.get("preferredName_B","")
            partner=b if a.upper()==gene.upper() else a
            if partner and partner.upper()!=gene.upper() and partner not in seen:
                seen.add(partner); partners.append({"partner":partner,"score":round(item.get("score",0),3),"mode":item.get("mode","")})
        return partners[:10]
    except: return []

@st.cache_data(ttl=3600,show_spinner=False)
def api_opentargets(gene):
    try:
        r0=requests.get(f"https://mygene.info/v3/query?q={gene}&species=human&fields=ensembl.gene",timeout=8)
        hits=r0.json().get("hits",[])
        if not hits: return {}
        ensembl=hits[0].get("ensembl",{})
        if isinstance(ensembl,list): ensembl=ensembl[0]
        eid=ensembl.get("gene","")
        if not eid: return {}
        q='query($id:String!){ target(ensemblId:$id){ knownDrugs{ rows{ drug{ name } phase approvedIndications } } tractability{ label modality value } associatedDiseases(page:{size:8}){ rows{ disease{ name } score } } } }'
        r=requests.post("https://api.platform.opentargets.org/api/v4/graphql",json={"query":q,"variables":{"id":eid}},timeout=12)
        t=r.json().get("data",{}).get("target",{})
        drugs=[{"name":row.get("drug",{}).get("name",""),"phase":row.get("phase",0),"indication":(row.get("approvedIndications") or [""])[0]} for row in (t.get("knownDrugs") or {}).get("rows",[])[:8]]
        tract=[x.get("label","") for x in (t.get("tractability") or []) if x.get("value")]
        dis_assoc=[{"name":row.get("disease",{}).get("name",""),"score":round(row.get("score",0),3)} for row in (t.get("associatedDiseases") or {}).get("rows",[])[:6]]
        return{"drugs":drugs,"tractability":tract,"disease_assoc":dis_assoc,"ensembl":eid}
    except: return {}

@st.cache_data(ttl=3600,show_spinner=False)
def api_clinicaltrials(gene):
    try:
        r=requests.get("https://clinicaltrials.gov/api/v2/studies",params={"query.term":gene,"filter.status":"RECRUITING","pageSize":10,"format":"json"},timeout=12)
        studies=[]
        for s in r.json().get("studies",[])[:8]:
            proto=s.get("protocolSection",{}); ident=proto.get("identificationModule",{})
            status=proto.get("statusModule",{}); design=proto.get("designModule",{})
            studies.append({"nct":ident.get("nctId",""),"title":ident.get("briefTitle","")[:90],"phase":", ".join(design.get("phases",[])),"status":status.get("overallStatus",""),"sponsor":proto.get("sponsorCollaboratorsModule",{}).get("leadSponsor",{}).get("name","")[:50],"url":f"https://clinicaltrials.gov/study/{ident.get('nctId','')}"})
        return studies
    except: return []

@st.cache_data(ttl=3600,show_spinner=False)
def api_pubmed(query,n=10):
    try:
        r=requests.get(ESEARCH,params={"db":"pubmed","term":query,"retmax":n,"retmode":"json","sort":"relevance"},timeout=12)
        ids=r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return []
        r2=requests.get(ESUMMARY,params={"db":"pubmed","id":",".join(ids),"retmode":"json"},timeout=12)
        result=r2.json().get("result",{}); papers=[]
        for uid in result.get("uids",[]):
            e=result.get(uid,{}); auth=", ".join(a.get("name","") for a in e.get("authors",[])[:3])
            if len(e.get("authors",[]))>3: auth+=" et al."
            title=e.get("title",""); doi=e.get("elocationid","").replace("doi: ","")
            papers.append({"pmid":uid,"title":title,"authors":auth,"journal":e.get("source",""),"year":e.get("pubdate","")[:4],"doi":doi,"tier":classify_tier(title),"url":f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"})
        return papers
    except: return []

@st.cache_data(ttl=3600,show_spinner=False)
def api_alphafold(uid):
    try:
        r=requests.get(f"https://alphafold.ebi.ac.uk/api/prediction/{uid}",timeout=10)
        d=r.json()
        if not d: return {}
        return{"af_url":f"https://alphafold.ebi.ac.uk/entry/{uid}","pdb_url":d[0].get("pdbUrl",""),"am_url":d[0].get("amAnnotationsUrl","")}
    except: return {}

@st.cache_data(ttl=3600,show_spinner=False)
def api_alphamissense(uid):
    """Fetch AlphaMissense per-residue pathogenicity scores."""
    try:
        af=api_alphafold(uid)
        am_url=af.get("am_url","")
        if not am_url: return {}
        r=requests.get(am_url,timeout=20)
        lines=r.text.strip().split("\n")
        scores=[]; pathogenic=0; benign=0; ambiguous=0
        for line in lines[1:]:
            parts=line.split(",")
            if len(parts)>=4:
                try:
                    pos=int(parts[1]); score=float(parts[3]); cls=parts[4].strip() if len(parts)>4 else ""
                    scores.append({"pos":pos,"ref":parts[0],"alt":parts[2],"score":score,"class":cls})
                    if score>=0.564: pathogenic+=1
                    elif score<=0.34: benign+=1
                    else: ambiguous+=1
                except: pass
        mean=round(sum(s["score"] for s in scores)/len(scores),3) if scores else 0
        # Get unique positions for heatmap
        pos_dict={}
        for s in scores:
            p=s["pos"]
            if p not in pos_dict or s["score"]>pos_dict[p]: pos_dict[p]=s["score"]
        return{"scores":scores,"pathogenic_count":pathogenic,"benign_count":benign,"ambiguous_count":ambiguous,"mean_score":mean,"total":len(scores),"pos_max_scores":pos_dict}
    except: return {}

@st.cache_data(ttl=3600,show_spinner=False)
def api_pubchem_structure(compound_name):
    """Get SMILES and 2D structure info from PubChem."""
    try:
        r=requests.get(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{requests.utils.quote(compound_name)}/property/MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName,XLogP/JSON",timeout=10)
        props=r.json().get("PropertyTable",{}).get("Properties",[{}])[0]
        cid=r.json().get("PropertyTable",{}).get("Properties",[{}])[0].get("CID","")
        return{"cid":cid,"formula":props.get("MolecularFormula",""),"mw":props.get("MolecularWeight",""),"smiles":props.get("CanonicalSMILES",""),"iupac":props.get("IUPACName",""),"logp":props.get("XLogP",""),"img_url":f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/PNG" if cid else ""}
    except: return {}

@st.cache_data(ttl=3600,show_spinner=False)
def api_kegg_pathway(gene):
    """Fetch KEGG pathway annotations for a gene."""
    try:
        r=requests.get(f"https://rest.kegg.jp/find/genes/hsa:{gene}",timeout=10)
        genes_found=r.text.strip().split("\n")[:3]
        pathways=[]
        for gline in genes_found:
            if "\t" in gline:
                kegg_id=gline.split("\t")[0]
                r2=requests.get(f"https://rest.kegg.jp/link/pathway/{kegg_id}",timeout=8)
                for pline in r2.text.strip().split("\n")[:5]:
                    if "\t" in pline:
                        pw_id=pline.split("\t")[1].replace("path:","")
                        r3=requests.get(f"https://rest.kegg.jp/get/{pw_id}",timeout=8)
                        for kline in r3.text.split("\n")[:3]:
                            if kline.startswith("NAME"):
                                pathways.append({"id":pw_id,"name":kline.replace("NAME","").strip()})
        return pathways[:6]
    except: return []

def gi_score(cv,length):
    n=len(cv); density=n/max(length,1); per100=n/(length/100) if length else 0
    n_crit=sum(1 for v in cv if v.get("ml_rank")=="CRITICAL")
    n_lof=sum(1 for v in cv if any(k in v.get("title","").lower() for k in ["frameshift","nonsense","stop gained","stop_gained","del"]))
    if not cv: return{"verdict":"NO DISEASE VARIANTS","color":"#1e3a5a","pursue":"deprioritise","n":0,"per100":0,"n_crit":0,"n_lof":0,"icon":"⚪","explanation":"Zero pathogenic variants. Cannot classify as disease driver without human genetic evidence."}
    if per100>=1.0 and n>=5 and n_crit>=1: return{"verdict":"DISEASE-CRITICAL","color":"#ff2d55","pursue":"prioritise","n":n,"per100":round(per100,2),"n_crit":n_crit,"n_lof":n_lof,"icon":"🔴","explanation":f"{n} confirmed P/LP variants · {n_crit} CRITICAL (multi-star review) · Strong genetic validation for therapeutic investment."}
    if per100>=0.5 or n>=15: return{"verdict":"DISEASE-ASSOCIATED","color":"#ff8c42","pursue":"proceed","n":n,"per100":round(per100,2),"n_crit":n_crit,"n_lof":n_lof,"icon":"🟠","explanation":f"{n} pathogenic variants. Meaningful genetic association. Work from confirmed P/LP variants only."}
    if n>=3: return{"verdict":"MODERATE","color":"#ffd60a","pursue":"selective","n":n,"per100":round(per100,2),"n_crit":n_crit,"n_lof":n_lof,"icon":"🟡","explanation":f"{n} variants — low density. Be selective. Do not extrapolate beyond confirmed P/LP entries."}
    return{"verdict":"VERY LOW","color":"#3a5a7a","pursue":"caution","n":n,"per100":round(per100,2),"n_crit":n_crit,"n_lof":n_lof,"icon":"🔵","explanation":f"Only {n} pathogenic variants. Possible functional redundancy."}

# ============ MOL CELL ============
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

# ============ MICROBIOME AI ============
# _get_client defined above globally
def _get_client_UNUSED():
    global ANTHROPIC_CLIENT
    if ANTHROPIC_CLIENT is None:
        import os, streamlit as st
        key = None
        try: key = st.secrets.get("ANTHROPIC_API_KEY") or st.secrets.get("anthropic_api_key")
        except: pass
        if not key: key = os.environ.get("ANTHROPIC_API_KEY","")
        if not key: raise ValueError("Set ANTHROPIC_API_KEY in Streamlit secrets (Settings → Secrets).")
        ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=key)
    return ANTHROPIC_CLIENT

# ─── Microbiome-specific databases ─────────────────────────────────────────────

@st.cache_data(ttl=7200,show_spinner=False)
def fetch_mgnify_study(accession):
    """Fetch MGnify study metadata and functional annotations."""
    try:
        r=requests.get(f"https://www.ebi.ac.uk/metagenomics/api/v1/studies/{accession}",timeout=12)
        if not r.ok: return {}
        data=r.json().get("data",{})
        attrs=data.get("attributes",{})
        return{"id":accession,"name":attrs.get("study-name",""),"abstract":attrs.get("study-abstract",""),"centre":attrs.get("centre-name",""),"biomes":[b.get("id","") for b in data.get("relationships",{}).get("biomes",{}).get("data",[])[:3]]}
    except: return {}

@st.cache_data(ttl=7200,show_spinner=False)
def fetch_ncbi_taxonomy(taxon_id):
    """Fetch NCBI taxonomy information for a microbe."""
    try:
        r=requests.get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=taxonomy&id={taxon_id}&retmode=json",timeout=10)
        data=r.json()
        tax=data.get("result",{}).get(str(taxon_id),{})
        lineage=tax.get("lineage",""); sci_name=tax.get("scientificname","")
        return{"taxon_id":taxon_id,"name":sci_name,"lineage":lineage,"rank":tax.get("rank","")}
    except: return {}

@st.cache_data(ttl=7200,show_spinner=False)
def fetch_interpro_entry(interpro_id):
    """Fetch InterPro functional domain information."""
    try:
        r=requests.get(f"https://www.ebi.ac.uk/interpro/api/entry/interpro/{interpro_id}/?format=json",timeout=10)
        if not r.ok: return {}
        data=r.json(); attrs=data.get("metadata",{})
        return{"id":interpro_id,"name":attrs.get("name",""),"type":attrs.get("type",""),"description":attrs.get("description","")[:400]}
    except: return {}

@st.cache_data(ttl=3600,show_spinner=False)
def pubmed_microbiome(query,n=8):
    """Fetch microbiome-specific papers from PubMed."""
    try:
        r=requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                       params={"db":"pubmed","term":query,"retmax":n,"retmode":"json","sort":"relevance"},timeout=12)
        ids=r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return []
        r2=requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                        params={"db":"pubmed","id":",".join(ids),"retmode":"json"},timeout=12)
        result=r2.json().get("result",{}); papers=[]
        for uid in result.get("uids",[]):
            e=result.get(uid,{}); auth=", ".join(a.get("name","") for a in e.get("authors",[])[:3])
            if len(e.get("authors",[]))>3: auth+=" et al."
            papers.append({"pmid":uid,"title":e.get("title",""),"authors":auth,"journal":e.get("source",""),"year":e.get("pubdate","")[:4],"doi":e.get("elocationid","").replace("doi: ",""),"url":f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"})
        return papers
    except: return []

# ─── THE KEY FEATURE: LLM re-annotation of microbial functions ─────────────────

def annotate_microbial_genes_llm(gene_ids: list, context: str = "", lab_focus: str = "") -> dict:
    """
    Takes a list of microbial gene IDs (KEGG, COG, GO terms, InterPro IDs)
    and returns LLM-generated meaningful biological narratives.
    
    This solves the annotation problem: databases say "biosynthesis" or "chemosynth"
    which tells you nothing. This module produces:
    - What the microbe ACTUALLY does in the host
    - Which metabolites it produces/consumes
    - Host interaction mechanism
    - Disease relevance
    - Whether it's been studied in humans
    """
    if not gene_ids:
        return {"error": "No gene IDs provided"}
    
    prompt = f"""You are a world-leading microbiome bioinformatician specialising in functional annotation of microbial genes.

PROBLEM STATEMENT:
Standard microbiome functional annotation databases (KEGG, GO, COG, InterPro) provide extremely generic annotations. When you sequence a microbiome and annotate functions, you get terms like "biosynthesis", "chemosynthesis", "protein aggregation", "metabolic process" — these tell researchers NOTHING about what the microbe actually does in the host.

YOUR TASK:
For each of the following gene IDs, provide a detailed, biologically meaningful annotation that goes beyond the database label. Base your answer on published literature and known microbial biology.

Gene IDs / Functional Annotations:
{chr(10).join(f"- {g}" for g in gene_ids[:20])}

{f"Research context: {context}" if context else ""}
{f"Lab focus: {lab_focus}" if lab_focus else ""}

For each gene/function, provide:
1. **True biological function**: What does this gene/pathway actually DO in the host-microbiome context?
2. **Metabolite produced/consumed**: Specific metabolites, not vague "metabolic products"
3. **Host interaction**: How does this affect the host? (immune modulation, epithelial barrier, neurotransmitter, etc.)
4. **Key organisms**: Which bacteria carry this? (genus/species level)
5. **Disease relevance**: Associated with which human conditions? With what direction of effect?
6. **Evidence quality**: Is this well-established or inferred from model organisms?
7. **Research gap**: What is not yet known that would be valuable?

CRITICAL RULES:
- Never use vague terms: "biosynthesis", "metabolism", "process" without being specific
- Always name the specific metabolite, receptor, or pathway
- If you are uncertain, say so — do not hallucinate specific citations
- Ground everything in human microbiome context (not just mouse models)

Respond in JSON format:
{{"annotations": [{{"id": "gene_id", "true_function": "...", "metabolite": "...", "host_interaction": "...", "key_organisms": ["..."], "disease_relevance": "...", "evidence_quality": "high/medium/low", "research_gap": "..."}}]}}"""

    try:
        client = _get_anthropic_client()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}]
        )
        # Extract text from response
        text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                text += block.text
        # Parse JSON
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        return {"raw": text, "annotations": []}
    except Exception as e:
        return {"error": str(e), "annotations": []}

def annotate_microbe_taxonomy_llm(taxon_name: str, context: str = "") -> dict:
    """
    Given a microbe name/taxon, generate a comprehensive biological narrative:
    - What does this organism do in the human gut?
    - What metabolites does it produce?
    - Host immune modulation
    - Association with health/disease states
    - Interaction with other microbiome members
    """
    prompt = f"""You are an expert microbiologist specialising in host-microbiome interactions.

Provide a comprehensive biological profile of: {taxon_name}

{f"Research context: {context}" if context else ""}

Structure your response as JSON:
{{
  "organism": "{taxon_name}",
  "classification": "phylum, class, order, family, genus",
  "gram_status": "positive/negative/neither",
  "metabolism": "aerobic/anaerobic/facultative",
  "key_functions": [
    "specific function 1 — NOT vague terms like biosynthesis",
    "specific function 2"
  ],
  "metabolites_produced": ["butyrate", "indole", "etc — specific molecules"],
  "metabolites_consumed": ["specific substrates"],
  "host_receptor_interactions": ["specific receptors/pathways"],
  "immune_modulation": "specific effect on host immunity",
  "gut_niche": "where in gut, what conditions favour it",
  "disease_associations": [
    {{"condition": "name", "direction": "increased/decreased", "evidence": "strong/moderate/weak"}}
  ],
  "health_associations": ["specific health benefits with mechanism"],
  "key_species_variants": ["strain-level differences if important"],
  "therapeutic_potential": "probiotic/drug target/biomarker/none",
  "annotation_confidence": "high/medium/low",
  "key_papers": ["Author et al. Year — finding"]
}}

CRITICAL: Every function must be SPECIFIC. 'Biosynthesis' alone is unacceptable — state WHAT is synthesised and WHY it matters for the host."""

    try:
        client = _get_anthropic_client()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        text = "".join(block.text for block in response.content if hasattr(block, 'text'))
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except: pass
        return {"raw": text}
    except Exception as e:
        return {"error": str(e)}

def parse_functional_annotation_file(text: str) -> list:
    """
    Parse a functional annotation file (COG, KEGG, GO format).
    Returns list of IDs for LLM reannotation.
    """
    ids = []
    lines = text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"): continue
        # Match COG IDs: COG0001
        cog = re.findall(r'COG\d{4}', line)
        ids.extend(cog)
        # Match KEGG KO IDs: K00001
        ko = re.findall(r'K\d{5}', line)
        ids.extend(ko)
        # Match GO terms: GO:0001234
        go = re.findall(r'GO:\d{7}', line)
        ids.extend(go)
        # Match InterPro: IPR001234
        ipr = re.findall(r'IPR\d{6}', line)
        ids.extend(ipr)
        # If no IDs found, take the whole line as a functional term
        if not any([cog, ko, go, ipr]) and len(line) > 3:
            ids.append(line[:80])
    return list(dict.fromkeys(ids))[:30]  # deduplicate, max 30

def pathway_annotation_analysis(pathways: list, lab_context: str = "") -> dict:
    """
    Takes a list of pathway names/IDs from metagenome analysis
    and explains what they mean for the biological system being studied.
    """
    if not pathways:
        return {}
    
    prompt = f"""A metagenome analysis produced these functional pathway annotations:
{chr(10).join(f"- {p}" for p in pathways[:20])}

{f"Research context: {lab_context}" if lab_context else ""}

For each pathway, explain in plain biology what this means for the MICROBIOME COMMUNITY, not just the individual gene. Consider:
- Community-level metabolism: what is the community doing collectively?
- Cross-feeding relationships between community members
- End-products that reach the host
- What pathways being ABUNDANT vs DEPLETED means for host health

Respond as JSON:
{{"pathway_summary": "Overall biological interpretation of this community's function profile",
  "dominant_processes": ["specific process 1 with biological meaning", "process 2"],
  "key_metabolites_predicted": ["{{'metabolite': 'name', 'source_pathway': 'pathway', 'host_effect': 'specific effect'}}"],
  "health_implications": "specific health/disease relevance",
  "missing_functions": "what functional capacities this community lacks",
  "research_priorities": ["what to measure next", "what experiments would test this"]}}"""
    
    try:
        client = _get_anthropic_client()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        text = "".join(block.text for block in response.content if hasattr(block, 'text'))
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except: pass
        return {"raw": text}
    except Exception as e:
        return {"error": str(e)}

# ============ ASSAY ANALYSIS ============
# _client() merged above
def _client_UNUSED():
    key = None
    try: key = st.secrets.get("ANTHROPIC_API_KEY") or st.secrets.get("anthropic_api_key")
    except: pass
    if not key: key = os.environ.get("ANTHROPIC_API_KEY","")
    return anthropic.Anthropic(api_key=key) if key else None

def detect_assay_type(df: pd.DataFrame, filename: str = "") -> str:
    """Auto-detect the type of assay data from column names and filename."""
    cols = " ".join(df.columns.astype(str)).lower()
    fname = filename.lower()

    if any(x in cols for x in ["deltacp","delta ct","dct","ct value","cq"]): return "qpcr"
    if any(x in cols for x in ["tm","melting temperature","fluorescence","rfu","delta f"]): return "tsf_dsf"
    if any(x in cols for x in ["absorbance","od450","optical density","elisa"]): return "elisa"
    if any(x in cols for x in ["intensity","band","kda","molecular weight"]): return "western"
    if any(x in cols for x in ["log2fc","log2foldchange","padj","pvalue","basemean"]): return "rnaseq"
    if any(x in cols for x in ["peptide","protein group","razor","lfq intensity","ms/ms"]): return "proteomics"
    if any(x in cols for x in ["otu","asv","taxon","species","genus","phylum","16s"]): return "16s_microbiome"
    if any(x in cols for x in ["scfa","butyrate","propionate","acetate","tmao","metabolite"]): return "metabolomics"
    if any(x in cols for x in ["ic50","ec50","ki","kd","hill"]): return "binding_kinetics"
    if any(x in cols for x in ["rfu/s","kcat","km","vmax","velocity"]): return "enzyme_kinetics"
    if "western" in fname or "blot" in fname: return "western"
    if "elisa" in fname: return "elisa"
    if "16s" in fname or "microbiome" in fname or "otu" in fname: return "16s_microbiome"
    if "rnaseq" in fname or "deseq" in fname: return "rnaseq"
    return "generic"

def analyse_tsf_dsf(df: pd.DataFrame, gene: str = "", lab_context: str = "") -> dict:
    """Analyse Thermal Shift Assay (TSF/DSF) data — Tm comparison WT vs variants."""
    results = {}
    # Try to find Tm column
    tm_col = next((c for c in df.columns if any(x in c.lower() for x in ["tm","melting","temp"])), None)
    sample_col = next((c for c in df.columns if any(x in c.lower() for x in ["sample","name","protein","variant","condition"])), None)

    if tm_col and sample_col:
        df[tm_col] = pd.to_numeric(df[tm_col], errors="coerce")
        grouped = df.groupby(sample_col)[tm_col].agg(["mean","std","count"]).reset_index()

        # Find WT / reference
        wt_row = grouped[grouped[sample_col].str.lower().str.contains("wt|wild|control|ref", na=False)]
        wt_tm = float(wt_row["mean"].iloc[0]) if len(wt_row) > 0 else None

        fig = go.Figure()
        for _, row in grouped.iterrows():
            tm_val = row["mean"]; std_val = row["std"] if not pd.isna(row["std"]) else 0
            delta_tm = round(tm_val - wt_tm, 2) if wt_tm else None
            is_wt = "wt" in str(row[sample_col]).lower() or "control" in str(row[sample_col]).lower()
            # Classify
            if is_wt: color = "#00e5ff"; interpretation = "WT reference"
            elif delta_tm is not None:
                if delta_tm <= -2.0: color = "#ff2d55"; interpretation = f"ΔTm {delta_tm}°C — structurally destabilising → pharmacochaperone screen"
                elif delta_tm >= 2.0: color = "#00c896"; interpretation = f"ΔTm +{delta_tm}°C — stabilised (hit compound or stabilising variant)"
                else: color = "#ffd60a"; interpretation = f"ΔTm {delta_tm}°C — marginal change; functional mechanism likely"
            else: color = "#5a8090"; interpretation = "No WT reference for comparison"

            fig.add_trace(go.Bar(x=[str(row[sample_col])], y=[tm_val],
                                  error_y=dict(type="data", array=[std_val]),
                                  marker_color=color, name=str(row[sample_col]),
                                  hovertemplate=f"{row[sample_col]}<br>Tm: {tm_val:.1f}°C<br>{interpretation}<extra></extra>"))

        if wt_tm:
            fig.add_hline(y=wt_tm, line_dash="dash", line_color="#00e5ff",
                          annotation_text=f"WT Tm={wt_tm:.1f}°C", annotation_font_color="#00e5ff")

        fig.update_layout(height=350, plot_bgcolor="#010306", paper_bgcolor="#010306",
                          font=dict(color="#d0e8ff",size=11), margin=dict(l=40,r=20,t=40,b=80),
                          title=dict(text=f"Thermal Shift Assay (DSF) — {gene or 'Protein'} WT vs Variants",font=dict(color="#a855f7",size=12)),
                          xaxis=dict(title="Sample",gridcolor="#0d2545",tickangle=45),
                          yaxis=dict(title="Melting temperature (°C)",gridcolor="#0d2545"),
                          showlegend=False)
        results["figure"] = fig
        results["wt_tm"] = wt_tm
        results["grouped"] = grouped
    return results

def analyse_rnaseq(df: pd.DataFrame, gene: str = "", lab_context: str = "") -> dict:
    """Analyse RNA-seq differential expression results."""
    # Find key columns
    lfc_col = next((c for c in df.columns if "log2" in c.lower() and "fold" in c.lower()), None)
    pval_col = next((c for c in df.columns if "padj" in c.lower() or "fdr" in c.lower() or "p_adj" in c.lower()), None)
    gene_col = next((c for c in df.columns if any(x in c.lower() for x in ["gene","symbol","name"])), df.columns[0] if len(df.columns)>0 else None)

    if not lfc_col or not pval_col:
        return {"error": "Could not identify log2FC or adjusted p-value columns. Expected columns containing 'log2', 'fold', 'padj', or 'fdr'."}

    df[lfc_col] = pd.to_numeric(df[lfc_col], errors="coerce")
    df[pval_col] = pd.to_numeric(df[pval_col], errors="coerce")
    df = df.dropna(subset=[lfc_col, pval_col])

    # Classify
    df["neg_log_p"] = -np.log10(df[pval_col].clip(lower=1e-300))
    df["sig"] = ((df[pval_col] < 0.05) & (df[lfc_col].abs() > 1))
    df["direction"] = df[lfc_col].apply(lambda x: "Up" if x>1 else ("Down" if x<-1 else "NS"))

    up = (df["sig"] & (df[lfc_col]>0)).sum()
    down = (df["sig"] & (df[lfc_col]<0)).sum()

    # Volcano plot
    colors = {"Up":"#ff2d55","Down":"#4a90d9","NS":"#3a5a7a"}
    fig = px.scatter(df, x=lfc_col, y="neg_log_p", color="direction",
                     color_discrete_map=colors, hover_name=gene_col if gene_col else None,
                     labels={lfc_col:"log₂ Fold Change", "neg_log_p":"-log₁₀(adj. p-value)"},
                     title=f"Volcano Plot — DEGs (up: {up}, down: {down})")
    fig.add_hline(y=-np.log10(0.05), line_dash="dash", line_color="#ffd60a")
    fig.add_vline(x=1, line_dash="dash", line_color="#ffd60a")
    fig.add_vline(x=-1, line_dash="dash", line_color="#ffd60a")
    fig.update_layout(height=400, plot_bgcolor="#010306", paper_bgcolor="#010306",
                      font=dict(color="#d0e8ff",size=11), margin=dict(l=40,r=20,t=40,b=40))

    # Top hits
    top_up = df[df["sig"]&(df[lfc_col]>0)].nlargest(10, lfc_col)
    top_dn = df[df["sig"]&(df[lfc_col]<0)].nsmallest(10, lfc_col)

    return {"figure":fig, "n_up":int(up), "n_down":int(down), "top_up":top_up, "top_down":top_dn, "df":df}

def analyse_16s_microbiome(df: pd.DataFrame, lab_context: str = "") -> dict:
    """Analyse 16S OTU/ASV table — diversity, relative abundance, key taxa."""
    # Find taxonomy column
    tax_col = next((c for c in df.columns if any(x in c.lower() for x in ["taxon","taxonomy","species","genus","phylum","otu","asv"])), df.columns[0])
    # Numeric columns = samples
    num_cols = [c for c in df.columns if c != tax_col and pd.to_numeric(df[c], errors="coerce").notna().sum() > 0]

    if not num_cols:
        return {"error": "Could not identify sample abundance columns."}

    df_num = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    total_per_sample = df_num.sum()
    rel_abund = df_num.div(total_per_sample, axis=1) * 100

    # Top 10 taxa
    df["mean_rel_abund"] = rel_abund.mean(axis=1)
    top10 = df.nlargest(10, "mean_rel_abund")

    fig = px.bar(top10, x=tax_col, y="mean_rel_abund",
                 title="Top 10 Taxa — Mean Relative Abundance (%)",
                 labels={"mean_rel_abund": "Mean Relative Abundance (%)"},
                 color="mean_rel_abund", color_continuous_scale="Viridis")
    fig.update_layout(height=380, plot_bgcolor="#010306", paper_bgcolor="#010306",
                      font=dict(color="#d0e8ff",size=11), xaxis_tickangle=45,
                      coloraxis_showscale=False)

    # Alpha diversity (Shannon)
    def shannon(row):
        p = row[row>0]/row.sum()
        return -sum(p*np.log(p)) if len(p)>0 else 0
    alpha_div = rel_abund.apply(shannon, axis=0)

    taxa_list = top10[tax_col].tolist()
    return {"figure":fig, "top_taxa":taxa_list, "alpha_diversity":alpha_div.to_dict(), "n_taxa":len(df), "n_samples":len(num_cols)}

def analyse_with_llm(df: pd.DataFrame, assay_type: str, gene: str = "", lab_context: str = "", extra_context: str = "") -> str:
    """Use Claude to interpret assay results in context of the protein/gene being studied."""
    # Prepare data summary for LLM
    summary = f"Assay type: {assay_type}\n"
    summary += f"Dimensions: {df.shape[0]} rows × {df.shape[1]} columns\n"
    summary += f"Columns: {list(df.columns)}\n"
    summary += f"First 5 rows:\n{df.head().to_string()}\n"
    summary += f"Statistical summary:\n{df.describe().to_string()}\n"

    prompt = f"""You are a senior biomedical scientist interpreting laboratory assay data.

Gene/protein being studied: {gene or 'Unknown'}
Lab research context: {lab_context or 'General biomedical research'}
{f"Additional context: {extra_context}" if extra_context else ""}

Assay data summary:
{summary}

Provide a rigorous scientific interpretation:

1. **Data quality assessment**: Are the results technically valid? Any red flags (CV% too high, control failures)?
2. **Key findings**: What does this data tell us about {gene or 'the protein'} function?
3. **Statistical interpretation**: What conclusions can be drawn with what confidence level?
4. **Biological interpretation**: What does this mean mechanistically?
5. **Next experiments**: What is the logical follow-on experiment based on these results?
6. **Potential issues**: What technical artefacts or confounders could affect these results?
7. **ClinVar relevance**: How do these findings relate to known disease-causing variants (if applicable)?

Be specific — avoid vague statements like "results suggest a role in" — state exactly what is shown and what it means.
Note any statistical issues without being asked."""

    try:
        client = _get_anthropic_client()
        if not client: return "AI analysis unavailable — add ANTHROPIC_API_KEY to Streamlit Secrets."
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role":"user","content":prompt}]
        )
        return "".join(block.text for block in response.content if hasattr(block,"text"))
    except Exception as e:
        return f"AI analysis unavailable: {str(e)}"

def render_assay_analysis_tab(gene: str, color: str, lab_profile: dict = None):
    """Full assay data analysis tab."""
    lab_context = ""
    if lab_profile:
        lab_context = f"{lab_profile.get('lab_name','')}: {lab_profile.get('research_goal','')}"

    st.markdown("<div style='color:#5a8090;font-size:.82rem;margin-bottom:.8rem'>Upload wet-lab or dry-lab assay data for AI-assisted interpretation. Supported: TSA/DSF, western blot densitometry, RNA-seq DEG tables, 16S OTU tables, ELISA, proteomics, metabolomics, binding kinetics.</div>", unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload assay data (CSV, TSV, Excel)", type=["csv","tsv","xlsx","xls"], key=f"assay_upload_{gene}")

    if uploaded:
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            elif uploaded.name.endswith(".tsv"):
                df = pd.read_csv(uploaded, sep="\t")
            else:
                df = pd.read_excel(uploaded)

            assay_type = detect_assay_type(df, uploaded.name)
            st.markdown(f"<div style='background:#040c14;border:1px solid {color}44;border-radius:8px;padding:.5rem 1rem;margin-bottom:.5rem'><span style='color:{color};font-weight:600'>Detected assay type:</span> <span style='color:#d0e8ff'>{assay_type.replace('_',' ').upper()}</span> &nbsp; ({df.shape[0]} rows, {df.shape[1]} columns)</div>", unsafe_allow_html=True)

            override = st.selectbox("Override assay type:", ["Auto-detected","tsf_dsf","western","elisa","rnaseq","16s_microbiome","proteomics","metabolomics","binding_kinetics","generic"], key=f"assay_type_{gene}")
            if override != "Auto-detected": assay_type = override

            with st.expander("📋 Preview data", expanded=False):
                st.dataframe(df.head(10), use_container_width=True)

            if assay_type == "tsf_dsf":
                result = analyse_tsf_dsf(df, gene, lab_context)
                if result.get("figure"): st.plotly_chart(result["figure"], use_container_width=True)
                if result.get("grouped") is not None:
                    st.markdown("<div style='color:#5a8090;font-size:.78rem;font-weight:600;margin:.4rem 0'>Interpretation guide: ΔTm ≤-2°C = structurally destabilising → pharmacochaperone screen. ΔTm ≥2°C = stabilised compound hit.</div>", unsafe_allow_html=True)

            elif assay_type == "rnaseq":
                result = analyse_rnaseq(df, gene, lab_context)
                if "error" in result: st.error(result["error"])
                else:
                    st.plotly_chart(result["figure"], use_container_width=True)
                    c1,c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Top upregulated genes ({result['n_up']} total)**")
                        if not result["top_up"].empty: st.dataframe(result["top_up"].head(8), use_container_width=True)
                    with c2:
                        st.markdown(f"**Top downregulated genes ({result['n_down']} total)**")
                        if not result["top_down"].empty: st.dataframe(result["top_down"].head(8), use_container_width=True)

            elif assay_type == "16s_microbiome":
                result = analyse_16s_microbiome(df, lab_context)
                if "error" in result: st.error(result["error"])
                else:
                    st.plotly_chart(result["figure"], use_container_width=True)
                    st.markdown(f"**Total taxa:** {result['n_taxa']} · **Samples:** {result['n_samples']}")

            else:
                st.dataframe(df.describe(), use_container_width=True)

            # AI interpretation
            st.markdown("---")
            extra_ctx = st.text_area("Additional experimental context for AI analysis (optional)", placeholder="e.g. 'Cells were treated with 10µM of compound X for 24h before lysis. Western probed with anti-pSer2152 antibody.'", key=f"extra_ctx_{gene}", height=80)
            if st.button("🤖 AI Interpret Results", key=f"ai_assay_{gene}", type="primary"):
                with st.spinner("Claude is interpreting your assay data..."):
                    interpretation = analyse_with_llm(df, assay_type, gene, lab_context, extra_ctx)
                st.markdown("<div style='background:#020d10;border:1px solid #00e5ff33;border-radius:10px;padding:1rem 1.2rem;margin-top:.5rem'>", unsafe_allow_html=True)
                st.markdown(interpretation)
                st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error reading file: {e}")


def render_auth_page():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');
*{font-family:'Space Grotesk',sans-serif}
#MainMenu,footer,header{display:none!important}
[data-testid="stAppViewContainer"]{background:#010306}
.block-container{padding:2rem 1rem!important;max-width:480px!important;margin:0 auto}
.stTextInput>div>div>input{background:#030810!important;border:1px solid #0d2545!important;color:#d0e8ff!important;border-radius:8px!important;font-size:.9rem!important}
.stButton>button{background:#00e5ff!important;color:#010306!important;font-weight:700!important;border:none!important;border-radius:8px!important;width:100%!important;padding:.5rem!important;font-size:.9rem!important}
.stRadio label{color:#5a8090!important;font-size:.85rem!important}
@keyframes pulse{0%,100%{opacity:.4;transform:scale(.97)}50%{opacity:1;transform:scale(1.03)}}
@keyframes fadeUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
</style>
""", unsafe_allow_html=True)
    st.markdown("""
<div style='text-align:center;padding:2.5rem 0 1.5rem;animation:fadeUp .8s ease both'>
  <div style='font-size:3rem;animation:pulse 3s infinite'>🔬</div>
  <div style='font-size:2.4rem;font-weight:700;color:#00e5ff;letter-spacing:-.03em;margin:.4rem 0'>Protellect</div>
  <div style='font-size:.75rem;color:#3a6080;letter-spacing:.1em;text-transform:uppercase'>Biology Intelligence Platform</div>
  <div style='width:40px;height:2px;background:#00e5ff;margin:.8rem auto;animation:pulse 2s infinite'></div>
</div>""", unsafe_allow_html=True)
    mode = st.radio("", ["Sign In", "Create Account"], horizontal=True, label_visibility="collapsed")
    if mode == "Sign In":
        email = st.text_input("Email", placeholder="you@lab.com", key="login_email")
        password = st.text_input("Password", type="password", key="login_pw")
        if st.button("Sign In ->", key="signin_btn"):
            ok, msg = login(email.strip(), password)
            if ok: st.success("Welcome back!"); st.rerun()
            else: st.error(msg)
        st.markdown("<div style='color:#3a6080;font-size:.75rem;text-align:center;margin-top:.5rem'>Demo: demo@protellect.com / protellect2024</div>", unsafe_allow_html=True)
    else:
        name  = st.text_input("Full name", placeholder="Dr. Jane Smith", key="reg_name")
        email = st.text_input("Email", placeholder="you@lab.com", key="reg_email")
        pw    = st.text_input("Password (8+ chars)", type="password", key="reg_pw")
        if st.button("Create Account ->", key="register_btn"):
            ok, msg = register(email.strip(), pw, name.strip())
            if ok: st.success("Account created!"); st.rerun()
            else: st.error(msg)

# ============ MAIN APP ============


st.set_page_config(page_title="Protellect",page_icon=":microscope:",layout="wide",initial_sidebar_state="collapsed")

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
*{font-family:'Space Grotesk',sans-serif;box-sizing:border-box}
code,.mono{font-family:'JetBrains Mono',monospace}
#MainMenu,footer,header,[data-testid="stDeployButton"]{display:none!important}
[data-testid="stSidebar"]{background:#030810!important;border-right:1px solid #0d2545!important}
.block-container{padding:0!important;max-width:100%!important}
[data-testid="stAppViewContainer"]{background:#010306}
div[data-testid="metric-container"]{background:#070d1a;border:1px solid #0d2545;border-radius:11px;padding:.75rem}
div[data-testid="metric-container"] label{color:#3a6080!important;font-size:.68rem!important;letter-spacing:.07em!important;text-transform:uppercase!important}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{color:#00e5ff!important;font-size:1.35rem!important;font-weight:600!important}
.stTabs [data-baseweb="tab-list"]{gap:2px;background:#030810;border-radius:10px;padding:3px;border:1px solid #0d2545}
.stTabs [data-baseweb="tab"]{background:transparent;color:#3a6080;border-radius:7px;font-size:.75rem;padding:.28rem .75rem;font-weight:500}
.stTabs [aria-selected="true"]{background:#0d2545!important;color:#00e5ff!important}
.stButton>button{background:transparent;border:1px solid #0d2545;color:#d0e8ff;font-size:.78rem;border-radius:8px;font-weight:500;transition:all .2s;padding:.28rem .75rem}
.stButton>button:hover{border-color:#00e5ff44;color:#00e5ff;background:#00e5ff08}
.stButton>button[kind="primary"]{background:#00e5ff!important;color:#010306!important;border:none!important;font-weight:600!important}
.stTextInput>div>div>input,.stSelectbox>div>div,.stTextArea textarea{background:#030810!important;border:1px solid #0d2545!important;color:#d0e8ff!important;border-radius:8px!important}
.stExpander{border:1px solid #0d2545!important;border-radius:10px!important;background:#040c14!important;margin-bottom:.28rem!important}
.stFileUploader{background:#030810;border:1px dashed #0d2545;border-radius:10px;padding:.5rem}
h1,h2,h3{color:#d0e8ff!important}
a{color:#00e5ff!important;text-decoration:none!important}
@keyframes fadeUp{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:.4;transform:scale(.98)}50%{opacity:1;transform:scale(1.02)}}
@keyframes glow{0%,100%{box-shadow:0 0 20px #00e5ff22}50%{box-shadow:0 0 50px #00e5ff55}}
@keyframes rotateDNA{0%{transform:rotate(0deg) scale(1)}50%{transform:rotate(180deg) scale(1.1)}100%{transform:rotate(360deg) scale(1)}}
@keyframes scanline{0%{top:-10px}100%{top:100%}}
</style>"""
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ── helpers ─────────────────────────────────────────────────────────────────────
def sh(icon,title,color="#00e5ff"):
    st.markdown(f"<div style='display:flex;align-items:center;gap:8px;margin:.8rem 0 .35rem'><span style='font-size:.9rem'>{icon}</span><span style='color:{color};font-weight:600;font-size:.88rem;letter-spacing:-.01em'>{title}</span></div>",unsafe_allow_html=True)

def badge(text,color="#00e5ff"):
    return f"<span style='background:{color}18;color:{color};font-size:.67rem;padding:2px 8px;border-radius:7px;border:1px solid {color}44;font-weight:600'>{text}</span>"

def warn_box(title,body):
    st.markdown(f"<div style='background:#0a0205;border:1px solid #ff2d5544;border-radius:9px;padding:.6rem .9rem;margin:.25rem 0'><div style='color:#ff2d55;font-weight:600;font-size:.76rem;margin-bottom:2px'>{title}</div><div style='color:#6a3040;font-size:.76rem;line-height:1.6'>{body}</div></div>",unsafe_allow_html=True)

def info_box(body,color="#00e5ff"):
    st.markdown(f"<div style='background:{color}0a;border:1px solid {color}33;border-radius:9px;padding:.6rem .9rem;margin:.25rem 0'><div style='color:{color};font-size:.8rem;line-height:1.7'>{body}</div></div>",unsafe_allow_html=True)

def tier_badge(t): c=TIER_MAP.get(t,{}).get("color","#3a5a7a"); return badge(t,c)

def src_link(label,url):
    return f"<a href='{url}' target='_blank' style='display:inline-flex;align-items:center;gap:3px;font-size:.68rem;color:#00e5ff;background:#00e5ff0d;border:1px solid #00e5ff33;border-radius:6px;padding:2px 7px;margin:2px'>{label} ↗</a>"

# ── session init ────────────────────────────────────────────────────────────────
for k,v in [("domain",None),("subdomain",None),("onboarding_done",False),("lab_profile",None),("analysis_cache",{})]:
    if k not in st.session_state: st.session_state[k]=v

# ── auth gate ───────────────────────────────────────────────────────────────────
if not is_logged_in():
    render_auth_page(); st.stop()

u = current_user()

# ── onboarding ──────────────────────────────────────────────────────────────────
def render_onboarding():
    st.markdown("""
    <div style='min-height:100vh;display:flex;align-items:center;justify-content:center;padding:2rem'>
    <div style='max-width:600px;width:100%;animation:fadeUp .8s ease both'>""", unsafe_allow_html=True)

    # Animated logo
    st.markdown("""
    <div style='text-align:center;margin-bottom:2rem'>
      <div style='position:relative;width:90px;height:90px;margin:0 auto .8rem;display:flex;align-items:center;justify-content:center'>
        <div style='position:absolute;width:90px;height:90px;border:2px solid #00e5ff33;border-radius:50%;animation:pulse 3s infinite'></div>
        <div style='position:absolute;width:70px;height:70px;border:1px solid #00e5ff22;border-radius:50%;animation:pulse 3s infinite .5s'></div>
        <div style='font-size:2.5rem;animation:rotateDNA 8s linear infinite'>🔬</div>
      </div>
      <div style='font-size:2.4rem;font-weight:700;color:#00e5ff;letter-spacing:-.03em'>Protellect</div>
      <div style='font-size:.8rem;color:#3a6080;letter-spacing:.1em;text-transform:uppercase'>Biology Intelligence Platform</div>
      <div style='width:50px;height:2px;background:linear-gradient(90deg,transparent,#00e5ff,transparent);margin:.8rem auto;animation:pulse 2s infinite'></div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"<div style='text-align:center;color:#5a8090;font-size:.85rem;margin-bottom:1.5rem'>Welcome, <b style='color:#d0e8ff'>{u.get('name','')}</b> — let's personalise your experience</div>", unsafe_allow_html=True)

    with st.form("onboarding_form"):
        st.markdown("<div style='color:#00e5ff;font-weight:600;font-size:.9rem;margin-bottom:.8rem'>Tell us about your lab</div>", unsafe_allow_html=True)

        lab_name = st.text_input("Lab / Institute name", placeholder="e.g. Smith Lab, Wellcome Sanger Institute", key="ob_lab")
        pi_name  = st.text_input("Principal Investigator name", placeholder="e.g. Prof. Jane Smith", key="ob_pi")
        lab_focus= st.text_area("What does your lab research?", placeholder="e.g. We study GPCR signalling in cardiac disease, focusing on filamin phosphorylation and arrhythmia mechanisms...", height=100, key="ob_focus")
        domain_pref = st.selectbox("Primary domain of interest", ["Neuroscience & Pharma","Oncology","Proteins & Structural Biology","Microbiome","All domains equally"], key="ob_domain")
        organisms = st.multiselect("Organisms you work with", ["Human","Mouse","Zebrafish","C. elegans","Drosophila","E. coli","Yeast","Gut bacteria/microbiome","In vitro only"], default=["Human"], key="ob_org")
        assay_types = st.multiselect("Primary assay types", ["Western blot","CRISPR knock-in/out","RNA-seq","16S microbiome","Mass spectrometry","BRET/FRET","SPR/ITC binding","Flow cytometry","Patch clamp","In vivo mouse","Computational/dry-lab only"], key="ob_assays")
        budget = st.select_slider("Lab budget for new experiments", ["<$10K","$10K–50K","$50K–200K","$200K–1M",">$1M"], value="$50K–200K", key="ob_budget")
        pi_pubmed = st.text_input("PI PubMed search term (to pull your lab's papers)", placeholder="e.g. Smith J[au] GPCR OR Smith Jane filamin", key="ob_pubmed")

        submitted = st.form_submit_button("Begin Research →", type="primary", use_container_width=True)
        if submitted:
            if not lab_name or not lab_focus:
                st.error("Please provide at least a lab name and research focus.")
            else:
                save_lab_profile({
                    "lab_name": lab_name, "pi_name": pi_name, "research_focus": lab_focus,
                    "domain_pref": domain_pref, "organisms": organisms, "assay_types": assay_types,
                    "budget": budget, "pi_pubmed_query": pi_pubmed
                })
                st.rerun()

    st.markdown("</div></div>", unsafe_allow_html=True)

if not st.session_state.onboarding_done and not u.get("onboarded"):
    render_onboarding(); st.stop()

lab = st.session_state.lab_profile or u.get("lab_profile") or {}

# ── domain splash ───────────────────────────────────────────────────────────────
DOMAINS_META = {
    "neuro":{"label":"Neuroscience & Pharma","icon":"🧠","color":"#a855f7","tagline":"Alzheimer's · Parkinson's · Epilepsy · ALS · Psychiatry · BBB"},
    "onco":{"label":"Oncology","icon":"🎗️","color":"#ff2d55","tagline":"Somatic mutations · Immunotherapy · ADCs · Liquid biopsy · Resistance"},
    "proteins":{"label":"Proteins & Structural","icon":"🧬","color":"#00e5ff","tagline":"AlphaFold · AlphaMissense · Kinases · GPCRs · FBM-Filamin · PTMs"},
    "microbiome":{"label":"Microbiome","icon":"🦠","color":"#00c896","tagline":"AI functional annotation · TMAO · FMT · Host-microbe · Pathway reannotation"},
}

def render_splash():
    # Animated logo
    st.markdown("""
    <div style='text-align:center;padding:3rem 1rem 1.5rem;animation:fadeUp .7s ease both'>
      <div style='position:relative;width:80px;height:80px;margin:0 auto .6rem;display:flex;align-items:center;justify-content:center'>
        <div style='position:absolute;inset:0;border:2px solid #00e5ff33;border-radius:50%;animation:glow 3s infinite'></div>
        <span style='font-size:2.2rem'>🔬</span>
      </div>
      <div style='font-size:2.6rem;font-weight:700;color:#00e5ff;letter-spacing:-.03em'>Protellect</div>
      <div style='font-size:.78rem;color:#3a6080;letter-spacing:.1em;text-transform:uppercase;margin:.2rem 0'>Biology Intelligence Platform</div>
      <div style='width:50px;height:2px;background:linear-gradient(90deg,transparent,#00e5ff,transparent);margin:.8rem auto;animation:pulse 2s infinite'></div>
    </div>""", unsafe_allow_html=True)

    if lab.get("lab_name"):
        st.markdown(f"<div style='text-align:center;color:#3a6080;font-size:.82rem;margin-bottom:1.5rem'>Welcome back, <b style='color:#d0e8ff'>{lab['lab_name']}</b></div>", unsafe_allow_html=True)

    cols = st.columns(4, gap="medium")
    for i,(col,(key,D)) in enumerate(zip(cols, DOMAINS_META.items())):
        with col:
            # Highlight recommended domain based on lab profile
            lab_dom = lab.get("domain_pref","")
            is_rec = D["label"].lower() in lab_dom.lower() if lab_dom and lab_dom!="All domains equally" else False
            border = f"border:2px solid {D['color']}88" if is_rec else "border:1px solid #0d2545"
            rec_badge = f"<div style='background:{D['color']}22;color:{D['color']};font-size:.65rem;padding:1px 7px;border-radius:6px;margin-bottom:.3rem'>Recommended for your lab</div>" if is_rec else ""
            st.markdown(
                f"<div style='background:#040c14;{border};border-radius:16px;padding:1.5rem 1rem;text-align:center;animation:fadeUp {.6+i*.1}s ease both;margin-bottom:.4rem'>"
                f"{rec_badge}"
                f"<div style='font-size:2rem;margin-bottom:.4rem'>{D['icon']}</div>"
                f"<div style='color:{D['color']};font-weight:700;font-size:.88rem;margin-bottom:.2rem'>{D['label']}</div>"
                f"<div style='color:#2a4050;font-size:.7rem;line-height:1.5'>{D['tagline']}</div>"
                f"</div>", unsafe_allow_html=True)
            if st.button(f"Open {D['icon']}", key=f"open_{key}", use_container_width=True):
                st.session_state.domain = key; st.rerun()

    # Lab papers if PI name set
    if lab.get("pi_pubmed_query"):
        st.markdown("---")
        sh("📄","Your Lab's Recent Papers","#ffd60a")
        if st.button("Load lab papers", key="load_lab_papers"):
            with st.spinner("Fetching your lab's papers from PubMed..."):
                lab_papers = api_pubmed(lab["pi_pubmed_query"]+" 2020:2025[pdat]", 6)
            if lab_papers:
                for p in lab_papers:
                    pm_url = p.get("url","")
                    pm_id = p.get("pmid","")
                    st.markdown(f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:9px;padding:.6rem .9rem;margin-bottom:.25rem'><div style='color:#d0e8ff;font-size:.82rem;font-weight:500'>{p['title'][:80]}...</div><div style='color:#3a6080;font-size:.74rem'>{p['authors']} · {p['journal']} · {p['year']} · <a href='{pm_url}' target='_blank'>PMID {pm_id}</a></div></div>", unsafe_allow_html=True)
            else:
                st.info("No recent papers found. Adjust the PubMed search term in your lab profile.")

# ── SIDEBAR ─────────────────────────────────────────────────────────────────────
def render_sidebar(domain_key):
    D = DOMAINS_META[domain_key]; color = D["color"]
    with st.sidebar:
        st.markdown(f"<div style='color:{color};font-weight:700;font-size:.95rem;padding:.4rem 0'>🔬 Protellect</div>", unsafe_allow_html=True)
        if lab.get("lab_name"):
            st.markdown(f"<div style='color:#3a5060;font-size:.72rem;margin-bottom:.4rem'>{lab['lab_name']}</div>", unsafe_allow_html=True)
        st.markdown("---")
        gene_input = st.text_input("🔍 Gene / protein", placeholder="FLNC, EGFR, LRRK2, ARRB2...", key="gene_box")
        do_search  = st.button("Analyse ↗", use_container_width=True, key="search_btn", type="primary")
        
        # Search quota
        if u.get("plan","free") == "free":
            used = u.get("searches_used",0); mx = u.get("max_searches",10)
            st.markdown(f"<div style='color:#3a6080;font-size:.7rem;text-align:center'>{used}/{mx} searches used</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f"<div style='color:#3a6080;font-size:.68rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin-bottom:.3rem'>Quick Genes</div>", unsafe_allow_html=True)
        quick_genes = {
            "neuro":["APP","LRRK2","SNCA","GBA","SCN1A","DRD2","SOD1","MAPT","TREM2","KCNQ2"],
            "onco":["TP53","KRAS","BRCA1","EGFR","HER2","ALK","BRAF","PIK3CA","CDK4","FLT3"],
            "proteins":["FLNA","FLNC","ARRB2","EGFR","HSP90","GRK2","ADRB2","AGTR1","MDM2","PTEN"],
            "microbiome":["FXR","TLR4","NLRP3","GPR41","NOD2","FMO3","FUT2","CARD9","IL10","TGR5"],
        }.get(domain_key, [])
        for g in quick_genes[:10]:
            if st.button(g, key=f"qg_{g}", use_container_width=True):
                st.session_state["_run_gene"]=g; st.rerun()

        st.markdown("---")
        if st.button("← Domains", key="back", use_container_width=True):
            st.session_state.domain=None; st.rerun()
        if st.button(f"👤 {u.get('name','').split()[0] if u.get('name') else 'Profile'} · Sign Out", key="signout", use_container_width=True):
            logout(); st.rerun()

    return gene_input, do_search

# ── GENE ANALYSIS ────────────────────────────────────────────────────────────────
def render_gene_analysis(gene: str, domain_key: str):
    D = DOMAINS_META[domain_key]; color = D["color"]
    gene = gene.upper().strip()

    if not can_search():
        st.error("Search quota reached. Upgrade to Pro for unlimited searches.")
        return

    sh("🔎", f"Live Analysis — {gene}", color)
    with st.spinner(f"Fetching {gene} from 7 databases..."):
        pdata    = api_uniprot(gene)
        cv       = api_clinvar(gene)
        partners = api_string(gene)
        ot       = api_opentargets(gene)
        gnomad   = api_gnomad(gene)
        trials   = api_clinicaltrials(gene)
        af       = api_alphafold(pdata.get("uid","")) if pdata.get("uid") else {}
        am_data  = api_alphamissense(pdata.get("uid","")) if pdata.get("uid") else {}

    decrement_search()

    is_arrb = gene in ("ARRB1","ARRB2","BARR1","BARR2")
    gi = gi_score(cv, pdata.get("length",500) if pdata else 500)

    if is_arrb:
        st.markdown(
            f"<div style='background:#0a0205;border:2px solid #ff2d55;border-radius:12px;padding:1.1rem 1.4rem;margin-bottom:.7rem'>"
            f"<div style='color:#ff2d55;font-weight:700;font-size:1rem;margin-bottom:.25rem'>⛔ DEPRIORITISE — {gene}: $4,050,000 in avoidable spend</div>"
            f"<div style='color:#6a3040;font-size:.8rem;line-height:1.7'>ARRB1/ARRB2 double KO mice are viable and fertile. Zero confirmed Mendelian disease-causing variants in ClinVar. Beta-arrestin phosphorylation codes are kinase noise — no disease variant validates any phospho-site on ARRB proteins. Redirect investment to: Filamin A Ser2152-P assay ($2K) · ADRB1 · ADRB2 · AGTR1 · MAS1</div>"
            f"<div style='display:flex;gap:5px;flex-wrap:wrap;margin-top:.5rem'>"
            + "".join(f"<span style='background:#ff2d5511;border:1px solid #ff2d5533;border-radius:6px;padding:2px 9px;font-size:.7rem;color:#ff8c42'>${v:,} — {k}</span>"
                      for k,v in [("HTS screen",2500000),("CRISPR x6",150000),("Cryo-EM",500000),("Mouse x2",800000),("BRET screens",100000)])
            + "</div></div>", unsafe_allow_html=True)

    # Verdict banner
    gc = gi.get("color","#3a5a7a")
    af_link = f"<a href='{af.get('af_url','')}' target='_blank' style='font-size:.74rem;color:#a855f7;margin-left:auto'>AlphaFold ↗</a>" if af.get("af_url") else ""
    st.markdown(
        f"<div style='background:{gc}10;border:1px solid {gc}44;border-radius:11px;padding:.85rem 1.1rem;margin-bottom:.5rem'>"
        f"<div style='color:{gc};font-weight:700;font-size:.92rem'>{gi.get('icon','')} {gi.get('verdict','')}</div>"
        f"<div style='color:#5a8090;font-size:.78rem;margin-top:2px'>{gi.get('explanation','')}</div>"
        f"<div style='display:flex;gap:12px;margin-top:.4rem;align-items:center'>"
        f"<span style='font-size:.76rem;color:#3a6080'>P/LP: <b style='color:{gc}'>{gi.get('n',0)}</b></span>"
        f"<span style='font-size:.76rem;color:#3a6080'>Per 100 aa: <b style='color:{gc}'>{gi.get('per100',0)}</b></span>"
        f"<span style='font-size:.76rem;color:#3a6080'>CRITICAL: <b style='color:{gc}'>{gi.get('n_crit',0)}</b></span>"
        f"<span style='font-size:.76rem;color:#3a6080'>pLI: <b style='color:{gc}'>{gnomad.get('pLI','—')}</b></span>"
        f"{af_link}</div></div>", unsafe_allow_html=True)

    # Pull lab-relevant papers if PI name set
    lab_paper_note = ""
    if lab.get("pi_pubmed_query") and gene.upper() in (lab.get("research_focus","").upper()+"FLNA ADRB KRAS TP53"):
        lab_paper_note = f" · Your lab may have publications on {gene}"

    # Tab structure
    tabs = st.tabs(["🧬 Protein","🔬 Variants","🧠 AlphaMissense","⚙️ Pathways","💊 Drugs","🏥 Trials","📚 Literature","🧪 Experiments","📊 Assay Analysis"])
    t_prot, t_var, t_am, t_path, t_drugs, t_trials, t_lit, t_exp, t_assay = tabs

    with t_prot:
        c1,c2 = st.columns(2)
        with c1:
            if pdata.get("name"):
                st.markdown(f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:10px;padding:.75rem 1rem;margin-bottom:.4rem'>"
                            f"<div style='color:{color};font-weight:600;font-size:.88rem'>{pdata['name']}</div>"
                            f"<div style='color:#3a6080;font-size:.72rem'>{gene} · {pdata.get('length',0)} aa</div>"
                            f"<div style='color:#3a5060;font-size:.76rem;line-height:1.6;margin-top:.35rem'>{pdata.get('function','')[:400]}{'...' if len(pdata.get('function',''))>400 else ''}</div>"
                            f"</div>", unsafe_allow_html=True)
            for d in pdata.get("diseases",[])[:5]:
                st.markdown(f"<div style='padding:4px 0;border-bottom:1px solid #0d2545;font-size:.78rem'><span style='color:#d0e8ff'>{d['name']}</span><div style='color:#2a4050;font-size:.72rem'>{d.get('desc','')[:100]}</div></div>", unsafe_allow_html=True)
            if pdata.get("ptms"):
                sh("🔘","PTM data (UniProt)",color)
                for ptm in pdata["ptms"]: st.markdown(f"<div style='color:#5a8090;font-size:.76rem;padding:3px 0;border-bottom:1px solid #0d2545'>{ptm[:200]}</div>", unsafe_allow_html=True)
        with c2:
            if partners:
                sh("🕸️","STRING Interaction Partners ≥700",color)
                for p in partners:
                    st.markdown(f"<div style='display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #0d2545;font-size:.78rem'><span style='color:#d0e8ff'>{p['partner']}</span><span style='color:#00c896;font-size:.73rem'>Score {p['score']} · {p.get('mode','')}</span></div>", unsafe_allow_html=True)
            if gnomad:
                sh("📊","gnomAD Constraint",color); cc=st.columns(3)
                with cc[0]: st.metric("pLI",gnomad.get("pLI","—"))
                with cc[1]: st.metric("o/e LoF",gnomad.get("oe_lof","—"))
                with cc[2]: st.metric("o/e Mis",gnomad.get("oe_mis","—"))
            if ot.get("disease_assoc"):
                sh("🎯","Disease Associations — OpenTargets",color)
                for da in ot["disease_assoc"][:5]:
                    st.markdown(f"<div style='display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #0d2545;font-size:.78rem'><span style='color:#d0e8ff'>{da['name']}</span><span style='color:#ff8c42;font-size:.73rem'>{da['score']}</span></div>", unsafe_allow_html=True)
            if pdata.get("keywords"):
                sh("🏷️","Keywords",color)
                st.markdown(" ".join(badge(k,"#3a6080") for k in pdata["keywords"][:10]), unsafe_allow_html=True)

    with t_var:
        if is_arrb:
            warn_box("Disease triage suppressed","ClinVar entries for ARRB proteins reflect co-occurrence with GPCR-driven disease, not independent pathogenicity.")
        elif not cv:
            st.info("No P/LP variants in ClinVar for this gene.")
        else:
            sh("🔴",f"ClinVar — {len(cv)} Pathogenic/Likely Pathogenic Variants",color)
            info_box("ClinVar is the triage filter — not the truth source. Multi-star reviewed P/LP variants are the starting point. Superimpose onto drug structures or run functional assays to validate target engagement.",color)
            for v in cv[:20]:
                rc={"CRITICAL":"#ff2d55","HIGH":"#ff8c42","MODERATE":"#ffd60a","LOW":"#5a8090"}.get(v["ml_rank"],"#3a5a7a")
                with st.expander(f"{badge(v['ml_rank'],rc)} &nbsp; {v['title'][:68]}...",expanded=False):
                    st.markdown(f"{badge(v['cs'],'#4a90d9')} &nbsp; {'⭐'*v['stars'] if v['stars'] else '☆ No review'} &nbsp; <a href='{v['url']}' target='_blank' style='font-size:.72rem'>ClinVar ↗</a>",unsafe_allow_html=True)
                    if v.get("condition"): st.markdown(f"<div style='color:#5a8090;font-size:.76rem;margin-top:2px'>{v['condition'][:150]}</div>",unsafe_allow_html=True)

    with t_am:
        sh("🧠","AlphaMissense — DeepMind Per-Residue Pathogenicity",color)
        if am_data:
            render_alphamissense_chart(am_data, cv, color)
        else:
            st.info("AlphaMissense data not available. UniProt accession may not have an AlphaFold structure.")

        if pdata.get("ptms"):
            st.markdown("---")
            sh("🔘","Phosphorylation Signal vs Noise",color)
            render_phospho_network(gene, pdata.get("ptms",[]), cv)

    with t_path:
        sh("⚙️","Pathway & Signalling Analysis",color)
        t_kin, t_gpcr, t_chem = st.tabs(["Kinases & Phosphatases","GPCR Signalling","Chemical Structures"])
        with t_kin:
            render_kinase_phosphatase_panel(gene, color)
        with t_gpcr:
            render_gpcr_signalling_diagram(gene, color)
        with t_chem:
            sh("⚗️","Chemical Structure Lookup",color)
            compound = st.text_input("Drug/compound name", placeholder="e.g. imatinib, sotorasib, venetoclax", key=f"chem_{gene}")
            if compound:
                with st.spinner("Fetching from PubChem..."):
                    render_chemical_structure(compound)

    with t_drugs:
        if ot.get("drugs"):
            sh("💊","Known Drugs — OpenTargets",color)
            ph_l={4:"Approved",3:"Phase 3",2:"Phase 2",1:"Phase 1",0:"Preclinical"}; ph_c={4:"#00c896",3:"#4a90d9",2:"#ffd60a",1:"#5a8090",0:"#3a4050"}
            for drug in ot["drugs"]:
                ph=int(drug.get("phase",0) or 0)
                st.markdown(f"<div style='display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid #0d2545;font-size:.8rem'><span style='color:#d0e8ff'>{drug['name']}</span><span style='background:{ph_c.get(ph,'#3a4050')}22;color:{ph_c.get(ph,'#5a8090')};padding:2px 7px;border-radius:6px;font-size:.7rem'>{ph_l.get(ph,'?')}</span></div>", unsafe_allow_html=True)
        if ot.get("tractability"):
            sh("🎯","Tractability",color); st.markdown(" ".join(badge(t,"#00c896") for t in ot["tractability"]),unsafe_allow_html=True)
        if not ot.get("drugs") and not ot.get("tractability"): st.info("No drug data found.")

    with t_trials:
        sh("🏥","Active Recruiting Trials — ClinicalTrials.gov",color)
        if not trials: st.info("No actively recruiting trials found.")
        else:
            for tr in trials:
                ph_clr="#4a90d9" if "3" in tr.get("phase","") else "#ffd60a" if "2" in tr.get("phase","") else "#5a8090"
                st.markdown(f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:9px;padding:.6rem .85rem;margin-bottom:.25rem;display:flex;justify-content:space-between;align-items:center'><div style='flex:1'><a href='{tr['url']}' target='_blank' style='color:#d0e8ff;font-size:.8rem;font-weight:500'>{tr['title']}</a><div style='color:#2a4050;font-size:.71rem;margin-top:1px'>{tr['sponsor']} · {tr['nct']}</div></div><span style='background:{ph_clr}22;color:{ph_clr};padding:2px 7px;border-radius:6px;font-size:.7rem;margin-left:8px;white-space:nowrap'>{tr['phase'] or 'Unspecified'}</span></div>", unsafe_allow_html=True)

    with t_lit:
        sh("📄",f"PubMed Literature 2022–2025 · {gene}{lab_paper_note}",color)
        lit_q = f"{gene}[gene] 2022:2025[pdat]"
        if lab.get("pi_pubmed_query"):
            lit_q_lab = f"{gene} AND ({lab['pi_pubmed_query']})"
            show_lab = st.checkbox("Show only your lab's papers about this gene", key=f"lab_lit_{gene}")
            if show_lab: lit_q = lit_q_lab
        with st.spinner("Fetching papers..."):
            papers = api_pubmed(lit_q, 12)
        if not papers: st.info("No papers found.")
        for p in papers:
            wk = detect_weaknesses(p["title"])
            with st.expander(f"{tier_badge(p['tier'])} &nbsp; {p['title'][:70]}{'...' if len(p['title'])>70 else ''}",expanded=False):
                st.markdown(f"<div style='font-size:.76rem;color:#5a8090'>{p['authors']} · <i>{p['journal']}</i> · {p['year']}</div>",unsafe_allow_html=True)
                pm=p.get("pmid",""); doi=p.get("doi",""); url=p.get("url","")
                if doi: st.markdown(f"<a href='https://doi.org/{doi}' target='_blank' style='font-size:.7rem'>DOI ↗</a> &nbsp; <a href='{url}' target='_blank' style='font-size:.7rem'>PubMed {pm} ↗</a>",unsafe_allow_html=True)
                else: st.markdown(f"<a href='{url}' target='_blank' style='font-size:.7rem'>PubMed {pm} ↗</a>",unsafe_allow_html=True)
                for wt,wb in wk: warn_box(wt,wb)

    with t_exp:
        sh("🧪","Protein-Specific Experiments",color)
        render_experiments_panel(gene, pdata, cv, gnomad, ot, partners, am_data, is_arrb, color, lab)

    with t_assay:
        render_assay_analysis_tab(gene, color, lab)

# ── EXPERIMENTS ──────────────────────────────────────────────────────────────────
def render_experiments_panel(gene,pdata,cv,gnomad,ot,partners,am_data,is_arrb,color,lab):
    if is_arrb: warn_box("Experiments suppressed","Zero disease variants. ARRB1/ARRB2 KO mice viable. Redirect investment to genetically validated targets."); return
    n_cv=len(cv); pli=gnomad.get("pLI",0); n_crit=sum(1 for v in cv if v.get("ml_rank")=="CRITICAL")
    n_lof=gi_score(cv,pdata.get("length",500) if pdata else 500).get("n_lof",0); n_miss=n_cv-n_lof
    top_cv=cv[0].get("title","")[:35] if cv else "top pathogenic variant"
    top_part=partners[0]["partner"] if partners else "key interaction partner"
    concordant=am_data.get("pathogenic_count",0) if am_data else 0
    is_gpcr=any(x in gene for x in ["ADRB","AGTR","MAS1","CHRM","ADRA","DRD","HTR","CCR","CXCR"])
    is_kin=any(x in gene for x in ["GRK","CDK","BRAF","EGFR","ALK","FGFR","MET","RET","JAK","ABL","LRRK"])
    is_fil=gene in ("FLNA","FLNB","FLNC")
    is_sm=any("small" in t.lower() for t in ot.get("tractability",[]))
    lab_assays=lab.get("assay_types",[])
    budget_tier={"<$10K":0,"$10K–50K":1,"$50K–200K":2,"$200K–1M":3,">$1M":4}.get(lab.get("budget","$50K–200K"),2)

    exps=[]
    exps.append({"name":f"Rosetta ΔΔG + AlphaMissense dual screen — {n_miss} missense variants","cost":"Free","time":"1–3d","p":.92,"v":8,"first":True,"body":f"Zero-cost dual validation. Rosetta ΔΔG: structural destabilisation. AlphaMissense (DeepMind): independent pathogenicity prediction. Concordant (ClinVar P/LP + AM ≥0.564 + ΔΔG ≥2 REU) = highest priority for TSA/chaperone. Discordant (ClinVar P/LP, AM <0.564) = non-structural mechanism → Co-IP or functional assay instead. {concordant} AlphaMissense-pathogenic positions detected."})
    if n_lof>n_miss:
        exps.append({"name":f"Western blot — protein level in {n_lof} LoF variant models","cost":"$500","time":"1 wk","p":.90,"v":9,"first":True,"body":f"LoF-dominant ({n_lof}/{n_cv} P/LP are frameshift/stop-gain). Anti-{gene} antibody (HPA-validated). CRISPR knock-in or patient-derived cells. pLI={pli} — {'expect absent band (NMD/proteasomal degradation)' if pli>0.8 else 'may show truncated band (NMD-escape or dominant-negative)'}. Absent = gene supplementation strategy. Truncated = different approach."})
    elif n_miss>0:
        exps.append({"name":f"Thermal shift assay (DSF) — {min(n_crit+3,8)} missense variants vs WT","cost":"$2,000","time":"2 wks","p":.85,"v":9,"first":True,"body":f"Missense-dominant ({n_miss}/{n_cv} P/LP). Purify WT + {top_cv[:25]}... DSF (SYPRO Orange, 384-well, 0.3mg/mL). ΔTm ≤-2°C = structurally destabilising → pharmacochaperone screen (Prestwick 1,280 drugs, $2K, 2 wks — fastest path to clinical candidate). ΔTm <1°C but P/LP = functional mechanism → Co-IP with {top_part}. AlphaMissense concordance strengthens structural interpretation. {'Matches your lab assay repertoire.' if 'Western blot' in lab_assays else ''}"})
    if is_gpcr:
        exps.append({"name":f"Filamin A Ser2152-P western — agonist-stimulated {gene} (PRIMARY GPCR readout)","cost":"$2,000","time":"1 wk","p":.90,"v":10,"first":True,"body":f"H8 helix dislodgement → Filamin Ig21 binding → PKA phosphorylates Ser2152. More receptor-proximal than cAMP, IP3, or beta-arrestin. Agonist → anti-Filamin A IP → pSer2152 western (Cell Signaling anti-pS2152). Variant in H8 or ICL3 → REDUCED Filamin-P despite normal cAMP. PhosphoSite highest FLNA peak = only non-noise signal. Nakamura JBC 2015. IP-protected readout."})
        exps.append({"name":f"cAMP HTRF — G-protein coupling WT vs {top_cv[:20]}...","cost":"$3,000","time":"2 wks","p":.85,"v":8,"first":False,"body":f"Gs/Gi primary coupling. cAMP HTRF (Cisbio 384-well). WT vs each P/LP variant at matched expression (confirm by western first). Kills cAMP not Filamin-P = G-protein defect. Kills Filamin-P not cAMP = cytoskeletal decoupling. Different mechanism = different target."})
    if is_kin:
        exps.append({"name":f"ADP-Glo kinase activity — {top_cv[:25]}... vs WT","cost":"$5,000","time":"3 wks","p":.85,"v":9,"first":True,"body":f"ADP-Glo (Promega) = most direct kinase activity readout. WT vs {top_cv} at matched protein concentration (confirm by western). ≥70% activity reduced = LoF → substrate accumulation is disease mechanism. Unchanged = allosteric/scaffolding defect → test {top_part} interaction. Before HTS: KINOMEscan 468-kinase panel ($50K) to confirm selectivity."})
    if is_fil:
        exps.append({"name":"SPR — Filamin Ig21 vs GPCR FBM peptides","cost":"$8,000","time":"3 wks","p":.85,"v":10,"first":True,"body":f"Pathogenic FLNA variants in Ig19-21 disrupt FBM binding. Immobilise Filamin Ig21 on CM5 chip. Analytes: AT1R C-tail (positive control), MAS1 C-tail, {top_cv[:20]}... peptide. KD >10-fold increased = FBM disruption confirmed. Follow with PKA Ser2152-P assay: reduced Filamin-P in cells confirms cytoskeletal decoupling mechanism."})
    crispr_ok=n_crit>=2 and budget_tier>=2
    exps.append({"name":f"CRISPR knock-in — {top_cv[:30]}... in disease-relevant cells","cost":"$25,000","time":"8 wks","p":.80 if crispr_ok else .35,"v":10 if crispr_ok else 3,"first":False,"body":f"{'JUSTIFIED: ' + str(n_crit) + ' CRITICAL variants + budget allows.' if crispr_ok else 'PREMATURE: run TSA/western first. Only ' + str(n_crit) + ' CRITICAL variants, or budget may be limiting.'} HDR in {gene} endogenous locus. Screen ≥50 clones Sanger + western. Readout: {'Filamin Ser2152-P after agonist' if is_gpcr else 'kinase activity assay' if is_kin else 'disease-relevant functional assay'}. Positive = ClinGen PS3 evidence. pLI={pli}."})
    if top_part and top_part!="key interaction partner":
        exps.append({"name":f"AP-MS interactome — {gene}:{top_part} WT vs {top_cv[:18]}...","cost":"$15,000","time":"6 wks","p":.75,"v":8,"first":False,"body":f"Endogenous 3xFLAG-tag {gene} via CRISPR. Anti-FLAG IP × 3 replicates. TMT-LC-MS/MS. SAINTexpress + CRAPome filtering. Hypothesis: {top_cv[:25]}... reduces interaction with {top_part}. Gained HSP70/HSP90 interactions = protein misfolding and dominant-negative behaviour."})
    if is_sm or n_miss>5:
        exps.append({"name":"Pharmacochaperone screen — Prestwick 1,280 approved drugs","cost":"$3,000","time":"2 wks","p":.60,"v":8,"first":False,"body":"Screen Prestwick at 10µM by DSF. Flag ΔTm ≥1°C. Dose-response (0.1–100µM) on top 20. Cellular rescue: add hit to CRISPR mutant cells. Approved drug = known safety profile → accelerated clinical translation. Fastest path to clinical candidate for missense-dominant proteins."})

    first=[e for e in exps if e.get("first")]; rest=sorted([e for e in exps if not e.get("first")],key=lambda x:-x["v"])
    for i,exp in enumerate(first+rest):
        border="#00c896" if exp.get("first") else "#0d2545"
        with st.expander(f"{'🥇 DO FIRST — ' if exp.get('first') else f'#{i+1} — '}{exp['name']}  ·  {exp['cost']}  ·  ⏱ {exp['time']}",expanded=(i<2)):
            cl,cr=st.columns([4,1])
            with cl: st.markdown(f"<div style='background:#020810;border-left:3px solid {border};padding:.7rem 1rem;border-radius:0 8px 8px 0;color:#7ab0c0;font-size:.81rem;line-height:1.7'>{exp['body']}</div>",unsafe_allow_html=True)
            with cr: st.markdown(f"<div style='background:#030810;border:1px solid #0d2545;border-radius:9px;padding:.55rem;text-align:center'><div style='color:#3a6080;font-size:.63rem;font-weight:600;text-transform:uppercase'>P(success)</div><div style='color:#ffd60a;font-size:1.15rem;font-weight:700'>{int(exp['p']*100)}%</div><div style='color:#3a6080;font-size:.63rem;margin-top:3px'>Value</div><div style='color:#00c896;font-size:.9rem;font-weight:600'>{exp['v']}/10</div></div>",unsafe_allow_html=True)

# ── MICROBIOME DOMAIN ────────────────────────────────────────────────────────────
def render_microbiome_domain():
    color = "#00c896"
    gene_input, do_search = render_sidebar("microbiome")
    run_gene = st.session_state.pop("_run_gene", None)
    if do_search and gene_input.strip(): run_gene = gene_input.strip()

    st.markdown(f"<div style='padding:1.1rem 1.5rem .5rem;border-bottom:1px solid #0d2545'><span style='font-size:1.7rem'>🦠</span> <span style='color:{color};font-weight:700;font-size:1.1rem'>Microbiome Intelligence</span><div style='color:#2a4050;font-size:.75rem;margin-top:2px'>AI-powered functional annotation · Host-microbe interactions · TMAO · FMT · Pathway reannotation</div></div>", unsafe_allow_html=True)

    if run_gene: render_gene_analysis(run_gene, "microbiome"); st.markdown("<hr style='border-color:#0d2545;margin:.6rem 0'>", unsafe_allow_html=True)

    t_ai, t_tax, t_file, t_lit = st.tabs(["🤖 AI Functional Annotation","🔬 Microbe Profile","📁 Annotate My Data","📚 Literature"])

    with t_ai:
        sh("🤖","AI-Powered Gene Function Reannotation","#00c896")
        st.markdown("<div style='background:#020d10;border:1px solid #00c89633;border-radius:10px;padding:.8rem 1.1rem;margin-bottom:.8rem'><div style='color:#00c896;font-weight:600;font-size:.85rem;margin-bottom:.3rem'>The annotation problem — solved</div><div style='color:#3a6060;font-size:.8rem;line-height:1.7'>Standard tools (KEGG, GO, COG) annotate microbial genes as \"biosynthesis\", \"chemosynthesis\", \"protein aggregation\" — these terms are useless for understanding what the microbe actually DOES in the host. This tool uses Claude to reannotate database IDs with meaningful biological context: specific metabolites produced, host receptor interactions, disease associations, and community-level function.</div></div>", unsafe_allow_html=True)
        gene_ids_input = st.text_area("Paste gene IDs or functional annotations (one per line)", placeholder="COG0001\nK00001\nGO:0009058\nbiosynthesis\nbeta-oxidation\nphosphate transport", height=120, key="micro_gene_ids")
        research_ctx = st.text_input("Research context (optional)", placeholder="e.g. Gut dysbiosis in IBD patients, analysing Firmicutes-to-Bacteroidetes ratio changes", key="micro_ctx")
        if st.button("🧠 Reannotate with AI", key="micro_annotate", type="primary"):
            if gene_ids_input.strip():
                ids = parse_functional_annotation_file(gene_ids_input)
                lab_focus = lab.get("research_focus","")
                with st.spinner(f"Claude is reannotating {len(ids)} functional annotations..."):
                    result = annotate_microbial_genes_llm(ids, research_ctx, lab_focus)
                if result.get("error"): st.error(result["error"])
                elif result.get("annotations"):
                    for ann in result["annotations"]:
                        conf_c = {"high":"#00c896","medium":"#ffd60a","low":"#ff8c42"}.get(ann.get("evidence_quality","low"),"#5a8090")
                        with st.expander(f"**{ann.get('id','')}** — {ann.get('true_function','')[:60]}...", expanded=True):
                            st.markdown(f"<div style='background:#020d10;border-left:3px solid {conf_c};padding:.75rem 1rem;border-radius:0 9px 9px 0'>", unsafe_allow_html=True)
                            for field,label,clr in [("true_function","True biological function","#00c896"),("metabolite","Metabolite","#4a90d9"),("host_interaction","Host interaction","#a855f7"),("disease_relevance","Disease relevance","#ff8c42"),("research_gap","Research gap","#ffd60a")]:
                                val = ann.get(field,"")
                                if val: st.markdown(f"<div style='margin-bottom:.25rem'><span style='color:{clr};font-weight:600;font-size:.76rem'>{label}:</span> <span style='color:#8ab0c0;font-size:.8rem'>{val}</span></div>", unsafe_allow_html=True)
                            orgs = ann.get("key_organisms",[])
                            if orgs: st.markdown(f"<div style='color:#3a6080;font-size:.74rem'>Key organisms: {', '.join(orgs[:4])}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div style='color:{conf_c};font-size:.7rem'>Evidence: {ann.get('evidence_quality','?')}</div>", unsafe_allow_html=True)
                            st.markdown("</div>", unsafe_allow_html=True)
                elif result.get("raw"): st.markdown(result["raw"])
            else:
                st.warning("Paste some gene IDs or functional annotations first.")

    with t_tax:
        sh("🔬","Microbe Biological Profile","#00c896")
        taxon_input = st.text_input("Microbe name", placeholder="e.g. Akkermansia muciniphila, Bacteroides fragilis, Faecalibacterium prausnitzii", key="taxon_input")
        tax_ctx = st.text_input("Host/disease context (optional)", placeholder="e.g. Gut microbiome in colorectal cancer patients", key="tax_ctx")
        if st.button("🧬 Generate Microbe Profile", key="taxon_btn", type="primary"):
            if taxon_input.strip():
                with st.spinner(f"Claude is profiling {taxon_input}..."):
                    profile = annotate_microbe_taxonomy_llm(taxon_input, tax_ctx)
                if profile.get("error"): st.error(profile["error"])
                elif profile.get("raw"): st.markdown(profile["raw"])
                else:
                    # Structured display
                    c1,c2 = st.columns(2)
                    with c1:
                        for field,label,clr in [("classification","Classification","#00c896"),("gram_status","Gram status","#4a90d9"),("metabolism","Metabolism","#a855f7"),("gut_niche","Gut niche","#ffd60a")]:
                            val=profile.get(field,""); st.markdown(f"<div style='padding:4px 0;border-bottom:1px solid #0d2545;font-size:.8rem'><span style='color:{clr};font-weight:600'>{label}:</span> <span style='color:#d0e8ff'>{val}</span></div>", unsafe_allow_html=True) if val else None
                        if profile.get("key_functions"):
                            sh("⚙️","Key functions",color)
                            for f in profile["key_functions"]: st.markdown(f"<div style='color:#6a9ab0;font-size:.78rem;padding:2px 0'>→ {f}</div>", unsafe_allow_html=True)
                    with c2:
                        if profile.get("metabolites_produced"):
                            sh("⚗️","Metabolites produced",color)
                            for m in profile["metabolites_produced"]: st.markdown(f"<div style='color:#6a9ab0;font-size:.78rem;padding:2px 0'>• {m}</div>", unsafe_allow_html=True)
                        if profile.get("disease_associations"):
                            sh("🩺","Disease associations",color)
                            for da in profile["disease_associations"]:
                                dir_clr="#ff2d55" if da.get("direction")=="increased" else "#4a90d9"
                                ev_clr={"strong":"#00c896","moderate":"#ffd60a","weak":"#ff8c42"}.get(da.get("evidence","weak"),"#5a8090")
                                st.markdown(f"<div style='font-size:.78rem;padding:3px 0;border-bottom:1px solid #0d2545'><span style='color:#d0e8ff'>{da.get('condition','')}</span> <span style='color:{dir_clr}'>{da.get('direction','')}</span> <span style='color:{ev_clr};font-size:.7rem'>({da.get('evidence','')})</span></div>", unsafe_allow_html=True)
                        if profile.get("therapeutic_potential"):
                            sh("💊","Therapeutic potential",color)
                            st.markdown(f"<div style='color:#6a9ab0;font-size:.8rem'>{profile['therapeutic_potential']}</div>", unsafe_allow_html=True)
            else:
                st.warning("Enter a microbe name.")

    with t_file:
        sh("📁","Annotate My Metagenome Data","#00c896")
        st.markdown("<div style='color:#5a8090;font-size:.8rem;margin-bottom:.6rem'>Upload your functional annotation output from DIAMOND, HUMAnN3, PROKKA, eggNOG-mapper, or any tool that produces COG/KEGG/GO/InterPro annotations. Claude will explain what your community is ACTUALLY doing.</div>", unsafe_allow_html=True)
        uploaded = st.file_uploader("Upload functional annotation file (CSV, TSV, TXT)", type=["csv","tsv","txt"], key="micro_file")
        pathway_text = st.text_area("Or paste pathway/function list directly", placeholder="K00001\nK00002\nbiosynthesis of cofactors\nCOG0001\nGO:0009058", height=100, key="micro_paste")
        context_input = st.text_input("Sample context", placeholder="e.g. Gut microbiome, IBD patient, post-FMT day 7", key="micro_sample_ctx")
        if st.button("🧠 Annotate Community Function", key="annotate_file", type="primary"):
            text_to_parse = pathway_text
            if uploaded:
                try:
                    import pandas as pd, io
                    if uploaded.name.endswith(".csv"): df=pd.read_csv(uploaded)
                    else: df=pd.read_csv(uploaded,sep="\t")
                    text_to_parse = "\n".join(df.iloc[:,0].astype(str).tolist()[:50])
                except: text_to_parse = uploaded.read().decode("utf-8","ignore")[:3000]
            if text_to_parse.strip():
                ids = parse_functional_annotation_file(text_to_parse)
                with st.spinner(f"Reannotating {len(ids)} functions with Claude..."):
                    result = annotate_microbial_genes_llm(ids, context_input, lab.get("research_focus",""))
                    if ids[:5]:
                        pathway_interp = pathway_annotation_analysis(ids[:15], context_input)
                with st.spinner("Generating community-level interpretation..."):
                    pass  # Already done above
                if pathway_interp and not pathway_interp.get("error"):
                    st.markdown("---")
                    sh("🌐","Community-Level Interpretation","#00c896")
                    if pathway_interp.get("pathway_summary"): info_box(pathway_interp["pathway_summary"], "#00c896")
                    if pathway_interp.get("key_metabolites_predicted"):
                        sh("⚗️","Predicted metabolites reaching host","#00c896")
                        for met in pathway_interp["key_metabolites_predicted"][:5]:
                            if isinstance(met, dict):
                                st.markdown(f"<div style='padding:4px 0;border-bottom:1px solid #0d2545;font-size:.8rem'><span style='color:#00c896;font-weight:500'>{met.get('metabolite','')}</span> <span style='color:#3a6060;font-size:.75rem'>from {met.get('source_pathway','')} → {met.get('host_effect','')}</span></div>", unsafe_allow_html=True)
                if result.get("annotations"):
                    st.markdown("---")
                    sh("🔬","Per-function annotations","#00c896")
                    for ann in result["annotations"][:8]:
                        with st.expander(f"{ann.get('id','')} — {ann.get('true_function','')[:55]}...", expanded=False):
                            for field,label in [("true_function","True function"),("metabolite","Metabolite"),("host_interaction","Host interaction"),("disease_relevance","Disease relevance")]:
                                val=ann.get(field,"")
                                if val: st.markdown(f"**{label}:** {val}")
            else:
                st.warning("Upload a file or paste annotations.")

    with t_lit:
        sh("📄","Microbiome Literature — PubMed 2022–2025","#00c896")
        micro_qs = ["gut microbiome disease mechanism metabolite 2023 2024[pdat]","TMAO cardiovascular arrhythmia gut bacteria 2023 2024[pdat]","fecal microbiota transplant clinical trial 2023 2024[pdat]","gut-brain axis serotonin 2023 2024[pdat]","microbiome AI machine learning functional annotation 2023 2024[pdat]","16S metagenomics annotation LLM 2023 2024[pdat]"]
        sel_q = st.selectbox("Query",micro_qs,key="micro_lit_q")
        if st.button("Fetch ↗",key="micro_fetch"):
            with st.spinner("Fetching..."):
                papers = pubmed_microbiome(sel_q, 10)
            for p in papers:
                with st.expander(f"{tier_badge(classify_tier(p['title']))} &nbsp; {p['title'][:70]}...", expanded=False):
                    st.markdown(f"<div style='font-size:.76rem;color:#5a8090'>{p['authors']} · <i>{p['journal']}</i> · {p['year']}</div>",unsafe_allow_html=True)
                    st.markdown(f"<a href='{p['url']}' target='_blank' style='font-size:.7rem'>PubMed {p['pmid']} ↗</a>",unsafe_allow_html=True)
        else:
            st.info("Select a query and click Fetch.")

# ── DOMAIN ROUTER ────────────────────────────────────────────────────────────────
def render_standard_domain(domain_key):
    D = DOMAINS_META[domain_key]; color = D["color"]
    gene_input, do_search = render_sidebar(domain_key)
    run_gene = st.session_state.pop("_run_gene", None)
    if do_search and gene_input.strip(): run_gene = gene_input.strip()

    st.markdown(f"<div style='padding:1.1rem 1.5rem .5rem;border-bottom:1px solid #0d2545;display:flex;align-items:center;gap:10px'><span style='font-size:1.7rem'>{D['icon']}</span><div><div style='color:{color};font-weight:700;font-size:1.1rem'>{D['label']}</div><div style='color:#2a4050;font-size:.75rem'>{D['tagline']}</div></div></div>", unsafe_allow_html=True)

    if run_gene: render_gene_analysis(run_gene, domain_key); st.markdown("<hr style='border-color:#0d2545;margin:.6rem 0'>", unsafe_allow_html=True)

    # Domain info tabs
    t_quick, t_ref = st.tabs(["Quick Reference","Domain Resources"])
    with t_quick:
        domain_facts = {
            "neuro":[("Tau (MAPT) phosphorylation","85+ phospho-sites on PhosphoSite — most are kinase noise. Only disease-causing mutations (R406W FTLD, P301L/S) and NFT-forming sites (Ser202/Thr205) are validated signals.","#a855f7"),("GBA + LRRK2 interaction","GBA variants + LRRK2 variants together cause earlier-onset Parkinson's than either alone. Digenic genetics.","#a855f7"),("BBB penetration rules","MW <500 Da, logP 1–3, few H-bond donors, few H-bond acceptors. P-gp efflux substrate = CNS failure.","#a855f7"),("DRD2 occupancy","65% receptor occupancy = therapeutic threshold. >80% = EPS risk. Clozapine: lower D2 + higher 5-HT2A = atypical.","#a855f7"),("SOD1 G93A model warning","100+ drugs worked in this model, zero translated to ALS. Not a reliable preclinical model for non-SOD1 ALS.","#ff2d55")],
            "onco":[("KRAS targetability","G12C = covalently targetable (sotorasib, adagrasib). G12D and G12V still lack approved direct inhibitors. Different chemistries required.","#ff2d55"),("TMB threshold","≥10 mut/Mb predicts pembrolizumab response (FDA pan-tumour approval). Ultra-high TMB (>100, POLE) = exceptional IO response.","#ff2d55"),("Founder mutation principle","Earliest somatic mutation in tumour evolution = primary target. Late mutations are passengers — targeting them causes rapid resistance.","#ff2d55"),("HER2-low","IHC 1+ or 2+/ISH- was previously HER2-negative. T-DXd (Enhertu) achieves 57% ORR — redefined a new targetable population.","#ff2d55"),("Biomarker-unselected trial failure","EGFR inhibitors failed in unselected NSCLC until EGFR mutation testing was mandatory. Never run a targeted therapy trial without predictive biomarker selection.","#ff8c42")],
            "proteins":[("AlphaMissense threshold","Score ≥0.564 = pathogenic prediction. Sensitivity 90%, specificity 73% vs ClinVar. Concordant + ClinVar P/LP = highest priority.","#00e5ff"),("FLNA Ser2152 gating","PKA cannot phosphorylate FLNA Ser2152 in the autoinhibited state. Gating by GPCR H8 dislodgement = mechanistically distinct from background noise.","#00e5ff"),("ARRB2 deprioritise","Zero confirmed Mendelian disease variants. ARRB1/ARRB2 double KO mice viable. $4,050,000 in avoidable spend if pursuing. Use Filamin Ser2152-P instead.","#ff2d55"),("Cryo-EM resolution","Now routinely sub-2Å for soluble proteins. Below ~1.5Å: direct observation of H atoms, water networks, protonation states.","#00e5ff"),("Discordant variants","ClinVar P/LP but AlphaMissense <0.564 = non-structural mechanism. Do NOT do TSA — do Co-IP or splicing assay instead.","#ffd60a")],
        }
        facts = domain_facts.get(domain_key, [])
        for fact_title, fact_body, fact_color in facts:
            st.markdown(f"<div style='display:flex;gap:9px;padding:6px 0;border-bottom:1px solid #0d2545'><span style='color:{fact_color};flex-shrink:0;font-size:.9rem;margin-top:1px'>→</span><div><div style='color:{fact_color};font-size:.78rem;font-weight:600'>{fact_title}</div><div style='color:#6a9ab0;font-size:.77rem;line-height:1.6'>{fact_body}</div></div></div>", unsafe_allow_html=True)

    with t_ref:
        resources = {
            "neuro":[("AlzForum","https://www.alzforum.org","Free","AD mutations, failed drugs, models"),("PDGene","https://pdgene.org","Free","PD GWAS loci"),("DisGeNET","https://www.disgenet.org","Free/API","Gene-disease associations"),("Allen Brain Atlas","https://portal.brain-map.org","Free/API","Brain region-specific expression"),("ADNI","https://adni.loni.usc.edu","Controlled","AD Neuroimaging Initiative — longitudinal")],
            "onco":[("cBioPortal","https://www.cbioportal.org","Free/API","Cancer genomics — TCGA + cohorts"),("OncoKB","https://www.oncokb.org","Free/API","Actionable variants — 4-level evidence"),("COSMIC","https://cancer.sanger.ac.uk/cosmic","Free/API","Somatic mutations — curated signatures"),("DepMap","https://depmap.org","Free","CRISPR screens — 900+ cell lines"),("IARC TP53","https://tp53.isb-cgc.org","Free","TP53 variant functional data")],
            "proteins":[("UniProt","https://www.uniprot.org","Free/API","Gold-standard curated proteins"),("AlphaFold DB","https://alphafold.ebi.ac.uk","Free/API","DeepMind structure predictions"),("AlphaMissense","https://alphamissense.hegelab.org","Free/API","Per-residue pathogenicity"),("PhosphoSite","https://www.phosphosite.org","Free","PTMs — curated modifications"),("GPCRdb","https://gpcrdb.org","Free","GPCR H8 conservation, FBM motifs")],
        }.get(domain_key, [])
        for rname,rurl,rtag,rdesc in resources:
            tc="#00c896" if "Free" in rtag and "API" not in rtag else "#ffd60a" if "API" in rtag else "#5a8090"
            st.markdown(f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:9px;padding:.55rem .85rem;margin-bottom:.22rem;display:flex;justify-content:space-between;align-items:center'><div><a href='{rurl}' target='_blank' style='color:#d0e8ff;font-weight:500;font-size:.83rem'>{rname}</a><div style='color:#2a4050;font-size:.71rem'>{rdesc}</div></div><span style='background:{tc}18;color:{tc};font-size:.67rem;padding:2px 7px;border-radius:6px;border:1px solid {tc}44;margin-left:8px;white-space:nowrap'>{rtag}</span></div>", unsafe_allow_html=True)

    st.markdown(f"<div style='color:#1e3a5a;font-size:.68rem;text-align:center;padding:1.2rem 0'>Protellect · {lab.get('lab_name','Biology Intelligence')} · UniProt · ClinVar · gnomAD · STRING · OpenTargets · AlphaFold · AlphaMissense · PubMed · ClinicalTrials.gov · {datetime.now().year}</div>", unsafe_allow_html=True)

# ── MAIN ROUTER ──────────────────────────────────────────────────────────────────
d = st.session_state.domain
if d is None:
    render_splash()
elif d == "microbiome":
    render_microbiome_domain()
else:
    render_standard_domain(d)
