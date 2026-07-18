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
