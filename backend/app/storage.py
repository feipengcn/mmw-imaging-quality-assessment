from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from .processing import compute_image_features, compute_quality_metrics, extract_body_mask, save_mask_png


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
SUBJECTIVE_SCORE_KEYS = [
    "contour_clarity",
    "structure_integrity",
    "background_cleanliness",
    "artifact_acceptability",
    "practical_usability",
]


class ImageRepository:
    def __init__(self, data_dir: Path | str = "data") -> None:
        self.data_dir = Path(data_dir)
        self.uploads_dir = self.data_dir / "uploads"
        self.masks_dir = self.data_dir / "masks"
        self.state_path = self.data_dir / "state.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.masks_dir.mkdir(parents=True, exist_ok=True)

    def list_records(self) -> list[dict[str, Any]]:
        return self._read_state().get("images", [])

    def import_files(
        self,
        files: list[tuple[str, bytes]],
        experiment_group: str,
        algorithm: str,
        parameters: str,
        batch: str,
    ) -> list[dict[str, Any]]:
        imported: list[dict[str, Any]] = []
        state = self._read_state()
        for filename, content in files:
            suffix = Path(filename).suffix.lower()
            if suffix not in IMAGE_EXTENSIONS:
                continue
            image_id = uuid.uuid4().hex
            safe_name = f"{image_id}{suffix}"
            stored_path = self.uploads_dir / safe_name
            stored_path.write_bytes(content)

            original_image = Image.open(stored_path)
            image = original_image.convert("L")
            mask = extract_body_mask(image)
            mask_path = self.masks_dir / f"{image_id}.png"
            save_mask_png(mask, mask_path)
            metrics = compute_quality_metrics(image)
            features = compute_image_features(original_image)

            record = {
                "id": image_id,
                "filename": _display_filename(filename),
                "stored_filename": safe_name,
                "mask_filename": mask_path.name,
                "experiment_group": experiment_group or "default",
                "algorithm": algorithm or "unknown",
                "parameters": parameters or "",
                "batch": batch or "",
                "metrics": metrics,
                "features": features,
                "subjective_scores": _empty_subjective_scores(),
                "subjective_rating": None,
                "subjective_rating_complete": False,
                "notes": "",
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            }
            imported.append(record)
            state.setdefault("images", []).append(record)
        self._write_state(state)
        return imported

    def update_rating(
        self,
        image_id: str,
        subjective_rating: int | float | None = None,
        subjective_scores: dict[str, int | None] | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        state = self._read_state()
        for record in state.get("images", []):
            if record["id"] == image_id:
                if subjective_scores is not None:
                    normalized_scores = _normalize_subjective_scores(subjective_scores)
                    record["subjective_scores"] = normalized_scores
                    average = _subjective_average(normalized_scores)
                    record["subjective_rating"] = average
                    record["subjective_rating_complete"] = all(
                        normalized_scores[key] is not None for key in SUBJECTIVE_SCORE_KEYS
                    )
                elif subjective_rating is not None:
                    record["subjective_rating"] = round(max(1.0, min(5.0, float(subjective_rating))), 2)
                if notes is not None:
                    record["notes"] = notes
                self._write_state(state)
                return record
        raise KeyError(image_id)

    def image_path(self, image_id: str) -> Path:
        record = self._get_record(image_id)
        return self.uploads_dir / record["stored_filename"]

    def mask_path(self, image_id: str) -> Path:
        record = self._get_record(image_id)
        return self.masks_dir / record["mask_filename"]

    def reset(self) -> None:
        if self.data_dir.exists():
            shutil.rmtree(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.masks_dir.mkdir(parents=True, exist_ok=True)
        self._write_state({"images": []})

    def _get_record(self, image_id: str) -> dict[str, Any]:
        for record in self.list_records():
            if record["id"] == image_id:
                return record
        raise KeyError(image_id)

    def _read_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"images": []}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _write_state(self, state: dict[str, Any]) -> None:
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _display_filename(filename: str) -> str:
    normalized = filename.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part not in ("", ".", "..")]
    return "/".join(parts) or Path(filename).name


def _empty_subjective_scores() -> dict[str, None]:
    return {key: None for key in SUBJECTIVE_SCORE_KEYS}


def _normalize_subjective_scores(scores: dict[str, int | None]) -> dict[str, int | None]:
    normalized: dict[str, int | None] = {}
    for key in SUBJECTIVE_SCORE_KEYS:
        value = scores.get(key)
        normalized[key] = None if value is None else max(1, min(5, int(value)))
    return normalized


def _subjective_average(scores: dict[str, int | None]) -> float | None:
    values = [value for value in scores.values() if value is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 2)
