import streamlit as st
import requests
import json
import re
from datetime import datetime

st.set_page_config(page_title="BioIntel — Biology Intelligence Browser",
                   page_icon="🔬", layout="wide", initial_sidebar_state="expanded")

# ═══════════════════════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Inter:wght@300;400;500;600&display=swap');
*{font-family:'Inter',sans-serif}
code,pre,.mono{font-family:'JetBrains Mono',monospace}
[data-testid="stSidebar"]{background:#040c14!important;border-right:1px solid #0d2545}
[data-testid="stSidebar"] *{color:#d0e8ff}
.block-container{padding:1.5rem 2rem!important;max-width:1400px}
div[data-testid="metric-container"]{background:#070d1a;border:1px solid #0d2545;border-radius:10px;padding:.7rem}
div[data-testid="metric-container"] label{color:#5a8090!important;font-size:.75rem!important}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{color:#00e5ff!important;font-size:1.4rem!important}
.stTabs [data-baseweb="tab-list"]{gap:4px;background:#040c14;border-radius:10px;padding:4px}
.stTabs [data-baseweb="tab"]{background:transparent;color:#5a8090;border-radius:8px;font-size:.78rem;padding:.3rem .7rem}
.stTabs [aria-selected="true"]{background:#0d2545!important;color:#00e5ff!important}
.stButton>button{background:transparent;border:1px solid #0d2545;color:#d0e8ff;font-size:.8rem;border-radius:8px;padding:.3rem .8rem}
.stButton>button:hover{border-color:#00e5ff;color:#00e5ff}
.stTextInput>div>div>input,.stSelectbox>div>div{background:#040c14!important;border:1px solid #0d2545!important;color:#d0e8ff!important;border-radius:8px!important;font-size:.85rem!important}
h1,h2,h3{color:#d0e8ff!important}
a{color:#00e5ff!important;text-decoration:none}
a:hover{text-decoration:underline}
hr{border-color:#0d2545!important}
.stExpander{border:1px solid #0d2545!important;border-radius:10px!important;background:#040c14!important}
.stExpander [data-testid="stExpanderToggleIcon"]{color:#5a8090}
</style>""", unsafe_allow_html=True)

def card(html): return st.markdown(f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:12px;padding:1rem 1.2rem;margin-bottom:.5rem'>{html}</div>", unsafe_allow_html=True)
def sh(icon, title, color="#00e5ff"): st.markdown(f"<div style='display:flex;align-items:center;gap:8px;margin:.8rem 0 .4rem'><span style='font-size:1rem'>{icon}</span><span style='color:{color};font-weight:600;font-size:1rem'>{title}</span></div>", unsafe_allow_html=True)
def badge(text, color="#00e5ff"): return f"<span style='background:{color}22;color:{color};font-size:.7rem;padding:2px 8px;border-radius:8px;border:1px solid {color}44;font-weight:500'>{text}</span>"
def src_link(label, url): return f"<a href='{url}' target='_blank' style='display:inline-flex;align-items:center;gap:3px;font-size:.72rem;color:#00e5ff;background:#00e5ff11;border:1px solid #00e5ff33;border-radius:6px;padding:2px 8px;margin:2px;text-decoration:none'>{label} ↗</a>"
def pill(text, color="#3a5a7a"): return f"<span style='display:inline-block;background:{color}22;border:1px solid {color};color:{color};font-size:.72rem;padding:2px 10px;border-radius:10px;margin:2px'>{text}</span>"
def tier_badge(t):
    colors={"Tier 1 — RCT":"#00c896","Tier 2 — Cohort":"#4a90d9","Tier 3 — Functional":"#ff8c42","Tier 4 — Structural":"#a855f7","Tier 5 — Animal":"#ffd60a","Tier 6 — Computational":"#5a8090","Tier 7 — Case report":"#3a5a7a","Tier 8 — Review":"#2a4060","Tier 9 — Preprint":"#ff2d55"}
    c=colors.get(t,"#3a5a7a"); return badge(t,c)

# ═══════════════════════════════════════════════════════════════════════════════
# API HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
ESEARCH="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_pubmed(query, n=6):
    try:
        r=requests.get(ESEARCH,params={"db":"pubmed","term":query,"retmax":n,"retmode":"json","sort":"relevance"},timeout=10)
        ids=r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return []
        r2=requests.get(ESUMMARY,params={"db":"pubmed","id":",".join(ids),"retmode":"json"},timeout=10)
        result=r2.json().get("result",{})
        papers=[]
        for uid in result.get("uids",[]):
            e=result.get(uid,{})
            auth=", ".join(a.get("name","") for a in e.get("authors",[])[:3])
            if len(e.get("authors",[]))>3: auth+=" et al."
            pt=[p.get("value","").lower() for p in e.get("pubtype",[])]
            tier="Tier 8 — Review" if "review" in pt else "Tier 2 — Cohort" if "clinical trial" in pt or "randomized" in " ".join(pt) else "Tier 3 — Functional"
            papers.append({"pmid":uid,"title":e.get("title",""),"authors":auth,"journal":e.get("source",""),"year":e.get("pubdate","")[:4],"url":f"https://pubmed.ncbi.nlm.nih.gov/{uid}/","tier":tier})
        return papers
    except: return []

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_uniprot(gene):
    try:
        r=requests.get(f"https://rest.uniprot.org/uniprotkb/search",params={"query":f"{gene} AND organism_id:9606","format":"json","size":1},timeout=10)
        d=r.json().get("results",[])
        if not d: return {}
        p=d[0]
        return {"name":p.get("proteinDescription",{}).get("recommendedName",{}).get("fullName",{}).get("value",""),"function":" ".join(c.get("value","") for c in p.get("comments",[]) if c.get("commentType")=="FUNCTION")[:300],"uid":p.get("primaryAccession",""),"gene":gene}
    except: return {}

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_string(gene, n=5):
    try:
        r=requests.get("https://string-db.org/api/json/network",params={"identifiers":gene,"species":9606,"required_score":700,"limit":n},timeout=10)
        data=r.json()
        partners=[]
        for item in data[:n]:
            p=item.get("preferredName_B","") if item.get("preferredName_A","").upper()==gene.upper() else item.get("preferredName_A","")
            partners.append({"partner":p,"score":round(item.get("score",0),2)})
        return partners
    except: return []

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_opentargets(ensembl_id):
    try:
        q="""query($id:String!){target(ensemblId:$id){knownDrugs{rows{drug{name}phase approvedIndications}}tractability{label modality}}}"""
        r=requests.post("https://api.platform.opentargets.org/api/v4/graphql",json={"query":q,"variables":{"id":ensembl_id}},timeout=10)
        t=r.json().get("data",{}).get("target",{})
        return {"drugs":[row.get("drug",{}).get("name","") for row in (t.get("knownDrugs",{}) or {}).get("rows",[])[:5]],"tractability":[x.get("label","") for x in (t.get("tractability") or [])[:3]]}
    except: return {}

@st.cache_data(ttl=3600, show_spinner=False)
def gene_to_ensembl(gene):
    try:
        r=requests.get(f"https://mygene.info/v3/query?q={gene}&species=human&fields=ensembl.gene",timeout=8)
        hits=r.json().get("hits",[])
        if not hits: return ""
        e=hits[0].get("ensembl",{})
        if isinstance(e,list): return e[0].get("gene","")
        return e.get("gene","")
    except: return ""

def classify_paper(title,abstract=""):
    t=(title+" "+abstract).lower()
    if any(x in t for x in ["randomised","randomized","rct","placebo-controlled"]): return "Tier 1 — RCT"
    if any(x in t for x in ["cohort","prospective","retrospective","patients","case-control"]): return "Tier 2 — Cohort"
    if any(x in t for x in ["crispr","knock-in","knock-out","functional assay","western blot","luciferase"]): return "Tier 3 — Functional"
    if any(x in t for x in ["crystal structure","cryo-em","nmr","x-ray","alphafold","spr","itc"]): return "Tier 4 — Structural"
    if any(x in t for x in ["mouse model","zebrafish","drosophila","xenograft","in vivo","murine"]): return "Tier 5 — Animal"
    if any(x in t for x in ["computational","in silico","machine learning","deep learning","algorithm"]): return "Tier 6 — Computational"
    if any(x in t for x in ["case report","case series"]): return "Tier 7 — Case report"
    if any(x in t for x in ["review","meta-analysis","systematic review"]): return "Tier 8 — Review"
    return "Tier 9 — Preprint"

# ═══════════════════════════════════════════════════════════════════════════════
# DOMAIN DATABASE
# ═══════════════════════════════════════════════════════════════════════════════
DOMAINS = {
    "🦠 Microbiome": {
        "icon":"🦠","color":"#00c896",
        "description":"Gut, oral, skin, vaginal — host-microbiome interactions, dysbiosis, therapeutic targets",
        "pubmed_queries":["gut microbiome disease 2023 2024","microbiota therapeutic interventions","16S metagenomics clinical"],
        "key_genes":["FXR","TLR4","NLRP3","AhR","IL-18","GPR41","GPR43","TGR5","IL-10","TNF"],
        "databases":[("Human Microbiome Project","https://hmpdacc.org","Free","Reference body-site microbiome data"),("MGnify (EBI)","https://www.ebi.ac.uk/metagenomics","Free/API","Metagenome analysis pipeline + public studies"),("SILVA rRNA","https://www.arb-silva.de","Free","16S/18S taxonomy reference"),("gutMDisorder","http://bio-annotation.cn/gutMDisorder","Free","Gut microbiome–disease associations"),("MicrobiomeDB","https://microbiomedb.org","Free","Integrated microbiome study data"),("NCBI SRA","https://www.ncbi.nlm.nih.gov/sra","Free","Raw sequencing data — 16S and shotgun")],
        "tools":[("QIIME2","https://qiime2.org"),("MetaPhlAn4","https://github.com/biobakery/MetaPhlAn"),("Kraken2","https://ccb.jhu.edu/software/kraken2"),("HUMAnN3","https://huttenhower.sph.harvard.edu/humann")],
        "key_facts":["~38 trillion bacterial cells in human body","1,000+ species colonise the gut","Short-chain fatty acids (SCFAs) produced by Firmicutes regulate colonic health","Akkermansia muciniphila abundance inversely correlates with obesity","Faecalibacterium prausnitzii is the most abundant butyrate producer","Dysbiosis associated with IBD, T2D, autism, depression, CVD"]
    },
    "⚗️ Biotech": {
        "icon":"⚗️","color":"#4a90d9",
        "description":"Recombinant proteins, gene editing, synthetic biology, biomanufacturing, fermentation",
        "pubmed_queries":["CRISPR base editing 2023","gene therapy AAV clinical","synthetic biology applications"],
        "key_genes":["Cas9","Cas12a","SpCas9","SaCas9","ABE8e","PE2","AAV2","LNP","mRNA"],
        "databases":[("Addgene","https://www.addgene.org","Free","250K+ plasmid constructs"),("NCBI GenBank","https://www.ncbi.nlm.nih.gov/genbank","Free","Nucleotide sequences — reference genomes"),("iGEM Registry","https://parts.igem.org","Free","Standardised biological parts (BioBricks)"),("BRENDA","https://www.brenda-enzymes.org","Free/API","Enzyme kinetics + substrate specificity"),("ExPASy","https://www.expasy.org","Free/API","Bioinformatics portal — UniProt, PROSITE, HAMAP"),("SnapGene","https://www.snapgene.com","Commercial","Plasmid viewer + molecular cloning design")],
        "tools":[("Benchling","https://www.benchling.com"),("CRISPOR","http://crispor.tefor.net"),("Primer3","https://primer3.ut.ee"),("SnapGene Viewer","https://www.snapgene.com/snapgene-viewer")],
        "key_facts":["Prime editing enables precise edits without DSBs","Base editing: C→T (CBE) and A→G (ABE) without cuts","AAV gene therapy approved for SMA (Zolgensma), haemophilia A/B","mRNA platform enabled COVID-19 vaccines in <12 months","CHO cells produce >70% of approved biologic drugs","LNP delivery enables systemic siRNA/mRNA therapeutics"]
    },
    "🧬 Proteins": {
        "icon":"🧬","color":"#a855f7",
        "description":"Structure, function, PTMs, interaction networks, drug targets, AlphaFold, AlphaMissense",
        "pubmed_queries":["AlphaFold protein structure 2023","cryo-EM structure determination","protein-protein interaction drug"],
        "key_genes":["TP53","BRCA1","FLNA","HSP90","MDM2","KRAS","EGFR","VEGFR","mTOR","AKT"],
        "databases":[("UniProt / Swiss-Prot","https://www.uniprot.org","Free/API","Gold-standard curated protein database"),("RCSB PDB","https://www.rcsb.org","Free","200K+ experimental structures"),("AlphaFold DB","https://alphafold.ebi.ac.uk","Free/API","DeepMind structure predictions for all human proteins"),("STRING DB","https://string-db.org","Free/API","Protein-protein interaction networks"),("PhosphoSitePlus","https://www.phosphosite.org","Free","Post-translational modifications — curated"),("AlphaMissense","https://alphamissense.hegelab.org","Free/API","Per-residue pathogenicity predictions")],
        "tools":[("Mol* Viewer","https://molstar.org"),("ChimeraX","https://www.cgl.ucsf.edu/chimerax"),("PyMOL","https://pymol.org"),("RoseTTAFold","https://robetta.bakerlab.org")],
        "key_facts":["AlphaFold2 predicted structures for 200M+ proteins at near-experimental accuracy","AlphaMissense scored all possible single amino acid substitutions in the human proteome","PhosphoSite Ser2152 on FLNA is the highest peak — conformationally gated (not background noise)","Only phospho sites whose mutation causes human disease are validated signals","STRING DB has >2 billion interactions across 14,000 organisms","Cryo-EM now routinely achieves sub-2Å resolution for soluble proteins"]
    },
    "🔬 Mol Cell Bio": {
        "icon":"🔬","color":"#ffd60a",
        "description":"Gene regulation, chromatin remodelling, signalling cascades, cell cycle, organelles",
        "pubmed_queries":["single cell RNA sequencing cell atlas","CRISPR screen gene regulation","chromatin accessibility ATAC"],
        "key_genes":["MYC","RB1","CDKN2A","APC","PIK3CA","MAPK1","NFkB1","CTNNB1","TP53","STAT3"],
        "databases":[("ENCODE","https://www.encodeproject.org","Free","Regulatory elements — ChIP-seq, ATAC-seq, RNA-seq"),("GTEx","https://gtexportal.org","Free/API","Tissue-specific gene expression — 54 human tissues"),("Reactome","https://reactome.org","Free/API","Curated biological pathways"),("JASPAR","https://jaspar.genereg.net","Free","Transcription factor binding motifs"),("OMIM","https://www.omim.org","Free","Mendelian disease gene catalogue"),("GeneCards","https://www.genecards.org","Free","Gene-centric summary — disease, expression, variants")],
        "tools":[("Ensembl","https://www.ensembl.org"),("UCSC Genome Browser","https://genome.ucsc.edu"),("IGV","https://igv.org"),("Galaxy","https://usegalaxy.org")],
        "key_facts":["98.5% of human DNA is non-coding — much is regulatory","Wnt/β-catenin is dysregulated in >80% of colorectal cancers","PI3K/AKT/mTOR is the most frequently mutated pathway in cancer","CRISPR interference (CRISPRi) allows gene suppression without cutting DNA","Single-cell RNA-seq can profile >10,000 cells per experiment","ENCODE project identified 1.2M cis-regulatory elements in the human genome"]
    },
    "🌿 Taxonomy": {
        "icon":"🌿","color":"#00c896",
        "description":"Species classification, phylogenetics, evolutionary biology, DNA barcoding, biodiversity",
        "pubmed_queries":["phylogenomics evolution 2023","species discovery metagenomics","biodiversity loss extinction"],
        "key_genes":["COI (barcode)","16S rRNA","18S rRNA","rbcL","ITS","matK","cytb","ND5"],
        "databases":[("NCBI Taxonomy","https://www.ncbi.nlm.nih.gov/taxonomy","Free/API","Authoritative species taxonomy + lineage"),("GBIF","https://www.gbif.org","Free/API","2 billion+ species occurrence records"),("BOLD Systems","https://www.boldsystems.org","Free/API","DNA barcoding — species ID via COI gene"),("Tree of Life","https://tolweb.org","Free","Phylogenetic tree of all life"),("SILVA","https://www.arb-silva.de","Free","rRNA taxonomy reference — 16S/18S/23S"),("iNaturalist","https://www.inaturalist.org","Free/API","Citizen science — 300M+ observations")],
        "tools":[("TimeTree","https://timetree.org"),("IQ-TREE","http://www.iqtree.org"),("MAFFT","https://mafft.cbrc.jp/alignment/server"),("RAxML","https://cme.h-its.org/exelixis/web/software/raxml")],
        "key_facts":["~8.7M estimated eukaryotic species on Earth, ~2.5M formally described","~15,000 new species described per year","6th mass extinction: species loss 100–1,000× background rate","Microbes represent >99% of Earth's biomass","The tree of life has >100 bacterial phyla, most not yet cultured","COI barcoding can ID most animal species from tissue or environmental DNA"]
    },
    "🎗️ Cancer": {
        "icon":"🎗️","color":"#ff2d55",
        "description":"Oncogenes, tumour suppressors, somatic mutations, cancer genomics, immunotherapy, liquid biopsy",
        "pubmed_queries":["KRAS G12C inhibitor clinical trial 2023","CAR T cell therapy 2023","tumour mutational burden immunotherapy"],
        "key_genes":["KRAS","TP53","BRCA1","BRCA2","CDKN2A","PIK3CA","BRAF","EGFR","HER2","PD-L1"],
        "databases":[("TCGA","https://www.cancer.gov/tcga","Free","Somatic mutations + expression — 33 cancer types"),("cBioPortal","https://www.cbioportal.org","Free/API","Cancer genomics — TCGA + ICGC cohorts"),("COSMIC","https://cancer.sanger.ac.uk/cosmic","Free/API","Catalogue of somatic mutations in cancer"),("OncoKB","https://www.oncokb.org","Free/API","Actionable variants + drug-level evidence"),("DepMap","https://depmap.org","Free","Cancer dependency map — CRISPR screens 900+ lines"),("ClinVar","https://www.ncbi.nlm.nih.gov/clinvar","Free/API","Germline cancer susceptibility variants")],
        "tools":[("IGV","https://igv.org"),("Oncotator","https://portals.broadinstitute.org/oncotator"),("MutSigCV","https://software.broadinstitute.org/cancer/cga/mutsig"),("ANNOVAR","https://annovar.openbioinformatics.org")],
        "key_facts":["19.3M new cancer cases globally per year (2020)","KRAS G12C inhibitors (sotorasib, adagrasib) — first direct KRAS targeting","Tumour mutational burden (TMB) predicts response to checkpoint inhibitors","CAR-T cell therapies achieve >80% complete remission in r/r B-ALL","Liquid biopsy: ctDNA detectable 1–2 years before clinical diagnosis","Founder mutations: earliest somatic events are the primary therapeutic targets"]
    },
    "❤️ Cardiology": {
        "icon":"❤️","color":"#ff8c42",
        "description":"Cardiac genetics, arrhythmia, heart failure, GPCR-Filamin-actin axis, TMAO rattling receptor",
        "pubmed_queries":["cardiac channelopathy genetics 2023","heart failure GPCR beta blocker","arrhythmia genetic variant mechanism"],
        "key_genes":["KCNQ1","SCN5A","MYH7","LMNA","ADRB1","ADRB2","AGTR1","FLNA","FLNC","HCN4"],
        "databases":[("ClinVar — Cardiac Panel","https://www.ncbi.nlm.nih.gov/clinvar","Free/API","P/LP variants in cardiac genes"),("ClinGen","https://clinicalgenome.org","Free","Gene-disease validity — cardiac panels"),("GPCRdb","https://gpcrdb.org","Free","GPCR H8 helix conservation — FBM motifs"),("PhosphoSite FLNA","https://www.phosphosite.org/proteinAction.action?id=2546&showAllSites=true","Free","FLNA Ser2152 — highest phospho peak"),("gnomAD","https://gnomad.broadinstitute.org","Free/API","Population variant frequencies — pLI constraint"),("OMIM Cardiology","https://www.omim.org","Free","Heritable cardiac conditions catalogue")],
        "tools":[("Ioannidis VarSome","https://varsome.com"),("Franklin by Genoox","https://franklin.genoox.com"),("SpliceAI","https://spliceailookup.broadinstitute.org")],
        "key_facts":["18.6M CVD deaths per year — #1 cause of death globally","TMAO (gut microbiome metabolite) → GPCR rattling → H8-Filamin decoupling → arrhythmia","Filamin A Ser2152-P is more receptor-proximal than calcium, IP3, or beta-arrestin","KCNQ1 has 600+ P/LP ClinVar variants — the most of any arrhythmia gene","ARRB1/ARRB2 double KO mice viable — not primary disease drivers","Beta-blockers work via ADRB1/ADRB2 — the GPCR, not the arrestin, is the target","Arrhythmia literature biased toward Golgi/hERG — cardiac GPCR-Filamin axis understudied"],
        "insight":"KEY INSIGHT: The cardiac GPCR → Filamin A Ser2152 → actin cytoskeleton axis is a mechanistic explanation for arrhythmia that bypasses the indirect calcium/IP3 cascade. TMAO binding causes receptor rattling (rapid conformational transitions) that disrupts H8 helix dislodgement and Filamin coupling. This IP position is unoccupied."
    },
    "🔧 Biomedical Devices": {
        "icon":"🔧","color":"#5a8090",
        "description":"Implants, diagnostics, wearables, biosensors, neural interfaces, organ-on-chip, regulatory",
        "pubmed_queries":["biomedical device clinical trial 2023","neural interface brain computer","wearable biosensor continuous monitoring"],
        "key_genes":["Piezo1","CFTR","SCN1A","TRPV1","KCNA1"],
        "databases":[("FDA 510(k)","https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm","Free","Premarket notifications — Class II device clearances"),("FDA PMA","https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpma/pma.cfm","Free","Premarket approvals — Class III high-risk devices"),("MAUDE","https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfmaude/search.cfm","Free","Adverse event reports — medical devices"),("ClinicalTrials.gov","https://clinicaltrials.gov","Free/API","Active device trials — all phases"),("IEEE Xplore","https://ieeexplore.ieee.org","Subscription","Biomedical engineering literature"),("ISO 10993 Standards","https://www.iso.org/standard/68936.html","Paid","Biocompatibility testing standards")],
        "tools":[("FDA eCFR","https://www.ecfr.gov/current/title-21"),("Ansys (FEA simulation)","https://www.ansys.com"),("COMSOL","https://www.comsol.com")],
        "key_facts":["Global medical device market: $612B (2023), growing 5.5% CAGR","AI-enabled devices require FDA's Predetermined Change Control Plan (PCCP)","Organ-on-chip can model disease microenvironments with patient-derived cells","BCI (Neuralink, Synchron) entering human trials for paralysis","Continuous glucose monitors (CGM) now achieve 14-day accuracy <10% MARD","Biodegradable implants (Mg, Fe alloys) eliminate revision surgery need","Wearables: ECG patch (AliveCor), SpO2, PPG, EDA, skin temperature now real-time"]
    },
    "📡 GPCRs": {
        "icon":"📡","color":"#00e5ff",
        "description":"G protein-coupled receptors — H8 FBM, Filamin assay, biased agonism, drug targets, ARRB evidence gap",
        "pubmed_queries":["GPCR structure drug design 2023","biased agonism beta-arrestin 2023","GPCR Filamin cytoskeleton"],
        "key_genes":["ADRB1","ADRB2","AGTR1","MAS1","CHRM2","ADRA1D","DRD2","HTR1A","CXCR4","CCR5"],
        "databases":[("GPCRdb","https://gpcrdb.org","Free","Structure-based alignments, H8 FBM conservation, mutation data"),("IUPHAR/BPS","https://www.guidetopharmacology.org","Free","Curated GPCR pharmacology + approved drugs"),("ChEMBL","https://www.ebi.ac.uk/chembl","Free/API","GPCR-ligand bioactivity — IC50, Ki, EC50"),("PhosphoSite FLNA","https://www.phosphosite.org/proteinAction.action?id=2546","Free","FLNA Ser2152-P — receptor-proximal readout"),("PRESTO-Tango","https://prestotango.com","Free","GPCR activation assay screening data"),("RCSB PDB","https://www.rcsb.org","Free","GPCR crystal and cryo-EM structures")],
        "tools":[("GPCRdb segment viewer","https://gpcrdb.org/protein/adrb2_human/"),("Maestro GPCR prep","https://www.schrodinger.com"),("AlphaFold GPCR","https://alphafold.ebi.ac.uk")],
        "key_facts":["~800 human GPCRs — 4% of the genome","~34% of all FDA-approved drugs target GPCRs","H8 helix dislodgement upon agonist binding → Filamin Ig21 binding → PKA phosphorylates Ser2152","FBM anchors: Phe (hydrophobic, inward), Arg (hydrophilic, outward), Leu (hydrophobic, inward)","~300 Class A rhodopsin GPCRs carry the H8 FBM motif (GPCRdb)","FLNA Ser2152-P is more proximal than cAMP (2-4 steps via ryanodine receptors)","ARRB2 KO mice are viable: beta-arrestin is NOT an independent disease driver","Biased agonism: G-protein vs arrestin pathway selectivity in therapeutic design","TMAO causes GPCR rattling → disrupts H8-Filamin axis → cardiac arrhythmia"],
        "insight":"PROTELLECT IP: Filamin A Ser2152 phosphorylation is a proprietary GPCR activation assay. H8 helix dislodgement is the mechanistic signature of receptor activation — more proximal than cAMP, IP3, or beta-arrestin. ~300 Class A GPCRs carry the H8 FBM. PhosphoSite confirms Ser2152 as the only non-noise FLNA phosphorylation site."
    },
    "🔑 RTKs / Kinases": {
        "icon":"🔑","color":"#ff8c42",
        "description":"Receptor tyrosine kinases, downstream MAPK/PI3K, kinase inhibitors, resistance mechanisms",
        "pubmed_queries":["kinase inhibitor resistance mechanism 2023","KRAS EGFR targeted therapy 2023","KINOMEscan selectivity profiling"],
        "key_genes":["EGFR","HER2","VEGFR2","PDGFRA","ALK","MET","FGFR1","KIT","RET","BRAF"],
        "databases":[("KinHub / KinBase","http://www.kinhub.org","Free","Complete human kinome — Manning classification"),("KLIFS","https://klifs.net","Free","Kinase-ligand interaction fingerprints + structures"),("ChEMBL","https://www.ebi.ac.uk/chembl","Free/API","Kinase inhibitor bioactivity data — IC50, selectivity"),("DepMap","https://depmap.org","Free","Kinase dependency — CRISPR screens 900+ cancer lines"),("PhosphoELM","http://phospho.elm.eu.org","Free","Experimentally validated phosphorylation sites"),("cBioPortal","https://www.cbioportal.org","Free/API","Kinase mutation frequencies across cancer types")],
        "tools":[("KINOMEscan (Eurofins DiscoverX)","https://www.discoverx.com"),("Kinase.com","http://kinase.com"),("ChEMBL Kinase SARfari","https://www.ebi.ac.uk/chembl/sarfari/kinasesarfari")],
        "key_facts":["90 human receptor tyrosine kinases; 580+ total kinases (kinome)","80+ FDA-approved kinase inhibitor drugs","EGFR T790M gatekeeper mutation drives osimertinib-resistant NSCLC","KRAS was 'undruggable' until AMG 510 (sotorasib) in 2021","KINOMEscan screens 468 kinases simultaneously at 1µM — selectivity before cellular work","S-score <0.1 at 1µM = highly selective kinase inhibitor","Covalent inhibitors (osimertinib, afatinib) achieve irreversible target engagement","Kinase domain mutations cluster in ATP-binding hinge, DFG motif, P-loop"]
    },
    "📚 Literature Compare": {
        "icon":"📚","color":"#ffd60a",
        "description":"Side-by-side evidence comparison — study design, evidence tier, genetic validation, mechanistic depth",
        "pubmed_queries":["systematic review methodology evidence quality","clinical trial design randomisation"],
        "key_genes":[],"databases":[],"tools":[],"key_facts":[]
    },
    "💊 Pharma": {
        "icon":"💊","color":"#a855f7",
        "description":"Drug pipeline, approval status, mechanism of action, target classes, market data, patent landscape",
        "pubmed_queries":["FDA drug approval 2023 2024","novel mechanism of action drug","antibody drug conjugate clinical"],
        "key_genes":["GLP1R","PCSK9","VEGFA","PD1","CTLA4","HER2","CD19","BCMA","EGFR","IL6"],
        "databases":[("DrugBank","https://go.drugbank.com","Free/API","Comprehensive drug-target-pathway data"),("ChEMBL","https://www.ebi.ac.uk/chembl","Free/API","Bioactivity — IC50, EC50, Ki for all drug classes"),("DGIdb","https://www.dgidb.org","Free/API","Drug-gene interaction database"),("ClinicalTrials.gov","https://clinicaltrials.gov","Free/API","54,000+ active trials — phase, status, endpoints"),("FDA Drugs@FDA","https://www.accessdata.fda.gov/scripts/cder/daf","Free","Approval history + prescribing labels"),("OpenTargets","https://platform.opentargets.org","Free/API","Target-disease evidence + tractability + drug pipeline")],
        "tools":[("PharmGKB","https://www.pharmgkb.org"),("ADMET Predictor","https://www.simulations-plus.com"),("pkCSM","https://biosig.lab.uq.edu.au/pkcsm")],
        "key_facts":["Global pharma market: $1.57 trillion (2023)","7,000+ drugs in active clinical development worldwide","Average drug development: 10–15 years, $2.6B cost to approval","GLP-1 receptor agonists (semaglutide, tirzepatide) reshaping obesity treatment","ADCs (antibody-drug conjugates): 14 FDA approvals — fastest growing modality","AI-designed drugs: first Phase 2 trial results expected 2024–2025","~50% of drugs act on GPCRs, enzymes, or nuclear receptors","PROTAC degraders: 3 in Phase 2/3 — first modality to destroy proteins not just inhibit"]
    }
}

DRUG_PIPELINE = [
    ("Semaglutide (Ozempic/Wegovy)","GLP-1R agonist","T2D, Obesity","Approved","Novo Nordisk"),
    ("Tirzepatide (Mounjaro/Zepbound)","GIP/GLP-1R dual agonist","T2D, Obesity","Approved","Eli Lilly"),
    ("Lecanemab (Leqembi)","Anti-amyloid-β mAb","Alzheimer's","Approved","Eisai/BioGen"),
    ("Nirsevimab (Beyfortus)","Anti-RSV F mAb","RSV prophylaxis (infants)","Approved","AstraZeneca/Sanofi"),
    ("Futibatinib (Lytgobi)","FGFR1-4 inhibitor","Cholangiocarcinoma","Approved","Taiho"),
    ("Sotorasib (Lumakras)","KRAS G12C covalent inhibitor","NSCLC (KRAS G12C+)","Approved","Amgen"),
    ("Donanemab","Anti-amyloid-β mAb","Alzheimer's (early)","Phase 3","Eli Lilly"),
    ("Olpasiran","siRNA — Lp(a) knockdown","Cardiovascular risk","Phase 3","Amgen"),
    ("Milvexian","Factor XIa inhibitor","Thrombosis (oral)","Phase 3","BMS/Janssen"),
    ("Imetelstat","Telomerase inhibitor","MDS, myelofibrosis","Phase 3","Geron"),
    ("ARV-471","PROTAC — ERα degrader","ER+ breast cancer","Phase 3","Arvinas/Pfizer"),
    ("Clesrovimab","Anti-RSV mAb","RSV prophylaxis","Phase 3","Merck"),
    ("NovaBay NovaBay-100","HBV core assembly inhibitor","Chronic HBV","Phase 2","NovaBay"),
    ("KY1005","Anti-OX40L mAb","Atopic dermatitis","Phase 2","Kymab/Sanofi"),
]

GPCR_STUDY_PROTOCOL = [
    ("Step 1","Confirm surface expression","Transfect SNAP/CLIP-tagged receptor into HEK293T. SNAP-Surface stain (NEB) + confocal — confirm plasma membrane localisation. Dose-response with known agonist. Do NOT proceed until surface expression is confirmed.","#00e5ff"),
    ("Step 2","G-protein coupling (cAMP HTRF)","Gs: measure cAMP (HTRF, Cisbio). Gi: measure GTPγS binding or cAMP inhibition after forskolin pre-stimulation. Primary pharmacological efficacy readout. Compare WT vs each ClinVar P/LP variant.","#00c896"),
    ("Step 3","Filamin A Ser2152-P — receptor-proximal assay (PRIMARY)","Stimulate with agonist → whole-cell lysis → anti-Filamin A IP → pSer2152 western blot (Cell Signaling anti-pS2152). H8 dislodgement is the mechanistic signature of GPCR activation. More proximal than cAMP, IP3, or beta-arrestin. This is the proprietary readout.","#a855f7"),
    ("Step 4","β-arrestin BRET — SECONDARY only","RLuc8-tagged receptor + Venus-β-arrestin2. Use ONLY to characterise biased agonism — NOT as primary disease readout. ARRB2 has no confirmed Mendelian disease variants (KO mice viable). Beta-arrestin codes are kinase noise without disease variant evidence.","#ff8c42"),
    ("Step 5","Receptor internalisation","SNAP-surface before/after agonist stimulation. Measure % receptor lost from surface. Variants in TM bundle or ECLs may alter internalisation independent of G-protein coupling — different biology, different drug target.","#ffd60a"),
    ("Step 6","Variant functional panel","For each ClinVar P/LP variant: run Steps 2 + 3 in parallel. Variant kills cAMP but not Filamin-P = G-protein defect. Variant kills Filamin-P but not cAMP = cytoskeletal decoupling. Different readout, different mechanism, different target.","#ff2d55"),
    ("Step 7 (cardiac only)","TMAO rattling assay","Add TMAO (5–50µM) to cells expressing a cardiac GPCR. Measure conformational transitions by FlAsH-BRET or NanoBRET conformational sensor. TMAO increases conformational sampling and reduces Filamin-P — mechanistic basis for arrhythmia.","#ff2d55"),
]

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("<div style='color:#00e5ff;font-weight:700;font-size:1.2rem;padding:.5rem 0'>🔬 BioIntel</div>", unsafe_allow_html=True)
    st.markdown("<div style='color:#5a8090;font-size:.78rem;margin-bottom:1rem'>Biology Intelligence Browser</div>", unsafe_allow_html=True)
    
    domain = st.selectbox("Domain", list(DOMAINS.keys()), index=0)
    
    st.markdown("---")
    st.markdown("<div style='color:#5a8090;font-size:.75rem;font-weight:600;margin-bottom:.4rem'>LIVE SEARCH</div>", unsafe_allow_html=True)
    search_gene = st.text_input("Gene/protein", placeholder="e.g. FLNA, EGFR, ARRB2", key="gene_search")
    do_search = st.button("🔍 Analyse", use_container_width=True)
    
    st.markdown("---")
    st.markdown("<div style='color:#5a8090;font-size:.75rem;font-weight:600;margin-bottom:.4rem'>QUICK LINKS</div>", unsafe_allow_html=True)
    for name, url in [("UniProt","https://www.uniprot.org"),("ClinVar","https://www.ncbi.nlm.nih.gov/clinvar"),("GPCRdb","https://gpcrdb.org"),("PhosphoSite FLNA","https://www.phosphosite.org/proteinAction.action?id=2546"),("AlphaFold DB","https://alphafold.ebi.ac.uk"),("STRING DB","https://string-db.org")]:
        st.markdown(f"<a href='{url}' target='_blank' style='display:block;font-size:.78rem;color:#00e5ff;padding:3px 0;border-bottom:1px solid #0d2545'>{name} ↗</a>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
D = DOMAINS[domain]

st.markdown(f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:.3rem'><span style='font-size:1.8rem'>{D['icon']}</span><span style='color:{D['color']};font-weight:700;font-size:1.5rem'>{domain.split(' ',1)[1]}</span></div>", unsafe_allow_html=True)
st.markdown(f"<div style='color:#5a8090;font-size:.88rem;margin-bottom:1.2rem'>{D['description']}</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# GENE SEARCH PANEL (if triggered)
# ═══════════════════════════════════════════════════════════════════════════════
if do_search and search_gene.strip():
    gene = search_gene.strip().upper()
    st.markdown(f"<hr style='border-color:#0d2545'>", unsafe_allow_html=True)
    sh("🔎", f"Live Analysis — {gene}", "#00e5ff")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.spinner("Fetching UniProt..."):
            pdata = fetch_uniprot(gene)
        if pdata.get("name"):
            card(f"<div style='color:#00e5ff;font-weight:600;font-size:.95rem;margin-bottom:.3rem'>{pdata['name']}</div><div style='color:#5a8090;font-size:.8rem'>{pdata.get('function','')[:250]}{'...' if len(pdata.get('function',''))>250 else ''}</div>")
        
        with st.spinner("Fetching STRING partners..."):
            partners = fetch_string(gene)
        if partners:
            sh("🕸️","Top Interaction Partners (STRING ≥700)","#4a90d9")
            for p in partners:
                st.markdown(f"<div style='display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #0d2545;font-size:.83rem'><span style='color:#d0e8ff'>{p['partner']}</span><span style='color:#00c896'>Score: {p['score']}</span></div>", unsafe_allow_html=True)
    
    with col2:
        ensembl = gene_to_ensembl(gene)
        if ensembl:
            with st.spinner("Fetching OpenTargets..."):
                ot = fetch_opentargets(ensembl)
            if ot.get("drugs"):
                sh("💊","Known Drugs (OpenTargets)","#a855f7")
                for d in ot["drugs"][:5]:
                    st.markdown(f"<div style='color:#d0e8ff;font-size:.82rem;padding:3px 0;border-bottom:1px solid #0d2545'>{d}</div>", unsafe_allow_html=True)
            if ot.get("tractability"):
                st.markdown("<div style='margin-top:.5rem'>" + " ".join(badge(t,"#00c896") for t in ot["tractability"]) + "</div>", unsafe_allow_html=True)
        
        with st.spinner("Fetching PubMed..."):
            papers = fetch_pubmed(f"{gene}[gene] 2022:2025[pdat] functional OR clinical")
        if papers:
            sh("📄","Recent Papers (PubMed)","#ffd60a")
            for p in papers[:4]:
                t = classify_paper(p["title"])
                with st.expander(f"{p['title'][:70]}...", expanded=False):
                    st.markdown(f"{tier_badge(t)} {p['authors']} · {p['journal']} · {p['year']}", unsafe_allow_html=True)
                    st.markdown(f"<a href='{p['url']}' target='_blank'>PubMed PMID {p['pmid']} ↗</a>", unsafe_allow_html=True)
    
    st.markdown("<hr style='border-color:#0d2545'>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# DOMAIN-SPECIFIC CONTENT
# ═══════════════════════════════════════════════════════════════════════════════

if domain == "📚 Literature Compare":
    sh("📚","Side-by-side Literature Evidence Comparison","#ffd60a")
    
    c1, c2 = st.columns(2)
    with c1:
        topic_a = st.text_input("Topic A", value="beta-arrestin signalling GPCR disease")
    with c2:
        topic_b = st.text_input("Topic B", value="Filamin A Ser2152 GPCR activation")
    
    run_compare = st.button("📊 Compare Evidence", use_container_width=True)
    
    if run_compare:
        with st.spinner("Fetching papers for both topics..."):
            papers_a = fetch_pubmed(topic_a, 5)
            papers_b = fetch_pubmed(topic_b, 5)
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown(f"<div style='background:#0a0205;border:1px solid #ff2d5544;border-radius:10px;padding:.7rem 1rem;margin-bottom:.8rem'><div style='color:#ff2d55;font-weight:600;font-size:.85rem'>Topic A</div><div style='color:#6a3040;font-size:.8rem'>{topic_a}</div></div>", unsafe_allow_html=True)
            for p in papers_a:
                t = classify_paper(p["title"])
                with st.expander(p["title"][:65]+"...", expanded=False):
                    st.markdown(f"{tier_badge(t)}", unsafe_allow_html=True)
                    st.markdown(f"**{p['authors']}** · {p['journal']} {p['year']}")
                    st.markdown(f"<a href='{p['url']}' target='_blank'>PMID {p['pmid']} ↗</a>", unsafe_allow_html=True)
        
        with col_b:
            st.markdown(f"<div style='background:#020d08;border:1px solid #00c89644;border-radius:10px;padding:.7rem 1rem;margin-bottom:.8rem'><div style='color:#00c896;font-weight:600;font-size:.85rem'>Topic B</div><div style='color:#3a6050;font-size:.8rem'>{topic_b}</div></div>", unsafe_allow_html=True)
            for p in papers_b:
                t = classify_paper(p["title"])
                with st.expander(p["title"][:65]+"...", expanded=False):
                    st.markdown(f"{tier_badge(t)}", unsafe_allow_html=True)
                    st.markdown(f"**{p['authors']}** · {p['journal']} {p['year']}")
                    st.markdown(f"<a href='{p['url']}' target='_blank'>PMID {p['pmid']} ↗</a>", unsafe_allow_html=True)
        
        tier_weights = {"Tier 1 — RCT":10,"Tier 2 — Cohort":8,"Tier 3 — Functional":7,"Tier 4 — Structural":6,"Tier 5 — Animal":5,"Tier 6 — Computational":4,"Tier 7 — Case report":3,"Tier 8 — Review":2,"Tier 9 — Preprint":1}
        score_a = sum(tier_weights.get(classify_paper(p["title"]),1) for p in papers_a)
        score_b = sum(tier_weights.get(classify_paper(p["title"]),1) for p in papers_b)
        winner = "Topic A" if score_a > score_b else "Topic B"
        st.markdown(f"<div style='background:#020d18;border:1px solid #00e5ff44;border-radius:10px;padding:.8rem 1rem;margin-top:.5rem'><div style='color:#00e5ff;font-weight:600;margin-bottom:.2rem'>Evidence quality score</div><div style='color:#5a8090;font-size:.85rem'>Topic A: <b style='color:#d0e8ff'>{score_a}</b> &nbsp;|&nbsp; Topic B: <b style='color:#d0e8ff'>{score_b}</b> &nbsp;|&nbsp; <b style='color:#00c896'>{winner} has stronger literature support</b></div><div style='color:#3a5060;font-size:.78rem;margin-top:.3rem'>Score = sum of evidence tier weights (RCT=10 → Preprint=1) across top 5 papers per topic</div></div>", unsafe_allow_html=True)
    
    # Pre-loaded example
    st.markdown("---")
    sh("📋","Pre-loaded Example: beta-arrestin vs Filamin Ser2152","#ffd60a")
    ex_papers = [
        ("Bohn et al., Science 1999","10221987","ARRB2 knockout mice are viable and fertile — dispensable protein","Tier 3 — Functional","ARRB2 KO is not lethal","a"),
        ("Shenoy & Lefkowitz, NRDD 2011","21455238","Comprehensive beta-arrestin review — zero germline disease variants discussed","Tier 8 — Review","No disease variant evidence","a"),
        ("Kim et al., Science 2017","28280032","Arrestin-independent signalling exists — contradicts requirement for arrestin","Tier 3 — Functional","ARRB2 not required for signalling","a"),
        ("Nakamura et al., JBC 2015","26124276","Filamin A Ig21 directly binds GPCR H8 FBM — receptor-proximal coupling","Tier 4 — Structural","FLNA Ser2152-P is true signal","b"),
        ("Ortiz-Genga et al., JACC 2016","27908349","FLNC variants cause arrhythmogenic cardiomyopathy — 1000+ P/LP variants","Tier 2 — Cohort","FLNC is a true disease driver","b"),
        ("JBC 2015 — PKA gating","","Ser2152 is conformationally gated — not accessible in autoinhibited state","Tier 4 — Structural","Mechanistically distinct from noise","b"),
    ]
    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("<div style='background:#0a0205;border:1px solid #ff2d5544;border-radius:10px;padding:.7rem 1rem;margin-bottom:.5rem'><div style='color:#ff2d55;font-weight:600;font-size:.85rem'>⚠️ beta-arrestin (ARRB2) — weak genetic evidence</div></div>", unsafe_allow_html=True)
        for title, pmid, finding, tier, conclusion, side in ex_papers:
            if side=="a":
                with st.expander(title, expanded=False):
                    st.markdown(f"{tier_badge(tier)}", unsafe_allow_html=True)
                    st.markdown(f"**Finding:** {finding}")
                    st.markdown(f"**Conclusion:** {conclusion}")
                    if pmid: st.markdown(f"<a href='https://pubmed.ncbi.nlm.nih.gov/{pmid}/' target='_blank'>PubMed {pmid} ↗</a>", unsafe_allow_html=True)
    with cc2:
        st.markdown("<div style='background:#020d08;border:1px solid #00c89644;border-radius:10px;padding:.7rem 1rem;margin-bottom:.5rem'><div style='color:#00c896;font-weight:600;font-size:.85rem'>✅ Filamin Ser2152 — strong mechanistic evidence</div></div>", unsafe_allow_html=True)
        for title, pmid, finding, tier, conclusion, side in ex_papers:
            if side=="b":
                with st.expander(title, expanded=False):
                    st.markdown(f"{tier_badge(tier)}", unsafe_allow_html=True)
                    st.markdown(f"**Finding:** {finding}")
                    st.markdown(f"**Conclusion:** {conclusion}")
                    if pmid: st.markdown(f"<a href='https://pubmed.ncbi.nlm.nih.gov/{pmid}/' target='_blank'>PubMed {pmid} ↗</a>", unsafe_allow_html=True)

elif domain == "💊 Pharma":
    sh("💊","Drug Pipeline","#a855f7")
    phase_colors = {"Approved":"#00c896","Phase 3":"#4a90d9","Phase 2":"#ffd60a","Phase 1":"#5a8090"}
    for name, moa, indication, phase, sponsor in DRUG_PIPELINE:
        pc = phase_colors.get(phase,"#5a8090")
        st.markdown(f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:10px;padding:.7rem 1rem;margin-bottom:.3rem;display:flex;align-items:center;justify-content:space-between'><div><div style='color:#d0e8ff;font-weight:500;font-size:.88rem'>{name}</div><div style='color:#5a8090;font-size:.78rem'>{moa} · {indication}</div><div style='color:#3a5060;font-size:.75rem'>{sponsor}</div></div><span style='background:{pc}22;color:{pc};font-size:.75rem;padding:3px 10px;border-radius:8px;border:1px solid {pc}44;white-space:nowrap'>{phase}</span></div>", unsafe_allow_html=True)
    
    sh("📊","Key Target Classes","#a855f7")
    target_classes = [("GPCRs","~34% of all approved drugs","#00e5ff"),("Protein kinases","80+ approved inhibitors","#ff8c42"),("Nuclear receptors","Steroids, thyroid, retinoic acid","#ffd60a"),("Ion channels","Cardiology, neurology, anaesthesia","#4a90d9"),("Proteases","ACE inhibitors, HIV protease","#a855f7"),("mAbs / biologics","Fastest growing class","#00c896"),("ADCs","14 FDA approved — linker+payload","#ff2d55"),("PROTACs","3 in Phase 2/3 — degraders","#5a8090")]
    for tc, desc, color in target_classes:
        st.markdown(f"<div style='display:flex;align-items:center;gap:10px;padding:5px 0;border-bottom:1px solid #0d2545'><span style='color:{color};font-weight:500;font-size:.85rem;min-width:140px'>{tc}</span><span style='color:#5a8090;font-size:.82rem'>{desc}</span></div>", unsafe_allow_html=True)
    
    sh("🔗","Databases","#a855f7")
    for name, url, tag, desc in D["databases"]:
        tag_c = "#00c896" if "Free" in tag else "#ffd60a"
        st.markdown(f"<div style='display:flex;align-items:center;justify-content:space-between;padding:5px 0;border-bottom:1px solid #0d2545'><div><a href='{url}' target='_blank' style='color:#d0e8ff;font-size:.85rem'>{name}</a><div style='color:#3a5060;font-size:.75rem'>{desc}</div></div>{badge(tag,tag_c)}</div>", unsafe_allow_html=True)

elif domain == "📡 GPCRs":
    # Special GPCR domain with full study protocol
    if D.get("insight"):
        st.markdown(f"<div style='background:#020d18;border:1px solid #00e5ff33;border-radius:12px;padding:1rem 1.2rem;margin-bottom:1rem'><div style='color:#00e5ff;font-weight:600;font-size:.85rem;margin-bottom:.3rem'>Protellect IP — Research Framework</div><div style='color:#5a9090;font-size:.83rem;line-height:1.7'>{D['insight']}</div></div>", unsafe_allow_html=True)
    
    tab_db, tab_protocol, tab_papers, tab_targets = st.tabs(["Databases","GPCR Study Protocol","Literature","Key Targets"])
    
    with tab_db:
        sh("🗄️","Key Databases","#00e5ff")
        for name, url, tag, desc in D["databases"]:
            tag_c = "#00c896" if "Free" in tag else "#ffd60a"
            st.markdown(f"<div style='display:flex;align-items:center;justify-content:space-between;padding:6px 0;border-bottom:1px solid #0d2545'><div><a href='{url}' target='_blank' style='color:#d0e8ff;font-size:.88rem'>{name}</a><div style='color:#3a5060;font-size:.76rem'>{desc}</div></div>{badge(tag,tag_c)}</div>", unsafe_allow_html=True)
    
    with tab_protocol:
        sh("📡","7-Step GPCR Characterisation Protocol","#00e5ff")
        st.markdown("<div style='color:#5a8090;font-size:.83rem;margin-bottom:.8rem'>This protocol applies to any GPCR. Step 3 (Filamin Ser2152-P) is the receptor-proximal primary readout — more direct than cAMP, IP3, or beta-arrestin. Step 4 is secondary only.</div>", unsafe_allow_html=True)
        for step, title, body, color in GPCR_STUDY_PROTOCOL:
            with st.expander(f"{step} — {title}", expanded=(step in ("Step 1","Step 2","Step 3"))):
                st.markdown(f"<div style='background:#020810;border-left:3px solid {color};padding:.8rem 1rem;border-radius:0 8px 8px 0'><div style='color:#7ab0c0;font-size:.86rem;line-height:1.7'>{body}</div></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        sh("🔗","Protocol References","#00e5ff")
        st.markdown(" ".join([src_link("GPCRdb","https://gpcrdb.org"), src_link("PhosphoSite FLNA","https://www.phosphosite.org/proteinAction.action?id=2546&showAllSites=true"), src_link("Nakamura 2015","https://doi.org/10.1074/jbc.M115.671826"), src_link("IUPHAR Pharmacology","https://www.guidetopharmacology.org")]), unsafe_allow_html=True)
    
    with tab_papers:
        with st.spinner("Fetching GPCR literature..."):
            gpcr_papers = fetch_pubmed("GPCR signalling drug target 2022 2023 2024", 8)
        sh("📄","Recent GPCR Literature","#ffd60a")
        for p in gpcr_papers:
            t = classify_paper(p["title"])
            with st.expander(p["title"][:75]+"...", expanded=False):
                st.markdown(f"{tier_badge(t)} &nbsp; **{p['authors']}** · {p['journal']} · {p['year']}", unsafe_allow_html=True)
                st.markdown(f"<a href='{p['url']}' target='_blank'>PubMed {p['pmid']} ↗</a>", unsafe_allow_html=True)
    
    with tab_targets:
        sh("🎯","Confirmed FBM-containing GPCRs","#00e5ff")
        fbm_gpcrs = [("AGTR1","AT1R","Hypertension, cardiac hypertrophy","#ff2d55"),("ADRB1","β1-AR","Heart failure, arrhythmia","#ff8c42"),("ADRB2","β2-AR","Asthma, heart failure","#ff8c42"),("MAS1","MAS","Cardiovascular, cognitive","#4a90d9"),("ADRA1D","α1D-AR","Hypertension","#ffd60a"),("CHRM2","M2-mAChR","Cardiac rate, CNS","#00c896"),("ADRB3","β3-AR","Adipose, bladder","#a855f7")]
        for gene, common, disease, color in fbm_gpcrs:
            st.markdown(f"<div style='display:flex;align-items:center;justify-content:space-between;padding:6px 0;border-bottom:1px solid #0d2545'><div><span style='color:{color};font-weight:500;font-size:.88rem'>{gene}</span> <span style='color:#5a8090;font-size:.82rem'>({common})</span></div><span style='color:#3a5060;font-size:.8rem'>{disease}</span></div>", unsafe_allow_html=True)
        
        sh("⚠️","Proteins to Deprioritise","#ff2d55")
        st.markdown("<div style='background:#0a0205;border:1px solid #ff2d5533;border-radius:10px;padding:.8rem 1rem'><div style='color:#ff2d55;font-weight:600;font-size:.85rem;margin-bottom:.3rem'>ARRB1 / ARRB2 — No independent disease variants</div><div style='color:#6a3040;font-size:.82rem'>Individual ARRB1/ARRB2 knockouts are viable and fertile. Zero confirmed Mendelian disease variants in ClinVar. Phosphorylation codes on PhosphoSite are kinase noise — not validated signals. Use Filamin Ser2152-P instead. Estimated avoidable spend if pursuing: $4,050,000.</div></div>", unsafe_allow_html=True)

else:
    # GENERIC DOMAIN LAYOUT
    tab1, tab2, tab3, tab4 = st.tabs(["Overview","Databases","Live Literature","Key Facts"])
    
    with tab1:
        if D.get("insight"):
            st.markdown(f"<div style='background:#020d18;border:1px solid {D['color']}33;border-radius:12px;padding:1rem 1.2rem;margin-bottom:1rem'><div style='color:{D['color']};font-weight:600;font-size:.85rem;margin-bottom:.3rem'>Key Insight</div><div style='color:#5a8090;font-size:.83rem;line-height:1.7'>{D['insight']}</div></div>", unsafe_allow_html=True)
        
        sh("🎯","Key Genes & Targets", D["color"])
        cols = st.columns(5)
        for i, gene in enumerate(D["key_genes"]):
            with cols[i%5]:
                st.markdown(f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:8px;padding:.4rem .6rem;text-align:center;font-size:.8rem;color:" + D["color"] + f";margin:2px'>{gene}</div>", unsafe_allow_html=True)
        
        if D.get("key_facts"):
            sh("💡","Key Facts", D["color"])
            for fact in D["key_facts"]:
                st.markdown(f"<div style='display:flex;gap:8px;padding:5px 0;border-bottom:1px solid #0d2545'><span style='color:" + D["color"] + ";font-size:.8rem;margin-top:2px'>→</span><span style='color:#8ab0c0;font-size:.83rem'>{fact}</span></div>", unsafe_allow_html=True)
        
        if D.get("tools"):
            sh("🔧","Tools", D["color"])
            st.markdown(" ".join(src_link(name, url) for name, url in D["tools"]), unsafe_allow_html=True)
    
    with tab2:
        sh("🗄️","Key Databases", D["color"])
        for name, url, tag, desc in D["databases"]:
            tag_c = "#00c896" if "Free" in tag else "#ffd60a" if "API" in tag else "#5a8090"
            st.markdown(
                f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:10px;padding:.7rem 1rem;margin-bottom:.3rem;display:flex;align-items:center;justify-content:space-between'>"
                f"<div style='flex:1'><a href='{url}' target='_blank' style='color:#d0e8ff;font-weight:500;font-size:.88rem'>{name}</a>"
                f"<div style='color:#3a5060;font-size:.76rem;margin-top:2px'>{desc}</div></div>"
                f"<div style='margin-left:12px'>{badge(tag, tag_c)}</div></div>",
                unsafe_allow_html=True
            )
    
    with tab3:
        sh("📄","Live Literature (PubMed 2022–2025)", D["color"])
        if "pubmed_queries" in D and D["pubmed_queries"]:
            q_select = st.selectbox("Query", D["pubmed_queries"])
            if st.button("Fetch papers", use_container_width=False):
                with st.spinner("Searching PubMed..."):
                    papers = fetch_pubmed(q_select, 8)
                if papers:
                    for p in papers:
                        t = classify_paper(p["title"])
                        with st.expander(p["title"][:80]+"...", expanded=False):
                            st.markdown(f"{tier_badge(t)}", unsafe_allow_html=True)
                            st.markdown(f"**{p['authors']}** · *{p['journal']}* · {p['year']}")
                            st.markdown(f"<a href='{p['url']}' target='_blank'>PubMed PMID {p['pmid']} ↗</a>", unsafe_allow_html=True)
                else:
                    st.info("No papers found — try a different query.")
            else:
                st.info("Select a query and click Fetch.")
    
    with tab4:
        sh("📊","Evidence Tiers Reference", D["color"])
        tiers = [("Tier 1 — RCT","Randomised controlled trial — highest evidence, hardest to achieve","#00c896"),("Tier 2 — Cohort","Clinical cohort, prospective, retrospective — real patient data","#4a90d9"),("Tier 3 — Functional","Experimental — CRISPR, assays, western blot, cell models","#ff8c42"),("Tier 4 — Structural","Cryo-EM, X-ray, NMR, SPR, ITC — biophysical validation","#a855f7"),("Tier 5 — Animal","Mouse models, zebrafish, xenograft — translational gap","#ffd60a"),("Tier 6 — Computational","In silico, ML, AlphaFold, docking — hypothesis generating","#5a8090"),("Tier 7 — Case report","Single patient reports — lowest clinical evidence","#3a5a7a"),("Tier 8 — Review","Systematic reviews — synthesise existing evidence","#2a4060"),("Tier 9 — Preprint","Not yet peer reviewed — treat with caution","#ff2d55")]
        for t, desc, color in tiers:
            st.markdown(f"<div style='display:flex;align-items:center;gap:10px;padding:5px 0;border-bottom:1px solid #0d2545'>{badge(t,color)}<span style='color:#5a8090;font-size:.82rem'>{desc}</span></div>", unsafe_allow_html=True)

# Footer
st.markdown("<hr style='border-color:#0d2545;margin-top:2rem'>", unsafe_allow_html=True)
st.markdown(f"<div style='color:#1e3a5a;font-size:.73rem;text-align:center'>BioIntel · Biology Intelligence Browser · Real-time data from UniProt, PubMed, STRING, OpenTargets, AlphaFold · {datetime.now().strftime('%Y')}</div>", unsafe_allow_html=True)
