from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json


def _safe(value: Any) -> str:
    return normalize_whitespace(value) if isinstance(value, str) else ""


def _has(value: str) -> bool:
    return bool(value and value.strip())


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a deterministic evaluation set from a clean dataframe.

    Every ``ground_truth_doc_ids`` is verified to exist in the source
    dataframe so the evaluator never dereferences a missing document.
    """
    if df is None or df.empty:
        raise ValueError("build_test_set requires a non-empty clean dataframe.")
    if "paper_id" not in df.columns:
        raise ValueError("Clean dataframe must contain a 'paper_id' column.")

    available_ids = {str(pid).strip() for pid in df["paper_id"].tolist()}
    if not available_ids:
        raise ValueError("Clean dataframe has no usable paper_id values.")

    questions: list[dict[str, Any]] = []
    next_id = 1

    def _new_id() -> str:
        nonlocal next_id
        value = f"q{next_id:03d}"
        next_id += 1
        return value

    for _, row in df.iterrows():
        paper_id = _safe(row.get("paper_id"))
        if not paper_id or paper_id not in available_ids:
            continue

        title = _safe(row.get("title"))
        summary = _safe(row.get("summary"))
        authors = _safe(row.get("authors_joined"))
        published = _safe(row.get("published"))

        if _has(summary):
            short_summary = first_sentence(summary)
            if short_summary and short_summary != title:
                questions.append(
                    {
                        "id": _new_id(),
                        "question_type": "summary",
                        "question": f"What is the summary of the paper titled \"{title}\"?",
                        "ground_truth": short_summary,
                        "ground_truth_doc_ids": [paper_id],
                    }
                )

        if _has(authors):
            questions.append(
                {
                    "id": _new_id(),
                    "question_type": "authors",
                    "question": f"Who are the authors of the paper titled \"{title}\"?",
                    "ground_truth": authors,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

        if _has(published):
            questions.append(
                {
                    "id": _new_id(),
                    "question_type": "date",
                    "question": f"When was the paper titled \"{title}\" published?",
                    "ground_truth": published,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

    # Fallback retrieval probe so the set always exercises semantic search.
    has_text = df["text_for_embedding"].astype(str).str.len() > 0
    if has_text.any():
        anchor = df[has_text].iloc[0]
        anchor_id = _safe(anchor["paper_id"])
        anchor_title = _safe(anchor["title"])
        if anchor_id and anchor_title:
            questions.append(
                {
                    "id": _new_id(),
                    "question_type": "retrieval",
                    "question": f"Find a paper related to: \"{anchor_title}\".",
                    "ground_truth": anchor_title,
                    "ground_truth_doc_ids": [anchor_id],
                }
            )

    if not questions:
        raise ValueError("Could not build any evaluation questions from the clean dataframe.")

    # Determinism + integrity: every doc id referenced must resolve to a row.
    missing = [
        doc_id
        for item in questions
        for doc_id in item["ground_truth_doc_ids"]
        if doc_id not in available_ids
    ]
    if missing:
        raise RuntimeError(
            f"Test set references missing paper_ids: {sorted(set(missing))[:5]}..."
        )

    write_json(output_path, questions)
    return questions


__all__ = ["build_test_set"]