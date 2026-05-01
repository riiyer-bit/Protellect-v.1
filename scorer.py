"""
scorer.py — Protellect Triage Engine

Handles any experimental dataset:
- DMS (0–1 fitness or enrichment)
- CRISPR log2FC (negative = depleted = disruptive)
- ΔΔG stability (positive = destabilising)
- Inverted fitness (1=WT, 0=dead)
- Signed enrichment (both +/-)
- Any numeric scale, any column naming convention
"""

import pandas as pd
import numpy as np

POSITION_ALIASES = {
    "residue_position","position","residue","pos","aa_position",
    "amino_acid_position","site","residue_pos","mut_position",
    "codon","codon_position","resi","res_pos","variant_position",
    "aa_pos","pdb_position","uniprot_position","seq_position",
}

SCORE_ALIASES = {
    "effect_score","score","functional_score","fitness","fitness_score",
    "enrichment","log2_enrichment","dms_score","activity","activity_score",
    "delta_fitness","log2fc","log2_fc","fold_change","ddg","stability_score",
    "disruption_score","effect","normalized_score","relative_activity",
    "fraction_active","growth_effect","selection_coefficient","z_score",
    "log_enrichment","functional_effect","functional_impact","impact_score",
    "relative_fitness","norm_fitness","scaled_effect","lfc","log2foldchange",
}

MUTATION_ALIASES = {
    "mutation","variant","mut","substitution","aa_change","amino_acid_change",
    "hgvs_p","protein_change","aa_substitution","change","variant_id",
    "mutation_id","alt","alternative","sub","codon_change","nt_change",
}

EXPERIMENT_ALIASES = {
    "experiment_type","assay","assay_type","experiment","method",
    "screen_type","dataset","condition","library","replicate","sample",
    "treatment","construct","category","type",
}


def _find_col(cols, aliases):
    lower = {c.lower().strip(): c for c in cols}
    for a in aliases:
        if a in lower:
            return lower[a]
    return None


def _standardise(df):
    df = df.copy()
    df.columns = df.columns.str.strip()
    renames = {}
    for aliases, std in [
        (POSITION_ALIASES, "residue_position"),
        (SCORE_ALIASES,    "effect_score"),
        (MUTATION_ALIASES, "mutation"),
        (EXPERIMENT_ALIASES,"experiment_type"),
    ]:
        col = _find_col(df.columns, aliases)
        if col and col != std:
            renames[col] = std
    return df.rename(columns=renames)


def _detect_direction(scores):
    s = pd.to_numeric(scores, errors="coerce").dropna()
    has_neg = (s < 0).any()
    has_pos = (s > 0).any()
    if has_neg and has_pos:
        return "signed"
    if has_neg:
        return "negative"
    if s.max() <= 0.0:
        return "negative"
    pct_high = float((s > s.median()).mean())
    if s.max() <= 2.0 and s.min() >= 0 and pct_high > 0.55:
        return "low_bad"
    return "high_bad"


def _normalise(scores, direction):
    s = pd.to_numeric(scores, errors="coerce").astype(float)
    if direction == "signed":
        s = s.abs()
    elif direction == "negative":
        s = -s
    elif direction == "low_bad":
        mn, mx = s.min(), s.max()
        if mx == mn:
            return pd.Series([0.5]*len(s), index=s.index)
        return 1.0 - (s - mn)/(mx - mn)
    mn, mx = s.min(), s.max()
    if mx == mn:
        return pd.Series([0.5]*len(s), index=s.index)
    return (s - mn)/(mx - mn)


def validate_dataframe(df):
    df2 = _standardise(df)
    missing = []
    if "residue_position" not in df2.columns:
        missing.append(f"residue position (tried: {', '.join(sorted(POSITION_ALIASES)[:6])}...)")
    if "effect_score" not in df2.columns:
        missing.append(f"effect score (tried: {', '.join(sorted(SCORE_ALIASES)[:6])}...)")
    if missing:
        return False, f"Missing columns: {'; '.join(missing)}. Your columns: {', '.join(df.columns.tolist())}"
    try:
        pd.to_numeric(df2["effect_score"], errors="raise")
    except Exception:
        # Try coercing — some rows may be non-numeric (headers embedded in data)
        valid = pd.to_numeric(df2["effect_score"], errors="coerce").notna()
        if valid.sum() == 0:
            return False, "Score column has no numeric values."
    if df2.empty:
        return False, "File has no data rows."
    return True, ""


