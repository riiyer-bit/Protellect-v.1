"""diagrams.py — Protellect v3: clean, readable, GPCR association, paper citations"""
import re

TISSUE_DATA = {
    "FLNA":  {"Brain":3,"Heart":3,"Lung":3,"Liver":3,"Kidney":3,"Smooth muscle":3,"Blood vessels":3,"Spleen":2,"Skin":2},
    "FLNB":  {"Bone/Cartilage":3,"Skeletal muscle":2,"Brain":1,"Heart":1,"Kidney":1,"Liver":0},
    "FLNC":  {"Heart":3,"Skeletal muscle":3,"Diaphragm":3,"Smooth muscle":1,"Brain":0,"Liver":0,"Kidney":0},
    "CHRM2": {"Heart":3,"Brain":3,"Smooth muscle":2,"GI tract":2,"Lung":1,"Liver":0},
    "CHRM3": {"Bladder":3,"Exocrine glands":3,"GI tract":3,"Eye":3,"Lung":2,"Kidney":2,"Pancreas":2,"Brain":1,"Heart":0},
    "ARRB1": {"Brain":3,"Adrenal gland":3,"Heart":2,"Liver":2,"Kidney":2,"Spleen":2},
    "ARRB2": {"Brain":3,"Liver":3,"Kidney":2,"Heart":2,"Lung":2,"Spleen":2},
    "TALN1": {"Skeletal muscle":3,"Blood (platelets)":3,"Fibroblasts":3,"Heart":2,"Brain":2},
    "BRCA1": {"Breast":3,"Ovary":3,"Blood":3,"Thymus":2,"Liver":2},
    "TP53":  {"All tissues":3,"Blood":3,"Thymus":3,"Liver":3,"Brain":2},
    "EGFR":  {"Lung":3,"Skin":3,"GI tract":3,"Brain":2,"Kidney":2},
    "KRAS":  {"Pancreas":3,"Colon":3,"Lung":3,"Liver":2},
}

GPCR_ASSOC = {
    "FLNA":  {"type":"INTRACELLULAR GPCR SCAFFOLD","color":"#9370DB","g_protein":"Multiple GPCRs (via repeat domains)",
              "mechanism":"Filamin A repeat domains bind intracellular loops of hundreds of GPCRs simultaneously. Acts as a signalling hub linking GPCRs to the actin cytoskeleton. Proposed memory mechanism: specific GPCR-Filamin configurations established during development encode cell identity.",
              "partners":["CHRM2","CHRM3","ADRB1","ADRB2","DRD2","HTR2A","100+ others"],
              "paper":"Ithychanda SS et al. — Filamin as GPCR scaffold, Cleveland Clinic",
              "note":"β-arrestin piggybacks on the same GPCR-Filamin interaction. FLNA has 847 ClinVar pathogenic variants. ARRB1/2 have ZERO. The essential component is Filamin, not β-arrestin."},
    "FLNC":  {"type":"CARDIAC GPCR SCAFFOLD","color":"#FF4C4C","g_protein":"CHRM2, ADRB1 (cardiac)",
              "mechanism":"Filamin C in cardiomyocytes scaffolds GPCR signalling to the sarcomere contractile apparatus. Loss of this scaffolding causes arrhythmogenic and dilated cardiomyopathy.",
              "partners":["CHRM2","ADRB1","ADRB2"],
              "paper":"Ithychanda & Bhatt — Filamin C cardiomyopathy pathway"},
    "ARRB1": {"type":"GPCR DESENSITISER (structural scaffold)","color":"#888","g_protein":"Post-activation (multiple)",
              "mechanism":"Binds phosphorylated GPCRs after GRK activation. Also docks onto Filamin. ZERO disease variants in 418 amino acids — not the essential regulator textbooks claim. The essential biology is in Filamin.",
              "partners":["FLNA","FLNB","All phosphorylated GPCRs"],
              "paper":"Lefkowitz RJ, Shenoy SK. Science 2005;308:512-517",
              "note":"CRITICAL: 400+ amino acid variants exist in healthy humans. Mouse knockout survives. The signalling role of β-arrestin in human physiology is NOT supported by ClinVar."},
    "ARRB2": {"type":"GPCR DESENSITISER (structural scaffold)","color":"#888","g_protein":"Post-activation (multiple)",
              "mechanism":"Identical pattern to β-arrestin 1. ZERO germline pathogenic variants in human populations despite extensive in vitro study.",
              "partners":["FLNA","All GPCRs"],
              "paper":"Premont RT, Gainetdinov RR. Annu Rev Physiol 2007;69:511-534",
              "note":"Mouse knockouts viable. Human variants tolerated. Reassess all drug discovery programs targeting β-arrestin."},
    "CHRM2": {"type":"IS A GPCR — Muscarinic M2","color":"#FFA500","g_protein":"Gi/o",
              "mechanism":"Acetylcholine binds CHRM2 → Gαi dissociates → adenylate cyclase inhibited → cAMP falls → PKA reduced → GIRK channels open → cardiac slowing. 102 dominant pathogenic variants cause dilated cardiomyopathy.",
              "partners":["FLNA","Gαi","Adenylate cyclase","GIRK channels","β-arrestin (desensitisation)"],
              "paper":"Bristow MR et al. Circulation 1989;82:12-25 — muscarinic receptor in heart failure"},
    "CHRM3": {"type":"IS A GPCR — Muscarinic M3","color":"#FFD700","g_protein":"Gq/11",
              "mechanism":"Acetylcholine → CHRM3 → Gαq → PLCβ → PIP2→IP3+DAG → Ca²⁺ release → smooth muscle contraction. Frameshift mutations disrupt bladder smooth muscle → Prune belly syndrome.",
              "partners":["FLNA","Gαq","PLCβ","IP3 receptor","PKC"],
              "paper":"Weber S et al. Am J Hum Genet 2011;89:468-474 — CHRM3 frameshift causes PBS"},
}

