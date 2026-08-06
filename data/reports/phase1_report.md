# Phase 1 Baseline Report

## Source and pipeline configuration

- **source_api:** Crossref REST API
- **source_query:** agentic retrieval augmented generation large language model
- **source_filter:** from-pub-date:2026-02-07,has-abstract:true
- **source_mode:** loaded_from_snapshot
- **max_results:** 24
- **raw_records:** 24
- **clean_rows:** 24
- **embedding_model:** sentence-transformers/all-MiniLM-L6-v2
- **collection_name:** papers-baseline
- **top_k:** 4
- **llm_provider:** openrouter
- **llm_model:** deepseek-v4-pro
- **test_set_size:** 73
- **test_set_mode:** loaded_existing

## Evaluation metrics

| Metric | Baseline |
|---|---|
| `samples` | 73 |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 0.9206 |
| `judge_accuracy` | 0.9178 |
| `mean_judge_score` | 4.6712 |
| `ragas` | {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'} |

## Data quality

- **Overall pass:** True
- **Total rows:** 24
- **Failed checks:** None

## Freshness

- **latest_published:** 2026-08-01
- **oldest_published:** 2026-02-12
- **stale_rows:** 0
- **invalid_date_rows:** 0
- **total_rows:** 24
- **threshold_days:** 180
- **is_fresh:** True

> All conclusions in this report are limited to the recorded artifacts above.
