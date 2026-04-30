from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageFilter

from app.processing import compute_image_features, compute_quality_metrics, extract_body_mask
import app.processing as processing


ROOT = Path(__file__).resolve().parents[2]


def synthetic_body_image(
    noise_level: int = 4,
    stripe_period: int | None = None,
    stripe_amplitude: int = 0,
    saturation_patch: bool = False,
    background_spots: bool = False,
) -> Image.Image:
    rng = np.random.default_rng(42)
    image = rng.normal(16, noise_level, size=(128, 96)).clip(0, 255).astype(np.float32)
    image[18:112, 28:68] = 150
    image[28:102, 34:62] = 205
    if stripe_period and stripe_amplitude > 0:
        body = image[18:112, 28:68]
        x = np.arange(body.shape[1], dtype=np.float32)
        stripe = ((np.sin((2.0 * np.pi * x) / stripe_period) + 1.0) * 0.5) * stripe_amplitude
        body += stripe[np.newaxis, :]
        image[18:112, 28:68] = body
    if background_spots:
        image[6:10, 6:10] = 220
        image[14:18, 80:84] = 245
        image[108:114, 6:12] = 210
        image[108:114, 80:90] = 235
    if saturation_patch:
        image[40:96, 42:58] = 255
    return Image.fromarray(image.clip(0, 255).astype(np.uint8), mode="L")


def test_extract_body_mask_selects_largest_human_region_and_rejects_background():
    image = synthetic_body_image()

    mask = extract_body_mask(image)

    assert mask.shape == (128, 96)
    assert mask[40:80, 36:60].mean() > 0.95
    assert mask[:12, :12].mean() < 0.05
    assert 0.18 < mask.mean() < 0.42


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


def test_quality_metrics_expose_mmwave_specific_fields():
    metrics = compute_quality_metrics(synthetic_body_image())

    expected_keys = {
        "tenengrad_variance",
        "edge_rise_distance",
        "cnr",
        "leakage_ratio",
        "background_bright_spot_ratio",
        "background_local_std",
        "component_count",
        "solidity",
        "saturation_ratio",
        "roi_entropy",
        "pai",
        "coherent_speckle_index",
        "body_area_ratio",
    }

    assert expected_keys.issubset(metrics.keys())


def test_quality_metrics_can_reuse_precomputed_mask():
    image = synthetic_body_image()
    mask = extract_body_mask(image)

    direct = compute_quality_metrics(image)
    reused = compute_quality_metrics(image, mask=mask)

    assert reused["cnr"] == direct["cnr"]
    assert reused["body_area_ratio"] == direct["body_area_ratio"]


def test_blur_reduces_tenengrad_and_worsens_edge_rise_distance():
    sharp = synthetic_body_image()
    blurred = sharp.filter(ImageFilter.GaussianBlur(radius=3))

    sharp_metrics = compute_quality_metrics(sharp)
    blurred_metrics = compute_quality_metrics(blurred)

    assert sharp_metrics["tenengrad_variance"] > blurred_metrics["tenengrad_variance"] * 2
    assert sharp_metrics["edge_rise_distance"] < blurred_metrics["edge_rise_distance"]


def test_noise_increases_background_local_std():
    clean = synthetic_body_image(noise_level=2)
    noisy = synthetic_body_image(noise_level=24)

    clean_metrics = compute_quality_metrics(clean)
    noisy_metrics = compute_quality_metrics(noisy)

    assert noisy_metrics["background_local_std"] > clean_metrics["background_local_std"] * 2


def test_background_spots_increase_background_bright_spot_ratio():
    clean = synthetic_body_image()
    spotted = synthetic_body_image(background_spots=True)

    clean_metrics = compute_quality_metrics(clean)
    spotted_metrics = compute_quality_metrics(spotted)

    assert spotted_metrics["background_bright_spot_ratio"] > clean_metrics["background_bright_spot_ratio"] + 0.01


def test_striped_body_produces_higher_pai():
    smooth = synthetic_body_image()
    striped = synthetic_body_image(stripe_period=6, stripe_amplitude=46)

    smooth_metrics = compute_quality_metrics(smooth)
    striped_metrics = compute_quality_metrics(striped)

    assert striped_metrics["pai"] > smooth_metrics["pai"] * 1.2


def test_striped_body_produces_higher_coherent_speckle_index():
    smooth = synthetic_body_image()
    striped = synthetic_body_image(stripe_period=6, stripe_amplitude=46)

    smooth_metrics = compute_quality_metrics(smooth)
    striped_metrics = compute_quality_metrics(striped)

    assert striped_metrics["coherent_speckle_index"] > smooth_metrics["coherent_speckle_index"] * 1.2


def test_saturated_region_produces_higher_saturation_ratio():
    base = synthetic_body_image()
    saturated = synthetic_body_image(saturation_patch=True)

    base_metrics = compute_quality_metrics(base)
    saturated_metrics = compute_quality_metrics(saturated)

    assert saturated_metrics["saturation_ratio"] > base_metrics["saturation_ratio"] + 0.05


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


def test_find_golden_edge_computes_gradient_threshold_once(monkeypatch):
    image = synthetic_body_image()
    arr = processing.normalize_grayscale(image)
    mask = extract_body_mask(image)
    calls = {"mask_percentile": 0}
    original_percentile = processing.np.percentile

    def tracking_percentile(values, q, *args, **kwargs):
        result = original_percentile(values, q, *args, **kwargs)
        if q == 60 and isinstance(values, np.ndarray) and values.shape == arr[mask].shape:
            calls["mask_percentile"] += 1
        return result

    monkeypatch.setattr(processing.np, "percentile", tracking_percentile)
    edge = processing._find_golden_edge(mask, arr)

    assert edge is not None
    assert calls["mask_percentile"] == 1


def test_adaptive_leakage_width_scales_with_body_size():
    small = synthetic_body_image()
    large = small.resize((192, 256), Image.Resampling.BILINEAR)

    small_mask = extract_body_mask(small)
    large_mask = extract_body_mask(large)

    small_width = processing._adaptive_leakage_width(small_mask)
    large_width = processing._adaptive_leakage_width(large_mask)

    assert small_width >= 6
    assert large_width > small_width
