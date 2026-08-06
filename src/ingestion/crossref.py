from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from html import unescape
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


CROSSREF_API_URL = "https://api.crossref.org/works"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref works response into stable raw paper records."""
    if not isinstance(payload, dict):
        raise ValueError("Crossref payload must be a JSON object.")

    message = payload.get("message")
    items = message.get("items") if isinstance(message, dict) else None
    if not isinstance(items, list):
        raise ValueError("Crossref payload must contain message.items as a list.")

    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue

        paper_id = _normalize_doi(item.get("DOI"))
        title = _first_text(item.get("title"))
        if not paper_id or not title or paper_id in seen_ids:
            continue

        authors = []
        author_items = item.get("author")
        for author in (author_items if isinstance(author_items, list) else []):
            if not isinstance(author, dict):
                continue
            name_parts = [
                part
                for part in (author.get("given"), author.get("family"))
                if isinstance(part, str) and part.strip()
            ]
            name = normalize_whitespace(" ".join(name_parts)) or _clean_text(author.get("name"))
            if name:
                authors.append(name)

        subject_items = item.get("subject")
        categories = [
            normalize_whitespace(subject)
            for subject in (subject_items if isinstance(subject_items, list) else [])
            if isinstance(subject, str) and subject.strip()
        ]
        primary_category = categories[0] if categories else _clean_text(item.get("type"))
        abs_url = _clean_text(item.get("URL")) or f"https://doi.org/{paper_id}"
        pdf_url = _find_pdf_url(item.get("link"))

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=_clean_markup(item.get("abstract")),
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=_extract_date(item),
                updated=_extract_updated(item),
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=_first_text(item.get("container-title")) or _clean_text(item.get("publisher")),
            )
        )
        seen_ids.add(paper_id)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref records and persist both source and parsed snapshots."""
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "day10-data-observability-lab/0.1",
    }

    response: requests.Response | None = None
    max_attempts = 4
    for attempt in range(max_attempts):
        try:
            response = requests.get(
                CROSSREF_API_URL,
                params=params,
                headers=headers,
                timeout=30,
            )
        except (requests.ConnectionError, requests.Timeout):
            if attempt == max_attempts - 1:
                raise
            time.sleep(2**attempt)
            continue

        if response.status_code not in RETRYABLE_STATUS_CODES:
            break
        if attempt == max_attempts - 1:
            response.raise_for_status()

        retry_after = response.headers.get("Retry-After", "")
        try:
            delay = max(float(retry_after), float(2**attempt))
        except ValueError:
            delay = float(2**attempt)
        time.sleep(min(delay, 60.0))

    if response is None:
        raise RuntimeError("Crossref request completed without a response.")

    response.raise_for_status()
    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError as exc:
        raise ValueError("Crossref returned an invalid JSON response.") from exc

    # Preserve source evidence even if parsing later detects an incompatible payload.
    write_json(settings.paths.raw_api_response, payload)
    records = parse_crossref_payload(payload)
    if not records:
        raise ValueError("Crossref response contained no valid paper records.")

    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load and validate a parsed raw-record snapshot."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Raw records file must contain a JSON list: {path}")

    records: list[PaperRecord] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Raw record at index {index} must be a JSON object.")
        try:
            record = PaperRecord(**item)
        except TypeError as exc:
            raise ValueError(f"Invalid raw record schema at index {index}: {exc}") from exc

        if not isinstance(record.paper_id, str) or not isinstance(record.title, str):
            raise ValueError(f"Raw record at index {index} has a non-string paper_id or title.")
        if not record.paper_id.strip() or not record.title.strip():
            raise ValueError(f"Raw record at index {index} has an empty paper_id or title.")
        if not isinstance(record.authors, list) or not isinstance(record.categories, list):
            raise ValueError(f"Raw record at index {index} has invalid authors or categories.")
        records.append(record)

    return records


def _clean_text(value: Any) -> str:
    return normalize_whitespace(value) if isinstance(value, str) else ""


def _clean_markup(value: Any) -> str:
    text = _clean_text(value)
    text = normalize_whitespace(unescape(re.sub(r"<[^>]+>", " ", text)))
    return re.sub(r"\s+([,.;:!?])", r"\1", text)


def _first_text(value: Any) -> str:
    if isinstance(value, list):
        return next((_clean_text(item) for item in value if _clean_text(item)), "")
    return _clean_text(value)


def _normalize_doi(value: Any) -> str:
    doi = _clean_text(value).lower()
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", doi).strip()


def _date_parts(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    parts_container = value.get("date-parts")
    if not isinstance(parts_container, list) or not parts_container:
        return ""
    parts = parts_container[0]
    if not isinstance(parts, list) or not parts:
        return ""
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return date(year, month, day).isoformat()
    except (TypeError, ValueError):
        return ""


def _extract_date(item: dict) -> str:
    for key in ("published", "published-online", "published-print", "issued"):
        published = _date_parts(item.get(key))
        if published:
            return published
    return ""


def _extract_updated(item: dict) -> str:
    for key in ("indexed", "deposited", "created"):
        value = item.get(key)
        if not isinstance(value, dict):
            continue
        timestamp = _clean_text(value.get("date-time"))
        if timestamp:
            return timestamp
        fallback = _date_parts(value)
        if fallback:
            return fallback
    return ""


def _find_pdf_url(links: Any) -> str:
    if not isinstance(links, list):
        return ""
    for link in links:
        if not isinstance(link, dict):
            continue
        content_type = _clean_text(link.get("content-type")).lower()
        url = _clean_text(link.get("URL"))
        if url and (content_type == "application/pdf" or url.lower().endswith(".pdf")):
            return url
    return ""
