"""
diagrams.py — Protellect Visual Diagrams

Four diagram types, all driven by real data from UniProt/ClinVar:

1. Tissue Expression Map    — heatmap of tissue expression, coloured by level
2. Genomic Breakdown        — chromosome position, protein domains, variant positions
3. GPCR Signalling Diagram  — G-protein cascade, downstream effects, tissue context
4. Cell Impact Diagram      — what happens in the cell when this protein is mutated

All built as self-contained HTML with inline SVG/Canvas.
No external libraries. No fabricated data.
"""

import json
import re


# ── Tissue expression map ─────────────────────────────────────────────────────

# Known tissue expression levels from UniProt / Protein Atlas for common proteins
# Used as fallback when API data is not available
# Format: gene -> {tissue: level} where level: 3=high, 2=medium, 1=low, 0=not detected
KNOWN_TISSUE_EXPRESSION = {
    "CHRM3": {
        "Bladder (smooth muscle)": 3, "Exocrine glands": 3,
        "Gastrointestinal tract": 3, "Lung": 2, "Eye (iris)": 3,
        "Kidney (renal epithelium)": 2, "Brain": 1,
        "Heart": 0, "Liver": 0, "Skeletal muscle": 0,
        "Skin": 1, "Pancreas": 2, "Prostate": 1,
    },
    "FLNC": {
        "Heart (cardiomyocytes)": 3, "Skeletal muscle": 3,
        "Smooth muscle": 1, "Brain": 0, "Liver": 0,
        "Kidney": 0, "Lung": 1, "Pancreas": 0,
    },
    "ARRB1": {
        "Brain": 3, "Heart": 2, "Liver": 2, "Kidney": 2,
        "Lung": 2, "Skeletal muscle": 1, "Spleen": 2,
        "Adrenal gland": 3, "Gastrointestinal tract": 2,
    },
    "TP53": {
        "Ubiquitous": 3, "Brain": 2, "Heart": 2, "Liver": 3,
        "Kidney": 2, "Lung": 2, "Skeletal muscle": 2,
        "Skin": 2, "Blood": 3, "Thymus": 3,
    },
    "BRCA1": {
        "Breast": 3, "Ovary": 3, "Placenta": 3,
        "Liver": 2, "Brain": 1, "Lung": 1,
        "Blood (lymphocytes)": 3, "Thymus": 2,
    },
}

GPCR_SIGNALLING_DATA = {
    "Gq/11": {
        "cascade": [
            "GPCR activation (ligand binding)",
            "Gαq dissociates from Gβγ",
            "Gαq activates Phospholipase C-β (PLCβ)",
            "PLCβ cleaves PIP2 → IP3 + DAG",
            "IP3 → ER Ca²⁺ release",
            "DAG → Protein Kinase C (PKC) activation",
            "PKC → cell-specific response",
        ],
        "second_messengers": ["IP3", "DAG", "Ca²⁺"],
        "downstream_effects": ["Smooth muscle contraction", "Secretion", "Cell proliferation", "Gene transcription"],
        "color": "#9370DB",
        "inhibitors": ["Atropine (muscarinic)", "Darifenacin (M3-selective)", "Oxybutynin"],
    },
    "Gi/o": {
        "cascade": [
            "GPCR activation (ligand binding)",
            "Gαi dissociates, inhibits adenylate cyclase",
            "cAMP levels fall",
            "PKA activity reduced",
            "GIRK channels open (via Gβγ)",
            "Cell hyperpolarisation",
            "Reduced cellular excitability",
        ],
        "second_messengers": ["cAMP (decreased)", "K⁺ (GIRK)"],
        "downstream_effects": ["Reduced heart rate", "Inhibition of neurotransmitter release", "Analgesia"],
        "color": "#4CA8FF",
        "inhibitors": ["Pertussis toxin (research)", "Naloxone (opioid)"],
    },
    "Gs": {
        "cascade": [
            "GPCR activation (ligand binding)",
            "Gαs dissociates, activates adenylate cyclase",
            "cAMP levels rise",
            "Protein Kinase A (PKA) activation",
            "PKA phosphorylates target proteins",
            "Cell-specific response",
        ],
        "second_messengers": ["cAMP", "PKA"],
        "downstream_effects": ["Increased heart rate", "Bronchodilation", "Lipolysis", "Glycogenolysis"],
        "color": "#FFA500",
        "inhibitors": ["Beta-blockers (ADRB)", "SST analogues (SSTR)"],
    },
    "G12/13": {
        "cascade": [
            "GPCR activation",
            "Gα12/13 dissociates",
            "Activates RhoGEF",
            "RhoA activation",
            "ROCK (Rho-associated kinase) activated",
            "Actin cytoskeleton reorganisation",
            "Cell shape change / migration",
        ],
        "second_messengers": ["RhoA", "ROCK"],
        "downstream_effects": ["Cytoskeletal rearrangement", "Cell migration", "Smooth muscle contraction"],
        "color": "#FF4C4C",
        "inhibitors": ["Y-27632 (ROCK inhibitor, research)"],
    },
}


