"""
Protellect — Experimental Intelligence Layer v4
Complete rewrite. Protein-first. ClinVar-first. Truth-first.

Architecture:
  - Everything is driven by the protein/gene entered in the Q&A sidebar
  - Wet lab data augments the analysis but is never the primary source of truth
  - AlphaFold structures for any protein (no TP53 default)
  - ClinVar germline variants are the only ground truth for disease relevance
  - Every claim is backed by a published paper
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import requests
import json
import io
import re
import time
import base64
from pathlib import Path

# ── Imports ───────────────────────────────────────────────────────────────────
try:
    from logo import LOGO_DATA_URL as LOGO_B64
except Exception:
    _lp = Path("/mnt/user-data/uploads/1777622887238_image.png")
    LOGO_B64 = ("data:image/png;base64," + base64.b64encode(_lp.read_bytes()).decode()) if _lp.exists() else None

from scorer import load_file, score_residues, get_summary_stats, validate_dataframe, detect_dataset_info, generate_top_pathways, ML_AVAILABLE

from evidence_layer import calculate_dbr, assign_genomic_tier, get_genomic_verdict
try:
    from evidence_layer import classify_protein_role, EXPERIMENT_LADDER
except ImportError:
    def classify_protein_role(g, n, **kw):
        if n == 0: return {"role":"unvalidated","label":"No ClinVar disease evidence","icon":"⚪","color":"#555","note":"Zero pathogenic variants.","warning":"Zero ClinVar variants — validate before any investment."}
        elif n < 10: return {"role":"rare_mendelian","label":"Confirmed rare Mendelian disease gene","icon":"🟡","color":"#FFD700","note":f"{n} pathogenic variant(s)."}
        elif n < 500: return {"role":"validated","label":"Genomically validated disease gene","icon":"🟠","color":"#FFA500","note":f"{n} pathogenic variants."}
        else: return {"role":"critical_driver","label":"Critical disease driver","icon":"🔴","color":"#FF4C4C","note":f"{n} pathogenic variants."}
    EXPERIMENT_LADDER = {}

from diagrams import build_tissue_diagram, build_genomic_diagram, build_cell_impact_diagram, GPCR_ASSOC, TISSUE_DATA
try:
    from protein_data import get_protein_info
except ImportError:
    def get_protein_info(gene):
        return {"real_biology":"","gpcr_interaction":{},"experiments_specific":[],"timeline_stages":[],"piggyback_relationship":{}}
try:
    from diagrams import build_gpcr_association_diagram
except ImportError:
    def build_gpcr_association_diagram(gene, g_protein="", protein_name="", is_gpcr=False):
        from diagrams import build_gpcr_diagram
        return build_gpcr_diagram(gene, g_protein or "Gq/11", protein_name, 7)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Protellect", page_icon="🧬", layout="wide",
                   initial_sidebar_state="expanded")

# ── Ground truth ClinVar counts ───────────────────────────────────────────────
GROUND_TRUTH = {
    "FLNA": (847,2647,"Filamin A","X","Periventricular heterotopia · Cardiac malformations · Aortic aneurysm · Intellectual disability · Epilepsy · Melnick-Needles · OPD syndrome"),
    "FLNB": (412,2602,"Filamin B","3","Boomerang dysplasia · Larsen syndrome · Atelosteogenesis · Spondylocarpotarsal synostosis"),
    "FLNC": (3800,2725,"Filamin C","7","Arrhythmogenic cardiomyopathy · Dilated cardiomyopathy · Distal myopathy · Myofibrillar myopathy"),
    "CHRM2":(102,466,"Muscarinic receptor M2","7","Dilated cardiomyopathy (dominant)"),
    "CHRM3":(8,590,"Muscarinic receptor M3","1","Prune belly syndrome"),
    "BRCA1":(6000,1863,"BRCA1","17","Breast/ovarian cancer · Fanconi anaemia"),
    "BRCA2":(5500,3418,"BRCA2","13","Breast/ovarian cancer · Fanconi anaemia"),
    "TP53": (8000,393,"Tumour protein p53","17","Li-Fraumeni syndrome · Most mutated cancer gene"),
    "EGFR": (1200,1210,"Epidermal growth factor receptor","7","Lung adenocarcinoma · Glioblastoma"),
    "KRAS": (900,189,"KRAS proto-oncogene","12","Pancreatic · colorectal · lung cancer · Noonan syndrome"),
    "MYH7": (700,1935,"Myosin heavy chain 7","14","Hypertrophic cardiomyopathy · Dilated cardiomyopathy"),
    "LMNA": (500,664,"Lamin A/C","1","Dilated cardiomyopathy · Muscular dystrophy · Progeria"),
    "ARRB1":(0,418,"β-arrestin 1","11","NONE — zero germline pathogenic variants"),
    "ARRB2":(0,410,"β-arrestin 2","17","NONE — zero germline pathogenic variants"),
    "TALN1":(0,2541,"Talin 1","9","NONE — zero germline pathogenic variants"),
    "TALN2":(0,1289,"Talin 2","15","NONE — zero germline pathogenic variants"),
    "ITB2": (200,769,"Integrin β2","21","Leucocyte adhesion deficiency"),
    "ITGA2B":(280,1039,"Integrin αIIb","17","Glanzmann thrombasthenia"),
    "ITB3": (300,788,"Integrin β3","17","Glanzmann thrombasthenia"),
    "ITAM": (3,1152,"Integrin αM","16","Very limited disease association despite many variants"),
    "ITAL": (1,1170,"Integrin αL","16","Very limited disease association despite many variants"),
}

PAPERS = {
    "king_2024":   {"cite":"King et al., Nature 2024","url":"https://www.nature.com/articles/s41586-024-07316-0","finding":"Drug targets with human genetic support are 2.6× more likely to succeed in clinical development."},
    "minikel_2021":{"cite":"Minikel et al., Nature 2021","url":"https://www.nature.com/articles/s41586-020-2267-z","finding":"Naturally occurring LOF variants provide in vivo human knockouts — more informative than mouse models."},
    "plenge_2016": {"cite":"Plenge et al., Nat Rev Drug Discov 2016","url":"https://www.nature.com/articles/nrd.2016.29","finding":"Most clinical failures occur because the target is not causally related to human disease."},
    "cook_2014":   {"cite":"Cook et al., Nat Rev Drug Discov 2014","url":"https://www.nature.com/articles/nrd4309","finding":"~90% of drug candidates fail. Right-target failures account for the majority of efficacy failures."},
    "braxton_2024":{"cite":"Braxton et al., Hum Genet 2024","url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC11303574/","finding":"Functional assay data reclassifies ~55% of VUS when calibrated against ClinVar."},
}

SESSION = requests.Session()
SESSION.headers.update({"User-Agent":"Protellect/4.0 research@protellect.com","Accept":"application/json"})

# ── Helpers ───────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_uniprot(gene: str) -> dict:
    base = {"found":False,"gene":gene,"uid":"","protein_name":"","length":0,
            "function":"","subcellular":[],"tissue":"","domains":[],"is_gpcr":False,
            "g_protein":"","natural_variants":[],"disease_comments":[],"keywords":[],
            "pdb_ids":[],"ensembl_id":"","omim":"","n_tm":0,"transmembrane_regions":[]}
    for q in [f'gene_exact:{gene} AND organism_id:9606 AND reviewed:true',
               f'gene:{gene} AND organism_id:9606 AND reviewed:true',
               f'gene:{gene} AND organism_id:9606']:
        try:
            r = SESSION.get("https://rest.uniprot.org/uniprotkb/search",
                            params={"query":q,"format":"json","size":1},timeout=12)
            if r.status_code==200 and r.json().get("results"):
                uid = r.json()["results"][0]["primaryAccession"]
                base["uid"] = uid
                base["found"] = True
                break
        except Exception: pass
    if not base["found"]: return base
    try:
        r2 = SESSION.get(f"https://rest.uniprot.org/uniprotkb/{base['uid']}",
                         params={"format":"json"},timeout=20)
        if r2.status_code != 200: return base
        d = r2.json()
        base["gene"]         = d.get("genes",[{}])[0].get("geneName",{}).get("value",gene) if d.get("genes") else gene
        base["protein_name"] = d.get("proteinDescription",{}).get("recommendedName",{}).get("fullName",{}).get("value","")
        base["length"]       = d.get("sequence",{}).get("length",0)
        for c in d.get("comments",[]):
            ct = c.get("commentType","")
            if ct=="FUNCTION":     base["function"]  = c.get("texts",[{}])[0].get("value","")[:600]
            elif ct=="SUBCELLULAR LOCATION":
                for loc in c.get("subcellularLocations",[]):
                    v=loc.get("location",{}).get("value","")
                    if v and v not in base["subcellular"]: base["subcellular"].append(v)
            elif ct=="TISSUE SPECIFICITY": base["tissue"] = c.get("texts",[{}])[0].get("value","")[:400]
            elif ct=="DISEASE":
                for dis in c.get("diseases",[]): base["disease_comments"].append(dis.get("disease",{}).get("diseaseName",{}).get("value",""))
        for f in d.get("features",[]):
            ft=f.get("type",""); loc=f.get("location",{})
            s=loc.get("start",{}).get("value"); e=loc.get("end",{}).get("value",s)
            if s is None: continue
            s,e=int(s),int(e); desc=f.get("description","")
            if ft in ("Domain","Region","Zinc finger","Transmembrane","Repeat","Motif"):
                base["domains"].append({"start":s,"end":e,"name":desc,"type":ft})
            if ft=="Transmembrane":
                base["transmembrane_regions"].append({"start":s,"end":e})
                base["n_tm"] += 1
            elif ft=="Natural variant":
                orig=f.get("alternativeSequence",{}).get("originalSequence","")
                var=f.get("alternativeSequence",{}).get("alternativeSequences",[""])[0]
                is_d=any(x in desc.lower() for x in ("disease","pathogenic","disorder","syndrome","myopathy"))
                base["natural_variants"].append({"pos":s,"orig":orig,"var":var,"note":desc,"disease":is_d})
        for xr in d.get("uniProtKBCrossReferences",[]):
            db=xr.get("database",""); xid=xr.get("id","")
            if db=="PDB": base["pdb_ids"].append(xid)
            elif db=="OMIM": base["omim"]=xid
            elif db=="Ensembl" and not base["ensembl_id"]: base["ensembl_id"]=xid
        kws=[kw.get("value","").lower() for kw in d.get("keywords",[])]
        base["keywords"]=kws
        gpcr_kw=["g protein-coupled","gpcr","rhodopsin","muscarinic","adrenergic","dopamine receptor","serotonin receptor","opioid","chemokine receptor","adenosine receptor","cannabinoid"]
        base["is_gpcr"] = any(k in " ".join(kws) for k in gpcr_kw) or base["n_tm"]==7
        if base["is_gpcr"]:
            known_gp={"CHRM1":"Gq/11","CHRM2":"Gi/o","CHRM3":"Gq/11","CHRM4":"Gi/o","CHRM5":"Gq/11",
                      "ADRB1":"Gs","ADRB2":"Gs","ADRA1A":"Gq/11","ADRA2A":"Gi/o",
                      "DRD1":"Gs","DRD2":"Gi/o","HTR1A":"Gi/o","HTR2A":"Gq/11"}
            base["g_protein"] = known_gp.get(gene.upper(),"")
    except Exception: pass
    return base

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_alphafold(uid: str, gene: str) -> tuple:
    """Returns (pdb_text, source_label). Always tries AlphaFold first."""
    if not uid: return None,""
    try:
        r = SESSION.get(f"https://alphafold.ebi.ac.uk/api/prediction/{uid}",timeout=12)
        if r.status_code==200 and r.json():
            pdb_url = r.json()[0].get("pdbUrl","")
            if pdb_url:
                pr = SESSION.get(pdb_url,timeout=20)
                if pr.status_code==200:
                    return pr.text[:400000], f"AlphaFold predicted structure · {uid}"
    except Exception: pass
    # Try best PDB
    try:
        r2 = SESSION.get("https://rest.uniprot.org/uniprotkb/search",
                         params={"query":f'accession:{uid}',"format":"json","size":1,"fields":"xref_pdb"},timeout=10)
        if r2.status_code==200:
            for xr in r2.json().get("results",[{}])[0].get("uniProtKBCrossReferences",[]):
                if xr.get("database")=="PDB":
                    pid=xr.get("id","")
                    pr=SESSION.get(f"https://files.rcsb.org/download/{pid}.pdb",timeout=15)
                    if pr.status_code==200:
                        return pr.text[:400000],f"PDB {pid} (experimental)"
    except Exception: pass
    return None,""

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_clinvar(gene: str) -> dict:
    result={"pathogenic":[],"likely_pathogenic":[],"benign":[],"vus":[],"somatic":[],"all":[],"diseases":set()}
    try:
        s=SESSION.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                      params={"db":"clinvar","term":f"{gene}[gene] AND single_gene[prop]","retmax":500,"retmode":"json","tool":"protellect","email":"research@protellect.com"},timeout=12)
        if not s or s.status_code!=200: return result
        ids=s.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return result
        time.sleep(0.35)
        for i in range(0,min(len(ids),500),100):
            batch=ids[i:i+100]; time.sleep(0.35)
            sm=SESSION.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                           params={"db":"clinvar","id":",".join(batch),"retmode":"json","tool":"protellect","email":"research@protellect.com"},timeout=20)
            if not sm or sm.status_code!=200: continue
            doc=sm.json().get("result",{})
            for vid in doc.get("uids",[]):
                e=doc.get(vid,{})
                germline_sig=e.get("germline_classification",{}).get("description","").strip()
                somatic_sig=e.get("somatic_clinical_impact",{}).get("description","").strip()
                onco=e.get("oncogenicity_classification",{}).get("description","").strip()
                is_somatic=bool((somatic_sig or onco) and not germline_sig)
                title=e.get("title",""); conditions=[c.get("trait_name","") for c in e.get("trait_set",[])]
                stars=e.get("review_status_label",""); sig=germline_sig or somatic_sig or onco or ""
                m=re.search(r'[A-Z\*](\d+)[A-Za-z\*=]',title); pos=int(m.group(1)) if m else 0
                var={"id":vid,"title":title,"sig":sig,"germline":germline_sig,"somatic":somatic_sig,"is_somatic":is_somatic,"conditions":[c for c in conditions if c],"stars":stars,"pos":pos}
                result["all"].append(var)
                for c in conditions:
                    if c: result["diseases"].add(c)
                if is_somatic: result["somatic"].append(var)
                else:
                    sl=sig.lower()
                    if "pathogenic" in sl and "likely" not in sl and "benign" not in sl: result["pathogenic"].append(var)
                    elif "likely pathogenic" in sl: result["likely_pathogenic"].append(var)
                    elif "benign" in sl and "likely" not in sl: result["benign"].append(var)
                    elif "uncertain" in sl or "vus" in sl: result["vus"].append(var)
    except Exception: pass
    result["diseases"]=sorted(list(result["diseases"]))
    return result

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_pubmed(gene: str, disease: str = "", n: int = 6) -> list:
    papers=[]; seen=set()
    queries=[f'{gene}[gene] AND "pathogenic variant" AND "human"[tiab]']
    if disease: queries.insert(0,f'{gene}[gene] AND "{disease}"[tiab] AND ("mutation" OR "variant")[tiab]')
    try:
        for q in queries:
            if len(papers)>=n: break
            s=SESSION.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                          params={"db":"pubmed","term":q,"retmax":4,"retmode":"json","sort":"relevance","tool":"protellect","email":"research@protellect.com"},timeout=10)
            if not s or s.status_code!=200: continue
            ids=[i for i in s.json().get("esearchresult",{}).get("idlist",[]) if i not in seen]; seen.update(ids)
            if not ids: continue
            time.sleep(0.3)
            sm=SESSION.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                           params={"db":"pubmed","id":",".join(ids),"retmode":"json","tool":"protellect","email":"research@protellect.com"},timeout=10)
            if not sm or sm.status_code!=200: continue
            rd=sm.json().get("result",{})
            for pid in rd.get("uids",[]):
                en=rd.get(pid,{})
                papers.append({"pmid":pid,"title":en.get("title","")[:100],"journal":en.get("fulljournalname",""),"year":en.get("pubdate","")[:4],"url":f"https://pubmed.ncbi.nlm.nih.gov/{pid}/"})
    except Exception: pass
    return papers[:n]

def get_protein_ground_truth(gene: str) -> dict:
    gu = gene.upper().strip()
    if gu in GROUND_TRUTH:
        n,l,pname,chrom,diseases=GROUND_TRUTH[gu]
        dbr=calculate_dbr(n,l)
        tier=assign_genomic_tier(dbr,n)
        return {"n_path":n,"length":l,"protein_name":pname,"chromosome":chrom,
                "diseases":diseases,"dbr":dbr,"tier":tier,"from_ground_truth":True}
    return {"n_path":0,"length":0,"protein_name":"","chromosome":"","diseases":"","dbr":None,"tier":"UNKNOWN","from_ground_truth":False}

def make_3d_viewer(pdb_text, scored_residues, width=700, height=450,
                   clinvar_positions=None, residue_annotations=None, gene_label=""):
    """Bright clickable 3D viewer — click any residue for full mutation triage."""
    if not pdb_text or len(pdb_text)<100:
        return f"<html><body style='margin:0;background:#0a0e1a;display:flex;align-items:center;justify-content:center;height:{height}px;font-family:IBM Plex Mono,monospace;color:#4CA8FF;text-align:center;font-size:12px'>AlphaFold structure loading...</body></html>"
    esc = pdb_text[:380000].replace("\\","\\\\").replace("`","\\`").replace("${","\\${")
    res_list=[]
    for line in pdb_text.split('\n'):
        if line.startswith('ATOM'):
            try: res_list.append(int(line[22:26].strip()))
            except: pass
    zoom = f"{min(res_list)}-{max(res_list)}" if res_list else "1-999"
    # Sphere JS
    sph_parts=[]
    for r,d in scored_residues.items():
        sph_parts.append("v.addStyle({resi:%d},{sphere:{color:'%s',radius:%s,opacity:0.95}});" % (r,d["color"],d["radius"]))
    cv_positions = clinvar_positions or {}
    for pos in cv_positions:
        if int(pos) not in scored_residues:
            sph_parts.append("v.addStyle({resi:%d},{sphere:{color:'#FF2244',radius:0.8,opacity:0.9}});" % int(pos))
    sph = "\n".join(sph_parts)
    annot_json = json.dumps(residue_annotations or {})
    cv_json    = json.dumps({str(k):v for k,v in cv_positions.items()})
    gene_safe  = gene_label.replace("'","").replace('"',"")

    html = f"""<!DOCTYPE html><html><head>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.3/3Dmol-min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0a0e1a;overflow:hidden}}
