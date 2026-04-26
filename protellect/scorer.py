"""
scorer.py — Protellect Triage Engine

This is the brain of the MVP. It takes your uploaded experimental data
and assigns each residue a priority tier (HIGH / MEDIUM / LOW) based on
its functional effect score. No ML yet — pure rule-based logic that you
can tune based on your biological intuition.
"""

import pandas as pd


REQUIRED_COLUMNS = {"residue_position", "effect_score"}


def validate_dataframe(df: pd.DataFrame) -> tuple[bool, str]:
    """
    Check that the uploaded CSV has the columns we need.
    Returns (is_valid, error_message).
    """
    missing = REQUIRED_COLUMNS - set(df.columns.str.lower().str.strip())
    if missing:
        return False, f"Missing required columns: {', '.join(missing)}"
    if df.empty:
        return False, "The uploaded file has no data rows."
    return True, ""


def normalize_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize effect_score to a 0–1 range so different experiments
    (which may use different scales) are comparable.
    """
    df = df.copy()
    df.columns = df.columns.str.lower().str.strip()

    min_val = df["effect_score"].min()
    max_val = df["effect_score"].max()

    if max_val == min_val:
        # All scores identical — set everything to 0.5
        df["normalized_score"] = 0.5
    else:
        df["normalized_score"] = (df["effect_score"] - min_val) / (max_val - min_val)

    return df


def assign_priority(score: float) -> str:
    """
    Rule-based priority assignment.

    Thresholds are tunable — adjust these based on your biological
    judgment of what constitutes a meaningful effect in your assay.
    """
    if score >= 0.75:
        return "HIGH"
    elif score >= 0.40:
        return "MEDIUM"
    else:
        return "LOW"


def generate_hypothesis(row: pd.Series) -> str:
    """
    Generate a plain-English hypothesis string for each residue.
    This is intentionally simple for the MVP — Phase 2 will enrich
    this with UniProt annotations and domain context.
    """
    mutation = row.get("mutation", f"residue {int(row['residue_position'])}")
    score = round(row["normalized_score"], 2)
    priority = row["priority"]

    if priority == "HIGH":
        return (
            f"{mutation} shows strong functional disruption (score: {score}). "
            f"High priority for structural follow-up and experimental validation."
        )
    elif priority == "MEDIUM":
        return (
            f"{mutation} shows moderate functional effect (score: {score}). "
            f"Consider in context of domain location and conservation."
        )
    else:
        return (
            f"{mutation} shows limited functional effect (score: {score}). "
            f"Low priority — may represent tolerated variation."
        )


def score_residues(df: pd.DataFrame) -> pd.DataFrame:
    """
    Main entry point. Takes a raw uploaded DataFrame and returns
    a scored, ranked, annotated DataFrame ready for display.
    """
    df = normalize_scores(df)
    df["priority"] = df["normalized_score"].apply(assign_priority)
    df["hypothesis"] = df.apply(generate_hypothesis, axis=1)
    df["residue_position"] = df["residue_position"].astype(int)
    df = df.sort_values("normalized_score", ascending=False).reset_index(drop=True)
    df.index += 1  # Start rank at 1
    return df


def get_color_for_priority(priority: str) -> str:
    """
    Returns a hex color for each priority tier.
    Used by the 3D viewer to color residues.
    """
    return {
        "HIGH": "#FF4C4C",
        "MEDIUM": "#FFA500",
        "LOW": "#4CA8FF",
    }.get(priority, "#AAAAAA")


def get_summary_stats(df: pd.DataFrame) -> dict:
    """
    Returns a quick summary dict for display in the dashboard header.
    """
    return {
        "total_residues": len(df),
        "high_priority": len(df[df["priority"] == "HIGH"]),
        "medium_priority": len(df[df["priority"] == "MEDIUM"]),
        "low_priority": len(df[df["priority"] == "LOW"]),
        "top_residue": int(df.iloc[0]["residue_position"]) if not df.empty else None,
        "top_score": round(df.iloc[0]["normalized_score"], 3) if not df.empty else None,
    }
