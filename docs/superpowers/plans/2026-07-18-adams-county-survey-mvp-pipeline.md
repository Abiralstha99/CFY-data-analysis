# Adams County Youth Survey MVP Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python pipeline + Streamlit dashboard that ingests an annual survey CSV, cleans/validates it against a configurable schema, stores it alongside prior years in SQLite, detects year-over-year and multi-year trends with statistical testing, and renders county-wide and demographic-subgroup charts.

**Architecture:** A Python package (`cfy_pipeline`) implements schema-driven cleaning, SQLite-backed multi-year storage, statistical comparison, and trend detection as independently testable modules with no Streamlit dependency. A thin Streamlit dashboard (`cfy_pipeline/dashboard.py`) wires these modules to a browser UI for upload, review, and chart exploration. All survey structure (questions, valid ranges, demographic categories) lives in `config/survey_schema.yaml` so the pipeline can be reused for a different survey later by swapping the config, not the code.

**Tech Stack:** Python 3.11+, pandas, PyYAML, scipy, streamlit, plotly, pytest.

## Global Constraints

- Tech stack is fixed to Python + pandas + PyYAML + scipy + streamlit + plotly, per PRD §8 — do not introduce alternative frameworks.
- Survey structure (question names, labels, categories, valid ranges, demographic fields/values) must live in `config/survey_schema.yaml`, never hardcoded in Python, per PRD §9 (design for reuse).
- Data is assumed fully anonymous at intake — no PII handling, hashing, or redaction logic is in scope, per PRD §5.
- No school/district-level breakdowns anywhere in this plan — only county-wide ("All") and demographic-subgroup views, per PRD §6.4.
- Multi-year trend detection requires at least 3 years of data before flagging a trend, per PRD §6.4.
- Statistical significance threshold is p < 0.05 for both year-over-year comparison and multi-year trend regression — this is an assumed default (PRD §12 open item) and must be revisited once real data is available.
- Auto-generated plain-language summaries and export tooling (PDF/image export for grant use) are explicitly **out of scope** for this plan — they are Phase 2 per PRD §7.
- The exact survey schema (columns, question wording, valid ranges) used throughout this plan is an **assumed placeholder schema** pending real sample data (PRD §12, item 1). Task 1 documents this assumption explicitly; adjusting `config/survey_schema.yaml` to match real data later requires no code changes elsewhere.

---

## Assumed Survey Schema (placeholder, pending real data)

Because no real sample CSV was available at planning time, this plan uses a placeholder schema modeled on the PRD's description (Likert-scale substance-use/mental-health questions + demographics). It is intentionally realistic but **must be validated against actual survey files before production use**:

- **Demographics:** `grade` (6–12), `gender`, `race_ethnicity`
- **Questions (5-point Likert, 1–5):**
  - `q_vaping_30day` (substance_use) — vaping frequency, past 30 days
  - `q_alcohol_30day` (substance_use) — alcohol use frequency, past 30 days
  - `q_mh_sad_hopeless` (mental_health) — persistent sadness/hopelessness
  - `q_mh_anxiety` (mental_health) — anxiety symptoms
  - `q_connectedness_school` (protective_factors) — school connectedness

---

### Task 1: Project Scaffolding & Survey Schema Config

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `config/survey_schema.yaml`
- Create: `cfy_pipeline/__init__.py`
- Create: `cfy_pipeline/schema.py`
- Create: `data/.gitkeep`
- Test: `tests/test_schema.py`

**Interfaces:**
- Produces: `DemographicField(name: str, valid_values: tuple[str, ...])`, `QuestionField(name: str, label: str, category: str, valid_range: tuple[int, int])`, `SurveySchema(demographics: tuple[DemographicField, ...], questions: tuple[QuestionField, ...])` with methods `demographic_names() -> list[str]`, `question_names() -> list[str]`, `expected_columns() -> list[str]`, `question_by_name(name: str) -> QuestionField`, `demographic_by_name(name: str) -> DemographicField`; `load_schema(path: str | Path) -> SurveySchema`.

- [ ] **Step 1: Create the dependency and pytest config files**

`requirements.txt`:
```
pandas>=2.0
PyYAML>=6.0
scipy>=1.10
streamlit>=1.30
plotly>=5.18
pytest>=8.0
```

`pyproject.toml`:
```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: all packages install without error.

- [ ] **Step 3: Create the survey schema config**

Create `config/survey_schema.yaml`:
```yaml
demographics:
  - name: grade
    valid_values: ["6", "7", "8", "9", "10", "11", "12"]
  - name: gender
    valid_values: ["Male", "Female", "Non-binary", "Prefer not to say"]
  - name: race_ethnicity
    valid_values:
      - "White"
      - "Black or African American"
      - "Hispanic or Latino"
      - "Asian"
      - "American Indian or Alaska Native"
      - "Native Hawaiian or Pacific Islander"
      - "Two or more races"
      - "Prefer not to say"

