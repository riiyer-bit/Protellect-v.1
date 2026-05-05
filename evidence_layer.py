"""
evidence_layer.py — Protellect Scientific Evidence & Validation Layer

Implements the "Why trust this hit?" framework:
  - Disease Burden Ratio (ClinVar pathogenic / protein length)
  - Genomic validation tier assignment
  - Paper-backed explanations per tier
  - Experiment recommendations from simple to rigorous
  - Contextual scientific justification

Key papers underpinning this layer:
  1. Minikel et al., Nature 2021 — gnomAD LOF variants as in vivo knockouts
  2. King et al., Nature 2024 — genetic support gives 2.6x clinical success rate
  3. Nelson et al., Nature Genetics 2015 — genetic validation doubles success rate
  4. Plenge et al., Nature Reviews Drug Discovery 2016 — validate the target not the drug
  5. Boycott et al., Nature Reviews Genetics 2013 — rare disease gene discovery
"""

from __future__ import annotations
import math
from typing import Optional


# ── Piggyback protein classification ─────────────────────────────────────────
# Based on Sujay Subbayya Ithychanda's framework (Cleveland Clinic):
# Some proteins are "space fillers" or "scaffold proteins" — they dock onto
# essential proteins like Filamin and preserve their structure, but have no
# independent essential function. They are extensively studied in vitro because
# they are easy to study (soluble, abundant, bindable) but their lack of ClinVar
# variants is the truth: humans can break them without getting sick.
# The disease implications lie in THEIR INTERACTION PARTNERS, not in them.

KNOWN_PIGGYBACK_PROTEINS = {
    # Protein: {partners: [essential proteins they scaffold],
    #           note: explanation, type: classification}
    "ARRB1": {
        "common_name": "β-arrestin 1",
        "partners": ["FLNA", "FLNB", "FLNC", "GPCRs"],
        "note": "Docks onto GPCRs and Filamin. Studied as GPCR regulator but has zero confirmed pathogenic variants in humans. The real signal in GPCR/Filamin studies is coming from the receptor or Filamin, not β-arrestin.",
        "type": "Scaffold/space filler",
    },
    "ARRB2": {
        "common_name": "β-arrestin 2",
        "partners": ["FLNA","FLNB","FLNC","GPCRs"],
        "note": "Structural homologue of β-arrestin 1. Same pattern — zero pathogenic variants, extensively studied, but dispensable in humans.",
        "type": "Scaffold/space filler",
    },
    "TALN1": {
        "common_name": "Talin 1",
        "partners": ["Integrins","Vinculin","Actin"],
        "note": "Taught in every textbook as 'the integrin activator'. Talin KO mouse dies — but zero human disease variants in ClinVar. Talin holds the structure together but the disease implications are in the integrin or downstream effectors.",
        "type": "Structural scaffold",
    },
    "TALN2": {
        "common_name": "Talin 2",
        "partners": ["Integrins","Vinculin"],
        "note": "Same pattern as Talin 1 — structural role, tolerated in humans.",
        "type": "Structural scaffold",
    },
    "VCL": {
        "common_name": "Vinculin",
        "partners": ["Talin","Actin","Integrins"],
        "note": "Cytoskeletal linker. Limited pathogenic variants relative to the volume of literature.",
        "type": "Structural linker",
    },
}

# Proteins that ARE the real drivers — high ClinVar burden
KNOWN_ESSENTIAL_PROTEINS = {
    "FLNA": {
        "common_name": "Filamin A",
        "chromosome": "X",
        "dbr_approx": 0.8,
        "diseases": ["Periventricular nodular heterotopia","Cardiac arrhythmia","Aortic aneurysm","Intellectual disability","Epilepsy","Prune belly syndrome (interaction)"],
        "note": "Ubiquitous. Docks 100s of GPCRs. Mutations cause intellectual disability, epilepsy in females (males often die). The hub protein for GPCR scaffolding — β-arrestin attaches to Filamin, not the other way round.",
    },
    "FLNB": {
        "common_name": "Filamin B",
        "chromosome": "3",
        "dbr_approx": 0.6,
        "diseases": ["Boomerang dysplasia","Larsen syndrome","Atelosteogenesis","Spondylocarpotarsal syndrome"],
        "note": "All mutations cause skeletal/bone disorders. Chromosome 3.",
    },
    "FLNC": {
        "common_name": "Filamin C",
        "chromosome": "7",
        "dbr_approx": 1.58,
        "diseases": ["Arrhythmogenic cardiomyopathy","Dilated cardiomyopathy","Distal myopathy","Myofibrillar myopathy"],
        "note": "Skeletal and cardiac muscle specific. DBR >1.5 — one of the most constrained proteins in the human genome. Every mutation here is serious.",
    },
    "CHRM2": {
        "common_name": "CHRM2 (Muscarinic M2)",
        "chromosome": "7",
        "dbr_approx": 0.22,
        "diseases": ["Dilated cardiomyopathy","Cardiac arrhythmia"],
        "note": "The cardiac muscarinic receptor Sujay flagged as critically important. Dominant-form cardiomyopathies.",
    },
    "CHRM3": {
        "common_name": "CHRM3 (Muscarinic M3)",
        "chromosome": "1",
        "dbr_approx": 0.009,
        "diseases": ["Prune belly syndrome","Congenital bladder malformation"],
        "note": "Rare Mendelian disease — frameshift mutations in the 3rd intracellular loop cause PBS. Confirmed in ClinVar.",
    },
}