#wrap{{display:flex;height:{height}px}}
#v{{flex:1;min-width:0}}
#panel{{width:0;background:#0c1428;border-left:2px solid #1e3060;transition:width 0.25s;overflow:hidden}}
#panel.open{{width:240px}}
#pi{{padding:14px;width:240px}}
.pt{{font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:0.14em;color:#4477aa;margin-bottom:4px;margin-top:10px}}
.pv{{font-size:11px;color:#cce0ff;line-height:1.6;margin-bottom:2px}}
.badge{{display:inline-block;padding:3px 10px;border-radius:10px;font-family:'IBM Plex Mono',monospace;font-size:9px;font-weight:600;margin:2px}}
.exp{{background:#0a1830;border:1px solid #1e3060;border-radius:6px;padding:8px 10px;margin-top:6px;font-size:10px;color:#88aacc;line-height:1.6}}
.hint{{position:absolute;bottom:8px;left:50%;transform:translateX(-50%);background:#0c1428cc;border:1px solid #1e3060;border-radius:20px;padding:4px 16px;font-size:10px;font-family:'IBM Plex Mono',monospace;color:#336699;pointer-events:none}}
</style>
</head><body style="position:relative">
<div id="wrap"><div id="v"></div><div id="panel"><div id="pi"><div id="pc" style="color:#336699;font-family:'IBM Plex Mono',monospace;font-size:10px;text-align:center;padding-top:50px">🔬<br><br>Click any residue<br>sphere to see full<br>mutation triage</div></div></div></div>
<div class="hint">● Click residue sphere for triage · ● = ClinVar pathogenic · ● = Wet lab hit</div>
<script>
const pdb=`{esc}`;
const ANNOT={annot_json};
const CV={cv_json};
const GENE='{gene_safe}';
let v=$3Dmol.createViewer('v',{{backgroundColor:'#0a0e1a',antialias:true}});
v.addModel(pdb,'pdb');
// BRIGHT high-contrast cartoon
v.setStyle({{}},{{cartoon:{{color:'spectrum',opacity:0.82,thickness:0.5,smoothSheet:true}}}});
// Faint surface
v.addSurface($3Dmol.VDW,{{opacity:0.04,color:'#4488ff'}});
{sph}
v.setHoverable({{}},true,function(a){{
  if(!a||!a.resi)return;
  const cv=CV[String(a.resi)]||{{}};
  const an=ANNOT[String(a.resi)]||{{}};
  const p=an.priority||'';
  const pc=p==='HIGH'?'#FF4444':p==='MEDIUM'?'#FFA500':'#4CA8FF';
  const hint=document.querySelector('.hint');
  if(hint)hint.innerHTML='<b style="color:'+pc+'">['+p+']</b> '+a.resn+'-'+a.resi+(cv.sig?' · ClinVar: '+cv.sig.slice(0,25):'');
}},function(){{const h=document.querySelector('.hint');if(h)h.innerHTML='● Click residue sphere for triage · ● = ClinVar pathogenic · ● = Wet lab hit';}});
function applyStyles(){{
  v.setStyle({{}},{{cartoon:{{color:'spectrum',opacity:0.82,thickness:0.5,smoothSheet:true}}}});
  {sph}
}}
v.setClickable({{}},true,function(atom){{
  if(!atom||!atom.resi)return;
  const r=atom.resi; const resn=atom.resn||'';
  const cv=CV[String(r)]||{{}};
  const an=ANNOT[String(r)]||{{}};
  const priority=an.priority||'—';
  const score=typeof an.score==='number'?an.score.toFixed(3):an.score||'—';
  const hyp=(an.hypothesis||'').slice(0,140);
  const pc=priority==='HIGH'?'#FF4444':priority==='MEDIUM'?'#FFA500':'#4CA8FF';
  const cvHtml=cv.sig?
    '<div class="pt">ClinVar (germline)</div><div class="pv" style="color:#ff6688">'+cv.sig+'</div><div class="pv" style="color:#aac">'+(cv.conditions||[]).slice(0,2).join(' · ')+'</div>':
    '<div class="pt">ClinVar</div><div class="pv" style="color:#336699">No germline pathogenic at Pos '+r+'</div>';
  const expText=priority==='HIGH'?'ITC binding assay (gold standard) — quantify Kd change vs WT. No fluorescent artefacts. Recommended by Sujay Ithychanda, Cleveland Clinic':
    priority==='MEDIUM'?'Thermal shift DSF — confirm ΔTm vs WT. Expect 3-8°C for moderate variants. Then ITC if confirmed':
    'ClinVar + gnomAD database check first — free, <1h. Confirm this position has no known human disease variant';
  document.getElementById('pc').innerHTML=
    '<div class="pt" style="margin-top:0">'+GENE+' · Position '+r+'</div>'+
    '<div style="font-size:14px;font-weight:600;color:#eef;font-family:IBM Plex Mono,monospace;margin:4px 0">'+resn+'-'+r+'</div>'+
    '<span class="badge" style="background:'+pc+'22;color:'+pc+';border:1px solid '+pc+'66">'+priority+' PRIORITY</span>'+
    '<span class="badge" style="background:#1a2040;color:#99aacc;border:1px solid #252840">score '+score+'</span>'+
    cvHtml+
    (hyp?'<div class="pt">Hypothesis</div><div class="pv">'+hyp+'</div>':'')+
    '<div class="pt">Recommended experiment</div>'+
    '<div class="exp">'+expText+'</div>'+
    '<div style="margin-top:10px;font-size:9px;color:#336699;text-align:center;font-family:IBM Plex Mono,monospace">Click another residue to compare</div>';
  document.getElementById('panel').classList.add('open');
  applyStyles();
  v.addStyle({{resi:r}},{{sphere:{{color:'#ffffff',radius:1.4,opacity:1}}}});
  v.render();
}});
v.zoomTo({{resi:'{zoom}'}});v.spin(false);v.render();
</script></body></html>"""
    return html


def paper_chip(key: str) -> str:
    p=PAPERS.get(key,{})
    if not p: return ""
    return f'<a href="{p["url"]}" target="_blank" style="display:inline-block;background:#0a0c1a;border:1px solid #1e2030;color:#4CA8FF;font-family:IBM Plex Mono,monospace;font-size:0.65rem;padding:2px 10px;border-radius:10px;text-decoration:none;margin:2px">📄 {p["cite"]}</a>'

def dbr_bar(dbr, max_dbr=2.0):
    if dbr is None: return ""
    pct=min(dbr/max_dbr*100,100)
    c="#FF4C4C" if pct>40 else "#FFA500" if pct>10 else "#FFD700" if pct>0 else "#333"
    return f'<div style="background:#1a1d2e;border-radius:3px;height:6px;overflow:hidden;margin-top:4px"><div style="width:{pct:.0f}%;height:100%;background:{c};border-radius:3px"></div></div>'

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600&family=Inter:wght@300;400;500;600&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif}
h1,h2,h3{font-family:'IBM Plex Mono',monospace}
[data-testid="stSidebar"]{background:#0a0b14;border-right:1px solid #12141e}
.block{background:#0d1020;border:1px solid #252840;border-radius:10px;padding:16px 18px;margin-bottom:12px}
.block-red{background:#0a0607;border:1px solid #FF4C4C55;border-radius:10px;padding:16px 18px;margin-bottom:12px}
.block-green{background:#070a07;border:1px solid #4CAF5055;border-radius:10px;padding:16px 18px;margin-bottom:12px}
.label{font-family:'IBM Plex Mono',monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.18em;color:#5a5d7a;padding-bottom:5px;border-bottom:1px solid #12141e;margin-bottom:10px}
.stat{background:#0a0b14;border:1px solid #1e2035;border-radius:8px;padding:14px;text-align:center}
.stat-n{font-size:1.6rem;font-weight:600;font-family:'IBM Plex Mono',monospace;display:block}
.stat-l{font-size:0.62rem;text-transform:uppercase;letter-spacing:0.1em;color:#555;margin-top:3px}
.row{display:flex;gap:8px;padding:5px 0;border-bottom:1px solid #0d0f18;font-size:0.8rem}
.rl{color:#4a4d6a;min-width:100px;font-family:'IBM Plex Mono',monospace;font-size:0.68rem;flex-shrink:0}
.rv{color:#bbb}
.pill{display:inline-block;padding:2px 10px;border-radius:12px;font-size:0.65rem;font-family:'IBM Plex Mono',monospace;margin:2px}
.hyp{background:#0d1020;border-left:2px solid #1a1d2e;padding:10px 14px;border-radius:0 6px 6px 0;font-size:0.8rem;color:#aaaaaa;line-height:1.8;margin-bottom:8px}
.dis-pill{padding:5px 12px;margin-bottom:4px;background:#0a0607;border:1px solid #FF4C4C22;border-radius:5px;font-size:0.78rem;color:#bbb}
</style>""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    if LOGO_B64:
        st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px"><img src="{LOGO_B64}" style="width:32px;height:32px;object-fit:contain;border-radius:6px"><span style="font-family:IBM Plex Mono,monospace;font-size:1.1rem;font-weight:600;color:#eee">Protellect</span></div>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:0.65rem;color:#4a4d6a;font-family:IBM Plex Mono,monospace;margin:-2px 0 12px">Experimental Intelligence Layer v4</p>', unsafe_allow_html=True)
    if ML_AVAILABLE:
        st.markdown('<div style="background:#0a0c1a;border:1px solid #1a2a4a;border-radius:6px;padding:6px 10px;font-size:0.72rem;color:#6688cc;margin-bottom:12px">🤖 ML scoring active</div>', unsafe_allow_html=True)

    st.markdown('<div class="label" style="margin-top:4px">Protein / Gene</div>', unsafe_allow_html=True)
    protein_input = st.text_input("Gene or protein name", placeholder="e.g. FLNA, CHRM2, BRCA1, TP53...", key="qa_prot", label_visibility="collapsed")

    st.markdown('<div class="label">Research goal</div>', unsafe_allow_html=True)
    study_goal = st.text_input("Study goal", placeholder="e.g. identify drug targets in cardiomyopathy", key="qa_goal", label_visibility="collapsed")

    st.markdown('<div class="label">Disease context</div>', unsafe_allow_html=True)
    disease_ctx = st.text_input("Disease context", placeholder="e.g. prune belly syndrome, cardiomyopathy", key="qa_dis", label_visibility="collapsed")

    st.markdown('<div class="label">Research direction</div>', unsafe_allow_html=True)
    direction = st.selectbox("Direction", ["Not specified","Find drug targets","Loss-of-function analysis","Gain-of-function analysis","Clinical variant interpretation","Structural biology","Basic science mechanism"], label_visibility="collapsed", key="qa_dir")

    st.divider()
    st.markdown('<div class="label">Wet Lab Data (optional)</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload assay data", type=["csv","tsv","xlsx","xls","txt"], label_visibility="collapsed")
    st.caption("CSV · TSV · Excel · any biological format  \nDMS · CRISPR · RNA-seq · proteomics · variants")
    use_sample = st.checkbox("Use TP53 DMS sample data", value=not bool(uploaded_file) and not bool(protein_input))

    st.divider()
    st.markdown('<div class="label">Scoring Sensitivity</div>', unsafe_allow_html=True)
    preset = st.selectbox("Profile", ["Standard (0.75/0.40)","Strict (0.85/0.55)","Permissive (0.65/0.30)"], label_visibility="collapsed", key="sens")
    pmap = {"Standard (0.75/0.40)":(0.75,0.40),"Strict (0.85/0.55)":(0.85,0.55),"Permissive (0.65/0.30)":(0.65,0.30)}
    high_t, med_t = pmap[preset]

    use_db = st.checkbox("Live DB enrichment (UniProt · ClinVar · AlphaFold)", value=True)
    run_btn = st.button("▶  Analyse", type="primary", use_container_width=True)

    # Sidebar results summary
    if "prot_data" in st.session_state and st.session_state.prot_data.get("found"):
        pd_s = st.session_state.prot_data; gt = st.session_state.get("gt",{})
        n_path=gt.get("n_path",0)
        tc={"CRITICAL":"#FF4C4C","HIGH":"#FFA500","LOW":"#FFD700","NONE":"#888","UNKNOWN":"#4CA8FF"}.get(gt.get("tier","UNKNOWN"),"#888")
        cur_gene = st.session_state.get("gene","")
        pdata_sb = get_protein_info(cur_gene) if cur_gene else {}
        role_sb  = classify_protein_role(cur_gene, n_path)
        gpcr_type_sb = pdata_sb.get("gpcr_interaction",{}).get("type","")
        st.divider()
        dbr_val_sb = gt.get("dbr",0)
        dbr_str_sb = f"{dbr_val_sb:.3f}" if dbr_val_sb else "—"
        role_label_sb = role_sb["label"][:22] if role_sb.get("label") else "—"
        gpcr_label_sb = ("GPCR: "+gpcr_type_sb[:18]) if gpcr_type_sb else "Non-GPCR"
        prot_name_sb = pd_s.get("protein_name","")[:40]
        gene_sb = pd_s.get("gene","")
        st.markdown(f'<div style="background:#0d1020;border:1px solid {tc};border-radius:10px;padding:12px 14px;margin-bottom:8px"><div style="font-family:IBM Plex Mono,monospace;font-size:0.62rem;color:{tc};text-transform:uppercase;margin-bottom:6px">{gt.get("tier","—")} · DBR {dbr_str_sb}</div><div style="font-size:0.88rem;font-weight:600;color:#f0f0f0;margin-bottom:2px">{gene_sb}</div><div style="font-size:0.72rem;color:#777;margin-bottom:8px">{prot_name_sb}</div><div style="display:flex;justify-content:space-between;align-items:center"><div><div style="font-size:1.6rem;font-weight:700;font-family:IBM Plex Mono,monospace;color:{tc}">{n_path}</div><div style="font-size:0.6rem;color:#666;text-transform:uppercase">Germline pathogenic</div></div><div style="text-align:right"><div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;color:{tc}">{role_sb["icon"]} {role_label_sb}</div><div style="font-size:0.62rem;color:#666;margin-top:2px">{gpcr_label_sb}</div></div></div>{dbr_bar(dbr_val_sb)}</div>', unsafe_allow_html=True)
        spec_exps_sb = pdata_sb.get("experiments_specific",[])
        if spec_exps_sb:
            next_exp_sb = spec_exps_sb[0]
            st.markdown(f'<div style="background:#070a07;border:1px solid #1a3a1a;border-radius:8px;padding:10px 12px;margin-bottom:8px"><div style="font-family:IBM Plex Mono,monospace;font-size:0.6rem;text-transform:uppercase;color:#4CAF50;margin-bottom:4px">Recommended next experiment</div><div style="font-size:0.75rem;color:#dddddd;font-weight:600;margin-bottom:3px">{next_exp_sb["name"][:42]}</div><div style="font-size:0.68rem;color:#777">{next_exp_sb.get("rationale","")[:75]}...</div></div>', unsafe_allow_html=True)
        st.markdown(paper_chip("king_2024"), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# RUN ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
ctx = {"study_goal":study_goal,"disease_context":disease_ctx,"hypothesis_direction":direction,"protein_of_interest":protein_input}
gene = protein_input.strip().upper() if protein_input.strip() else ""

if run_btn or (gene and "prot_data" not in st.session_state):
    if not gene:
        st.sidebar.error("⬆ Enter a gene/protein name to begin.")
    else:
        with st.sidebar:
            with st.spinner(f"Loading {gene}..."):
                prot_data = fetch_uniprot(gene)
                gt = get_protein_ground_truth(gene)
                cv = fetch_clinvar(gene) if use_db else {"pathogenic":[],"likely_pathogenic":[],"benign":[],"vus":[],"somatic":[],"all":[],"diseases":[]}
                pdb_text, pdb_source = fetch_alphafold(prot_data.get("uid",""), gene) if use_db else (None,"")

                # Wet lab scoring
                scored = None; stats = None; info = None; pathways = None
                if uploaded_file:
                    df_raw = load_file(uploaded_file)
                    valid, err = validate_dataframe(df_raw)
                    if valid:
                        info     = detect_dataset_info(df_raw, ctx)
                        scored   = score_residues(df_raw, context=ctx, high_t=high_t, med_t=med_t)
                        stats    = get_summary_stats(scored)
                        pathways = generate_top_pathways(scored, info, ctx)
                elif use_sample:
                    df_raw = pd.read_csv("sample_data/example.csv")
                    info     = detect_dataset_info(df_raw, ctx)
                    scored   = score_residues(df_raw, context=ctx, high_t=high_t, med_t=med_t)
                    stats    = get_summary_stats(scored)
                    pathways = generate_top_pathways(scored, info, ctx)

                st.session_state.update({
                    "prot_data":prot_data, "gt":gt, "cv":cv,
                    "pdb_text":pdb_text, "pdb_source":pdb_source,
                    "scored":scored, "stats":stats, "info":info, "pathways":pathways,
                    "gene":gene, "ctx":ctx,
                })

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🧬  Triage","🔬  Protein Profile","🗺️  Visual Context","💊  Therapy","🔎  Deep Dive","🦠  Disease Explorer"
])

# ──────────────────────────────────────────────────────────────────────────────
# TAB 1 — TRIAGE
# ──────────────────────────────────────────────────────────────────────────────
with tab1:
    if not gene:
        if LOGO_B64:
            st.markdown(f'<div style="text-align:center;padding:40px 0"><img src="{LOGO_B64}" style="height:64px;object-fit:contain;border-radius:12px;margin-bottom:16px"><h2 style="font-family:IBM Plex Mono,monospace;color:#f0f0f0;margin:0">Protellect</h2><p style="color:#555;margin:8px 0 24px">Enter a protein name in the sidebar to begin. Wet lab data is optional.</p></div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;max-width:900px;margin:0 auto">
          <div class="block"><div class="label">How it works</div><p style="font-size:0.82rem;color:#666;line-height:1.7">Enter any gene/protein → Protellect fetches AlphaFold structure, ClinVar germline variants, UniProt annotation. Wet lab data augments the analysis but is never the primary truth.</p></div>
          <div class="block"><div class="label">ClinVar first</div><p style="font-size:0.82rem;color:#666;line-height:1.7">The only ground truth for target validation is germline pathogenic variants in humans. {paper_chip("king_2024")} Proteins with variants = essential. Proteins without = question everything.</p></div>
          <div class="block"><div class="label">Try these proteins</div>
            <p style="font-size:0.8rem;color:#666;margin-bottom:8px">High burden: FLNA · FLNC · CHRM2 · TP53</p>
            <p style="font-size:0.8rem;color:#666;margin-bottom:8px">Rare Mendelian: CHRM3 · LMNA</p>
            <p style="font-size:0.8rem;color:#666">Scaffolds: ARRB1 · ARRB2 · TALN1</p>
          </div>
        </div>""", unsafe_allow_html=True)
        st.stop()

    if "prot_data" not in st.session_state:
        st.info("👈 Click **▶ Analyse** to load the protein.")
        st.stop()

    pd_s = st.session_state.prot_data
    gt   = st.session_state.get("gt",{})
    cv   = st.session_state.get("cv",{})
    pdb  = st.session_state.get("pdb_text")
    pdb_src = st.session_state.get("pdb_source","")
    scored= st.session_state.get("scored")
    stats = st.session_state.get("stats")
    info  = st.session_state.get("info")
    pathways = st.session_state.get("pathways",[])

    n_path = gt.get("n_path",0)
    tier   = gt.get("tier","UNKNOWN")
    dbr    = gt.get("dbr")
    tc     = {"CRITICAL":"#FF4C4C","HIGH":"#FFA500","LOW":"#FFD700","NONE":"#888","UNKNOWN":"#4CA8FF"}.get(tier,"#888")
    role   = classify_protein_role(gene, n_path)
    prot_name = pd_s.get("protein_name","") or gt.get("protein_name","") or gene
    diseases_str = gt.get("diseases","")

    # ── BIG DISEASE ASSOCIATION BANNER ────────────────────────────────────────
    if tier == "NONE":
        banner_title = f"⚪ NO GERMLINE DISEASE ASSOCIATION — Zero pathogenic variants"
        banner_body  = f"{gene} has zero confirmed germline pathogenic variants in ClinVar. Humans who carry broken versions are apparently healthy. This is the β-arrestin pattern — extensively studied in vitro, not validated in human genetics."
        banner_action= f"DO NOT pursue as primary drug target. Study interaction partners that DO have ClinVar burden."
        banner_style = "border-color:#555"
    elif tier in ("CRITICAL","HIGH"):
        banner_title = f"{role['icon']} {tier} — {role['label']}"
        banner_body  = f"{n_path} confirmed germline pathogenic variants. Diseases: {diseases_str[:120]}"
        banner_action= f"Human genetics unambiguously supports this target. {paper_chip('king_2024')}"
        banner_style = f"border-color:{tc}"
    else:
        banner_title = f"🟡 CONFIRMED RARE MENDELIAN DISEASE GENE"
        banner_body  = f"{n_path} confirmed pathogenic variant(s). Low count reflects disease rarity — NOT protein dispensability. Diseases: {diseases_str}"
        banner_action= "Pursue with rare disease strategy. Orphan drug regulatory pathway applies."
        banner_style = "border-color:#FFD700"

    st.markdown(f"""
    <div style="background:#0d0e1a;border:2px solid;{banner_style};border-radius:14px;padding:22px 26px;margin-bottom:20px">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:1rem;font-weight:700;color:{tc};margin-bottom:8px">{banner_title}</div>
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap">
        <div style="flex:1">
          <div style="font-size:0.88rem;color:#f0f0f0;font-weight:600;margin-bottom:4px">{gene} — {prot_name}</div>
          <div style="font-size:0.82rem;color:#aaaaaa;line-height:1.7;margin-bottom:8px">{banner_body}</div>
          <div style="font-size:0.8rem;color:#4CAF50">{banner_action}</div>
        </div>
        <div style="text-align:right;min-width:140px">
          <div style="font-size:2.2rem;font-weight:700;font-family:'IBM Plex Mono',monospace;color:{tc}">{n_path}</div>
          <div style="font-size:0.65rem;color:#666;text-transform:uppercase;letter-spacing:0.1em">germline pathogenic</div>
          <div style="font-size:0.75rem;color:{tc};font-family:'IBM Plex Mono',monospace;margin-top:4px">DBR {f"{dbr:.3f}" if dbr else "N/A"}</div>
          {dbr_bar(dbr)}
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Piggyback warning ──────────────────────────────────────────────────────
    if role.get("role")=="piggyback":
        partners = role.get("partners",["interaction partners"])[:4]
        st.markdown(f"""
        <div class="block-red">
          <div class="label" style="color:#FF4C4C44;border-color:#FF4C4C22">⚠ Structural scaffold / piggyback protein</div>
          <p style="font-size:0.83rem;color:#cccccc;line-height:1.7;margin:0">{role.get('note','')} Study these proteins instead: <strong style="color:#eee">{' · '.join(partners)}</strong></p>
          <div style="margin-top:8px">{paper_chip('minikel_2021')} {paper_chip('plenge_2016')}</div>
        </div>""", unsafe_allow_html=True)

    # ── Main layout: structure + triage ───────────────────────────────────────
    sc, tc2 = st.columns([1.4,1], gap="large")

    with sc:
        st.markdown(f'<div class="label">AlphaFold / PDB Structure — {gene}</div>', unsafe_allow_html=True)
        if pdb_src: st.caption(f"🏗️ {pdb_src}")

        # Build scored residue map
        cmap={"HIGH":"#FF4C4C","MEDIUM":"#FFA500","LOW":"#4CA8FF"}
        rmap={"HIGH":1.1,"MEDIUM":0.75,"LOW":0.45}
        rs={}

        if scored is not None and pdb:
            pdb_res=set()
            for line in pdb.split('\n'):
                if line.startswith('ATOM'):
                    try: pdb_res.add(int(line[22:26].strip()))
                    except: pass
            pc_col = "priority_final" if "priority_final" in scored.columns else "priority"
            upos=[int(r["residue_position"]) for _,r in scored.iterrows()]
            if pdb_res and any(p in pdb_res for p in upos):
                rs={int(row["residue_position"]):{"color":cmap[str(row[pc_col])],"radius":rmap[str(row[pc_col])]} for _,row in scored.iterrows() if int(row["residue_position"]) in pdb_res}
            else:
                pr=sorted(pdb_res) if pdb_res else list(range(1,min(pd_s.get("length",500)+1,500)))
                n_map=min(len(scored),len(pr))
                mp=[pr[i] for i in np.linspace(0,len(pr)-1,n_map,dtype=int)]
                rs={mp[i]:{"color":cmap[str(row[pc_col])],"radius":rmap[str(row[pc_col])]*1.5} for i,(_,row) in enumerate(scored.head(n_map).iterrows())}
        elif pdb and n_path > 0:
            # Colour by ClinVar pathogenic positions
            cv_path = cv.get("pathogenic",[]) + cv.get("likely_pathogenic",[])
            for v in cv_path[:60]:
                pos=v.get("pos",0)
                if pos>0: rs[pos]={"color":"#FF4C4C","radius":0.9}

        if pdb:
            # Build residue annotation dict for click panel
            res_annot = {}
            if scored is not None:
                pc_col_v = "priority_final" if "priority_final" in scored.columns else "priority"
                for _, row_v in scored.iterrows():
                    pos_v = int(row_v["residue_position"])
                    res_annot[str(pos_v)] = {
                        "priority": str(row_v.get(pc_col_v,"LOW")),
                        "score":    float(row_v.get("normalized_score",0)),
                        "hypothesis": str(row_v.get("hypothesis",""))[:200],
                    }
            # Build ClinVar position dict
            cv_pos_map = {}
            for v_cv in cv.get("pathogenic",[]) + cv.get("likely_pathogenic",[]):
                pos_cv = v_cv.get("pos",0)
                if pos_cv > 0:
                    cv_pos_map[pos_cv] = {
                        "sig": v_cv.get("germline","") or v_cv.get("sig",""),
                        "conditions": v_cv.get("conditions",[]),
                    }
            components.html(make_3d_viewer(pdb, rs, 700, 450,
                                            clinvar_positions=cv_pos_map,
                                            residue_annotations=res_annot,
                                            gene_label=gene), height=456)
            st.markdown('<div style="display:flex;gap:18px;margin-top:5px;font-size:0.75rem"><span><span style="color:#FF4C4C">●</span> HIGH / Pathogenic</span><span><span style="color:#FFA500">●</span> MEDIUM</span><span><span style="color:#4CA8FF">●</span> LOW / Benign</span></div>', unsafe_allow_html=True)
        else:
            st.markdown(f"""<div style="background:#060910;border:1px solid #1e2035;border-radius:10px;height:380px;display:flex;align-items:center;justify-content:center;text-align:center;color:#555;font-family:IBM Plex Mono,monospace;font-size:12px">
              AlphaFold structure loading...<br><span style="font-size:10px;color:#222;display:block;margin-top:8px">Enable DB enrichment and click Analyse</span></div>""", unsafe_allow_html=True)

    with tc2:
        # Stat cards
        st.markdown('<div class="label">ClinVar Germline Evidence</div>', unsafe_allow_html=True)
        n_lp = len(cv.get("likely_pathogenic",[]))
        n_p  = len(cv.get("pathogenic",[]))
        n_b  = len(cv.get("benign",[]) + cv.get("likely_benign",[]) if cv.get("likely_benign") else cv.get("benign",[]))
        n_vus= len(cv.get("vus",[]))
        n_som= len(cv.get("somatic",[]))

        c1,c2 = st.columns(2)
        c1.markdown(f'<div class="stat"><span class="stat-n" style="color:#FF4C4C">{n_path}</span><span class="stat-l">Germline P/LP</span></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat"><span class="stat-n" style="color:#FFA500">{n_som}</span><span class="stat-l">Somatic only ⚠</span></div>', unsafe_allow_html=True)
        c3,c4 = st.columns(2)
        c3.markdown(f'<div class="stat"><span class="stat-n" style="color:#555">{n_vus}</span><span class="stat-l">VUS</span></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="stat"><span class="stat-n" style="color:#4CA8FF">{n_b}</span><span class="stat-l">Benign/LB</span></div>', unsafe_allow_html=True)

        if n_som > 0:
            st.markdown(f'<div style="background:#14100a;border:1px solid #3a2a0055;border-radius:6px;padding:8px 12px;margin-top:6px;font-size:0.73rem;color:#888">⚠ {n_som} somatic variants excluded from disease count. Somatic = cancer cell mutations, NOT inherited disease evidence. {paper_chip("minikel_2021")}</div>', unsafe_allow_html=True)

        # Disease list
        if diseases_str:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="label">Confirmed diseases (ClinVar)</div>', unsafe_allow_html=True)
            for dis in diseases_str.split("·")[:6]:
                if dis.strip():
                    st.markdown(f'<div class="dis-pill">● {dis.strip()}</div>', unsafe_allow_html=True)

        # Wet lab stats
        if scored is not None and stats:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="label">Wet Lab Triage Results</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:0.72rem;color:#777;margin-bottom:6px">{info.get("assay_guess","") if info else ""}</div>', unsafe_allow_html=True)
            c5,c6,c7 = st.columns(3)
            c5.markdown(f'<div class="stat"><span class="stat-n" style="color:#FF4C4C">{stats["high_priority"]}</span><span class="stat-l">HIGH</span></div>', unsafe_allow_html=True)
            c6.markdown(f'<div class="stat"><span class="stat-n" style="color:#FFA500">{stats["medium_priority"]}</span><span class="stat-l">MEDIUM</span></div>', unsafe_allow_html=True)
            c7.markdown(f'<div class="stat"><span class="stat-n" style="color:#4CA8FF">{stats["low_priority"]}</span><span class="stat-l">LOW</span></div>', unsafe_allow_html=True)

    # ── Residue triage table ───────────────────────────────────────────────────
    if scored is not None:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="label">Residue Triage — every hit annotated by genetic framework</div>', unsafe_allow_html=True)
        pc_col = "priority_final" if "priority_final" in scored.columns else "priority"
        top_n  = st.slider("Show top N residues", 3, min(20,len(scored)), min(10,len(scored)))

        cv_path_set = {v.get("pos",0) for v in cv.get("pathogenic",[]) + cv.get("likely_pathogenic",[])}

        for _, row in scored.head(top_n).iterrows():
            p   = str(row.get(pc_col,"LOW"))
            col = "#FF4C4C" if p=="HIGH" else "#FFA500" if p=="MEDIUM" else "#4CA8FF"
            pos = int(row["residue_position"])
            mut = str(row.get("mutation",f"Pos{pos}")); mut = f"Pos{pos}" if mut in ("nan","") else mut
            score = round(float(row["normalized_score"]),3)
            hyp   = str(row.get("hypothesis",""))
            conf  = row.get("ml_confidence",None)
            conf_s= f" · ML {conf:.0%}" if pd.notna(conf) else ""
            in_cv = pos in cv_path_set
            cv_badge = f'<span class="pill" style="background:#1a0808;border:1px solid #FF4C4C55;color:#FF4C4C">ClinVar pathogenic at pos {pos}</span>' if in_cv else ""
            # Domain info
            dom = ""
            for d in pd_s.get("domains",[]):
                if d["start"]<=pos<=d["end"]:
                    dom = f'<span class="pill" style="background:#100a18;border:1px solid #9370DB44;color:#9370DB">{d.get("name","domain")}</span>'
                    break
            active = pos in pd_s.get("active_sites",[])
            active_badge = '<span class="pill" style="background:#0a1418;border:1px solid #4CA8FF55;color:#4CA8FF">Active site</span>' if active else ""

            st.markdown(
                f'<div style="margin-bottom:10px">'
                f'<span style="font-family:IBM Plex Mono,monospace;font-size:0.72rem;font-weight:600;color:{col}">[{p}]</span> '
                f'<span style="color:#f0f0f0;font-family:IBM Plex Mono,monospace;font-size:0.82rem">{mut}</span>'
                f'<span style="color:#666;font-size:0.7rem;font-family:IBM Plex Mono,monospace"> · score {score}{conf_s}</span>'
                f'{cv_badge}{dom}{active_badge}'
                f'<div class="hyp">{hyp}</div></div>',
                unsafe_allow_html=True)

        # Export to Excel
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⬇ Export results as Excel workbook (multiple sheets)"):
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                # Sheet 1: Scored residues
                export_df = scored.drop(columns=["hypothesis"],errors="ignore")
                export_df.to_excel(writer, sheet_name="Triage Results", index=True)
                # Sheet 2: ClinVar pathogenic
                if cv.get("pathogenic") or cv.get("likely_pathogenic"):
                    cv_df = pd.DataFrame(cv.get("pathogenic",[]) + cv.get("likely_pathogenic",[]))
                    cv_df.to_excel(writer, sheet_name="ClinVar Germline Pathogenic", index=False)
                # Sheet 3: Somatic
                if cv.get("somatic"):
                    sdf = pd.DataFrame(cv["somatic"])
                    sdf.to_excel(writer, sheet_name="ClinVar Somatic (excluded)", index=False)
                # Sheet 4: Protein info
                info_df = pd.DataFrame([{"Gene":gene,"UniProt":pd_s.get("uid",""),"Protein":prot_name,"Length":pd_s.get("length",""),"Chromosome":gt.get("chromosome",""),"DBR":dbr,"Tier":tier,"Germline Pathogenic":n_path,"GPCR":pd_s.get("is_gpcr",False),"Diseases":diseases_str}])
                info_df.to_excel(writer, sheet_name="Protein Summary", index=False)
            buf.seek(0)
            st.download_button("Download Excel workbook", buf, f"protellect_{gene}_analysis.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Experimental pathways
    if pathways:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="label">Experimental Pathways — tailored to your data and goal</div>', unsafe_allow_html=True)
        for pw in pathways:
            with st.expander(f"{pw['icon']} {pw['rank']}. {pw['title']} · {pw['cost']} · {pw['timeline']}"):
                st.markdown(f"*{pw['rationale']}*")
                for step in pw["steps"]:
                    st.markdown(f"• {step}")

# ──────────────────────────────────────────────────────────────────────────────
# TAB 2 — PROTEIN PROFILE
# ──────────────────────────────────────────────────────────────────────────────
with tab2:
    if "prot_data" not in st.session_state or not gene:
        st.info("👈 Enter a protein name and click Analyse.")
        st.stop()

    pd_s=st.session_state.prot_data; gt=st.session_state.get("gt",{}); cv=st.session_state.get("cv",{})
    n_path=gt.get("n_path",0); tier=gt.get("tier","UNKNOWN"); dbr=gt.get("dbr")
    tc={"CRITICAL":"#FF4C4C","HIGH":"#FFA500","LOW":"#FFD700","NONE":"#888","UNKNOWN":"#4CA8FF"}.get(tier,"#888")
    prot_name=pd_s.get("protein_name","") or gt.get("protein_name","") or gene
    diseases_str=gt.get("diseases",""); role=classify_protein_role(gene,n_path)

    st.markdown(f'<h2 style="font-family:IBM Plex Mono,monospace;font-size:1.4rem;color:#f0f0f0;margin-bottom:4px">{gene} — {prot_name}</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:#777;font-size:0.82rem;margin-bottom:16px">UniProt {pd_s.get("uid","")} · {pd_s.get("length",0)} aa · Chr {gt.get("chromosome","—")} · {"GPCR" if pd_s.get("is_gpcr") else "Non-GPCR"} · {role["icon"]} {role["label"]}</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,1,1], gap="medium")

    with col1:
        st.markdown('<div class="block"><div class="label">Function</div>', unsafe_allow_html=True)
        func = pd_s.get("function","")
        if func:
            st.markdown(f'<p style="font-size:0.81rem;color:#cccccc;line-height:1.7">{func[:500]}</p>', unsafe_allow_html=True)
        else:
            st.markdown(f'<p style="font-size:0.81rem;color:#555">Function data from UniProt — enable DB enrichment to load</p>', unsafe_allow_html=True)

        st.markdown('<div class="label" style="margin-top:12px">Subcellular location</div>', unsafe_allow_html=True)
        subcel = pd_s.get("subcellular",[])
        if subcel:
            for loc in subcel[:5]:
                ico = "🔬" if "nucle" in loc.lower() else "🧬" if "membran" in loc.lower() else "⚙️" if any(x in loc.lower() for x in ("mitoch","cytopl")) else "📍"
                st.markdown(f'<div style="padding:4px 0;font-size:0.8rem;color:#dddddd;border-bottom:1px solid #0d0f18">{ico} {loc}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<p style="font-size:0.8rem;color:#444">Enable DB enrichment to load subcellular locations</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="block"><div class="label">Genomic identity</div>', unsafe_allow_html=True)
        rows_data = [("Gene",gene),("Protein",prot_name[:35] if prot_name else "—"),("UniProt",pd_s.get("uid","—")),("Chromosome",f"Chr {gt.get('chromosome','—')}"),("Length",f"{pd_s.get('length',0)} aa"),("Domains",f"{len(pd_s.get('domains',[]))} annotated"),("TM helices",str(pd_s.get("n_tm",0))),("GPCR","✓ "+pd_s.get("g_protein","—") if pd_s.get("is_gpcr") else "No"),("OMIM",pd_s.get("omim","—") or "—"),("Ensembl",pd_s.get("ensembl_id","—")[:20] or "—")]
        for lbl,val in rows_data:
            st.markdown(f'<div class="row"><span class="rl">{lbl}</span><span class="rv">{val}</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # GPCR association
        assoc = GPCR_ASSOC.get(gene.upper())
        if assoc:
            gc = assoc.get("color","#9370DB"); atype = assoc.get("type","")
            st.markdown(f"""<div class="block" style="border-color:{gc}44;margin-top:0">
              <div class="label" style="color:{gc}44;border-color:{gc}22">GPCR Association</div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:{gc};font-weight:600;margin-bottom:6px">{atype}</div>
              <p style="font-size:0.78rem;color:#aaaaaa;line-height:1.6">{assoc["mechanism"][:180]}</p>
              <div style="font-size:0.7rem;color:#666;margin-top:6px">📄 {assoc.get("paper","")}</div>
            </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f'<div class="block" style="border-color:{tc}44"><div class="label">ClinVar — Germline vs Somatic</div>', unsafe_allow_html=True)
        n_gp = len(cv.get("pathogenic",[])) + len(cv.get("likely_pathogenic",[]))
        n_som= len(cv.get("somatic",[]))
        n_vus= len(cv.get("vus",[]))
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px">
          <div class="stat"><span class="stat-n" style="color:{tc}">{n_path}</span><span class="stat-l">Germline P/LP</span></div>
          <div class="stat"><span class="stat-n" style="color:#FFA500">{n_som}</span><span class="stat-l">Somatic only</span></div>
          <div class="stat"><span class="stat-n" style="color:#555">{n_vus}</span><span class="stat-l">VUS</span></div>
          <div class="stat"><span class="stat-n" style="color:{tc}">{f"{dbr:.3f}" if dbr else "0.000"}</span><span class="stat-l">DBR</span></div>
        </div>""", unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:0.73rem;color:#aaaaaa;line-height:1.6;margin-bottom:8px">{role.get("note","")[:150]}</div>', unsafe_allow_html=True)
        if diseases_str:
            st.markdown('<div class="label">Confirmed diseases</div>', unsafe_allow_html=True)
            for d in diseases_str.split("·")[:5]:
                if d.strip(): st.markdown(f'<div style="font-size:0.75rem;color:#cccccc;padding:3px 0;border-bottom:1px solid #0d0f18">● {d.strip()}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="margin-top:8px">{paper_chip("king_2024")}{paper_chip("minikel_2021")}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ClinVar full table
    st.markdown("<br>", unsafe_allow_html=True)
    gpath_all = cv.get("pathogenic",[]) + cv.get("likely_pathogenic",[])
    if gpath_all:
        st.markdown('<div class="label">ClinVar Germline Pathogenic Variants (P/LP only)</div>', unsafe_allow_html=True)
        rows_cv=[]
        for v in gpath_all[:50]:
            aa=re.search(r'p\.([A-Za-z]{3}\d+[A-Za-z]{3}|[A-Za-z]\d+[A-Za-z=\*])',v.get("title",""))
            rows_cv.append({"Variant":v.get("title","")[:65],"AA change":aa.group(0) if aa else "—","Classification":v.get("germline","") or v.get("sig",""),"Disease":(v.get("conditions",["—"])[0] if v.get("conditions") else "—")[:50],"Stars":v.get("stars","")[:25]})
        df_cv=pd.DataFrame(rows_cv)
        def _style_cv(val):
            if "Pathogenic" in str(val) and "Likely" not in str(val): return "color:#FF4C4C;font-weight:600"
            if "Likely" in str(val): return "color:#FFA500;font-weight:600"
            return ""
        st.dataframe(df_cv.style.map(_style_cv,subset=["Classification"]),use_container_width=True,height=min(300,len(rows_cv)*40+50))
        st.caption(f"Showing {min(50,len(gpath_all))} of {len(gpath_all)} germline P/LP submissions. Somatic variants shown separately. Source: NCBI ClinVar.")

    if cv.get("somatic"):
        with st.expander(f"⚠ Somatic variants ({len(cv['somatic'])}) — cancer-acquired, NOT germline disease evidence"):
            st.markdown(f'<div class="block" style="margin-bottom:10px"><p style="font-size:0.8rem;color:#aaaaaa;line-height:1.7;margin:0">Somatic variants are mutations in individual cancer cells — NOT inherited. They do NOT prove the protein is essential for human development. A protein in COSMIC is not necessarily a valid drug target. {paper_chip("plenge_2016")}</p></div>', unsafe_allow_html=True)
            sdf=pd.DataFrame([{"Variant":v.get("title","")[:60],"Somatic classification":v.get("somatic",""),"Context":(v.get("conditions",[""])[0] if v.get("conditions") else "")[:40]} for v in cv["somatic"][:20]])
            if len(sdf)>0: st.dataframe(sdf,use_container_width=True,height=180)

    # PubMed papers
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="label">PubMed — Human Genetics Papers</div>', unsafe_allow_html=True)
    papers_pm = fetch_pubmed(gene, disease_ctx, 6)
    if papers_pm:
        c1p,c2p=st.columns(2,gap="medium")
        for i,p in enumerate(papers_pm):
            with (c1p if i%2==0 else c2p):
                st.markdown(f'<div class="block" style="margin-bottom:8px"><div style="font-size:0.8rem;font-weight:600;color:#f0f0f0;margin-bottom:3px;line-height:1.4">{p["title"]}</div><div style="font-size:0.7rem;color:#666;margin-bottom:5px">{p["journal"]} · {p["year"]}</div><a href="{p["url"]}" target="_blank" style="font-size:0.68rem;color:#4CA8FF;text-decoration:none">PubMed →</a></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<p style="font-size:0.8rem;color:#444">Loading papers for {gene}... or no disease-specific papers found.</p>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# TAB 3 — VISUAL CONTEXT
# ──────────────────────────────────────────────────────────────────────────────
with tab3:
    if "prot_data" not in st.session_state or not gene:
        st.info("👈 Enter a protein name and click Analyse.")
        st.stop()

    pd_s=st.session_state.prot_data; gt=st.session_state.get("gt",{}); cv=st.session_state.get("cv",{})
    scored=st.session_state.get("scored"); n_path=gt.get("n_path",0); tier=gt.get("tier","UNKNOWN")
    tc={"CRITICAL":"#FF4C4C","HIGH":"#FFA500","LOW":"#FFD700","NONE":"#888","UNKNOWN":"#4CA8FF"}.get(tier,"#888")
    prot_name=pd_s.get("protein_name","") or gene; chrom=gt.get("chromosome","")
    domains=pd_s.get("domains",[]); subcel=pd_s.get("subcellular",[]); is_gpcr=pd_s.get("is_gpcr",False); g_prot=pd_s.get("g_protein","")

    st.markdown(f'<h2 style="font-family:IBM Plex Mono,monospace;font-size:1.3rem;color:#f0f0f0;margin-bottom:4px">{gene} — Visual Context</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:#777;font-size:0.8rem;margin-bottom:16px">Tissue distribution · Genomic breakdown · GPCR association · Cell impact · Click-residue experiments</p>', unsafe_allow_html=True)

    v1,v2,v3,v4 = st.tabs(["🧬 Tissue & Location","📍 Genomic Breakdown","⚡ GPCR Association","🔬 Cell Impact"])

    with v1:
        st.markdown('<div class="label">Where this protein is expressed (UniProt experimental + curated)</div>', unsafe_allow_html=True)
        # Show text location always
        if gene.upper() in TISSUE_DATA:
            tdata = TISSUE_DATA[gene.upper()]
            lc={"3":"#FF4C4C","2":"#FFA500","1":"#4CA8FF","0":"#2a2d3a"}
            st.markdown('<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px">', unsafe_allow_html=True)
            for tissue,lv in sorted(tdata.items(),key=lambda x:-x[1]):
                c=["#FF4C4C","#FFA500","#4CA8FF","#333"][min(3,3-lv)]; lbl=["ABSENT","LOW","MEDIUM","HIGH"][lv]
                st.markdown(f'<div style="background:{c}22;border:1px solid {c}88;border-radius:8px;padding:6px 14px;font-size:0.78rem;color:{c};font-family:IBM Plex Mono,monospace;font-weight:600">{tissue}<br><span style="font-weight:400;font-size:0.65rem;opacity:0.7">{lbl}</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        elif pd_s.get("tissue"):
            st.markdown(f'<div class="block"><p style="font-size:0.82rem;color:#cccccc;line-height:1.7">{pd_s["tissue"]}</p></div>', unsafe_allow_html=True)

        # Chromosome location
        st.markdown(f'<div class="label">Chromosomal location</div>', unsafe_allow_html=True)
        if chrom:
            st.markdown(f'<div class="block-green"><div style="font-size:1.1rem;font-weight:700;font-family:IBM Plex Mono,monospace;color:#4CAF50;margin-bottom:4px">Chromosome {chrom}</div><div style="font-size:0.8rem;color:#888">{gene} · {pd_s.get("ensembl_id","") or "Ensembl ID pending"} · {pd_s.get("length",0)} amino acids</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="block"><div style="font-size:0.8rem;color:#555">Chromosome location not in curated database for {gene}. Enable DB enrichment and check Ensembl.</div></div>', unsafe_allow_html=True)

        # Subcellular
        if subcel:
            st.markdown('<div class="label">Subcellular locations</div>', unsafe_allow_html=True)
            for loc in subcel[:6]:
                ico="🔬" if "nucle" in loc.lower() else "🧬" if "membran" in loc.lower() else "⚙️" if any(x in loc.lower() for x in ("mitoch","cytopl")) else "📍"
                st.markdown(f'<div style="padding:6px 12px;margin-bottom:4px;background:#0d1020;border:1px solid #252840;border-radius:6px;font-size:0.8rem;color:#bbb">{ico} {loc}</div>', unsafe_allow_html=True)

        # Tissue diagram
        components.html(build_tissue_diagram(gene, pd_s.get("tissue",""), None), height=320, scrolling=False)
        st.caption(f"Source: {'Curated: UniProt + Protein Atlas' if gene.upper() in TISSUE_DATA else 'UniProt tissue specificity annotation'} · Experimental evidence only")

    with v2:
        st.markdown('<div class="label">Protein domain map and variant positions</div>', unsafe_allow_html=True)
        pv=[]; bv=[]
        for variants in cv.get("pathogenic",[]) + cv.get("likely_pathogenic",[]):
            if isinstance(variants,dict):
                pos=variants.get("pos",0)
                if pos>0: pv.append({"pos":pos})
        for variants in cv.get("benign",[]):
            if isinstance(variants,dict):
                pos=variants.get("pos",0)
                if pos>0: bv.append({"pos":pos})
        for nv in pd_s.get("natural_variants",[]):
            p=int(nv.get("pos") or 0)
            if p>0:
                (pv if nv.get("disease") else bv).append({"pos":p})

        components.html(build_genomic_diagram(gene, chrom, pd_s.get("length",0), domains, pv, bv), height=250, scrolling=False)
        st.caption(f"Domains from UniProt · Red = ClinVar pathogenic positions · Blue = benign · {len(pv)} pathogenic positions shown · Germline only")

        if domains:
            st.markdown('<div class="label" style="margin-top:12px">Domain annotations</div>', unsafe_allow_html=True)
            c1d,c2d=st.columns(2)
            dc=["#9370DB","#4CA8FF","#FFA500","#4CAF50","#FF6B9D","#00BCD4","#FF4C4C","#FFD700"]
            for i,d in enumerate(domains[:8]):
                with (c1d if i%2==0 else c2d):
                    c=dc[i%len(dc)]
                    st.markdown(f'<div style="padding:5px 10px;margin-bottom:4px;background:{c}11;border:1px solid {c}44;border-radius:5px;font-size:0.75rem"><span style="color:{c};font-weight:600">{d.get("name","")[:30]}</span><span style="color:#777;font-size:0.68rem;font-family:IBM Plex Mono,monospace;margin-left:8px">{d.get("start")}–{d.get("end")}</span></div>', unsafe_allow_html=True)

    with v3:
        pdata = get_protein_info(gene)
        gpcr_info = pdata.get('gpcr_interaction', {})
        atype_pk = gpcr_info.get('type','')
        mech_pk  = gpcr_info.get('mechanism','')
        why_pk   = pdata.get('why_mutations_major','') or pdata.get('why_mutations_minor','')
        tc2_ = '#FFA500' if 'IS A GPCR' in atype_pk else '#9370DB' if 'SCAFFOLD' in atype_pk else '#4CA8FF' if 'INDIRECT' in atype_pk else '#888'
        if atype_pk:
            st.markdown(f'<div style="display:inline-block;background:{tc2_}22;border:1px solid {tc2_};border-radius:8px;padding:6px 16px;font-family:IBM Plex Mono,monospace;font-size:0.72rem;font-weight:600;color:{tc2_};margin-bottom:12px">{atype_pk}</div>', unsafe_allow_html=True)
        if mech_pk:
            st.markdown(f'<div style="background:#0d1020;border:1px solid #252840;border-radius:8px;padding:14px 16px;margin-bottom:12px"><p style="font-size:0.82rem;color:#dddddd;line-height:1.8;margin:0">{mech_pk}</p></div>', unsafe_allow_html=True)
        if why_pk:
            label_why = 'Why mutations are major' if n_path>50 else 'Why mutations are minor — the real biology' if n_path==0 else 'Rare Mendelian — why low count matters'
            st.markdown(f'<div style="background:#0d1020;border-left:3px solid {tc};border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:12px"><div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.12em;color:{tc};margin-bottom:6px">{label_why}</div><p style="font-size:0.79rem;color:#cccccc;line-height:1.8;margin:0">{why_pk[:800]}</p></div>', unsafe_allow_html=True)
        partners_pk = gpcr_info.get('which_gpcrs', [])
        if partners_pk:
            st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.12em;color:#5a5d7a;margin-bottom:6px">GPCR partners</div>', unsafe_allow_html=True)
            st.markdown(' '.join(f'<span style="background:#0d1020;border:1px solid #252840;color:#cccccc;font-family:IBM Plex Mono,monospace;font-size:0.68rem;padding:2px 10px;border-radius:8px;margin:2px;display:inline-block">{p}</span>' for p in partners_pk[:8]), unsafe_allow_html=True)
        downstream_pk = gpcr_info.get('downstream', [])
        if downstream_pk:
            st.markdown('<br><div style="font-family:IBM Plex Mono,monospace;font-size:0.63rem;text-transform:uppercase;letter-spacing:0.12em;color:#5a5d7a;margin-bottom:6px">Downstream effects</div>', unsafe_allow_html=True)
            st.markdown(' '.join(f'<span style="background:#0a140a;border:1px solid #1a3a1a;color:#4CAF50;font-family:IBM Plex Mono,monospace;font-size:0.68rem;padding:2px 10px;border-radius:8px;margin:2px;display:inline-block">{d}</span>' for d in downstream_pk[:6]), unsafe_allow_html=True)
        components.html(build_gpcr_association_diagram(gene, g_prot, prot_name, is_gpcr), height=340, scrolling=False)
        assoc=GPCR_ASSOC.get(gene.upper(),{})
        paper_line = assoc.get('paper','') if assoc else ''
        st.caption(f'{gene} GPCR association · {paper_line[:80] if paper_line else "Source: UniProt + IUPHAR/BPS + Protellect knowledge base"}')

    with v4:
        st.markdown('<div class="label">Cell impact — what breaks when this protein is mutated</div>', unsafe_allow_html=True)
        dis4=[]
        for v in cv.get("pathogenic",[]) + cv.get("likely_pathogenic",[]):
            for c in v.get("conditions",[]):
                if c and "not provided" not in c.lower() and c not in dis4: dis4.append(c)
        # EXPANDED cell impact — full width, more height
        components.html(build_cell_impact_diagram(gene, tier, n_path, dis4[:6], subcel, is_gpcr, g_prot), height=460, scrolling=True)
        st.caption(f"Cell impact for {gene} · {n_path} ClinVar germline pathogenic variants · Germline only")
        # Real biology from protein_data
        pdata_v4 = get_protein_info(gene)
        real_bio = pdata_v4.get('real_biology','')
        pig_rel  = pdata_v4.get('piggyback_relationship',{})
        if real_bio and len(real_bio) > 100:
            st.markdown('<br>', unsafe_allow_html=True)
            st.markdown('<div class="label">What this protein actually does — full biology</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="background:#0d1020;border:1px solid #252840;border-radius:8px;padding:16px 18px;font-size:0.79rem;color:#cccccc;line-height:1.9;white-space:pre-line">{real_bio[:1200]}</div>', unsafe_allow_html=True)
        if pig_rel:
            ess = pig_rel.get('essential_partners',[])
            mech_pig = pig_rel.get('mechanism','')
            analogy  = pig_rel.get('analogy','')
            st.markdown('<br>', unsafe_allow_html=True)
            st.markdown('<div class="label" style="color:#FF4C4C44;border-color:#FF4C4C22">Piggyback relationship — essential partners carry the disease burden</div>', unsafe_allow_html=True)
            partners_str = ' '.join(f'<span style="background:#1a0808;border:1px solid #FF4C4C44;color:#FF4C4C;font-family:IBM Plex Mono,monospace;font-size:0.68rem;padding:2px 10px;border-radius:8px;margin:2px;display:inline-block">{p}</span>' for p in ess[:4])
            analogy_html = f'<div style="font-size:0.75rem;color:#777;font-style:italic;margin-top:6px">{analogy}</div>' if analogy else ''
            st.markdown(f'<div style="background:#0a0607;border:1px solid #FF4C4C33;border-radius:8px;padding:14px 16px"><p style="font-size:0.79rem;color:#dddddd;line-height:1.7;margin-bottom:8px">{mech_pig}</p>{analogy_html}<div style="margin-top:8px">Essential partners: {partners_str}</div></div>', unsafe_allow_html=True)

        # Click-to-residue experiment recommender
        # Click-to-residue experiment recommender
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="label">Experiment recommender — click a residue to get specific protocols</div>', unsafe_allow_html=True)
        gpath=cv.get("pathogenic",[])+cv.get("likely_pathogenic",[])
        if gpath:
            positions=[v.get("pos",0) for v in gpath if v.get("pos",0)>0][:20]
            selected_pos = st.selectbox("Select a pathogenic residue position from ClinVar", ["—"]+[str(p) for p in positions], key="res_sel")
            if selected_pos and selected_pos != "—":
                pos=int(selected_pos)
                variant=[v for v in gpath if v.get("pos")==pos]
                if variant:
                    v=variant[0]; sig=v.get("germline","") or v.get("sig",""); dis=v.get("conditions",["—"])[0] if v.get("conditions") else "—"
                    dom_at=""
                    for d in domains:
                        if d["start"]<=pos<=d["end"]: dom_at=d.get("name",""); break
                    st.markdown(f"""<div class="block-red">
                      <div style="font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:#FF4C4C;margin-bottom:6px">Position {pos} — {sig}</div>
                      <div style="font-size:0.82rem;color:#f0f0f0;margin-bottom:4px">{v.get("title","")[:80]}</div>
                      <div style="font-size:0.78rem;color:#aaaaaa;margin-bottom:8px">Disease: {dis} {"· Domain: "+dom_at if dom_at else ""}</div>
                      <div class="label" style="margin-top:8px">Recommended experiments for this specific residue</div>
                      <div style="font-size:0.78rem;color:#cccccc;line-height:2">
                        1. <strong>ClinVar + gnomAD (free, 1h):</strong> Confirm this exact variant · check population frequency · verify dominant vs recessive<br>
                        2. <strong>Thermal shift DSF (2-3 days, ~$300):</strong> Express WT + Pos{pos} mutant · expect ΔTm of {'6-12°C' if sig and 'Pathogenic' in sig and 'Likely' not in sig else '3-8°C'}<br>
                        3. <strong>ITC binding assay (1-2 weeks, ~$2,000):</strong> Measure Kd change at {'domain: '+dom_at if dom_at else 'this position'} · ITC is robust, no false positives (Sujay Ithychanda, Cleveland Clinic)<br>
                        4. <strong>{'GPCR binding assay' if is_gpcr or assoc else 'Functional assay'}:</strong> {'Test Gi/o or Gq/11 signalling with Pos'+str(pos)+' mutant vs WT' if is_gpcr else 'Measure native protein activity with Pos'+str(pos)+' mutant'}<br>
                        5. <strong>Patient cell study:</strong> Obtain fibroblasts/iPSCs from known Pos{pos} carrier · validate in human-derived material
                      </div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown(paper_chip("king_2024")+paper_chip("minikel_2021"), unsafe_allow_html=True)
        elif scored is not None:
            pc_col="priority_final" if "priority_final" in scored.columns else "priority"
            top3=scored[scored[pc_col]=="HIGH"].head(3)
            st.markdown('<div class="label">Top HIGH residues from your assay — select one for experiment plan</div>', unsafe_allow_html=True)
            if len(top3)>0:
                selected_r=st.selectbox("Select residue",["—"]+[f"Pos{int(r['residue_position'])} (score {round(float(r['normalized_score']),3)})" for _,r in top3.iterrows()],key="res_sel2")
                if selected_r and selected_r!="—":
                    st.markdown(f'<div class="block"><div style="font-family:IBM Plex Mono,monospace;font-size:0.7rem;color:#FF4C4C;margin-bottom:6px">{selected_r}</div><p style="font-size:0.78rem;color:#cccccc;line-height:1.8">1. DSF thermal shift · 2. ITC binding · 3. ClinVar position check · 4. Functional assay in relevant cell line</p></div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# TAB 4 — THERAPY
# ──────────────────────────────────────────────────────────────────────────────
with tab4:
    if "prot_data" not in st.session_state or not gene:
        st.info("👈 Enter a protein name and click Analyse.")
        st.stop()
    import hypothesis_lab
    hypothesis_lab.render()

# ──────────────────────────────────────────────────────────────────────────────
# TAB 5 — DEEP DIVE
# ──────────────────────────────────────────────────────────────────────────────
with tab5:
    import protein_deep_dive
    protein_deep_dive.render()

# ──────────────────────────────────────────────────────────────────────────────
# TAB 6 — DISEASE EXPLORER
# ──────────────────────────────────────────────────────────────────────────────
with tab6:
    import disease_explorer
    disease_explorer.render()
