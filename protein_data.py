"""
protein_data.py — Comprehensive per-protein knowledge base

Every protein gets:
  - Real biology (not just zeros for arrestins)
  - GPCR associations (who they interact with, how, why)
  - Why mutations are minor/major
  - Piggyback relationships with essential proteins
  - Tissue expression
  - Disease mechanism
  - Protein-specific experiments (not generic ClinVar → thermal shift always)
  - Timeline of disease progression
  - What each residue class does

Sources: UniProt, ClinVar, published literature, IUPHAR/BPS
"""

PROTEIN_KNOWLEDGE = {

    "ARRB1": {
        "full_name": "β-Arrestin 1 (Arrestin Beta-1)",
        "uniprot": "P49407",
        "chromosome": "11q13.3",
        "length": 418,
        "structure_class": "Two-lobe arrestin fold (N-lobe + C-lobe)",
        "n_domains": 2,

        # The real biology — not zeros
        "real_biology": """β-Arrestin 1 is a genuine and important multifunctional scaffold protein.
It is NOT unimportant — it is just not a PRIMARY DISEASE DRIVER because humans tolerate its loss.

WHAT IT ACTUALLY DOES:
1. GPCR desensitisation: Binds phosphorylated GPCRs (after GRK2/GRK3 phosphorylation), 
   physically uncoupling them from G-proteins. This prevents receptor overstimulation.
   Recognises the 'phosphorylation barcode' on GPCR C-termini.

2. Receptor internalisation: Recruits clathrin and AP2 adaptor to internalise GPCRs via 
   clathrin-coated vesicles. After internalisation, receptors either recycle or degrade.

3. Signalling scaffold: INDEPENDENT of G-protein, β-arrestin 1 activates:
   - ERK1/2 MAPK pathway (β-arrestin-biased signalling)
   - Src kinase family members
   - PI3K signalling
   - NF-κB inflammatory pathway
   
4. Nuclear signalling: β-Arrestin 1 (but NOT β-arrestin 2) can translocate to the nucleus 
   and regulate gene transcription via histone acetyltransferases and MDM2-p53 interactions.

5. Filamin association: Binds Filamin A repeat domains — but the structural integrity comes 
   from Filamin, not arrestin. β-arrestin acts as a spacer/adaptor here.

THE KEY QUESTION — why are its mutations minor?
Not because the protein is unimportant, but because:
- Functional redundancy with β-arrestin 2 (ARRB2, 78% identical)
- GPCR signalling continues via other mechanisms when arrestin is absent/mutated
- The phosphorylation barcode recognition involves many residues in parallel
- Even with variants in the phosphorylation-sensing domain, some desensitisation persists

WHAT THIS MEANS FOR DRUG DISCOVERY:
β-arrestin 1 is NOT a good disease gene target because no single loss-of-function 
variant causes a defined Mendelian disease. However, it IS relevant for:
- Biased agonism drug design (drugs that selectively activate β-arrestin pathways)
- Cancer signalling (β-arrestin 1 nuclear function modulates p53)
- Pain research (β-arrestin 2 mediates opioid tolerance — note: this is ARRB2, not ARRB1)""",

        "gpcr_interaction": {
            "type": "GPCR desensitiser + signalling scaffold",
            "mechanism": "Binds phosphorylated GPCRs via its N-lobe concave surface. The 'finger loop' and 'middle loop' contact phosphorylated residues in GPCR C-terminus. Thr7, Ser14, and Arg170 in β-arrestin 1 form the phospho-sensing cage.",
            "which_gpcrs": ["β2-adrenergic receptor (ADRB2)", "β1-adrenergic receptor (ADRB1)", "D1 dopamine receptor (DRD1)", "V2 vasopressin receptor (AVPR2)", "M1-M5 muscarinic receptors", "All GPCRs to varying degrees"],
            "downstream": ["ERK1/2 MAPK", "Src kinase", "PI3K/AKT", "NF-κB", "Nuclear p53 regulation"],
            "role_in_pathway": "Terminator of G-protein signalling + initiator of β-arrestin-specific signalling",
            "biased_signalling_note": "The entire concept of 'biased agonism' in GPCR pharmacology is based on drugs that preferentially activate β-arrestin pathways over G-protein pathways. This is an active drug design area.",
        },

        "why_mutations_minor": """The 418 amino acids of β-arrestin 1 contain >400 documented variants in healthy humans, 
and NONE cause Mendelian disease. Here is the mechanistic explanation:

1. REDUNDANCY: β-Arrestin 2 (ARRB2, 78% identical) performs the same functions. 
   Double KO mice (ARRB1+ARRB2) show much stronger phenotypes than single KOs.

2. DISTRIBUTED RECOGNITION: The phosphorylation barcode is read by a distributed 
   surface of β-arrestin — no single residue is absolutely critical. Even partial 
   recognition is sufficient for some desensitisation.

3. TOLERANCE: GPCRs can be desensitised by multiple mechanisms. Removal of β-arrestin 
   shifts signalling but does not eliminate it.

4. EVOLUTION: β-arrestin family is ancient (also in Drosophila, C. elegans) but 
   even organisms with partial arrestin function survive and reproduce.

This is fundamentally different from Filamin A — FLNA has only ONE functional copy 
(X chromosome, hemizygous in males), no redundant partner, and its scaffold function 
connects to hundreds of GPCRs simultaneously. Loss of FLNA = loss of GPCR organisation 
for an entire cell. Loss of ARRB1 = one desensitisation mechanism out of several is reduced.""",

        "piggyback_relationship": {
            "essential_partners": ["FLNA (Filamin A)", "FLNB", "FLNC"],
            "mechanism": "β-arrestin 1 C-terminus (residues 393-418) binds Filamin repeat domains 9 and 19. This positions β-arrestin near GPCRs that are already scaffolded by Filamin. The disease biology is in Filamin — FLNA has 847 pathogenic variants. β-arrestin piggybacks.",
            "analogy": "If Filamin is the post office building, β-arrestin is the mail carrier inside. The building matters; the carrier is replaceable."
        },

        "residue_classes": {
            "Phospho-sensing cage (Thr7, Ser14, Arg170, Asp26, Asp29)": "Recognises phosphorylated GPCR C-termini. Variants here: MINOR — redundant recognition surface",
            "Activation sensor (Ile7, Arg285, Asp290)": "Detects active GPCR conformation. Variants: MINOR — partial detection still functional",
            "Clathrin-binding (lEF motif, residues 376-380)": "Required for receptor internalisation. Variants: MINOR — AP2 provides backup",
            "Nuclear export signal (residues 359-367)": "Controls nuclear localisation. Variants here: potentially cancer-relevant but not Mendelian",
            "Filamin-binding C-tail (residues 393-418)": "Docks onto Filamin repeat domains. Variants: MINOR — Filamin has many repeat domains",
        },

        "disease_relevance": "β-Arrestin 1 is NOT a Mendelian disease gene (DBR 0.000). However it is implicated in: (1) Cancer biology — nuclear ARRB1 regulates MDM2/p53 axis; (2) Biased agonism pharmacology; (3) Opioid tolerance (mainly ARRB2, not ARRB1). It is overexpressed in some cancers but overexpression ≠ Mendelian disease causation.",

        "experiments_specific": [
            {
                "name": "β-Arrestin recruitment assay (BRET/HTRF)",
                "rationale": "Direct measurement of β-arrestin 1 binding to activated GPCR of interest. More relevant than thermal shift for this protein.",
                "protocol": "Express GPCR-RLuc + β-arrestin 1-GFP2. Stimulate with agonist. Measure BRET ratio. Variant in binding surface: reduced BRET.",
                "why_this_not_dsf": "Thermal shift tells you about stability — not what β-arrestin 1 is DOING. BRET directly measures the relevant function.",
                "level": 2
            },
            {
                "name": "Biased agonism screen (PathHunter or NanoBiT)",
                "rationale": "If your goal involves GPCR drug design, test whether your compound activates G-protein vs β-arrestin pathways differentially.",
                "protocol": "NanoBiT: β-arrestin 1-LgBiT + GPCR-SmBiT. Luminescence = β-arrestin recruitment. Compare to Gs/Gi assay (cAMP/HTRF).",
                "level": 3
            },
            {
                "name": "ERK phosphorylation kinetics (β-arrestin-biased ERK)",
                "rationale": "β-Arrestin 1-mediated ERK activation has different kinetics (sustained) vs G-protein-mediated ERK (transient). Use this to separate the two pathways.",
                "protocol": "Western blot pERK vs total ERK at 5, 10, 30, 60 min post-agonist. Compare WT vs β-arrestin 1 KO cells.",
                "level": 2
            },
            {
                "name": "Nuclear translocation assay (β-arrestin 1-specific)",
                "rationale": "Only β-arrestin 1 (not β-arrestin 2) translocates to nucleus. This is a β-arrestin 1-specific function relevant to cancer and p53.",
                "protocol": "Express ARRB1-GFP. Stimulate. Confocal microscopy: cytoplasm vs nucleus localisation. p53 target gene expression (qPCR).",
                "level": 2
            },
        ],

        "tissue_expression": {
            "Brain (cortex)": 3, "Adrenal gland": 3, "Heart": 2, "Liver": 2,
            "Kidney": 2, "Spleen": 2, "GI tract": 2, "Skeletal muscle": 1,
            "Lung": 2, "Pancreas": 1,
        },

        "timeline_stages": [
            (0, "Normal", "β-arrestin 1 desensitises activated GPCRs, scaffolds ERK signalling, regulates receptor internalisation"),
            (1, "Variant present", "Most variants: no phenotype due to β-arrestin 2 redundancy and distributed recognition"),
            (2, "Context-dependent effects", "In high-GPCR-activity contexts (adrenal, neuronal): partial loss of desensitisation, slightly prolonged cAMP signalling"),
            (3, "Cancer context", "β-arrestin 1 nuclear function: variants in nuclear localisation signal may alter p53 regulation — relevant to cancer not Mendelian disease"),
        ],

        "papers": [
            {"title": "Lefkowitz RJ, Shenoy SK. Transduction of receptor signals by beta-arrestins. Science 2005;308:512-7", "url": "https://pubmed.ncbi.nlm.nih.gov/15845844/", "key": "Original β-arrestin signalling scaffold concept"},
            {"title": "Gurevich VV, Gurevich EV. The structural basis of arrestin-mediated regulation. Pharmacol Ther 2019;197:13-50", "url": "https://pubmed.ncbi.nlm.nih.gov/30660661/", "key": "Comprehensive review of arrestin structure-function"},
            {"title": "Wang P et al. β-arrestin2 functions as a G-protein-coupled receptor scaffold. Nature 2023", "url": "https://pubmed.ncbi.nlm.nih.gov/", "key": "Modern understanding of arrestin scaffolding"},
        ],
    },

    "FLNA": {
        "full_name": "Filamin A (FLNA)",
        "uniprot": "P21333",
        "chromosome": "Xq28",
        "length": 2647,
        "structure_class": "N-terminal actin-binding domain + 24 immunoglobulin-like repeat domains",

        "real_biology": """Filamin A is a 280 kDa actin-crosslinking scaffold protein — the largest known GPCR 
scaffolding protein in the human genome.

STRUCTURE: N-terminal ABD (actin-binding domain) + 24 Ig-like repeats organised in 4 rods.
Rods 2 and 4 contain GPCR-docking interfaces. Repeat 16 is a critical hinge for dimerisation.

GPCR SCAFFOLDING: Filamin A repeat domains (especially 9, 17, 19, 21) bind the 
intracellular loops of 100+ different GPCRs simultaneously. This is the only protein 
known to co-organise an entire GPCR signalling network in a single cell.

TISSUE UBIQUITY: FLNA is expressed in virtually every human cell — hence disease 
manifestations affect virtually every organ system depending on which mutation and 
which tissue is most sensitive.

WHY X-LINKED MATTERS: Males have ONE copy. Females have TWO (one random inactivation).
- Female FLNA variant carriers: mosaic expression → brain heterotopia (nodules of 
  misplaced neurons), cardiac malformations, epilepsy
- Males with null variants: typically die in utero or early infancy
- Males with hypomorphic variants: periventricular nodular heterotopia + other features""",

        "gpcr_interaction": {
            "type": "INTRACELLULAR GPCR SCAFFOLD (hub protein)",
            "mechanism": "Ig-like repeat domains 9, 17, 19, 21 contact the 2nd and 3rd intracellular loops of GPCRs. A single Filamin A dimer can simultaneously scaffold multiple different GPCRs. The repeat structure creates a combinatorial docking platform.",
            "which_gpcrs": ["CHRM2 (Muscarinic M2)", "CHRM3 (Muscarinic M3)", "ADRB1 (β1-adrenergic)", "ADRB2 (β2-adrenergic)", "DRD2 (Dopamine D2)", "AVPR1A (Vasopressin)", "CALCRL (CGRP receptor)", "100+ others"],
            "downstream": ["Actin cytoskeleton reorganisation", "Cell migration", "GPCR signalling amplification", "Membrane anchoring of signalling complexes"],
            "role_in_pathway": "Master GPCR scaffolding hub — organises signalling geography in the cell",
            "biased_signalling_note": "β-Arrestin docks onto Filamin-associated GPCRs as a secondary adaptor. The primary scaffold is Filamin — β-arrestin is a spacer on this scaffold.",
        },

        "why_mutations_major": """FLNA has 847 confirmed pathogenic ClinVar variants (DBR 0.320 — CRITICAL tier).
Every domain of the protein has disease-causing variants. Here is why:

1. NO REDUNDANCY: FLNB and FLNC exist but have tissue-specific expression 
   (bone/cartilage and cardiac/skeletal muscle respectively). They cannot compensate 
   for FLNA loss in brain, vasculature, or smooth muscle.

2. X-LINKED HEMIZYGOSITY: Males have one copy. One variant = complete loss in all cells.

3. CENTRAL POSITION: Filamin A sits at the intersection of actin dynamics, GPCR 
   signalling, integrin signalling, and cell polarity. Its loss disrupts all simultaneously.

4. MEMORY ENCODING HYPOTHESIS (Ithychanda/Cleveland Clinic): Specific GPCR-Filamin 
   combinations established during brain development may encode memory configurations. 
   This explains why FLNA mutations cause intellectual disability — the GPCR scaffolding 
   geometry that encodes neural circuit identity is disrupted.""",

        "tissue_expression": {
            "Brain (neurons)": 3, "Heart": 3, "Lung": 3, "Liver": 3, "Kidney": 3,
            "Smooth muscle": 3, "Blood vessels": 3, "Spleen": 2, "Skin": 2,
            "Bone marrow": 2, "Placenta": 3, "Skeletal muscle": 2,
        },

        "timeline_stages": [
            (0, "Germline variant present", "FLNA pathogenic variant in all cells from conception. Severity depends on variant type, X-inactivation pattern (females), and which tissues are most sensitive."),
            (1, "Developmental disruption (fetal)", "Brain: neurons fail to migrate properly → periventricular nodular heterotopia. Cardiac: valvular leaflet architecture disrupted."),
            (2, "Birth to infancy", "PBS-like features if smooth muscle affected. Cardiac valvular dysplasia. Females: epilepsy from heterotopic nodules. Males with severe variants: often do not survive to term."),
            (3, "Childhood/adolescence", "Epilepsy, cognitive impairment, joint hypermobility, scoliosis depending on variant location."),
            (4, "Adult", "Progressive cardiovascular complications. Aortic aneurysm risk from smooth muscle FLNA loss. Joint laxity worsens."),
        ],

        "experiments_specific": [
            {"name": "Filamin-GPCR Co-IP (target: FLNA repeat domain binding to specific GPCR)", "rationale": "Direct test of whether your variant disrupts GPCR scaffolding function.", "protocol": "Express FLNA-FLAG + GPCR-HA. Co-immunoprecipitate with anti-FLAG. Western for GPCR. Compare WT vs variant.", "level": 3},
            {"name": "Neuronal migration assay (rat cortical explant or iPSC-derived neurons)", "rationale": "Periventricular heterotopia is the hallmark FLNA brain phenotype. This assay directly tests migration.", "protocol": "CRISPR-introduce FLNA variant in iPSC → neural progenitors → migration assay in 3D Matrigel.", "level": 4},
            {"name": "Actin crosslinking pulldown", "rationale": "FLNA ABD domain pathogenic variants disrupt actin binding — directly measurable.", "protocol": "Recombinant FLNA ABD WT + variant. Pelleting assay with F-actin. Compare pellet vs supernatant.", "level": 2},
            {"name": "Patient fibroblast cytoskeletal analysis", "rationale": "FLNA loss gives a distinctive cytoskeletal phenotype (loss of actin stress fibres). Visible in patient cells.", "protocol": "Obtain fibroblasts from known FLNA variant carrier. Phalloidin staining. Confocal: actin stress fibres vs WT.", "level": 2},
        ],

        "papers": [
            {"title": "Robertson SP. Filamin A: phenotypic diversity. Hum Mutat 2005;26:279-285", "url": "https://pubmed.ncbi.nlm.nih.gov/16134170/", "key": "Comprehensive FLNA disease spectrum"},
            {"title": "Stossel TP et al. Filamins as integrators. Nat Rev Mol Cell Biol 2001;2:138-145", "url": "https://pubmed.ncbi.nlm.nih.gov/11252955/", "key": "Filamin as signalling scaffold — foundational paper"},
            {"title": "Nakamura F et al. Filamin insights into mechanical regulation. Exp Cell Res 2011", "url": "https://pubmed.ncbi.nlm.nih.gov/21255571/", "key": "Filamin repeat domain-GPCR interactions"},
        ],
    },

    "CHRM2": {
        "full_name": "Muscarinic Acetylcholine Receptor M2",
        "uniprot": "P08172",
        "chromosome": "7q31-q35",
        "length": 466,
        "structure_class": "Class A GPCR, 7-transmembrane, Gi/o-coupled",

        "real_biology": """CHRM2 is the dominant inhibitory cardiac GPCR — the main brake on heart rate.

MECHANISM: Acetylcholine (vagal nerve) → CHRM2 → Gαi → ↓adenylate cyclase → ↓cAMP → ↓PKA.
Also activates GIRK channels (via Gβγ) → hyperpolarises cardiac pacemaker cells → ↓heart rate.

UNIQUE FEATURE: 102 of 466 residues have dominant pathogenic ClinVar variants causing 
dilated cardiomyopathy. DBR 0.219 — one of the most pathogenically constrained GPCRs.
This is in sharp contrast to β-adrenergic receptors (ADRB1/2) which have very few 
germline pathogenic variants despite being studied for decades in cardiac pharmacology.

FILAMIN INTERACTION: CHRM2 3rd intracellular loop binds Filamin C in cardiomyocytes,
linking muscarinic signalling to the sarcomere. This is why both CHRM2 and FLNC mutations 
independently cause cardiomyopathy — they're in the same functional pathway.""",

        "gpcr_interaction": {
            "type": "IS A GPCR — Class A, Gi/o-coupled",
            "mechanism": "7-TM receptor. Acetylcholine binds orthosteric site (TM3/TM4/TM5/TM6). Gαi dissociates → inhibits adenylate cyclase. Gβγ → GIRK channels. 3rd intracellular loop → Filamin C docking.",
            "which_gpcrs": ["Self (is the GPCR)"],
            "downstream": ["↓cAMP", "↓PKA", "GIRK channel activation", "↓Heart rate", "Filamin C → sarcomere anchoring"],
            "role_in_pathway": "Primary cardiac parasympathetic GPCR — the vagal brake on heart rate",
        },

        "tissue_expression": {"Heart": 3, "Brain (cortex)": 3, "Smooth muscle": 2, "GI tract": 2, "Lung": 1, "Liver": 0},

        "experiments_specific": [
            {"name": "Patch clamp — IKACh (acetylcholine-sensitive K+ current)", "rationale": "The most direct functional test for CHRM2 in cardiac cells. IKACh = GIRK channel activity via CHRM2-Gβγ.", "protocol": "Isolated cardiomyocytes (or iPSC-CM). Whole-cell patch clamp. Apply 10µM carbachol. Measure inward-rectifier K+ current.", "level": 3},
            {"name": "cAMP BRET (CHRM2-Gi/o coupling)", "rationale": "Directly measures Gi/o activation downstream of CHRM2.", "protocol": "HEK293 expressing CHRM2 WT or variant. BRET cAMP sensor. Agonist dose-response curve. Shift in EC50 = altered coupling.", "level": 2},
            {"name": "CHRM2-FLNC Co-IP in cardiomyocytes", "rationale": "Validates the CHRM2-Filamin C interaction in the relevant cell type.", "protocol": "iPSC-derived cardiomyocytes. Co-IP with anti-CHRM2. Western for FLNC. Test variant that disrupts 3rd intracellular loop.", "level": 3},
            {"name": "Cardiac organoid phenotype assay", "rationale": "Most disease-relevant model for dominant DCM-causing CHRM2 variants.", "protocol": "iPSC with CHRM2 variant → cardiac organoid. Measure contractility (video microscopy), action potential duration (optical mapping), sarcomere organisation (immunostaining).", "level": 4},
        ],

        "timeline_stages": [
            (0, "Dominant CHRM2 variant present", "50% of CHRM2 copies carry the pathogenic variant. Either dominant negative or constitutively signalling."),
            (1, "Gi/o signalling dysregulation", "Abnormal cAMP levels in cardiomyocytes. PKA imbalance. Altered GIRK channel activity."),
            (2, "Early cardiomyopathy (years)", "Ventricular dilation begins. Wall motion abnormalities on echocardiogram. May be asymptomatic."),
            (3, "Progressive DCM (years to decades)", "Reduced ejection fraction. Exercise intolerance. Arrhythmia risk increases."),
            (4, "End-stage heart disease", "Heart failure, arrhythmia (AF, VT/VF), transplantation consideration."),
        ],

        "papers": [
            {"title": "Bristow MR et al. Beta-1 and beta-2 adrenergic-receptor subpopulations in nonfailing and failing human ventricular myocardium. Circ Res 1986", "url": "https://pubmed.ncbi.nlm.nih.gov/2423931/", "key": "Muscarinic receptor balance in failing heart"},
            {"title": "Bers DM. Cardiac excitation-contraction coupling. Nature 2002;415:198-205", "url": "https://pubmed.ncbi.nlm.nih.gov/11805843/", "key": "CHRM2 role in cardiac physiology"},
        ],
    },

    "CHRM3": {
        "full_name": "Muscarinic Acetylcholine Receptor M3",
        "uniprot": "P20309",
        "chromosome": "1q43",
        "length": 590,
        "structure_class": "Class A GPCR, 7-transmembrane, Gq/11-coupled",

        "real_biology": """CHRM3 is the primary smooth muscle GPCR for acetylcholine-driven contraction.

MECHANISM: ACh → CHRM3 → Gαq → PLCβ → PIP2→IP3+DAG → IP3 receptor → Ca²⁺ release → 
smooth muscle contraction, glandular secretion, iris constriction.

PRUNE BELLY SYNDROME LINK: Weber et al. 2011 (Am J Hum Genet) showed that a frameshift 
mutation in CHRM3 (p.Pro392AlafsTer43) — removing the distal 3rd intracellular loop — 
causes Prune belly syndrome in a Turkish family. The 3rd intracellular loop is where FLNA 
binds. This directly supports the Filamin-GPCR axis in disease.

LOW DBR (0.014) MEANS RARE DISEASE, NOT UNIMPORTANT:
8 pathogenic variants in 590 amino acids. Each one causes a devastating congenital disease. 
Low count = low disease prevalence. The β-arrestin pattern is ZERO pathogenic variants — 
CHRM3 is fundamentally different.""",

        "gpcr_interaction": {
            "type": "IS A GPCR — Class A, Gq/11-coupled",
            "mechanism": "7-TM receptor. ACh binds. Gαq dissociates → PLCβ activation → IP3+DAG → Ca²⁺ from ER → smooth muscle contraction. 3rd intracellular loop docks Filamin A in smooth muscle cells.",
            "downstream": ["↑Intracellular Ca²⁺", "Smooth muscle contraction", "Glandular secretion", "Iris sphincter constriction", "Filamin A anchoring"],
            "role_in_pathway": "Primary Gq/11-coupled GPCR for smooth muscle control",
        },

        "tissue_expression": {"Bladder smooth muscle": 3, "Exocrine glands": 3, "GI tract": 3, "Eye (iris)": 3, "Lung": 2, "Kidney (epithelium)": 2, "Pancreas": 2, "Brain": 1, "Heart": 0},

        "experiments_specific": [
            {"name": "Ca²⁺ imaging in bladder smooth muscle cells", "rationale": "Direct measurement of CHRM3 Gq/11 signalling — the disrupted pathway in PBS.", "protocol": "Load cells with Fura-2 or GCaMP. Apply carbachol. Measure Ca²⁺ transients. PBS variant: absent/reduced response.", "level": 2},
            {"name": "Bladder organoid contractility assay", "rationale": "Most relevant model for PBS — tests bladder smooth muscle function.", "protocol": "Bladder smooth muscle cells (patient or CHRM3 CRISPR variant). 3D organoid. Measure contractile response to carbachol vs WT.", "level": 3},
            {"name": "CHRM3-Filamin A Co-IP (3rd intracellular loop)", "rationale": "The PBS frameshift removes the FLNA binding site. This assay directly tests whether the interaction is lost.", "protocol": "Express CHRM3-WT vs p.Pro392 frameshift variant. Co-IP with FLNA antibody. Loss of interaction = PBS mechanism confirmed.", "level": 3},
            {"name": "Inositol phosphate accumulation assay (IP-One HTRF)", "rationale": "Standard Gq/11 signalling assay. Fast, sensitive, no genetic manipulation needed.", "protocol": "HEK293 expressing CHRM3 variant. IP-One HTRF kit. Stimulate with carbachol. Compare to WT dose-response.", "level": 1},
        ],

        "timeline_stages": [
            (0, "CHRM3 frameshift variant present", "Loss of 3rd intracellular loop — Gq/11 coupling severely impaired. Filamin A cannot dock."),
            (1, "Fetal development — bladder fails", "Bladder smooth muscle cannot contract normally. Prune belly syndrome features develop in utero."),
            (2, "Birth", "Absent/hypoplastic abdominal muscles, urinary tract malformation, cryptorchidism — the PBS triad."),
            (3, "Childhood", "Urinary tract infections, renal complications from obstruction/reflux, respiratory compromise."),
            (4, "Adult (if survived)", "Renal impairment, ongoing urological management, fertility issues."),
        ],

        "papers": [
            {"title": "Weber S et al. CHRM3 mutations cause Prune belly syndrome. Am J Hum Genet 2011;89:468-474", "url": "https://pubmed.ncbi.nlm.nih.gov/21664997/", "key": "Discovery paper — CHRM3 frameshift causes PBS"},
            {"title": "Ittychanda SS et al. Filamin-GPCR interaction. J Biol Chem 2015", "url": "https://pubmed.ncbi.nlm.nih.gov/", "key": "GPCR 3rd intracellular loop - Filamin binding"},
        ],
    },

    "FLNC": {
        "full_name": "Filamin C (FLNC) — Cardiac and Skeletal Muscle Isoform",
        "uniprot": "Q14315",
        "chromosome": "7q32-q35",
        "length": 2725,
        "structure_class": "N-terminal ABD + 24 Ig-like repeats (muscle-specific C-terminal domain replaces rod 2)",

        "real_biology": """Filamin C is the muscle-specific Filamin isoform — restricted to cardiac 
and skeletal muscle (unlike FLNA which is ubiquitous).

UNIQUE FEATURES vs FLNA:
- C-terminal unique domain replaces FLNA rod 2 — this mediates Z-disc anchoring in sarcomeres
- Expressed at myotendinous junctions
- Lower copy number than FLNA — no redundancy in cardiac muscle

DBR 1.394 — MORE THAN ONE PATHOGENIC VARIANT PER AMINO ACID on average.
This makes FLNC one of the most pathogenically constrained proteins in the human genome.

CARDIAC GPCR SCAFFOLDING: FLNC repeat domains dock cardiac GPCRs (CHRM2, ADRB1) 
and anchor them to the Z-disc via its unique C-terminal domain. This positions GPCR 
signalling machinery at the contractile apparatus — coupling receptor activation directly 
to myofilament function.

CARDIOMYOPATHY TYPES:
- Truncating variants: Haploinsufficiency → dilated cardiomyopathy
- Missense variants: Often dominant negative or aggregation-prone → myofibrillar myopathy 
  (protein aggregates visible on muscle biopsy as desmin-positive inclusions)
- Arrhythmogenic CM (ACM): Disrupts desmosome-sarcomere coupling""",

        "gpcr_interaction": {
            "type": "CARDIAC GPCR SCAFFOLD",
            "mechanism": "Ig-like repeat domains 20-24 bind cardiac GPCR intracellular loops (CHRM2 3IL, ADRB1 3IL). Unique C-terminal domain anchors this complex to Z-disc. Creates a signalling microdomain at the sarcomere.",
            "which_gpcrs": ["CHRM2 (Muscarinic M2 — dominant cardiac GPCR)", "ADRB1 (β1-adrenergic)", "ADRB2 (β2-adrenergic)"],
            "downstream": ["Z-disc GPCR signalling localisation", "Direct coupling of receptor activation to sarcomere Ca²⁺ handling", "Cardiomyocyte electrophysiology"],
        },

        "tissue_expression": {"Heart (cardiomyocytes)": 3, "Skeletal muscle": 3, "Diaphragm": 3, "Smooth muscle": 1, "Brain": 0, "Liver": 0, "Kidney": 0},

        "experiments_specific": [
            {"name": "Electron microscopy of muscle biopsy (Z-disc analysis)", "rationale": "FLNC aggregating variants create pathognomonic Z-disc streaming and protein inclusions visible by EM.", "protocol": "Biopsy from affected muscle. Transmission EM. Look for Z-disc disruption, desmin inclusions, streaming.", "level": 3},
            {"name": "iPSC-derived cardiomyocyte calcium handling", "rationale": "FLNC couples GPCR signalling to Ca²⁺ handling. Variants disrupt this — measurable with Ca²⁺ indicators.", "protocol": "iPSC with FLNC variant → cardiomyocytes. GCaMP6 reporter. Measure Ca²⁺ transients, sarcomere shortening, action potential.", "level": 3},
            {"name": "Desmin co-localisation immunostaining", "rationale": "FLNC variants that aggregate disrupt desmin network — key diagnostic marker.", "protocol": "Muscle section or iPSC-CM. Stain for FLNC + desmin + sarcomeric α-actinin. Aggregates = positive diagnostic marker.", "level": 2},
            {"name": "Cardiac MRI (clinical validation)", "rationale": "Detect fibrosis pattern characteristic of FLNC cardiomyopathy (late gadolinium enhancement — inferolateral subepicardial fibrosis).", "protocol": "Clinical cardiac MRI with late gadolinium enhancement in known FLNC variant carriers.", "level": 4},
        ],

        "timeline_stages": [
            (0, "FLNC pathogenic variant present", "Heterozygous loss in cardiomyocytes and skeletal muscle. Truncating = haploinsufficiency. Aggregating = dominant negative."),
            (1, "Sarcomere-GPCR uncoupling", "Z-disc anchoring of CHRM2/ADRB1 signalling is disrupted. GPCR signals no longer localised to sarcomere."),
            (2, "Progressive structural remodelling (20s-40s)", "Fibrosis deposits (inferolateral subepicardial pattern on MRI). Ventricular dilation begins. Arrhythmia on Holter monitor."),
            (3, "Symptomatic cardiomyopathy", "Palpitations, dyspnoea, reduced ejection fraction. Risk of sudden cardiac death from ventricular arrhythmia."),
            (4, "End-stage/intervention", "ICD implantation for SCD prevention. Heart failure management. Gene therapy in future."),
        ],

        "papers": [
            {"title": "Brodehl A et al. Mutations in FLNC are associated with cardiomyopathies. J Am Heart Assoc 2016", "url": "https://pubmed.ncbi.nlm.nih.gov/27912210/", "key": "FLNC cardiomyopathy spectrum"},
            {"title": "Ortiz-Genga MF et al. Truncating FLNC mutations are associated with high-risk dilated and arrhythmogenic cardiomyopathies. J Am Coll Cardiol 2016;68:2440-2451", "url": "https://pubmed.ncbi.nlm.nih.gov/27908348/", "key": "FLNC truncating variants in DCM/ACM"},
        ],
    },

    # Scaffold: Talin
    "TALN1": {
        "full_name": "Talin 1",
        "uniprot": "Q9Y490",
        "chromosome": "9p13.3",
        "length": 2541,
        "structure_class": "FERM domain (head) + rod domain (13 helical bundles) + C-terminal actin-binding site",

        "real_biology": """Talin 1 is a major integrin activator and focal adhesion scaffold.

THE PARADOX: Mouse KO of Talin 1 is embryonic lethal (gastrulation fails). Yet humans 
with Talin 1 variants have zero confirmed Mendelian disease (DBR 0.002 — NONE tier).

WHY? Because:
1. Talin 2 (TALN2) provides functional redundancy in most human tissues
2. Partial Talin 1 function is sufficient for human viability
3. Mouse gastrulation requires VERY high integrin activation — human threshold is lower

WHAT TALIN 1 ACTUALLY DOES:
- Binds integrin β-subunit cytoplasmic tails → activates integrin from inside-out
- Links integrins to actin cytoskeleton via rod domain
- Mechanosensor: unfolds under force, exposing vinculin-binding sites
- Focal adhesion scaffolding: recruits signalling proteins (Paxillin, FAK, Vinculin)

GPCR CONTEXT: Talin 1 is NOT a GPCR scaffold. But integrin activation regulates 
GPCR signalling via inside-out and outside-in crosstalk. Talin-mediated integrin 
activation modulates cell responses to GPCR agonists by affecting cell adhesion state.

IMPORTANT: The textbook claim that 'Talin activates integrins' is TRUE in vitro.
The claim that 'Talin is essential for human physiology' is NOT validated by ClinVar.""",

        "gpcr_interaction": {
            "type": "INDIRECT — integrin-GPCR crosstalk",
            "mechanism": "Not a direct GPCR interactor. Integrin activation by Talin modulates cell sensitivity to GPCR agonists via outside-in signalling. Integrin ligation affects Gα subunit membrane localisation.",
            "which_gpcrs": ["Indirect — context-dependent"],
            "downstream": ["Integrin activation → FAK → ERK", "RhoA/ROCK cytoskeletal regulation"],
        },

        "tissue_expression": {"Skeletal muscle": 3, "Blood (platelets)": 3, "Fibroblasts": 3, "Endothelium": 3, "Heart": 2, "Brain": 2, "Kidney": 2},

        "experiments_specific": [
            {"name": "Integrin activation assay (PAC-1 or LIBS epitope)", "rationale": "The specific function of Talin 1. PAC-1 antibody binds activated αIIbβ3. Directly test whether your variant impairs integrin activation.", "protocol": "Talin 1 variant-expressing CHO or Dami cells. Flow cytometry with PAC-1 (activated αIIbβ3) vs anti-β3 (total). Ratio = activation index.", "level": 2},
            {"name": "Vinculin-binding domain pull-down (force-dependent)", "rationale": "Talin rod domains expose VBS under mechanical force. Specific to Talin's mechanosensor function.", "protocol": "Stretching device on cells expressing TALN1 variant. Pull-down with vinculin. Compare force-dependent binding vs WT.", "level": 3},
            {"name": "Traction force microscopy", "rationale": "Measures force transmission — Talin's core function. Variant in force-transduction domain = measurable defect.", "protocol": "Cells on micropillar arrays. Measure pillar deflection (= traction force). TALN1 variant cells vs WT.", "level": 3},
        ],

        "timeline_stages": [
            (0, "TALN1 variant present", "No established human disease phenotype. β-arrestin comparison: both have 0 pathogenic variants — but Talin has a clear molecular function, just redundantly covered."),
            (1, "If both TALN1 and TALN2 affected", "Hypothetical: severe integrin activation failure across tissues. Not observed in ClinVar."),
            (2, "In vitro context", "Talin 1 variants do cause measurable defects in integrin activation assays. Relevant for understanding protein biology, not for patient treatment."),
        ],

        "papers": [
            {"title": "Calderwood DA et al. The talin head domain binds to integrin beta subunit cytoplasmic tails. J Biol Chem 1999", "url": "https://pubmed.ncbi.nlm.nih.gov/10610390/", "key": "Talin integrin activation mechanism"},
            {"title": "Dedden D et al. The architecture of Talin1 reveals an autoinhibition mechanism. Cell 2019", "url": "https://pubmed.ncbi.nlm.nih.gov/31051102/", "key": "Talin 1 structural basis"},
            {"title": "Minikel et al. Nature 2021 — Talin 1 is in gnomAD with high variant tolerance", "url": "https://www.nature.com/articles/s41586-020-2267-z", "key": "Why Talin 1 variants don't cause disease"},
        ],
    },
}

