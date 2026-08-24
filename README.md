# Adams County Youth Survey Dashboard

A data pipeline and interactive dashboard that automates annual survey analysis for the CFY Youth Coalition. Upload raw CSV data, get cleaned results, year-over-year statistical comparisons, and multi-year trend detection — all in a browser.

## Overview

Each year, coalition staff receive raw survey data from the Adams County Youth Survey. This tool replaces the manual spreadsheet-based workflow with an automated pipeline that:

- **Cleans and validates** uploaded CSVs against a configurable schema
- **Persists** cleaned data across years in a local SQLite database
- **Detects statistically significant changes** between any two years (Welch's t-test)
- **Identifies sustained multi-year trends** across 3+ years (linear regression)
- **Visualizes** results in an interactive Plotly dashboard with demographic breakdowns

## Quick Start

### Prerequisites

- Python 3.10+

### Installation

```bash
pip install -r requirements.txt
```

### Run the Dashboard

```bash
streamlit run cfy_pipeline/dashboard.py
```

Then open the local URL shown in terminal. Upload a survey CSV to get started.

> [!TIP]
> A sample CSV is included at `data/sample_2025.csv` for testing.

## How It Works

```
Raw CSV → cleaning → SQLite storage → statistical analysis → Plotly charts
```

1. **Upload** — Staff upload the year's CSV through the web UI
2. **Clean** — The pipeline validates against `config/survey_schema.yaml`, clips out-of-range values, and flags missing columns
3. **Store** — Cleaned data is persisted alongside all prior years
4. **Analyze** — Year-over-year t-tests and multi-year trend regression run automatically
5. **Visualize** — Interactive charts with significance highlighting and demographic drill-downs

## Project Structure

```
cfy_pipeline/
├── __init__.py       # Package API (process_uploaded_file)
├── schema.py         # Survey schema loader (from YAML config)
├── cleaning.py       # Data validation and normalization
├── storage.py        # SQLite persistence layer
├── comparison.py     # Year-over-year statistical tests
├── trends.py         # Multi-year trend detection
├── charts.py         # Plotly figure builders
└── dashboard.py      # Streamlit web app

config/
└── survey_schema.yaml  # Survey structure definition

data/
├── sample_2025.csv     # Sample data for testing
└── survey.db           # SQLite database (created on first upload)

tests/                  # pytest test suite (25 tests)
docs/
├── architecture.md     # System design and decisions
└── prd/                # Product requirements document
```

## Configuration

The survey schema is defined in `config/survey_schema.yaml`. To adapt the pipeline for a different survey:

1. Create a new YAML file with your demographics and questions
2. Point `SCHEMA_PATH` in `dashboard.py` to the new config

No pipeline code changes needed — the analysis logic is schema-agnostic.

```yaml
demographics:
  - name: grade
    valid_values: ["6", "7", "8", "9", "10", "11", "12"]

questions:
  - name: q_vaping_30day
    label: "Vaping frequency (past 30 days)"
    category: substance_use
    valid_range: [1, 5]
```

## Testing

```bash
python -m pytest tests/ -v
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python |
| Data processing | pandas |
| Statistics | scipy |
| Storage | SQLite |
| Visualization | Plotly |
| Web framework | Streamlit |

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for detailed system design, data flow, and key decisions.
