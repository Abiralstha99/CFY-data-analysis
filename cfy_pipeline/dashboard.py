"""Streamlit dashboard — run with: streamlit run cfy_pipeline/dashboard.py

Thin UI layer: all analysis logic lives in the cfy_pipeline modules.
group_by=None means county-wide (no demographic split).
st.rerun() after upload forces a refresh since Streamlit doesn't detect DB changes.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from cfy_pipeline import DataQualityReport, SurveySchema, load_schema, process_uploaded_file
from cfy_pipeline.charts import build_comparison_figure, build_trend_figure
from cfy_pipeline.comparison import SIGNIFICANCE_THRESHOLD, ComparisonResult, compare_years
from cfy_pipeline.storage import load_all_years, load_year
from cfy_pipeline.trends import MIN_YEARS_FOR_TREND, TrendResult, detect_multi_year_trends

# Paths are relative to this file's parent (cfy_pipeline/) going up one level
# to the project root. Works in both local dev and Streamlit Cloud deployments.
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "config" / "survey_schema.yaml"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "survey.db"

COUNTY_WIDE_OPTION = "County-wide (All)"
LAST_UPLOAD_STATE_KEY = "last_upload"


def format_p_value(p_value: float) -> str:
    return "< 0.001" if p_value < 0.001 else f"{p_value:.3f}"


def render_metrics_row(df_all: pd.DataFrame, schema: SurveySchema) -> None:
    """Top-level summary metrics shown above the tabs when data exists."""
    years = sorted(df_all["survey_year"].unique().tolist())
    latest_year = years[-1]

    significant_changes = 0
    if len(years) >= 2:
        comparisons = compare_years(df_all, schema, previous_year=years[-2], current_year=latest_year)
        significant_changes = sum(r.significant for r in comparisons)

    sustained_trends = sum(t.is_sustained for t in detect_multi_year_trends(df_all, schema))

    total, years_col, latest, changes, trends = st.columns(5)
    total.metric("Total responses", f"{len(df_all):,}")
    years_col.metric("Years stored", f"{years[0]}–{latest_year}" if len(years) > 1 else str(latest_year))
    latest.metric(f"{latest_year} responses", f"{int((df_all['survey_year'] == latest_year).sum()):,}")
    changes.metric("Significant YoY changes", significant_changes)
    trends.metric("Sustained trends", sustained_trends)


def render_quality_report(year: int, report: DataQualityReport) -> None:
    """Display the data quality report after a successful upload."""
    st.success(f"Processed {report.row_count} responses for {year}.")
    with st.expander("Data quality details", expanded=report.has_issues()):
        if report.dropped_columns:
            st.warning(
                "Columns expected by the schema but missing from the file "
                f"(dropped): {', '.join(report.dropped_columns)}"
            )
        if report.normalized_columns:
            st.write("Values normalized during cleaning (out-of-range or invalid):")
            st.dataframe(
                pd.DataFrame(
                    {
                        "Column": list(report.normalized_columns.keys()),
                        "Values normalized": list(report.normalized_columns.values()),
                    }
                ),
                hide_index=True,
            )
        if not report.has_issues():
            st.write("No issues — every column matched the schema and all values were in range.")

        preview = load_year(DB_PATH, year).drop(columns=["survey_year"]).head(10)
        st.caption("Preview of cleaned stored data (first 10 rows)")
        st.dataframe(preview, hide_index=True)


def render_upload_tab(schema: SurveySchema, df_all: pd.DataFrame) -> None:
    """Upload tab: file picker, year selector, confirmation for overwrites."""
    st.subheader("Upload a survey year")
    year_counts = df_all["survey_year"].value_counts().to_dict() if not df_all.empty else {}

    year = int(st.number_input("Survey Year", min_value=2000, max_value=2100, step=1, value=2025))
    uploaded_file = st.file_uploader("Choose the survey CSV file", type="csv")

    if uploaded_file is not None:
        existing_rows = year_counts.get(year, 0)
        confirmed = True
        if existing_rows:
            # Guard against accidental overwrites — staff must explicitly confirm
            st.warning(
                f"{existing_rows} responses are already stored for {year}. "
                "Processing this file will replace them."
            )
            confirmed = st.checkbox(f"Yes, replace the {year} data")

        if st.button("Process Upload", type="primary", disabled=not confirmed):
            report = process_uploaded_file(uploaded_file, year, schema, DB_PATH)
            st.session_state[LAST_UPLOAD_STATE_KEY] = {"year": year, "report": report}
            st.rerun()

    last_upload = st.session_state.get(LAST_UPLOAD_STATE_KEY)
    if last_upload is not None:
        render_quality_report(last_upload["year"], last_upload["report"])


def comparison_results_table(results: list[ComparisonResult]) -> pd.DataFrame:
    """Format comparison results as a DataFrame for display below charts."""
    return pd.DataFrame(
        {
            "Group": [r.group for r in results],
            f"{results[0].previous_year} mean": [round(r.previous_mean, 2) for r in results],
            f"{results[0].current_year} mean": [round(r.current_year_mean, 2) for r in results],
            "Change": [round(r.current_year_mean - r.previous_mean, 2) for r in results],
            "p-value": [format_p_value(r.p_value) for r in results],
            "Significant": ["Yes" if r.significant else "No" for r in results],
        }
    )


def render_comparison_tab(df_all: pd.DataFrame, schema: SurveySchema, group_by: str | None) -> None:
    """Year-over-year tab: select two years, see per-question bar charts."""
    years = sorted(df_all["survey_year"].unique().tolist())
    if len(years) < 2:
        st.info("Year-over-year comparison needs at least 2 years of data.")
        return

    current_col, previous_col = st.columns(2)
    current_year = current_col.selectbox("Current year", years[::-1], index=0)
    previous_options = [y for y in years[::-1] if y < current_year]
    if not previous_options:
        st.info("No earlier year available to compare against.")
        return
    previous_year = previous_col.selectbox("Compare against", previous_options, index=0)

    st.caption(
        f"Red bars mark a statistically significant change (Welch's t-test, "
        f"p < {SIGNIFICANCE_THRESHOLD}). Hover a bar for its p-value."
    )

    comparisons = compare_years(
        df_all, schema, previous_year=previous_year, current_year=current_year, group_by=group_by
    )
    for question in schema.questions:
        question_results = [r for r in comparisons if r.question_name == question.name]
        if not question_results:
            continue
        st.plotly_chart(build_comparison_figure(question_results, question.label))
        st.dataframe(comparison_results_table(question_results), hide_index=True)


def trend_results_table(trends: list[TrendResult]) -> pd.DataFrame:
    """Format trend results as a DataFrame for display below charts."""
    return pd.DataFrame(
        {
            "Group": [t.group for t in trends],
            "Years": [f"{t.years[0]}–{t.years[-1]}" for t in trends],
            "Slope per year": [round(t.slope, 3) for t in trends],
            "p-value": [format_p_value(t.p_value) for t in trends],
            "Direction": [t.direction for t in trends],
        }
    )


def render_trends_tab(df_all: pd.DataFrame, schema: SurveySchema, group_by: str | None) -> None:
    """Multi-year trends tab: line charts per question with regression results."""
    year_count = df_all["survey_year"].nunique()
    if year_count < MIN_YEARS_FOR_TREND:
        st.info(
            f"Trend detection needs at least {MIN_YEARS_FOR_TREND} years of data "
            f"({year_count} stored so far)."
        )
        return

    st.caption(
        f"Red lines mark a sustained trend (linear regression across yearly means, "
        f"p < {SIGNIFICANCE_THRESHOLD})."
    )

    trends = detect_multi_year_trends(df_all, schema, group_by=group_by)
    for question in schema.questions:
        question_trends = [t for t in trends if t.question_name == question.name]
        if not question_trends:
            continue
        for trend in question_trends:
            st.plotly_chart(build_trend_figure(trend, question.label))
        st.dataframe(trend_results_table(question_trends), hide_index=True)


def main() -> None:
    st.set_page_config(page_title="Adams County Youth Survey Dashboard", layout="wide")
    st.title("Adams County Youth Survey Dashboard")
    schema = load_schema(SCHEMA_PATH)
    df_all = load_all_years(DB_PATH)

    # Sidebar: demographic breakdown control applies to comparison + trends tabs
    with st.sidebar:
        st.header("View options")
        group_by_choice = st.selectbox("Break down by", [COUNTY_WIDE_OPTION] + schema.demographic_names())
        group_by = None if group_by_choice == COUNTY_WIDE_OPTION else group_by_choice
        if not df_all.empty:
            st.caption(
                f"{len(df_all):,} responses stored across "
                f"{df_all['survey_year'].nunique()} year(s)."
            )

    if df_all.empty:
        st.info("No data yet — upload a survey file to get started.")
    else:
        render_metrics_row(df_all, schema)

    upload_tab, comparison_tab, trends_tab = st.tabs(
        ["📤 Upload", "📊 Year-over-Year", "📈 Multi-Year Trends"]
    )
    with upload_tab:
        render_upload_tab(schema, df_all)
    with comparison_tab:
        if df_all.empty:
            st.info("Upload data first to see comparisons.")
        else:
            render_comparison_tab(df_all, schema, group_by)
    with trends_tab:
        if df_all.empty:
            st.info("Upload data first to see trends.")
        else:
            render_trends_tab(df_all, schema, group_by)


if __name__ == "__main__":
    main()