questions:
  - name: q_vaping_30day
    label: "Vaping frequency (past 30 days)"
    category: substance_use
    valid_range: [1, 5]
  - name: q_alcohol_30day
    label: "Alcohol use frequency (past 30 days)"
    category: substance_use
    valid_range: [1, 5]
  - name: q_mh_sad_hopeless
    label: "Persistent sadness/hopelessness"
    category: mental_health
    valid_range: [1, 5]
  - name: q_mh_anxiety
    label: "Anxiety symptoms"
    category: mental_health
    valid_range: [1, 5]
  - name: q_connectedness_school
    label: "School connectedness"
    category: protective_factors
    valid_range: [1, 5]
```

- [ ] **Step 4: Create the package directory and data directory**

Run: `mkdir -p cfy_pipeline data && touch cfy_pipeline/__init__.py data/.gitkeep`
Expected: `cfy_pipeline/__init__.py` and `data/.gitkeep` exist (both empty files).

- [ ] **Step 5: Write the failing test for schema loading**

Create `tests/test_schema.py`:
```python
from pathlib import Path

from cfy_pipeline.schema import load_schema

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "config" / "survey_schema.yaml"


def test_load_schema_parses_demographics_and_questions():
    schema = load_schema(SCHEMA_PATH)

    assert "grade" in schema.demographic_names()
    assert "gender" in schema.demographic_names()
    assert "q_vaping_30day" in schema.question_names()

    vaping = schema.question_by_name("q_vaping_30day")
    assert vaping.category == "substance_use"
    assert vaping.valid_range == (1, 5)

    grade = schema.demographic_by_name("grade")
    assert "9" in grade.valid_values


def test_expected_columns_combines_demographics_and_questions():
    schema = load_schema(SCHEMA_PATH)
    expected = schema.expected_columns()

    assert "grade" in expected
    assert "q_mh_anxiety" in expected
    assert len(expected) == len(schema.demographics) + len(schema.questions)
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cfy_pipeline.schema'`

- [ ] **Step 7: Implement the schema loader**

Create `cfy_pipeline/schema.py`:
```python
from __future__ import annotations

import dataclasses
from pathlib import Path

import yaml


@dataclasses.dataclass(frozen=True)
class DemographicField:
    name: str
    valid_values: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class QuestionField:
    name: str
    label: str
    category: str
    valid_range: tuple[int, int]


@dataclasses.dataclass(frozen=True)
class SurveySchema:
    demographics: tuple[DemographicField, ...]
    questions: tuple[QuestionField, ...]

    def demographic_names(self) -> list[str]:
        return [d.name for d in self.demographics]

    def question_names(self) -> list[str]:
        return [q.name for q in self.questions]

    def expected_columns(self) -> list[str]:
        return self.demographic_names() + self.question_names()

    def question_by_name(self, name: str) -> QuestionField:
        for q in self.questions:
            if q.name == name:
                return q
        raise KeyError(f"Unknown question field: {name}")

    def demographic_by_name(self, name: str) -> DemographicField:
        for d in self.demographics:
            if d.name == name:
                return d
        raise KeyError(f"Unknown demographic field: {name}")


def load_schema(path: str | Path) -> SurveySchema:
    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    demographics = tuple(
        DemographicField(name=d["name"], valid_values=tuple(d["valid_values"]))
        for d in raw["demographics"]
    )
    questions = tuple(
        QuestionField(
            name=q["name"],
            label=q["label"],
            category=q["category"],
            valid_range=tuple(q["valid_range"]),
        )
        for q in raw["questions"]
    )
    return SurveySchema(demographics=demographics, questions=questions)
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/test_schema.py -v`
Expected: PASS (2 passed)

- [ ] **Step 9: Commit**

```bash
git init
git add requirements.txt pyproject.toml config/survey_schema.yaml cfy_pipeline/__init__.py cfy_pipeline/schema.py data/.gitkeep tests/test_schema.py
git commit -m "feat: add project scaffolding and survey schema loader"
```

---

### Task 2: Data Cleaning & Validation

**Files:**
- Create: `cfy_pipeline/cleaning.py`
- Test: `tests/test_cleaning.py`

