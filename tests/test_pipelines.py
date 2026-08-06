from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path

import pandas as pd
import pytest

from core.config import load_settings
from core.utils import write_json
from ingestion.crossref import PaperRecord
from pipelines import corruption_flow, phase1
from script import ask


def test_load_or_fetch_records_uses_existing_snapshot(tmp_path, monkeypatch) -> None:
    settings = load_settings(tmp_path)
    snapshot_path = tmp_path / "snapshots" / "records.json"
    settings = replace(
        settings,
        refresh_source=False,
        paths=replace(settings.paths, raw_records_json=snapshot_path),
    )
    expected = PaperRecord(
        paper_id="10.1000/test",
        title="A test paper",
        summary="A local snapshot.",
        authors=["Ada Lovelace"],
        categories=["Computer Science"],
        primary_category="Computer Science",
        published="2026-08-06",
        updated="2026-08-06T00:00:00Z",
        abs_url="https://doi.org/10.1000/test",
        pdf_url="",
        comment="Test Journal",
    )
    write_json(snapshot_path, [asdict(expected)])

    def fail_if_fetched(_settings):
        pytest.fail("fetch_source_records must not be called for an existing snapshot")

    monkeypatch.setattr(phase1, "fetch_source_records", fail_if_fetched)

    records, mode = phase1.load_or_fetch_records(settings)

    assert records == [expected]
    assert mode == "loaded_from_snapshot"


def test_load_or_build_test_set_uses_existing_file(tmp_path, monkeypatch) -> None:
    settings = load_settings(tmp_path)
    test_set_path = tmp_path / "eval" / "test_set.json"
    settings = replace(
        settings,
        refresh_test_set=False,
        paths=replace(settings.paths, eval_testset=test_set_path),
    )
    expected = [
        {
            "id": "q001",
            "question": "What is this paper about?",
            "ground_truth": "Testing.",
            "ground_truth_doc_ids": ["10.1000/test"],
        }
    ]
    write_json(test_set_path, expected)

    def fail_if_built(_df, _path):
        pytest.fail("build_test_set must not be called for an existing test set")

    monkeypatch.setattr(phase1, "build_test_set", fail_if_built)

    test_set, mode = phase1.load_or_build_test_set(settings, pd.DataFrame())

    assert test_set == expected
    assert mode == "loaded_existing"


def test_save_clean_dataframe_round_trip(tmp_path) -> None:
    source = pd.DataFrame(
        [
            {"paper_id": "10.1000/a", "title": "Paper A", "score": 1.5},
            {"paper_id": "10.1000/b", "title": "Paper B", "score": 2.0},
        ]
    )
    csv_path = tmp_path / "clean" / "papers.csv"
    json_path = tmp_path / "clean" / "papers.json"

    phase1.save_clean_dataframe(source, csv_path, json_path)

    pd.testing.assert_frame_equal(pd.read_csv(csv_path), source)
    assert pd.read_json(json_path).to_dict(orient="records") == source.to_dict(orient="records")


@pytest.mark.parametrize(
    ("missing_attr", "missing_name"),
    [
        ("clean_csv", "clean data"),
        ("raw_records_json", "raw records"),
        ("eval_testset", "test set"),
        ("baseline_metrics", "baseline metrics"),
    ],
)
def test_require_baseline_artifacts_names_missing_artifact(
    tmp_path, missing_attr: str, missing_name: str
) -> None:
    settings = load_settings(tmp_path)
    required_attrs = ("clean_csv", "raw_records_json", "eval_testset", "baseline_metrics")
    fake_paths = {
        attr: tmp_path / "artifacts" / f"{attr}.json"
        for attr in required_attrs
    }
    settings = replace(settings, paths=replace(settings.paths, **fake_paths))

    for attr, path in fake_paths.items():
        if attr != missing_attr:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

    with pytest.raises(RuntimeError, match=missing_name):
        corruption_flow.require_baseline_artifacts(settings)


def test_freshness_path_for_all_states(tmp_path) -> None:
    settings = load_settings(tmp_path)
    quality_dir = tmp_path / "quality-reports"
    settings = replace(settings, paths=replace(settings.paths, quality_dir=quality_dir))

    actual = {
        state: corruption_flow.freshness_path_for(settings, state)
        for state in ("baseline", "corrupted", "repaired")
    }

    assert actual == {
        "baseline": quality_dir / "freshness_report_baseline.json",
        "corrupted": quality_dir / "freshness_report_corrupted.json",
        "repaired": quality_dir / "freshness_report_repaired.json",
    }
    assert len(set(actual.values())) == 3


def test_embeddings_path_for_all_states(tmp_path) -> None:
    settings = load_settings(tmp_path)
    paths = replace(
        settings.paths,
        embeddings_json=tmp_path / "embeddings" / "baseline.json",
        corrupted_embeddings_json=tmp_path / "embeddings" / "corrupted.json",
        repaired_embeddings_json=tmp_path / "embeddings" / "repaired.json",
    )
    settings = replace(settings, paths=paths)

    assert ask.embeddings_path_for(settings, "baseline") == paths.embeddings_json
    assert ask.embeddings_path_for(settings, "corrupted") == paths.corrupted_embeddings_json
    assert ask.embeddings_path_for(settings, "repaired") == paths.repaired_embeddings_json


def test_match_test_sample_is_case_insensitive() -> None:
    expected = {"id": "q001", "question": "  What Is RAG?  "}
    test_set = [expected, {"id": "q002", "question": "Who wrote it?"}]

    assert ask.match_test_sample(test_set, " what is rag? ") is expected


def test_match_test_sample_returns_none_when_question_is_absent() -> None:
    test_set = [{"id": "q001", "question": "What is RAG?"}]

    assert ask.match_test_sample(test_set, "When was it published?") is None
