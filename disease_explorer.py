"""
disease_explorer.py — Protellect Disease Explorer

Enter any disease → get every protein affiliated with it from ClinVar:
  - All genes with confirmed pathogenic variants for that disease
  - Disease burden ratio for each
  - GPCR status
  - Chromosome location
  - Genomic verdict (worth pursuing or not)
  - Ranked by actual ClinVar evidence strength

Source: ClinVar only. No text mining. No pathway databases.
If a protein is not in ClinVar for this disease, it is not shown.
"""

import streamlit as st
import requests
import time
import re
import pandas as pd
from pathlib import Path
import base64

try:
    from logo import LOGO_DATA_URL as LOGO_B64
except Exception:
    _lp = Path("/mnt/user-data/uploads/1777622887238_image.png")
    LOGO_B64 = ("data:image/png;base64," + base64.b64encode(_lp.read_bytes()).decode()) if _lp.exists() else None

from evidence_layer import calculate_dbr, assign_genomic_tier, get_genomic_verdict

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Protellect/2.0 research@protellect.com",
    "Accept": "application/json",
})

def _get(url, params=None, timeout=14):
    try:
        r = SESSION.get(url, params=params, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


@st.cache_data(show_spinner=False, ttl=3600)
def search_disease_proteins(disease_name: str) -> list:
    """
    Search ClinVar for all genes with pathogenic variants for a given disease.
    Returns list of dicts: {gene, n_pathogenic, n_total, variants, conditions}
    ClinVar ONLY — no text mining, no pathway inference.
    """
    results = {}

    try:
        # Search ClinVar for this disease
        search = _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", {
            "db": "clinvar",
            "term": f'"{disease_name}"[dis] AND clinsig_pathogenic[prop]',
            "retmax": 500,
            "retmode": "json",
            "tool": "protellect",
            "email": "research@protellect.com",
        })

        if not search or not search.get("esearchresult",{}).get("idlist"):
            # Broader searches in sequence - rare diseases need multiple attempts
            for broad_term in [
                f'{disease_name}[dis]',
                f'{disease_name}[title]',
                f'{disease_name}[all fields] AND human[org]',
            ]:
                search = _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", {
                    "db": "clinvar",
                    "term": broad_term,
                    "retmax": 500,
                    "retmode": "json",
                    "tool": "protellect",
                    "email": "research@protellect.com",
                })
                if search and search.get("esearchresult",{}).get("idlist"):
                    break
                time.sleep(0.35)

        if not search:
            return []

        ids = search.get("esearchresult",{}).get("idlist",[])
        if not ids:
            return []

        # Fetch summaries in batches
        for batch_start in range(0, min(len(ids), 500), 100):
            batch = ids[batch_start:batch_start+100]
            time.sleep(0.35)
            summary = _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi", {
                "db": "clinvar",
                "id": ",".join(batch),
                "retmode": "json",
                "tool": "protellect",
                "email": "research@protellect.com",
            }, timeout=20)

            if not summary:
                continue

            doc = summary.get("result", {})
            for vid in doc.get("uids", []):
                entry = doc.get(vid, {})
                sig   = entry.get("germline_classification", {}).get("description", "")
                title = entry.get("title", "")
                conditions = [c.get("trait_name","") for c in entry.get("trait_set", [])]
                stars = entry.get("review_status_label","")

                # Extract gene from title (format: "NM_xxx(GENE):c.xxx")
                gene_match = re.search(r'\(([A-Z][A-Z0-9]{1,15})\)', title)
                gene = gene_match.group(1) if gene_match else None
                if not gene:
                    continue

                sig_lower = sig.lower()
                is_pathogenic = "pathogenic" in sig_lower and "benign" not in sig_lower

                if gene not in results:
                    results[gene] = {
                        "gene": gene,
                        "n_pathogenic": 0,
                        "n_likely_pathogenic": 0,
                        "n_vus": 0,
                        "n_total": 0,
                        "variants": [],
                        "diseases": set(),
                        "best_stars": "",
                    }

                results[gene]["n_total"] += 1
                results[gene]["diseases"].update(c for c in conditions if c)

                if "pathogenic" in sig_lower and "likely pathogenic" not in sig_lower:
                    results[gene]["n_pathogenic"] += 1
                elif "likely pathogenic" in sig_lower:
                    results[gene]["n_likely_pathogenic"] += 1
                elif "uncertain" in sig_lower:
                    results[gene]["n_vus"] += 1

                results[gene]["variants"].append({
                    "title": title[:80],
                    "significance": sig,
                    "conditions": conditions,
                    "stars": stars,
                })

                if stars and len(stars) > len(results[gene]["best_stars"]):
                    results[gene]["best_stars"] = stars

    except Exception as e:
        st.error(f"ClinVar query failed: {e}")
        return []

    # Convert sets to lists
    for g in results:
        results[g]["diseases"] = sorted(list(results[g]["diseases"]))

    # Sort by pathogenic count descending
    sorted_results = sorted(
        results.values(),
        key=lambda x: (x["n_pathogenic"] + x["n_likely_pathogenic"]),
        reverse=True
    )
    return sorted_results


