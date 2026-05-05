"""
Protellect v2 — Complete Rewrite
ClinVar-First Drug Target Validation System

Spec:
  Sidebar: disease breakdown + ranking + wet lab summary + experiments
  Tab 1 (Triage): bright AlphaFold structure + disease affiliation + sphere residues + triage list
  Tab 2 (Case Study): tissue + genomic + GPCR association + somatic/germline diseases
  Tab 3 (Protein Explorer): clickable backbone diagram + mutation slider animation + disease list
  Tab 4 (Therapy & Experiments): detailed dropdown experiments with cost + focus guidance
"""
import streamlit as st, streamlit.components.v1 as components
import pandas as pd, numpy as np, requests, json, io, re, time, base64, os
from pathlib import Path

# ── Logo ───────────────────────────────────────────────────────────────────────
try:
    from logo import LOGO_DATA_URL as LOGO
except Exception:
    _lp = Path("/mnt/user-data/uploads/1777622887238_image.png")
    LOGO = ("data:image/png;base64," + base64.b64encode(_lp.read_bytes()).decode()) if _lp.exists() else None

# ── Support modules ────────────────────────────────────────────────────────────
from scorer import load_file, score_residues, get_summary_stats, validate_dataframe, detect_dataset_info, generate_top_pathways, ML_AVAILABLE
from evidence_layer import calculate_dbr, assign_genomic_tier, get_genomic_verdict
try:
    from evidence_layer import classify_protein_role
except Exception:
    def classify_protein_role(g, n, **kw):
        if n==0: return {"role":"unvalidated","label":"No ClinVar evidence","icon":"⚪","color":"#666","note":"Zero pathogenic variants.","warning":"Zero germline pathogenic variants — validate before any investment."}
        elif n<10: return {"role":"rare","label":"Rare Mendelian disease gene","icon":"🟡","color":"#FFD700","note":f"{n} pathogenic variant(s)."}
        elif n<500: return {"role":"validated","label":"Validated disease gene","icon":"🟠","color":"#FFA500","note":f"{n} pathogenic variants."}
        else: return {"role":"critical","label":"Critical disease driver","icon":"🔴","color":"#FF4C4C","note":f"{n} pathogenic variants."}
try:
    from protein_data import get_protein_info
except Exception:
    def get_protein_info(g): return {}

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Protellect", page_icon="🧬", layout="wide", initial_sidebar_state="expanded")

# ── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
html,body,[class*="css"]{font-family:'Space Grotesk',sans-serif}
h1,h2,h3{font-family:'JetBrains Mono',monospace}
[data-testid="stSidebar"]{background:#050810;border-right:1px solid #0f1525}
.block-container{padding-top:1.2rem}
.stTabs [data-baseweb="tab-list"]{gap:2px;background:#050810;border-radius:8px;padding:4px}
.stTabs [data-baseweb="tab"]{background:#0a0d18;border-radius:6px;color:#666;font-family:'JetBrains Mono',monospace;font-size:0.72rem;font-weight:600;padding:6px 16px}
.stTabs [aria-selected="true"]{background:#1a2040;color:#60a5fa}
.card{background:#080c18;border:1px solid #1a2040;border-radius:10px;padding:16px 18px;margin-bottom:10px}
.card-red{background:#0c0810;border:1px solid #FF4C4C44;border-radius:10px;padding:14px 16px;margin-bottom:8px}
.card-green{background:#080c08;border:1px solid #4CAF5044;border-radius:10px;padding:14px 16px;margin-bottom:8px}
.mono{font-family:'JetBrains Mono',monospace}
.tag{display:inline-block;padding:2px 10px;border-radius:12px;font-size:0.63rem;font-family:'JetBrains Mono',monospace;margin:2px;font-weight:600}
.label{font-family:'JetBrains Mono',monospace;font-size:0.62rem;text-transform:uppercase;letter-spacing:0.16em;color:#334;margin-bottom:6px;border-bottom:1px solid #0f1525;padding-bottom:5px}
.row-item{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid #0a0d18;font-size:0.79rem}
.rl{color:#445;font-size:0.67rem;font-family:'JetBrains Mono',monospace;min-width:110px}
.rv{color:#dde}
.paper-link{font-size:0.68rem;color:#60a5fa;text-decoration:none;padding:2px 8px;background:#0a1020;border:1px solid #1a2040;border-radius:8px;display:inline-block;margin:2px}
</style>""", unsafe_allow_html=True)

# ── Ground truth ClinVar ──────────────────────────────────────────────────────
GT = {
    "FLNA": (847,2647,"Filamin A","Xq28","CRITICAL","Periventricular heterotopia · Cardiac malformations · Aortic aneurysm · Intellectual disability · Epilepsy · Melnick-Needles syndrome · Otopalatodigital syndrome"),
    "FLNB": (412,2602,"Filamin B","3p14","CRITICAL","Boomerang dysplasia · Larsen syndrome · Atelosteogenesis I/II/III · Spondylocarpotarsal synostosis"),
    "FLNC": (3800,2725,"Filamin C","7q32","CRITICAL","Arrhythmogenic cardiomyopathy · Dilated cardiomyopathy · Myofibrillar myopathy · Distal myopathy"),
    "CHRM2": (102,466,"Muscarinic M2","7q31","HIGH","Dilated cardiomyopathy (dominant)"),
    "CHRM3": (8,590,"Muscarinic M3","1q43","LOW","Prune belly syndrome"),
    "BRCA1": (6000,1863,"BRCA1","17q21","CRITICAL","Breast cancer · Ovarian cancer · Fanconi anaemia"),
    "BRCA2": (5500,3418,"BRCA2","13q12","CRITICAL","Breast cancer · Ovarian cancer · Fanconi anaemia D1"),
    "TP53":  (8000,393,"Tumour protein p53","17p13","CRITICAL","Li-Fraumeni syndrome · Most mutated cancer gene"),
    "EGFR":  (1200,1210,"EGFR","7p11","CRITICAL","Lung adenocarcinoma · Glioblastoma"),
    "KRAS":  (900,189,"KRAS","12p12","CRITICAL","Pancreatic · colorectal · lung cancer · Noonan syndrome"),
    "MYH7":  (700,1935,"MYH7","14q11","CRITICAL","Hypertrophic cardiomyopathy · Dilated cardiomyopathy · Laing myopathy"),
    "LMNA":  (500,664,"Lamin A/C","1q22","CRITICAL","Dilated cardiomyopathy · Muscular dystrophy · Progeria"),
    "ITB3":  (300,788,"Integrin β3","17q21","HIGH","Glanzmann thrombasthenia"),
    "ITGA2B":(280,1039,"Integrin αIIb","17q21","HIGH","Glanzmann thrombasthenia"),
    "ITB2":  (200,769,"Integrin β2","21q22","HIGH","Leucocyte adhesion deficiency"),
    "ARRB1": (0,418,"β-Arrestin 1","11q13","NEUTRAL","No confirmed germline pathogenic variants — structural scaffold pattern"),
    "ARRB2": (0,410,"β-Arrestin 2","17p13","NEUTRAL","No confirmed germline pathogenic variants — structural scaffold pattern"),
    "TALN1": (0,2541,"Talin 1","9p13","NEUTRAL","No confirmed germline pathogenic variants — structural scaffold"),
    "TALN2": (0,1289,"Talin 2","15q22","NEUTRAL","No confirmed germline pathogenic variants"),
    "ITAM":  (3,1152,"Integrin αM","16p11","MEDIUM","Very limited disease association despite many variants"),
    "ITAL":  (1,1170,"Integrin αL","16p11","MEDIUM","Very limited disease association despite many variants"),
}

TIER_COLORS = {"CRITICAL":"#FF4C4C","HIGH":"#FFA500","MEDIUM":"#FFD700","LOW":"#60a5fa","NEUTRAL":"#666"}
TIER_ICONS  = {"CRITICAL":"🔴","HIGH":"🟠","MEDIUM":"🟡","LOW":"🔵","NEUTRAL":"⚪"}

PAPERS = {
    "king_2024":   {"cite":"King et al., Nature 2024","url":"https://www.nature.com/articles/s41586-024-07316-0","key":"Drug targets with human genetic support are 2.6× more likely to succeed."},
    "minikel_2021":{"cite":"Minikel et al., Nature 2021","url":"https://www.nature.com/articles/s41586-020-2267-z","key":"Human LOF variants are in vivo knockouts — more informative than mouse models."},
    "plenge_2016": {"cite":"Plenge et al., Nat Rev Drug Discov 2016","url":"https://www.nature.com/articles/nrd.2016.29","key":"Targets not causally related to human disease fail clinically."},
    "cook_2014":   {"cite":"Cook et al., Nat Rev Drug Discov 2014","url":"https://www.nature.com/articles/nrd4309","key":"~90% of drugs fail — right-target failures are the majority."},
    "braxton_2024":{"cite":"Braxton et al., Hum Genet 2024","url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC11303574/","key":"Functional assays reclassify ~55% of VUS when calibrated against ClinVar."},
}

def paper_chip(key):
    p = PAPERS.get(key,{})
    return f'<a href="{p.get("url","#")}" target="_blank" class="paper-link">📄 {p.get("cite","")}</a>' if p else ""

def tier_badge(tier):
    c = TIER_COLORS.get(tier,"#666"); i = TIER_ICONS.get(tier,"⚪")
    return f'<span class="tag" style="background:{c}22;color:{c};border:1px solid {c}55">{i} {tier}</span>'

SESSION = requests.Session()
SESSION.headers.update({"User-Agent":"Protellect/2.0 research@protellect.com","Accept":"application/json"})

# ── API helpers ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_uniprot(gene: str) -> dict:
    base = {"found":False,"uid":"","pname":"","length":0,"function":"","subcellular":[],"tissue":"",
            "domains":[],"is_gpcr":False,"g_protein":"","natural_variants":[],"n_tm":0,
            "pdb_ids":[],"omim":"","ensembl_id":"","disease_comments":[]}
    for q in [f'gene_exact:{gene} AND organism_id:9606 AND reviewed:true',
               f'gene:{gene} AND organism_id:9606 AND reviewed:true']:
        try:
            r = SESSION.get("https://rest.uniprot.org/uniprotkb/search",params={"query":q,"format":"json","size":1},timeout=12)
            if r.status_code==200 and r.json().get("results"):
                base["uid"]=r.json()["results"][0]["primaryAccession"]; base["found"]=True; break
        except: pass
    if not base["found"]: return base
    try:
        e = SESSION.get(f"https://rest.uniprot.org/uniprotkb/{base['uid']}",params={"format":"json"},timeout=20).json()
        if not e: return base
        base["pname"] = e.get("proteinDescription",{}).get("recommendedName",{}).get("fullName",{}).get("value","")
        base["length"] = e.get("sequence",{}).get("length",0)
        for c in e.get("comments",[]):
            ct=c.get("commentType","")
            if ct=="FUNCTION": base["function"]=c.get("texts",[{}])[0].get("value","")[:600]
            elif ct=="SUBCELLULAR LOCATION":
                for loc in c.get("subcellularLocations",[]): 
                    v=loc.get("location",{}).get("value","")
                    if v and v not in base["subcellular"]: base["subcellular"].append(v)
            elif ct=="TISSUE SPECIFICITY": base["tissue"]=c.get("texts",[{}])[0].get("value","")[:500]
            elif ct=="DISEASE":
                for d in c.get("diseases",[]): base["disease_comments"].append(d.get("disease",{}).get("diseaseName",{}).get("value",""))
        for f in e.get("features",[]):
            ft=f.get("type",""); loc=f.get("location",{}); s=loc.get("start",{}).get("value"); en=loc.get("end",{}).get("value",s)
            if s is None: continue
            s,en=int(s),int(en); desc=f.get("description","")
            if ft in ("Domain","Region","Zinc finger","Transmembrane","Repeat","Motif"):
                base["domains"].append({"start":s,"end":en,"name":desc,"type":ft})
            if ft=="Transmembrane": base["n_tm"]+=1
            elif ft=="Natural variant":
                orig=f.get("alternativeSequence",{}).get("originalSequence","")
                var=f.get("alternativeSequence",{}).get("alternativeSequences",[""])[0]
                is_d=any(x in desc.lower() for x in ("disease","pathogenic","disorder","syndrome","myopathy"))
                base["natural_variants"].append({"pos":s,"orig":orig,"var":var,"note":desc,"disease":is_d,"source":"UniProt"})
        for xr in e.get("uniProtKBCrossReferences",[]):
            db=xr.get("database",""); xid=xr.get("id","")
            if db=="PDB": base["pdb_ids"].append(xid)
            elif db=="OMIM": base["omim"]=xid
            elif db=="Ensembl" and not base["ensembl_id"]: base["ensembl_id"]=xid
        kws=" ".join(kw.get("value","").lower() for kw in e.get("keywords",[]))
        base["is_gpcr"]=any(k in kws for k in ["g protein-coupled","gpcr","muscarinic","adrenergic","dopamine receptor","serotonin receptor"]) or base["n_tm"]==7
        if base["is_gpcr"]:
            gmap={"CHRM1":"Gq/11","CHRM2":"Gi/o","CHRM3":"Gq/11","ADRB1":"Gs","ADRB2":"Gs","DRD1":"Gs","DRD2":"Gi/o","HTR1A":"Gi/o","HTR2A":"Gq/11"}
            base["g_protein"]=gmap.get(gene.upper(),"")
    except: pass
    return base

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_clinvar(gene: str) -> dict:
    r={"germline_pathogenic":[],"germline_lp":[],"germline_benign":[],"germline_vus":[],"somatic":[],"all":[],"diseases":[],"n_path":0,"n_somatic":0}
    try:
        s=SESSION.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                      params={"db":"clinvar","term":f"{gene}[gene] AND single_gene[prop]","retmax":500,"retmode":"json","tool":"protellect","email":"r@protellect.com"},timeout=12)
        if not s or s.status_code!=200: return r
        ids=s.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return r
        time.sleep(0.3)
        for i in range(0,min(len(ids),500),100):
            batch=ids[i:i+100]; time.sleep(0.3)
            sm=SESSION.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                           params={"db":"clinvar","id":",".join(batch),"retmode":"json","tool":"protellect","email":"r@protellect.com"},timeout=20)
            if not sm or sm.status_code!=200: continue
            doc=sm.json().get("result",{})
            for vid in doc.get("uids",[]):
                e=doc.get(vid,{})
                gs=e.get("germline_classification",{}).get("description","").strip()
                ss=e.get("somatic_clinical_impact",{}).get("description","").strip()
                is_s=bool(ss and not gs)
                title=e.get("title",""); conds=[c.get("trait_name","") for c in e.get("trait_set",[])]
                stars=e.get("review_status_label",""); sig=gs or ss or ""
                m=re.search(r'[A-Z\*](\d+)[A-Za-z\*=]',title); pos=int(m.group(1)) if m else 0
                v={"id":vid,"title":title,"sig":sig,"germline":gs,"somatic":ss,"is_somatic":is_s,
                   "conditions":[c for c in conds if c],"stars":stars,"pos":pos,"gene":gene}
                r["all"].append(v)
                for c in conds:
                    if c and c not in r["diseases"]: r["diseases"].append(c)
                if is_s: r["somatic"].append(v); r["n_somatic"]+=1
                else:
                    sl=sig.lower()
                    if "pathogenic" in sl and "likely" not in sl and "benign" not in sl:
                        r["germline_pathogenic"].append(v); r["n_path"]+=1
                    elif "likely pathogenic" in sl:
                        r["germline_lp"].append(v); r["n_path"]+=1
                    elif "benign" in sl: r["germline_benign"].append(v)
                    elif "uncertain" in sl or "vus" in sl: r["germline_vus"].append(v)
    except: pass
    return r

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_alphafold(uid: str, gene: str="") -> tuple:
    if not uid: return None,""
    try:
        r=SESSION.get(f"https://alphafold.ebi.ac.uk/api/prediction/{uid}",timeout=12)
        if r.status_code==200 and r.json():
            url=r.json()[0].get("pdbUrl","")
            if url:
                pr=SESSION.get(url,timeout=20)
                if pr.status_code==200: return pr.text[:400000], f"AlphaFold DB · {uid}"
    except: pass
    # Try PDB
    try:
        r2=SESSION.get("https://rest.uniprot.org/uniprotkb/search",
                       params={"query":f"accession:{uid}","format":"json","size":1,"fields":"xref_pdb"},timeout=10)
        if r2.status_code==200:
            for xr in r2.json().get("results",[{}])[0].get("uniProtKBCrossReferences",[]):
                if xr.get("database")=="PDB":
                    pid=xr.get("id","")
                    pr=SESSION.get(f"https://files.rcsb.org/download/{pid}.pdb",timeout=15)
                    if pr.status_code==200: return pr.text[:400000], f"PDB {pid} (experimental)"
    except: pass
    # Try by gene name directly (AlphaFold has gene-based search)
    if gene:
        try:
            # Try common UniProt accessions for known proteins
            _KNOWN_UID = {"FLNA":"P21333","FLNB":"O75369","FLNC":"Q14315","CHRM2":"P08172",
                          "CHRM3":"P20309","ARRB1":"P49407","ARRB2":"P32121","TP53":"P04637",
                          "BRCA1":"P38398","BRCA2":"P51587","EGFR":"P00533","KRAS":"P01116",
                          "MYH7":"P12883","LMNA":"P02545","TALN1":"Q9Y490","ITB3":"P05106"}
            fallback_uid = _KNOWN_UID.get(gene.upper(),"")
            if fallback_uid and fallback_uid != uid:
                r3=SESSION.get(f"https://alphafold.ebi.ac.uk/api/prediction/{fallback_uid}",timeout=12)
                if r3.status_code==200 and r3.json():
                    url3=r3.json()[0].get("pdbUrl","")
                    if url3:
                        pr3=SESSION.get(url3,timeout=25)
                        if pr3.status_code==200: return pr3.text[:400000], f"AlphaFold DB · {fallback_uid} ({gene})"
        except: pass
    return None,""

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_pubmed(gene: str, disease: str="", n: int=5) -> list:
    papers=[]; seen=set()
    for q in ([f'{gene}[gene] AND "{disease}"[tiab]'] if disease else [])+[f'{gene}[gene] AND "pathogenic variant" AND "human"[tiab]']:
        if len(papers)>=n: break
        try:
            s=SESSION.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                          params={"db":"pubmed","term":q,"retmax":3,"retmode":"json","sort":"relevance","tool":"protellect","email":"r@protellect.com"},timeout=10)
            if not s or s.status_code!=200: continue
            ids=[i for i in s.json().get("esearchresult",{}).get("idlist",[]) if i not in seen]; seen.update(ids)
            if not ids: continue
            time.sleep(0.25)
            sm=SESSION.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                           params={"db":"pubmed","id":",".join(ids),"retmode":"json","tool":"protellect","email":"r@protellect.com"},timeout=10)
            if not sm or sm.status_code!=200: continue
            rd=sm.json().get("result",{})
            for pid in rd.get("uids",[]):
                en=rd.get(pid,{})
                papers.append({"pmid":pid,"title":en.get("title","")[:90],"journal":en.get("fulljournalname",""),"year":en.get("pubdate","")[:4],"url":f"https://pubmed.ncbi.nlm.nih.gov/{pid}/"})
        except: pass
    return papers[:n]

# ── 3D Viewer ────────────────────────────────────────────────────────────────
def make_viewer(pdb: str, scored_res: dict, cv_positions: dict, residue_annotations: dict=None, gene: str='', w=680, h=450) -> str:
    if not pdb or len(pdb)<100:
        return f"<html><body style='margin:0;background:#050810;display:flex;align-items:center;justify-content:center;height:{h}px;font-family:JetBrains Mono,monospace;color:#334;text-align:center;font-size:12px'>AlphaFold structure loading...<br><span style='font-size:10px;color:#1a2040;display:block;margin-top:8px'>Query in progress</span></body></html>"
    esc=pdb[:400000].replace("\\","\\\\").replace("`","\\`").replace("${","\\${")
    res_list=[]
    for line in pdb.split('\n'):
        if line.startswith('ATOM'):
            try: res_list.append(int(line[22:26].strip()))
            except: pass
    zoom=f"{min(res_list)}-{max(res_list)}" if res_list else "1-999"
    sph=[]
    for r,d in scored_res.items():
        sph.append("v.addStyle({resi:%d},{sphere:{color:'%s',radius:%s,opacity:0.95}});" % (r,d["c"],d["r"]))
    for p in cv_positions:
        if int(p) not in scored_res:
            sph.append("v.addStyle({resi:%d},{sphere:{color:'#FF2255',radius:0.7,opacity:0.88}});" % int(p))
    sph_str="\n".join(sph)
    cv_js = json.dumps({str(k):v for k,v in cv_positions.items()})
    annot_src = residue_annotations if residue_annotations is not None else scored_res
    annot_js = json.dumps({str(k):v for k,v in annot_src.items()})
    gene_safe = gene.replace("'","")
    return f"""<!DOCTYPE html><html><head>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#050810;overflow:hidden;font-family:'JetBrains Mono',monospace}}
#wrap{{display:flex;height:{h}px}}
#vw{{flex:1;min-width:0}}
#panel{{width:0;background:#070c1a;border-left:2px solid #1a2540;overflow:hidden;transition:width 0.22s}}
#panel.open{{width:230px}}
#pi{{padding:14px;width:230px}}
.pt{{font-size:9px;text-transform:uppercase;letter-spacing:0.16em;color:#334;margin:8px 0 3px}}
.pv{{font-size:11px;color:#c0d0f0;line-height:1.6;margin-bottom:3px}}
.badge{{display:inline-block;padding:2px 9px;border-radius:10px;font-size:9px;font-weight:600;margin:2px}}
.exp-box{{background:#0a1020;border:1px solid #1a2540;border-radius:6px;padding:7px 9px;margin-top:5px;font-size:10px;color:#6080a0;line-height:1.6}}
.hint{{position:absolute;bottom:8px;left:50%;transform:translateX(-50%);background:#070c1acc;border:1px solid #1a2540;border-radius:20px;padding:4px 16px;font-size:9px;color:#334;pointer-events:none;white-space:nowrap}}
</style></head><body style="position:relative">
<div id="wrap"><div id="vw"></div><div id="panel"><div id="pi">
<div id="pc" style="color:#1a2540;font-size:10px;text-align:center;padding-top:50px">Click a residue<br>sphere for triage</div>
</div></div></div>
<div class="hint">● Click sphere for triage · Red = ClinVar pathogenic · Orange = HIGH · Blue = LOW</div>
<script>
const pdb=`{esc}`;const CV={cv_js};const ANNOT=__ANNOT_JSON__;const GENE='{gene_safe}';
let v=$3Dmol.createViewer('vw',{{backgroundColor:'#050810',antialias:true}});
v.addModel(pdb,'pdb');
v.setStyle({{}},{{cartoon:{{color:'spectrum',opacity:0.88,thickness:0.5,smoothSheet:true}}}});
v.addSurface($3Dmol.VDW,{{opacity:0.03,color:'#3060ff'}});
{sph_str}
function applyS(){{v.setStyle({{}},{{cartoon:{{color:'spectrum',opacity:0.88,thickness:0.5,smoothSheet:true}}}});{sph_str}}}
v.setHoverable({{}},true,function(a){{
  if(!a||!a.resi)return;
  const cv=CV[String(a.resi)]||{{}};const an=ANNOT[String(a.resi)]||{{}};
  const p=an.p||'';const pc=p==='HIGH'?'#FF4444':p==='MEDIUM'?'#FFA500':'#60a5fa';
  document.querySelector('.hint').innerHTML='<b style="color:'+pc+'">['+p+']</b> '+a.resn+'-'+a.resi+(cv.sig?' · '+cv.sig.slice(0,30):'');
}},function(){{document.querySelector('.hint').innerHTML='● Click sphere for triage · Red = ClinVar pathogenic · Orange = HIGH · Blue = LOW';}});
v.setClickable({{}},true,function(atom){{
  if(!atom||!atom.resi)return;
  const r=atom.resi,resn=atom.resn||'';
  const cv=CV[String(r)]||{{}};const an=ANNOT[String(r)]||{{}};
  const p=an.p||'—',sc=an.s||'—',hy=an.h||'';
  const pc=p==='HIGH'?'#FF4444':p==='MEDIUM'?'#FFA500':'#60a5fa';
  const cvH=cv.sig?`<div class="pt">ClinVar Germline</div><div class="pv" style="color:#FF8899">${{cv.sig}}</div><div class="pv" style="color:#8090b0">${{(cv.conds||[]).slice(0,2).join(' · ')}}</div>`:`<div class="pt">ClinVar</div><div class="pv" style="color:#1a2540">No germline pathogenic at pos ${{r}}</div>`;
  const expT=p==='HIGH'?'ITC binding assay — gold standard. Kd, ΔH, ΔS simultaneously. No artefacts.':p==='MEDIUM'?'Thermal shift DSF — confirm ΔTm vs WT. Expect 3-8°C. Then ITC if confirmed.':'ClinVar + gnomAD check first. Free, &lt;1h. Establish genomic context.';
  document.getElementById('pc').innerHTML=`
    <div class="pt" style="margin-top:0;color:#334">${{GENE}} · Pos ${{r}}</div>
    <div style="font-size:14px;font-weight:600;color:#e0f0ff;margin:4px 0">${{resn}}-${{r}}</div>
    <span class="badge" style="background:${{pc}}22;color:${{pc}};border:1px solid ${{pc}}55">${{p}} PRIORITY</span>
    <span class="badge" style="background:#0a1020;color:#6080a0;border:1px solid #1a2540">score ${{typeof sc==='number'?sc.toFixed(3):sc}}</span>
    ${{cvH}}
    ${{hy?`<div class="pt">Hypothesis</div><div class="pv">${{hy.slice(0,140)}}</div>`:''}}
    <div class="pt">Recommended experiment</div>
    <div class="exp-box">${{expT}}</div>
    <div style="margin-top:8px;font-size:8px;color:#1a2540;text-align:center">Click another residue to compare</div>`;
  document.getElementById('panel').classList.add('open');
  applyS();v.addStyle({{resi:r}},{{sphere:{{color:'#ffffff',radius:1.5,opacity:1}}}});v.render();
}});
v.zoomTo({{resi:'{zoom}'}});v.spin(false);v.render();
</script></body></html>"""

# ── Tutorial dialog ─────────────────────────────────────────────────────────
@st.dialog("How to use Protellect")
def show_tutorial():
    if LOGO:
        st.markdown(f'<img src="{LOGO}" style="height:44px;object-fit:contain;border-radius:8px;margin-bottom:10px">', unsafe_allow_html=True)
    st.markdown("### Experimental Intelligence Layer")
    st.markdown("**Purpose:** Eliminate wasted resources in bio-experimentation by triage-ranking proteins and mutations before any bench work — using human genetic evidence as the primary filter.")
    for i,(t,d) in enumerate([
        ("Enter protein in sidebar","Type any gene/protein name (FLNA, CHRM2, TP53, ARRB1, etc.). Protellect fetches AlphaFold structure, all ClinVar germline variants, UniProt biology, and PubMed papers automatically."),
        ("Upload wet lab data (optional)","CSV/TSV/Excel: DMS, CRISPR screens, RNA-seq, proteomics, variant data. Any format. If no data is uploaded, the system works purely from ClinVar + UniProt."),
        ("Read the sidebar first","The sidebar shows disease ranking, ClinVar tier, wet lab summary, and protein-specific experiments before you even look at the tabs."),
        ("Tab 1 — Triage","AlphaFold structure with clickable spheres. Each click shows priority, ClinVar evidence, hypothesis, and the right experiment for that residue."),
        ("Tab 2 — Case Study","Tissue expression, genomic breakdown, GPCR association, and full disease list separated into somatic vs germline."),
        ("Tab 3 — Protein Explorer","Large interactive structure. Click residue → mutation animation with slider. Below: every disease caused by each mutation."),
        ("Tab 4 — Therapy & Experiments","Detailed experiment protocols with costs, which mutations to focus on, which to neglect, and how to reach your research goal."),
    ], 1):
        c1,c2=st.columns([0.06,0.94])
        with c1: st.markdown(f'<div style="width:24px;height:24px;border-radius:50%;background:#FF4C4C22;color:#FF4C4C;border:1px solid #FF4C4C44;display:flex;align-items:center;justify-content:center;font-family:JetBrains Mono;font-size:11px;font-weight:600;margin-top:2px">{i}</div>', unsafe_allow_html=True)
        with c2: st.markdown(f"**{t}**  \n{d}")
        st.markdown("")
    st.markdown(f'{paper_chip("king_2024")} {paper_chip("minikel_2021")} {paper_chip("plenge_2016")}', unsafe_allow_html=True)
    if st.button("Start →", type="primary", use_container_width=True):
        st.session_state.tut_seen = True
        st.rerun()

if "tut_seen" not in st.session_state: st.session_state.tut_seen = False
if not st.session_state.tut_seen: show_tutorial()

# ── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    cl,ct,ch=st.columns([1,3,1])
    with cl:
        if LOGO: st.markdown(f'<img src="{LOGO}" style="width:32px;height:32px;object-fit:contain;border-radius:6px;margin-top:6px">', unsafe_allow_html=True)
    with ct: st.markdown("### Protellect")
    with ch:
        if st.button("❓"): show_tutorial()
    st.markdown('<p style="font-family:JetBrains Mono;font-size:0.68rem;color:#1a2040;margin:-4px 0 0">Experimental Intelligence · v2.0</p>', unsafe_allow_html=True)
    if ML_AVAILABLE: st.markdown('<div style="background:#0a1020;border:1px solid #1a2540;border-radius:6px;padding:5px 10px;font-size:0.7rem;color:#60a5fa;margin:6px 0;font-family:JetBrains Mono">🤖 ML scoring active</div>', unsafe_allow_html=True)
    st.divider()

    st.markdown('<div class="label">Protein / Gene</div>', unsafe_allow_html=True)
    protein_in = st.text_input("Gene", placeholder="FLNA · CHRM2 · ARRB1 · TP53 · BRCA1...", label_visibility="collapsed", key="prot_in")

    st.markdown('<div class="label">Research goal</div>', unsafe_allow_html=True)
    goal_in = st.text_input("Goal", placeholder="find drug targets in cardiomyopathy", label_visibility="collapsed", key="goal_in")

    st.markdown('<div class="label">Disease context</div>', unsafe_allow_html=True)
    dis_in = st.text_input("Disease", placeholder="dilated cardiomyopathy", label_visibility="collapsed", key="dis_in")

    st.markdown('<div class="label">Direction</div>', unsafe_allow_html=True)
    dir_in = st.selectbox("Direction", ["Not specified","Drug target discovery","LOF analysis","GOF analysis","Clinical variant interpretation","Basic science"], label_visibility="collapsed")

    st.divider()
    st.markdown('<div class="label">Wet Lab Data (optional)</div>', unsafe_allow_html=True)
    upfile = st.file_uploader("Upload", type=["csv","tsv","xlsx","xls","txt"], label_visibility="collapsed")
    use_sample = st.checkbox("Use sample TP53 DMS data", value=not bool(upfile) and not bool(protein_in))

    st.markdown('<div class="label">Sensitivity</div>', unsafe_allow_html=True)
    sensitivity = st.selectbox("Sens", ["Standard (0.75/0.40)","Strict (0.85/0.55)","Permissive (0.65/0.30)"], label_visibility="collapsed")
    ht,mt = {"Standard (0.75/0.40)":(0.75,0.40),"Strict (0.85/0.55)":(0.85,0.55),"Permissive (0.65/0.30)":(0.65,0.30)}[sensitivity]
    use_db = st.checkbox("Live DB (UniProt · ClinVar · AlphaFold)", value=True)
    run_btn = st.button("▶ Analyse", type="primary", use_container_width=True)

    ctx = {"study_goal":goal_in,"disease_context":dis_in,"hypothesis_direction":dir_in,"protein_of_interest":protein_in}
    # Normalize gene name — handle spaces, dashes, common aliases
    _raw = protein_in.strip().upper()
    gene = re.sub(r'\s+', '', _raw)   # remove all whitespace: "CHRM 2" → "CHRM2"
    gene = gene.replace('-','')          # "MYH-7" → "MYH7"
    # Common aliases
    _aliases = {"BETAARRESTIN1":"ARRB1","BETAARRESTIN2":"ARRB2","FILAMIN":"FLNA",
                "FILAMINC":"FLNC","FILAMINB":"FLNB","TALIN":"TALN1",
                "MUSC2":"CHRM2","MUSC3":"CHRM3","ACM2":"CHRM2","ACM3":"CHRM3",
                "P53":"TP53","BCRA1":"BRCA1","BCRA2":"BRCA2"}
    gene = _aliases.get(gene, gene)

    # ── SIDEBAR RESULTS ────────────────────────────────────────────────────
    if "ss_gene" in st.session_state and st.session_state.ss_gene:
        sg = st.session_state.ss_gene
        sgt = GT.get(sg,())
        if sgt:
            n_p,plen,pname,chrom,tier,diseases = sgt
        else:
            n_p=st.session_state.get("ss_n_path",0); tier=st.session_state.get("ss_tier","UNKNOWN")
            pname=st.session_state.get("ss_pname",""); chrom=""; diseases=""
            plen=st.session_state.get("ss_plen",0)
        tc=TIER_COLORS.get(tier,"#666"); ti=TIER_ICONS.get(tier,"⚪")
        dbr=calculate_dbr(n_p,plen)
        st.divider()
        st.markdown(f"""
        <div style="background:#070c1a;border:1px solid {tc}44;border-radius:10px;padding:12px 14px;margin-bottom:8px">
          <div style="font-family:JetBrains Mono;font-size:0.62rem;color:{tc};text-transform:uppercase;margin-bottom:5px">{ti} {tier} · DBR {f"{dbr:.3f}" if dbr else "—"}</div>
          <div style="font-size:0.88rem;font-weight:600;color:#e0f0ff;margin-bottom:2px">{sg}</div>
          <div style="font-size:0.72rem;color:#445;margin-bottom:8px">{pname[:38]}</div>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div><div style="font-size:1.5rem;font-weight:700;font-family:JetBrains Mono;color:{tc}">{n_p}</div>
            <div style="font-size:0.58rem;color:#334;text-transform:uppercase">Germline pathogenic</div></div>
            <div style="text-align:right;font-size:0.7rem;color:{tc};font-family:JetBrains Mono">{chrom}</div>
          </div>
          <div style="background:#0a0d18;border-radius:3px;height:5px;overflow:hidden;margin-top:6px">
            <div style="width:{min(100,int(min(n_p/plen*100*20,100) if plen else 0))}%;height:100%;background:{tc};border-radius:3px"></div>
          </div>
        </div>""", unsafe_allow_html=True)

        # Disease breakdown
        if diseases:
            st.markdown('<div class="label">Disease breakdown</div>', unsafe_allow_html=True)
            for d in diseases.split("·")[:5]:
                d=d.strip()
                if d: st.markdown(f'<div style="padding:4px 8px;margin-bottom:3px;background:#0a0810;border:1px solid #FF4C4C22;border-radius:5px;font-size:0.75rem;color:#e0d0d0">● {d}</div>', unsafe_allow_html=True)

        # Protein-specific next experiment from protein_data
        pd_sb = get_protein_info(sg)
        exps_sb = pd_sb.get("experiments_specific",[])
        if exps_sb:
            st.markdown('<div class="label" style="margin-top:8px">Recommended experiment</div>', unsafe_allow_html=True)
            ne=exps_sb[0]
            st.markdown(f"""<div style="background:#080c08;border:1px solid #4CAF5033;border-radius:8px;padding:9px 11px">
              <div style="font-family:JetBrains Mono;font-size:0.6rem;color:#4CAF50;text-transform:uppercase;margin-bottom:3px">Level {ne.get('level','?')}</div>
              <div style="font-size:0.75rem;color:#c0e0c0;font-weight:500;margin-bottom:2px">{ne['name'][:40]}</div>
              <div style="font-size:0.68rem;color:#446">{ne.get('rationale','')[:70]}...</div>
            </div>""", unsafe_allow_html=True)

        # Wet lab summary
        if "ss_stats" in st.session_state and st.session_state.ss_stats:
            st=st  # keep reference
            stats=st.session_state.ss_stats
            st.markdown('<div class="label" style="margin-top:8px">Wet lab summary</div>', unsafe_allow_html=True)
            st.markdown(f"""<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px">
              <div style="background:#0a0810;border:1px solid #FF4C4C33;border-radius:6px;padding:7px;text-align:center">
                <div style="font-size:1.2rem;font-weight:700;font-family:JetBrains Mono;color:#FF4C4C">{stats.get("high_priority",0)}</div>
                <div style="font-size:0.58rem;color:#334;text-transform:uppercase">HIGH</div>
              </div>
              <div style="background:#0a0d10;border:1px solid #FFA50033;border-radius:6px;padding:7px;text-align:center">
                <div style="font-size:1.2rem;font-weight:700;font-family:JetBrains Mono;color:#FFA500">{stats.get("medium_priority",0)}</div>
                <div style="font-size:0.58rem;color:#334;text-transform:uppercase">MED</div>
              </div>
              <div style="background:#0a0d18;border:1px solid #60a5fa33;border-radius:6px;padding:7px;text-align:center">
                <div style="font-size:1.2rem;font-weight:700;font-family:JetBrains Mono;color:#60a5fa">{stats.get("low_priority",0)}</div>
                <div style="font-size:0.58rem;color:#334;text-transform:uppercase">LOW</div>
              </div>
            </div>""", unsafe_allow_html=True)

        st.markdown(f'<div style="margin-top:8px">{paper_chip("king_2024")}</div>', unsafe_allow_html=True)

# ── RUN ANALYSIS ─────────────────────────────────────────────────────────────
if run_btn or (gene and "ss_gene" not in st.session_state):
    if not gene:
        st.sidebar.error("Enter a gene/protein name first.")
    else:
        with st.spinner(f"Loading {gene}..."):
            ss = st.session_state
            ss.ss_gene = gene
            ss.ss_pdata = get_protein_info(gene)
            ss.ss_uni = fetch_uniprot(gene) if use_db else {}
            ss.ss_cv  = fetch_clinvar(gene)  if use_db else {}
            ss.ss_pubmed = fetch_pubmed(gene, dis_in) if use_db else []

            # Ground truth override
            gt_entry = GT.get(gene,())
            if gt_entry:
                ss.ss_n_path = max(gt_entry[0], ss.ss_cv.get("n_path",0))
                ss.ss_plen   = gt_entry[1] or ss.ss_uni.get("length",0)
                ss.ss_pname  = gt_entry[2] or ss.ss_uni.get("pname","")
                ss.ss_tier   = gt_entry[4]
                ss.ss_diseases = gt_entry[5]
            else:
                n_api = ss.ss_cv.get("n_path",0)
                plen  = ss.ss_uni.get("length",0) or 1
                ss.ss_n_path = n_api
                ss.ss_plen   = plen
                ss.ss_pname  = ss.ss_uni.get("pname","")
                dbr = calculate_dbr(n_api, plen)
                ss.ss_tier   = assign_genomic_tier(dbr, n_api)
                ss.ss_diseases = " · ".join(ss.ss_cv.get("diseases",[])[:5])

            # AlphaFold
            uid = ss.ss_uni.get("uid","") if ss.ss_uni else ""
            ss.ss_pdb, ss.ss_pdb_src = fetch_alphafold(uid, gene) if use_db else (None,"")

            # Wet lab scoring
            ss.ss_scored = None; ss.ss_stats = None; ss.ss_info = None; ss.ss_pathways = None
            if upfile:
                df_raw = load_file(upfile)
                v, err = validate_dataframe(df_raw)
                if v:
                    ss.ss_info     = detect_dataset_info(df_raw, ctx)
                    ss.ss_scored   = score_residues(df_raw, context=ctx, high_t=ht, med_t=mt)
                    ss.ss_stats    = get_summary_stats(ss.ss_scored)
                    ss.ss_pathways = generate_top_pathways(ss.ss_scored, ss.ss_info, ctx)
                else:
                    st.sidebar.error(f"Data error: {err}")
            elif use_sample:
                try:
                    df_raw = pd.read_csv("sample_data/example.csv")
                    ss.ss_info     = detect_dataset_info(df_raw, ctx)
                    ss.ss_scored   = score_residues(df_raw, context=ctx, high_t=ht, med_t=mt)
                    ss.ss_stats    = get_summary_stats(ss.ss_scored)
                    ss.ss_pathways = generate_top_pathways(ss.ss_scored, ss.ss_info, ctx)
                except: pass

# ── TABS ─────────────────────────────────────────────────────────────────────
tab1,tab2,tab3,tab4 = st.tabs(["🧬 Triage System","📊 Case Study","⚗️ Protein Explorer","💊 Therapy & Experiments"])

# Shorthand
def ss(): return st.session_state


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — TRIAGE SYSTEM
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    if "ss_gene" not in st.session_state or not st.session_state.ss_gene:
        # Welcome screen
        st.markdown(f"""
        <div style="max-width:900px;margin:20px auto">
          <div style="text-align:center;padding:40px 20px;background:#070c1a;border:1px solid #1a2040;border-radius:16px;margin-bottom:20px">
            {"" if not LOGO else f'<img src="{LOGO}" style="height:52px;object-fit:contain;border-radius:8px;margin-bottom:12px"><br>'}
            <div style="font-family:JetBrains Mono;font-size:1.6rem;font-weight:700;color:#e0f0ff;margin-bottom:6px">Protellect</div>
            <div style="font-family:JetBrains Mono;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.18em;color:#60a5fa;margin-bottom:14px">ClinVar-First Drug Target Validation</div>
            <p style="font-size:0.87rem;color:#445;max-width:520px;margin:0 auto;line-height:1.8">Enter a gene/protein in the sidebar. The system analyses any protein against ClinVar germline evidence — wet lab data is optional but enhances the triage.</p>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:16px">
            <div style="background:#070c1a;border:1px solid #FF4C4C33;border-radius:10px;padding:14px">
              <div style="font-family:JetBrains Mono;font-size:0.6rem;text-transform:uppercase;color:#FF4C4C;margin-bottom:6px">Try: Critical proteins</div>
              <div style="font-size:0.77rem;color:#c0d0f0">FLNA · FLNC · TP53 · BRCA1 · MYH7</div>
              <div style="font-size:0.7rem;color:#334;margin-top:4px">847–8000 ClinVar pathogenic variants each</div>
            </div>
            <div style="background:#070c1a;border:1px solid #FFA50033;border-radius:10px;padding:14px">
              <div style="font-family:JetBrains Mono;font-size:0.6rem;text-transform:uppercase;color:#FFA500;margin-bottom:6px">Try: High / Rare Mendelian</div>
              <div style="font-size:0.77rem;color:#c0d0f0">CHRM2 · CHRM3 · LMNA · ITB3</div>
              <div style="font-size:0.7rem;color:#334;margin-top:4px">Confirmed disease genes — rare to common</div>
            </div>
            <div style="background:#070c1a;border:1px solid #66666633;border-radius:10px;padding:14px">
              <div style="font-family:JetBrains Mono;font-size:0.6rem;text-transform:uppercase;color:#666;margin-bottom:6px">Try: Scaffold pattern</div>
              <div style="font-size:0.77rem;color:#778">ARRB1 · ARRB2 · TALN1 · TALN2</div>
              <div style="font-size:0.7rem;color:#334;margin-top:4px">Zero germline pathogenic variants — do not target</div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)
    if "ss_gene" in st.session_state:
        gene      = st.session_state.ss_gene
        n_path    = st.session_state.get("ss_n_path", 0)
        tier      = st.session_state.get("ss_tier", "UNKNOWN")
        tc        = TIER_COLORS.get(tier,"#666"); ti=TIER_ICONS.get(tier,"⚪")
        uni       = st.session_state.ss_uni or {}
        cv        = st.session_state.ss_cv  or {}
        pdb       = st.session_state.ss_pdb
        pdb_src   = st.session_state.ss_pdb_src or ""
        scored    = st.session_state.ss_scored
        stats     = st.session_state.ss_stats
        diseases_str = st.session_state.ss_diseases or ""
        pname     = st.session_state.ss_pname or gene
        pdata     = st.session_state.ss_pdata or {}
        pc_col    = "priority_final" if scored is not None and "priority_final" in scored.columns else "priority"

        # ── BIG DISEASE BANNER ──────────────────────────────────────────────────
        if tier == "NEUTRAL":
            banner_h = f"⚪ NO GERMLINE DISEASE ASSOCIATION"
            banner_d = f"{gene} has zero confirmed germline pathogenic variants in ClinVar. Humans with broken versions are healthy. This is the β-arrestin/Talin pattern."
            banner_a = "DO NOT pursue as primary drug target. Study interaction partners with confirmed ClinVar burden."
        elif tier == "CRITICAL":
            banner_h = f"🔴 CRITICAL — Essential disease gene"
            banner_d = f"{n_path} confirmed germline pathogenic variants. Diseases: {diseases_str[:120]}"
            banner_a = f"Strong human genetic justification for drug development. {paper_chip('king_2024')}"
        elif tier == "HIGH":
            banner_h = f"🟠 HIGH — Confirmed disease gene"
            banner_d = f"{n_path} confirmed germline pathogenic variants. {diseases_str[:100]}"
            banner_a = "Solid genetic support. Proceed with target validation."
        elif tier == "LOW":
            banner_h = f"🟡 CONFIRMED RARE MENDELIAN DISEASE GENE"
            banner_d = f"{n_path} pathogenic variant(s). Low count = disease rarity, not protein dispensability."
            banner_a = "Rare disease strategy. Orphan drug pathway applies."
        else:
            banner_h = "❓ GENOMICALLY UNCHARACTERISED"; banner_d = "Insufficient ClinVar data."; banner_a = "Run ClinVar query before any wet lab investment."

        st.markdown(f"""
        <div style="background:#070c1a;border:2px solid {tc};border-radius:14px;padding:20px 24px;margin-bottom:18px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
            <div style="flex:1">
              <div style="font-family:JetBrains Mono;font-size:1rem;font-weight:700;color:{tc};margin-bottom:6px">{banner_h}</div>
              <div style="font-size:0.87rem;color:#c0d0f0;font-weight:500;margin-bottom:4px">{gene} — {pname}</div>
              <div style="font-size:0.81rem;color:#556;line-height:1.7">{banner_d}</div>
              <div style="margin-top:10px;font-size:0.8rem;color:#4CAF50">{banner_a}</div>
            </div>
            <div style="text-align:right;min-width:130px">
              <div style="font-size:2.2rem;font-weight:700;font-family:JetBrains Mono;color:{tc}">{n_path}</div>
              <div style="font-size:0.6rem;color:#334;text-transform:uppercase">Germline pathogenic</div>
              <div style="font-size:0.72rem;color:{tc};font-family:JetBrains Mono;margin-top:3px">DBR {f"{calculate_dbr(n_path, st.session_state.ss_plen):.3f}" if st.session_state.ss_plen else "—"}</div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

        # ── Structure + triage ──────────────────────────────────────────────────
        scol, rcol = st.columns([1.4, 1], gap="large")

        with scol:
            st.markdown(f'<div class="label">AlphaFold Structure — {gene}</div>', unsafe_allow_html=True)
            if pdb_src: st.caption(f"🏗️ {pdb_src}")

            cmap={"HIGH":"#FF4C4C","MEDIUM":"#FFA500","LOW":"#60a5fa"}
            rmap={"HIGH":1.2,"MEDIUM":0.8,"LOW":0.45}
            rs={}; annot_map={}

            # ClinVar pathogenic positions
            cv_pos={}
            for v2 in cv.get("germline_pathogenic",[]) + cv.get("germline_lp",[]):
                pos2=v2.get("pos",0)
                if not pos2:
                    m2=re.search(r'[A-Z](\d+)[A-Z=*]', v2.get("title",""))
                    if m2: pos2=int(m2.group(1))
                if pos2>0:
                    cv_pos[pos2]={"sig":v2.get("germline","") or v2.get("sig",""),"conds":v2.get("conditions",[])}

            if scored is not None and pdb:
                pdb_res=set()
                for line in pdb.split('\n'):
                    if line.startswith('ATOM'):
                        try: pdb_res.add(int(line[22:26].strip()))
                        except: pass
                upos=[int(r["residue_position"]) for _,r in scored.iterrows()]
                has_overlap = pdb_res and any(p in pdb_res for p in upos)
                for _,row in scored.iterrows():
                    pos3=int(row["residue_position"]); p3=str(row.get(pc_col,"LOW"))
                    hyp3=str(row.get("hypothesis",""))[:200]; sc3=float(row.get("normalized_score",0))
                    annot_map[pos3]={"p":p3,"s":round(sc3,3),"h":hyp3}
                    if has_overlap and pos3 in pdb_res:
                        rs[pos3]={"c":cmap.get(p3,"#60a5fa"),"r":rmap.get(p3,0.45)}
                    elif not has_overlap:
                        rs[pos3]={"c":cmap.get(p3,"#60a5fa"),"r":rmap.get(p3,0.45)*1.4}
            elif pdb and cv_pos:
                # Colour ClinVar pathogenic positions
                pdb_res2=set()
                for line in pdb.split('\n'):
                    if line.startswith('ATOM'):
                        try: pdb_res2.add(int(line[22:26].strip()))
                        except: pass
                for cpos in list(cv_pos.keys())[:60]:
                    if cpos in pdb_res2:
                        rs[cpos]={"c":"#FF4C4C","r":0.9}
                        annot_map[cpos]={"p":"HIGH","s":1.0,"h":f"ClinVar pathogenic at position {cpos}"}

            if pdb:
                components.html(make_viewer(pdb, rs, cv_pos, annot_map, gene, 690, 450), height=456)
            else:
                st.markdown(f"""<div style="background:#070c1a;border:1px solid #1a2040;border-radius:10px;height:380px;display:flex;align-items:center;justify-content:center;text-align:center;color:#1a2040;font-family:JetBrains Mono;font-size:12px">AlphaFold structure loading...<br><span style='font-size:10px;color:#0f1525;display:block;margin-top:8px'>Enable DB enrichment and click Analyse</span></div>""", unsafe_allow_html=True)
            st.markdown('<div style="display:flex;gap:16px;margin-top:5px;font-size:0.73rem;color:#334"><span><span style="color:#FF4C4C">●</span> HIGH / ClinVar pathogenic</span><span><span style="color:#FFA500">●</span> MEDIUM</span><span><span style="color:#60a5fa">●</span> LOW / Benign</span><span><span style="color:#fff">●</span> Selected residue</span></div>', unsafe_allow_html=True)

        with rcol:
            # Germline vs somatic counts
            n_gp=cv.get("n_path",0); n_s=cv.get("n_somatic",0); n_vus=len(cv.get("germline_vus",[]))
            n_b=len(cv.get("germline_benign",[]))
            st.markdown('<div class="label">ClinVar Evidence — Germline vs Somatic</div>', unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:#070c1a;border:1px solid {tc}44;border-radius:8px;padding:12px;margin-bottom:10px">
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">
                <div style="background:#0a0810;border:1px solid #FF4C4C33;border-radius:6px;padding:9px;text-align:center">
                  <div style="font-size:1.5rem;font-weight:700;font-family:JetBrains Mono;color:{tc}">{n_path}</div>
                  <div style="font-size:0.58rem;color:#334;text-transform:uppercase">Germline P/LP</div>
                  <div style="font-size:0.62rem;color:#445;margin-top:2px">Ground truth</div>
                </div>
                <div style="background:#0a0d10;border:1px solid #FFA50033;border-radius:6px;padding:9px;text-align:center">
                  <div style="font-size:1.5rem;font-weight:700;font-family:JetBrains Mono;color:#FFA500">{n_s}</div>
                  <div style="font-size:0.58rem;color:#334;text-transform:uppercase">Somatic only ⚠</div>
                  <div style="font-size:0.62rem;color:#445;margin-top:2px">Cancer cell mutations</div>
                </div>
              </div>
              <div style="font-size:0.7rem;color:#334;background:#050810;border-radius:4px;padding:6px 8px;line-height:1.6">
                Somatic = NOT inherited disease evidence. Only germline variants validate a drug target.
                {paper_chip("minikel_2021")}
              </div>
            </div>""", unsafe_allow_html=True)

            # Disease list
            if diseases_str:
                st.markdown('<div class="label">Confirmed diseases</div>', unsafe_allow_html=True)
                for d in diseases_str.split("·")[:6]:
                    d=d.strip()
                    if d: st.markdown(f'<div style="padding:5px 9px;margin-bottom:3px;background:#0c0810;border:1px solid #FF4C4C22;border-radius:5px;font-size:0.78rem;color:#e0d0e0">● {d}</div>', unsafe_allow_html=True)

            # Wet lab stats
            if stats:
                st.markdown('<div class="label" style="margin-top:10px">Wet lab triage results</div>', unsafe_allow_html=True)
                assay_name = (st.session_state.ss_info or {}).get("assay_guess","") if st.session_state.get("ss_info") else ""
                if assay_name: st.caption(assay_name)
                c1,c2,c3=st.columns(3)
                c1.metric("HIGH",stats["high_priority"])
                c2.metric("MEDIUM",stats["medium_priority"])
                c3.metric("LOW",stats["low_priority"])

        # ── Residue triage list ─────────────────────────────────────────────────
        if scored is not None:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="label">Residue Triage — click spheres in structure for details, or expand here</div>', unsafe_allow_html=True)
            top_n = st.slider("Show top residues", 3, min(25,len(scored)), min(10,len(scored)))

            for _,row in scored.head(top_n).iterrows():
                p4=str(row.get(pc_col,"LOW")); c4={"HIGH":"#FF4C4C","MEDIUM":"#FFA500","LOW":"#60a5fa"}.get(p4,"#60a5fa")
                pos4=int(row["residue_position"]); sc4=round(float(row["normalized_score"]),3)
                mut4=str(row.get("mutation",f"Pos{pos4}")); mut4=f"Pos{pos4}" if mut4 in ("nan","") else mut4
                hyp4=str(row.get("hypothesis",""))
                conf4=row.get("ml_confidence",None)
                in_cv4 = pos4 in cv_pos
                cv_badge4 = f'<span class="tag" style="background:#FF4C4C22;color:#FF4C4C;border:1px solid #FF4C4C44">ClinVar P at pos {pos4}</span>' if in_cv4 else ""
                dom4=""
                for d4 in uni.get("domains",[]):
                    if d4.get("start",0)<=pos4<=d4.get("end",0):
                        dom4=f'<span class="tag" style="background:#9370DB22;color:#9370DB;border:1px solid #9370DB44">{d4.get("name","")[:20]}</span>'; break
                st.markdown(
                    f'<div style="margin-bottom:8px">'
                    f'<span style="font-family:JetBrains Mono;font-size:0.7rem;font-weight:600;color:{c4}">[{p4}]</span> '
                    f'<span style="color:#e0f0ff;font-family:JetBrains Mono;font-size:0.8rem">{mut4}</span>'
                    f'<span style="color:#334;font-size:0.68rem;font-family:JetBrains Mono"> · {sc4}{f" · ML {conf4:.0%}" if conf4 and pd.notna(conf4) else ""}</span>'
                    f'{cv_badge4}{dom4}'
                    f'<div style="background:#080c18;border-left:2px solid {c4}44;padding:8px 12px;font-size:0.78rem;color:#556;line-height:1.8;margin-top:4px;border-radius:0 6px 6px 0">{hyp4}</div></div>',
                    unsafe_allow_html=True)

            # Excel export
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("⬇ Export Excel workbook (4 sheets)"):
                buf=io.BytesIO()
                with pd.ExcelWriter(buf,engine="openpyxl") as w:
                    scored.to_excel(w,sheet_name="Triage Results",index=True)
                    gp=cv.get("germline_pathogenic",[])+cv.get("germline_lp",[])
                    if gp: pd.DataFrame(gp).to_excel(w,sheet_name="ClinVar Germline P-LP",index=False)
                    if cv.get("somatic"): pd.DataFrame(cv["somatic"]).to_excel(w,sheet_name="ClinVar Somatic",index=False)
                    pd.DataFrame([{"Gene":gene,"Protein":pname,"Germline pathogenic":n_path,"Somatic":n_s,"Tier":tier,"DBR":calculate_dbr(n_path,st.session_state.ss_plen)}]).to_excel(w,sheet_name="Protein Summary",index=False)
                buf.seek(0)
                st.download_button("Download",buf,f"protellect_{gene}.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # Pathways
        if st.session_state.get("ss_pathways"):
            st.markdown('<div class="label" style="margin-top:16px">Experimental pathways — tailored to your data + goal</div>', unsafe_allow_html=True)
            for pw in st.session_state.ss_pathways:
                with st.expander(f"{pw['icon']} {pw['rank']}. {pw['title']} · {pw['cost']} · {pw['timeline']}"):
                    st.markdown(f"*{pw['rationale']}*")
                    for step in pw["steps"]: st.markdown(f"• {step}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CASE STUDY (tissue · genomic · GPCR · somatic/germline diseases)
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    _show2 = "ss_gene" in st.session_state
    if not _show2:
        st.info("👈 Enter a protein and click Analyse.")
    if _show2:
        gene=st.session_state.ss_gene; uni=st.session_state.ss_uni or {}
        cv=st.session_state.ss_cv or {}; pdata=st.session_state.ss_pdata or {}
        n_path=st.session_state.ss_n_path; tier=st.session_state.ss_tier
        tc=TIER_COLORS.get(tier,"#666"); pname=st.session_state.ss_pname or gene
        plen=st.session_state.ss_plen; diseases_str=st.session_state.ss_diseases or ""
        gt_entry=GT.get(gene,())

        st.markdown(f'<h3 style="font-family:JetBrains Mono;color:#e0f0ff;margin-bottom:4px">{gene} — Case Study</h3>', unsafe_allow_html=True)
        st.markdown(f'<p style="color:#334;font-size:0.8rem;margin-bottom:16px">{pname} · {tier} · {n_path} germline pathogenic (ClinVar)</p>', unsafe_allow_html=True)

        col_left, col_right = st.columns([1,1], gap="large")

        with col_left:
            # ── Tissue expression ───────────────────────────────────────────────
            st.markdown('<div class="label">Tissue expression</div>', unsafe_allow_html=True)
            from protein_data import PROTEIN_KNOWLEDGE
            tissue_data = PROTEIN_KNOWLEDGE.get(gene.upper(),{}).get("tissue_expression",{})
            if not tissue_data and uni.get("tissue"):
                # Parse from UniProt text
                ttext = uni["tissue"]
                for lv,pat in [(3,r'high\w*\s+in\s+([^.,;]{3,22})'),(2,r'moderate\w*\s+in\s+([^.,;]{3,22})'),(1,r'low\w*\s+in\s+([^.,;]{3,22})')]:
                    for m in re.findall(pat, ttext, re.I):
                        tissue_data[m.strip()[:18]] = lv
            if tissue_data:
                lc={3:"#FF4C4C",2:"#FFA500",1:"#60a5fa",0:"#1a2040"}; lb={3:"HIGH",2:"MED",1:"LOW",0:"—"}
                cols_t = st.columns(2)
                for i,(t2,lv) in enumerate(sorted(tissue_data.items(),key=lambda x:-x[1])[:10]):
                    c=lc.get(lv,"#334"); l=lb.get(lv,"—")
                    with cols_t[i%2]:
                        st.markdown(f'<div style="background:{c}22;border:1px solid {c}55;border-radius:7px;padding:7px 10px;margin-bottom:5px"><span style="font-family:JetBrains Mono;font-size:0.6rem;font-weight:600;color:{c}">{l}</span><br><span style="font-size:0.8rem;color:#c0d0f0">{t2}</span></div>', unsafe_allow_html=True)
                st.caption("Source: UniProt + Protein Atlas experimental evidence")
            else:
                st.markdown('<div style="background:#070c1a;border:1px solid #1a2040;border-radius:6px;padding:12px;font-size:0.79rem;color:#334">Enable DB enrichment to load tissue expression data</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Genomic data ────────────────────────────────────────────────────
            st.markdown('<div class="label">Genomic data</div>', unsafe_allow_html=True)
            chrom = gt_entry[3] if gt_entry else "—"
            for lbl,val in [
                ("Gene",gene),("Protein",pname[:35] if pname else "—"),
                ("UniProt",uni.get("uid","—") or "—"),("Chromosome",chrom),
                ("Length",f"{plen} aa" if plen else "—"),
                ("Domains",f"{len(uni.get('domains',[]))} annotated"),
                ("TM helices",str(uni.get("n_tm",0))),
                ("GPCR","✓ "+uni.get("g_protein","") if uni.get("is_gpcr") else "No"),
                ("OMIM",uni.get("omim","—") or "—"),
                ("Ensembl",uni.get("ensembl_id","—")[:18] or "—"),
            ]:
                st.markdown(f'<div class="row-item"><span class="rl">{lbl}</span><span class="rv">{val}</span></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── GPCR association ────────────────────────────────────────────────
            st.markdown('<div class="label">GPCR association</div>', unsafe_allow_html=True)
            gpcr_info = pdata.get("gpcr_interaction",{})
            atype = gpcr_info.get("type","") if gpcr_info else ""
            is_gpcr = uni.get("is_gpcr",False); gprot = uni.get("g_protein","")
            if not atype and is_gpcr: atype = f"IS A GPCR — {gprot}"
            if atype:
                role_label = "IMPORTANT — direct GPCR" if "IS A GPCR" in atype else "SCAFFOLD / PIGGYBACK" if any(x in atype for x in ("SCAFFOLD","DESENSITISER","PIGGYBACK")) else "GPCR ASSOCIATED"
                role_c = "#FFA500" if "IS A GPCR" in atype else "#9370DB" if "SCAFFOLD" in atype else "#60a5fa"
                st.markdown(f"""
                <div style="background:#0a0518;border:1px solid {role_c}44;border-radius:8px;padding:12px 14px;margin-bottom:8px">
                  <div style="font-family:JetBrains Mono;font-size:0.6rem;text-transform:uppercase;color:{role_c};margin-bottom:5px">{role_label}</div>
                  <div style="font-size:0.62rem;color:{role_c};font-family:JetBrains Mono;margin-bottom:6px">{atype}</div>
                  <div style="font-size:0.79rem;color:#b0c0e0;line-height:1.7">{gpcr_info.get("mechanism","")[:220] if gpcr_info else ""}</div>
                  {"" if not gpcr_info else f'<div style="font-size:0.7rem;color:#334;margin-top:6px">Partners: {" · ".join(gpcr_info.get("which_gpcrs",[])[:4])}</div>'}
                  {"" if not gpcr_info else f'<div style="font-size:0.68rem;color:#334;margin-top:4px">📄 {gpcr_info.get("paper","")[:60]}</div>'}
                </div>""", unsafe_allow_html=True)
                if "SCAFFOLD" in atype or "PIGGYBACK" in atype or "DESENSITISER" in atype:
                    pig = pdata.get("piggyback_relationship",{})
                    if pig:
                        partners_s = " · ".join(pig.get("essential_partners",[])[:3])
                        st.markdown(f'<div style="background:#100818;border:1px solid #FF4C4C22;border-radius:6px;padding:9px 11px;font-size:0.75rem;color:#c0a0c0"><strong style="color:#FF8888">Disease burden is in its partners:</strong> {partners_s}<br><span style="color:#556">{pig.get("analogy","")[:80]}</span></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="background:#070c1a;border:1px solid #1a2040;border-radius:6px;padding:10px;font-size:0.78rem;color:#334">No curated GPCR association. Check UniProt interactions tab and IUPHAR for this protein.</div>', unsafe_allow_html=True)

        with col_right:
            # ── Diseases — somatic vs germline ─────────────────────────────────
            st.markdown('<div class="label">Disease associations — Germline vs Somatic</div>', unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:#070c1a;border:1px solid #1a2040;border-radius:8px;padding:12px;margin-bottom:10px;font-size:0.74rem;color:#445;line-height:1.7">
              <strong style="color:#60a5fa">Germline</strong> = inherited variants proven to cause human disease — the drug target validation gold standard.<br>
              <strong style="color:#FFA500">Somatic</strong> = mutations in cancer cells, NOT inherited. A protein in cancer databases is NOT automatically a valid drug target.
              {paper_chip("minikel_2021")} {paper_chip("king_2024")}
            </div>""", unsafe_allow_html=True)

            # Germline diseases
            gpath_all = cv.get("germline_pathogenic",[]) + cv.get("germline_lp",[])
            germline_diseases = set()
            for v2 in gpath_all:
                for c2 in v2.get("conditions",[]):
                    if c2 and "not provided" not in c2.lower(): germline_diseases.add(c2)
            # Also add from GT
            if diseases_str:
                for d in diseases_str.split("·"):
                    if d.strip(): germline_diseases.add(d.strip())
            if germline_diseases:
                st.markdown(f'<div style="font-family:JetBrains Mono;font-size:0.6rem;text-transform:uppercase;color:#FF4C4C;margin-bottom:5px">Germline — confirmed inherited disease ({len(germline_diseases)})</div>', unsafe_allow_html=True)
                for dis in list(germline_diseases)[:7]:
                    st.markdown(f'<div style="padding:5px 9px;margin-bottom:3px;background:#0c0810;border:1px solid #FF4C4C22;border-radius:5px;font-size:0.78rem;color:#e0d0d0"><span class="tag" style="background:#FF4C4C22;color:#FF4C4C;border:1px solid #FF4C4C44;font-size:0.58rem">GERMLINE</span> {dis}</div>', unsafe_allow_html=True)
            elif n_path == 0:
                st.markdown('<div style="background:#100818;border:1px solid #FF4C4C22;border-radius:6px;padding:10px;font-size:0.79rem;color:#778">Zero confirmed germline pathogenic variants. This protein does not cause inherited disease.</div>', unsafe_allow_html=True)

            # Somatic diseases
            somatic_dis = set()
            for v2 in cv.get("somatic",[]):
                for c2 in v2.get("conditions",[]):
                    if c2 and "not provided" not in c2.lower(): somatic_dis.add(c2)
            if somatic_dis:
                st.markdown(f'<div style="font-family:JetBrains Mono;font-size:0.6rem;text-transform:uppercase;color:#FFA500;margin-bottom:5px;margin-top:10px">Somatic — cancer mutations ONLY ({len(somatic_dis)})</div>', unsafe_allow_html=True)
                for dis in list(somatic_dis)[:5]:
                    st.markdown(f'<div style="padding:5px 9px;margin-bottom:3px;background:#0d0a06;border:1px solid #FFA50022;border-radius:5px;font-size:0.78rem;color:#d0c0a0"><span class="tag" style="background:#FFA50022;color:#FFA500;border:1px solid #FFA50044;font-size:0.58rem">SOMATIC</span> {dis}</div>', unsafe_allow_html=True)

            # Real biology
            real_bio = pdata.get("real_biology","")
            if real_bio:
                st.markdown('<div class="label" style="margin-top:12px">What this protein actually does</div>', unsafe_allow_html=True)
                with st.expander("Show full biology"):
                    st.markdown(f'<div style="font-size:0.79rem;color:#b0c0e0;line-height:1.9;white-space:pre-line">{real_bio[:1200]}</div>', unsafe_allow_html=True)

            # Why mutations major/minor
            why_text = pdata.get("why_mutations_major","") or pdata.get("why_mutations_minor","")
            if why_text:
                label2 = "Why mutations are critical" if n_path>50 else "Why mutations are tolerated (human)" if n_path==0 else "Why this is a rare Mendelian gene"
                st.markdown(f'<div class="label" style="margin-top:10px">{label2}</div>', unsafe_allow_html=True)
                with st.expander("Show explanation"):
                    st.markdown(f'<div style="font-size:0.79rem;color:#b0c0e0;line-height:1.8;white-space:pre-line">{why_text[:800]}</div>', unsafe_allow_html=True)

            # PubMed
            pubmed = st.session_state.get("ss_pubmed",[])
            if pubmed:
                st.markdown('<div class="label" style="margin-top:12px">PubMed papers</div>', unsafe_allow_html=True)
                for p2 in pubmed[:4]:
                    st.markdown(f'<div style="padding:6px 9px;margin-bottom:4px;background:#070c1a;border:1px solid #1a2040;border-radius:6px"><a href="{p2["url"]}" target="_blank" style="color:#60a5fa;text-decoration:none;font-size:0.75rem">{p2["title"]}</a><div style="font-size:0.65rem;color:#334;margin-top:2px">{p2["journal"]} · {p2["year"]}</div></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PROTEIN EXPLORER (clickable structure + mutation animation + disease list)
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    _show_tab3 = "ss_gene" in st.session_state
    if not _show_tab3:
        st.info("👈 Enter a protein and click Analyse.")
    if _show_tab3:
        gene=st.session_state.ss_gene; pdb=st.session_state.ss_pdb; pdb_src=st.session_state.ss_pdb_src or ""
        uni=st.session_state.ss_uni or {}; cv=st.session_state.ss_cv or {}
        pdata=st.session_state.ss_pdata or {}; n_path=st.session_state.ss_n_path
        tier=st.session_state.ss_tier; tc=TIER_COLORS.get(tier,"#666")
        scored=st.session_state.ss_scored; pc_col="priority_final" if scored is not None and "priority_final" in scored.columns else "priority"
        diseases_str=st.session_state.ss_diseases or ""; pname=st.session_state.ss_pname or gene
        plen=st.session_state.ss_plen; gt_entry=GT.get(gene,())

        st.markdown(f'<h3 style="font-family:JetBrains Mono;color:#e0f0ff;margin-bottom:4px">{gene} — Protein Explorer</h3>', unsafe_allow_html=True)

        # ── Full-width clickable structure ──────────────────────────────────────
        st.markdown('<div class="label">3D Structure — click any residue sphere for detailed mutation analysis</div>', unsafe_allow_html=True)
        if pdb_src: st.caption(f"🏗️ {pdb_src}")

        cmap2={"HIGH":"#FF4C4C","MEDIUM":"#FFA500","LOW":"#60a5fa"}
        rmap2={"HIGH":1.3,"MEDIUM":0.9,"LOW":0.5}
        rs2={}; annot2={}
        cv_pos2={}
        for v2 in cv.get("germline_pathogenic",[]) + cv.get("germline_lp",[]):
            pos2=v2.get("pos",0)
            if not pos2:
                m2=re.search(r'[A-Z](\d+)[A-Z=*]',v2.get("title",""))
                if m2: pos2=int(m2.group(1))
            if pos2>0: cv_pos2[pos2]={"sig":v2.get("germline","") or v2.get("sig",""),"conds":v2.get("conditions",[])}

        if scored is not None and pdb:
            pdb_res3=set()
            for line in pdb.split('\n'):
                if line.startswith('ATOM'):
                    try: pdb_res3.add(int(line[22:26].strip()))
                    except: pass
            for _,row in scored.iterrows():
                pos3=int(row["residue_position"]); p3=str(row.get(pc_col,"LOW"))
                rs2[pos3]={"c":cmap2.get(p3,"#60a5fa"),"r":rmap2.get(p3,0.5)}
                annot2[pos3]={"p":p3,"s":round(float(row.get("normalized_score",0)),3),"h":str(row.get("hypothesis",""))[:200]}
        elif pdb and cv_pos2:
            pdb_res3=set()
            for line in pdb.split('\n'):
                if line.startswith('ATOM'):
                    try: pdb_res3.add(int(line[22:26].strip()))
                    except: pass
            for cpos in list(cv_pos2.keys())[:80]:
                if cpos in pdb_res3:
                    rs2[cpos]={"c":"#FF4C4C","r":1.0}
                    annot2[cpos]={"p":"HIGH","s":1.0,"h":f"ClinVar pathogenic at position {cpos}"}

        if pdb:
            components.html(make_viewer(pdb, rs2, cv_pos2, annot2, gene, 860, 500), height=506)
        else:
            st.warning(f"AlphaFold structure for {gene} loading... Enable DB enrichment and click Analyse.")

        # ── Mutation animation ──────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="label">Structural mutation progression — drag slider to see how the protein changes</div>', unsafe_allow_html=True)

        # Get protein-specific structural data
        pse = pdata.get("gpcr_interaction",{})
        struct_stages = pdata.get("timeline_stages",[]) if pdata.get("timeline_stages") else [
            (0,"WT conformation","Wild-type protein in native state. All domains correctly folded."),
            (1,"Variant introduced","Pathogenic amino acid substitution. Local environment changes."),
            (2,"Local perturbation","Bond angles/distances altered. Neighbouring residues affected."),
            (3,"Domain perturbation","Secondary structure element destabilised."),
            (4,"Functional disruption","Binding partner recognition impaired."),
            (5,"Disease manifestation","Cellular dysfunction leads to tissue pathology."),
        ]
        max_s = len(struct_stages)-1
        if max_s > 0:
            sel_s = st.slider("Stage", 0, max_s, 0, key="explorer_slider")
            stg = struct_stages[sel_s]
            stg_name, stg_desc = stg[1], stg[2]
            pct = int(sel_s/max_s*100) if max_s > 0 else 0
            bc = "#4CAF50" if pct==0 else "#FFA500" if pct<50 else "#FF8C00" if pct<80 else "#FF4C4C"

            # Structural animation canvas
            STRUCT_HTML = f"""
            <div style="background:#050810;border:1px solid #1a2040;border-radius:10px;padding:0;overflow:hidden">
              <canvas id="sc" width="860" height="200" style="display:block;width:100%;background:#050810"></canvas>
              <div style="padding:12px 16px;border-top:1px solid #0a1020">
                <div style="font-family:JetBrains Mono;font-weight:600;color:{bc};font-size:0.9rem;margin-bottom:4px">{stg_name}</div>
                <div style="background:#0a1020;border-radius:3px;height:6px;overflow:hidden;margin-bottom:8px">
                  <div style="width:{pct}%;height:100%;background:{bc};border-radius:3px"></div>
                </div>
                <div style="font-size:0.82rem;color:#889;line-height:1.7">{stg_desc}</div>
              </div>
            </div>
            <script>
            (function(){{
              const canvas=document.getElementById('sc'); if(!canvas)return;
              const ctx=canvas.getContext('2d'); const W=canvas.width,H=canvas.height;
              const t={pct/100}; const c='{bc}';
              function lerp(a,b,t){{return a+(b-a)*Math.max(0,Math.min(1,t));}}
              function lerpC(c1,c2,t){{
                const h=v=>parseInt(v,16);
                const r=Math.round(lerp(h(c1.slice(1,3)),h(c2.slice(1,3)),t));
                const g=Math.round(lerp(h(c1.slice(3,5)),h(c2.slice(3,5)),t));
                const b=Math.round(lerp(h(c1.slice(5,7)),h(c2.slice(5,7)),t));
                return '#'+[r,g,b].map(v=>v.toString(16).padStart(2,'0')).join('');
              }}
              ctx.clearRect(0,0,W,H);
              // Draw protein chain
              const chainColor=lerpC('#4CAF50',c,t);
              ctx.strokeStyle=chainColor; ctx.lineWidth=4; ctx.beginPath();
              const midY=H/2+10;
              for(let x=40;x<W-40;x++){{
                const wobble=t*Math.sin((x/45)*Math.PI)*18*Math.sin((x/(W/2.2))*Math.PI);
                const y=midY+Math.sin((x/80)*Math.PI)*12+wobble;
                x===40?ctx.moveTo(x,y):ctx.lineTo(x,y);
              }}
              ctx.stroke();
              // Draw domains as rectangles
              const domains=[{json.dumps([{"start":d.get("start",0),"end":d.get("end",0),"name":d.get("name","")[:10]} for d in uni.get("domains",[])[:8]])}];
              const pl={plen or 500};
              const dc=['#9370DB','#60a5fa','#FFA500','#4CAF50','#FF6B9D','#00BCD4'];
              domains.forEach((d,i)=>{{
                const x1=40+(d.start/pl)*(W-80); const x2=40+(d.end/pl)*(W-80);
                const dw=Math.max(x2-x1,3);
                ctx.fillStyle=dc[i%dc.length]+'44'; ctx.strokeStyle=dc[i%dc.length];
                ctx.lineWidth=1.5;
                ctx.beginPath(); ctx.roundRect(x1,midY-20,dw,40,4); ctx.fill(); ctx.stroke();
                if(dw>40){{ctx.fillStyle=dc[i%dc.length]; ctx.font='8px JetBrains Mono'; ctx.textAlign='center'; ctx.fillText(d.name.slice(0,10),x1+dw/2,midY+5);}}
              }});
              // Draw pathogenic variant positions
              const cvPos=[{",".join(str(int(p)) for p in list(cv_pos2.keys())[:50])}];
              cvPos.forEach(pos=>{{
                if(!pos)return;
                const x=40+(pos/pl)*(W-80);
                ctx.fillStyle=c; ctx.strokeStyle=c; ctx.lineWidth=2;
                ctx.beginPath(); ctx.arc(x,midY-30+t*15,5+t*4,0,Math.PI*2); ctx.fill();
                ctx.beginPath(); ctx.moveTo(x,midY-25); ctx.lineTo(x,midY-20); ctx.stroke();
              }});
              // WT vs mutant indicator
              ctx.fillStyle='#4CAF50'; ctx.font='bold 10px JetBrains Mono'; ctx.textAlign='left';
              ctx.fillText('WT',12,midY+4);
              ctx.fillStyle=c; ctx.textAlign='right';
              const mutLabel=t>0.05?'MUT':'WT';
              ctx.fillText(mutLabel,W-12,midY+4);
              // Progress label
              ctx.fillStyle=c+'aa'; ctx.font='9px JetBrains Mono'; ctx.textAlign='center';
              ctx.fillText(Math.round(t*100)+'% mutation effect',W/2,H-8);
            }})();
            </script>"""
            components.html(STRUCT_HTML, height=260, scrolling=False)

            # Stage roadmap
            pills=" ".join(f'<span style="background:{""+bc+"22" if i==sel_s else "#0a1020"};border:1px solid {""+bc if i==sel_s else "#1a2040"};border-radius:6px;padding:4px 10px;font-family:JetBrains Mono;font-size:0.6rem;color:{""+bc if i==sel_s else "#334"};display:inline-block;margin:2px">{i+1}. {s[1][:14]}</span>' for i,s in enumerate(struct_stages))
            st.markdown(pills, unsafe_allow_html=True)

        # ── Disease-mutation table ──────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="label">Every disease caused by this protein — with causal mutation and genomic implication</div>', unsafe_allow_html=True)

        gpath_all = cv.get("germline_pathogenic",[]) + cv.get("germline_lp",[])
        if gpath_all:
            dis_mut_map = {}
            for v2 in gpath_all[:100]:
                title2=v2.get("title",""); sig2=v2.get("germline","") or v2.get("sig","")
                conds2=v2.get("conditions",[]); pos2=v2.get("pos",0)
                for c2 in conds2:
                    if c2 and "not provided" not in c2.lower():
                        if c2 not in dis_mut_map: dis_mut_map[c2]=[]
                        dis_mut_map[c2].append({"title":title2,"sig":sig2,"pos":pos2})

            # Also add GT diseases
            if diseases_str and not dis_mut_map:
                for d in diseases_str.split("·")[:6]:
                    d=d.strip()
                    if d and d not in dis_mut_map: dis_mut_map[d]=[{"title":"See ClinVar","sig":"Pathogenic","pos":0}]

            for disease_name, mutations in list(dis_mut_map.items())[:8]:
                with st.expander(f"🔴 {disease_name} — {len(mutations)} variant(s)"):
                    for mut2 in mutations[:5]:
                        pos_d=mut2.get("pos",0)
                        # Find domain for this position
                        dom_d=""
                        for d in uni.get("domains",[]):
                            if d.get("start",0)<=pos_d<=d.get("end",0): dom_d=d.get("name",""); break
                        # Infer genomic implication
                        if "CRITICAL" in tier or n_path>500:
                            impl = f"Dominant pathogenic. Expected: Tm ↓4-12°C on DSF. Disrupts {'domain: '+dom_d if dom_d else 'protein stability'}. Loss of interaction with key partner."
                        elif n_path>0:
                            impl = f"Pathogenic variant. Check ClinVar review stars for confidence. {'Domain: '+dom_d+' affected.' if dom_d else ''} Validate with DSF → ITC."
                        else:
                            impl = "No confirmed genomic implication — zero germline pathogenic variants."
                        st.markdown(f"""
                        <div style="background:#080c18;border:1px solid #1a2040;border-radius:6px;padding:10px 12px;margin-bottom:6px">
                          <div style="font-family:JetBrains Mono;font-size:0.72rem;color:#FF4C4C;margin-bottom:3px">{mut2.get("title","")[:65]}</div>
                          <div style="font-size:0.75rem;color:#556;margin-bottom:4px">{mut2.get("sig","")} {"· Pos "+str(pos_d) if pos_d else ""} {"· Domain: "+dom_d if dom_d else ""}</div>
                          <div style="font-size:0.74rem;color:#889;line-height:1.6"><strong style="color:#b0c0e0">Genomic implication:</strong> {impl}</div>
                        </div>""", unsafe_allow_html=True)
        elif n_path == 0:
            st.markdown(f'<div style="background:#100818;border:1px solid #FF4C4C22;border-radius:8px;padding:14px;font-size:0.82rem;color:#778;line-height:1.7">Zero confirmed germline pathogenic variants for <strong style="color:#e0d0e0">{gene}</strong>. This protein does not cause any confirmed inherited human disease. {"Study its interaction partners: "+", ".join(pdata.get("piggyback_relationship",{}).get("essential_partners",[])[:3]) if pdata.get("piggyback_relationship") else ""}</div>', unsafe_allow_html=True)
        else:
            st.info(f"{n_path} pathogenic variants exist — enable DB enrichment for detailed position mapping.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — THERAPY & EXPERIMENTS
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    _show_tab4 = "ss_gene" in st.session_state
    if not _show_tab4:
        st.info("👈 Enter a protein and click Analyse.")
    if _show_tab4:
        gene=st.session_state.ss_gene; n_path=st.session_state.ss_n_path; tier=st.session_state.ss_tier
        tc=TIER_COLORS.get(tier,"#666"); pdata=st.session_state.ss_pdata or {}
        scored=st.session_state.ss_scored; pc_col="priority_final" if scored is not None and "priority_final" in scored.columns else "priority"
        uni=st.session_state.ss_uni or {}; cv=st.session_state.ss_cv or {}
        goal_ctx=goal_in or "general research"; diseases_str=st.session_state.ss_diseases or ""
        pname=st.session_state.ss_pname or gene

        # Warning for scaffold proteins
        if tier == "NEUTRAL":
            st.markdown(f"""
            <div style="background:#0c0818;border:2px solid #FF4C4C;border-radius:12px;padding:18px 22px;margin-bottom:16px">
              <div style="font-family:JetBrains Mono;font-weight:700;color:#FF4C4C;margin-bottom:8px">⚠ DO NOT PURSUE {gene} AS A PRIMARY DRUG TARGET</div>
              <p style="font-size:0.84rem;color:#c0a0b0;line-height:1.7;margin-bottom:10px">Zero germline pathogenic variants in ClinVar. Humans who carry broken versions of this protein are apparently healthy. Any drug program targeting {gene} faces a ~90% failure rate from wrong target selection.</p>
              <div>{paper_chip("cook_2014")} {paper_chip("plenge_2016")} {paper_chip("minikel_2021")}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown(f'<h3 style="font-family:JetBrains Mono;color:#e0f0ff;margin-bottom:4px">{gene} — Therapy & Experiments</h3>', unsafe_allow_html=True)
        st.markdown(f'<p style="color:#334;font-size:0.8rem;margin-bottom:16px">Goal: {goal_ctx} · Tier: {tier} · {n_path} germline pathogenic variants</p>', unsafe_allow_html=True)

        # Get protein-specific experiments
        specific_exps = pdata.get("experiments_specific",[])

        t4a, t4b, t4c = st.tabs(["🧪 Experiments","💊 Drug & Therapy","🎯 Focus: which mutations to target"])

        with t4a:
            st.markdown(f'<div style="background:#070c1a;border:1px solid #1a2040;border-radius:8px;padding:10px 14px;margin-bottom:12px;font-size:0.79rem;color:#445">Experiments below are <strong style="color:#e0f0ff">specific to {gene}</strong> — not a generic protocol. Different proteins require fundamentally different validation strategies.</div>', unsafe_allow_html=True)

            # Protein-specific experiments from protein_data
            if specific_exps:
                st.markdown('<div class="label">Protein-specific experiments (prioritised for your protein)</div>', unsafe_allow_html=True)
                lc_map={1:"#4CAF50",2:"#FFA500",3:"#FF8C00",4:"#FF4C4C",5:"#FF0000"}
                for exp in specific_exps:
                    lc=lc_map.get(exp.get("level",2),"#60a5fa")
                    level_n=exp.get("level",2)
                    cost_map={1:"Free","2":"$200-500","3":"$1,000-3,000","4":"$5,000-15,000","5":"$20,000+"}
                    time_map={1:"<1 day","2":"2-5 days","3":"1-3 weeks","4":"1-3 months","5":"3-6 months"}
                    with st.expander(f"Level {level_n} — {exp['name']} · {time_map.get(level_n,'—')} · {cost_map.get(level_n,'—')}"):
                        st.markdown(f'<div style="background:{lc}11;border-left:3px solid {lc};border-radius:0 6px 6px 0;padding:10px 14px;margin-bottom:8px"><div style="font-family:JetBrains Mono;font-size:0.6rem;text-transform:uppercase;color:{lc};margin-bottom:4px">Why this experiment for {gene} specifically</div><p style="font-size:0.82rem;color:#c0d0f0;line-height:1.7">{exp.get("rationale","")}</p></div>', unsafe_allow_html=True)
                        if exp.get("protocol"):
                            st.markdown("**Protocol:**")
                            st.code(exp["protocol"], language="text")
                        why_not=exp.get("why_this_not_dsf","")
                        if why_not:
                            st.markdown(f'<div style="font-size:0.74rem;color:#556;font-style:italic;margin-top:4px">Why not generic thermal shift: {why_not}</div>', unsafe_allow_html=True)

            # Universal experiments
            st.markdown('<div class="label" style="margin-top:14px">Universal validation hierarchy (always applicable)</div>', unsafe_allow_html=True)
            UNIVERSAL_EXPS = [
                (1,"ClinVar + gnomAD database screen","Free","<1 hour","#4CAF50",
                 f"Confirm {gene} DBR and germline pathogenic variant count. gnomAD pLI >0.9 = highly constrained. This is ALWAYS step 1 before any wet lab investment.",
                 "Establishes genomic context — eliminates wrong targets at zero cost.",
                 ""),
                (1,"OpenTargets genetic association score","Free","30 min","#4CAF50",
                 f"Search {gene} at platform.opentargets.org. Check ClinVar column weight. Compare to β-adrenergic receptors and arrestins — the contrast is instructive.",
                 "Multi-disease genetic association score across all evidence types.",
                 ""),
                (2,"AlphaFold + FPocket druggability","Free","1-2 hours","#60a5fa",
                 f"Run FPocket on {gene} AlphaFold structure. Identify druggable cavities near pathogenic variant hotspots. Only meaningful for proteins WITH ClinVar variants.",
                 "Identifies druggable pockets without any wet lab. Filters structural-mutant from surface-mutant.",
                 ""),
                (3,"Thermal shift (DSF)","$200-500","2-3 days","#FFA500",
                 f"Express WT and top pathogenic {gene} variants. DSF with SYPRO Orange (25→95°C, 1°C/min). Expect ΔTm 3-15°C for pathogenic variants vs WT.",
                 "Confirms structural destabilisation. Required before ITC. Cannot give Kd.",
                 "Note: For signalling proteins like β-arrestin, DSF is NOT the right first assay — use BRET/functional assays instead."),
                (4,"ITC (Isothermal Titration Calorimetry)","$1,500-3,000","1-2 weeks","#FF8C00",
                 f"Gold standard binding thermodynamics. Measures Kd, ΔH, ΔS, stoichiometry simultaneously. No fluorescent artefacts. Recommended by Sujay Ithychanda (Cleveland Clinic) as the most robust assay for {gene} binding validation.",
                 "Definitive binding characterisation. No false positives. Quantitative.",
                 ""),
                (5,"Patient-derived cell validation","$5,000-20,000","1-3 months","#FF4C4C",
                 f"Obtain fibroblasts or iPSCs from confirmed {gene} pathogenic variant carriers. Differentiate to relevant cell type ({', '.join((pdata.get('tissue_expression',{}) or {}).keys())[:2] if pdata.get('tissue_expression') else 'affected tissue'}). Measure native protein function.",
                 "Human evidence — more relevant than mouse models. Required before clinical claims.",
                 ""),
            ]
            for (level,name,cost,time_v,lc,desc,validates,caveat) in UNIVERSAL_EXPS:
                with st.expander(f"Level {level} — {name} · {time_v} · {cost}"):
                    st.markdown(f'<p style="font-size:0.82rem;color:#c0d0f0;line-height:1.7">{desc}</p>', unsafe_allow_html=True)
                    if validates: st.markdown(f'<div style="font-size:0.75rem;color:#4CAF50;margin-bottom:4px"><strong>Validates:</strong> {validates}</div>', unsafe_allow_html=True)
                    if caveat:    st.markdown(f'<div style="font-size:0.73rem;color:#FFA500;font-style:italic">{caveat}</div>', unsafe_allow_html=True)
                    st.markdown(f'{paper_chip("king_2024")} {paper_chip("minikel_2021")}', unsafe_allow_html=True)

        with t4b:
            st.markdown('<div class="label">Drug strategy based on ClinVar evidence</div>', unsafe_allow_html=True)
            if tier == "NEUTRAL":
                st.markdown(f"""
                <div class="card-red">
                  <div style="font-family:JetBrains Mono;font-size:0.65rem;color:#FF4C4C;margin-bottom:6px">NO DRUG DEVELOPMENT RECOMMENDED</div>
                  <p style="font-size:0.82rem;color:#c0a0b0;line-height:1.7">Zero germline pathogenic variants = the protein is dispensable in humans. Any drug that acts on {gene} as a primary target will likely fail for lack of disease relevance.</p>
                  <p style="font-size:0.8rem;color:#778;margin-top:6px">Study the interaction partners with confirmed ClinVar burden instead: {", ".join(pdata.get("piggyback_relationship",{}).get("essential_partners",[])[:3]) if pdata.get("piggyback_relationship") else "check UniProt interactions"}</p>
                </div>""", unsafe_allow_html=True)
            else:
                dbr_val = calculate_dbr(n_path, st.session_state.ss_plen)
                if dbr_val and dbr_val > 0.5: strategy = "Gene therapy / mRNA replacement justified by critical disease burden. DBR >0.5 confirms this is among the most pathogenically constrained proteins."
                elif n_path > 50: strategy = "Small molecule or antibody development justified. Confirmed target-disease linkage via ClinVar germline variants."
                elif n_path > 0: strategy = "Rare disease strategy. Orphan drug regulatory pathway. Gene therapy appropriate given confirmed Mendelian genetics."
                else: strategy = "Insufficient evidence — establish genomic context before any therapeutic investment."
                st.markdown(f"""
                <div class="card-green">
                  <div style="font-family:JetBrains Mono;font-size:0.65rem;color:#4CAF50;margin-bottom:6px">DRUG DEVELOPMENT STRATEGY — {tier}</div>
                  <p style="font-size:0.82rem;color:#c0e0c0;line-height:1.7">{strategy}</p>
                  <div style="margin-top:8px">{paper_chip("king_2024")} {paper_chip("cook_2014")}</div>
                </div>""", unsafe_allow_html=True)

            # Known drugs
            KNOWN_DRUGS = {
                "TP53": [("APR-246/Eprenetapopt","Structural mutants (R175H, R248)","Phase III — refolds mutant p53"),("PC14586/Rezatapopt","Y220C surface cavity","Phase II — fills druggable pocket"),],
                "BRCA1":[("Olaparib (PARP inhibitor)","BRCA1/2 LOF","FDA approved — synthetic lethality"),],
                "EGFR": [("Erlotinib","L858R, exon19del","FDA approved"),("Osimertinib","T790M resistance","FDA approved"),],
                "KRAS": [("Sotorasib","G12C specific","FDA approved"),("Adagrasib","G12C specific","FDA approved"),],
            }
            drugs = KNOWN_DRUGS.get(gene.upper(),[])
            if drugs:
                st.markdown('<div class="label" style="margin-top:12px">Known therapies</div>', unsafe_allow_html=True)
                for (name,target,status) in drugs:
                    st.markdown(f"""
                    <div class="card">
                      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                        <span style="font-weight:600;color:#e0f0ff;font-size:0.84rem">{name}</span>
                        <span class="tag" style="background:#4CAF5022;color:#4CAF50;border:1px solid #4CAF5044">{status}</span>
                      </div>
                      <div style="font-size:0.75rem;color:#445">Target: {target}</div>
                    </div>""", unsafe_allow_html=True)

        with t4c:
            st.markdown('<div class="label">Which mutations to focus on — which to neglect</div>', unsafe_allow_html=True)

            if scored is not None:
                high_hits = scored[scored[pc_col]=="HIGH"].head(10)
                low_hits  = scored[scored[pc_col]=="LOW"].tail(5)

                st.markdown('<div style="font-family:JetBrains Mono;font-size:0.62rem;text-transform:uppercase;color:#FF4C4C;margin-bottom:6px">FOCUS ON — HIGH PRIORITY</div>', unsafe_allow_html=True)
                for _,row in high_hits.iterrows():
                    pos=int(row["residue_position"]); sc=round(float(row["normalized_score"]),3)
                    mut=str(row.get("mutation",f"Pos{pos}")); mut=f"Pos{pos}" if mut in ("nan","") else mut
                    in_cv=pos in cv_pos2 if cv_pos2 else False
                    st.markdown(f'<div style="padding:6px 10px;margin-bottom:4px;background:#0c0810;border:1px solid #FF4C4C44;border-radius:6px;font-size:0.78rem;display:flex;justify-content:space-between"><span style="font-family:JetBrains Mono;color:#FF4C4C">{mut}</span><span style="color:#556">score {sc} {"· ClinVar P" if in_cv else ""}</span></div>', unsafe_allow_html=True)

                st.markdown('<div style="font-family:JetBrains Mono;font-size:0.62rem;text-transform:uppercase;color:#334;margin-bottom:6px;margin-top:10px">NEGLECT — LOW PRIORITY</div>', unsafe_allow_html=True)
                for _,row in low_hits.iterrows():
                    pos=int(row["residue_position"]); sc=round(float(row["normalized_score"]),3)
                    mut=str(row.get("mutation",f"Pos{pos}")); mut=f"Pos{pos}" if mut in ("nan","") else mut
                    st.markdown(f'<div style="padding:5px 10px;margin-bottom:3px;background:#0a0d18;border:1px solid #1a2040;border-radius:6px;font-size:0.75rem;display:flex;justify-content:space-between"><span style="color:#334;font-family:JetBrains Mono">{mut}</span><span style="color:#223">score {sc} — tolerated substitution</span></div>', unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="card">
                  <p style="font-size:0.82rem;color:#c0d0f0;line-height:1.7">Upload wet lab data to get a ranked list of which mutations to focus on vs neglect. Without data, use ClinVar pathogenic positions as the focus list — these are the human-validated mutations.</p>
                  <p style="font-size:0.79rem;color:#445;margin-top:8px">ClinVar pathogenic positions for {gene}: {", ".join(["Pos "+str(v2.get("pos",0)) for v2 in (cv.get("germline_pathogenic",[]) or [])[:8] if v2.get("pos",0)>0]) or "Loading..."}</p>
                </div>""", unsafe_allow_html=True)

            # Evidence hierarchy
            st.markdown("""
            <div style="background:#070c1a;border:1px solid #1a2040;border-radius:8px;padding:14px 16px;margin-top:12px">
              <div style="font-family:JetBrains Mono;font-size:0.6rem;text-transform:uppercase;color:#334;margin-bottom:8px">Evidence hierarchy — what counts as truth</div>
              <div style="font-size:0.79rem;color:#667;line-height:2">
                🏆 <strong style="color:#e0f0ff">Gold:</strong> Germline pathogenic in ClinVar — proven to cause human disease<br>
                🥈 <strong style="color:#e0f0ff">Silver:</strong> ITC binding thermodynamics — quantitative, no artefacts<br>
                🥉 <strong style="color:#e0f0ff">Bronze:</strong> Thermal shift (DSF) — structural destabilisation confirmed<br>
                ⚠️ <strong style="color:#c0c0c0">Caution:</strong> Cell culture, mouse knockouts — informative but not sufficient alone<br>
                ❌ <strong style="color:#445">Reject:</strong> Text mining, pathway inference, LLM predictions without experimental validation
              </div>
            </div>""", unsafe_allow_html=True)
            st.markdown(f'<div style="margin-top:8px">{paper_chip("king_2024")} {paper_chip("minikel_2021")} {paper_chip("plenge_2016")} {paper_chip("cook_2014")}</div>', unsafe_allow_html=True)