def classify_protein_role(gene_name: str, n_pathogenic: int,
                           interaction_partners: list = None) -> dict:
    """
    Classify a protein as essential driver, scaffold/piggyback, or unclassified.
    Returns a classification dict with explanation.
    """
    gene_upper = gene_name.upper()

    # Check known piggyback list
    if gene_upper in KNOWN_PIGGYBACK_PROTEINS:
        pb = KNOWN_PIGGYBACK_PROTEINS[gene_upper]
        return {
            "role":    "piggyback",
            "label":   f"Structural scaffold / piggyback protein ({pb['type']})",
            "icon":    "🔗",
            "color":   "#888888",
            "name":    pb["common_name"],
            "note":    pb["note"],
            "partners":pb["partners"],
            "warning": (
                f"{pb['common_name']} has no confirmed pathogenic variants in ClinVar. "
                f"It acts as a {pb['type'].lower()} for proteins like {', '.join(pb['partners'][:3])}. "
                "The disease implications you are studying likely reside in its interaction "
                "partners, not in this protein itself. "
                "Pursuing this as a primary drug target risks the β-arrestin trap: "
                "extensive in vitro evidence, no human genetic validation."
            ),
        }

    # Check known essential list
    if gene_upper in KNOWN_ESSENTIAL_PROTEINS:
        ess = KNOWN_ESSENTIAL_PROTEINS[gene_upper]
        return {
            "role":     "essential",
            "label":    "Confirmed essential driver",
            "icon":     "⚡",
            "color":    "#FF4C4C",
            "name":     ess["common_name"],
            "note":     ess["note"],
            "diseases": ess["diseases"],
        }

    # Generic classification by ClinVar count
    if n_pathogenic == 0:
        return {
            "role":    "unvalidated",
            "label":   "Genomically unvalidated",
            "icon":    "⚪",
            "color":   "#555555",
            "note":    "No pathogenic variants in ClinVar. Cannot confirm essential role in humans.",
            "warning": "Zero ClinVar pathogenic variants. Check whether this protein is a structural scaffold for an essential partner.",
        }
    elif n_pathogenic <= 10:
        return {
            "role":  "rare_mendelian",
            "label": "Confirmed rare Mendelian disease gene",
            "icon":  "🟡",
            "color": "#FFD700",
            "note":  f"{n_pathogenic} confirmed pathogenic variant(s). Rare disease — low ClinVar count reflects disease rarity, not protein dispensability.",
        }
    elif n_pathogenic <= 200:
        return {
            "role":  "validated",
            "label": "Genomically validated disease gene",
            "icon":  "🟠",
            "color": "#FFA500",
            "note":  f"{n_pathogenic} confirmed pathogenic variants. Solid human genetic evidence.",
        }
    else:
        return {
            "role":  "critical_driver",
            "label": "Critical disease driver",
            "icon":  "🔴",
            "color": "#FF4C4C",
            "note":  f"{n_pathogenic} confirmed pathogenic variants. One of the most important disease genes in this category.",
        }