@st.cache_data(show_spinner=False, ttl=3600)
def get_protein_length_and_gpcr(gene_name: str) -> dict:
    """Quick UniProt fetch for protein length and GPCR status."""
    result = {"length": 0, "protein_name": "", "is_gpcr": False, "g_protein": "", "uniprot_id": ""}
    try:
        data = _get("https://rest.uniprot.org/uniprotkb/search", {
            "query": f'gene_exact:{gene_name} AND organism_id:9606 AND reviewed:true',
            "format": "json", "size": 1,
            "fields": "accession,protein_name,sequence,keyword,cc_function,ft_transmem,length",
        })
        if not data or not data.get("results"):
            return result

        entry = data["results"][0]
        result["uniprot_id"]   = entry.get("primaryAccession","")
        result["protein_name"] = entry.get("proteinDescription",{}).get("recommendedName",{}).get("fullName",{}).get("value","")
        result["length"]       = entry.get("sequence",{}).get("length",0)

        kws = [kw.get("value","").lower() for kw in entry.get("keywords",[])]
        kw_str = " ".join(kws)
        result["is_gpcr"] = any(g in kw_str for g in [
            "g protein-coupled receptor","gpcr","rhodopsin","muscarinic","adrenergic"
        ])

        # Count TM regions
        n_tm = sum(1 for f in entry.get("features",[]) if f.get("type","") == "Transmembrane")
        if n_tm == 7:
            result["is_gpcr"] = True

        # G-protein from known map
        known = {
            "CHRM1":"Gq/11","CHRM2":"Gi/o","CHRM3":"Gq/11","CHRM4":"Gi/o","CHRM5":"Gq/11",
            "ADRB1":"Gs","ADRB2":"Gs","ADRA1A":"Gq/11","ADRA2A":"Gi/o",
            "DRD1":"Gs","DRD2":"Gi/o","HTR1A":"Gi/o","HTR2A":"Gq/11",
        }
        result["g_protein"] = known.get(gene_name.upper(),"")

    except Exception:
        pass
    return result


