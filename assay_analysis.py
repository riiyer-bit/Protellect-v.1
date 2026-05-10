"""
Wet-lab and dry-lab assay data analysis module.
Handles: western blots (densitometry), ELISA, TSA/DSF, Co-IP quantification,
RNA-seq summary stats, proteomics, 16S OTU tables, mass spec.
"""
import streamlit as st, pandas as pd, numpy as np
import plotly.graph_objects as go
import plotly.express as px
import io, re, json
import anthropic

def _client():
    return anthropic.Anthropic()

def detect_assay_type(df: pd.DataFrame, filename: str = "") -> str:
    """Auto-detect the type of assay data from column names and filename."""
    cols = " ".join(df.columns.astype(str)).lower()
    fname = filename.lower()

    if any(x in cols for x in ["deltacp","delta ct","dct","ct value","cq"]): return "qpcr"
    if any(x in cols for x in ["tm","melting temperature","fluorescence","rfu","delta f"]): return "tsf_dsf"
    if any(x in cols for x in ["absorbance","od450","optical density","elisa"]): return "elisa"
    if any(x in cols for x in ["intensity","band","kda","molecular weight"]): return "western"
    if any(x in cols for x in ["log2fc","log2foldchange","padj","pvalue","basemean"]): return "rnaseq"
    if any(x in cols for x in ["peptide","protein group","razor","lfq intensity","ms/ms"]): return "proteomics"
    if any(x in cols for x in ["otu","asv","taxon","species","genus","phylum","16s"]): return "16s_microbiome"
    if any(x in cols for x in ["scfa","butyrate","propionate","acetate","tmao","metabolite"]): return "metabolomics"
    if any(x in cols for x in ["ic50","ec50","ki","kd","hill"]): return "binding_kinetics"
    if any(x in cols for x in ["rfu/s","kcat","km","vmax","velocity"]): return "enzyme_kinetics"
    if "western" in fname or "blot" in fname: return "western"
    if "elisa" in fname: return "elisa"
    if "16s" in fname or "microbiome" in fname or "otu" in fname: return "16s_microbiome"
    if "rnaseq" in fname or "deseq" in fname: return "rnaseq"
    return "generic"

def analyse_tsf_dsf(df: pd.DataFrame, gene: str = "", lab_context: str = "") -> dict:
    """Analyse Thermal Shift Assay (TSF/DSF) data — Tm comparison WT vs variants."""
    results = {}
    # Try to find Tm column
    tm_col = next((c for c in df.columns if any(x in c.lower() for x in ["tm","melting","temp"])), None)
    sample_col = next((c for c in df.columns if any(x in c.lower() for x in ["sample","name","protein","variant","condition"])), None)

    if tm_col and sample_col:
        df[tm_col] = pd.to_numeric(df[tm_col], errors="coerce")
        grouped = df.groupby(sample_col)[tm_col].agg(["mean","std","count"]).reset_index()

        # Find WT / reference
        wt_row = grouped[grouped[sample_col].str.lower().str.contains("wt|wild|control|ref", na=False)]
        wt_tm = float(wt_row["mean"].iloc[0]) if len(wt_row) > 0 else None

        fig = go.Figure()
        for _, row in grouped.iterrows():
            tm_val = row["mean"]; std_val = row["std"] if not pd.isna(row["std"]) else 0
            delta_tm = round(tm_val - wt_tm, 2) if wt_tm else None
            is_wt = "wt" in str(row[sample_col]).lower() or "control" in str(row[sample_col]).lower()
            # Classify
            if is_wt: color = "#00e5ff"; interpretation = "WT reference"
            elif delta_tm is not None:
                if delta_tm <= -2.0: color = "#ff2d55"; interpretation = f"ΔTm {delta_tm}°C — structurally destabilising → pharmacochaperone screen"
                elif delta_tm >= 2.0: color = "#00c896"; interpretation = f"ΔTm +{delta_tm}°C — stabilised (hit compound or stabilising variant)"
                else: color = "#ffd60a"; interpretation = f"ΔTm {delta_tm}°C — marginal change; functional mechanism likely"
            else: color = "#5a8090"; interpretation = "No WT reference for comparison"

            fig.add_trace(go.Bar(x=[str(row[sample_col])], y=[tm_val],
                                  error_y=dict(type="data", array=[std_val]),
                                  marker_color=color, name=str(row[sample_col]),
                                  hovertemplate=f"{row[sample_col]}<br>Tm: {tm_val:.1f}°C<br>{interpretation}<extra></extra>"))

        if wt_tm:
            fig.add_hline(y=wt_tm, line_dash="dash", line_color="#00e5ff",
                          annotation_text=f"WT Tm={wt_tm:.1f}°C", annotation_font_color="#00e5ff")

        fig.update_layout(height=350, plot_bgcolor="#010306", paper_bgcolor="#010306",
                          font=dict(color="#d0e8ff",size=11), margin=dict(l=40,r=20,t=40,b=80),
                          title=dict(text=f"Thermal Shift Assay (DSF) — {gene or 'Protein'} WT vs Variants",font=dict(color="#a855f7",size=12)),
                          xaxis=dict(title="Sample",gridcolor="#0d2545",tickangle=45),
                          yaxis=dict(title="Melting temperature (°C)",gridcolor="#0d2545"),
                          showlegend=False)
        results["figure"] = fig
        results["wt_tm"] = wt_tm
        results["grouped"] = grouped
    return results