# ── Core papers ──────────────────────────────────────────────────────────────
PAPERS = {
    "king_2024": {
        "short":   "King et al., Nature 2024",
        "full":    "Refining the impact of genetic evidence on clinical success",
        "journal": "Nature",
        "year":    2024,
        "doi":     "10.1038/s41586-024-07316-0",
        "url":     "https://www.nature.com/articles/s41586-024-07316-0",
        "key_finding": (
            "Drug mechanisms with human genetic support are 2.6× more likely "
            "to succeed from clinical development to approval than those without."
        ),
        "quote": (
            "The probability of success for drug mechanisms with genetic support "
            "is 2.6 times greater than those without. Human genetics is one of "
            "the only forms of scientific evidence that can demonstrate the causal "
            "role of genes in human disease."
        ),
    },
    "minikel_2021": {
        "short":   "Minikel et al., Nature 2021",
        "full":    "Evaluating drug targets through human loss-of-function genetic variation",
        "journal": "Nature",
        "year":    2021,
        "doi":     "10.1038/s41586-020-2267-z",
        "url":     "https://www.nature.com/articles/s41586-020-2267-z",
        "key_finding": (
            "Analysis of 125,748 human exomes provides a roadmap for drug-target "
            "selection. Naturally occurring LOF variants are a direct in vivo model "
            "of human gene inactivation — more informative than mouse knockouts."
        ),
        "quote": (
            "Naturally occurring human genetic variants that are predicted to "
            "inactivate protein-coding genes provide an in vivo model of human "
            "gene inactivation that complements knockout studies in cells and "
            "model organisms."
        ),
    },
    "plenge_2016": {
        "short":   "Plenge et al., Nat Rev Drug Discov 2016",
        "full":    "Disciplined approach to drug discovery and early development",
        "journal": "Nature Reviews Drug Discovery",
        "year":    2016,
        "doi":     "10.1038/nrd.2016.29",
        "url":     "https://www.nature.com/articles/nrd.2016.29",
        "key_finding": (
            "Most clinical drug candidates fail for lack of efficacy. The target "
            "itself — not the drug — is too often not causally related to human disease. "
            "Candidates targeting genes with human genetic evidence are more likely "
            "to become approved drugs."
        ),
        "quote": (
            "Most drug candidates that enter clinical trials eventually fail for "
            "lack of efficacy, and while in vitro, cell culture and animal model "
            "systems can provide preclinical evidence that the compound engages "
            "its target, too often the target itself is not causally related to "
            "human disease."
        ),
    },
    "cook_2014": {
        "short":   "Cook et al., Nature Reviews Drug Discovery 2014",
        "full":    "Lessons learned from the fate of AstraZeneca's drug pipeline",
        "journal": "Nature Reviews Drug Discovery",
        "year":    2014,
        "doi":     "10.1038/nrd4309",
        "url":     "https://www.nature.com/articles/nrd4309",
        "key_finding": (
            "Only ~10% of drug candidates that enter clinical trials receive "
            "approval. 'Right target' failures — where the biology was wrong "
            "from the start — account for the majority of efficacy failures."
        ),
        "quote": (
            "Approximately 90% of drug candidates fail to progress through "
            "clinical trials because of issues with safety or efficacy. "
            "Drug side effects are more likely to occur in organ systems where "
            "there is genetic evidence of a link between the drug target and a "
            "phenotype involving that organ system."
        ),
    },
    "braxton_2023": {
        "short":   "Braxton et al., Human Genetics 2024",
        "full":    "Scalable approaches for generating, validating and incorporating data from high-throughput functional assays",
        "journal": "Human Genetics",
        "year":    2024,
        "doi":     "10.1007/s00439-024-02691-0",
        "url":     "https://pmc.ncbi.nlm.nih.gov/articles/PMC11303574/",
        "key_finding": (
            "Functional assay data can reclassify ~55% of Variants of Uncertain "
            "Significance when calibrated against ClinVar pathogenic and benign "
            "variants — but the calibration requires human genetic ground truth."
        ),
        "quote": (
            "Incorporating MAVE data into variant classification workflows allows "
            "reclassification of ~55% of VUS across well-studied genes, and can "
            "play a major role in reducing classification disparities."
        ),
    },
}


