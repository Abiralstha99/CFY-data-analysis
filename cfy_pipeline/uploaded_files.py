"""File-library interface for annual survey CSVs."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from io import BytesIO
from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st

from cfy_pipeline import DataQualityReport, SurveySchema, process_uploaded_file
from cfy_pipeline.cleaning import clean_dataframe
from cfy_pipeline.storage import (
    SurveyFile,
    delete_year_data,
    list_survey_files,
    load_original_file,
    load_year,
)

LAST_UPLOAD_STATE_KEY = "last_upload"


def _field_label(name: str, schema: SurveySchema) -> str:
    for question in schema.questions:
        if question.name == name:
            return question.label
    return name.replace("_", " ").title()


def _file_size(size: int | None) -> str:
    if size is None:
        return "Not recorded"
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def _upload_date(timestamp: str | None) -> str:
    if timestamp is None:
        return "Not recorded"
    return datetime.fromisoformat(timestamp).astimezone(timezone.utc).strftime("%b %d, %Y")


def _read_and_validate_csv(uploaded_file, schema: SurveySchema) -> pd.DataFrame | None:
    try:
        uploaded_file.seek(0)
        raw_data = pd.read_csv(uploaded_file)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
        st.error("This file could not be read as a CSV. Check the file and try again.")
        return None
    finally:
        uploaded_file.seek(0)

    if raw_data.empty:
        st.error("This CSV has no survey responses. Add at least one row and try again.")
        return None

    question_columns = [name for name in schema.question_names() if name in raw_data.columns]
    if not question_columns:
        st.error("No survey question columns were found. Check that this is the correct survey CSV.")
        return None

    invalid_columns = []
    for name in question_columns:
        values = raw_data[name]
        if (values.notna() & pd.to_numeric(values, errors="coerce").isna()).any():
            invalid_columns.append(_field_label(name, schema))
    if invalid_columns:
        st.error(
            "These question columns contain text where a number is expected: "
            f"{', '.join(invalid_columns)}. Correct those values and try again."
        )
        return None
    return raw_data


def _upload_csv_contents(schema: SurveySchema, db_path: Path, replace_year: int | None = None) -> None:
    """Review an upload before calling the existing cleaning pipeline."""
    st.caption("Select the survey year, review the CSV, then save it.")
    nonce = st.session_state.get("file_upload_nonce", 0)
    stored_years = {item.year: item for item in list_survey_files(db_path)}
    if replace_year is not None:
        st.subheader(f"Replace existing dataset · {replace_year}")
        year = replace_year
    else:
        current_year = datetime.now().year
        year_options = [
            "Select a year",
            *(year for year in range(current_year, 1999, -1) if year not in stored_years),
            *(year for year in range(current_year + 1, 2101) if year not in stored_years),
        ]
        selected_year = st.selectbox(
            "Survey year",
            year_options,
            key=f"file_year_new_{nonce}",
        )
        year = selected_year if isinstance(selected_year, int) else None
        if stored_years:
            years_on_file = ", ".join(str(year) for year in sorted(stored_years, reverse=True))
            st.caption(f"Existing years: {years_on_file}. Use that file's Actions → Replace to change one.")
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type="csv",
        help="Drag and drop a CSV here or use Browse files. Use one row per response.",
        key=f"file_upload_{replace_year or 'new'}_{nonce}",
    )

    raw_data = _read_and_validate_csv(uploaded_file, schema) if uploaded_file is not None else None
    report = None
    if raw_data is not None:
        _, report = clean_dataframe(raw_data, schema)
        st.write(f"**{len(raw_data):,} responses** · {_file_size(uploaded_file.size)} · {uploaded_file.name}")
        missing = [name for name in schema.expected_columns() if name not in raw_data.columns]
        extra = [name for name in raw_data.columns if name not in schema.expected_columns()]
        if missing:
            labels = ", ".join(_field_label(name, schema) for name in missing)
            st.warning(f"Missing survey fields will be left out of the results: {labels}.")
        if extra:
            st.info(f"Extra columns will be ignored in analysis: {', '.join(extra)}.")
        st.caption(f"Columns ({len(raw_data.columns)}): {', '.join(raw_data.columns)}")
        st.dataframe(raw_data.head(5), hide_index=True, width="stretch")
        st.caption("Showing the first five rows. The original CSV is saved with the processed survey data.")
        if report.normalized_columns:
            st.warning("The saved responses will include these value adjustments:")
            for field, count in report.normalized_columns.items():
                examples = ", ".join(
                    f"{before} → {after}" for before, after in report.normalized_examples.get(field, [])
                )
                st.write(f"**{_field_label(field, schema)}:** {count:,} adjusted. Examples: {examples}")

    existing = stored_years.get(year)
    confirmed = True
    if existing is not None:
        st.warning(
            f"**Replacing {year} will remove its {existing.response_count:,} saved responses "
            "and original CSV.** The new file will become the only dataset for that year."
        )
        confirmed = st.checkbox(f"I understand and want to replace the {year} dataset")
    reviewed = True
    if report is not None and (report.has_issues() or bool(extra)):
        reviewed = st.checkbox("I reviewed the missing, extra, and adjusted fields above")

    cancel_col, save_col = st.columns(2)
    with cancel_col:
        if st.button("Cancel", width="stretch"):
            st.session_state["file_upload_nonce"] = nonce + 1
            st.rerun()
    with save_col:
        label = "Replace dataset" if existing is not None else "Save CSV"
        save_clicked = st.button(
            label,
            type="primary",
            disabled=raw_data is None or year is None or not confirmed or not reviewed,
            width="stretch",
        )

    if save_clicked:
        progress = st.progress(25, text="Validating CSV…")
        try:
            uploaded_file.seek(0)
            progress.progress(60, text="Processing and saving responses…")
            report = process_uploaded_file(uploaded_file, year, schema, db_path)
        except (OSError, ValueError, TypeError, KeyError, sqlite3.Error) as exc:
            progress.empty()
            st.error(f"The CSV could not be saved: {exc}")
        else:
            progress.progress(100, text="Upload complete")
            st.session_state[LAST_UPLOAD_STATE_KEY] = {"year": year, "report": report}
            st.session_state["upload_flash"] = {
                "kind": "upload", "year": year, "message": f"{uploaded_file.name} was saved for {year}."
            }
            st.session_state["file_upload_nonce"] = nonce + 1
            st.session_state["file_search_nonce"] = st.session_state.get("file_search_nonce", 0) + 1
            st.rerun()


@st.dialog("Upload CSV", width="large")
def upload_csv_dialog(schema: SurveySchema, db_path: Path) -> None:
    _upload_csv_contents(schema, db_path)


@st.dialog("Replace existing dataset", width="large")
def replace_csv_dialog(schema: SurveySchema, db_path: Path, year: int) -> None:
    _upload_csv_contents(schema, db_path, replace_year=year)


@st.dialog("Preview CSV", width="large")
def preview_csv_dialog(file: SurveyFile, db_path: Path, schema: SurveySchema) -> None:
    st.subheader(file.file_name)
    st.caption(f"{file.year} survey · {file.response_count:,} responses")
    original = load_original_file(db_path, file.year)
    if original is None:
        st.info("The original CSV was not stored for this older dataset. Showing saved survey responses.")
        preview = load_year(db_path, file.year).drop(columns=["survey_year"])
    else:
        try:
            preview = pd.read_csv(BytesIO(original[1]))
        except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
            st.error("The original CSV could not be previewed. Try downloading it instead.")
            return
    st.caption(f"{len(preview):,} rows · {len(preview.columns)} columns")
    friendly_columns = {
        name: f"{_field_label(name, schema)} ({name})" for name in preview.columns
    }
    st.dataframe(preview.rename(columns=friendly_columns), hide_index=True, width="stretch", height=420)


@st.dialog("Delete dataset", width="small")
def delete_file_dialog(file: SurveyFile, db_path: Path) -> None:
    st.warning(
        f"Deleting **{file.file_name}** will permanently remove all "
        f"{file.response_count:,} survey responses for **{file.year}**."
    )
    confirmed = st.checkbox(f"I understand and want to delete the {file.year} dataset")
    cancel_col, delete_col = st.columns(2)
    with cancel_col:
        if st.button("Cancel", key=f"cancel_delete_{file.year}", width="stretch"):
            st.rerun()
    with delete_col:
        if st.button(
            "Delete dataset",
            type="primary",
            disabled=not confirmed,
            key=f"confirm_delete_{file.year}",
            width="stretch",
        ):
            try:
                with st.spinner("Deleting dataset…"):
                    delete_year_data(db_path, file.year)
            except sqlite3.Error as exc:
                st.error(f"The dataset could not be deleted: {exc}")
            else:
                last_upload = st.session_state.get(LAST_UPLOAD_STATE_KEY)
                if last_upload and last_upload["year"] == file.year:
                    st.session_state.pop(LAST_UPLOAD_STATE_KEY, None)
                st.session_state["upload_flash"] = {
                    "kind": "delete", "message": f"{file.year} survey data was deleted."
                }
                st.rerun()


def _render_file_row(file: SurveyFile, db_path: Path, schema: SurveySchema) -> None:
    with st.container(key=f"file_row_{file.year}"):
        details_col, actions_col = st.columns([9, 2.2], vertical_alignment="center")
        with details_col:
            name = escape(file.file_name)
            year = escape(str(file.year))
            upload_date = escape(_upload_date(file.uploaded_at))
            size = escape(_file_size(file.file_size))
            st.markdown(
                '<div class="file-row-grid">'
                f'<div class="file-cell file-name"><span class="file-mobile-label">File Name</span>'
                f'<strong>{name}</strong><small>{file.response_count:,} responses</small></div>'
                f'<div class="file-cell"><span class="file-mobile-label">Survey Year</span>{year}</div>'
                f'<div class="file-cell"><span class="file-mobile-label">Upload Date</span>{upload_date}</div>'
                f'<div class="file-cell"><span class="file-mobile-label">File Size</span>{size}</div>'
                '<div class="file-cell"><span class="file-mobile-label">Status</span>'
                '<span class="file-status">Ready</span></div></div>',
                unsafe_allow_html=True,
            )
        with actions_col:
            with st.popover("Actions", icon=":material/more_vert:", help=f"Actions for {file.file_name}"):
                if st.button("Preview", key=f"preview_{file.year}", width="stretch"):
                    preview_csv_dialog(file, db_path, schema)
                if st.button("Replace", key=f"replace_{file.year}", width="stretch"):
                    replace_csv_dialog(schema, db_path, file.year)
                original = load_original_file(db_path, file.year)
                if original is None:
                    saved_data = load_year(db_path, file.year).drop(columns=["survey_year"])
                    st.download_button(
                        "Download saved data",
                        data=saved_data.to_csv(index=False).encode("utf-8"),
                        file_name=f"survey_{file.year}_saved.csv",
                        mime="text/csv",
                        key=f"download_{file.year}",
                        width="stretch",
                    )
                    st.caption("Original CSV unavailable for this older year.")
                else:
                    st.download_button(
                        "Download original CSV",
                        data=original[1],
                        file_name=original[0],
                        mime="text/csv",
                        key=f"download_{file.year}",
                        width="stretch",
                    )
                if st.button("Delete", key=f"delete_{file.year}", width="stretch"):
                    delete_file_dialog(file, db_path)


def _render_last_upload(schema: SurveySchema, db_path: Path) -> None:
    last_upload = st.session_state.get(LAST_UPLOAD_STATE_KEY)
    if last_upload is None:
        return
    year = last_upload["year"]
    report: DataQualityReport = last_upload["report"]
    with st.expander(f"Upload quality report · {year}", expanded=report.has_issues()):
        if report.dropped_columns:
            labels = ", ".join(_field_label(name, schema) for name in report.dropped_columns)
            st.warning(f"These expected fields were missing and left out of the results: {labels}.")
        if report.normalized_columns:
            st.write("Responses adjusted to match the survey's allowed values:")
            st.dataframe(
                pd.DataFrame(
                    {
                        "Survey field": [_field_label(name, schema) for name in report.normalized_columns],
                        "Responses adjusted": list(report.normalized_columns.values()),
                    }
                ),
                hide_index=True,
                width="stretch",
            )
        if not report.has_issues():
            st.write("All expected fields were present and values were within their allowed ranges.")
        saved = load_year(db_path, year)
        if not saved.empty:
            st.caption("First 10 saved responses")
            st.dataframe(saved.drop(columns=["survey_year"]).head(10), hide_index=True, width="stretch")


def render_uploaded_files_tab(schema: SurveySchema, db_path: Path) -> None:
    """Render the searchable file library and its upload entry points."""
    heading_col, upload_col = st.columns([5, 1.4], vertical_alignment="center")
    with heading_col:
        st.header("Uploaded Files")
        st.caption("View and manage your annual survey datasets.")
    with upload_col:
        if st.button("Upload CSV", type="primary", width="stretch", key="upload_csv_top"):
            upload_csv_dialog(schema, db_path)

    files = list_survey_files(db_path)
    flash = st.session_state.pop("upload_flash", None)
    if isinstance(flash, str):
        st.success(flash)
    elif flash and flash["kind"] == "delete":
        st.success(flash["message"])
    if not files:
        st.info("No survey files have been uploaded yet. Add a CSV to start exploring results.")
        if st.button("Upload CSV", key="upload_csv_empty"):
            upload_csv_dialog(schema, db_path)
        return

    search_nonce = st.session_state.get("file_search_nonce", 0)
    with st.form(f"file_search_{search_nonce}"):
        search_col, year_col, button_col = st.columns([3, 1.2, 1], vertical_alignment="bottom")
        with search_col:
            query = st.text_input("Search files", placeholder="File name or survey year", key=f"file_query_{search_nonce}")
        with year_col:
            years = [item.year for item in files]
            selected_year = st.selectbox("Survey year", ["All years", *years], key=f"file_filter_year_{search_nonce}")
        with button_col:
            st.form_submit_button("Search", width="stretch")

    normalized_query = query.strip().casefold()
    visible = [
        item for item in files
        if (selected_year == "All years" or item.year == selected_year)
        and (not normalized_query or normalized_query in item.file_name.casefold() or normalized_query in str(item.year))
    ]
    st.caption(f"{len(visible)} of {len(files)} dataset{'s' if len(files) != 1 else ''}")
    st.caption("Older datasets may show “Not recorded” for upload date and file size because their original CSV was not stored.")
    if not visible:
        st.info("No files match this search. Try a different file name or year.")
        return

    st.markdown(
        '<div class="file-table-header">'
        '<span>File Name</span><span>Survey Year</span><span>Upload Date</span>'
        '<span>File Size</span><span>Status</span><span>Actions</span></div>',
        unsafe_allow_html=True,
    )
    for file in visible:
        if isinstance(flash, dict) and flash["kind"] == "upload" and flash["year"] == file.year:
            st.success(flash["message"])
        _render_file_row(file, db_path, schema)
        if st.session_state.get(LAST_UPLOAD_STATE_KEY, {}).get("year") == file.year:
            _render_last_upload(schema, db_path)