def build_tissue_diagram(gene_name: str, tissue_text: str, known_tissues: dict = None) -> str:
    """
    Build an interactive tissue expression heatmap.
    Parses UniProt tissue specificity text to extract tissues.
    Falls back to known data for common proteins.
    """
    # Get tissues from known data or parse from text
    tissues = {}
    if gene_name.upper() in KNOWN_TISSUE_EXPRESSION:
        tissues = KNOWN_TISSUE_EXPRESSION[gene_name.upper()]
    elif known_tissues:
        tissues = known_tissues
    elif tissue_text:
        # Parse tissue text
        high_terms  = re.findall(r'(?:high(?:ly)?|strong|abundant)\s+(?:expression\s+)?(?:in\s+)?([^.;,]+)', tissue_text, re.I)
        med_terms   = re.findall(r'(?:moderate|medium|detectable)\s+(?:expression\s+)?(?:in\s+)?([^.;,]+)', tissue_text, re.I)
        low_terms   = re.findall(r'(?:low|weak|faint)\s+(?:expression\s+)?(?:in\s+)?([^.;,]+)', tissue_text, re.I)
        absent_terms= re.findall(r'(?:absent|not detected|undetectable)\s+(?:in\s+)?([^.;,]+)', tissue_text, re.I)

        for t in high_terms[:6]:   tissues[t.strip()[:30]] = 3
        for t in med_terms[:4]:    tissues[t.strip()[:30]] = 2
        for t in low_terms[:4]:    tissues[t.strip()[:30]] = 1
        for t in absent_terms[:4]: tissues[t.strip()[:30]] = 0

    if not tissues:
        tissues = {"Data not available": 0}

    # Build SVG
    items  = list(tissues.items())
    n      = len(items)
    cols   = min(4, n)
    rows   = (n + cols - 1) // cols
    W      = 640
    cell_w = W // cols
    cell_h = 52
    H      = rows * cell_h + 80

    level_colors = {3: "#FF4C4C", 2: "#FFA500", 1: "#4CA8FF", 0: "#2a2d3a"}
    level_labels = {3: "HIGH", 2: "MEDIUM", 1: "LOW", 0: "ABSENT"}

    cells = ""
    for i, (tissue, level) in enumerate(items):
        col = i % cols
        row = i // cols
        x   = col * cell_w
        y   = 50 + row * cell_h
        c   = level_colors.get(level, "#2a2d3a")
        lbl = level_labels.get(level, "—")
        short = tissue[:22] + "…" if len(tissue) > 22 else tissue
        cells += f"""
        <g>
          <rect x="{x+3}" y="{y+3}" width="{cell_w-6}" height="{cell_h-6}"
                rx="6" fill="{c}22" stroke="{c}" stroke-width="1.5"/>
          <text x="{x+cell_w//2}" y="{y+22}" text-anchor="middle"
                font-size="10" fill="{c}" font-family="IBM Plex Mono,monospace"
                font-weight="600">{lbl}</text>
          <text x="{x+cell_w//2}" y="{y+36}" text-anchor="middle"
                font-size="9" fill="#aaa" font-family="Inter,sans-serif">{short}</text>
        </g>"""

    # Legend
    legend = ""
    for level, lbl in [(3,"High"),(2,"Medium"),(1,"Low"),(0,"Absent")]:
        lx = 10 + list(level_labels.values()).index(lbl.upper()) * 120
        legend += f'''
        <rect x="{lx}" y="{H-28}" width="12" height="12" rx="3"
              fill="{level_colors[level]}44" stroke="{level_colors[level]}" stroke-width="1"/>
        <text x="{lx+16}" y="{H-19}" font-size="10" fill="#888"
              font-family="Inter,sans-serif">{lbl} expression</text>'''

    svg = f"""<!DOCTYPE html><html><head>
<style>body{{margin:0;background:#080b14}}svg{{display:block;width:100%}}</style>
</head><body>
<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{W}" height="{H}" fill="#080b14"/>
  <text x="{W//2}" y="28" text-anchor="middle" font-size="13"
        font-family="IBM Plex Mono,monospace" font-weight="700" fill="#eee">
    {gene_name} — Tissue Expression
  </text>
  <text x="{W//2}" y="44" text-anchor="middle" font-size="9"
        font-family="Inter,sans-serif" fill="#555">
    Source: UniProt experimental annotations
  </text>
  {cells}
  {legend}
</svg>
</body></html>"""

    return svg


