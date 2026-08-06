from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings, load_settings, require_llm_credentials
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import PaperRecord, fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex

DEMO_QUESTIONS = [
    "What is this corpus about?",
    "Which paper discusses retrieval augmented generation the most directly?",
]


def load_or_fetch_records(settings: Settings) -> tuple[list[PaperRecord], str]:
    """Uu tien raw snapshot da co; chi goi API khi thieu hoac REFRESH_SOURCE=1."""
    raw_path = settings.paths.raw_records_json
    if settings.refresh_source or not raw_path.exists():
        records = fetch_source_records(settings)
        return records, "fetched"
    return load_raw_records(raw_path), "loaded_from_snapshot"


def load_or_build_test_set(settings: Settings, df: pd.DataFrame) -> tuple[list[dict[str, Any]], str]:
    """Test set phai co dinh giua 3 trang thai; chi build lai khi REFRESH_TEST_SET=1."""
    test_set_path = settings.paths.eval_testset
    if settings.refresh_test_set or not test_set_path.exists():
        return build_test_set(df, test_set_path), "built"
    return read_json(test_set_path), "loaded_existing"


def sanitize_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Doi NaN o cot text thanh chuoi rong.

    Ly do: `pd.read_csv` doc o trong thanh NaN (float). NaN di vao hai cho:
    - `json.dumps` sinh token `NaN` -> file KHONG hop le theo RFC 8259,
      `jq` va `JSON.parse` deu tu choi.
    - Chroma metadata -> `qa.py::_extract_answer` goi `first_sentence(NaN)`
      va crash TypeError.
    Chuan hoa mot lan tai tang dieu phoi, khong sua logic cua owner khac.
    """
    cleaned = df.copy()
    for column in cleaned.columns:
        if cleaned[column].dtype == object:
            cleaned[column] = cleaned[column].fillna("")
    return cleaned


def save_clean_dataframe(df: pd.DataFrame, csv_path, json_path) -> None:
    df = sanitize_missing(df)
    write_csv(df, csv_path)
    write_json(json_path, df.to_dict(orient="records"))


def run_agent_demo(settings: Settings, index: LocalEmbeddingIndex) -> None:
    """Demo agent tren vai cau hoi. Loi o day khong duoc lam hong pipeline."""
    try:
        agent = build_agent(settings=settings, index=index)
        demo = [
            {"question": question, "answer": run_agent_question(agent, question)}
            for question in DEMO_QUESTIONS
        ]
    except Exception as exc:  # pragma: no cover - phu thuoc LLM provider
        demo = [{"error": f"Agent demo skipped: {exc}"}]
    write_json(settings.paths.demo_answers, demo)


def main() -> None:
    settings = load_settings()
    require_llm_credentials(settings)
    paths = settings.paths

    records, source_mode = load_or_fetch_records(settings)
    if not records:
        raise RuntimeError("Raw records rong. Kiem tra lai buoc ingestion truoc khi chay tiep.")
    print(f"[1/7] raw records: {len(records)} ({source_mode})")

    df = build_clean_dataframe(records, now_utc())
    save_clean_dataframe(df, paths.clean_csv, paths.clean_json)
    print(f"[2/7] clean rows: {len(df)} -> {paths.clean_csv}")

    index = LocalEmbeddingIndex.build(sanitize_missing(df), settings=settings, embeddings_output_path=paths.embeddings_json)
    print(f"[3/7] indexed collection: {index.collection_name}")

    test_set, test_set_mode = load_or_build_test_set(settings, df)
    print(f"[4/7] test set: {len(test_set)} samples ({test_set_mode})")

    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )
    print(
        f"[5/7] hit_rate={bundle.summary['retrieval_hit_rate']:.3f} "
        f"token_f1={bundle.summary['mean_token_f1']:.3f} "
        f"judge_acc={bundle.summary['judge_accuracy']:.3f}"
    )

    quality = run_data_quality_checks(df, settings=settings, report_name="baseline")
    freshness = build_freshness_report(df, settings=settings, report_path=paths.freshness_report)
    print(f"[6/7] quality + freshness -> {paths.quality_dir}")

    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "source_mode": source_mode,
        "max_results": settings.max_results,
        "raw_records": len(records),
        "clean_rows": int(len(df)),
        "embedding_model": settings.embedding_model,
        "collection_name": index.collection_name,
        "top_k": settings.top_k,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.model_name,
        "test_set_size": len(test_set),
        "test_set_mode": test_set_mode,
    }
    generate_phase1_report(
        report_path=paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality,
        freshness=freshness,
    )
    print(f"[7/7] report -> {paths.baseline_report}")

    run_agent_demo(settings, index)