# ── Genomic validation tiers ─────────────────────────────────────────────────
TIER_DEFINITIONS = {
    "CRITICAL": {
        "label":       "Genomically Critical",
        "threshold":   0.50,   # DBR >= 0.50
        "icon":        "🔴",
        "color":       "#FF4C4C",
        "badge_color": "#FF4C4C",
        "description": (
            "This protein has an extremely high burden of disease-causing variants "
            "relative to its length. Every mutation here has a high probability of "
            "serious human consequence. Wet lab hits at this target are almost "
            "certainly real biology."
        ),
        "clinvar_verdict":   "Overwhelming pathogenic evidence in human populations.",
        "trust_statement":   "Hits here are genomically validated. Prioritise for immediate experimental follow-up.",
        "example_proteins":  ["FLNC (Filamin C)", "CHRM2 (Muscarinic receptor 2)", "BRCA1", "TP53"],
    },
    "HIGH": {
        "label":       "Genomically Supported",
        "threshold":   0.10,   # DBR >= 0.10
        "icon":        "🟠",
        "color":       "#FFA500",
        "badge_color": "#FFA500",
        "description": (
            "This protein has meaningful human genetic disease evidence. "
            "Pathogenic variants exist and cause recognisable disease. "
            "Wet lab hits here are likely to reflect real biology, though "
            "domain context matters."
        ),
        "clinvar_verdict":   "Moderate-to-strong pathogenic evidence in human populations.",
        "trust_statement":   "Hits here deserve validation. Cross-reference with domain location before committing.",
        "example_proteins":  ["EGFR", "KRAS", "MYH7"],
    },
    "LOW": {
        "label":       "Confirmed Rare Disease Gene",
        "threshold":   0.01,   # n_pathogenic > 0 but DBR < 0.10
        "icon":        "🟡",
        "color":       "#FFD700",
        "badge_color": "#c8a000",
        "description": (
            "Confirmed pathogenic variants exist in ClinVar — this protein DOES cause "
            "human disease. The low Disease Burden Ratio reflects the rarity of the "
            "disease, not the unimportance of the protein. Rare Mendelian disease genes "
            "will always have few ClinVar submissions simply because fewer patients exist. "
            "This is NOT the beta-arrestin pattern. Beta-arrestin has zero pathogenic "
            "variants. This protein has confirmed disease-causing mutations in humans."
        ),
        "clinvar_verdict":   "Confirmed pathogenic variants — rare Mendelian disease gene.",
        "trust_statement":   "Genuine disease gene. Pursue validation — especially if studying the confirmed disease. Low DBR reflects disease rarity, not protein dispensability.",
        "example_proteins":  ["CHRM3 (Prune belly syndrome)", "Rare metabolic disease genes", "Low-prevalence Mendelian disorder genes"],
    },
    "NONE": {
        "label":       "No Human Disease Evidence",
        "threshold":   0.0,    # n_pathogenic == 0
        "icon":        "⚪",
        "color":       "#888888",
        "badge_color": "#666666",
        "description": (
            "Zero confirmed pathogenic variants exist in ClinVar for this protein. "
            "This means no mutations in this gene have been shown to cause disease "
            "in a human being. This is the β-arrestin pattern: extensively studied "
            "in vitro, but humans who carry broken or absent versions are apparently "
            "healthy. Your wet lab signal may reflect a real molecular interaction, "
            "but it is NOT genomically validated as biologically essential. "
            "This is fundamentally different from a rare disease gene with few "
            "ClinVar submissions — those genes have confirmed cases. This protein "
            "has zero."
        ),
        "clinvar_verdict":   "Zero pathogenic variants confirmed in human populations.",
        "trust_statement":   (
            "No ClinVar pathogenic variants exist. Before committing resources, check: "
            "gnomAD pLI score, OMIM entry, and mouse KO phenotype. If all three are "
            "weak, you are likely studying a dispensable protein."
        ),
        "example_proteins":  ["ARRB1 (β-arrestin 1)", "ARRB2 (β-arrestin 2)", "TALN1 (Talin 1)", "Many scaffolding intermediates"],
    },
    "UNKNOWN": {
        "label":       "Genomically Uncharacterised",
        "threshold":   None,
        "icon":        "❓",
        "color":       "#4CA8FF",
        "badge_color": "#4CA8FF",
        "description": (
            "Insufficient ClinVar data exists to assess the genomic importance "
            "of this protein. This may mean it is understudied, the gene is novel, "
            "or sequencing coverage is incomplete. "
            "Proceed with standard wet lab validation while keeping the genomic "
            "question open."
        ),
        "clinvar_verdict":   "Insufficient human variant data to classify.",
        "trust_statement":   "Treat as unvalidated. Expand ClinVar submissions if possible.",
        "example_proteins":  ["Novel genes", "Recently discovered proteins"],
    },
}