**Interfaces:**
- Consumes: `SurveySchema`, `DemographicField`, `QuestionField` from `cfy_pipeline.schema` (Task 1).
- Produces: `DataQualityReport(dropped_columns: list[str], normalized_columns: dict[str, int], row_count: int)` with method `has_issues() -> bool`; `clean_dataframe(df: pd.DataFrame, schema: SurveySchema) -> tuple[pd.DataFrame, DataQualityReport]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cleaning.py`:
```python
import pandas as pd

from cfy_pipeline.cleaning import clean_dataframe
from cfy_pipeline.schema import DemographicField, QuestionField, SurveySchema


def make_test_schema() -> SurveySchema:
    return SurveySchema(
        demographics=(
            DemographicField(name="grade", valid_values=("9", "10", "11", "12")),
        ),
        questions=(
            QuestionField(name="q_vaping_30day", label="Vaping", category="substance_use", valid_range=(1, 5)),
        ),
    )


def test_clean_dataframe_drops_missing_expected_column():
    schema = make_test_schema()
    df = pd.DataFrame({"grade": ["9", "10"]})

    cleaned, report = clean_dataframe(df, schema)

    assert "q_vaping_30day" not in cleaned.columns
    assert report.dropped_columns == ["q_vaping_30day"]


def test_clean_dataframe_normalizes_out_of_range_likert_values():
    schema = make_test_schema()
    df = pd.DataFrame({
        "grade": ["9", "10", "11"],
        "q_vaping_30day": [1, 7, -2],
    })

    cleaned, report = clean_dataframe(df, schema)

    assert cleaned["q_vaping_30day"].tolist() == [1, 5, 1]
    assert report.normalized_columns["q_vaping_30day"] == 2


def test_clean_dataframe_normalizes_invalid_categorical_value():
    schema = make_test_schema()
    df = pd.DataFrame({
        "grade": ["9", "13"],
        "q_vaping_30day": [1, 2],
    })

    cleaned, report = clean_dataframe(df, schema)

    assert cleaned["grade"].tolist() == ["9", "Unknown"]
    assert report.normalized_columns["grade"] == 1


def test_clean_dataframe_reports_row_count():
    schema = make_test_schema()
    df = pd.DataFrame({
        "grade": ["9", "10"],
        "q_vaping_30day": [1, 2],
    })

    _, report = clean_dataframe(df, schema)

    assert report.row_count == 2


def test_has_issues_false_when_data_is_clean():
    schema = make_test_schema()
    df = pd.DataFrame({"grade": ["9"], "q_vaping_30day": [1]})

    _, report = clean_dataframe(df, schema)

    assert report.has_issues() is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cleaning.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cfy_pipeline.cleaning'`

- [ ] **Step 3: Implement the cleaning module**

Create `cfy_pipeline/cleaning.py`:
```python
from __future__ import annotations

import dataclasses

import pandas as pd

from cfy_pipeline.schema import SurveySchema


@dataclasses.dataclass
class DataQualityReport:
    dropped_columns: list[str]
    normalized_columns: dict[str, int]
    row_count: int

    def has_issues(self) -> bool:
        return bool(self.dropped_columns) or bool(self.normalized_columns)


def clean_dataframe(df: pd.DataFrame, schema: SurveySchema) -> tuple[pd.DataFrame, DataQualityReport]:
    dropped_columns: list[str] = []
    normalized_columns: dict[str, int] = {}
    cleaned = df.copy()

    for demographic in schema.demographics:
        if demographic.name not in cleaned.columns:
            dropped_columns.append(demographic.name)
            continue
        invalid_mask = ~cleaned[demographic.name].isin(demographic.valid_values)
        invalid_count = int(invalid_mask.sum())
        if invalid_count:
            cleaned.loc[invalid_mask, demographic.name] = "Unknown"
            normalized_columns[demographic.name] = invalid_count

    for question in schema.questions:
        if question.name not in cleaned.columns:
            dropped_columns.append(question.name)
            continue
        low, high = question.valid_range
        out_of_range_mask = (cleaned[question.name] < low) | (cleaned[question.name] > high)
        out_of_range_count = int(out_of_range_mask.sum())
        if out_of_range_count:
            cleaned[question.name] = cleaned[question.name].clip(lower=low, upper=high)
            normalized_columns[question.name] = out_of_range_count

    kept_columns = [c for c in schema.expected_columns() if c not in dropped_columns]
    cleaned = cleaned[kept_columns]

    report = DataQualityReport(
        dropped_columns=dropped_columns,
        normalized_columns=normalized_columns,
        row_count=len(cleaned),
    )
    return cleaned, report
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cleaning.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add cfy_pipeline/cleaning.py tests/test_cleaning.py
git commit -m "feat: add schema-driven data cleaning and validation"
```

---

### Task 3: SQLite Storage Layer

**Files:**
- Create: `cfy_pipeline/storage.py`
- Test: `tests/test_storage.py`

**Interfaces:**
- Consumes: none from earlier tasks (works on plain `pd.DataFrame`).
- Produces: `save_year_data(df: pd.DataFrame, year: int, db_path: str | Path) -> None`, `load_all_years(db_path: str | Path) -> pd.DataFrame`, `load_year(db_path: str | Path, year: int) -> pd.DataFrame`. Persisted table adds a `survey_year` integer column to every stored row.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_storage.py`:
```python
import pandas as pd

from cfy_pipeline.storage import load_all_years, load_year, save_year_data


def test_save_and_load_all_years(tmp_path):
    db_path = tmp_path / "survey.db"
    df_2024 = pd.DataFrame({"grade": ["9", "10"], "q_vaping_30day": [1, 2]})
    df_2025 = pd.DataFrame({"grade": ["9", "10"], "q_vaping_30day": [2, 3]})

    save_year_data(df_2024, 2024, db_path)
    save_year_data(df_2025, 2025, db_path)

    all_years = load_all_years(db_path)

    assert set(all_years["survey_year"]) == {2024, 2025}
    assert len(all_years) == 4