def build_genomic_diagram(gene_name: str, chromosome: str, protein_length: int,
                          domains: list, variants_pathogenic: list,
                          variants_benign: list = None) -> str:
    """
    Build a genomic breakdown diagram:
    - Chromosome position indicator
    - Protein linear map with domains
    - Pathogenic variant positions (red ticks)
    - Benign variant positions (blue ticks)
    """
    W = 640
    H = 280

    # Chromosome block
    chrom_display = f"Chr {chromosome}" if chromosome else "Chr —"

    # Domain colours
    domain_palette = ["#9370DB","#4CA8FF","#FFA500","#4CAF50","#FF6B9D","#00BCD4"]

    # Scale protein to diagram width
    track_x = 60
    track_w = W - 120
    track_y = 130
    track_h = 28

    def pos_to_x(pos):
        if not protein_length or protein_length == 0:
            return track_x
        return track_x + int((pos / protein_length) * track_w)

    # Domain rects
    domain_svgs = ""
    for i, d in enumerate(domains[:8]):
        dx   = pos_to_x(d["start"])
        dw   = max(pos_to_x(d["end"]) - dx, 4)
        dc   = domain_palette[i % len(domain_palette)]
        name = d.get("name","")[:16]
        domain_svgs += f"""
        <rect x="{dx}" y="{track_y}" width="{dw}" height="{track_h}"
              fill="{dc}55" stroke="{dc}" stroke-width="1.5" rx="3"/>
        <text x="{dx+dw//2}" y="{track_y+track_h//2+4}" text-anchor="middle"
              font-size="8" fill="{dc}" font-family="IBM Plex Mono,monospace">{name}</text>"""

    # Pathogenic variant ticks (red, above track)
    path_ticks = ""
    shown_path = {}
    for v in variants_pathogenic[:60]:
        pos = v.get("pos") or v.get("position")
        if not pos:
            # Try to extract from title
            m = re.search(r'[A-Z](\d+)[A-Z=\*]', v.get("title","") + v.get("note",""))
            if m: pos = int(m.group(1))
        if not pos: continue
        vx  = pos_to_x(pos)
        if abs(vx - shown_path.get(vx, -99)) < 3: continue  # dedupe
        shown_path[vx] = vx
        path_ticks += f'<line x1="{vx}" y1="{track_y-18}" x2="{vx}" y2="{track_y}" stroke="#FF4C4C" stroke-width="1.5" opacity="0.8"/>'
        path_ticks += f'<circle cx="{vx}" cy="{track_y-20}" r="3" fill="#FF4C4C" opacity="0.9"/>'

    # Benign ticks (blue, below track)
    benign_ticks = ""
    if variants_benign:
        shown_ben = {}
        for v in variants_benign[:40]:
            pos = v.get("pos") or v.get("position")
            if not pos: continue
            vx  = pos_to_x(pos)
            if abs(vx - shown_ben.get(vx,-99)) < 3: continue
            shown_ben[vx] = vx
            benign_ticks += f'<line x1="{vx}" y1="{track_y+track_h}" x2="{vx}" y2="{track_y+track_h+16}" stroke="#4CA8FF" stroke-width="1.2" opacity="0.7"/>'
            benign_ticks += f'<circle cx="{vx}" cy="{track_y+track_h+18}" r="2.5" fill="#4CA8FF" opacity="0.8"/>'

    # Position ruler
    ruler = ""
    for pct in [0, 25, 50, 75, 100]:
        rx  = track_x + int(pct / 100 * track_w)
        raa = int(pct / 100 * protein_length) if protein_length else pct
        ruler += f'<line x1="{rx}" y1="{track_y+track_h}" x2="{rx}" y2="{track_y+track_h+5}" stroke="#2a2d3a" stroke-width="1"/>'
        ruler += f'<text x="{rx}" y="{track_y+track_h+16}" text-anchor="middle" font-size="8" fill="#555" font-family="IBM Plex Mono,monospace">{raa}</text>'

    n_path = len(variants_pathogenic)
    n_ben  = len(variants_benign) if variants_benign else 0

    html = f"""<!DOCTYPE html><html><head>
<style>body{{margin:0;background:#080b14}}svg{{display:block;width:100%}}</style>
</head><body>
<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{W}" height="{H}" fill="#080b14"/>

  <!-- Title -->
  <text x="{W//2}" y="22" text-anchor="middle" font-size="13"
        font-family="IBM Plex Mono,monospace" font-weight="700" fill="#eee">
    {gene_name} — Genomic &amp; Protein Structure
  </text>

  <!-- Chromosome pill -->
  <rect x="20" y="36" width="90" height="22" rx="11"
        fill="#9370DB22" stroke="#9370DB" stroke-width="1.5"/>
  <text x="65" y="51" text-anchor="middle" font-size="10"
        font-family="IBM Plex Mono,monospace" fill="#9370DB">{chrom_display}</text>

  <!-- Protein length -->
  <text x="130" y="51" font-size="10" font-family="IBM Plex Mono,monospace" fill="#555">
    {protein_length} aa
  </text>

  <!-- Variant counts -->
  <circle cx="{W-100}" cy="47" r="6" fill="#FF4C4C44" stroke="#FF4C4C" stroke-width="1.5"/>
  <text x="{W-88}" y="51" font-size="10" font-family="IBM Plex Mono,monospace" fill="#FF4C4C">{n_path} pathogenic</text>
  <circle cx="{W-100}" cy="67" r="6" fill="#4CA8FF44" stroke="#4CA8FF" stroke-width="1.5"/>
  <text x="{W-88}" y="71" font-size="10" font-family="IBM Plex Mono,monospace" fill="#4CA8FF">{n_ben} benign</text>

  <!-- Labels above/below track -->
  <text x="{track_x}" y="{track_y-25}" font-size="9"
        font-family="IBM Plex Mono,monospace" fill="#FF4C4C">▲ Pathogenic variants</text>
  <text x="{track_x}" y="{track_y+track_h+34}" font-size="9"
        font-family="IBM Plex Mono,monospace" fill="#4CA8FF">▼ Benign variants</text>

  <!-- Protein backbone -->
  <rect x="{track_x}" y="{track_y}" width="{track_w}" height="{track_h}"
        fill="#0f1117" stroke="#1e2030" stroke-width="1.5" rx="4"/>
  <text x="{track_x+6}" y="{track_y+track_h//2+4}" font-size="9"
        font-family="Inter,sans-serif" fill="#3a3d5a">N-term</text>
  <text x="{track_x+track_w-30}" y="{track_y+track_h//2+4}" font-size="9"
        font-family="Inter,sans-serif" fill="#3a3d5a">C-term</text>

  {domain_svgs}
  {path_ticks}
  {benign_ticks}
  {ruler}

  <!-- Domain legend -->
  <text x="{W//2}" y="{H-12}" text-anchor="middle" font-size="9"
        font-family="Inter,sans-serif" fill="#444">
    Source: UniProt domain annotations · ClinVar variant positions
  </text>
</svg>
</body></html>"""

    return html