# ── Experiment recommendations ───────────────────────────────────────────────
EXPERIMENT_LADDER = {
    "CRITICAL": [
        {
            "level":      1,
            "complexity": "Simple",
            "name":       "ClinVar / gnomAD cross-reference",
            "time":       "< 1 hour",
            "cost":       "Free",
            "tools":      "clinvar.ncbi.nlm.nih.gov, gnomad.broadinstitute.org",
            "purpose":    "Confirm the disease burden ratio and identify which specific variants cause which diseases.",
            "steps": [
                "Go to ClinVar and search your gene. Filter by 'Pathogenic' — note the count and the diseases.",
                "Go to gnomAD and check the pLI score (> 0.9 = highly constrained = likely essential).",
                "Check the LOEUF score (< 0.35 = strong intolerance to loss-of-function).",
                "Cross-reference your wet lab hit positions with known pathogenic ClinVar positions.",
            ],
            "expected_result": "Your hit positions overlap with known pathogenic variants → high confidence the signal is real.",
            "validates":  "That the protein is essential in humans AND that your specific positions matter.",
        },
        {
            "level":      2,
            "complexity": "Simple",
            "name":       "OpenTargets target-disease association check",
            "time":       "30 minutes",
            "cost":       "Free",
            "tools":      "platform.opentargets.org",
            "purpose":    "Map the protein across all diseases it is implicated in and identify the strongest genetic associations.",
            "steps": [
                "Search your gene at platform.opentargets.org.",
                "Filter by 'Genetic association' evidence — note the score for each disease.",
                "Click through to see tissue-specific expression and affected organ systems.",
                "Compare your assay context to the disease tissue — do they match?",
            ],
            "expected_result": "Strong genetic association score (> 0.7) in the disease context relevant to your assay.",
            "validates":  "Target-disease relevance before any bench work.",
        },
        {
            "level":      3,
            "complexity": "Moderate",
            "name":       "Thermal shift assay (DSF) — WT vs hit variants",
            "time":       "2–3 days",
            "cost":       "$300–800",
            "tools":      "qPCR machine, SYPRO Orange dye, purified protein",
            "purpose":    "Confirm that your top wet lab hits cause measurable thermodynamic destabilisation.",
            "steps": [
                "Express and purify wild-type protein and top 3 HIGH-priority variants.",
                "Run DSF with SYPRO Orange: heat 25°C → 95°C at 1°C/min.",
                "Calculate Tm for each variant. Expect ΔTm of -3 to -15°C for truly destabilising hits.",
                "Rank variants by ΔTm. Compare ranking to your triage score ranking.",
            ],
            "expected_result": "Triage score ranking correlates with ΔTm ranking (Spearman r > 0.7).",
            "validates":  "That your functional score predicts structural impact, not just assay artefact.",
        },
        {
            "level":      4,
            "complexity": "Rigorous",
            "name":       "Isothermal titration calorimetry (ITC)",
            "time":       "1–2 weeks",
            "cost":       "$1,500–4,000",
            "tools":      "ITC instrument (MicroCal/TA Instruments), purified protein, binding partner",
            "purpose":    "Gold-standard binding thermodynamics. Gives Kd, ΔH, ΔS, stoichiometry simultaneously. No fluorescent artefacts.",
            "steps": [
                "Prepare 50–100 µM purified protein in syringe and 5–10 µM binding partner in cell.",
                "Run 19 injections at 25°C. Collect full thermogram.",
                "Fit one-site binding model to extract Kd, n (stoichiometry), ΔH.",
                "Compare Kd between WT and your top variants. Expect 10–1000× affinity loss for real disrupting variants.",
                "Run the same experiment for a LOW-priority variant from the same protein as internal control.",
            ],
            "expected_result": "HIGH-priority variants show Kd shift > 10×. LOW-priority variants show < 2× shift.",
            "validates":  "Direct causal link between your triage score and binding disruption — no indirect readout.",
        },
        {
            "level":      5,
            "complexity": "Definitive",
            "name":       "Prospective validation — blinded orthogonal assay",
            "time":       "3–6 months",
            "cost":       "$5,000–20,000",
            "tools":      "Cell-based reporter, collaborating lab (ideally independent)",
            "purpose":    "Prospective test of whether the Disease Burden Ratio predicts validation success better than functional score alone.",
            "steps": [
                "Score a new dataset through Protellect. Separate hits into: (A) HIGH functional + HIGH genomic, (B) HIGH functional + LOW genomic.",
                "Send group A and B to a collaborating lab without revealing which is which.",
                "Have them validate with an orthogonal assay (reporter, cell phenotype, binding).",
                "Unmask groups. Calculate validation rate for A vs B.",
                "If A validates at > 2× the rate of B, publish the comparison.",
            ],
            "expected_result": "Group A (genomically validated) validates at > 2× the rate of Group B.",
            "validates":  "The entire Protellect methodology. This is the publishable proof point.",
        },
    ],
    "HIGH": [
        {
            "level":      1,
            "complexity": "Simple",
            "name":       "ClinVar domain overlap check",
            "time":       "< 1 hour",
            "cost":       "Free",
            "tools":      "ClinVar, UniProt domain viewer",
            "purpose":    "Check whether your hit positions overlap with known pathogenic positions in the same domain.",
            "steps": [
                "Pull ClinVar pathogenic variants for your gene. Export as CSV.",
                "Map your top 5 hits onto the same position axis.",
                "Check whether hits cluster in the same domain as known pathogenic variants.",
            ],
            "expected_result": "Hit positions cluster with known pathogenic positions in the same domain.",
            "validates":  "Domain-level relevance of your specific experimental hits.",
        },
        {
            "level":      2,
            "complexity": "Moderate",
            "name":       "Thermal shift — confirmation of signal",
            "time":       "2–3 days",
            "cost":       "$300–600",
            "tools":      "DSF / SYPRO Orange",
            "purpose":    "Confirm destabilisation for top hits before committing to expensive assays.",
            "steps": [
                "Prioritise variants that overlap ClinVar pathogenic positions.",
                "Run DSF on these specific variants vs WT.",
                "Only proceed to ITC for variants showing ΔTm > 3°C.",
            ],
            "expected_result": "Variants in known pathogenic positions show ΔTm > 3°C.",
            "validates":  "That ClinVar-overlapping hits are structurally meaningful.",
        },
        {
            "level":      3,
            "complexity": "Rigorous",
            "name":       "ITC binding confirmation",
            "time":       "1–2 weeks",
            "cost":       "$1,500–3,500",
            "tools":      "ITC instrument",
            "purpose":    "Confirm binding disruption for the highest-confidence hits.",
            "steps": [
                "Shortlist variants with: HIGH triage score + ClinVar overlap + ΔTm > 3°C.",
                "Run ITC on these variants. Expect Kd shift > 10× for real disrupting hits.",
                "Include one LOW-priority variant as internal control — expect < 2× Kd shift.",
            ],
            "expected_result": "ITC confirms binding disruption for ClinVar-overlapping variants.",
            "validates":  "Combined evidence from triage + genomic + structural → binding disruption.",
        },
    ],
    "LOW": [
        {
            "level":      1,
            "complexity": "Simple",
            "name":       "Literature and database check — before any bench work",
            "time":       "2–4 hours",
            "cost":       "Free",
            "tools":      "ClinVar, gnomAD, OMIM, PubMed",
            "purpose":    "Determine whether the weak genomic signal is due to the protein being truly dispensable or simply understudied.",
            "steps": [
                "Check gnomAD pLI. If > 0.9 despite few ClinVar entries, the gene may be essential but undersequenced.",
                "Check OMIM — is there any Mendelian disease listed? If yes, ClinVar may just lag behind.",
                "PubMed: search for mouse knockout phenotype. Does KO mouse die or show strong phenotype?",
                "If mouse KO is severe but no human disease: the protein may matter but human compensation exists.",
            ],
            "expected_result": "Clear categorisation: truly dispensable, understudied, or human-mouse discordant.",
            "validates":  "Whether the low genomic score reflects biology or data gaps.",
        },
        {
            "level":      2,
            "complexity": "Moderate",
            "name":       "Thermal shift with WT and positive control",
            "time":       "2–3 days",
            "cost":       "$300–600",
            "tools":      "DSF",
            "purpose":    "Check whether your hit variants cause any measurable destabilisation at all.",
            "steps": [
                "Include a known ClinVar pathogenic variant from a related protein as positive control.",
                "Compare your hit variants to this positive control.",
                "If your hits show less ΔTm than the positive control, reconsider their priority.",
            ],
            "expected_result": "Compare destabilisation magnitude to a genomically validated positive control.",
            "validates":  "Relative importance of your hit compared to a known disease-causing variant.",
        },
    ],
    "NONE": [
        {
            "level":      1,
            "complexity": "Simple — do this BEFORE any bench work",
            "name":       "The β-arrestin test — is this protein dispensable?",
            "time":       "1–2 hours",
            "cost":       "Free",
            "tools":      "ClinVar, gnomAD, UniProt",
            "purpose":    "Determine whether human populations tolerate complete loss of this protein — if so, your hit is probably not disease-relevant.",
            "steps": [
                "gnomAD: search your gene. Check pLI score. If pLI < 0.1, humans tolerate LOF variants — protein likely dispensable.",
                "gnomAD: check observed/expected ratio. If close to 1.0, variants are not depleted — protein is tolerated.",
                "ClinVar: confirm < 5 pathogenic submissions. Check if any are linked to serious Mendelian disease.",
                "UniProt: read the function section. Is this a scaffolding / adaptor protein? These are often dispensable.",
                "Decision: if pLI < 0.1, OE ratio > 0.5, and < 5 ClinVar pathogenic — apply extreme caution to your hit.",
            ],
            "expected_result": "Clear answer: is this protein genomically dispensable or just undersequenced?",
            "validates":  "Whether it is worth running ANY experiments on this target.",
        },
        {
            "level":      2,
            "complexity": "Moderate — only if step 1 passes",
            "name":       "Paired assay: essential protein vs your protein",
            "time":       "1 week",
            "cost":       "$500–1,500",
            "tools":      "Same assay as your original wet lab experiment",
            "purpose":    "Run your assay simultaneously on your low-genomic protein AND a genomically critical protein (e.g. FLNC or BRCA1 variant as positive control). Compare magnitudes.",
            "steps": [
                "Select a variant in a genomically critical protein (ClinVar pathogenic, pLI > 0.9).",
                "Run it through your exact same assay under identical conditions.",
                "Compare: how does the effect size of your low-genomic hit compare to the known essential hit?",
                "If your hit shows > 50% of the effect of the essential positive control, it may still be worth pursuing.",
            ],
            "expected_result": "Calibrates your assay signal in absolute terms relative to known biology.",
            "validates":  "Whether your assay is even sensitive enough to detect real effects in this system.",
        },
    ],
    "UNKNOWN": [
        {
            "level":      1,
            "complexity": "Simple",
            "name":       "Establish the genomic baseline first",
            "time":       "1–2 hours",
            "cost":       "Free",
            "tools":      "ClinVar, gnomAD, OMIM, OpenTargets",
            "purpose":    "Before validating your hit, establish whether human genetics agrees this protein matters.",
            "steps": [
                "Run your gene through OpenTargets — any disease associations at all?",
                "gnomAD: get the constraint metrics (pLI, LOEUF) even if ClinVar is empty.",
                "OMIM: check for any Mendelian disease linkage regardless of ClinVar submission count.",
                "If all three are empty: you are working on a novel target with no human genetic validation yet. Proceed with caution but also with opportunity.",
            ],
            "expected_result": "Either: this is genuinely unstudied (real opportunity) or the data exists elsewhere (look harder).",
            "validates":  "Whether the lack of data is absence of evidence or evidence of absence.",
        },
    ],
}


