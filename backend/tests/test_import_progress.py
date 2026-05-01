from io import BytesIO
import json

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

import app.main as main
import app.storage as storage
from app.processing import QualityAnalysis
from app.storage import ImageRepository


def test_import_progress_streams_per_file_events(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "repository", ImageRepository(tmp_path))

    def fake_analyze_quality(image, mask=None):
        analysis_mask = np.ones((image.height, image.width), dtype=bool)
        return QualityAnalysis(mask=analysis_mask, metrics={"body_area_ratio": 1.0}, overlays={
            "aoi": analysis_mask,
            "leakage": np.zeros_like(analysis_mask, dtype=bool),
            "stripe": np.zeros_like(analysis_mask, dtype=bool),
        })

    monkeypatch.setattr(storage, "analyze_quality", fake_analyze_quality)
    monkeypatch.setattr(storage, "predict_view", lambda image, mask=None, source_name=None: {"view": "unknown", "confidence": 0.0})

    def image_bytes() -> bytes:
        buffer = BytesIO()
        Image.fromarray(np.full((24, 24), 128, dtype=np.uint8), mode="L").save(buffer, format="PNG")
        return buffer.getvalue()

    client = TestClient(main.app)
    response = client.post(
        "/api/import/progress",
        files=[
            ("files", ("a.png", image_bytes(), "image/png")),
            ("files", ("b.png", image_bytes(), "image/png")),
        ],
        data={"experiment_group": "default", "algorithm": "unknown", "parameters": "", "batch": ""},
    )

    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines()]
    assert [event["type"] for event in events] == ["progress", "progress", "complete"]
    assert events[0]["completed"] == 1
    assert events[0]["total"] == 2
    assert events[0]["filename"] == "a.png"
    assert events[1]["completed"] == 2
    assert events[2]["imported"] == 2
    assert len(events[2]["images"]) == 2
