"""
structure_loader.py — Protein Structure Fetcher

Pulls PDB-format structure files from two public sources:
  1. AlphaFold DB  — predicted structures for almost any protein (UniProt ID)
  2. RCSB PDB      — experimental structures (PDB ID, e.g. "1TUP")

No login or API key required. Both are free and open access.
"""

import requests


ALPHAFOLD_URL = "https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-model_v4.pdb"
PDB_URL = "https://files.rcsb.org/download/{pdb_id}.pdb"

REQUEST_TIMEOUT = 15  # seconds


def fetch_alphafold(uniprot_id: str) -> tuple[str | None, str]:
    """
    Fetch a predicted structure from the AlphaFold database.

    Args:
        uniprot_id: e.g. "P04637" for TP53

    Returns:
        (pdb_string, error_message)
        pdb_string is None if fetch failed.
    """
    uniprot_id = uniprot_id.strip().upper()
    url = ALPHAFOLD_URL.format(uniprot_id=uniprot_id)

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.text, ""
        elif response.status_code == 404:
            return None, (
                f"No AlphaFold structure found for UniProt ID '{uniprot_id}'. "
                f"Check the ID at uniprot.org."
            )
        else:
            return None, f"AlphaFold returned status {response.status_code}."
    except requests.exceptions.Timeout:
        return None, "Request timed out. Check your internet connection."
    except requests.exceptions.RequestException as e:
        return None, f"Network error: {str(e)}"


def fetch_pdb(pdb_id: str) -> tuple[str | None, str]:
    """
    Fetch an experimental structure from the RCSB Protein Data Bank.

    Args:
        pdb_id: 4-character PDB accession, e.g. "1TUP" (TP53 + DNA)

    Returns:
        (pdb_string, error_message)
    """
    pdb_id = pdb_id.strip().upper()
    url = PDB_URL.format(pdb_id=pdb_id)

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.text, ""
        elif response.status_code == 404:
            return None, (
                f"No PDB structure found for ID '{pdb_id}'. "
                f"Check the ID at rcsb.org."
            )
        else:
            return None, f"RCSB PDB returned status {response.status_code}."
    except requests.exceptions.Timeout:
        return None, "Request timed out. Check your internet connection."
    except requests.exceptions.RequestException as e:
        return None, f"Network error: {str(e)}"


def fetch_structure(source: str, identifier: str) -> tuple[str | None, str]:
    """
    Unified entry point. Routes to AlphaFold or PDB depending on source.

    Args:
        source:     "AlphaFold" or "PDB"
        identifier: UniProt ID (AlphaFold) or PDB accession (PDB)

    Returns:
        (pdb_string, error_message)
    """
    if source == "AlphaFold":
        return fetch_alphafold(identifier)
    elif source == "PDB":
        return fetch_pdb(identifier)
    else:
        return None, f"Unknown source: {source}"


# ── Useful test proteins ──────────────────────────────────────────────────────
EXAMPLE_PROTEINS = {
    "TP53 (tumor suppressor)":        {"source": "AlphaFold", "id": "P04637"},
    "EGFR (receptor kinase)":         {"source": "AlphaFold", "id": "P00533"},
    "BRCA1 (DNA repair)":             {"source": "AlphaFold", "id": "P38398"},
    "KRAS (oncogene)":                {"source": "AlphaFold", "id": "P01116"},
    "TP53 + DNA complex (PDB)":       {"source": "PDB",        "id": "1TUP"},
}
