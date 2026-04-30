from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from .processing import analyze_quality, compute_image_features, save_mask_png, save_overlay_png
from .view_classifier import predict_view


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


class ImageRepository:
    def __init__(self, data_dir: Path | str = "data") -> None:
        self.data_dir = Path(data_dir)
        self.uploads_dir = self.data_dir / "uploads"
        self.masks_dir = self.data_dir / "masks"
        self.overlays_dir = self.data_dir / "overlays"
        self.state_path = self.data_dir / "state.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.masks_dir.mkdir(parents=True, exist_ok=True)
        self.overlays_dir.mkdir(parents=True, exist_ok=True)

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
            analysis = analyze_quality(image)
            mask = analysis.mask
            mask_path = self.masks_dir / f"{image_id}.png"
            save_mask_png(mask, mask_path)
            overlay_filenames = {
                "aoi": f"{image_id}-aoi.png",
                "leakage": f"{image_id}-leakage.png",
                "stripe": f"{image_id}-stripe.png",
            }
            save_overlay_png(analysis.overlays["aoi"], self.overlays_dir / overlay_filenames["aoi"], (20, 184, 166, 96))
            save_overlay_png(analysis.overlays["leakage"], self.overlays_dir / overlay_filenames["leakage"], (217, 45, 32, 110))
            save_overlay_png(analysis.overlays["stripe"], self.overlays_dir / overlay_filenames["stripe"], (245, 158, 11, 120))
            features = compute_image_features(original_image)
            view_result = predict_view(image, mask=mask, source_name=Path(filename).name)

            record = {
                "id": image_id,
                "filename": _display_filename(filename),
                "stored_filename": safe_name,
                "mask_filename": mask_path.name,
                "experiment_group": experiment_group or "default",
                "algorithm": algorithm or "unknown",
                "parameters": parameters or "",
                "batch": batch or "",
                "metrics": analysis.metrics,
                "features": features,
                "view": view_result["view"],
                "view_confidence": view_result["confidence"],
                "overlay_filenames": overlay_filenames,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            }
            imported.append(record)
            state.setdefault("images", []).append(record)
        self._write_state(state)
        return imported

    def image_path(self, image_id: str) -> Path:
        record = self._get_record(image_id)
        return self.uploads_dir / record["stored_filename"]

    def mask_path(self, image_id: str) -> Path:
        record = self._get_record(image_id)
        return self.masks_dir / record["mask_filename"]

    def overlay_path(self, image_id: str, kind: str) -> Path:
        record = self._get_record(image_id)
        overlay_filenames = record.get("overlay_filenames") or {}
        if kind not in overlay_filenames:
            raise KeyError(image_id)
        return self.overlays_dir / overlay_filenames[kind]

    def delete_image(self, image_id: str) -> None:
        state = self._read_state()
        images = state.get("images", [])
        record = next((item for item in images if item["id"] == image_id), None)
        if record is None:
            raise KeyError(image_id)

        for path in (
            self.uploads_dir / record["stored_filename"],
            self.masks_dir / record["mask_filename"],
        ):
            if path.exists():
                path.unlink()

        for filename in (record.get("overlay_filenames") or {}).values():
            overlay_path = self.overlays_dir / filename
            if overlay_path.exists():
                overlay_path.unlink()

        state["images"] = [item for item in images if item["id"] != image_id]
        self._write_state(state)

    def reset(self) -> None:
        if self.data_dir.exists():
            shutil.rmtree(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.masks_dir.mkdir(parents=True, exist_ok=True)
        self.overlays_dir.mkdir(parents=True, exist_ok=True)
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