# ── Core calculation functions ────────────────────────────────────────────────

def calculate_dbr(n_pathogenic: int, protein_length: int) -> Optional[float]:
    """
    Disease Burden Ratio = ClinVar pathogenic submissions / protein length.
    Higher = more evidence that mutations here matter in humans.
    
    Key reference points:
      FLNC (Filamin C): ~4300 / 2725 = 1.58  → CRITICAL
      CHRM2:            ~102  / 466  = 0.22  → HIGH
      BRCA1:            ~6000 / 1863 = 3.22  → CRITICAL
      β-arrestin 1:     ~12   / 418  = 0.03  → LOW/NONE
      Talin 1:          ~5    / 2541 = 0.002 → NONE
    """
    if not protein_length or protein_length == 0:
        return None
    return round(n_pathogenic / protein_length, 4)


def assign_genomic_tier(dbr: Optional[float], n_pathogenic: int) -> str:
    """
    Assign a genomic validation tier from the Disease Burden Ratio.

    CRITICAL RULE: NONE tier only applies when n_pathogenic == 0.
    Even a single confirmed pathogenic variant means the protein causes real disease.
    Small pathogenic counts with low DBR = RARE Mendelian disease, NOT dispensable protein.
    The beta-arrestin pattern is specifically zero pathogenic variants — not few.
    """
    if dbr is None or n_pathogenic is None:
        return "UNKNOWN"
    # NONE only when absolutely zero pathogenic evidence in ClinVar
    if n_pathogenic == 0:
        return "NONE"
    # Any confirmed pathogenic variants = at minimum LOW
    if dbr >= TIER_DEFINITIONS["CRITICAL"]["threshold"]:
        return "CRITICAL"
    elif dbr >= TIER_DEFINITIONS["HIGH"]["threshold"]:
        return "HIGH"
    else:
        # n_pathogenic > 0 but low DBR = rare Mendelian disease with few submissions
        return "LOW"


