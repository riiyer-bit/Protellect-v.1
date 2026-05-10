"""
Microbiome AI — LLM-powered functional re-annotation of microbial genes.
The problem: KEGG/GO/COG annotations say "biosynthesis" or "metabolism" without
telling you what the microbe ACTUALLY does in the host context.
This module uses Claude to translate database IDs → meaningful biological narrative.
"""
import streamlit as st, requests, json, re
import anthropic

ANTHROPIC_CLIENT = None

def _get_client():
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
        client = _get_client()
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
        client = _get_client()
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
        client = _get_client()
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
