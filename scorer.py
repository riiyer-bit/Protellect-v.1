"""
scorer.py — Protellect Triage Engine

Handles any experimental dataset format:
- DMS (deep mutational scanning) — typically 0–1 fitness or -1 to +1 enrichment
- CRISPR screens — log2 fold change, positive or negative
- Protein stability assays — ΔΔG values (positive = destabilising)
- Functional activity scores — any scale
- Negative-value datasets (fitness scores, enrichment ratios)
- Inverted scales (where LOW score = HIGH disruption)

The engine auto-detects the score distribution and normalises accordingly.
"""

import pandas as pd
import numpy as np


# ── Column name aliases ───────────────────────────────────────────────────────
# Accepts many common column naming conventions
POSITION_ALIASES = {
    "residue_position", "position", "residue", "pos", "aa_position",
    "amino_acid_position", "site", "residue_pos", "mut_position",
    "codon", "codon_position", "resi", "res_pos", "variant_position",
}

SCORE_ALIASES = {
    "effect_score", "score", "functional_score", "fitness", "fitness_score",
    "enrichment", "log2_enrichment", "dms_score", "activity", "activity_score",
    "delta_fitness", "log2fc", "log2_fc", "fold_change", "ddg", "stability_score",
    "disruption_score", "effect", "normalized_score", "relative_activity",
    "fraction_active", "growth_effect", "selection_coefficient",
}

MUTATION_ALIASES = {
    "mutation", "variant", "mut", "substitution", "aa_change", "amino_acid_change",
    "hgvs_p", "protein_change", "aa_substitution", "change", "variant_id",
}

EXPERIMENT_ALIASES = {
    "experiment_type", "assay", "assay_type", "experiment", "method",
    "screen_type", "dataset", "condition", "library",
}


def _find_column(df_cols, aliases):
    """Find the first matching column from a set of aliases (case-insensitive)."""
    lower_cols = {c.lower().strip(): c for c in df_cols}
    for alias in aliases:
        if alias in lower_cols:
            return lower_cols[alias]
    return None


