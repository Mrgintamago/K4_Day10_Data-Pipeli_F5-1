from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import write_text


def _value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    if value is None:
        return "N/A"
    return str(value)


def _bullet_map(values: dict[str, Any]) -> str:
    return "\n".join(f"- **{key}:** {_value(value)}" for key, value in values.items())


def _metrics_table(states: dict[str, dict[str, Any]]) -> str:
    keys = list(dict.fromkeys(key for payload in states.values() for key in payload))
    lines = ["| Metric | " + " | ".join(states) + " |", "|---|" + "---|" * len(states)]
    lines.extend(
        f"| `{key}` | {' | '.join(_value(states[state].get(key)) for state in states)} |"
        for key in keys
    )
    return "\n".join(lines)


def _delta_table(baseline: dict[str, Any], corrupted: dict[str, Any], repaired: dict[str, Any]) -> str:
    numeric_keys = [key for key, value in baseline.items() if isinstance(value, (int, float)) and key in corrupted and key in repaired]
    lines = ["| Metric | Corrupted - baseline | Repaired - baseline |", "|---|---:|---:|"]
    for key in numeric_keys:
        lines.append(f"| `{key}` | {_value(corrupted[key] - baseline[key])} | {_value(repaired[key] - baseline[key])} |")
    return "\n".join(lines) if numeric_keys else "No comparable numeric metrics were provided."


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write a baseline report whose values are copied from pipeline payloads."""
    content = "\n".join(
        [
            "# Phase 1 Baseline Report",
            "",
            "## Source and pipeline configuration",
            "",
            _bullet_map(source_summary),
            "",
            "## Evaluation metrics",
            "",
            _metrics_table({"Baseline": metrics}),
            "",
            "## Data quality",
            "",
            f"- **Overall pass:** {quality.get('overall_pass', False)}",
            f"- **Total rows:** {_value(quality.get('total_rows'))}",
            f"- **Failed checks:** {_value(', '.join(quality.get('summary', {}).get('failed_checks', [])) or 'None')}",
            "",
            "## Freshness",
            "",
            _bullet_map(freshness),
            "",
            "> All conclusions in this report are limited to the recorded artifacts above.",
            "",
        ]
    )
    write_text(Path(report_path), content)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write a three-state comparison without inferring recovery beyond the metrics."""
    content = "\n".join(
        [
            "# Corruption Comparison Report",
            "",
            "## Evaluation metrics",
            "",
            _metrics_table({
                "Baseline": baseline_metrics,
                "Corrupted": corrupted_metrics,
                "Repaired": repaired_metrics,
            }),
            "",
            "## Metric deltas",
            "",
            _delta_table(baseline_metrics, corrupted_metrics, repaired_metrics),
            "",
            "## Quality and freshness signals",
            "",
            "| State | Quality pass | Failed checks | Freshness | Stale rows |",
            "|---|---|---|---|---:|",
            f"| Corrupted | {corrupted_quality.get('overall_pass', False)} | {_value(', '.join(corrupted_quality.get('summary', {}).get('failed_checks', [])) or 'None')} | {_value(corrupted_freshness.get('is_fresh'))} | {_value(corrupted_freshness.get('stale_rows'))} |",
            f"| Repaired | {repaired_quality.get('overall_pass', False)} | {_value(', '.join(repaired_quality.get('summary', {}).get('failed_checks', [])) or 'None')} | {_value(repaired_freshness.get('is_fresh'))} | {_value(repaired_freshness.get('stale_rows'))} |",
            "",
            "> The report presents observed deltas only; it does not claim recovery unless the recorded numbers support that conclusion.",
            "",
        ]
    )
    write_text(Path(report_path), content)
