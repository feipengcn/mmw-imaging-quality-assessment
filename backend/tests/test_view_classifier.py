from pathlib import Path

from PIL import Image

from app.view_classifier import PrototypeViewClassifier


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