def render():
    if LOGO_B64:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px">'
            f'<img src="{LOGO_B64}" style="height:40px;object-fit:contain;border-radius:7px">'
            f'<div><strong style="font-size:1.1rem">Disease Explorer</strong>'
            f'<p style="color:#555;font-size:0.83rem;margin:0">'
            f'Enter a disease — get every protein with confirmed pathogenic variants in ClinVar</p></div></div>',
            unsafe_allow_html=True
        )
    st.divider()

    st.markdown("""
    <div style="background:#080b14;border:1px solid #1a1d2e;border-radius:8px;padding:10px 14px;
                font-size:0.78rem;color:#666;margin-bottom:16px;line-height:1.6">
      <strong style="color:#aaa">ClinVar only.</strong>
      This explorer shows proteins with <em>confirmed pathogenic variants</em> for your disease
      from ClinVar submissions. Proteins found only in expression studies, animal models,
      or pathway databases are not shown. The Disease Burden Ratio ranks each protein by
      how many pathogenic variants it has relative to its length — the higher the ratio,
      the more essential it is in humans.
    </div>""", unsafe_allow_html=True)

    disease_input = st.text_input(
        "Disease name",
        placeholder="e.g. Prune belly syndrome, Dilated cardiomyopathy, Breast cancer, Epilepsy...",
        key="dis_exp_input"
    )
    run = st.button("🔍 Find all affiliated proteins", type="primary", use_container_width=True)

    if not run or not disease_input.strip():
        if not disease_input.strip():
            st.markdown("""
            <div style="background:#0a0c14;border:1px solid #1e2030;border-radius:10px;padding:20px;margin-top:8px">
              <p style="font-family:IBM Plex Mono,monospace;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.15em;color:#555;margin-bottom:10px">Try these</p>
              <div style="display:flex;gap:10px;flex-wrap:wrap">
                <span style="background:#0f1117;border:1px solid #1e2030;border-radius:20px;padding:4px 14px;font-size:0.8rem;color:#aaa">Prune belly syndrome</span>
                <span style="background:#0f1117;border:1px solid #1e2030;border-radius:20px;padding:4px 14px;font-size:0.8rem;color:#aaa">Arrhythmogenic cardiomyopathy</span>
                <span style="background:#0f1117;border:1px solid #1e2030;border-radius:20px;padding:4px 14px;font-size:0.8rem;color:#aaa">Prune belly</span>
                <span style="background:#0f1117;border:1px solid #1e2030;border-radius:20px;padding:4px 14px;font-size:0.8rem;color:#aaa">Dilated cardiomyopathy</span>
              </div>
            </div>""", unsafe_allow_html=True)
        return

    disease = disease_input.strip()

    with st.spinner(f"Querying ClinVar for all proteins linked to '{disease}'..."):
        proteins = search_disease_proteins(disease)

    if not proteins:
        st.warning(f"No proteins with confirmed pathogenic ClinVar variants found for **{disease}**. Try a broader disease term or check the spelling.")
        return

    st.markdown(f"""
    <div style="background:#0a140a;border:1px solid #1a3a1a;border-radius:8px;
                padding:12px 16px;margin-bottom:16px">
      <span style="font-family:IBM Plex Mono,monospace;font-size:0.72rem;color:#4CAF50">
        Found {len(proteins)} gene(s) with confirmed pathogenic variants for:
        <strong style="color:#eee;font-size:0.85rem"> {disease}</strong>
      </span>
      <span style="font-size:0.72rem;color:#555;display:block;margin-top:4px">
        Source: NCBI ClinVar · Pathogenic + Likely pathogenic variants only ·
        Ranked by Disease Burden Ratio (pathogenic variants ÷ protein length)
      </span>
    </div>""", unsafe_allow_html=True)

    # Enrich with UniProt data
    enriched = []
    progress = st.progress(0)
    for i, prot in enumerate(proteins[:30]):  # limit to 30 for speed
        gene = prot["gene"]
        uni  = get_protein_length_and_gpcr(gene)
        n_p  = prot["n_pathogenic"] + prot["n_likely_pathogenic"]
        plen = uni["length"]
        dbr  = calculate_dbr(n_p, plen)
        tier = assign_genomic_tier(dbr, n_p)
        v    = get_genomic_verdict(tier, gene, n_p, plen, dbr)
        enriched.append({
            **prot,
            **uni,
            "n_combined_pathogenic": n_p,
            "dbr": dbr,
            "tier": tier,
            "verdict": v,
        })
        progress.progress((i+1)/min(len(proteins),30))

    progress.empty()

    # ── Summary table ─────────────────────────────────────────────────────────
    table_rows = []
    for e in enriched:
        dbr_str = f"{e['dbr']:.3f}" if e["dbr"] is not None else "N/A"
        table_rows.append({
            "Gene":              e["gene"],
            "Protein":           e["protein_name"][:40] if e["protein_name"] else "—",
            "Pathogenic (ClinVar)": e["n_combined_pathogenic"],
            "Total submissions": e["n_total"],
            "Protein length":    e["length"] or "—",
            "DBR":               dbr_str,
            "Tier":              e["verdict"]["label"],
            "GPCR":              "✓" if e["is_gpcr"] else "",
            "G-protein":         e["g_protein"] or ("see UniProt" if e["is_gpcr"] else ""),
        })

    df_table = pd.DataFrame(table_rows)

    def style_tier(val):
        if "Critical" in val: return "color:#FF4C4C;font-weight:600"
        if "Supported" in val: return "color:#FFA500;font-weight:600"
        if "Limited" in val: return "color:#FFD700"
        if "No Genomic" in val: return "color:#888"
        return ""

    st.dataframe(
        df_table.style.map(style_tier, subset=["Tier"]),
        use_container_width=True, height=min(400, len(enriched)*40+50)
    )

    # ── Per-protein cards ─────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.18em;color:#444;border-bottom:1px solid #1e2030;padding-bottom:6px;margin-bottom:14px">Full Breakdown — Each Protein</div>', unsafe_allow_html=True)

    for e in enriched:
        v   = e["verdict"]
        tc  = v["color"]
        dbr_str = f"{e['dbr']:.3f}" if e["dbr"] is not None else "N/A"
        n_p = e["n_combined_pathogenic"]

        with st.expander(f"{v['icon']} {e['gene']} — {e['protein_name'] or e['gene']} · {n_p} pathogenic · DBR {dbr_str} · {v['label']}"):
            c1, c2, c3 = st.columns([1,1,1], gap="medium")

            with c1:
                st.markdown(f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:{tc};margin-bottom:8px">Genomic verdict</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:0.8rem;color:#bbb;line-height:1.6">{v["description"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="margin-top:10px;font-size:0.78rem;color:#888;font-style:italic">{v["trust_statement"]}</div>', unsafe_allow_html=True)

            with c2:
                st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:#4CA8FF;margin-bottom:8px">ClinVar summary</div>', unsafe_allow_html=True)
                rows = [
                    ("Pathogenic",         e["n_pathogenic"]),
                    ("Likely pathogenic",  e["n_likely_pathogenic"]),
                    ("VUS",                e["n_vus"]),
                    ("Total submissions",  e["n_total"]),
                    ("Protein length",     f"{e['length']} aa" if e["length"] else "—"),
                    ("DBR",                dbr_str),
                ]
                for lbl, val in rows:
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;padding:4px 0;'
                        f'border-bottom:1px solid #0d0f1a;font-size:0.78rem">'
                        f'<span style="color:#555">{lbl}</span>'
                        f'<span style="color:{tc if "Path" in lbl else "#aaa"};font-family:IBM Plex Mono,monospace;font-size:0.75rem">{val}</span></div>',
                        unsafe_allow_html=True
                    )
                if e["is_gpcr"]:
                    gp_label = f"· G-protein: {e['g_protein']}" if e.get("g_protein") else ""
                    st.markdown(f'<div style="margin-top:8px;background:#100a18;border:1px solid #9370DB55;border-radius:6px;padding:8px 10px;font-size:0.75rem;color:#9370DB">GPCR ✓ {gp_label}</div>', unsafe_allow_html=True)

            with c3:
                st.markdown('<div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:#4CAF50;margin-bottom:8px">Disease associations (from ClinVar)</div>', unsafe_allow_html=True)
                diseases = e.get("diseases",[])
                if diseases:
                    for d in diseases[:6]:
                        if d and "not provided" not in d.lower():
                            st.markdown(f'<div style="font-size:0.78rem;color:#aaa;padding:3px 0;border-bottom:1px solid #0d0f1a">· {d}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div style="font-size:0.78rem;color:#555">No disease terms in ClinVar submissions</div>', unsafe_allow_html=True)

            # Top pathogenic variants
            path_vars = e["variants"][:8]
            if path_vars:
                st.markdown('<br><div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:#FF4C4C;margin-bottom:6px">Pathogenic variants (ClinVar)</div>', unsafe_allow_html=True)
                for var in path_vars[:5]:
                    sig = var["significance"]
                    sc  = "#FF4C4C" if "Pathogenic" in sig and "Likely" not in sig else "#FFA500"
                    conditions_str = var["conditions"][0][:50] if var["conditions"] else ""
                    st.markdown(
                        f'<div style="font-size:0.75rem;color:#aaa;padding:4px 0;border-bottom:1px solid #0d0f1a">'
                        f'<span style="color:{sc};font-weight:600;font-family:IBM Plex Mono,monospace;font-size:0.68rem">[{sig}]</span>'
                        f' {var["title"]} <span style="color:#555">· {conditions_str}</span></div>',
                        unsafe_allow_html=True
                    )

            # PubMed papers for this gene + disease
            if disease_input.strip():
                with st.spinner(f"Fetching papers for {e['gene']}..."):
                    @st.cache_data(show_spinner=False, ttl=3600)
                    def _get_papers_cached(gene, disease):
                        pubs = []
                        try:
                            q = f"{gene}[gene] AND {disease}[title] AND variant"
                            s = _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", {"db":"pubmed","term":q,"retmax":4,"retmode":"json","tool":"protellect","email":"research@protellect.com"})
                            if s:
                                ids = s.get("esearchresult",{}).get("idlist",[])
                                if ids:
                                    time.sleep(0.35)
                                    summ = _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi", {"db":"pubmed","id":",".join(ids),"retmode":"json","tool":"protellect","email":"research@protellect.com"})
                                    if summ:
                                        rd = summ.get("result",{})
                                        for pid in rd.get("uids",[]):
                                            en = rd.get(pid,{})
                                            pubs.append({"pmid":pid,"title":en.get("title",""),"url":f"https://pubmed.ncbi.nlm.nih.gov/{pid}/","year":en.get("pubdate","")[:4],"journal":en.get("fulljournalname","")})
                        except Exception:
                            pass
                        return pubs
                    gene_papers = _get_papers_cached(e["gene"], disease_input.strip())
                if gene_papers:
                    st.markdown(f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.15em;color:#4CA8FF;margin-top:10px;margin-bottom:6px">PubMed papers — {e["gene"]} + {disease_input.strip()}</div>', unsafe_allow_html=True)
                    for p in gene_papers[:4]:
                        st.markdown(f'<div style="font-size:0.73rem;color:#aaa;padding:3px 0;border-bottom:1px solid #0d0f1a"><a href="{p["url"]}" target="_blank" style="color:#4CA8FF;text-decoration:none">{p["title"][:100]}</a> <span style="color:#555">· {p["journal"][:30]} · {p["year"]}</span></div>', unsafe_allow_html=True)

    # ── Export ────────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    export_df = pd.DataFrame(table_rows)
    st.download_button(
        "⬇ Download full table (CSV)",
        export_df.to_csv(index=False).encode(),
        f"protellect_disease_explorer_{disease.replace(' ','_')}.csv",
        "text/csv"
    )
    st.caption(f"All data from NCBI ClinVar · Queried: {disease} · Protellect v2")
