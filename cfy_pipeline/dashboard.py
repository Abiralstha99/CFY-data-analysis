"""Streamlit dashboard — run with: streamlit run cfy_pipeline/dashboard.py.

Analysis and storage stay in the pipeline modules; this file handles presentation.
"""

from __future__ import annotations

from pathlib import Path
import sys

# Streamlit may put this file's directory, rather than the project root, on
# sys.path when launched with ``streamlit run cfy_pipeline/dashboard.py``.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

from cfy_pipeline import SurveySchema, load_schema
from cfy_pipeline.schema import QuestionField
from cfy_pipeline.charts import build_comparison_figure, build_trend_figure
from cfy_pipeline.comparison import SIGNIFICANCE_THRESHOLD, ComparisonResult, compare_years
from cfy_pipeline.storage import load_all_years
from cfy_pipeline.trends import MIN_YEARS_FOR_TREND, TrendResult, detect_multi_year_trends
from cfy_pipeline.uploaded_files import render_uploaded_files_tab

# Paths are relative to this file's parent (cfy_pipeline/) going up one level
# to the project root. Works in both local dev and Streamlit Cloud deployments.
SCHEMA_PATH = PROJECT_ROOT / "config" / "survey_schema.yaml"
DB_PATH = PROJECT_ROOT / "data" / "survey.db"

GROUP_LABELS = {
    "grade": "Grade",
    "gender": "Gender",
    "race_ethnicity": "Race or ethnicity",
}
P_VALUE_HELP = (
    "A p-value estimates how surprising this difference would be if there were "
    "no real change. Values below 0.05 are flagged for a closer look."
)
SMALL_GROUP_THRESHOLD = 10


