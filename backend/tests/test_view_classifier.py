from pathlib import Path

import numpy as np
from PIL import Image

import app.view_classifier as view_classifier
from app.view_classifier import PrototypeViewClassifier, REFERENCE_MAX_SIDE


ROOT = Path(__file__).resolve().parents[2]


def test_prototype_view_classifier_predicts_labeled_examples_with_leave_one_out():
    classifier = PrototypeViewClassifier(ROOT / "example_pic")
    samples = [
        ("1000_front.png", "front"),
        ("1000_back.png", "back"),
        ("1028_front.png", "front"),
        ("1028_back.png", "back"),
        ("1602_front.png", "front"),
    ]

    for filename, expected in samples:
        result = classifier.predict(
            Image.open(ROOT / "example_pic" / filename).convert("L"),
            source_name=filename,
        )
        assert result["view"] == expected
        assert 0.5 <= result["confidence"] <= 1.0


def test_reference_embeddings_are_built_from_bounded_previews(tmp_path, monkeypatch):
    for name in ("case_front.png", "case_back.png"):
        Image.new("L", (440, 840), color=128).save(tmp_path / name)

    embedded_sizes = []

    def fake_view_embedding(image, mask=None):
        embedded_sizes.append(image.size)
        return np.ones(16, dtype=np.float32)

    monkeypatch.setattr(view_classifier, "_view_embedding", fake_view_embedding)

    PrototypeViewClassifier(tmp_path)

    assert embedded_sizes
    assert all(max(size) <= REFERENCE_MAX_SIDE for size in embedded_sizes)
