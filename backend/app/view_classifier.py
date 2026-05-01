from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .processing import extract_body_mask, normalize_grayscale


REFERENCE_SIZE = (48, 96)
REFERENCE_MAX_SIDE = 160
MIN_CONFIDENCE = 0.55


def predict_view(
    image: Image.Image,
    mask: np.ndarray | None = None,
    source_name: str | None = None,
    reference_dir: Path | None = None,
) -> dict[str, Any]:
    classifier = _default_classifier() if reference_dir is None else PrototypeViewClassifier(reference_dir)
    return classifier.predict(image, mask=mask, source_name=source_name)


@dataclass(frozen=True)
class ReferenceSample:
    name: str
    view: str
    embedding: np.ndarray


class PrototypeViewClassifier:
    def __init__(self, reference_dir: Path | str) -> None:
        self.reference_dir = Path(reference_dir)
        self.samples = self._load_samples()

    def predict(
        self,
        image: Image.Image,
        mask: np.ndarray | None = None,
        source_name: str | None = None,
    ) -> dict[str, Any]:
        embedding = _view_embedding(image, mask=mask)
        samples = [sample for sample in self.samples if sample.name != source_name]
        if not samples:
            samples = self.samples
        if not samples:
            return {"view": "unknown", "confidence": 0.0}

        centroids = {
            view: _normalize_vector(np.mean([sample.embedding for sample in samples if sample.view == view], axis=0))
            for view in ("front", "back")
        }
        scores = {view: float(np.dot(embedding, centroid)) for view, centroid in centroids.items()}
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best_view, best_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else -1.0
        confidence = max(0.0, min(1.0, 0.5 + 0.5 * (best_score - second_score)))
        return {
            "view": best_view if confidence >= MIN_CONFIDENCE else "unknown",
            "confidence": round(confidence, 4),
        }

    def _load_samples(self) -> list[ReferenceSample]:
        if not self.reference_dir.exists():
            return []
        samples: list[ReferenceSample] = []
        for path in sorted(self.reference_dir.iterdir()):
            if not path.is_file():
                continue
            view = _view_from_name(path.name)
            if view is None:
                continue
            image = _resize_reference_image(Image.open(path))
            samples.append(ReferenceSample(path.name, view, _view_embedding(image)))
        return samples


def _view_embedding(image: Image.Image, mask: np.ndarray | None = None) -> np.ndarray:
    norm = normalize_grayscale(image).astype(np.float32)
    body_mask = extract_body_mask(image) if mask is None else mask.astype(bool)
    if body_mask.any():
        ys, xs = np.where(body_mask)
        y0, x0 = int(ys.min()), int(xs.min())
        y1, x1 = int(ys.max()) + 1, int(xs.max()) + 1
        crop = norm[y0:y1, x0:x1]
        crop_mask = body_mask[y0:y1, x0:x1]
        fill = float(np.mean(crop[crop_mask])) if crop_mask.any() else float(np.mean(crop))
        crop = np.where(crop_mask, crop, fill)
    else:
        crop = norm

    resized = Image.fromarray(crop.astype(np.uint8), mode="L").resize(REFERENCE_SIZE, Image.Resampling.BILINEAR)
    arr = np.asarray(resized, dtype=np.float32) / 255.0
    arr = (arr - float(arr.mean())) / (float(arr.std()) + 1e-6)
    vertical_profile = arr.mean(axis=1)
    horizontal_profile = arr.mean(axis=0)
    symmetry_gap = np.array([np.abs(arr - arr[:, ::-1]).mean()], dtype=np.float32)
    embedding = np.concatenate(
        [
            arr.ravel() * 0.35,
            vertical_profile * 0.40,
            horizontal_profile * 0.20,
            symmetry_gap,
        ]
    ).astype(np.float32)
    return _normalize_vector(embedding)


def _normalize_vector(values: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(values))
    if norm <= 1e-6:
        return values.astype(np.float32)
    return (values / norm).astype(np.float32)


def _view_from_name(name: str) -> str | None:
    stem = Path(name).stem.lower()
    if stem.endswith("_front") or "front" in stem:
        return "front"
    if stem.endswith("_back") or "back" in stem:
        return "back"
    return None


def _resize_reference_image(image: Image.Image) -> Image.Image:
    grayscale = image.convert("L")
    max_side = max(grayscale.size)
    if max_side <= REFERENCE_MAX_SIDE:
        return grayscale
    scale = REFERENCE_MAX_SIDE / float(max_side)
    size = (
        max(1, round(grayscale.width * scale)),
        max(1, round(grayscale.height * scale)),
    )
    return grayscale.resize(size, Image.Resampling.BILINEAR)


@lru_cache(maxsize=1)
def _default_classifier() -> PrototypeViewClassifier:
    reference_dir = Path(__file__).resolve().parents[2] / "example_pic"
    return PrototypeViewClassifier(reference_dir)