def apply_dashboard_styles() -> None:
    """Keep the Streamlit layout calm and readable in the dark theme."""
    st.markdown(
        """
        <style>
        .block-container { max-width: 1200px; padding-top: 4.5rem; padding-bottom: 4rem; }
        h2, h3 { font-family: "Avenir Next", "Aptos Display", sans-serif; }
        .dashboard-intro { padding: 0.5rem 0 1.5rem; overflow: visible; }
        div[data-testid="stMarkdownContainer"]:has(> .dashboard-intro) { margin-bottom: 0 !important; }
        .dashboard-intro p, .dashboard-intro h1 { margin: 0 !important; padding: 0 !important; overflow: visible; }
        .dashboard-intro .dashboard-intro__eyebrow {
            color: #A9BBCB;
            font-size: 0.875rem !important;
            line-height: 1.5 !important;
            letter-spacing: 0.03em;
            margin-bottom: 0.7rem !important;
        }
        .dashboard-intro .dashboard-intro__title {
            color: #E7EFF5;
            font-family: "Avenir Next", "Aptos Display", sans-serif;
            font-size: clamp(1.75rem, 1.25rem + 2vw, 3rem) !important;
            line-height: 1.2 !important;
            margin-bottom: 0.7rem !important;
        }
        .dashboard-intro .dashboard-intro__subtitle {
            color: #E7EFF5;
            font-size: 1rem !important;
            line-height: 1.55 !important;
        }
        h2 { margin-top: 0.5rem; }
        p, label { line-height: 1.55; }
        div[data-testid="stMetric"] { padding: 0.15rem 0; }
        div[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
        div[data-testid="stDataFrame"] { font-variant-numeric: tabular-nums; }
        div[data-testid="stRadio"] div[role="radiogroup"] { gap: 0.4rem; flex-wrap: wrap; }
        div[data-testid="stRadio"] label { border: 1px solid #354759; border-radius: 0.5rem; padding: 0.55rem 0.85rem; }
        div[data-testid="stRadio"] label:has(input:checked) { background: #284638; border-color: #73C7B3; }
        div[data-testid="stRadio"] label p { font-weight: 600; }
        div[data-testid="stRadio"] label:focus-within { outline: 2px solid #73C7B3; outline-offset: 2px; }
        .modebar-btn { min-width: 36px !important; min-height: 36px !important; }
        div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 0.75rem; }
        .file-table-header, .file-row-grid { display: grid; align-items: center; gap: 0.7rem; }
        .file-table-header {
            grid-template-columns: 2.7fr 0.9fr 1.25fr 0.75fr 0.8fr 1.4fr;
            padding: 0.75rem 0.4rem;
            color: #A9BBCB;
            font-size: 0.78rem;
            font-weight: 600;
            border-bottom: 1px solid #354759;
        }
        .file-row-grid { grid-template-columns: 2.7fr 0.9fr 1.25fr 0.75fr 0.8fr; }
        .file-cell { color: #DDE8F0; font-size: 0.88rem; min-width: 0; }
        .file-name strong { display: block; overflow-wrap: anywhere; }
        .file-name small { display: block; color: #A9BBCB; margin-top: 0.15rem; }
        .file-mobile-label { display: none; }
        .file-status { color: #9CE0C6; font-weight: 600; }
        [class*="st-key-file_row_"] {
            padding: 0.85rem 0.4rem;
            border-bottom: 1px solid #283B4C;
        }
        [class*="st-key-file_row_"]:hover { background-color: #172636; }
        @media (max-width: 700px) {
            .block-container { padding-top: 4.5rem; }
            .dashboard-intro { padding-bottom: 1.25rem; }
            h2 { font-size: 1.45rem !important; line-height: 1.15 !important; }
            h3 { font-size: 1.25rem !important; line-height: 1.2 !important; }
            div[data-testid="stMetric"] { padding: 0; }
            div[data-testid="stVerticalBlockBorderWrapper"] { padding-top: 0.4rem; padding-bottom: 0.4rem; }
            .modebar-btn { min-width: 44px !important; min-height: 44px !important; }
            div[data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
            div[data-testid="column"] { min-width: min(100%, 260px); }
            div[data-testid="stRadio"] label { padding: 0.48rem 0.65rem; }
            div[data-testid="stRadio"] label p { font-size: 0.85rem; }
            .file-table-header { display: none; }
            .file-row-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .file-name { grid-column: 1 / -1; }
            .file-mobile-label {
                display: block;
                color: #A9BBCB;
                font-size: 0.73rem;
                margin-bottom: 0.15rem;
            }
            [class*="st-key-file_row_"] div[data-testid="column"] { min-width: 0; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def available_schema(df_all: pd.DataFrame, schema: SurveySchema) -> SurveySchema:
    """Analyze only question columns that exist in stored survey data."""
    return SurveySchema(
        demographics=schema.demographics,
        questions=tuple(question for question in schema.questions if question.name in df_all.columns),
    )


def breakdown_options(df_all: pd.DataFrame, schema: SurveySchema) -> list[str | None]:
    return [None] + [name for name in schema.demographic_names() if name in df_all.columns]


def breakdown_label(name: str | None) -> str:
    return "All responses" if name is None else GROUP_LABELS.get(name, name.replace("_", " ").title())


def style_chart(figure) -> None:
    """Give Plotly charts the same dark canvas and readable axes as the app."""
    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E7EFF5", family="Avenir Next, Aptos, sans-serif", size=13),
        margin=dict(l=24, r=20, t=30, b=72),
        legend=dict(orientation="h", y=-0.22, x=0, title=None),
    )
    figure.update_xaxes(gridcolor="#2B3B4B", linecolor="#41566A")
    figure.update_yaxes(gridcolor="#2B3B4B", linecolor="#41566A")


def format_p_value(p_value: float) -> str:
    return "< 0.001" if p_value < 0.001 else f"{p_value:.3f}"


def render_metric_card(label: str, value: str, description: str) -> None:
    with st.container(border=True):
        st.metric(label, value)
        st.caption(description)


def render_scale_context(question: QuestionField) -> None:
    low, high = question.valid_range
    if question.low_label and question.high_label:
        st.caption(f"Response scale: {low} = {question.low_label} · {high} = {question.high_label}.")
        if question.interpretation:
            st.caption(question.interpretation)
    else:
        st.warning(
            f"The response wording for {question.label} is not configured. "
            "Check the survey questionnaire before interpreting score direction."
        )


def open_section(section: str) -> None:
    st.session_state["dashboard_section"] = section


def render_overview(df_all: pd.DataFrame, schema: SurveySchema) -> None:
    st.header("📊 Survey at a glance")
    st.caption("A quick view of the responses and patterns currently stored in this dashboard.")
    if df_all.empty:
        st.info("No survey data has been added yet. Open Uploaded Files to add the first CSV.")
        return

    years = sorted(df_all["survey_year"].unique().tolist())
    latest_year = years[-1]
    analysis_schema = available_schema(df_all, schema)
    changes = 0
    flagged_changes = []
    if len(years) >= 2:
        results = compare_years(df_all, analysis_schema, previous_year=years[-2], current_year=latest_year)
        flagged_changes = [result for result in results if result.significant]
        changes = len(flagged_changes)
    flagged_patterns = [result for result in detect_multi_year_trends(df_all, analysis_schema) if result.is_sustained]
    patterns = len(flagged_patterns)

    first_row = st.columns(2, gap="medium")
    with first_row[0]:
        render_metric_card("Responses on file", f"{len(df_all):,}", "Across every survey year in this dashboard.")
    with first_row[1]:
        latest_count = int((df_all["survey_year"] == latest_year).sum())
        render_metric_card(
            f"{latest_year} responses",
            f"{latest_count:,}",
            f"Most recent year · {len(years)} year{'s' if len(years) != 1 else ''} available.",
        )
    second_row = st.columns(2, gap="medium")
    with second_row[0]:
        render_metric_card(
            "Changes to review",
            str(changes) if len(years) >= 2 else "—",
            f"Question scores flagged between {years[-2]} and {latest_year}." if len(years) >= 2
            else "Add another year to compare survey results.",
        )
        if len(years) >= 2:
            st.button("Review comparisons →", on_click=open_section, args=("Compare Years",), key="review_comparisons")
            for result in flagged_changes[:3]:
                st.caption(f"• {analysis_schema.question_by_name(result.question_name).label}")
    with second_row[1]:
        render_metric_card(
            "Patterns over time",
            str(patterns) if len(years) >= MIN_YEARS_FOR_TREND else "—",
            "Questions with a consistent rise or fall across years." if len(years) >= MIN_YEARS_FOR_TREND
            else "Add at least three years to see longer-term patterns.",
        )
        if len(years) >= MIN_YEARS_FOR_TREND:
            st.button("Review trends →", on_click=open_section, args=("Trends",), key="review_trends")
            for result in flagged_patterns[:3]:
                st.caption(f"• {analysis_schema.question_by_name(result.question_name).label}")

    st.subheader("Years on file")
    year_counts = df_all["survey_year"].value_counts().sort_index(ascending=False)
    st.dataframe(
        pd.DataFrame({"Survey year": year_counts.index, "Responses": year_counts.values}),
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "A flagged change means the comparison passed a statistical check; it does not "
        "tell us whether a change is good or bad. Open Compare Years for context."
    )


def comparison_results_table(results: list[ComparisonResult]) -> pd.DataFrame:
    """Format comparison results for staff reading the charts."""
    return pd.DataFrame(
        {
            "Group": ["All responses" if r.group == "All" else r.group for r in results],
            f"{results[0].previous_year} average": [round(r.previous_mean, 2) for r in results],
            f"{results[0].previous_year} n": [r.previous_count for r in results],
            f"{results[0].current_year} average": [round(r.current_year_mean, 2) for r in results],
            f"{results[0].current_year} n": [r.current_count for r in results],
            "Score change": [round(r.current_year_mean - r.previous_mean, 2) for r in results],
            "p-value": [format_p_value(r.p_value) for r in results],
            "Flagged for review": ["Yes" if r.significant else "No" for r in results],
        }
    )


def render_comparison_tab(df_all: pd.DataFrame, schema: SurveySchema) -> None:
    """Compare question scores between two chosen years."""
    st.header("⇄ Compare years")
    st.caption("Choose two years to see where average response scores changed.")
    years = sorted(df_all["survey_year"].unique().tolist())
    if len(years) < 2:
        st.info("Add a second survey year in Uploaded Files to compare responses.")
        return

    group_by = st.selectbox(
        "View responses by",
        breakdown_options(df_all, schema),
        format_func=breakdown_label,
        key="compare_group",
    )
    current_col, previous_col = st.columns(2)
    current_year = current_col.selectbox("Year to review", years[:0:-1], index=0)
    previous_options = [y for y in years[::-1] if y < current_year]
    if not previous_options:
        st.info("Choose a later year to see earlier years available for comparison.")
        return
    previous_year = previous_col.selectbox("Compare with", previous_options, index=0)

    st.info(
        "Each bar shows an average response on a 1–5 scale. Coral bars flag a change "
        "that passed the statistical check; blue bars did not. A flag invites review "
        "and does not say whether the change is good or bad. n counts valid answers to that question."
    )
    with st.expander("What does “flagged” mean?"):
        st.write(
            f"The dashboard uses a statistical comparison and flags results with a "
            f"p-value below {SIGNIFICANCE_THRESHOLD}. {P_VALUE_HELP} "
            "Groups need at least two responses in each year to appear."
        )

    comparisons = compare_years(
        df_all, schema, previous_year=previous_year, current_year=current_year, group_by=group_by
    )
    if not comparisons:
        st.info("There are not enough responses for this selection. Try another year or group.")
        return

    question_options = [
        question for question in schema.questions
        if any(result.question_name == question.name for result in comparisons)
    ]
    question = st.selectbox(
        "Question to explore", question_options,
        format_func=lambda option: option.label,
        key="compare_question",
    )
    question_results = [r for r in comparisons if r.question_name == question.name]
    with st.container(border=True):
        st.subheader(question.label)
        render_scale_context(question)
        if any(min(r.previous_count, r.current_count) < SMALL_GROUP_THRESHOLD for r in question_results):
            st.warning("Small group: at least one bar uses fewer than 10 valid answers. Interpret with care.")
        figure = build_comparison_figure(question_results, question.label)
        figure.data[0].name = str(previous_year)
        figure.data[1].name = str(current_year)
        figure.update_layout(title=None, legend_title_text=None)
        style_chart(figure)
        st.plotly_chart(figure, width="stretch")
        st.caption("Coral in the more recent year marks a flagged change. Hover for the exact score, response count, and p-value.")
        st.dataframe(
            comparison_results_table(question_results),
            hide_index=True,
            width="stretch",
            column_config={"p-value": st.column_config.TextColumn("p-value", help=P_VALUE_HELP)},
        )


def trend_results_table(trends: list[TrendResult]) -> pd.DataFrame:
    """Format longer-term patterns for staff reading the charts."""
    return pd.DataFrame(
        {
            "Group": ["All responses" if t.group == "All" else t.group for t in trends],
            "Years": [", ".join(map(str, t.years)) for t in trends],
            "Responses by year": [", ".join(f"{year}: {count}" for year, count in zip(t.years, t.yearly_counts)) for t in trends],
            "Average score change per year": [round(t.slope, 3) for t in trends],
            "p-value": [format_p_value(t.p_value) for t in trends],
            "Pattern": [t.direction.capitalize() if t.is_sustained else "No clear pattern" for t in trends],
        }
    )


def render_trends_tab(df_all: pd.DataFrame, schema: SurveySchema) -> None:
    """Show how question scores move over at least three selected years."""
    st.header("📈 Trends over time")
    st.caption("Look for consistent changes in average response scores across survey years.")
    years = sorted(df_all["survey_year"].unique().tolist())
    if len(years) < MIN_YEARS_FOR_TREND:
        st.info("Add at least three survey years in Uploaded Files to see patterns over time.")
        return

    group_by = st.selectbox(
        "View responses by",
        breakdown_options(df_all, schema),
        format_func=breakdown_label,
        key="trend_group",
    )
    selected_years = st.multiselect("Years to include", years, default=years, help="Select at least three years.")
    if len(selected_years) < MIN_YEARS_FOR_TREND:
        st.info("Select at least three years to show trends.")
        return

    st.info(
        "Each point is that year's average response on a 1–5 scale. Coral lines "
        "show a consistent rise or fall that passed the statistical check. n counts valid answers to that question."
    )
    with st.expander("How are patterns identified?"):
        st.write(
            "The dashboard fits a straight line through the selected yearly averages "
            f"and flags a rise or fall when the p-value is below {SIGNIFICANCE_THRESHOLD}. "
            f"{P_VALUE_HELP} With only three years, one unusual year can strongly affect a result."
        )

    selected_data = df_all[df_all["survey_year"].isin(selected_years)]
    trends = detect_multi_year_trends(selected_data, schema, group_by=group_by)
    if not trends:
        st.info("There are not enough responses for this selection. Try more years or another group.")
        return

    question_options = [question for question in schema.questions if any(t.question_name == question.name for t in trends)]
    selected_question = st.selectbox("Question to explore", question_options, format_func=lambda question: question.label)
    for question in [selected_question]:
        question_trends = [t for t in trends if t.question_name == question.name]
        if not question_trends:
            continue
        for trend in question_trends:
            with st.container(border=True):
                st.subheader(question.label)
                render_scale_context(question)
                if any(count < SMALL_GROUP_THRESHOLD for count in trend.yearly_counts):
                    st.warning("Small group: at least one point uses fewer than 10 valid answers. Interpret with care.")
                figure = build_trend_figure(trend, question.label)
                group_name = "All responses" if trend.group == "All" else trend.group
                figure.update_layout(title=group_name, showlegend=False)
                figure.data[0].name = "Consistent pattern" if trend.is_sustained else "Yearly average"
                figure.data[0].showlegend = False
                style_chart(figure)
                st.plotly_chart(figure, width="stretch")
        st.dataframe(
            trend_results_table(question_trends),
            hide_index=True,
            width="stretch",
            column_config={"p-value": st.column_config.TextColumn("p-value", help=P_VALUE_HELP)},
        )


def main() -> None:
    st.set_page_config(page_title="Adams County Youth Survey Dashboard", layout="wide")
    apply_dashboard_styles()
    st.markdown(
        '<div class="dashboard-intro">'
        '<p class="dashboard-intro__eyebrow">CFY YOUTH COALITION  /  SURVEY INSIGHTS</p>'
        '<h1 class="dashboard-intro__title">Adams County Youth Survey Dashboard</h1>'
        '<p class="dashboard-intro__subtitle">Explore survey results, compare years, and keep annual data organized in one place.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    schema = load_schema(SCHEMA_PATH)
    df_all = load_all_years(DB_PATH)
    analysis_schema = available_schema(df_all, schema)

    section = st.radio(
        "Dashboard section",
        ["Overview", "Compare Years", "Trends", "Uploaded Files"],
        horizontal=True,
        label_visibility="collapsed",
        key="dashboard_section",
    )
    if section == "Overview":
        render_overview(df_all, schema)
    elif section == "Compare Years":
        if df_all.empty:
            st.header("⇄ Compare years")
            st.info("Upload survey data in Uploaded Files, then add a second year to compare results.")
        else:
            render_comparison_tab(df_all, analysis_schema)
    elif section == "Trends":
        if df_all.empty:
            st.header("📈 Trends over time")
            st.info("Upload survey data in Uploaded Files, then add at least three years to see patterns.")
        else:
            render_trends_tab(df_all, analysis_schema)
    else:
        render_uploaded_files_tab(schema, DB_PATH)


if __name__ == "__main__":
    main()