def analyse_rnaseq(df: pd.DataFrame, gene: str = "", lab_context: str = "") -> dict:
    """Analyse RNA-seq differential expression results."""
    # Find key columns
    lfc_col = next((c for c in df.columns if "log2" in c.lower() and "fold" in c.lower()), None)
    pval_col = next((c for c in df.columns if "padj" in c.lower() or "fdr" in c.lower() or "p_adj" in c.lower()), None)
    gene_col = next((c for c in df.columns if any(x in c.lower() for x in ["gene","symbol","name"])), df.columns[0] if len(df.columns)>0 else None)

    if not lfc_col or not pval_col:
        return {"error": "Could not identify log2FC or adjusted p-value columns. Expected columns containing 'log2', 'fold', 'padj', or 'fdr'."}

    df[lfc_col] = pd.to_numeric(df[lfc_col], errors="coerce")
    df[pval_col] = pd.to_numeric(df[pval_col], errors="coerce")
    df = df.dropna(subset=[lfc_col, pval_col])

    # Classify
    df["neg_log_p"] = -np.log10(df[pval_col].clip(lower=1e-300))
    df["sig"] = ((df[pval_col] < 0.05) & (df[lfc_col].abs() > 1))
    df["direction"] = df[lfc_col].apply(lambda x: "Up" if x>1 else ("Down" if x<-1 else "NS"))

    up = (df["sig"] & (df[lfc_col]>0)).sum()
    down = (df["sig"] & (df[lfc_col]<0)).sum()

    # Volcano plot
    colors = {"Up":"#ff2d55","Down":"#4a90d9","NS":"#3a5a7a"}
    fig = px.scatter(df, x=lfc_col, y="neg_log_p", color="direction",
                     color_discrete_map=colors, hover_name=gene_col if gene_col else None,
                     labels={lfc_col:"log₂ Fold Change", "neg_log_p":"-log₁₀(adj. p-value)"},
                     title=f"Volcano Plot — DEGs (up: {up}, down: {down})")
    fig.add_hline(y=-np.log10(0.05), line_dash="dash", line_color="#ffd60a")
    fig.add_vline(x=1, line_dash="dash", line_color="#ffd60a")
    fig.add_vline(x=-1, line_dash="dash", line_color="#ffd60a")
    fig.update_layout(height=400, plot_bgcolor="#010306", paper_bgcolor="#010306",
                      font=dict(color="#d0e8ff",size=11), margin=dict(l=40,r=20,t=40,b=40))

    # Top hits
    top_up = df[df["sig"]&(df[lfc_col]>0)].nlargest(10, lfc_col)
    top_dn = df[df["sig"]&(df[lfc_col]<0)].nsmallest(10, lfc_col)

    return {"figure":fig, "n_up":int(up), "n_down":int(down), "top_up":top_up, "top_down":top_dn, "df":df}

