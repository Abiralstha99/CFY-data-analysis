# Adams County Youth Survey Analysis Pipeline — Product Requirements Document

**Author:** CFY Youth Coalition (interview conducted 2026-07-18)
**Status:** Draft — pending validation against real sample data

---

## 1. Problem Statement

Each year, CFY Youth Coalition staff receive raw survey data from the Adams County Youth Survey and manually clean it, compare it against prior years, build charts, identify trends, and write up findings for stakeholders and grant applications. This process is time-consuming, error-prone, and not easily repeatable. The coalition wants an automated pipeline that non-technical staff can run once a year to go from "raw CSV" to "polished, explorable dashboard with plain-language findings" with minimal manual effort.

## 2. Goals

- Eliminate manual, spreadsheet-based cleaning and charting each survey cycle.
- Make year-over-year and multi-year comparisons consistent and repeatable.
- Automatically surface statistically meaningful and multi-year trends, not just raw deltas.
- Produce outputs staff can lift directly into stakeholder presentations and grant applications.
- Be operable end-to-end by non-technical staff, once a year, without engineering help.
- Keep hosting/operating cost near zero (nonprofit budget).

## 3. Non-Goals (for now)

- Supporting surveys/counties other than Adams County Youth Survey in v1 — however, the pipeline should be **designed for reuse** (see §9) so extending to other surveys later doesn't require a rewrite.
- School/district-level breakdowns (explicitly out of scope — see §6.4).
- Handling PII/identifiable data (data is confirmed fully anonymous at intake).
- Automated grant-narrative writing beyond short plain-language finding summaries (staff still assemble the full grant document).

## 4. Users

| User | Role | Technical Level |
|---|---|---|
| Coalition staff (primary operator) | Uploads new year's CSV, reviews dashboard, pulls findings into reports/grants | Non-technical — needs a simple web UI, no CLI/scripting |
| Stakeholders / grant reviewers | Consume the dashboard and/or exported figures | Non-technical, view-only |
| You / future maintainer | Builds and maintains the pipeline | Technical |

## 5. Data Overview (assumptions — see §12 open items)

- **Format:** CSV export, one file per survey cycle (delivered annually).
- **History:** Several years of prior data exist, in a **consistent schema** (same questions/columns across years).
- **Content:** Likert-scale questions (e.g. strongly agree → strongly disagree) on topics such as substance use and mental health, plus demographic fields (grade, gender, race/ethnicity, etc.).
- **Privacy:** Confirmed fully anonymous — no names, student IDs, or other direct identifiers. Because breakdowns go down to demographic subgroup level, **small-cell suppression** should still be considered for very small subgroups to avoid indirect re-identification, even though this wasn't explicitly requested — flagged as a recommendation in §12.
- **Granularity required:** County-wide totals **and** demographic subgroup breakdowns (grade, gender, race/ethnicity, etc.). School/district-level breakdowns are explicitly **not** required.

## 6. Functional Requirements

### 6.1 Ingestion
- Staff upload the new year's CSV directly through the web dashboard (file picker), no folder-drop or CLI step required.
- On upload, the system validates the file can be parsed and has the expected structure before proceeding.