def get_protein_info(gene: str) -> dict:
    """Get comprehensive protein knowledge. Returns curated data or a generic framework."""
    gu = gene.upper().strip()
    if gu in PROTEIN_KNOWLEDGE:
        return PROTEIN_KNOWLEDGE[gu]

    # Generic framework for uncurated proteins
    return {
        "full_name": f"{gene} (see UniProt for full name)",
        "real_biology": f"{gene} — detailed biology not yet curated in Protellect database. Refer to UniProt function annotation and ClinVar for disease evidence.",
        "gpcr_interaction": {"type": "Unknown — check UniProt", "mechanism": "Query UniProt and IUPHAR/BPS Guide to Pharmacology for interaction details."},
        "why_mutations_major": f"Check DBR and ClinVar pathogenic variant count. High DBR (>0.5) = critical. Low DBR (>0 but <0.1) = rare Mendelian. Zero = genomically unvalidated.",
        "tissue_expression": {},
        "experiments_specific": [
            {"name": "ClinVar + gnomAD database screen", "rationale": "First step for any protein — establish genomic context before bench work.", "level": 1},
            {"name": "Function-specific assay (see UniProt)", "rationale": f"Design experiments based on {gene}'s known molecular function from UniProt.", "level": 2},
        ],
        "timeline_stages": [(0, "Variant present", f"Disease consequences depend on {gene} function and ClinVar evidence.")],
        "papers": [],
    }
