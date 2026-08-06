# Corruption Comparison Report

## Evaluation metrics

| Metric | Baseline | Corrupted | Repaired |
|---|---|---|---|
| `samples` | 73 | 73 | 73 |
| `retrieval_hit_rate` | 1.0000 | 0.7397 | 1.0000 |
| `mean_token_f1` | 0.9206 | 0.2620 | 0.9206 |
| `judge_accuracy` | 0.9178 | 0.2740 | 0.9178 |
| `mean_judge_score` | 4.6712 | 2.0959 | 4.6712 |
| `ragas` | {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'} | {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'} | {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'} |

## Metric deltas

| Metric | Corrupted - baseline | Repaired - baseline |
|---|---:|---:|
| `samples` | 0 | 0 |
| `retrieval_hit_rate` | -0.2603 | 0.0000 |
| `mean_token_f1` | -0.6586 | 0.0000 |
| `judge_accuracy` | -0.6438 | 0.0000 |
| `mean_judge_score` | -2.5753 | 0.0000 |

## Quality and freshness signals

| State | Quality pass | Failed checks | Freshness | Stale rows |
|---|---|---|---|---:|
| Corrupted | False | paper_id_unique, summary_length, freshness | False | 22 |
| Repaired | True | None | True | 0 |

> The report presents observed deltas only; it does not claim recovery unless the recorded numbers support that conclusion.
