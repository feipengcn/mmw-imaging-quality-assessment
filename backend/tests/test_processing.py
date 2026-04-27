import numpy as np
import pytest
from pathlib import Path
from PIL import Image, ImageFilter

from app.processing import compute_image_features, compute_quality_metrics, extract_body_mask


ROOT = Path(__file__).resolve().parents[2]


def synthetic_body_image(noise_level: int = 4) -> Image.Image:
    rng = np.random.default_rng(42)
    image = rng.normal(18, noise_level, size=(96, 96)).clip(0, 255).astype(np.uint8)
    image[20:76, 30:66] = 165
    image[28:68, 38:58] = 210
    return Image.fromarray(image, mode="L")


def test_extract_body_mask_selects_largest_human_region_and_rejects_background():
    image = synthetic_body_image()

    mask = extract_body_mask(image)

    assert mask.shape == (96, 96)
    assert mask[40:60, 40:55].mean() > 0.95
    assert mask[:12, :12].mean() < 0.05
    assert 0.16 < mask.mean() < 0.35


def test_extract_body_mask_recovers_full_front_body_when_reflection_is_uneven():
    image = Image.open(ROOT / "example_pic" / "1602_front.png")

    mask = extract_body_mask(image)
    ys, xs = np.where(mask)

    assert mask.mean() > 0.10
    assert ys.min() < 330
    assert ys.max() > 760
    assert xs.min() < 90
    assert xs.max() > 340


@pytest.mark.parametrize(
    ("filename", "min_x", "max_x", "min_y"),
    [
        ("1063_front.png", 65, 340, 250),
        ("1093_front.png", 90, 340, 250),
        ("1615_front.png", 90, 360, 250),
        ("1000_front.png", 80, 340, 230),
    ],
)
def test_extract_body_mask_keeps_nearby_disconnected_body_parts(filename: str, min_x: int, max_x: int, min_y: int):
    image = Image.open(ROOT / "example_pic" / filename)

    mask = extract_body_mask(image)
    ys, xs = np.where(mask)

    assert xs.min() < min_x
    assert xs.max() > max_x
    assert ys.min() < min_y


def test_metrics_rank_sharp_image_above_blurred_image_for_sharpness():
    sharp = synthetic_body_image()
    blurred = sharp.filter(ImageFilter.GaussianBlur(radius=3))

    sharp_metrics = compute_quality_metrics(sharp)
    blurred_metrics = compute_quality_metrics(blurred)

    assert sharp_metrics["sharpness"] > blurred_metrics["sharpness"] * 2
    assert sharp_metrics["body_area_ratio"] > 0.15


def test_metrics_detect_more_background_noise():
    clean = synthetic_body_image(noise_level=2)
    noisy = synthetic_body_image(noise_level=28)

    clean_metrics = compute_quality_metrics(clean)
    noisy_metrics = compute_quality_metrics(noisy)

    assert noisy_metrics["background_noise"] > clean_metrics["background_noise"] * 4


def test_compute_image_features_returns_grayscale_and_rgb_histograms():
    rgb = np.zeros((8, 8, 3), dtype=np.uint8)
    rgb[:, :, 0] = 32
    rgb[:, :, 1] = 128
    rgb[:, :, 2] = 224

    features = compute_image_features(Image.fromarray(rgb, mode="RGB"), bins=16)

    assert features["width"] == 8
    assert features["height"] == 8
    assert len(features["histograms"]["gray"]) == 16
    assert len(features["histograms"]["red"]) == 16
    assert len(features["histograms"]["green"]) == 16
    assert len(features["histograms"]["blue"]) == 16
    assert sum(features["histograms"]["red"]) == 64