G_CASCADES = {
    "Gi/o": {"steps":["Agonist binds GPCR","Gαi·GDP→GTP","Adenylate cyclase INHIBITED","cAMP FALLS","PKA activity reduced","GIRK channel opening","Cell hyperpolarisation"],"color":"#4CA8FF","effects":["↓Heart rate","Analgesia","↓cAMP signalling"]},
    "Gq/11":{"steps":["Agonist binds GPCR","Gαq·GDP→GTP","PLCβ ACTIVATED","PIP2 → IP3+DAG","IP3→Ca²⁺ release","PKC activation","Smooth muscle contracts"],"color":"#9370DB","effects":["Smooth muscle contraction","Secretion","Cell proliferation"]},
    "Gs":   {"steps":["Agonist binds GPCR","Gαs·GDP→GTP","Adenylate cyclase ACTIVATED","cAMP RISES","PKA activation","Target phosphorylation","Cell response"],"color":"#FFA500","effects":["↑Heart rate","Bronchodilation","Lipolysis"]},
}

def build_tissue_diagram(gene_name: str, tissue_text: str = "", known_tissues: dict = None) -> str:
    gu = gene_name.upper()
    tissues = TISSUE_DATA.get(gu) or known_tissues or {}
    if not tissues and tissue_text:
        for lv,pat in [(3,r'high\w*\s+in\s+([^.,;]{3,25})'),(2,r'moderate\w*\s+in\s+([^.,;]{3,25})'),(1,r'low\w*\s+in\s+([^.,;]{3,25})')]:
            for m in re.findall(pat, tissue_text, re.I):
                tissues[m.strip()[:20]] = lv
    if not tissues:
        return _no_data(gene_name,"tissue","Run with DB enrichment enabled to load tissue expression data")
    items = list(tissues.items())[:12]
    lc={3:"#FF4C4C",2:"#FFA500",1:"#4CA8FF",0:"#2a2d3a"}; lb={3:"HIGH",2:"MED",1:"LOW",0:"ABSENT"}
    cols=min(3,len(items)); rows=(len(items)+cols-1)//cols
    W=600; cw=W//cols; rh=54; H=40+rows*rh+50
    cells=""
    for i,(t,lv) in enumerate(items):
        cx=(i%cols)*cw+4; cy=35+i//cols*rh+2; c=lc.get(lv,"#555"); nm=t[:20]+"…" if len(t)>20 else t
        cells+=f'<rect x="{cx}" y="{cy}" width="{cw-8}" height="{rh-6}" rx="6" fill="{c}22" stroke="{c}" stroke-width="1.5"/>'
        cells+=f'<text x="{cx+8}" y="{cy+17}" font-size="9" fill="{c}" font-family="IBM Plex Mono,monospace" font-weight="600">{lb.get(lv,"—")}</text>'
        cells+=f'<text x="{cx+8}" y="{cy+33}" font-size="10" fill="#bbb" font-family="Inter,sans-serif">{nm}</text>'
    leg="".join(f'<rect x="{10+i*130}" y="{H-30}" width="12" height="12" rx="3" fill="{c}44" stroke="{c}" stroke-width="1"/><text x="{26+i*130}" y="{H-21}" font-size="9" fill="#666" font-family="Inter,sans-serif">{l}</text>' for i,(c,l) in enumerate([("#FF4C4C","High"),("#FFA500","Medium"),("#4CA8FF","Low"),("#2a2d3a","Absent")]))
    src="Curated: UniProt + Protein Atlas" if gu in TISSUE_DATA else "UniProt tissue specificity"
    svg=f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg"><rect width="{W}" height="{H}" fill="#080b14"/><text x="{W//2}" y="24" text-anchor="middle" font-size="12" font-family="IBM Plex Mono,monospace" font-weight="700" fill="#eee">{gene_name} — Tissue Expression</text>{cells}{leg}<text x="{W//2}" y="{H-5}" text-anchor="middle" font-size="8" fill="#333" font-family="Inter,sans-serif">Source: {src}</text></svg>'
    return _wrap(svg)

