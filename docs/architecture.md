# Architecture

## Overview

This package implements a **CSV → clean → store → analyze → visualize** pipeline for the Adams County Youth Survey. It runs once per year when new survey data arrives. Non-technical staff operate it entirely through a Streamlit web dashboard.

## Data Flow

```
Raw CSV (uploaded by staff)
    │
    ▼
cleaning.py — validate against schema, normalize values
    │
    ▼
storage.py — persist to SQLite (data/survey.db)
    │
    ▼
comparison.py — year-over-year Welch's t-tests
trends.py     — multi-year linear regression on means
    │
    ▼
charts.py — build Plotly figures (stateless)
    │
    ▼
dashboard.py — Streamlit UI (thin wiring layer)
```



## Module Responsibilities


| Module          | Role                                                                                                                                                                                     |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `schema.py`     | Loads `config/survey_schema.yaml`; defines what columns and values are valid. Single source of truth for CSV structure.                                                                  |
| `cleaning.py`   | Validates and normalizes raw CSV data against the schema. Business rules: clip out-of-range Likert values, replace invalid demographics with "Unknown", drop missing columns gracefully. |
| `storage.py`    | SQLite persistence layer. One DB file accumulates all years. Upsert semantics: re-uploading a year replaces previous data.                                                               |
| `comparison.py` | Year-over-year statistical tests. Uses Welch's t-test (unequal variance, unpaired — responses are anonymous across years).                                                               |
| `trends.py`     | Multi-year trend detection. Fits linear regression on yearly question means. Flags sustained directional change across 3+ years.                                                         |
| `charts.py`     | Pure Plotly figure builders. No I/O, no state. Takes analysis results → returns figures.                                                                                                 |
| `dashboard.py`  | Streamlit app. Wires UI widgets to the analysis modules. All logic lives elsewhere; this file is purely presentation.                                                                    |
| `__init__.py`   | Package entry point. Exposes `process_uploaded_file` as the programmatic ingestion API.                                                                                                  |




## Key Design Decisions



### Config-driven schema

The survey structure lives in `config/survey_schema.yaml`, not in code. To onboard a new survey, add a new YAML file — the pipeline logic is schema-agnostic.

### SQLite over flat files

Chosen for multi-year querying without re-parsing CSVs each run. Single-file DB keeps hosting cost at zero (no server). The DB is gitignored; each deployment starts empty and accumulates data through the upload UI.

### Statistical methods

- **Year-over-year**: Welch's t-test (not chi-square) because we're comparing Likert scale means. Not paired because responses are anonymous — no way to link individuals across years.
- **Multi-year trends**: Linear regression on yearly means (not individual responses). The unit of observation is the yearly aggregate because each year has different respondents.



### Color system (charts)

- Red `#d03b3b` = statistically significant / sustained trend (action needed)
- Blue `#2a78d6` = no significant change (baseline)
- Gray `#898781` = previous-year reference (context)

Validated for color-vision-deficiency separation and WCAG ≥3:1 contrast.

### Preserve rows over data purity

Cleaning rules (PRD §6.2) prioritize keeping every row: out-of-range values are clipped, invalid demographics become "Unknown". Rows are never dropped. This maximizes sample size for the coalition's small-county data.

## Extensibility

The coalition may run similar surveys elsewhere. The pipeline is designed for reuse:

- Schema is config-driven (new YAML = new survey)
- Cleaning, comparison, and trend logic are schema-agnostic
- No multi-survey UI/switching is built yet (Phase 2)



## Running

```bash
# Dashboard
streamlit run cfy_pipeline/dashboard.py

# Tests
python -m pytest tests/ -v
```



## Limitations

- Trend detection assumes linearity — non-linear patterns (U-shaped, plateau) will be missed.
- With exactly 3 years of data, regression has low statistical power.
- No small-cell suppression yet for tiny demographic subgroups (flagged in PRD §12).

