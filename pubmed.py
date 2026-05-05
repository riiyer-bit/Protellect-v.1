from __future__ import annotations
"""
NCBI Gene & genomic data client.
Fetches chromosomal location, exon count, RefSeq IDs, GO terms.
"""

import requests
import streamlit as st


ESEARCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
EFETCH   = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


class NCBIClient:

    def fetch_gene(self, gene_symbol: str, organism: str = "Homo sapiens") -> dict:
        """Fetch NCBI Gene summary for a human gene."""
        gene_id = self._search_gene_id(gene_symbol, organism)
        if not gene_id:
            return {}
        return self._fetch_gene_summary(gene_id)

    # ── private ───────────────────────────────────────────────────────────────
    def _search_gene_id(self, symbol: str, organism: str) -> str | None:
        params = {
            "db":      "gene",
            "term":    f"{symbol}[gene name] AND {organism}[organism] AND alive[property]",
            "retmax":  1,
            "retmode": "json",
        }
        try:
            r = requests.get(ESEARCH, params=params, timeout=15)
            r.raise_for_status()
            ids = r.json().get("esearchresult", {}).get("idlist", [])
            return ids[0] if ids else None
        except Exception as e:
            st.warning(f"NCBI gene search error: {e}")
            return None

    def _fetch_gene_summary(self, gene_id: str) -> dict:
        params = {
            "db":      "gene",
            "id":      gene_id,
            "retmode": "json",
        }
        try:
            r = requests.get(ESUMMARY, params=params, timeout=15)
            r.raise_for_status()
            data   = r.json().get("result", {})
            entry  = data.get(gene_id, {})
            if not entry:
                return {}
            # Genomic location
            loc = entry.get("locationhist", [{}])
            # Genomic info
            ginfo = entry.get("genomicinfo", [{}])[0] if entry.get("genomicinfo") else {}
            return {
                "gene_id":          gene_id,
                "symbol":           entry.get("name", ""),
                "full_name":        entry.get("description", ""),
                "chromosome":       entry.get("chromosome", ""),
                "map_location":     entry.get("maplocation", ""),
                "summary":          entry.get("summary", ""),
                "refseq_mrna":      ginfo.get("chraccver", ""),
                "start":            ginfo.get("chrstart", ""),
                "stop":             ginfo.get("chrstop", ""),
                "exon_count":       ginfo.get("exoncount", ""),
                "orientation":      ginfo.get("chrorientation", ""),
                "gene_id_link":     f"https://www.ncbi.nlm.nih.gov/gene/{gene_id}",
                "omim_ids":         [ref.get("id") for ref in entry.get("xrefs", [])
                                     if ref.get("dbname") == "OMIM"],
                "hgnc_id":          next((ref.get("id") for ref in entry.get("xrefs", [])
                                          if ref.get("dbname") == "HGNC"), ""),
                "ensembl_id":       next((ref.get("id") for ref in entry.get("xrefs", [])
                                          if ref.get("dbname") == "Ensembl"), ""),
                "other_aliases":    entry.get("otheraliases", ""),
            }
        except Exception as e:
            st.warning(f"NCBI gene fetch error: {e}")
            return {}