def build_genomic_diagram(gene_name: str, chromosome: str, protein_length: int,
                           domains: list, variants_pathogenic: list, variants_benign: list = None) -> str:
    W,H=620,220; tx,tw,ty,th=50,520,100,24
    def px(p):
        if not protein_length: return tx
        return tx+int((min(p,protein_length)/protein_length)*tw)
    dc=["#9370DB","#4CA8FF","#FFA500","#4CAF50","#FF6B9D","#00BCD4","#FF4C4C","#FFD700"]
    doms=""
    for i,d in enumerate(domains[:8]):
        dx=px(d.get("start",1)); dw=max(px(d.get("end",d.get("start",1)))-dx,3); c=dc[i%len(dc)]; nm=d.get("name","")[:12]
        doms+=f'<rect x="{dx}" y="{ty}" width="{dw}" height="{th}" fill="{c}55" stroke="{c}" stroke-width="1.5" rx="3"/>'
        if dw>28: doms+=f'<text x="{dx+dw//2}" y="{ty+15}" text-anchor="middle" font-size="7" fill="{c}" font-family="IBM Plex Mono,monospace">{nm}</text>'
    pticks=""; seen=set()
    for v in (variants_pathogenic or [])[:80]:
        pos=v.get("pos",0) or v.get("position",0)
        if not pos: continue
        vx=px(int(pos))
        if any(abs(vx-s)<2 for s in seen): continue
        seen.add(vx)
        pticks+=f'<line x1="{vx}" y1="{ty-14}" x2="{vx}" y2="{ty}" stroke="#FF4C4C" stroke-width="1.5" opacity="0.9"/><circle cx="{vx}" cy="{ty-16}" r="2.5" fill="#FF4C4C" opacity="0.9"/>'
    bticks=""; seen2=set()
    for v in (variants_benign or [])[:50]:
        pos=v.get("pos",0) or v.get("position",0)
        if not pos: continue
        vx=px(int(pos))
        if any(abs(vx-s)<2 for s in seen2): continue
        seen2.add(vx)
        bticks+=f'<line x1="{vx}" y1="{ty+th}" x2="{vx}" y2="{ty+th+12}" stroke="#4CA8FF" stroke-width="1.2" opacity="0.7"/><circle cx="{vx}" cy="{ty+th+14}" r="2" fill="#4CA8FF" opacity="0.8"/>'
    ruler="".join(f'<line x1="{tx+int(p/100*tw)}" y1="{ty+th}" x2="{tx+int(p/100*tw)}" y2="{ty+th+5}" stroke="#2a2d3a" stroke-width="1"/><text x="{tx+int(p/100*tw)}" y="{ty+th+15}" text-anchor="middle" font-size="8" fill="#555" font-family="IBM Plex Mono,monospace">{int(p/100*(protein_length or 100))}</text>' for p in [0,25,50,75,100])
    np=len(variants_pathogenic or []); nb=len(variants_benign or [])
    chrom=f"Chr {chromosome}" if chromosome else "Chr —"
    svg=f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg"><rect width="{W}" height="{H}" fill="#080b14"/><text x="{W//2}" y="18" text-anchor="middle" font-size="12" font-family="IBM Plex Mono,monospace" font-weight="700" fill="#eee">{gene_name} — Protein &amp; Variant Map</text><rect x="10" y="26" width="72" height="18" rx="9" fill="#9370DB22" stroke="#9370DB" stroke-width="1.5"/><text x="46" y="38" text-anchor="middle" font-size="8" font-family="IBM Plex Mono,monospace" fill="#9370DB">{chrom}</text><text x="90" y="38" font-size="8" font-family="IBM Plex Mono,monospace" fill="#555">{protein_length} aa</text><text x="{W-8}" y="38" text-anchor="end" font-size="8" font-family="IBM Plex Mono,monospace" fill="#FF4C4C">▲{np} path.</text><text x="{W-8}" y="50" text-anchor="end" font-size="8" font-family="IBM Plex Mono,monospace" fill="#4CA8FF">▼{nb} benign</text><text x="{tx}" y="{ty-20}" font-size="8" fill="#FF4C4C" font-family="IBM Plex Mono,monospace">Pathogenic (ClinVar germline)</text><text x="{tx}" y="{ty+th+26}" font-size="8" fill="#4CA8FF" font-family="IBM Plex Mono,monospace">Benign variants</text><rect x="{tx}" y="{ty}" width="{tw}" height="{th}" fill="#0f1117" stroke="#1e2030" stroke-width="1.5" rx="4"/><text x="{tx+6}" y="{ty+15}" font-size="8" fill="#2a2d3a" font-family="Inter,sans-serif">N</text><text x="{tx+tw-12}" y="{ty+15}" font-size="8" fill="#2a2d3a" font-family="Inter,sans-serif">C</text>{doms}{pticks}{bticks}{ruler}<text x="{W//2}" y="{H-5}" text-anchor="middle" font-size="8" fill="#333" font-family="Inter,sans-serif">Source: UniProt domain annotations · ClinVar germline pathogenic variant positions</text></svg>'
    return _wrap(svg)