def test_save_year_data_is_idempotent_per_year(tmp_path):
    db_path = tmp_path / "survey.db"
    df_v1 = pd.DataFrame({"grade": ["9"], "q_vaping_30day": [1]})
    df_v2 = pd.DataFrame({"grade": ["9", "10"], "q_vaping_30day": [1, 2]})

    save_year_data(df_v1, 2024, db_path)
    save_year_data(df_v2, 2024, db_path)

    result = load_year(db_path, 2024)

    assert len(result) == 2


def test_load_year_filters_to_requested_year(tmp_path):
    db_path = tmp_path / "survey.db"
    save_year_data(pd.DataFrame({"grade": ["9"], "q_vaping_30day": [1]}), 2024, db_path)
    save_year_data(pd.DataFrame({"grade": ["10"], "q_vaping_30day": [3]}), 2025, db_path)

    result = load_year(db_path, 2025)

    assert len(result) == 1
    assert result.iloc[0]["grade"] == "10"


def test_load_all_years_returns_empty_dataframe_when_no_data(tmp_path):
    db_path = tmp_path / "empty.db"

    result = load_all_years(db_path)

    assert result.empty
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cfy_pipeline.storage'`

- [ ] **Step 3: Implement the storage module**

Create `cfy_pipeline/storage.py`:
```python
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

TABLE_NAME = "survey_responses"


def _table_exists(conn: sqlite3.Connection) -> bool:
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (TABLE_NAME,)
    )
    return cursor.fetchone() is not None


def save_year_data(df: pd.DataFrame, year: int, db_path: str | Path) -> None:
    to_write = df.copy()
    to_write["survey_year"] = year

    with sqlite3.connect(db_path) as conn:
        if _table_exists(conn):
            conn.execute(f"DELETE FROM {TABLE_NAME} WHERE survey_year = ?", (year,))
        to_write.to_sql(TABLE_NAME, conn, if_exists="append", index=False)


def load_all_years(db_path: str | Path) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        if not _table_exists(conn):
            return pd.DataFrame()
        return pd.read_sql(f"SELECT * FROM {TABLE_NAME}", conn)


def load_year(db_path: str | Path, year: int) -> pd.DataFrame:
    all_years = load_all_years(db_path)
    if all_years.empty:
        return all_years
    return all_years[all_years["survey_year"] == year].reset_index(drop=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_storage.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add cfy_pipeline/storage.py tests/test_storage.py
git commit -m "feat: add SQLite-backed multi-year storage layer"
```

---

### Task 4: Year-over-Year Comparison with Statistical Significance

**Files:**
- Create: `cfy_pipeline/comparison.py`
- Test: `tests/test_comparison.py`

**Interfaces:**
- Consumes: `SurveySchema` from `cfy_pipeline.schema` (Task 1); expects a DataFrame with a `survey_year` column as produced by `cfy_pipeline.storage.load_all_years` (Task 3).
- Produces: `ComparisonResult(question_name: str, group: str, previous_year: int, current_year: int, previous_mean: float, current_year_mean: float, p_value: float, significant: bool)`; `compare_years(df_all: pd.DataFrame, schema: SurveySchema, previous_year: int, current_year: int, group_by: str | None = None) -> list[ComparisonResult]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_comparison.py`:
```python
import pandas as pd

from cfy_pipeline.comparison import compare_years
from cfy_pipeline.schema import QuestionField, SurveySchema


def make_schema() -> SurveySchema:
    return SurveySchema(
        demographics=(),
        questions=(
            QuestionField(name="q_vaping_30day", label="Vaping", category="substance_use", valid_range=(1, 5)),
        ),
    )


def test_compare_years_detects_significant_change():
    schema = make_schema()
    df = pd.DataFrame({
        "survey_year": [2024] * 20 + [2025] * 20,
        "q_vaping_30day": [1] * 20 + [5] * 20,
    })

    results = compare_years(df, schema, previous_year=2024, current_year=2025)

    assert len(results) == 1
    result = results[0]
    assert result.question_name == "q_vaping_30day"
    assert result.significant is True
    assert result.current_year_mean > result.previous_mean


def test_compare_years_reports_not_significant_for_similar_years():
    schema = make_schema()
    df = pd.DataFrame({
        "survey_year": [2024] * 20 + [2025] * 20,
        "q_vaping_30day": ([1, 2] * 10) + ([1, 2] * 10),
    })

    results = compare_years(df, schema, previous_year=2024, current_year=2025)

    assert results[0].significant is False


def test_compare_years_by_group_splits_results_per_subgroup():
    schema = make_schema()
    df = pd.DataFrame({
        "survey_year": [2024] * 20 + [2025] * 20,
        "grade": (["9"] * 10 + ["10"] * 10) * 2,
        "q_vaping_30day": [1] * 20 + [5] * 20,
    })

    results = compare_years(df, schema, previous_year=2024, current_year=2025, group_by="grade")

    groups = {r.group for r in results}
    assert groups == {"9", "10"}


def test_compare_years_skips_question_with_insufficient_sample_size():
    schema = make_schema()
    df = pd.DataFrame({
        "survey_year": [2024, 2025],
        "q_vaping_30day": [1, 2],
    })

    results = compare_years(df, schema, previous_year=2024, current_year=2025)

    assert results == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_comparison.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cfy_pipeline.comparison'`

