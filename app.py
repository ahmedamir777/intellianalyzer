
import json
from io import BytesIO
import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = "https://amplify-ivy-poster.ngrok-free.dev"

st.set_page_config(
    page_title="Intellianalyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# SESSION STATE
# ============================================================

DEFAULTS = {
    "analysis": None,
    "chat_history": [],
    "report_filename": None,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# DESIGN SYSTEM
# ============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --bg: #0B0F17;
    --panel: #141A26;
    --panel2: #1A2130;
    --accent: #9B8AFF;
    --accent2: #59DCC0;
    --text: #F4F5FC;
    --muted: #9DA8BC;
    --border: rgba(173, 185, 210, .14);
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background:
        radial-gradient(ellipse at 85% 0%, rgba(124, 104, 255, .10), transparent 34%),
        var(--bg);
}

h1, h2, h3 {
    font-family: 'Space Grotesk', sans-serif !important;
    letter-spacing: -.5px;
}

[data-testid="stSidebar"] {
    background: #111722;
    border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] hr {
    border-color: var(--border);
}

.hero {
    background: linear-gradient(120deg, #242344 0%, #202B40 58%, #16382F 100%);
    border: 1px solid rgba(255,255,255,.10);
    border-radius: 23px;
    padding: 30px;
    margin-bottom: 22px;
}

.eyebrow {
    color: #C3B8FF;
    text-transform: uppercase;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    margin-bottom: 12px;
}

.hero-title {
    color: white;
    font-family: 'Space Grotesk', sans-serif;
    font-size: clamp(30px, 4vw, 43px);
    line-height: 1.15;
    font-weight: 700;
    margin-bottom: 12px;
}

.hero-subtitle {
    color: #C3CCDB;
    font-size: 15px;
    line-height: 1.8;
    max-width: 720px;
}

.section-eyebrow {
    color: #B7A9FF;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 5px;
}

.metric-card {
    background: linear-gradient(145deg, #1B2231, #141A25);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 19px;
    min-height: 116px;
}

.metric-label {
    color: var(--muted);
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 10px;
}

.metric-value {
    color: var(--text);
    font-family: 'Space Grotesk', sans-serif;
    font-size: 28px;
    font-weight: 700;
}

.metric-note {
    color: #8D9AB0;
    font-size: 11px;
    margin-top: 7px;
}

.insight-card {
    background: linear-gradient(145deg, #1A2232, #151B27);
    border: 1px solid var(--border);
    border-radius: 15px;
    padding: 17px 19px;
    margin: 8px 0;
}

.insight-title {
    color: #C7BEFF;
    font-weight: 700;
    font-size: 14px;
    margin-bottom: 7px;
}

.insight-body {
    color: #E2E7F1;
    font-size: 14px;
    line-height: 1.7;
}

div[data-testid="stMetric"] {
    background: #171D29;
    border: 1px solid var(--border);
    border-radius: 13px;
    padding: 13px 16px;
}

.stButton > button {
    border-radius: 11px;
    font-weight: 600;
    transition: all .2s ease;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(100deg, #7765F6, #A18AFF);
    border: none;
    color: white;
}

.stButton > button[kind="primary"]:hover {
    filter: brightness(1.12);
}

div[data-testid="stTabs"] button {
    font-weight: 600;
}

[data-testid="stChatMessage"] {
    border: 1px solid var(--border);
    border-radius: 15px;
    margin-bottom: 10px;
}

[data-testid="stFileUploader"] {
    border-radius: 13px;
}

.small-muted {
    color: #9DA8BC;
    font-size: 12px;
}

#MainMenu, footer {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# HELPERS
# ============================================================

def api_endpoint(path):
    return f"{API_URL.rstrip('/')}/{path.lstrip('/')}"


def safe_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def fmt(value, digits=2):
    if value is None:
        return "N/A"

    try:
        if pd.isna(value):
            return "N/A"
    except (TypeError, ValueError):
        pass

    if isinstance(value, (int, float, np.integer, np.floating)):
        return f"{value:,.{digits}f}"

    return str(value)


def read_preview(upload):
    upload.seek(0)

    if upload.name.lower().endswith(".csv"):
        return pd.read_csv(upload, nrows=1000)

    return pd.read_excel(upload, nrows=1000)


def api_error_message(exc):
    response = getattr(exc, "response", None)

    if response is not None:
        try:
            details = response.json()
        except ValueError:
            details = response.text[:1500]

        return f"{exc}\n\n{details}"

    return str(exc)


def display_statistical_result(result):
    """Display the statistical test result safely."""

    if not isinstance(result, dict) or not result:
        st.info("No result is available for this hypothesis.")
        return

    status = result.get("status")

    if status == "success":
        col1, col2 = st.columns(2)

        col1.metric(
            "Observations",
            f"{result.get('sample_size', 0):,}"
        )

        p_value = result.get("p_value")

        col2.metric(
            "P-value",
            f"{p_value:.6g}" if p_value is not None else "N/A"
        )

        st.write(
            "**Statistical test:**",
            result.get("test", "N/A")
        )

        if result.get("statistic") is not None:
            st.write(
                "**Test statistic:**",
                f"{result['statistic']:.4f}"
            )

        if p_value is not None:
            if p_value < 0.05:
                st.success(
                    "Statistically significant at the 0.05 level, "
                    "before any multiple-testing correction."
                )
            else:
                st.info(
                    "Not statistically significant at the 0.05 level. "
                    "This does not prove that no relationship exists."
                )

        st.caption(
            result.get(
                "interpretation_note",
                "Interpret results alongside assumptions and effect size."
            )
        )

    elif status == "error":
        st.warning(
            "The proposed test could not be completed: "
            + result.get("reason", "Unknown error")
        )

    elif status == "not_tested":
        st.info(result.get("reason", "No test was performed."))

    else:
        st.info("No validated statistical result is available.")

    with st.expander("View result details"):
        st.json(result)


def metric_card(label, value, note=""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("## 📊 Intellianalyzer")
    st.markdown(
        '<div class="small-muted">Your personal data intelligence workspace</div>',
        unsafe_allow_html=True
    )

    st.divider()

    st.markdown("### Your dataset")

    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=["csv", "xlsx", "xls"],
        help="Upload a dataset to explore its statistics and discover insights."
    )

    if uploaded_file:
        st.success(f"Selected: {uploaded_file.name}")
        # Keep the uploaded bytes available after Streamlit reruns.
        st.session_state["_current_upload_bytes"] = uploaded_file.getvalue()
        st.session_state["_current_upload_name"] = uploaded_file.name

    analyze_clicked = st.button(
        "✨ Explore My Data",
        type="primary",
        use_container_width=True
    )

    st.divider()

    if st.button("Start a new analysis", use_container_width=True):
        st.session_state.analysis = None
        st.session_state.chat_history = []
        st.session_state.report_filename = None
        st.session_state.pop("_current_upload_bytes", None)
        st.session_state.pop("_current_upload_name", None)
        st.rerun()

    st.markdown(
        """
        <div class="small-muted">
        Discover patterns, understand relationships, and explore
        your data through natural conversation.
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# ANALYSIS REQUEST
# ============================================================

if analyze_clicked:
    if uploaded_file is None:
        st.warning("Choose a dataset before starting the analysis.")

    else:
        progress_status = st.status(
            "Preparing your dataset analysis...",
            expanded=True
        )

        try:
            progress_status.write("Reading your uploaded dataset...")
            file_content = uploaded_file.getvalue()

            progress_status.write(
                "Examining data quality and statistical patterns..."
            )

            progress_status.write(
                "Discovering hypotheses and validating findings..."
            )

            response = requests.post(
                api_endpoint("/analyze"),
                files={
                    "file": (
                        uploaded_file.name,
                        file_content,
                        uploaded_file.type or "application/octet-stream"
                    )
                },
                timeout=(30, 1800)
            )

            response.raise_for_status()
            report = response.json()

            if not isinstance(report, dict) or "profile" not in report:
                raise ValueError("The analysis response is incomplete.")

            st.session_state.analysis = report
            st.session_state.chat_history = []
            st.session_state.report_filename = uploaded_file.name

            progress_status.update(
                label="Your analysis is ready!",
                state="complete",
                expanded=False
            )

            st.rerun()

        except requests.Timeout:
            progress_status.update(
                label="The analysis request timed out.",
                state="error",
                expanded=True
            )
            st.error(
                "The analysis service did not respond in time. "
                "Check whether the analysis is still running before "
                "submitting another request."
            )

        except requests.RequestException as exc:
            progress_status.update(
                label="We couldn't complete the analysis.",
                state="error",
                expanded=True
            )
            st.error(api_error_message(exc))

        except (ValueError, json.JSONDecodeError) as exc:
            progress_status.update(
                label="The returned report could not be read.",
                state="error",
                expanded=True
            )
            st.error(str(exc))


# ============================================================
# HERO / EMPTY STATE
# ============================================================

analysis = st.session_state.analysis

if not analysis:
    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">DATA INTELLIGENCE · MADE SIMPLE</div>
            <div class="hero-title">Make your data<br>tell its story.</div>
            <div class="hero-subtitle">
                Discover hidden patterns, explore meaningful relationships,
                investigate hypotheses, and turn complex datasets into
                understandable insights.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("### Everything you need to understand your data")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("#### 📈 Explore")
        st.write(
            "Understand distributions, missing values, correlations, "
            "and the structure of your dataset."
        )

    with c2:
        st.markdown("#### 🔎 Discover")
        st.write(
            "Explore promising hypotheses and examine the statistical "
            "evidence behind potential relationships."
        )

    with c3:
        st.markdown("#### 💬 Understand")
        st.write(
            "Ask questions about the generated findings and receive "
            "clear explanations grounded in your analysis."
        )

    st.info(
        "Upload your dataset from the sidebar to begin your exploration."
    )

    st.stop()


# ============================================================
# REPORT DATA
# ============================================================

profile = analysis.get("profile", {})
dataset = profile.get("dataset", {})
columns_info = profile.get("columns", {})
plan = analysis.get("analysis_plan", {})
results = analysis.get("test_results", [])

hypotheses = plan.get("hypotheses", [])
quality_findings = plan.get("data_quality_findings", [])
recommended_questions = plan.get("recommended_questions", [])
warnings = profile.get("warnings", [])
correlations = profile.get("correlations", {})

results_by_title = {
    item.get("hypothesis"): item
    for item in results
}


# ============================================================
# DASHBOARD HEADER
# ============================================================

st.markdown(
    f"""
    <div class="hero">
        <div class="eyebrow">YOUR DATA WORKSPACE</div>
        <div class="hero-title">Discover what's inside.</div>
        <div class="hero-subtitle">
            Exploring <b>{analysis.get('filename', 'your dataset')}</b>.
            Review the overview, explore distributions, investigate
            hypotheses, or ask a question about your findings.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

m1, m2, m3, m4 = st.columns(4)

with m1:
    metric_card("TOTAL RECORDS", f"{dataset.get('rows', 0):,}", "Rows in dataset")

with m2:
    metric_card("FEATURES", str(dataset.get("columns", 0)), "Available columns")

with m3:
    metric_card("DATA QUALITY", f"{len(warnings)}", "Profiler warnings")

with m4:
    metric_card("HYPOTHESES", str(len(hypotheses)), "Questions to investigate")


# ============================================================
# TABS
# ============================================================

tab_overview, tab_distributions, tab_report, tab_hypotheses, tab_chat = st.tabs(
    [
        "◈ Overview",
        "▥ Distributions",
        "▤ Analysis Report",
        "◇ Hypotheses",
        "✳ Ask Your Data"
    ]
)


# ============================================================
# OVERVIEW
# ============================================================

with tab_overview:
    st.markdown("### Dataset overview")
    st.markdown(
        '<div class="small-muted">A quick look at the structure and quality of your data.</div>',
        unsafe_allow_html=True
    )

    c1, c2 = st.columns([1.3, 1])

    with c1:
        st.markdown("#### Column profile")

        quality_rows = []

        for column, info in columns_info.items():
            quality_rows.append({
                "Column": column,
                "Type": info.get("dtype", "Unknown"),
                "Missing": info.get("missing_count", 0),
                "Missing (%)": info.get("missing_percent", 0),
                "Unique": info.get("unique_values", 0)
            })

        quality_df = pd.DataFrame(quality_rows)

        if not quality_df.empty:
            st.dataframe(
                quality_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No column profile is available.")

    with c2:
        st.markdown("#### Data completeness")

        if not quality_df.empty:
            completeness_df = quality_df[["Column", "Missing (%)"]].copy()
            completeness_df["Complete (%)"] = (
                100 - completeness_df["Missing (%)"]
            )

            completeness_df = completeness_df.sort_values(
                "Complete (%)", ascending=True
            )

            fig = px.bar(
                completeness_df,
                x="Complete (%)",
                y="Column",
                orientation="h",
                range_x=[0, 100],
                color="Complete (%)",
                color_continuous_scale=["#F18A94", "#F5CB7B", "#59DCC0"],
                template="plotly_dark"
            )

            fig.update_layout(
                height=max(300, len(completeness_df) * 30),
                margin=dict(l=5, r=10, t=15, b=10),
                coloraxis_showscale=False,
                xaxis_title="Completeness",
                yaxis_title=None,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )

            st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Data quality observations")

    if warnings:
        for warning in warnings:
            st.markdown(
                f'<div class="insight-card">'
                f'<div class="insight-body">• {warning}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.success("No profiler warnings were reported.")

    st.markdown("#### Numerical relationships")

    if correlations:
        corr_df = pd.DataFrame([
            {"Variable pair": key, "Correlation": value}
            for key, value in correlations.items()
        ])

        corr_df["Magnitude"] = corr_df["Correlation"].abs()

        corr_df = corr_df.sort_values(
            "Magnitude", ascending=False
        ).head(15)

        fig = px.bar(
            corr_df.sort_values("Correlation"),
            x="Correlation",
            y="Variable pair",
            orientation="h",
            color="Correlation",
            color_continuous_scale=["#F18A94", "#30394A", "#59DCC0"],
            range_color=[-1, 1],
            template="plotly_dark"
        )

        fig.update_layout(
            height=max(300, len(corr_df) * 35),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=5, r=5, t=15, b=10),
            coloraxis_showscale=False,
            xaxis_title="Correlation coefficient",
            yaxis_title=None
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No numerical correlations are available.")


# ============================================================
# DISTRIBUTIONS
# ============================================================

with tab_distributions:
    st.markdown("### Distribution explorer")
    st.markdown(
        '<div class="small-muted">'
        'Explore the shape, spread, central tendency, and potential outliers '
        'of individual numerical features.'
        '</div>',
        unsafe_allow_html=True
    )

    numeric_columns = [
        column
        for column, info in columns_info.items()
        if "statistics" in info
    ]

    if not numeric_columns:
        st.info("This dataset has no numerical columns to visualize.")
    else:
        chart_df = None
        upload_bytes = st.session_state.get("_current_upload_bytes")
        upload_name = st.session_state.get("_current_upload_name", "")

        # Use the saved upload bytes so the distribution explorer continues
        # to work after Streamlit reruns the script.
        if upload_bytes and upload_name:
            try:
                preview_file = BytesIO(upload_bytes)
                preview_file.name = upload_name
                chart_df = read_preview(preview_file)
            except Exception as exc:
                st.warning(f"Couldn't read the uploaded file for charts: {exc}")

        if chart_df is None:
            st.info(
                "Upload the dataset again from the sidebar to interact "
                "with its distributions. Existing analysis statistics "
                "remain available in the report."
            )

        else:
            selected_column = st.selectbox(
                "Select a numerical feature",
                numeric_columns,
                key="distribution_column"
            )

            values = pd.to_numeric(
                chart_df[selected_column],
                errors="coerce"
            ).replace([np.inf, -np.inf], np.nan).dropna()

            if values.empty:
                st.warning("This feature contains no valid numerical values.")
            else:
                stats_info = columns_info.get(
                    selected_column, {}
                ).get("statistics", {})

                q1 = values.quantile(0.25)
                median = values.median()
                q3 = values.quantile(0.75)
                iqr = q3 - q1

                lower_fence = q1 - 1.5 * iqr
                upper_fence = q3 + 1.5 * iqr
                outlier_count = int(
                    ((values < lower_fence) | (values > upper_fence)).sum()
                )

                a, b, c, d = st.columns(4)

                with a:
                    metric_card("MEAN", fmt(values.mean()), selected_column)

                with b:
                    metric_card("MEDIAN", fmt(median), "50th percentile")

                with c:
                    metric_card(
                        "STD. DEVIATION",
                        fmt(values.std()),
                        "Spread around the mean"
                    )

                with d:
                    metric_card(
                        "POTENTIAL OUTLIERS",
                        f"{outlier_count:,}",
                        "1.5 × IQR rule"
                    )

                st.markdown("#### Distribution shape")

                chart_mode = st.radio(
                    "Visualization",
                    ["Histogram", "Box plot", "Violin plot"],
                    horizontal=True,
                    key="distribution_mode"
                )

                if chart_mode == "Histogram":
                    fig = px.histogram(
                        x=values,
                        nbins=35,
                        marginal="box",
                        opacity=0.88,
                        template="plotly_dark",
                        labels={
                            "x": selected_column,
                            "count": "Frequency"
                        },
                        title=f"Distribution of {selected_column}"
                    )

                    fig.update_traces(
                        marker_line_width=0.5,
                        marker_line_color="#BDB1FF"
                    )

                    fig.update_layout(
                        bargap=0.08,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#E6EAF3"),
                        title_font_size=19,
                        xaxis_title=selected_column,
                        yaxis_title="Frequency",
                        showlegend=False,
                        margin=dict(l=10, r=10, t=60, b=15)
                    )

                    fig.add_vline(
                        x=values.mean(),
                        line_dash="dash",
                        line_color="#59DCC0",
                        annotation_text="Mean",
                        annotation_position="top"
                    )

                    fig.add_vline(
                        x=median,
                        line_dash="dot",
                        line_color="#F3C969",
                        annotation_text="Median",
                        annotation_position="bottom"
                    )

                elif chart_mode == "Box plot":
                    fig = px.box(
                        y=values,
                        points="outliers",
                        template="plotly_dark",
                        labels={"y": selected_column},
                        title=f"Spread and outliers: {selected_column}",
                        color_discrete_sequence=["#9B8AFF"]
                    )

                    fig.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        showlegend=False,
                        margin=dict(l=10, r=10, t=60, b=15)
                    )

                else:
                    fig = px.violin(
                        y=values,
                        box=True,
                        points="outliers",
                        template="plotly_dark",
                        labels={"y": selected_column},
                        title=f"Density and spread: {selected_column}",
                        color_discrete_sequence=["#59DCC0"]
                    )

                    fig.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        showlegend=False,
                        margin=dict(l=10, r=10, t=60, b=15)
                    )

                st.plotly_chart(fig, use_container_width=True)

                st.markdown("#### Five-number summary")

                summary = pd.DataFrame([{
                    "Minimum": values.min(),
                    "25th percentile": q1,
                    "Median": median,
                    "75th percentile": q3,
                    "Maximum": values.max()
                }])

                st.dataframe(
                    summary,
                    use_container_width=True,
                    hide_index=True
                )

                st.caption(
                    "Potential outliers are identified using the 1.5 × IQR rule. "
                    "They are not automatically errors."
                )


# ============================================================
# ANALYSIS REPORT
# ============================================================

with tab_report:
    st.markdown("### Complete analysis report")

    st.markdown(
        '<div class="small-muted">'
        'A consolidated view of the findings generated for your dataset.'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown("#### Executive summary")
    st.write(
        plan.get(
            "dataset_summary",
            "No executive summary is available."
        )
    )

    st.markdown("#### Dataset profile")

    profile_rows = []

    for column, info in columns_info.items():
        row = {
            "Column": column,
            "Type": info.get("dtype"),
            "Missing": info.get("missing_count"),
            "Missing (%)": info.get("missing_percent"),
            "Unique values": info.get("unique_values")
        }

        for key, value in info.get("statistics", {}).items():
            row[key.capitalize()] = value

        profile_rows.append(row)

    if profile_rows:
        st.dataframe(
            pd.DataFrame(profile_rows),
            use_container_width=True,
            hide_index=True
        )

    st.markdown("#### Data quality findings")

    if quality_findings:
        for finding in quality_findings:
            st.markdown(f"- {finding}")
    elif warnings:
        for warning in warnings:
            st.markdown(f"- {warning}")
    else:
        st.info("No additional quality findings were generated.")

    st.markdown("#### Recommended research questions")

    if recommended_questions:
        for index, question in enumerate(recommended_questions, 1):
            st.markdown(f"**{index}.** {question}")
    else:
        st.info("No separate research questions were generated.")

    st.markdown("#### Statistical findings")

    if results:
        for index, item in enumerate(results, 1):
            with st.expander(
                f"{index}. {item.get('hypothesis', 'Statistical finding')}"
            ):
                st.write(item.get("question", ""))
                result_data = item.get("result", {})
                # Use the shared renderer. Do not name this variable
                # `render_result`, because that would overwrite the function.
                display_statistical_result(result_data)
    else:
        st.info("No statistical test results are available.")

    st.markdown("#### Correlation overview")

    if correlations:
        corr_df = pd.DataFrame([
            {"Variables": key, "Correlation": value}
            for key, value in correlations.items()
        ])

        corr_df["Absolute correlation"] = corr_df["Correlation"].abs()

        st.dataframe(
            corr_df.sort_values(
                "Absolute correlation",
                ascending=False
            ).drop(columns="Absolute correlation"),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No correlation results are available.")

    st.divider()

    st.download_button(
        "⬇ Download complete analysis report",
        data=safe_json(analysis),
        file_name="intellianalyzer_report.json",
        mime="application/json",
        use_container_width=True
    )

    with st.expander("View structured report"):
        st.json(analysis)


# ============================================================
# HYPOTHESES
# ============================================================

with tab_hypotheses:
    st.markdown("### Explore the hypotheses")

    st.markdown(
        '<div class="small-muted">'
        'Investigate the questions suggested by the analysis and '
        'review the statistical evidence.'
        '</div>',
        unsafe_allow_html=True
    )

    if not hypotheses:
        st.info("No hypotheses were generated.")

    for index, hypothesis in enumerate(hypotheses, 1):
        title = hypothesis.get("title", f"Hypothesis {index}")
        result_item = results_by_title.get(title, {})
        result = result_item.get("result", {})

        with st.expander(f"{index}. {title}", expanded=True):
            st.markdown("**Research question**")
            st.write(hypothesis.get("question", "Not provided."))

            st.markdown("**Null hypothesis**")
            st.write(hypothesis.get("null_hypothesis", "Not provided."))

            st.markdown("**Alternative hypothesis**")
            st.write(
                hypothesis.get("alternative_hypothesis", "Not provided.")
            )

            st.markdown("**Variables**")
            st.write(
                ", ".join(hypothesis.get("variables", []))
                or "Not specified"
            )

            st.markdown("**Rationale**")
            st.write(hypothesis.get("rationale", "Not provided."))

            st.markdown("**Limitations**")
            st.write(hypothesis.get("limitations", "Not provided."))

            st.markdown("**Statistical evidence**")
            display_statistical_result(result)


# ============================================================
# CHAT
# ============================================================

with tab_chat:
    st.markdown("### Let's explore your findings")

    st.markdown(
        '<div class="small-muted">'
        'Ask about the hypotheses, patterns, relationships, and conclusions '
        'in your analysis.'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="insight-card">
            <div class="insight-title">Your data, explained</div>
            <div class="insight-body">
                Explore why a hypothesis matters, what the statistical
                evidence suggests, how variables relate to one another,
                or which findings deserve further investigation.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if message.get("computed_result"):
                with st.expander("Supporting calculation"):
                    st.json(message["computed_result"])

            if message.get("sources"):
                with st.expander("Supporting findings"):
                    st.json(message["sources"])

    question = st.chat_input(
        "Ask about the hypotheses or findings in your analysis..."
    )

    if question:
        st.session_state.chat_history.append({
            "role": "user",
            "content": question
        })

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            try:
                with st.spinner("Exploring your findings..."):
                    response = requests.post(
                        api_endpoint("/chat"),
                        json={"question": question},
                        timeout=(30, 180)
                    )

                    response.raise_for_status()
                    data = response.json()

                answer = data.get(
                    "answer",
                    "No answer was returned."
                )

                computed_result = data.get("computed_result")
                sources = data.get("sources", [])

                st.markdown(answer)

                if computed_result:
                    with st.expander("Supporting calculation"):
                        st.json(computed_result)

                if sources:
                    with st.expander("Supporting findings"):
                        st.json(sources)

                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": answer,
                    "computed_result": computed_result,
                    "sources": sources
                })

            except requests.RequestException as exc:
                error = (
                    "I couldn't retrieve an answer. "
                    "Please try again in a moment."
                )
                st.error(error)

                # Detailed error remains in the terminal rather than
                # exposing implementation details in the interface.
                print("Chat request failed:", exc)

                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": error
                })


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div style="text-align:center; color:#8F9AAF; font-size:12px;
                padding:8px 0 18px 0;">
        Intellianalyzer · Discover more in your data
    </div>
    """,
    unsafe_allow_html=True
)