def build_gpcr_association_diagram(gene_name: str, g_protein: str = "", protein_name: str = "", is_gpcr: bool = False) -> str:
    """GPCR ASSOCIATION — not just whether protein is a GPCR. Shows how it interacts with the GPCR pathway."""
    gu=gene_name.upper(); assoc=GPCR_ASSOC.get(gu); W,H=640,330
    if not assoc and not is_gpcr:
        return _no_data(gene_name,"GPCR association",f"{gene_name} has no curated GPCR association. Check UniProt 'interacts with' section and IUPHAR for GPCR interaction partners.")
    if assoc:
        atype=assoc["type"]; color=assoc["color"]; mech=assoc["mechanism"][:160]
        partners=assoc["partners"][:5]; paper=assoc["paper"]; note=assoc.get("note","")[:120]
        gp=assoc["g_protein"]
    else:
        atype="IS A GPCR"; color="#9370DB"; gp=g_protein or "—"; mech=f"{gene_name} is a GPCR. {g_protein} coupling."
        partners=[]; paper="IUPHAR/BPS Guide to Pharmacology"; note=""
    # Cascade boxes
    gp_key=g_protein if g_protein in G_CASCADES else ("Gi/o" if "i" in gp.lower() else "Gq/11" if "q" in gp.lower() else "Gs" if "s" in gp.lower() else None)
    cascade=G_CASCADES.get(gp_key,{})
    steps=cascade.get("steps",[]) if (is_gpcr or atype.startswith("IS A")) else partners[:6]
    cc=cascade.get("color",color) if cascade else color
    bw,bh,bg=82,28,8; total=len(steps); sx=max(8,(W-total*(bw+bg))//2)
    boxes=""; arrows=""
    for i,s in enumerate(steps[:7]):
        bx=sx+i*(bw+bg); by=135; alpha=max(0.4,1-i*0.07); short=s[:14]+"…" if len(s)>14 else s
        boxes+=f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="5" fill="{cc}22" stroke="{cc}" stroke-width="1.5" opacity="{alpha}"/>'
        boxes+=f'<text x="{bx+bw//2}" y="{by+12}" text-anchor="middle" font-size="7" fill="{cc}" font-family="IBM Plex Mono,monospace" font-weight="600" opacity="{alpha}">{i+1}</text>'
        boxes+=f'<text x="{bx+bw//2}" y="{by+23}" text-anchor="middle" font-size="6.5" fill="#bbb" font-family="Inter,sans-serif" opacity="{alpha}">{short}</text>'
        if i<len(steps)-1:
            ax=bx+bw+1; ay=by+bh//2
            arrows+=f'<line x1="{ax}" y1="{ay}" x2="{ax+bg-2}" y2="{ay}" stroke="{cc}" stroke-width="1.5" opacity="0.5"/>'
    # Partner pills
    pills="".join(f'<rect x="{10+i*118}" y="190" width="110" height="22" rx="11" fill="{color}22" stroke="{color}66" stroke-width="1"/><text x="{65+i*118}" y="205" text-anchor="middle" font-size="8.5" fill="{color}" font-family="IBM Plex Mono,monospace">{p}</text>' for i,p in enumerate(partners[:5]))
    mech1=mech[:95]; mech2=mech[95:] if len(mech)>95 else ""
    note_svg=f'<text x="{W//2}" y="248" text-anchor="middle" font-size="8" fill="#556" font-family="Inter,sans-serif" font-style="italic">{note[:100]}</text>' if note else ""
    aw=len(atype)*7+20
    svg=f'''<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
<rect width="{W}" height="{H}" fill="#080b14"/>
<text x="{W//2}" y="19" text-anchor="middle" font-size="12" font-family="IBM Plex Mono,monospace" font-weight="700" fill="#eee">{gene_name} — GPCR Association</text>
<rect x="8" y="26" width="{aw}" height="18" rx="9" fill="{color}33" stroke="{color}" stroke-width="1.5"/>
<text x="{8+aw//2}" y="38" text-anchor="middle" font-size="8" font-family="IBM Plex Mono,monospace" fill="{color}" font-weight="600">{atype}</text>
<text x="{8+aw+8}" y="38" font-size="8" fill="#555" font-family="IBM Plex Mono,monospace">G-protein: <tspan fill="{color}" font-weight="600">{gp}</tspan></text>
<text x="8" y="58" font-size="9" fill="#888" font-family="Inter,sans-serif">{mech1}</text>
{"" if not mech2 else f'<text x="8" y="70" font-size="9" fill="#888" font-family="Inter,sans-serif">{mech2}</text>'}
<text x="8" y="128" font-size="8" font-family="IBM Plex Mono,monospace" fill="{cc}" opacity="0.7">{'Signal cascade:' if is_gpcr or atype.startswith("IS A") else 'Interaction partners / cascade:'}</text>
{boxes}{arrows}
<text x="8" y="183" font-size="8" font-family="IBM Plex Mono,monospace" fill="{color}" opacity="0.7">Associated with:</text>
{pills}
{note_svg}
<text x="{W//2}" y="270" text-anchor="middle" font-size="8" fill="#444" font-family="Inter,sans-serif">📄 {paper}</text>
<text x="{W//2}" y="284" text-anchor="middle" font-size="8" fill="#333" font-family="Inter,sans-serif">All disease evidence from ClinVar germline variants only — not cell culture or animal models</text>
<text x="{W//2}" y="298" text-anchor="middle" font-size="8" fill="#4CA8FF" font-family="Inter,sans-serif">King et al Nature 2024: genetic support gives 2.6x better drug success rate</text>
</svg>'''
    return _wrap(svg)

def build_gpcr_diagram(gene_name: str, g_protein: str, protein_name: str = "", n_tm: int = 7) -> str:
    return build_gpcr_association_diagram(gene_name, g_protein, protein_name, True)

def build_cell_impact_diagram(gene_name: str, tier: str, n_pathogenic: int,
                               diseases: list, subcellular: list,
                               is_gpcr: bool = False, g_protein: str = "") -> str:
    W,H=640,300; tc={"CRITICAL":"#FF4C4C","HIGH":"#FFA500","LOW":"#FFD700","NONE":"#888","UNKNOWN":"#4CA8FF"}.get(tier,"#888")
    dis_s=diseases[0][:32] if diseases else "No confirmed disease"
    gu=gene_name.upper(); assoc=GPCR_ASSOC.get(gu,{}); atype=assoc.get("type","")
    if tier=="NONE": impact="No confirmed pathology"; sub="Zero germline variants — β-arrestin pattern"
    elif n_pathogenic>500: impact=f"CRITICAL: {dis_s}"; sub=f"{n_pathogenic} pathogenic variants"
    elif n_pathogenic>0: impact=f"CONFIRMED: {dis_s}"; sub=f"{n_pathogenic} pathogenic variant(s)"
    else: impact="Uncharacterised"; sub="Insufficient ClinVar data"
    ccx,ccy,crx,cry=175,155,140,115; ncx,ncy,nr=175,155,42
    locs="".join(f'<rect x="{360+(i%2)*128}" y="{55+(i//2)*40}" width="118" height="24" rx="12" fill="#4CA8FF22" stroke="#4CA8FF55" stroke-width="1"/><text x="{419+(i%2)*128}" y="{71+(i//2)*40}" text-anchor="middle" font-size="8.5" fill="#4CA8FF" font-family="IBM Plex Mono,monospace">{loc[:16]}</text>' for i,loc in enumerate(subcellular[:4]))
    gc=assoc.get("color","#9370DB") if atype else ""
    gpcr_svg=""
    if atype:
        gpcr_svg=f'<rect x="{ccx-crx+10}" y="{ccy-cry+10}" width="55" height="36" rx="4" fill="{gc}44" stroke="{gc}" stroke-width="2"/><text x="{ccx-crx+38}" y="{ccy-cry+25}" text-anchor="middle" font-size="7.5" fill="{gc}" font-family="IBM Plex Mono,monospace" font-weight="600">{gene_name[:7]}</text><text x="{ccx-crx+38}" y="{ccy-cry+36}" text-anchor="middle" font-size="6.5" fill="{gc}aa" font-family="IBM Plex Mono,monospace">{atype[:13]}</text>'
    svg=f'''<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
<rect width="{W}" height="{H}" fill="#080b14"/>
<text x="{W//2}" y="18" text-anchor="middle" font-size="12" font-family="IBM Plex Mono,monospace" font-weight="700" fill="#eee">{gene_name} — Cell Impact</text>
<ellipse cx="{ccx}" cy="{ccy}" rx="{crx}" ry="{cry}" fill="#0a0c14" stroke="#1e2030" stroke-width="2"/>
<ellipse cx="{ncx}" cy="{ncy}" rx="{nr}" ry="{nr-7}" fill="#0f1117" stroke="#2a2d3a" stroke-width="1.5"/>
<text x="{ncx}" y="{ncy-2}" text-anchor="middle" font-size="7.5" fill="#3a3d5a" font-family="IBM Plex Mono,monospace">Nucleus</text>
{gpcr_svg}
<circle cx="{ccx+50}" cy="{ccy-28}" r="15" fill="{tc}33" stroke="{tc}" stroke-width="2"/>
<text x="{ccx+50}" y="{ccy-23}" text-anchor="middle" font-size="7" fill="{tc}" font-family="IBM Plex Mono,monospace">{gene_name[:6]}</text>
<rect x="352" y="150" width="272" height="92" rx="8" fill="{tc}11" stroke="{tc}55" stroke-width="1.5"/>
<text x="488" y="170" text-anchor="middle" font-size="9" fill="{tc}" font-family="IBM Plex Mono,monospace" font-weight="600">When mutated:</text>
<text x="488" y="185" text-anchor="middle" font-size="9" fill="#eee" font-family="Inter,sans-serif">{impact[:34]}</text>
<text x="488" y="199" text-anchor="middle" font-size="8.5" fill="#888" font-family="Inter,sans-serif">{sub[:38]}</text>
<rect x="362" y="210" width="252" height="22" rx="11" fill="{tc}22" stroke="{tc}66" stroke-width="1"/>
<text x="488" y="225" text-anchor="middle" font-size="8.5" font-family="IBM Plex Mono,monospace" fill="{tc}" font-weight="600">ClinVar: {n_pathogenic} germline pathogenic</text>
<text x="352" y="42" font-size="8" font-family="IBM Plex Mono,monospace" fill="#4CA8FF" opacity="0.7">Subcellular locations (UniProt)</text>
{locs}
<text x="{W//2}" y="{H-6}" text-anchor="middle" font-size="8" fill="#333" font-family="Inter,sans-serif">Source: UniProt · ClinVar · Germline variants only · Not text-mined</text>
</svg>'''
    return _wrap(svg)

def _no_data(gene, dtype, msg):
    return f"<!DOCTYPE html><html><head><style>body{{margin:0;background:#080b14;display:flex;align-items:center;justify-content:center;height:260px;font-family:'IBM Plex Mono',monospace;text-align:center;color:#444}}</style></head><body><div><div style='font-size:1.2rem;margin-bottom:8px'>🔬</div><div style='font-size:10px;color:#555'>{gene} — {dtype}</div><div style='font-size:9px;margin-top:8px;color:#333;max-width:300px;line-height:1.6'>{msg}</div></div></body></html>"

def _wrap(svg):
    return f"<!DOCTYPE html><html><head><style>body{{margin:0;background:#080b14;overflow:hidden}}svg{{display:block;width:100%}}</style></head><body>{svg}</body></html>"
