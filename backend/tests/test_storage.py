from io import BytesIO

import numpy as np
from PIL import Image

from app.storage import ImageRepository


def test_import_files_preserves_folder_relative_display_path(tmp_path):
    arr = np.full((32, 32), 20, dtype=np.uint8)
    arr[8:24, 10:22] = 200
    buffer = BytesIO()
    Image.fromarray(arr, mode="L").save(buffer, format="PNG")

    repo = ImageRepository(tmp_path)
    imported = repo.import_files(
        [("case-a/algorithm-1/sample.png", buffer.getvalue())],
        experiment_group="group",
        algorithm="algorithm-1",
        parameters="p",
        batch="b",
    )

    assert imported[0]["filename"] == "case-a/algorithm-1/sample.png"
    assert "subjective_rating" not in imported[0]
    assert "subjective_scores" not in imported[0]

def test_import_files_persist_mmwave_metric_payload(tmp_path):
    arr = np.full((32, 32), 20, dtype=np.uint8)
    arr[8:24, 10:22] = 200
    buffer = BytesIO()
    Image.fromarray(arr, mode="L").save(buffer, format="PNG")

    repo = ImageRepository(tmp_path)
    record = repo.import_files(
        [("sample.png", buffer.getvalue())],
        experiment_group="group",
        algorithm="algorithm-1",
        parameters="p",
        batch="b",
    )[0]

    assert "tenengrad_variance" in record["metrics"]
    assert "cnr" in record["metrics"]
    assert "pai" in record["metrics"]
    assert record["view"] in {"front", "back", "unknown"}
    assert 0.0 <= record["view_confidence"] <= 1.0


def test_import_files_persist_overlay_assets(tmp_path):
    arr = np.full((32, 32), 20, dtype=np.uint8)
    arr[8:24, 10:22] = 200
    buffer = BytesIO()
    Image.fromarray(arr, mode="L").save(buffer, format="PNG")

    repo = ImageRepository(tmp_path)
    record = repo.import_files(
        [("sample.png", buffer.getvalue())],
        experiment_group="group",
        algorithm="algorithm-1",
        parameters="p",
        batch="b",
    )[0]

    assert set(record["overlay_filenames"].keys()) == {"aoi", "leakage", "stripe"}
    assert (repo.overlays_dir / record["overlay_filenames"]["aoi"]).exists()
    assert (repo.overlays_dir / record["overlay_filenames"]["leakage"]).exists()
    assert (repo.overlays_dir / record["overlay_filenames"]["stripe"]).exists()


def test_delete_image_removes_record_and_assets(tmp_path):
    arr = np.full((32, 32), 20, dtype=np.uint8)
    arr[8:24, 10:22] = 200
    buffer = BytesIO()
    Image.fromarray(arr, mode="L").save(buffer, format="PNG")

    repo = ImageRepository(tmp_path)
    record = repo.import_files(
        [("sample.png", buffer.getvalue())],
        experiment_group="group",
        algorithm="algorithm-1",
        parameters="p",
        batch="b",
    )[0]

    repo.delete_image(record["id"])

    assert repo.list_records() == []
    assert not (repo.uploads_dir / record["stored_filename"]).exists()
    assert not (repo.masks_dir / record["mask_filename"]).exists()
    for filename in record["overlay_filenames"].values():
        assert not (repo.overlays_dir / filename).exists()
