from __future__ import annotations

from datetime import datetime, timedelta
import json
import random
from typing import Any

import pandas as pd

from core.utils import write_json


def _records_for_json(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Serialize a dataframe to JSON-safe records.

    Replaces NaN with ``None`` so the output is valid JSON. Without this,
    ``pandas.DataFrame.to_dict`` can emit the literal ``NaN`` (the JS-style
    sentinel) on object-dtype columns that survived CSV round-trip —
    technically invalid JSON and rejected by strict parsers.
    """
    return json.loads(df.to_json(orient="records"))


# Defaults sized so the corruption is loud enough that retrieval/metric signals
# flip on the 24-record baseline, but not so destructive that the dataset is
# empty. Each value is also logged so the report can point to it later.
DEFAULT_DROP_LATEST_FRACTION = 0.20          # drop ~5 of 24 freshest rows
DEFAULT_BLANK_SUMMARY_FRACTION = 0.15        # blank ~3-4 summaries
DEFAULT_NOISE_SUMMARY_FRACTION = 0.20        # noise ~5 summaries
DEFAULT_NOISE_TOKEN = "corruptnoise"
DEFAULT_TITLE_TRUNCATE_CHARS = 40           # cut titles to a short prefix
DEFAULT_STALE_YEARS_BACK = 5                 # push date 5 years into the past
DEFAULT_DUPLICATE_FRACTION = 0.15            # duplicate ~3-4 rows


def _log_event(
    log: list[dict[str, Any]],
    corruption_type: str,
    affected_ids: list[str],
    parameter: Any,
    before: Any,
    after: Any,
) -> None:
    log.append(
        {
            "corruption_type": corruption_type,
            "affected_paper_ids": affected_ids,
            "parameter": parameter,
            "before": before,
            "after": after,
        }
    )


def _corrupt_drop_latest(
    df: pd.DataFrame, log: list[dict[str, Any]], fraction: float, _rng: random.Random
) -> pd.DataFrame:
    """Drop the freshest rows so the remaining corpus skews older."""
    if df.empty:
        _log_event(log, "drop_latest", [], {"fraction": fraction}, 0, 0)
        return df

    df = df.sort_values(by=["age_days", "paper_id"], ascending=[True, True]).reset_index(drop=True)
    n_drop = max(1, int(round(len(df) * fraction)))
    n_drop = min(n_drop, len(df) - 1)  # keep at least one row so eval still runs
    dropped_ids = df.iloc[:n_drop]["paper_id"].tolist()
    before_count = len(df)
    df = df.iloc[n_drop:].reset_index(drop=True)
    _log_event(
        log,
        "drop_latest",
        dropped_ids,
        {"fraction": fraction, "n_drop": n_drop, "sort_by": "age_days"},
        before_count,
        len(df),
    )
    return df


def _corrupt_blank_summary(
    df: pd.DataFrame, log: list[dict[str, Any]], fraction: float, rng: random.Random
) -> pd.DataFrame:
    """Replace summary with an empty string on a fraction of rows.

    pandas ``to_csv`` cannot distinguish empty strings from missing values —
    both round-trip as NaN. To keep the corruption visible in the CSV artifact
    we store a single whitespace character, and downstream consumers should
    treat any whitespace-only summary as blank. The log records the true
    before/after empty string so audit reads stay honest.
    """
    if df.empty:
        _log_event(log, "blank_summary", [], {"fraction": fraction}, 0, 0)
        return df

    n_target = max(1, int(round(len(df) * fraction)))
    indices = rng.sample(range(len(df)), k=min(n_target, len(df)))
    affected_ids = df.loc[indices, "paper_id"].tolist()
    before = [df.at[i, "summary"] for i in indices]
    for i in indices:
        df.at[i, "summary"] = " "  # see docstring — survives CSV round-trip
    _log_event(
        log,
        "blank_summary",
        affected_ids,
        {"fraction": fraction, "n": len(indices)},
        before,
        ["" for _ in indices],
    )
    return df


def _corrupt_noise_summary(
    df: pd.DataFrame,
    log: list[dict[str, Any]],
    fraction: float,
    rng: random.Random,
    token: str,
) -> pd.DataFrame:
    """Inject a noisy token into summary text on a fraction of rows."""
    if df.empty:
        _log_event(log, "noise_summary", [], {"fraction": fraction}, 0, 0)
        return df

    n_target = max(1, int(round(len(df) * fraction)))
    indices = rng.sample(range(len(df)), k=min(n_target, len(df)))
    affected_ids = df.loc[indices, "paper_id"].tolist()
    before = [df.at[i, "summary"] for i in indices]
    for i in indices:
        df.at[i, "summary"] = f"{df.at[i, 'summary']} {token} {rng.randint(1000, 9999)}"
    _log_event(
        log,
        "noise_summary",
        affected_ids,
        {"fraction": fraction, "n": len(indices), "token": token},
        before,
        [df.at[i, "summary"] for i in indices],
    )
    return df


def _corrupt_truncate_title(
    df: pd.DataFrame, log: list[dict[str, Any]], chars: int, _rng: random.Random
) -> pd.DataFrame:
    """Truncate every title to ``chars`` characters so the embedding signal weakens."""
    if df.empty:
        _log_event(log, "truncate_title", [], {"chars": chars}, 0, 0)
        return df

    affected_ids = df["paper_id"].tolist()
    before = df["title"].tolist()
    df["title"] = df["title"].astype(str).str.slice(0, chars).str.strip()
    # Rebuild text_for_embedding lazily; keep it consistent with title/summary changes.
    _log_event(
        log,
        "truncate_title",
        affected_ids,
        {"chars": chars, "n": len(df)},
        before,
        df["title"].tolist(),
    )
    return df


def _corrupt_stale_published_date(
    df: pd.DataFrame, log: list[dict[str, Any]], years_back: int, _rng: random.Random
) -> pd.DataFrame:
    """Shift published date backward by N years so freshness signals fail."""
    if df.empty:
        _log_event(log, "stale_published_date", [], {"years_back": years_back}, 0, 0)
        return df

    affected_ids: list[str] = []
    before_dates: list[str] = []
    after_dates: list[str] = []

    for i in df.index:
        current = df.at[i, "published"]
        if not current or not isinstance(current, str):
            continue
        try:
            parsed = datetime.fromisoformat(current)
        except ValueError:
            continue
        new_date = (parsed - timedelta(days=365 * years_back)).date().isoformat()
        df.at[i, "published"] = new_date
        # Recompute age_days against the implicit run_date used elsewhere; we
        # add years_back * 365 to keep the magnitude consistent with the
        # corruption. A more accurate recompute would need the run_date; the
        # downstream quality/freshness checks re-evaluate against a snapshot
        # date, so this shift is what triggers the freshness signal change.
        df.at[i, "age_days"] = int(df.at[i, "age_days"]) + 365 * years_back
        affected_ids.append(df.at[i, "paper_id"])
        before_dates.append(current)
        after_dates.append(new_date)

    _log_event(
        log,
        "stale_published_date",
        affected_ids,
        {"years_back": years_back, "n": len(affected_ids)},
        before_dates,
        after_dates,
    )
    return df


def _corrupt_duplicate_rows(
    df: pd.DataFrame, log: list[dict[str, Any]], fraction: float, rng: random.Random
) -> pd.DataFrame:
    """Append duplicate copies of a fraction of rows to inflate the corpus with junk."""
    if df.empty:
        _log_event(log, "duplicate_rows", [], {"fraction": fraction}, 0, 0)
        return df

    n_target = max(1, int(round(len(df) * fraction)))
    indices = rng.sample(range(len(df)), k=min(n_target, len(df)))
    duplicate_rows = df.iloc[indices].copy()
    affected_ids = duplicate_rows["paper_id"].tolist()
    before_count = len(df)
    df = pd.concat([df, duplicate_rows], ignore_index=True)
    _log_event(
        log,
        "duplicate_rows",
        affected_ids,
        {"fraction": fraction, "n_duplicated": len(indices)},
        before_count,
        len(df),
    )
    return df


def _rebuild_text_for_embedding(df: pd.DataFrame) -> None:
    """Recompute the embedding text from current title/summary/authors/categories.

    Corruption steps (noise, blank, truncate) edit the source columns; we
    keep ``text_for_embedding`` consistent so the downstream embedding/index
    sees the corrupted signal rather than a stale copy.
    """
    parts: list[str] = []
    for _, row in df.iterrows():
        chunks: list[str] = []
        title = str(row.get("title", "") or "").strip()
        summary = str(row.get("summary", "") or "").strip()
        authors = str(row.get("authors_joined", "") or "").strip()
        categories = str(row.get("categories_joined", "") or "").strip()
        if title:
            chunks.append(f"Title: {title}")
        if summary:
            chunks.append(f"Summary: {summary}")
        if authors:
            chunks.append(f"Authors: {authors}")
        if categories:
            chunks.append(f"Categories: {categories}")
        parts.append("\n".join(chunks).strip())

    df["text_for_embedding"] = parts


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Apply six controlled corruptions to a clean baseline dataframe.

    The flow follows PLAN §5 CP4:
        1. drop_latest        - drop the freshest ~20% of rows
        2. blank_summary      - blank summary on ~15% of rows
        3. noise_summary      - inject noise tokens into ~20% summaries
        4. truncate_title     - cut every title to 40 chars
        5. stale_published_date - shift every parseable date 5 years back
        6. duplicate_rows     - duplicate ~15% of rows

    ``text_for_embedding`` is rebuilt at the end so downstream Chroma /
    retrieval sees the corrupted surface form, not the original. A
    corruption log is written to ``output_log_path`` describing each step
    (affected paper ids, parameter, before/after values).

    The input dataframe is never mutated; the caller (TV4) already passes a
    deep copy so baseline stays intact on disk.
    """
    if df is None or df.empty:
        raise ValueError("corrupt_clean_dataframe requires a non-empty clean dataframe.")

    # Deterministic per-call RNG so reruns reproduce the same corruption.
    rng = random.Random(20260806)
    log: list[dict[str, Any]] = []
    before_snapshot = {
        "rows": int(len(df)),
        "paper_ids": df["paper_id"].tolist() if "paper_id" in df.columns else [],
    }

    df = df.copy(deep=True)
    df = _corrupt_drop_latest(df, log, DEFAULT_DROP_LATEST_FRACTION, rng)
    df = _corrupt_blank_summary(df, log, DEFAULT_BLANK_SUMMARY_FRACTION, rng)
    df = _corrupt_noise_summary(df, log, DEFAULT_NOISE_SUMMARY_FRACTION, rng, DEFAULT_NOISE_TOKEN)
    df = _corrupt_truncate_title(df, log, DEFAULT_TITLE_TRUNCATE_CHARS, rng)
    df = _corrupt_stale_published_date(df, log, DEFAULT_STALE_YEARS_BACK, rng)
    df = _corrupt_duplicate_rows(df, log, DEFAULT_DUPLICATE_FRACTION, rng)
    _rebuild_text_for_embedding(df)

    after_snapshot = {
        "rows": int(len(df)),
        "paper_ids": df["paper_id"].tolist() if "paper_id" in df.columns else [],
    }

    log_payload = {
        "schema_version": 1,
        "baseline_rows": before_snapshot["rows"],
        "corrupted_rows": after_snapshot["rows"],
        "baseline_paper_ids": before_snapshot["paper_ids"],
        "corrupted_paper_ids": after_snapshot["paper_ids"],
        "events": log,
        "corrupted_records": _records_for_json(df),
    }

    write_json(output_log_path, log_payload)
    return df


__all__ = ["corrupt_clean_dataframe"]