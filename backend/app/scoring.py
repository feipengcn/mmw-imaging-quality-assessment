from __future__ import annotations

from copy import deepcopy
import math
from typing import Any


QUALITY_DIMENSIONS = [
    "sharpness_score",
    "significance_score",
    "artifact_suppression_score",
    "structure_score",
    "detail_score",
]

DEFAULT_WEIGHTS: dict[str, float] = {
    "sharpness_score": 0.07,
    "significance_score": 0.10,
    "artifact_suppression_score": 0.45,
    "structure_score": 0.08,
    "detail_score": 0.30,
}

PAI_PENALTY_THRESHOLD = 6.0
SATURATION_PENALTY_THRESHOLD = 0.15
MIN_VALID_BODY_AREA_RATIO = 0.05
METRIC_SCORE_MAX = 100
TRANSFORMED_METRICS = {"tenengrad_variance", "cnr", "leakage_ratio"}

UNKNOWN_METRIC_SCORE_SPECS: dict[str, tuple[str, float, float]] = {
    "tenengrad_variance": ("high", 9.0, 10.05),
    "edge_rise_distance": ("low", 2.0, 8.5),
    "cnr": ("high", 1.0, 2.3),
    "leakage_ratio": ("low", 0.3, 1.9),
    "background_bright_spot_ratio": ("low", 0.0, 0.02),
    "background_local_std": ("low", 0.08, 5.0),
    "component_count": ("low", 1.0, 4.0),
    "solidity": ("high", 0.28, 0.5),
    "saturation_ratio": ("low", 0.01, 0.15),
    "roi_entropy": ("high", 7.35, 7.8),
    "pai": ("low", 2.8, 5.8),
    "coherent_speckle_index": ("low", 0.14, 0.34),
    "body_area_ratio": ("high", 0.05, 0.2),
}

