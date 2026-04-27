from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_WEIGHTS: dict[str, float] = {
    "sharpness": 0.2,
    "local_contrast": 0.15,
    "snr": 0.15,
    "structure_continuity": 0.15,
    "artifact_strength": 0.12,
    "body_area_ratio": 0.08,
    "background_noise": 0.1,
    "subjective_rating": 0.05,
}

METRIC_DIRECTIONS: dict[str, str] = {
    "sharpness": "high",
    "local_contrast": "high",
    "snr": "high",
    "structure_continuity": "high",
    "artifact_strength": "low",
    "body_area_ratio": "high",
    "background_noise": "low",
    "subjective_rating": "high",
}


def normalize_weights(weights: dict[str, float] | None) -> dict[str, float]:
    merged = DEFAULT_WEIGHTS if weights is None else {key: weights.get(key, 0.0) for key in DEFAULT_WEIGHTS}
    cleaned = {key: max(0.0, float(value)) for key, value in merged.items() if key in DEFAULT_WEIGHTS}
    total = sum(cleaned.values())
    if total <= 0:
        return deepcopy(DEFAULT_WEIGHTS)
    return {key: value / total for key, value in cleaned.items()}


def score_records(records: list[dict[str, Any]], weights: dict[str, float] | None = None) -> list[dict[str, Any]]:
    normalized_weights = normalize_weights(weights)
    if not records:
        return []
    if all(record.get("subjective_rating") in (None, "") for record in records):
        normalized_weights = normalize_weights(
            {key: value for key, value in normalized_weights.items() if key != "subjective_rating"}
        )

    metric_values = {
        metric: [_metric_value(record, metric) for record in records]
        for metric in normalized_weights.keys()
    }
    scored: list[dict[str, Any]] = []
    for record in records:
        item = deepcopy(record)
        normalized_metrics: dict[str, float] = {}
        total = 0.0
        for metric, weight in normalized_weights.items():
            values = metric_values[metric]
            value = _metric_value(record, metric)
            normalized = _normalize_metric(value, min(values), max(values), METRIC_DIRECTIONS[metric])
            normalized_metrics[metric] = round(normalized, 4)
            total += normalized * weight
        item["normalized_metrics"] = normalized_metrics
        item["quality_score"] = round(total * 100.0, 2)
        scored.append(item)

    return sorted(scored, key=lambda row: row["quality_score"], reverse=True)


def _metric_value(record: dict[str, Any], metric: str) -> float:
    if metric == "subjective_rating":
        rating = record.get("subjective_rating")
        return 0.0 if rating in (None, "") else float(rating)
    metrics = record.get("metrics") or {}
    return float(metrics.get(metric, 0.0))


def _normalize_metric(value: float, low: float, high: float, direction: str) -> float:
    if high <= low:
        return 1.0 if value > 0 else 0.0
    normalized = (value - low) / (high - low)
    normalized = max(0.0, min(1.0, normalized))
    return 1.0 - normalized if direction == "low" else normalized