- [ ] **Step 3: Implement the comparison module**

Create `cfy_pipeline/comparison.py`:
```python
from __future__ import annotations

import dataclasses

import pandas as pd
from scipy import stats

from cfy_pipeline.schema import SurveySchema

SIGNIFICANCE_THRESHOLD = 0.05


@dataclasses.dataclass
class ComparisonResult:
    question_name: str
    group: str
    previous_year: int
    current_year: int
    previous_mean: float
    current_year_mean: float
    p_value: float
    significant: bool


def compare_years(
    df_all: pd.DataFrame,
    schema: SurveySchema,
    previous_year: int,
    current_year: int,
    group_by: str | None = None,
) -> list[ComparisonResult]:
    results: list[ComparisonResult] = []

    groups = ["All"]
    if group_by is not None:
        groups = sorted(df_all[group_by].dropna().unique().tolist())

    for question in schema.questions:
        for group in groups:
            if group_by is None or group == "All":
                subset = df_all
            else:
                subset = df_all[df_all[group_by] == group]

            previous_values = subset.loc[subset["survey_year"] == previous_year, question.name].dropna()
            current_values = subset.loc[subset["survey_year"] == current_year, question.name].dropna()

            if len(previous_values) < 2 or len(current_values) < 2:
                continue

            _t_stat, p_value = stats.ttest_ind(current_values, previous_values, equal_var=False)

            results.append(
                ComparisonResult(
                    question_name=question.name,
                    group=group,
                    previous_year=previous_year,
                    current_year=current_year,
                    previous_mean=float(previous_values.mean()),
                    current_year_mean=float(current_values.mean()),
                    p_value=float(p_value),
                    significant=bool(p_value < SIGNIFICANCE_THRESHOLD),
                )
            )

    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_comparison.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add cfy_pipeline/comparison.py tests/test_comparison.py
git commit -m "feat: add year-over-year comparison with significance testing"
```

---

### Task 5: Multi-Year Trend Detection

**Files:**
- Create: `cfy_pipeline/trends.py`
- Test: `tests/test_trends.py`

**Interfaces:**
- Consumes: `SurveySchema` from `cfy_pipeline.schema` (Task 1); expects a DataFrame with a `survey_year` column as produced by `cfy_pipeline.storage.load_all_years` (Task 3).
- Produces: `TrendResult(question_name: str, group: str, years: list[int], yearly_means: list[float], slope: float, p_value: float, is_sustained: bool)` with property `direction -> str` (`"increasing"`, `"decreasing"`, or `"none"`); `detect_multi_year_trends(df_all: pd.DataFrame, schema: SurveySchema, group_by: str | None = None) -> list[TrendResult]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_trends.py`:
```python
import pandas as pd

from cfy_pipeline.schema import QuestionField, SurveySchema
from cfy_pipeline.trends import detect_multi_year_trends


def make_schema() -> SurveySchema:
    return SurveySchema(
        demographics=(),
        questions=(
            QuestionField(name="q_vaping_30day", label="Vaping", category="substance_use", valid_range=(1, 5)),
        ),
    )


def test_detect_multi_year_trends_flags_sustained_increase():
    schema = make_schema()
    df = pd.DataFrame({
        "survey_year": [2022] * 10 + [2023] * 10 + [2024] * 10 + [2025] * 10,
        "q_vaping_30day": [1] * 10 + [2] * 10 + [3] * 10 + [4] * 10,
    })

    results = detect_multi_year_trends(df, schema)

    assert len(results) == 1
    result = results[0]
    assert result.is_sustained is True
    assert result.direction == "increasing"
    assert result.years == [2022, 2023, 2024, 2025]


def test_detect_multi_year_trends_skips_when_fewer_than_min_years():
    schema = make_schema()
    df = pd.DataFrame({
        "survey_year": [2024] * 10 + [2025] * 10,
        "q_vaping_30day": [1] * 10 + [4] * 10,
    })

    results = detect_multi_year_trends(df, schema)

    assert results == []


def test_detect_multi_year_trends_reports_none_direction_when_not_sustained():
    schema = make_schema()
    df = pd.DataFrame({
        "survey_year": [2022] * 10 + [2023] * 10 + [2024] * 10,
        "q_vaping_30day": (
            [2, 3, 2, 3, 2, 3, 2, 3, 2, 3]
            + [3, 2, 3, 2, 3, 2, 3, 2, 3, 2]
            + [2, 3, 2, 3, 2, 3, 2, 3, 2, 3]
        ),
    })

    results = detect_multi_year_trends(df, schema)

    assert len(results) == 1
    assert results[0].is_sustained is False
    assert results[0].direction == "none"


def test_detect_multi_year_trends_by_group_splits_per_subgroup():
    schema = make_schema()
    df = pd.DataFrame({
        "survey_year": [2022] * 20 + [2023] * 20 + [2024] * 20,
        "grade": (["9"] * 10 + ["10"] * 10) * 3,
        "q_vaping_30day": [1] * 10 + [1] * 10 + [2] * 10 + [2] * 10 + [3] * 10 + [3] * 10,
    })

    results = detect_multi_year_trends(df, schema, group_by="grade")

    groups = {r.group for r in results}
    assert groups == {"9", "10"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_trends.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cfy_pipeline.trends'`