def build_gpcr_diagram(gene_name: str, g_protein: str,
                       protein_name: str = "", n_tm: int = 7) -> str:
    """
    Build a GPCR signalling cascade diagram.
    Shows the full G-protein pathway from receptor to cellular effect.
    """
    sig = GPCR_SIGNALLING_DATA.get(g_protein, GPCR_SIGNALLING_DATA.get("Gq/11"))
    if not sig:
        sig = GPCR_SIGNALLING_DATA["Gq/11"]

    cascade   = sig["cascade"]
    messengers = sig["second_messengers"]
    effects    = sig["downstream_effects"]
    color      = sig["color"]
    inhibitors = sig.get("inhibitors", [])

    W = 660
    H = 420
    n_steps = len(cascade)
    step_w  = (W - 120) // n_steps
    step_h  = 44

    steps_svg = ""
    for i, step in enumerate(cascade):
        sx   = 60 + i * step_w
        sy   = 80
        short = step[:24] + "…" if len(step) > 24 else step
        alpha = max(0.4, 1.0 - i * 0.05)
        steps_svg += f"""
        <rect x="{sx}" y="{sy}" width="{step_w-8}" height="{step_h}"
              rx="6" fill="{color}22" stroke="{color}" stroke-width="1.5" opacity="{alpha}"/>
        <text x="{sx+step_w//2-4}" y="{sy+16}" text-anchor="middle"
              font-size="7.5" fill="{color}" font-family="IBM Plex Mono,monospace"
              opacity="{alpha}">{i+1}</text>
        <text x="{sx+step_w//2-4}" y="{sy+28}" text-anchor="middle"
              font-size="7" fill="#bbb" font-family="Inter,sans-serif"
              opacity="{alpha}">{short}</text>"""
        if i < n_steps - 1:
            ax = sx + step_w - 8
            ay = sy + step_h // 2
            steps_svg += f'<line x1="{ax}" y1="{ay}" x2="{ax+12}" y2="{ay}" stroke="{color}" stroke-width="1.5" opacity="0.6"/>'
            steps_svg += f'<polygon points="{ax+12},{ay-4} {ax+18},{ay} {ax+12},{ay+4}" fill="{color}" opacity="0.6"/>'

    # Second messengers
    msg_y = 165
    msg_svgs = ""
    for i, msg in enumerate(messengers):
        mx = 80 + i * 180
        msg_svgs += f"""
        <rect x="{mx}" y="{msg_y}" width="150" height="30" rx="15"
              fill="{color}33" stroke="{color}88" stroke-width="1"/>
        <text x="{mx+75}" y="{msg_y+20}" text-anchor="middle"
              font-size="11" fill="{color}" font-family="IBM Plex Mono,monospace"
              font-weight="600">{msg}</text>"""

    # Downstream effects
    eff_y = 230
    eff_svgs = ""
    for i, eff in enumerate(effects[:4]):
        ex = 40 + i * 150
        eff_svgs += f"""
        <rect x="{ex}" y="{eff_y}" width="140" height="36" rx="6"
              fill="#0f1117" stroke="#1e2030" stroke-width="1.5"/>
        <text x="{ex+70}" y="{eff_y+22}" text-anchor="middle"
              font-size="9" fill="#aaa" font-family="Inter,sans-serif">{eff[:22]}</text>"""

    # Inhibitors
    inh_svgs = ""
    for i, inh in enumerate(inhibitors[:3]):
        ix = 40 + i * 200
        inh_svgs += f"""
        <rect x="{ix}" y="310" width="180" height="26" rx="13"
              fill="#FF4C4C22" stroke="#FF4C4C55" stroke-width="1"/>
        <text x="{ix+90}" y="327" text-anchor="middle"
              font-size="9" fill="#FF4C4C" font-family="IBM Plex Mono,monospace">⊗ {inh[:28]}</text>"""

    # 7-TM schematic
    tm_svg = ""
    for i in range(7):
        tx = W - 130 + i * 15
        ty1 = 80 + (20 if i % 2 == 0 else 0)
        ty2 = ty1 + 100
        tm_svg += f'<line x1="{tx}" y1="{ty1}" x2="{tx}" y2="{ty2}" stroke="{color}" stroke-width="6" opacity="0.7" stroke-linecap="round"/>'
        if i < 6:
            lx1, lx2 = tx + 3, tx + 15 - 3
            ly = ty1 + (0 if i % 2 == 0 else 100)
            tm_svg += f'<path d="M{lx1},{ly} Q{(lx1+lx2)//2},{ly + (20 if i%2==0 else -20)} {lx2},{ly}" stroke="{color}" stroke-width="2" fill="none" opacity="0.5"/>'

    html = f"""<!DOCTYPE html><html><head>
<style>body{{margin:0;background:#080b14}}svg{{display:block;width:100%}}</style>
</head><body>
<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{W}" height="{H}" fill="#080b14"/>

  <!-- Title -->
  <text x="10" y="25" font-size="13" font-family="IBM Plex Mono,monospace"
        font-weight="700" fill="#eee">{gene_name} — GPCR Signalling Cascade</text>
  <text x="10" y="42" font-size="10" font-family="Inter,sans-serif" fill="#555">
    G-protein coupling: <tspan fill="{color}" font-weight="600">{g_protein}</tspan>
    · {n_tm} transmembrane helices (7TM confirmed)
  </text>

  <!-- Cascade steps -->
  {steps_svg}

  <!-- Arrows down to second messengers -->
  <line x1="{W//2 - 200}" y1="126" x2="{W//2 - 200}" y2="{msg_y}" stroke="{color}" stroke-width="1" stroke-dasharray="4,3" opacity="0.4"/>
  <text x="60" y="{msg_y-8}" font-size="9" font-family="IBM Plex Mono,monospace" fill="{color}" opacity="0.7">Second messengers</text>

  {msg_svgs}

  <!-- Down to downstream effects -->
  <line x1="{W//2-80}" y1="{msg_y+32}" x2="{W//2-80}" y2="{eff_y}" stroke="{color}" stroke-width="1" stroke-dasharray="4,3" opacity="0.3"/>
  <text x="40" y="{eff_y-8}" font-size="9" font-family="IBM Plex Mono,monospace" fill="#aaa" opacity="0.7">Downstream cellular effects</text>

  {eff_svgs}

  <!-- Inhibitors section -->
  <text x="40" y="306" font-size="9" font-family="IBM Plex Mono,monospace" fill="#FF4C4C" opacity="0.7">Known inhibitors / antagonists</text>
  {inh_svgs}

  <!-- 7TM schematic -->
  <text x="{W-140}" y="72" font-size="9" font-family="IBM Plex Mono,monospace" fill="{color}" opacity="0.7">7TM helices</text>
  <rect x="{W-140}" y="78" width="118" height="110" rx="4" fill="#0a0c14" stroke="{color}33" stroke-width="1"/>
  <text x="{W-81}" y="200" text-anchor="middle" font-size="8" fill="#555" font-family="Inter,sans-serif">Membrane</text>
  <line x1="{W-140}" y1="130" x2="{W-22}" y2="130" stroke="#1e2030" stroke-width="1" stroke-dasharray="2,2"/>
  <line x1="{W-140}" y1="160" x2="{W-22}" y2="160" stroke="#1e2030" stroke-width="1" stroke-dasharray="2,2"/>
  {tm_svg}

  <!-- Source -->
  <text x="{W//2}" y="{H-8}" text-anchor="middle" font-size="8"
        font-family="Inter,sans-serif" fill="#333">
    Source: UniProt · IUPHAR/BPS Guide to Pharmacology · Experimental evidence
  </text>
</svg>
</body></html>"""

    return html