def get_genomic_verdict(tier: str, protein_name: str = "", n_pathogenic: int = 0,
                        protein_length: int = 0, dbr: Optional[float] = None) -> dict:
    """
    Build a full genomic verdict dict for display.
    """
    t = TIER_DEFINITIONS.get(tier, TIER_DEFINITIONS["UNKNOWN"])
    dbr_str = f"{dbr:.3f}" if dbr is not None else "N/A"

    # Select most relevant papers for this tier
    if tier == "CRITICAL":
        papers = [PAPERS["king_2024"], PAPERS["minikel_2021"]]
    elif tier == "HIGH":
        papers = [PAPERS["king_2024"], PAPERS["plenge_2016"]]
    elif tier in ("LOW", "NONE"):
        papers = [PAPERS["plenge_2016"], PAPERS["cook_2014"]]
    else:
        papers = [PAPERS["braxton_2023"]]

    return {
        "tier":             tier,
        "label":            t["label"],
        "icon":             t["icon"],
        "color":            t["color"],
        "badge_color":      t["badge_color"],
        "description":      t["description"],
        "clinvar_verdict":  t["clinvar_verdict"],
        "trust_statement":  t["trust_statement"],
        "example_proteins": t["example_proteins"],
        "dbr":              dbr,
        "dbr_str":          dbr_str,
        "n_pathogenic":     n_pathogenic,
        "protein_length":   protein_length,
        "papers":           papers,
        "experiments":      EXPERIMENT_LADDER.get(tier, EXPERIMENT_LADDER["UNKNOWN"]),
    }


