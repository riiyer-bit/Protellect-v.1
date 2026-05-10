import streamlit as st, requests, re

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