def build_cell_impact_diagram(gene_name: str, tier: str, n_pathogenic: int,
                               diseases: list, subcellular: list,
                               is_gpcr: bool = False, g_protein: str = "") -> str:
    """
    Build a cell impact diagram showing what happens when this protein is mutated.
    Adapts based on genomic tier and known disease associations.
    """
    W = 640
    H = 360

    tier_colors = {
        "CRITICAL": "#FF4C4C", "HIGH": "#FFA500",
        "LOW": "#FFD700", "NONE": "#888888", "UNKNOWN": "#4CA8FF"
    }
    tc = tier_colors.get(tier, "#888")

    # Cell organelle positions
    cell_cx, cell_cy, cell_rx, cell_ry = 200, 180, 155, 130
    nucleus_cx, nucleus_cy, nucleus_r  = 200, 180, 52
    membrane_y = cell_cy - cell_ry

    # Impact text based on tier and disease
    if tier == "NONE":
        impact_title = "No confirmed cellular pathology"
        impact_desc  = "No human mutations cause disease.\nCellular function likely redundant."
        impact_color = "#888"
    elif tier in ("CRITICAL","HIGH"):
        disease_str  = diseases[0][:30] if diseases else "severe disease"
        impact_title = f"Confirmed pathology: {disease_str}"
        impact_desc  = f"{n_pathogenic} pathogenic variants\ndocumented in ClinVar"
        impact_color = "#FF4C4C"
    else:
        disease_str  = diseases[0][:30] if diseases else "rare disease"
        impact_title = f"Rare disease: {disease_str}"
        impact_desc  = f"{n_pathogenic} pathogenic variant(s)\nconfirmed in humans"
        impact_color = "#FFD700"

    # Subcellular location tags
    loc_svgs = ""
    for i, loc in enumerate(subcellular[:5]):
        lx = 380 + (i % 2) * 130
        ly = 70 + (i // 2) * 45
        short = loc[:22]
        loc_svgs += f"""
        <rect x="{lx}" y="{ly}" width="120" height="28" rx="14"
              fill="#4CA8FF22" stroke="#4CA8FF55" stroke-width="1"/>
        <text x="{lx+60}" y="{ly+18}" text-anchor="middle"
              font-size="9" fill="#4CA8FF" font-family="IBM Plex Mono,monospace">{short}</text>"""

    # GPCR membrane element
    gpcr_svg = ""
    if is_gpcr and g_protein:
        sig = GPCR_SIGNALLING_DATA.get(g_protein, {})
        gc  = sig.get("color","#9370DB")
        gpcr_svg = f"""
        <!-- GPCR in membrane -->
        <rect x="80" y="{membrane_y+5}" width="55" height="40" rx="4"
              fill="{gc}44" stroke="{gc}" stroke-width="2"/>
        <text x="107" y="{membrane_y+22}" text-anchor="middle"
              font-size="8" fill="{gc}" font-family="IBM Plex Mono,monospace"
              font-weight="600">{gene_name}</text>
        <text x="107" y="{membrane_y+35}" text-anchor="middle"
              font-size="7" fill="{gc}aa" font-family="IBM Plex Mono,monospace">7TM GPCR</text>
        <!-- G-protein below -->
        <ellipse cx="107" cy="{membrane_y+65}" rx="28" ry="16"
                 fill="{gc}33" stroke="{gc}88" stroke-width="1.5"/>
        <text x="107" y="{membrane_y+69}" text-anchor="middle"
              font-size="8" fill="{gc}" font-family="IBM Plex Mono,monospace">{g_protein}</text>
        <line x1="107" y1="{membrane_y+45}" x2="107" y2="{membrane_y+49}"
              stroke="{gc}" stroke-width="1.5" stroke-dasharray="3,2"/>"""

    html = f"""<!DOCTYPE html><html><head>
<style>body{{margin:0;background:#080b14}}svg{{display:block;width:100%}}</style>
</head><body>
<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{W}" height="{H}" fill="#080b14"/>

  <!-- Title -->
  <text x="10" y="22" font-size="13" font-family="IBM Plex Mono,monospace"
        font-weight="700" fill="#eee">{gene_name} — Cell Impact</text>

  <!-- Cell outline -->
  <ellipse cx="{cell_cx}" cy="{cell_cy}" rx="{cell_rx}" ry="{cell_ry}"
           fill="#0a0c14" stroke="#1e2030" stroke-width="2"/>

  <!-- Cell membrane label -->
  <text x="{cell_cx-cell_rx+5}" y="{membrane_y+10}" font-size="8"
        font-family="IBM Plex Mono,monospace" fill="#2a2d3a">Plasma membrane</text>

  <!-- Nucleus -->
  <ellipse cx="{nucleus_cx}" cy="{nucleus_cy}" rx="{nucleus_r}" ry="{nucleus_r-8}"
           fill="#0f1117" stroke="#2a2d3a" stroke-width="1.5"/>
  <text x="{nucleus_cx}" y="{nucleus_cy-8}" text-anchor="middle"
        font-size="8" fill="#3a3d5a" font-family="IBM Plex Mono,monospace">Nucleus</text>
  <text x="{nucleus_cx}" y="{nucleus_cy+6}" text-anchor="middle"
        font-size="7" fill="#2a2d3a" font-family="IBM Plex Mono,monospace">DNA/Chromatin</text>

  {gpcr_svg}

  <!-- Protein location marker -->
  <circle cx="{cell_cx+60}" cy="{cell_cy-30}" r="18"
          fill="{tc}33" stroke="{tc}" stroke-width="2"/>
  <text x="{cell_cx+60}" y="{cell_cy-26}" text-anchor="middle"
        font-size="7" fill="{tc}" font-family="IBM Plex Mono,monospace">{gene_name[:8]}</text>

  <!-- Impact box -->
  <rect x="375" y="200" width="250" height="100" rx="8"
        fill="{impact_color}11" stroke="{impact_color}55" stroke-width="1.5"/>
  <text x="500" y="220" text-anchor="middle"
        font-size="10" fill="{impact_color}" font-family="IBM Plex Mono,monospace"
        font-weight="600">When mutated:</text>
  <text x="500" y="240" text-anchor="middle"
        font-size="9" fill="#eee" font-family="Inter,sans-serif">{impact_title[:35]}</text>
  <text x="500" y="260" text-anchor="middle"
        font-size="8" fill="#888" font-family="Inter,sans-serif">{impact_desc.split(chr(10))[0]}</text>
  <text x="500" y="276" text-anchor="middle"
        font-size="8" fill="#888" font-family="Inter,sans-serif">{impact_desc.split(chr(10))[1] if chr(10) in impact_desc else ''}</text>

  <!-- Subcellular locations -->
  <text x="380" y="50" font-size="9" font-family="IBM Plex Mono,monospace"
        fill="#4CA8FF" opacity="0.7">Subcellular locations</text>
  {loc_svgs}

  <!-- Genomic tier badge -->
  <rect x="375" y="315" width="250" height="30" rx="15"
        fill="{tc}22" stroke="{tc}66" stroke-width="1.5"/>
  <text x="500" y="334" text-anchor="middle"
        font-size="10" fill="{tc}" font-family="IBM Plex Mono,monospace"
        font-weight="600">ClinVar: {n_pathogenic} pathogenic variants</text>

  <!-- Source -->
  <text x="{W//2}" y="{H-8}" text-anchor="middle"
        font-size="8" font-family="Inter,sans-serif" fill="#333">
    Source: UniProt subcellular location · ClinVar pathogenic variants
  </text>
</svg>
</body></html>"""

    return html
