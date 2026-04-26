"""
uniprot_api.py — Live UniProt + ClinVar API Integration
Phase 2: replaces hardcoded residue data with live database calls
"""
import requests
import json
from functools import lru_cache

UNIPROT_BASE = "https://rest.uniprot.org/uniprotkb"
NCBI_BASE    = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TIMEOUT      = 12

@lru_cache(maxsize=32)
def fetch_uniprot_entry(uniprot_id: str) -> dict:
    url = f"{UNIPROT_BASE}/{uniprot_id.strip().upper()}.json"
    try:
        r = requests.get(url, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}

def get_protein_name(uniprot_id: str) -> str:
    data = fetch_uniprot_entry(uniprot_id)
    try:
        return data["proteinDescription"]["recommendedName"]["fullName"]["value"]
    except Exception:
        return uniprot_id

def get_gene_name(uniprot_id: str) -> str:
    data = fetch_uniprot_entry(uniprot_id)
    try:
        return data["genes"][0]["geneName"]["value"]
    except Exception:
        return ""

def get_organism(uniprot_id: str) -> str:
    data = fetch_uniprot_entry(uniprot_id)
    try:
        return data["organism"]["scientificName"]
    except Exception:
        return ""

def get_sequence_length(uniprot_id: str) -> int:
    data = fetch_uniprot_entry(uniprot_id)
    try:
        return data["sequence"]["length"]
    except Exception:
        return 0

def get_residue_annotations(uniprot_id: str) -> dict:
    """
    Returns per-residue annotations from UniProt features.
    Keys are residue positions (int), values are dicts of annotation info.
    """
    data = fetch_uniprot_entry(uniprot_id)
    annotations = {}
    features = data.get("features", [])

    for feat in features:
        ftype = feat.get("type", "")
        desc  = feat.get("description", "")
        loc   = feat.get("location", {})
        start = loc.get("start", {}).get("value")
        end   = loc.get("end", {}).get("value")

        if start is None:
            continue

        # Annotate every position in the feature range
        for pos in range(int(start), int(end or start) + 1):
            if pos not in annotations:
                annotations[pos] = {
                    "domain": "",
                    "active_site": False,
                    "binding_site": False,
                    "disulfide": False,
                    "ptm": "",
                    "natural_variant": [],
                    "mutagenesis": [],
                    "conservation": "",
                    "features": [],
                    "source": f"UniProt {uniprot_id}",
                }
            entry = annotations[pos]

            if ftype in ("Region", "Domain", "Topological domain", "Transmembrane"):
                if not entry["domain"]:
                    entry["domain"] = desc or ftype
            elif ftype == "Active site":
                entry["active_site"] = True
                entry["features"].append(f"Active site: {desc}")
            elif ftype == "Binding site":
                entry["binding_site"] = True
                entry["features"].append(f"Binding site: {desc}")
            elif ftype == "Disulfide bond":
                entry["disulfide"] = True
                entry["features"].append("Disulfide bond")
            elif ftype == "Modified residue":
                entry["ptm"] = desc
                entry["features"].append(f"PTM: {desc}")
            elif ftype == "Natural variant":
                entry["natural_variant"].append(desc)
            elif ftype == "Mutagenesis":
                entry["mutagenesis"].append(desc)
            else:
                if desc:
                    entry["features"].append(f"{ftype}: {desc}")

    return annotations

def get_protein_function(uniprot_id: str) -> str:
    data = fetch_uniprot_entry(uniprot_id)
    try:
        comments = data.get("comments", [])
        for c in comments:
            if c.get("commentType") == "FUNCTION":
                texts = c.get("texts", [])
                if texts:
                    return texts[0].get("value", "")
    except Exception:
        pass
    return ""

def get_disease_associations(uniprot_id: str) -> list:
    data = fetch_uniprot_entry(uniprot_id)
    diseases = []
    try:
        for c in data.get("comments", []):
            if c.get("commentType") == "DISEASE":
                d = c.get("disease", {})
                name = d.get("diseaseId", "")
                desc = d.get("description", "")
                if name:
                    diseases.append({"name": name, "description": desc})
    except Exception:
        pass
    return diseases

@lru_cache(maxsize=32)
def fetch_clinvar_variants(gene_name: str) -> list:
    """Search ClinVar for pathogenic variants in a gene."""
    try:
        search_url = f"{NCBI_BASE}/esearch.fcgi"
        params = {
            "db": "clinvar",
            "term": f"{gene_name}[gene] AND pathogenic[clinical_significance]",
            "retmode": "json",
            "retmax": 200,
        }
        r = requests.get(search_url, params=params, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        return ids
    except Exception:
        return []

def get_clinvar_count(gene_name: str) -> int:
    return len(fetch_clinvar_variants(gene_name))

def get_alphafold_pdb(uniprot_id: str) -> tuple:
    """Try AlphaFold, fall back to PDB search."""
    url = f"https://alphafold.ebi.ac.uk/files/AF-{uniprot_id.upper()}-F1-model_v4.pdb"
    try:
        r = requests.get(url, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.text, "AlphaFold"
    except Exception:
        pass
    return None, None

def search_pdb_for_uniprot(uniprot_id: str) -> tuple:
    """Search RCSB PDB for structures matching a UniProt ID."""
    try:
        query = {
            "query": {
                "type": "terminal",
                "service": "text",
                "parameters": {
                    "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
                    "operator": "exact_match",
                    "value": uniprot_id.upper()
                }
            },
            "return_type": "entry",
            "request_options": {"paginate": {"start": 0, "rows": 1}}
        }
        r = requests.post(
            "https://search.rcsb.org/rcsbsearch/v1/query",
            json=query, timeout=TIMEOUT
        )
        if r.status_code == 200:
            results = r.json().get("result_set", [])
            if results:
                pdb_id = results[0]["identifier"]
                pdb_url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
                pdb_r = requests.get(pdb_url, timeout=TIMEOUT)
                if pdb_r.status_code == 200:
                    return pdb_r.text, f"PDB:{pdb_id}"
    except Exception:
        pass
    return None, None

def get_structure_for_uniprot(uniprot_id: str) -> tuple:
    """
    Master function: tries AlphaFold first, then PDB search.
    Returns (pdb_string, source_label) or (None, None).
    """
    pdb, src = get_alphafold_pdb(uniprot_id)
    if pdb:
        return pdb, src
    pdb, src = search_pdb_for_uniprot(uniprot_id)
    if pdb:
        return pdb, src
    return None, None
