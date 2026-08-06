"""CLI hoi-dap tren corpus da index.

Vi du:
    uv run python script/ask.py "who authored the RAG survey?"
    uv run python script/ask.py --state corrupted "when was it published?"
    uv run python script/ask.py            # che do interactive
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

from core.config import Settings, load_settings
from core.utils import read_json
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question

STATES = ("baseline", "corrupted", "repaired")


def embeddings_path_for(settings: Settings, state: str) -> Path:
    return {
        "baseline": settings.paths.embeddings_json,
        "corrupted": settings.paths.corrupted_embeddings_json,
        "repaired": settings.paths.repaired_embeddings_json,
    }[state]


def load_index(settings: Settings, state: str) -> LocalEmbeddingIndex:
    path = embeddings_path_for(settings, state)
    if not path.exists():
        hint = "script/run_phase1.py" if state == "baseline" else "script/run_corruption_flow.py"
        raise SystemExit(f"Chua co index cho state '{state}' ({path}). Chay {hint} truoc.")
    return LocalEmbeddingIndex.load(settings, embeddings_path=path)


def load_test_set(settings: Settings) -> list[dict[str, Any]]:
    path = settings.paths.eval_testset
    return read_json(path) if path.exists() else []


def match_test_sample(test_set: list[dict[str, Any]], question: str) -> dict[str, Any] | None:
    needle = question.strip().lower()
    for item in test_set:
        if item["question"].strip().lower() == needle:
            return item
    return None


def safe(text: str) -> str:
    """Console Windows co the la cp1252 - tranh crash vi ky tu unicode trong title."""
    encoding = sys.stdout.encoding or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding)


def ask(settings: Settings, index: LocalEmbeddingIndex, test_set, question: str, top_k: int) -> None:
    result = answer_question(question, settings=settings, index=index, top_k=top_k)
    scores = {item.paper_id: item.score for item in index.search(question, top_k=top_k)}

    print(f"\nAnswer: {safe(result.answer)}\n")
    print(f"Retrieved (top_k={top_k}, collection={index.collection_name})")
    for rank, (paper_id, title) in enumerate(zip(result.retrieved_doc_ids, result.retrieved_titles), start=1):
        score = scores.get(paper_id)
        score_text = f"{score:.4f}" if score is not None else "  n/a "
        print(f"  {rank}. {paper_id:<34} {score_text}  {safe(title[:60])}")

    sample = match_test_sample(test_set, question)
    if sample:
        hit = any(doc_id in sample["ground_truth_doc_ids"] for doc_id in result.retrieved_doc_ids)
        print(f"\nGround truth doc: {', '.join(sample['ground_truth_doc_ids'])}  -> {'HIT' if hit else 'MISS'}")
        print(f"Ground truth    : {safe(sample['ground_truth'])}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Hoi-dap tren corpus paper da index.")
    parser.add_argument("question", nargs="*", help="Cau hoi. Bo trong de vao che do interactive.")
    parser.add_argument("--state", choices=STATES, default="baseline", help="Trang thai du lieu can hoi.")
    parser.add_argument("--top-k", type=int, default=None, help="So tai lieu lay ve (mac dinh lay tu config).")
    args = parser.parse_args()

    settings = load_settings()
    top_k = args.top_k or settings.top_k
    index = load_index(settings, args.state)
    test_set = load_test_set(settings)
    print(f"State: {args.state} | collection: {index.collection_name} | documents: {len(index.documents)}")

    if args.question:
        ask(settings, index, test_set, " ".join(args.question), top_k)
        return

    print("Go cau hoi, Enter de hoi. Ctrl+C hoac de trong de thoat.")
    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not question:
            return
        ask(settings, index, test_set, question, top_k)


if __name__ == "__main__":
    main()