def enrich_scored_df(scored_df, enrichment: dict = None):
    """
    Add genomic validation columns to scored DataFrame.
    Uses ClinVar data from enrichment if available.
    """
    import pandas as pd

    if scored_df is None or len(scored_df) == 0:
        return scored_df

    scored_df = scored_df.copy()

    # Get protein-level genomic data from enrichment
    n_pathogenic   = 0
    protein_length = 0
    gene_name      = ""

    if enrichment:
        clinvar       = enrichment.get("clinvar", {})
        uniprot       = enrichment.get("uniprot", {})
        gene_name     = enrichment.get("gene_name", "")
        protein_length = uniprot.get("length", 0)

        # Count all pathogenic ClinVar entries across all positions
        for pos, variants in clinvar.items():
            for v in variants:
                sig = v.get("significance", "").lower()
                if "pathogenic" in sig and "likely benign" not in sig and "benign" not in sig:
                    n_pathogenic += 1

    dbr  = calculate_dbr(n_pathogenic, protein_length)
    tier = assign_genomic_tier(dbr, n_pathogenic)

    # Add to dataframe
    scored_df["genomic_tier"]      = tier
    scored_df["disease_burden_ratio"] = dbr
    scored_df["n_pathogenic_clinvar"] = n_pathogenic
    scored_df["protein_length_aa"]    = protein_length

    return scored_df


def get_paper_citation_html(paper: dict, style: str = "inline") -> str:
    """Format a paper citation for HTML display."""
    return (
        f'<a href="{paper["url"]}" target="_blank" '
        f'style="color:#4CA8FF;text-decoration:none;font-size:0.75rem">'
        f'{paper["short"]}</a>'
    )


def format_experiments_html(experiments: list, max_show: int = 3) -> str:
    """Format experiment ladder as HTML for display."""
    colors = {"Simple":"#4CAF50", "Moderate":"#FFA500", "Rigorous":"#FF8C00", "Definitive":"#FF4C4C"}
    out = []
    for exp in experiments[:max_show]:
        c = colors.get(exp["complexity"].split(" — ")[0], "#888")
        out.append(f"""
        <div style="background:#080b14;border:1px solid #1e2030;border-radius:8px;
                    padding:12px 14px;margin-bottom:8px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <span style="font-family:IBM Plex Mono,monospace;font-size:0.72rem;
                         color:{c};font-weight:600">Level {exp['level']} — {exp['complexity']}</span>
            <span style="font-size:0.7rem;color:#555">{exp['time']} · {exp['cost']}</span>
          </div>
          <div style="font-weight:600;color:#eee;font-size:0.85rem;margin-bottom:4px">{exp['name']}</div>
          <div style="font-size:0.78rem;color:#888;margin-bottom:8px;line-height:1.6">{exp['purpose']}</div>
          <div style="font-size:0.73rem;color:#4CAF50;font-family:IBM Plex Mono,monospace;margin-bottom:4px">
            Expected: {exp['expected_result']}
          </div>
          <div style="font-size:0.7rem;color:#555">Validates: {exp['validates']}</div>
        </div>""")
    return "\n".join(out)
