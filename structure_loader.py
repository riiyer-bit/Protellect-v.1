import requests

ALPHAFOLD_URL = "https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-model_v4.pdb"
PDB_URL = "https://files.rcsb.org/download/{pdb_id}.pdb"
REQUEST_TIMEOUT = 15


def fetch_alphafold(uniprot_id):
    url = ALPHAFOLD_URL.format(uniprot_id=uniprot_id.strip().upper())
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.text, ""
        elif response.status_code == 404:
            return None, f"No AlphaFold structure found for UniProt ID '{uniprot_id}'."
        else:
            return None, f"AlphaFold returned status {response.status_code}."
    except requests.exceptions.Timeout:
        return None, "Request timed out."
    except requests.exceptions.RequestException as e:
        return None, f"Network error: {str(e)}"


def fetch_pdb(pdb_id):
    url = PDB_URL.format(pdb_id=pdb_id.strip().upper())
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.text, ""
        elif response.status_code == 404:
            return None, f"No PDB structure found for ID '{pdb_id}'."
        else:
            return None, f"RCSB PDB returned status {response.status_code}."
    except requests.exceptions.Timeout:
        return None, "Request timed out."
    except requests.exceptions.RequestException as e:
        return None, f"Network error: {str(e)}"


def fetch_structure(source, identifier):
    if source == "AlphaFold":
        return fetch_alphafold(identifier)
    elif source == "PDB":
        return fetch_pdb(identifier)
    else:
        return None, f"Unknown source: {source}"


EXAMPLE_PROTEINS = {
    "TP53 (tumor suppressor)":  {"source": "PDB", "id": "2OCJ"},
    "EGFR (receptor kinase)":   {"source": "PDB", "id": "1IVO"},
    "BRCA1 (DNA repair)":       {"source": "PDB", "id": "1JM7"},
    "KRAS (oncogene)":          {"source": "PDB", "id": "4OBE"},
    "TP53 + DNA complex":       {"source": "PDB", "id": "1TUP"},
}
