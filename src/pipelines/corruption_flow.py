from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings, require_llm_credentials
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import EvaluationBundle, evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from pipelines.phase1 import sanitize_missing
from retrieval.index import LocalEmbeddingIndex


def require_baseline_artifacts(settings: Settings) -> None:
    """Corruption flow chi co nghia khi baseline da chay xong."""
    required = {
        "clean data": settings.paths.clean_csv,
        "raw records": settings.paths.raw_records_json,
        "test set": settings.paths.eval_testset,
        "baseline metrics": settings.paths.baseline_metrics,
    }
    missing = [name for name, path in required.items() if not path.exists()]
    if missing:
        raise RuntimeError(
            "Thieu artifact baseline: " + ", ".join(missing) + ". Chay script/run_phase1.py truoc."
        )


def save_state_dataframe(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    df = sanitize_missing(df)
    write_csv(df, csv_path)
    write_json(json_path, df.to_dict(orient="records"))


def freshness_path_for(settings: Settings, state: str) -> Path:
    """Freshness rieng cho tung trang thai, van lay goc tu Paths.quality_dir."""
    return settings.paths.quality_dir / f"freshness_report_{state}.json"


def evaluate_state(
    settings: Settings,
    df: pd.DataFrame,
    state: str,
    embeddings_path: Path,
    metrics_path: Path,
    answers_path: Path,
) -> tuple[EvaluationBundle, dict[str, Any], dict[str, Any]]:
    """Index -> evaluate -> quality/freshness cho mot trang thai du lieu."""
    index = LocalEmbeddingIndex.build(sanitize_missing(df), settings=settings, embeddings_output_path=embeddings_path)
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=metrics_path,
        answers_output_path=answers_path,
    )
    quality = run_data_quality_checks(df, settings=settings, report_name=state)
    freshness = build_freshness_report(df, settings=settings, report_path=freshness_path_for(settings, state))
    print(
        f"  [{state}] collection={index.collection_name} "
        f"hit_rate={bundle.summary['retrieval_hit_rate']:.3f} "
        f"token_f1={bundle.summary['mean_token_f1']:.3f} "
        f"judge_acc={bundle.summary['judge_accuracy']:.3f}"
    )
    return bundle, quality, freshness


def main() -> None:
    settings = load_settings()
    require_llm_credentials(settings)
    require_baseline_artifacts(settings)
    paths = settings.paths

    baseline_metrics = read_json(paths.baseline_metrics)
    baseline_df = sanitize_missing(pd.read_csv(paths.clean_csv))
    print(f"[1/5] baseline: {len(baseline_df)} rows, hit_rate={baseline_metrics['retrieval_hit_rate']:.3f}")

    corrupted_df = corrupt_clean_dataframe(baseline_df.copy(deep=True), paths.corruption_log)
    save_state_dataframe(corrupted_df, paths.corrupted_clean_csv, paths.corrupted_clean_json)
    print(f"[2/5] corrupted: {len(corrupted_df)} rows, log -> {paths.corruption_log}")

    _, corrupted_quality, corrupted_freshness = evaluate_state(
        settings=settings,
        df=corrupted_df,
        state="corrupted",
        embeddings_path=paths.corrupted_embeddings_json,
        metrics_path=paths.corrupted_metrics,
        answers_path=paths.corrupted_answers,
    )

    # Repair = chay lai cleaning tu raw records, tuyet doi khong copy clean baseline.
    repaired_records = load_raw_records(paths.raw_records_json)
    repaired_df = build_clean_dataframe(repaired_records, now_utc())
    save_state_dataframe(repaired_df, paths.repaired_clean_csv, paths.repaired_clean_json)
    print(f"[3/5] repaired: {len(repaired_df)} rows (rebuilt tu {paths.raw_records_json.name})")

    _, repaired_quality, repaired_freshness = evaluate_state(
        settings=settings,
        df=repaired_df,
        state="repaired",
        embeddings_path=paths.repaired_embeddings_json,
        metrics_path=paths.repaired_metrics,
        answers_path=paths.repaired_answers,
    )
    print("[4/5] da danh gia du 3 trang thai tren cung test set")

    generate_corruption_report(
        report_path=paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=read_json(paths.corrupted_metrics),
        repaired_metrics=read_json(paths.repaired_metrics),
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"[5/5] comparison report -> {paths.comparison_report}")