def analyse_16s_microbiome(df: pd.DataFrame, lab_context: str = "") -> dict:
    """Analyse 16S OTU/ASV table — diversity, relative abundance, key taxa."""
    # Find taxonomy column
    tax_col = next((c for c in df.columns if any(x in c.lower() for x in ["taxon","taxonomy","species","genus","phylum","otu","asv"])), df.columns[0])
    # Numeric columns = samples
    num_cols = [c for c in df.columns if c != tax_col and pd.to_numeric(df[c], errors="coerce").notna().sum() > 0]

    if not num_cols:
        return {"error": "Could not identify sample abundance columns."}

    df_num = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    total_per_sample = df_num.sum()
    rel_abund = df_num.div(total_per_sample, axis=1) * 100

    # Top 10 taxa
    df["mean_rel_abund"] = rel_abund.mean(axis=1)
    top10 = df.nlargest(10, "mean_rel_abund")

    fig = px.bar(top10, x=tax_col, y="mean_rel_abund",
                 title="Top 10 Taxa — Mean Relative Abundance (%)",
                 labels={"mean_rel_abund": "Mean Relative Abundance (%)"},
                 color="mean_rel_abund", color_continuous_scale="Viridis")
    fig.update_layout(height=380, plot_bgcolor="#010306", paper_bgcolor="#010306",
                      font=dict(color="#d0e8ff",size=11), xaxis_tickangle=45,
                      coloraxis_showscale=False)

    # Alpha diversity (Shannon)
    def shannon(row):
        p = row[row>0]/row.sum()
        return -sum(p*np.log(p)) if len(p)>0 else 0
    alpha_div = rel_abund.apply(shannon, axis=0)

    taxa_list = top10[tax_col].tolist()
    return {"figure":fig, "top_taxa":taxa_list, "alpha_diversity":alpha_div.to_dict(), "n_taxa":len(df), "n_samples":len(num_cols)}

def analyse_with_llm(df: pd.DataFrame, assay_type: str, gene: str = "", lab_context: str = "", extra_context: str = "") -> str:
    """Use Claude to interpret assay results in context of the protein/gene being studied."""
    # Prepare data summary for LLM
    summary = f"Assay type: {assay_type}\n"
    summary += f"Dimensions: {df.shape[0]} rows × {df.shape[1]} columns\n"
    summary += f"Columns: {list(df.columns)}\n"
    summary += f"First 5 rows:\n{df.head().to_string()}\n"
    summary += f"Statistical summary:\n{df.describe().to_string()}\n"

    prompt = f"""You are a senior biomedical scientist interpreting laboratory assay data.

Gene/protein being studied: {gene or 'Unknown'}
Lab research context: {lab_context or 'General biomedical research'}
{f"Additional context: {extra_context}" if extra_context else ""}

Assay data summary:
{summary}

Provide a rigorous scientific interpretation:

1. **Data quality assessment**: Are the results technically valid? Any red flags (CV% too high, control failures)?
2. **Key findings**: What does this data tell us about {gene or 'the protein'} function?
3. **Statistical interpretation**: What conclusions can be drawn with what confidence level?
4. **Biological interpretation**: What does this mean mechanistically?
5. **Next experiments**: What is the logical follow-on experiment based on these results?
6. **Potential issues**: What technical artefacts or confounders could affect these results?
7. **ClinVar relevance**: How do these findings relate to known disease-causing variants (if applicable)?

Be specific — avoid vague statements like "results suggest a role in" — state exactly what is shown and what it means.
Note any statistical issues without being asked."""

    try:
        client = _client()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role":"user","content":prompt}]
        )
        return "".join(block.text for block in response.content if hasattr(block,"text"))
    except Exception as e:
        return f"AI analysis unavailable: {str(e)}"