### 6.2 Cleaning & Validation
- **Missing columns:** If an expected column is absent from the uploaded file, drop that column from analysis (don't fail the whole run) and clearly flag it as missing in the run's data-quality summary.
- **Out-of-range values / outliers:** Normalize the column (e.g. clip or rescale out-of-range Likert values to the valid range, per documented rule) rather than dropping the rows.
- All data-quality actions taken (dropped columns, normalized values, row counts affected) must be visible to staff in a data-quality report accompanying each run — this is required so non-technical staff can sanity-check a run before trusting its output.

### 6.3 Historical Comparison & Storage
- Each year's cleaned dataset is persisted to a **lightweight database** (e.g. SQLite) alongside all prior years' cleaned data, so comparisons don't require re-cleaning old files each run.
- Current-year results are compared against the full available history, not just the immediately prior year.

### 6.4 Trend Detection
- Two complementary methods, per stakeholder decision:
  1. **Statistical significance testing** (e.g. chi-square / proportion tests) comparing year-over-year metrics.
  2. **Multi-year directional pattern detection** — sustained trends across 3+ years, not just single-year jumps.
- Both are in scope for MVP (see §7).
- Breakdowns for trend detection: county-wide and by demographic subgroup. **No school/district-level trend detection.**

### 6.5 Visualization & Dashboard
- Delivered as a **web dashboard** (not a static PDF/deck as the primary artifact).
- Must support drill-down by demographic subgroup, in addition to county-wide totals.
- Charts should visually distinguish flagged/significant trends from routine year-over-year noise.

### 6.6 Reporting for Stakeholders / Grants
- Alongside charts, the system auto-generates a **plain-language summary** of key findings/trends (e.g. "Reported vaping rates among 10th graders declined 6 points since 2024, continuing a 3-year downward trend").
- Charts and summaries should be easy to export/copy for use in grant applications (exact export mechanism — image download, copy-paste, PDF export — to be defined during implementation planning).

## 7. MVP Definition (Phase 1)

MVP = **Clean + compare + basic charts + trend detection**:
1. CSV upload → cleaning/validation → data-quality report.
2. Persist cleaned data to lightweight DB alongside prior years.
3. Year-over-year comparison + statistical significance testing + multi-year directional trend detection.
4. Dashboard with county-wide and demographic-subgroup charts, flagging significant/trending metrics.

**Explicitly deferred to Phase 2:**
- Auto-generated plain-language narrative summaries.
- Export tooling polish (one-click export formats for grant use).
- Any generalization work beyond "reasonably reusable" for other surveys (full multi-survey configuration support).

*Rationale:* narrative generation and export polish add real value but are separable from the core clean→compare→detect→visualize loop, and can be layered on once the core pipeline is validated against real data.

## 8. Tech Stack

- **Language:** Python.
- **Data processing:** pandas.
- **Storage:** SQLite (or similar single-file DB) holding all years' cleaned data — chosen over flat files for simpler querying of multi-year comparisons, and over a hosted DB to keep costs at zero.
- **Visualization:** Plotly (interactive, dashboard-friendly).
- **Dashboard/web app:** Streamlit — matches the "web app with file upload" requirement, non-technical-friendly, and deploys free via Streamlit Community Cloud.
- **Hosting:** Free/low-cost cloud tier (e.g. Streamlit Community Cloud) per nonprofit budget constraint.

## 9. Extensibility / Design for Reuse

Coalition may run similar surveys elsewhere in the future. The pipeline should therefore:
- Keep survey schema (question list, valid ranges, demographic fields) in a **config file**, not hardcoded, so a new survey/county can be onboarded by writing a new config rather than modifying pipeline code.
- Keep cleaning, comparison, and trend-detection logic schema-agnostic where reasonably possible.
- This is a **design principle** for the codebase, not a Phase 1 deliverable — no multi-survey UI/switching is required in MVP.

## 10. Non-Functional Requirements

- **Cost:** Near-zero ongoing hosting cost.
- **Usability:** Entire annual workflow (upload → review dashboard → pull findings) must be completable by non-technical staff without engineering support.
- **Reliability:** A malformed or partially-invalid upload must never crash the app silently — staff must always see a clear data-quality report explaining what happened.
- **Data privacy:** No PII is expected at intake; pipeline should not introduce any (e.g. no logging of raw uploaded files to any third-party service beyond the chosen host).

## 11. Success Criteria

- Staff can go from "new year's CSV in hand" to "reviewed dashboard with flagged trends" in a single sitting, without developer involvement.
- Year-over-year comparisons and trend flags match what a careful manual analysis would find (validated against at least one historical year as a regression check).
- Dashboard output (charts + summary figures) is usable as-is (or with light copy/paste) in a real grant application.

## 12. Open Items / Risks — To Resolve Before or During Implementation Planning

1. **Real sample data not yet provided.** This PRD assumes a Likert + demographics schema; actual column names, value encodings, and edge cases (e.g. skipped questions, "prefer not to answer") are unknown until real CSVs (current + ≥1 prior year) are reviewed. **Action:** provide sample files before implementation planning begins.
2. **Small-cell suppression** for demographic subgroups was not explicitly requested but is a common requirement for anonymous youth survey data to prevent indirect identification of small groups. Recommend confirming whether a minimum-N suppression rule is needed.
3. **Exact significance test and threshold rules** (e.g. which test, what p-value/effect-size cutoff counts as "meaningful," how "sustained multi-year trend" is defined numerically) need to be pinned down — likely during implementation planning with sample data in hand.
4. **Export mechanism** for grant-application use (image download vs. PDF vs. copy-paste) deferred to Phase 2 — needs a decision once MVP dashboard is running.
5. **Column drift across years:** stated as "consistent format" historically, but real files should be checked for minor renames/reordering that could break naive comparisons.

## 13. Phasing Summary

| Phase | Scope |
|---|---|
| Pre-work | Obtain and review real sample CSVs (current + historical); confirm open items in §12 |
| Phase 1 (MVP) | Ingestion, cleaning/validation, historical storage, year-over-year + multi-year trend detection, dashboard with county/subgroup charts |
| Phase 2 | Auto-generated plain-language summaries, export tooling for grant use, any further reuse/generalization work |