- [ ] **Step 3: Implement the trends module**

Create `cfy_pipeline/trends.py`:
```python
from __future__ import annotations

import dataclasses

import pandas as pd
from scipy import stats

from cfy_pipeline.schema import SurveySchema

MIN_YEARS_FOR_TREND = 3
TREND_SIGNIFICANCE_THRESHOLD = 0.05


@dataclasses.dataclass
class TrendResult:
    question_name: str
    group: str
    years: list[int]
    yearly_means: list[float]
    slope: float
    p_value: float
    is_sustained: bool

    @property
    def direction(self) -> str:
        if not self.is_sustained:
            return "none"
        return "increasing" if self.slope > 0 else "decreasing"


def detect_multi_year_trends(
    df_all: pd.DataFrame,
    schema: SurveySchema,
    group_by: str | None = None,
) -> list[TrendResult]:
    results: list[TrendResult] = []

    groups = ["All"]
    if group_by is not None:
        groups = sorted(df_all[group_by].dropna().unique().tolist())

    for question in schema.questions:
        for group in groups:
            if group_by is None or group == "All":
                subset = df_all
            else:
                subset = df_all[df_all[group_by] == group]

            yearly = (
                subset.dropna(subset=[question.name])
                .groupby("survey_year")[question.name]
                .mean()
                .sort_index()
            )

            if len(yearly) < MIN_YEARS_FOR_TREND:
                continue

            years = yearly.index.tolist()
            means = yearly.values.tolist()
            slope, _intercept, _r, p_value, _stderr = stats.linregress(years, means)

            results.append(
                TrendResult(
                    question_name=question.name,
                    group=group,
                    years=years,
                    yearly_means=means,
                    slope=float(slope),
                    p_value=float(p_value),
                    is_sustained=bool(p_value < TREND_SIGNIFICANCE_THRESHOLD),
                )
            )

    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_trends.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add cfy_pipeline/trends.py tests/test_trends.py
git commit -m "feat: add multi-year trend detection"
```

---

### Task 6: Chart Building (Plotly Figures)

**Files:**
- Create: `cfy_pipeline/charts.py`
- Test: `tests/test_charts.py`

**Interfaces:**
- Consumes: `ComparisonResult` from `cfy_pipeline.comparison` (Task 4); `TrendResult` from `cfy_pipeline.trends` (Task 5).
- Produces: `build_comparison_figure(results: list[ComparisonResult], question_label: str) -> go.Figure`; `build_trend_figure(result: TrendResult, question_label: str) -> go.Figure`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_charts.py`:
```python
from cfy_pipeline.charts import build_comparison_figure, build_trend_figure
from cfy_pipeline.comparison import ComparisonResult
from cfy_pipeline.trends import TrendResult


def test_build_comparison_figure_marks_significant_bar_red():
    results = [
        ComparisonResult(
            question_name="q_vaping_30day",
            group="9",
            previous_year=2024,
            current_year=2025,
            previous_mean=1.0,
            current_year_mean=4.0,
            p_value=0.001,
            significant=True,
        )
    ]

    fig = build_comparison_figure(results, "Vaping frequency")

    assert len(fig.data) == 2
    assert fig.data[1].marker.color[0] == "crimson"


def test_build_trend_figure_colors_sustained_trend_red():
    result = TrendResult(
        question_name="q_vaping_30day",
        group="All",
        years=[2022, 2023, 2024],
        yearly_means=[1.0, 2.0, 3.0],
        slope=1.0,
        p_value=0.01,
        is_sustained=True,
    )

    fig = build_trend_figure(result, "Vaping frequency")

    assert fig.data[0].line.color == "crimson"
    assert "increasing" in fig.layout.title.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_charts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cfy_pipeline.charts'`

- [ ] **Step 3: Implement the charts module**