def render_assay_analysis_tab(gene: str, color: str, lab_profile: dict = None):
    """Full assay data analysis tab."""
    lab_context = ""
    if lab_profile:
        lab_context = f"{lab_profile.get('lab_name','')}: {lab_profile.get('research_goal','')}"

    st.markdown("<div style='color:#5a8090;font-size:.82rem;margin-bottom:.8rem'>Upload wet-lab or dry-lab assay data for AI-assisted interpretation. Supported: TSA/DSF, western blot densitometry, RNA-seq DEG tables, 16S OTU tables, ELISA, proteomics, metabolomics, binding kinetics.</div>", unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload assay data (CSV, TSV, Excel)", type=["csv","tsv","xlsx","xls"], key=f"assay_upload_{gene}")

    if uploaded:
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            elif uploaded.name.endswith(".tsv"):
                df = pd.read_csv(uploaded, sep="\t")
            else:
                df = pd.read_excel(uploaded)

            assay_type = detect_assay_type(df, uploaded.name)
            st.markdown(f"<div style='background:#040c14;border:1px solid {color}44;border-radius:8px;padding:.5rem 1rem;margin-bottom:.5rem'><span style='color:{color};font-weight:600'>Detected assay type:</span> <span style='color:#d0e8ff'>{assay_type.replace('_',' ').upper()}</span> &nbsp; ({df.shape[0]} rows, {df.shape[1]} columns)</div>", unsafe_allow_html=True)

            override = st.selectbox("Override assay type:", ["Auto-detected","tsf_dsf","western","elisa","rnaseq","16s_microbiome","proteomics","metabolomics","binding_kinetics","generic"], key=f"assay_type_{gene}")
            if override != "Auto-detected": assay_type = override

            with st.expander("📋 Preview data", expanded=False):
                st.dataframe(df.head(10), use_container_width=True)

            if assay_type == "tsf_dsf":
                result = analyse_tsf_dsf(df, gene, lab_context)
                if result.get("figure"): st.plotly_chart(result["figure"], use_container_width=True)
                if result.get("grouped") is not None:
                    st.markdown("<div style='color:#5a8090;font-size:.78rem;font-weight:600;margin:.4rem 0'>Interpretation guide: ΔTm ≤-2°C = structurally destabilising → pharmacochaperone screen. ΔTm ≥2°C = stabilised compound hit.</div>", unsafe_allow_html=True)

            elif assay_type == "rnaseq":
                result = analyse_rnaseq(df, gene, lab_context)
                if "error" in result: st.error(result["error"])
                else:
                    st.plotly_chart(result["figure"], use_container_width=True)
                    c1,c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Top upregulated genes ({result['n_up']} total)**")
                        if not result["top_up"].empty: st.dataframe(result["top_up"].head(8), use_container_width=True)
                    with c2:
                        st.markdown(f"**Top downregulated genes ({result['n_down']} total)**")
                        if not result["top_down"].empty: st.dataframe(result["top_down"].head(8), use_container_width=True)

            elif assay_type == "16s_microbiome":
                result = analyse_16s_microbiome(df, lab_context)
                if "error" in result: st.error(result["error"])
                else:
                    st.plotly_chart(result["figure"], use_container_width=True)
                    st.markdown(f"**Total taxa:** {result['n_taxa']} · **Samples:** {result['n_samples']}")

            else:
                st.dataframe(df.describe(), use_container_width=True)

            # AI interpretation
            st.markdown("---")
            extra_ctx = st.text_area("Additional experimental context for AI analysis (optional)", placeholder="e.g. 'Cells were treated with 10µM of compound X for 24h before lysis. Western probed with anti-pSer2152 antibody.'", key=f"extra_ctx_{gene}", height=80)
            if st.button("🤖 AI Interpret Results", key=f"ai_assay_{gene}", type="primary"):
                with st.spinner("Claude is interpreting your assay data..."):
                    interpretation = analyse_with_llm(df, assay_type, gene, lab_context, extra_ctx)
                st.markdown("<div style='background:#020d10;border:1px solid #00e5ff33;border-radius:10px;padding:1rem 1.2rem;margin-top:.5rem'>", unsafe_allow_html=True)
                st.markdown(interpretation)
                st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error reading file: {e}")