VIEW_PROFILES: dict[str, dict[str, Any]] = {
    "unknown": {
        "metric_score_specs": UNKNOWN_METRIC_SCORE_SPECS,
        "structure_component_scores": {1: 1.0, 2: 0.75, 3: 0.25},
        "score_component_scores": {1: 1.0, 2: 0.75, 3: 0.25},
    },
    "front": {
        "metric_score_specs": {
            **UNKNOWN_METRIC_SCORE_SPECS,
            "leakage_ratio": ("low", 0.25, 1.7),
            "background_bright_spot_ratio": ("low", 0.0, 0.018),
            "background_local_std": ("low", 0.08, 4.5),
            "solidity": ("high", 0.3, 0.52),
            "coherent_speckle_index": ("low", 0.14, 0.3),
        },
        "structure_component_scores": {1: 1.0, 2: 0.88, 3: 0.55},
        "score_component_scores": {1: 1.0, 2: 0.88, 3: 0.55},
    },
    "back": {
        "metric_score_specs": {
            **UNKNOWN_METRIC_SCORE_SPECS,
            "leakage_ratio": ("low", 0.35, 2.1),
            "background_bright_spot_ratio": ("low", 0.0, 0.022),
            "background_local_std": ("low", 0.08, 4.0),
            "solidity": ("high", 0.26, 0.46),
            "coherent_speckle_index": ("low", 0.14, 0.32),
        },
        "structure_component_scores": {1: 1.0, 2: 0.8, 3: 0.55},
        "score_component_scores": {1: 1.0, 2: 0.8, 3: 0.55},
    },
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
    scored: list[dict[str, Any]] = []

    for record in records:
        item = deepcopy(record)
        metrics = item.get("metrics") or {}
        view = _normalize_view(item.get("view"))
        profile = VIEW_PROFILES[view]
        specs = profile["metric_score_specs"]
        metric_scores = {
            key: round(_raw_metric_score(key, _metric_value(key, metrics, 0.0), specs, profile) * METRIC_SCORE_MAX, 1)
            for key in specs
        }
        normalized_metrics = {
            "sharpness_score": round(_sharpness_score(metrics, specs), 4),
            "significance_score": round(_significance_score(metrics, specs), 4),
            "artifact_suppression_score": round(_artifact_suppression_score(metrics, specs), 4),
            "structure_score": round(_structure_score(metrics, specs, profile), 4),
            "detail_score": round(_detail_score(metrics, specs), 4),
        }
        base_score = sum(normalized_metrics[key] * normalized_weights[key] for key in QUALITY_DIMENSIONS) * 100.0
        penalty_flags = {
            "saturation": float(metrics.get("saturation_ratio", 0.0)) > SATURATION_PENALTY_THRESHOLD,
            "pai": float(metrics.get("pai", 0.0)) > PAI_PENALTY_THRESHOLD,
        }
        valid_sample = float(metrics.get("body_area_ratio", 0.0)) >= MIN_VALID_BODY_AREA_RATIO
        penalty_factor = 1.0
        if penalty_flags["saturation"]:
            penalty_factor *= 0.45
        if penalty_flags["pai"]:
            penalty_factor *= 0.45
        final_score = base_score * penalty_factor
        if not valid_sample:
            final_score = min(final_score, 20.0)

        item["view"] = view
        item["normalized_metrics"] = normalized_metrics
        item["metric_scores"] = metric_scores
        item["metric_score_max"] = METRIC_SCORE_MAX
        item["penalty_flags"] = penalty_flags
        item["valid_sample"] = valid_sample
        item["quality_score"] = round(final_score, 2)
        scored.append(item)

    return sorted(scored, key=lambda row: row["quality_score"], reverse=True)


def _sharpness_score(metrics: dict[str, Any], specs: dict[str, tuple[str, float, float]]) -> float:
    tenengrad = _score_from_spec(_metric_value("tenengrad_variance", metrics, 0.0), specs["tenengrad_variance"])
    rise = _score_from_spec(_metric_value("edge_rise_distance", metrics, 10.0), specs["edge_rise_distance"])
    return 0.65 * tenengrad + 0.35 * rise


def _significance_score(metrics: dict[str, Any], specs: dict[str, tuple[str, float, float]]) -> float:
    return _score_from_spec(_metric_value("cnr", metrics, 0.0), specs["cnr"])


def _artifact_suppression_score(metrics: dict[str, Any], specs: dict[str, tuple[str, float, float]]) -> float:
    leakage = _score_from_spec(_metric_value("leakage_ratio", metrics, 1.0), specs["leakage_ratio"])
    bright_spots = _score_from_spec(_metric_value("background_bright_spot_ratio", metrics, 0.0), specs["background_bright_spot_ratio"])
    local_std = _score_from_spec(_metric_value("background_local_std", metrics, 0.0), specs["background_local_std"])
    speckle = _score_from_spec(_metric_value("coherent_speckle_index", metrics, 0.0), specs["coherent_speckle_index"])
    return 0.08 * leakage + 0.15 * bright_spots + 0.30 * local_std + 0.47 * speckle


def _structure_score(
    metrics: dict[str, Any],
    specs: dict[str, tuple[str, float, float]],
    profile: dict[str, Any],
) -> float:
    components = int(round(float(metrics.get("component_count", 0.0))))
    component_score = _component_score(components, profile["structure_component_scores"])
    solidity = _score_from_spec(_metric_value("solidity", metrics, 0.0), specs["solidity"])
    return 0.4 * component_score + 0.6 * solidity


def _detail_score(metrics: dict[str, Any], specs: dict[str, tuple[str, float, float]]) -> float:
    entropy = _score_from_spec(_metric_value("roi_entropy", metrics, 0.0), specs["roi_entropy"])
    saturation = _score_from_spec(_metric_value("saturation_ratio", metrics, 0.0), specs["saturation_ratio"])
    pai = _score_from_spec(_metric_value("pai", metrics, 0.0), specs["pai"])
    return 0.4 * entropy + 0.15 * saturation + 0.45 * pai


def _raw_metric_score(
    metric: str,
    value: float,
    specs: dict[str, tuple[str, float, float]],
    profile: dict[str, Any],
) -> float:
    if metric == "component_count":
        return _component_score(int(round(value)), profile["score_component_scores"])
    return _score_from_spec(value, specs[metric])


def _score_from_spec(value: float, spec: tuple[str, float, float]) -> float:
    direction, floor, ceiling = spec
    return _normalize_high(value, floor, ceiling) if direction == "high" else _normalize_low(value, floor, ceiling)


def _metric_value(metric: str, metrics: dict[str, Any], default: float) -> float:
    value = float(metrics.get(metric, default))
    if metric in TRANSFORMED_METRICS:
        return math.log10(max(value, 1e-6))
    return value


def _component_score(components: int, score_map: dict[int, float]) -> float:
    if components <= 1:
        return score_map.get(1, 1.0)
    if components == 2:
        return score_map.get(2, 0.75)
    if components == 3:
        return score_map.get(3, 0.25)
    return 0.0


def _normalize_view(view: Any) -> str:
    if isinstance(view, str):
        view = view.lower().strip()
        if view in VIEW_PROFILES:
            return view
    return "unknown"


def _normalize_high(value: float, floor: float, ceiling: float) -> float:
    if ceiling <= floor:
        return 0.0
    normalized = (value - floor) / (ceiling - floor)
    return max(0.0, min(1.0, normalized))


def _normalize_low(value: float, ideal: float, worst: float) -> float:
    if worst <= ideal:
        return 0.0
    normalized = (value - ideal) / (worst - ideal)
    normalized = max(0.0, min(1.0, normalized))
    return 1.0 - normalized