def detect_dataset_info(df):
    df2 = _standardise(df)
    scores = pd.to_numeric(df2["effect_score"], errors="coerce").dropna()
    direction = _detect_direction(scores)

    exp_types = []
    if "experiment_type" in df2.columns:
        exp_types = [str(e) for e in df2["experiment_type"].dropna().unique().tolist() if str(e) != "nan"]

    orig_cols = [c.lower() for c in df.columns]
    col_str   = " ".join(orig_cols)

    if any("ddg" in c for c in orig_cols) or any("stability" in c for c in orig_cols):
        assay_guess = "Protein stability assay (ΔΔG)"
    elif any("log2" in c for c in orig_cols) or direction in ("negative", "signed"):
        assay_guess = "CRISPR / sequencing enrichment screen (log2FC)"
    elif any("fitness" in c for c in orig_cols):
        assay_guess = "Deep mutational scanning — fitness"
    elif any("dms" in c for c in orig_cols) or any("dms" in str(e).lower() for e in exp_types):
        assay_guess = "Deep mutational scanning (DMS)"
    elif exp_types:
        assay_guess = " / ".join(exp_types[:3])
    else:
        assay_guess = f"Functional assay (score range {float(scores.min()):.2f}–{float(scores.max()):.2f})"

    direction_note = {
        "high_bad":  "Higher score → greater disruption (standard scale)",
        "low_bad":   "Lower score → greater disruption (fitness scale, auto-inverted)",
        "negative":  "More negative → greater disruption (log2FC scale, auto-inverted)",
        "signed":    "Large |deviation| from zero → greater disruption (signed scale)",
    }[direction]

    has_mutations = "mutation" in df2.columns

    # Infer target proteins from mutation column if available
    target_proteins = []
    if has_mutations:
        muts = df2["mutation"].dropna().astype(str).tolist()
        # Try to detect gene name prefixes like "TP53_R175H" or just residue patterns
        import re
        gene_candidates = set()
        for m in muts[:50]:
            gene_match = re.match(r'^([A-Z][A-Z0-9]{1,9})_', m)
            if gene_match:
                gene_candidates.add(gene_match.group(1))
        target_proteins = list(gene_candidates)[:3]

    return {
        "n_rows": len(df2),
        "score_direction": direction,
        "score_min": round(float(scores.min()), 3),
        "score_max": round(float(scores.max()), 3),
        "score_median": round(float(scores.median()), 3),
        "exp_types": exp_types,
        "has_mutations": has_mutations,
        "assay_guess": assay_guess,
        "direction_note": direction_note,
        "target_proteins": target_proteins,
        "n_high": 0,  # filled after scoring
        "n_med": 0,
        "top_hit": "",
    }


def assign_priority(score):
    if score >= 0.75:   return "HIGH"
    elif score >= 0.40: return "MEDIUM"
    else:               return "LOW"


def generate_hypothesis(row):
    mutation = row.get("mutation", f"residue {int(row['residue_position'])}")
    if str(mutation) in ("nan", ""):
        mutation = f"residue {int(row['residue_position'])}"
    score    = round(row["normalized_score"], 2)
    priority = row["priority"]
    exp      = row.get("experiment_type", "")
    exp_str  = f" ({exp})" if exp and str(exp) not in ("nan","") else ""
    if priority == "HIGH":
        return (f"{mutation} shows strong functional disruption{exp_str} (score: {score}). "
                f"High priority — recommend thermal shift assay and EMSA as first-line validation.")
    elif priority == "MEDIUM":
        return (f"{mutation} shows moderate functional effect{exp_str} (score: {score}). "
                f"Investigate in context of domain location and proximity to HIGH-priority hits.")
    else:
        return (f"{mutation} shows limited functional effect{exp_str} (score: {score}). "
                f"Low priority — likely tolerated variation. Validate before fully deprioritising.")


def score_residues(df):
    df = _standardise(df)
    df["effect_score"]    = pd.to_numeric(df["effect_score"], errors="coerce")
    df = df.dropna(subset=["effect_score"]).copy()
    direction             = _detect_direction(df["effect_score"])
    df["normalized_score"] = _normalise(df["effect_score"], direction).round(3)
    df["residue_position"] = pd.to_numeric(df["residue_position"], errors="coerce")
    df = df.dropna(subset=["residue_position"]).copy()
    df["residue_position"] = df["residue_position"].astype(int)
    df["priority"]   = df["normalized_score"].apply(assign_priority)
    df["hypothesis"] = df.apply(generate_hypothesis, axis=1)
    df = df.sort_values("normalized_score", ascending=False).reset_index(drop=True)
    df.index += 1
    return df


def get_color_for_priority(priority):
    return {"HIGH":"#FF4C4C","MEDIUM":"#FFA500","LOW":"#4CA8FF"}.get(priority,"#AAAAAA")


def get_summary_stats(df):
    return {
        "total_residues":  len(df),
        "high_priority":   int((df["priority"]=="HIGH").sum()),
        "medium_priority": int((df["priority"]=="MEDIUM").sum()),
        "low_priority":    int((df["priority"]=="LOW").sum()),
        "top_residue":     int(df.iloc[0]["residue_position"]) if not df.empty else None,
        "top_score":       round(float(df.iloc[0]["normalized_score"]),3) if not df.empty else None,
    }