def _standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename columns to standard names regardless of input format.
    Returns df with standardised column names.
    """
    df = df.copy()
    df.columns = df.columns.str.strip()

    renames = {}

    pos_col = _find_column(df.columns, POSITION_ALIASES)
    if pos_col and pos_col != "residue_position":
        renames[pos_col] = "residue_position"

    score_col = _find_column(df.columns, SCORE_ALIASES)
    if score_col and score_col != "effect_score":
        renames[score_col] = "effect_score"

    mut_col = _find_column(df.columns, MUTATION_ALIASES)
    if mut_col and mut_col != "mutation":
        renames[mut_col] = "mutation"

    exp_col = _find_column(df.columns, EXPERIMENT_ALIASES)
    if exp_col and exp_col != "experiment_type":
        renames[exp_col] = "experiment_type"

    df = df.rename(columns=renames)
    return df


def _detect_score_direction(scores: pd.Series) -> str:
    """
    Detect whether the score scale is:
    - 'high_bad':  HIGH score = HIGH disruption (standard DMS, most assays)
    - 'low_bad':   LOW score = HIGH disruption (fitness where 0=dead, 1=WT)
    - 'negative':  negative values indicate disruption (log2FC, ΔΔG enrichment)
    - 'signed':    both positive and negative, zero = WT-like

    Returns the direction string.
    """
    s = scores.dropna()
    has_neg = (s < 0).any()
    has_pos = (s > 0).any()

    if has_neg and has_pos:
        # Signed scale — both directions. Disruption = large absolute deviation from 0
        return "signed"
    elif has_neg and not has_pos:
        # All negative — typically log2FC where negative = depleted = disruptive
        return "negative"
    else:
        # All non-negative — figure out direction from distribution
        # If median > 0.5 (scores cluster high), probably high_bad
        # If median < 0.5 (scores cluster low), probably low_bad (fitness where 1=good)
        median = s.median()
        pct_high = (s > 0.5).mean()
        if pct_high > 0.6:
            # Majority of scores are high — probably fitness (high = alive, low = dead)
            return "low_bad"
        else:
            return "high_bad"


def _normalise_by_direction(scores: pd.Series, direction: str) -> pd.Series:
    """
    Normalise scores to 0–1 where 1 = maximum disruption / functional effect.
    """
    s = scores.astype(float)

    if direction == "signed":
        # Disruption = absolute deviation from zero. Normalise abs values.
        s = s.abs()
        mn, mx = s.min(), s.max()
        if mx == mn:
            return pd.Series([0.5] * len(s), index=s.index)
        return (s - mn) / (mx - mn)

    elif direction == "negative":
        # More negative = more disruptive. Invert and normalise.
        s = -s  # now large positive = disruptive
        mn, mx = s.min(), s.max()
        if mx == mn:
            return pd.Series([0.5] * len(s), index=s.index)
        return (s - mn) / (mx - mn)

    elif direction == "low_bad":
        # Low score = disruptive. Invert: disruption = 1 - normalised_fitness
        mn, mx = s.min(), s.max()
        if mx == mn:
            return pd.Series([0.5] * len(s), index=s.index)
        normalised = (s - mn) / (mx - mn)
        return 1.0 - normalised  # flip so low fitness → high disruption score

    else:  # "high_bad" — standard
        mn, mx = s.min(), s.max()
        if mx == mn:
            return pd.Series([0.5] * len(s), index=s.index)
        return (s - mn) / (mx - mn)


def validate_dataframe(df: pd.DataFrame) -> tuple[bool, str]:
    """
    Validate the uploaded DataFrame. Accepts many column naming conventions.
    Returns (is_valid, error_message).
    """
    df_std = _standardise_columns(df)

    has_position = "residue_position" in df_std.columns
    has_score    = "effect_score" in df_std.columns

    if not has_position:
        found = _find_column(df.columns, POSITION_ALIASES)
        if not found:
            return False, (
                f"Could not find a residue position column. "
                f"Expected one of: {', '.join(sorted(POSITION_ALIASES)[:8])}... "
                f"Got columns: {', '.join(df.columns.tolist())}"
            )

    if not has_score:
        found = _find_column(df.columns, SCORE_ALIASES)
        if not found:
            return False, (
                f"Could not find a score column. "
                f"Expected one of: {', '.join(sorted(SCORE_ALIASES)[:8])}... "
                f"Got columns: {', '.join(df.columns.tolist())}"
            )

    # Check for numeric scores
    df_std = _standardise_columns(df)
    try:
        pd.to_numeric(df_std["effect_score"], errors="raise")
    except (ValueError, KeyError):
        return False, "Score column contains non-numeric values. Check your data."

    if df_std.empty:
        return False, "The uploaded file has no data rows."

    return True, ""


def detect_dataset_info(df: pd.DataFrame) -> dict:
    """
    Auto-detect information about the dataset for the sidebar summary.
    Returns a dict with detected metadata.
    """
    df_std = _standardise_columns(df)
    scores = pd.to_numeric(df_std["effect_score"], errors="coerce").dropna()
    direction = _detect_score_direction(scores)

    # Detect experiment types
    exp_types = []
    if "experiment_type" in df_std.columns:
        exp_types = df_std["experiment_type"].dropna().unique().tolist()

    # Detect mutations column
    has_mutations = "mutation" in df_std.columns

    # Detect score range
    score_min = float(scores.min())
    score_max = float(scores.max())
    score_median = float(scores.median())

    # Infer assay type from score range and column names
    assay_guess = "Unknown assay"
    orig_cols = [c.lower() for c in df.columns]
    if "ddg" in orig_cols or "stability" in any(c for c in orig_cols):
        assay_guess = "Protein stability assay (ΔΔG)"
    elif "log2" in " ".join(orig_cols) or direction in ("negative", "signed"):
        assay_guess = "CRISPR/sequencing enrichment screen"
    elif "fitness" in " ".join(orig_cols):
        assay_guess = "Deep mutational scanning (fitness)"
    elif "dms" in " ".join(orig_cols) or exp_types and any("dms" in str(e).lower() for e in exp_types):
        assay_guess = "Deep mutational scanning (DMS)"
    elif exp_types:
        assay_guess = " / ".join(str(e) for e in exp_types[:3])
    elif 0 <= score_min and score_max <= 1.5:
        assay_guess = "Functional activity assay (0–1 scale)"
    else:
        assay_guess = f"Functional assay (score range {score_min:.2f} – {score_max:.2f})"

    return {
        "n_rows": len(df_std),
        "score_direction": direction,
        "score_min": round(score_min, 3),
        "score_max": round(score_max, 3),
        "score_median": round(score_median, 3),
        "exp_types": exp_types,
        "has_mutations": has_mutations,
        "assay_guess": assay_guess,
        "direction_note": {
            "high_bad":  "Higher score → greater functional disruption",
            "low_bad":   "Lower score → greater functional disruption (fitness scale — inverted automatically)",
            "negative":  "More negative → greater disruption (log2 enrichment scale — inverted automatically)",
            "signed":    "Large absolute deviation from zero → greater disruption (signed scale — magnitude used)",
        }[direction],
    }


def assign_priority(score: float) -> str:
    if score >= 0.75:
        return "HIGH"
    elif score >= 0.40:
        return "MEDIUM"
    else:
        return "LOW"


def generate_hypothesis(row: pd.Series) -> str:
    mutation = row.get("mutation", f"residue {int(row['residue_position'])}")
    score = round(row["normalized_score"], 2)
    priority = row["priority"]
    exp = row.get("experiment_type", "")
    exp_str = f" ({exp})" if exp and str(exp) not in ("nan", "") else ""

    if priority == "HIGH":
        return (
            f"{mutation} shows strong functional disruption{exp_str} (normalised score: {score}). "
            f"High priority for structural follow-up and experimental validation. "
            f"Recommend thermal shift assay and EMSA as first-line validation."
        )
    elif priority == "MEDIUM":
        return (
            f"{mutation} shows moderate functional effect{exp_str} (normalised score: {score}). "
            f"Consider in context of domain location, conservation, and proximity to HIGH-priority hits."
        )
    else:
        return (
            f"{mutation} shows limited functional effect{exp_str} (normalised score: {score}). "
            f"Low priority — likely represents tolerated variation. "
            f"Validate before fully deprioritising if evolutionarily conserved."
        )


def score_residues(df: pd.DataFrame) -> pd.DataFrame:
    """
    Main entry. Handles any dataset format, detects score direction,
    normalises, assigns priority, generates hypotheses.
    """
    df = _standardise_columns(df)

    # Convert to numeric, coerce errors to NaN, drop NaN score rows
    df["effect_score"] = pd.to_numeric(df["effect_score"], errors="coerce")
    df = df.dropna(subset=["effect_score"]).copy()

    # Detect direction and normalise
    direction = _detect_score_direction(df["effect_score"])
    df["normalized_score"] = _normalise_by_direction(df["effect_score"], direction)
    df["normalized_score"] = df["normalized_score"].round(3)

    # Convert position to int (handle floats like 175.0)
    df["residue_position"] = pd.to_numeric(df["residue_position"], errors="coerce").dropna().astype(int)
    df = df.dropna(subset=["residue_position"]).copy()
    df["residue_position"] = df["residue_position"].astype(int)

    # Apply priority
    df["priority"] = df["normalized_score"].apply(assign_priority)
    df["hypothesis"] = df.apply(generate_hypothesis, axis=1)

    df = df.sort_values("normalized_score", ascending=False).reset_index(drop=True)
    df.index += 1
    return df


def get_color_for_priority(priority: str) -> str:
    return {"HIGH": "#FF4C4C", "MEDIUM": "#FFA500", "LOW": "#4CA8FF"}.get(priority, "#AAAAAA")


def get_summary_stats(df: pd.DataFrame) -> dict:
    return {
        "total_residues":  len(df),
        "high_priority":   int((df["priority"] == "HIGH").sum()),
        "medium_priority": int((df["priority"] == "MEDIUM").sum()),
        "low_priority":    int((df["priority"] == "LOW").sum()),
        "top_residue":     int(df.iloc[0]["residue_position"]) if not df.empty else None,
        "top_score":       round(float(df.iloc[0]["normalized_score"]), 3) if not df.empty else None,
    }