Create `cfy_pipeline/charts.py`:
```python
from __future__ import annotations

import plotly.graph_objects as go

from cfy_pipeline.comparison import ComparisonResult
from cfy_pipeline.trends import TrendResult


def build_comparison_figure(results: list[ComparisonResult], question_label: str) -> go.Figure:
    groups = [r.group for r in results]
    previous_means = [r.previous_mean for r in results]
    current_means = [r.current_year_mean for r in results]
    colors = ["crimson" if r.significant else "steelblue" for r in results]

    fig = go.Figure()
    fig.add_bar(name="Previous Year", x=groups, y=previous_means, marker_color="lightgray")
    fig.add_bar(name="Current Year", x=groups, y=current_means, marker_color=colors)
    fig.update_layout(barmode="group", title=question_label, xaxis_title="Group", yaxis_title="Mean Score")
    return fig


def build_trend_figure(result: TrendResult, question_label: str) -> go.Figure:
    fig = go.Figure()
    line_color = "crimson" if result.is_sustained else "steelblue"
    fig.add_scatter(x=result.years, y=result.yearly_means, mode="lines+markers", line_color=line_color)
    fig.update_layout(
        title=f"{question_label} — {result.group} ({result.direction})",
        xaxis_title="Year",
        yaxis_title="Mean Score",
    )
    return fig
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_charts.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add cfy_pipeline/charts.py tests/test_charts.py
git commit -m "feat: add Plotly chart builders for comparisons and trends"
```

---

### Task 7: Upload Processing Pipeline

**Files:**
- Create: `cfy_pipeline/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `clean_dataframe` from `cfy_pipeline.cleaning` (Task 2); `save_year_data` from `cfy_pipeline.storage` (Task 3); `SurveySchema` from `cfy_pipeline.schema` (Task 1).
- Produces: `process_uploaded_file(csv_source, year: int, schema: SurveySchema, db_path: str | Path) -> DataQualityReport`. `csv_source` accepts anything `pandas.read_csv` accepts (file path or file-like object, e.g. a Streamlit `UploadedFile`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_pipeline.py`:
```python
import pandas as pd

from cfy_pipeline.pipeline import process_uploaded_file
from cfy_pipeline.schema import QuestionField, SurveySchema
from cfy_pipeline.storage import load_year


def make_schema() -> SurveySchema:
    return SurveySchema(
        demographics=(),
        questions=(
            QuestionField(name="q_vaping_30day", label="Vaping", category="substance_use", valid_range=(1, 5)),
        ),
    )


def test_process_uploaded_file_cleans_and_persists_data(tmp_path):
    schema = make_schema()
    csv_path = tmp_path / "survey_2025.csv"
    pd.DataFrame({"q_vaping_30day": [1, 7, 3]}).to_csv(csv_path, index=False)
    db_path = tmp_path / "survey.db"

    report = process_uploaded_file(csv_path, 2025, schema, db_path)

    assert report.normalized_columns["q_vaping_30day"] == 1
    stored = load_year(db_path, 2025)
    assert stored["q_vaping_30day"].tolist() == [1, 5, 3]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cfy_pipeline.pipeline'`

- [ ] **Step 3: Implement the pipeline module**

Create `cfy_pipeline/pipeline.py`:
```python
from __future__ import annotations

from pathlib import Path

import pandas as pd

from cfy_pipeline.cleaning import DataQualityReport, clean_dataframe
from cfy_pipeline.schema import SurveySchema
from cfy_pipeline.storage import save_year_data


def process_uploaded_file(
    csv_source,
    year: int,
    schema: SurveySchema,
    db_path: str | Path,
) -> DataQualityReport:
    df = pd.read_csv(csv_source)
    cleaned, report = clean_dataframe(df, schema)
    save_year_data(cleaned, year, db_path)
    return report
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pipeline.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add cfy_pipeline/pipeline.py tests/test_pipeline.py
git commit -m "feat: add upload processing pipeline tying cleaning to storage"
```

---

### Task 8: Streamlit Dashboard

**Files:**
- Create: `cfy_pipeline/dashboard.py`

**Interfaces:**
- Consumes: `load_schema` from `cfy_pipeline.schema` (Task 1); `process_uploaded_file` from `cfy_pipeline.pipeline` (Task 7); `load_all_years` from `cfy_pipeline.storage` (Task 3); `compare_years` from `cfy_pipeline.comparison` (Task 4); `detect_multi_year_trends` from `cfy_pipeline.trends` (Task 5); `build_comparison_figure`, `build_trend_figure` from `cfy_pipeline.charts` (Task 6).
- Produces: a runnable Streamlit entrypoint (`cfy_pipeline/dashboard.py`), no importable functions consumed by later tasks (this is the last task).

This task has no unit-testable business logic of its own — all underlying logic was already tested in Tasks 1–7. Verification here is a manual run of the live app, matching the PRD's requirement that non-technical staff can complete the full workflow (upload → review → explore charts) themselves.

- [ ] **Step 1: Implement the dashboard**

