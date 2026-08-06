from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


REQUIRED_COLUMNS = (
    "paper_id",
    "title",
    "summary",
    "published",
    "age_days",
    "authors_joined",
    "categories_joined",
    "text_for_embedding",
    "abs_url",
    "pdf_url",
)


def _missing_count(df: pd.DataFrame, column: str) -> int:
    if column not in df.columns:
        return len(df)
    return int(df[column].isna().sum())


def _blank_count(df: pd.DataFrame, column: str) -> int:
    if column not in df.columns:
        return len(df)
    values = df[column].fillna("").astype(str).str.strip()
    return int(values.eq("").sum())


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run deterministic checks on one dataframe state and persist a JSON artifact."""
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    row_count = int(len(df))
    paper_id_missing = _missing_count(df, "paper_id")
    paper_id_unique = bool(
        "paper_id" in df.columns and df["paper_id"].dropna().is_unique
    )
    title_blank = _blank_count(df, "title")
    summary_blank = _blank_count(df, "summary")
    summary_chars = (
        df["summary"].fillna("").astype(str).str.len()
        if "summary" in df.columns
        else pd.Series(dtype="int64")
    )
    age_missing = _missing_count(df, "age_days")
    age_numeric = pd.to_numeric(df["age_days"], errors="coerce") if "age_days" in df.columns else pd.Series(dtype="float64")
    stale_rows = int((age_numeric > settings.freshness_threshold_days).sum())
    invalid_age_rows = int(age_numeric.isna().sum()) if "age_days" in df.columns else row_count

    checks = {
        "required_columns": {
            "pass": not missing_columns,
            "missing": missing_columns,
        },
        "row_count": {"pass": row_count > 0, "value": row_count},
        "paper_id_not_null": {"pass": paper_id_missing == 0, "null_rows": paper_id_missing},
        "paper_id_unique": {"pass": paper_id_unique, "duplicate_rows": max(row_count - int(df["paper_id"].nunique()) if "paper_id" in df.columns else row_count, 0)},
        "title_not_blank": {"pass": title_blank == 0, "blank_rows": title_blank},
        "summary_length": {
            "pass": summary_blank == 0,
            "blank_rows": summary_blank,
            "min_chars": int(summary_chars.min()) if not summary_chars.empty else 0,
            "max_chars": int(summary_chars.max()) if not summary_chars.empty else 0,
        },
        "freshness": {
            "pass": age_missing == 0 and invalid_age_rows == 0 and stale_rows == 0,
            "stale_rows": stale_rows,
            "invalid_or_missing_age_rows": invalid_age_rows,
            "threshold_days": settings.freshness_threshold_days,
        },
    }
    overall_pass = all(bool(item["pass"]) for item in checks.values())
    payload = {
        "report_name": report_name,
        "total_rows": row_count,
        "overall_pass": overall_pass,
        "checks": checks,
        "summary": {
            "failed_checks": [name for name, result in checks.items() if not result["pass"]],
            "categories_are_optional": True,
        },
    }
    write_json(settings.paths.quality_dir / f"quality_{report_name}.json", payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarize publication-date freshness and persist it as JSON."""
    published = pd.to_datetime(df["published"], errors="coerce") if "published" in df.columns else pd.Series(dtype="datetime64[ns]")
    age_days = pd.to_numeric(df["age_days"], errors="coerce") if "age_days" in df.columns else pd.Series(dtype="float64")
    stale_rows = int((age_days > settings.freshness_threshold_days).sum())
    invalid_date_rows = int(published.isna().sum())
    total_rows = int(len(df))

    def iso_date(value: Any) -> str | None:
        return value.date().isoformat() if pd.notna(value) else None

    payload = {
        "latest_published": iso_date(published.max()) if not published.empty else None,
        "oldest_published": iso_date(published.min()) if not published.empty else None,
        "stale_rows": stale_rows,
        "invalid_date_rows": invalid_date_rows,
        "total_rows": total_rows,
        "threshold_days": settings.freshness_threshold_days,
        "is_fresh": total_rows > 0 and stale_rows == 0 and invalid_date_rows == 0,
    }
    write_json(Path(report_path), payload)
    return payload
