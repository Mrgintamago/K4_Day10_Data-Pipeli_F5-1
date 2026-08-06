from __future__ import annotations

from datetime import datetime
import re

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


REQUIRED_COLUMNS: tuple[str, ...] = (
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


# Sentinel age used when a record has no parseable publication date. Keeping
# it explicit (instead of NaN) makes freshness reports deterministic and
# keeps `sort by age_days` from blowing up.
_MISSING_DATE_AGE_DAYS = 10_000


def _clean_text(value: str | None) -> str:
    """Normalize whitespace and strip any leftover markup."""
    if not isinstance(value, str):
        return ""
    text = normalize_whitespace(value)
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(text)


def _parse_published(value: str, run_date: datetime) -> tuple[str, int]:
    """Return (iso_date, age_days) for a Crossref-style published string."""
    if not isinstance(value, str) or not value.strip():
        return "", _MISSING_DATE_AGE_DAYS

    candidate = value.strip()[:10]
    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m"):
            try:
                parsed = datetime.strptime(value.strip(), fmt)
                break
            except ValueError:
                continue

    if parsed is None:
        return "", _MISSING_DATE_AGE_DAYS

    # Strip tzinfo so naive parsed dates can be subtracted from an aware
    # ``run_date`` (or vice versa) without raising TypeError.
    if parsed.tzinfo is not None and run_date.tzinfo is None:
        parsed = parsed.replace(tzinfo=None)
    elif parsed.tzinfo is None and run_date.tzinfo is not None:
        parsed = parsed.replace(tzinfo=run_date.tzinfo)

    try:
        age_days = max((run_date - parsed).days, 0)
    except TypeError:
        return "", _MISSING_DATE_AGE_DAYS

    return parsed.date().isoformat(), age_days


def _build_text_for_embedding(row: pd.Series) -> str:
    """Compose the chunk fed to the embedding model.

    Order is deliberate: title is the strongest signal, then summary, then
    authors and categories as supporting context. Empty fields are dropped so
    the embedding never sees blank fragments.
    """
    parts: list[str] = []
    title = _clean_text(row.get("title", ""))
    if title:
        parts.append(f"Title: {title}")
    summary = _clean_text(row.get("summary", ""))
    if summary:
        parts.append(f"Summary: {summary}")
    authors = _clean_text(row.get("authors_joined", ""))
    if authors:
        parts.append(f"Authors: {authors}")
    categories = _clean_text(row.get("categories_joined", ""))
    if categories:
        parts.append(f"Categories: {categories}")
    return "\n".join(parts).strip()


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Convert raw ``PaperRecord`` objects into a clean, embed-ready dataframe.

    """
    if not isinstance(records, list) or not records:
        raise ValueError("build_clean_dataframe requires at least one PaperRecord.")

    rows: list[dict[str, object]] = []
    for record in records:
        if not isinstance(record, PaperRecord):
            continue

        paper_id = _clean_text(record.paper_id).lower()
        if not paper_id:
            continue  # need a stable id for dedupe and evaluation

        title = _clean_text(record.title)
        if not title:
            continue  # title is the primary embedding signal

        summary = _clean_text(record.summary)
        authors = [name for name in (_clean_text(a) for a in record.authors) if name]
        categories = [cat for cat in (_clean_text(c) for c in record.categories) if cat]

        published, age_days = _parse_published(record.published, run_date)

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "published": published,
                "age_days": age_days,
                "authors_joined": ", ".join(authors),
                "categories_joined": ", ".join(categories),
                "text_for_embedding": "",  # filled after helper columns exist
                "abs_url": _clean_text(record.abs_url),
                "pdf_url": _clean_text(record.pdf_url),
            }
        )

    if not rows:
        raise ValueError("No usable rows after sanitization; check raw records.")

    df = pd.DataFrame(rows, columns=list(REQUIRED_COLUMNS))

    # Deterministic dedupe by stable id; keep first occurrence by raw order.
    df = df.drop_duplicates(subset=["paper_id"], keep="first").reset_index(drop=True)

    # Build text_for_embedding once helper columns exist.
    df["text_for_embedding"] = df.apply(_build_text_for_embedding, axis=1)

    # Rows whose text collapsed to nothing cannot be embedded — drop them and
    # surface the count via the missing summary report rather than silently.
    empty_text_mask = df["text_for_embedding"].str.len() == 0
    if empty_text_mask.any():
        df = df[~empty_text_mask].reset_index(drop=True)

    # Freshest first, then alphabetical for determinism.
    df = df.sort_values(by=["age_days", "paper_id"], ascending=[True, True]).reset_index(drop=True)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise RuntimeError(f"Clean dataframe missing required columns: {missing}")

    return df


__all__ = ["REQUIRED_COLUMNS", "build_clean_dataframe"]