Create `cfy_pipeline/dashboard.py`:
```python
from __future__ import annotations

from pathlib import Path

import streamlit as st

from cfy_pipeline.charts import build_comparison_figure, build_trend_figure
from cfy_pipeline.comparison import compare_years
from cfy_pipeline.pipeline import process_uploaded_file
from cfy_pipeline.schema import SurveySchema, load_schema
from cfy_pipeline.storage import load_all_years
from cfy_pipeline.trends import detect_multi_year_trends

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "config" / "survey_schema.yaml"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "survey.db"


def render_upload_section(schema: SurveySchema) -> None:
    st.header("Upload New Survey Year")
    year = st.number_input("Survey Year", min_value=2000, max_value=2100, step=1, value=2025)
    uploaded_file = st.file_uploader("Choose the survey CSV file", type="csv")

    if uploaded_file is not None and st.button("Process Upload"):
        report = process_uploaded_file(uploaded_file, int(year), schema, DB_PATH)
        if report.dropped_columns:
            st.warning(f"Dropped missing columns: {', '.join(report.dropped_columns)}")
        if report.normalized_columns:
            st.info(f"Normalized out-of-range values: {report.normalized_columns}")
        st.success(f"Processed {report.row_count} responses for {int(year)}.")


def render_dashboard_section(schema: SurveySchema) -> None:
    st.header("Trends & Comparisons")
    df_all = load_all_years(DB_PATH)
    if df_all.empty:
        st.info("No data yet — upload a survey file above to get started.")
        return

    years = sorted(df_all["survey_year"].unique().tolist())
    group_by_options = ["None"] + schema.demographic_names()
    group_by_choice = st.selectbox("Break down by", group_by_options)
    group_by = None if group_by_choice == "None" else group_by_choice

    if len(years) >= 2:
        st.subheader("Year-over-Year Comparison")
        comparisons = compare_years(
            df_all, schema, previous_year=years[-2], current_year=years[-1], group_by=group_by
        )
        for question in schema.questions:
            question_results = [r for r in comparisons if r.question_name == question.name]
            if question_results:
                st.plotly_chart(build_comparison_figure(question_results, question.label))

    st.subheader("Multi-Year Trends")
    trends = detect_multi_year_trends(df_all, schema, group_by=group_by)
    for trend in trends:
        question_label = schema.question_by_name(trend.question_name).label
        st.plotly_chart(build_trend_figure(trend, question_label))


def main() -> None:
    st.set_page_config(page_title="Adams County Youth Survey Dashboard", layout="wide")
    st.title("Adams County Youth Survey Dashboard")
    schema = load_schema(SCHEMA_PATH)
    render_upload_section(schema)
    render_dashboard_section(schema)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the app locally**

Run: `streamlit run cfy_pipeline/dashboard.py`
Expected: browser opens to `localhost:8501` showing "Adams County Youth Survey Dashboard" with an upload section and a "No data yet" message.

- [ ] **Step 3: Manually verify the full workflow with synthetic data**

Create a throwaway test CSV (outside the repo, e.g. `/tmp/survey_2023.csv`) with columns `grade,gender,race_ethnicity,q_vaping_30day,q_alcohol_30day,q_mh_sad_hopeless,q_mh_anxiety,q_connectedness_school` and a few rows of plausible values (1–5 for question columns). Repeat for at least 3 distinct years with a visible upward or downward drift in one question column so trend detection has something to flag.

Upload each year's file through the running dashboard, one at a time, using the "Process Upload" button. After the 3rd year is uploaded, confirm:
- The data-quality messages (warning/info/success) reflect what you'd expect from your synthetic files.
- The "Year-over-Year Comparison" section shows a chart per question with bars colored crimson where you engineered a big jump.
- The "Multi-Year Trends" section shows a trend line for the question you drifted across all 3 years, colored crimson if `is_sustained`.
- Switching the "Break down by" selector to `grade` (or another demographic) re-renders charts split by subgroup.

Expected: all four checks pass visually in the browser.

- [ ] **Step 4: Commit**

```bash
git add cfy_pipeline/dashboard.py
git commit -m "feat: add Streamlit dashboard wiring upload, comparison, and trend charts"
```

---

## Self-Review Notes

- **Spec coverage:** PRD §6.1 (ingestion) → Task 7 + Task 8 upload section. §6.2 (cleaning/validation) → Task 2. §6.3 (historical storage) → Task 3. §6.4 (trend detection, both methods, no school-level breakdown) → Task 4 + Task 5. §6.5 (dashboard, subgroup drill-down) → Task 6 + Task 8. §9 (config-driven schema) → Task 1. Phase 2 items (auto-narrative, export tooling) are intentionally not planned here, per PRD §7.
- **Placeholder scan:** no TBD/TODO markers; every step has complete, runnable code or an exact command.
- **Type consistency:** `SurveySchema`, `DemographicField`, `QuestionField` (Task 1) are consumed identically in Tasks 2, 4, 5, 8. `ComparisonResult` (Task 4) and `TrendResult` (Task 5) field names match their usage in Task 6's chart builders and Task 8's dashboard. `DataQualityReport` (Task 2) fields match Task 7's and Task 8's usage (`dropped_columns`, `normalized_columns`, `row_count`).
