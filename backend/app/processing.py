from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class ProcessedImage:
    image: Image.Image
    mask: np.ndarray
    metrics: dict[str, float]


def load_grayscale(path: Path | str) -> Image.Image:
    return Image.open(path).convert("L")


def normalize_grayscale(image: Image.Image) -> np.ndarray:
    arr = np.asarray(image.convert("L"), dtype=np.float32)
    low, high = np.percentile(arr, [1, 99])
    if high <= low:
        return np.zeros_like(arr, dtype=np.float32)
    return np.clip((arr - low) / (high - low), 0, 1) * 255


def extract_body_mask(image: Image.Image) -> np.ndarray:
    arr = normalize_grayscale(image)
    threshold = _otsu_threshold(arr)
    seed = arr >= threshold

    if seed.mean() > 0.65 or seed.mean() < 0.02:
        seed = arr >= (arr.mean() + 0.45 * arr.std())

    mask = _seeded_body_candidate(arr, seed)
    mask = _binary_open(mask, iterations=1)
    mask = _binary_close(mask, iterations=1)
    return mask.astype(bool)


def compute_quality_metrics(image: Image.Image) -> dict[str, float]:
    arr = normalize_grayscale(image)
    mask = extract_body_mask(image)
    roi = arr[mask]
    background = arr[~mask]
    if roi.size == 0:
        roi = arr.reshape(-1)
    if background.size < 8:
        background = arr.reshape(-1)

    bg_std = float(np.std(background))
    roi_mean = float(np.mean(roi))
    bg_mean = float(np.mean(background))
    roi_std = float(np.std(roi))

    lap = _laplacian(arr)
    grad = _gradient_magnitude(arr)
    artifact_threshold = roi_mean + max(20.0, 1.5 * roi_std)
    artifact_pixels = np.logical_and(~mask, arr >= artifact_threshold)

    return {
        "sharpness": round(float(np.var(lap[mask])) if mask.any() else float(np.var(lap)), 4),
        "local_contrast": round((roi_std / 255.0) * 100.0, 4),
        "snr": round((roi_mean - bg_mean) / (bg_std + 1e-6), 4),
        "structure_continuity": round(_mask_fill_ratio(mask), 4),
        "artifact_strength": round(float(artifact_pixels.mean() * 100.0), 4),
        "body_area_ratio": round(float(mask.mean()), 4),
        "background_noise": round((bg_std / 255.0) * 100.0, 4),
        "edge_density": round(float((grad[mask] > np.percentile(grad, 75)).mean()) if mask.any() else 0.0, 4),
    }


def compute_image_features(image: Image.Image, bins: int = 64) -> dict[str, object]:
    rgb = image.convert("RGB")
    gray = image.convert("L")
    rgb_arr = np.asarray(rgb, dtype=np.uint8)
    gray_arr = np.asarray(gray, dtype=np.uint8)
    return {
        "width": int(rgb.width),
        "height": int(rgb.height),
        "mode": image.mode,
        "histograms": {
            "gray": _histogram(gray_arr, bins),
            "red": _histogram(rgb_arr[:, :, 0], bins),
            "green": _histogram(rgb_arr[:, :, 1], bins),
            "blue": _histogram(rgb_arr[:, :, 2], bins),
        },
    }


def save_mask_png(mask: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((mask.astype(np.uint8) * 255), mode="L").save(path)


def _otsu_threshold(arr: np.ndarray) -> float:
    hist, bin_edges = np.histogram(arr.ravel(), bins=256, range=(0, 255))
    total = arr.size
    sum_total = float(np.dot(hist, np.arange(256)))
    weight_bg = 0
    sum_bg = 0.0
    best_variance = -1.0
    best_threshold = float(arr.mean())

    for idx, count in enumerate(hist):
        weight_bg += int(count)
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += float(idx * count)
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_total - sum_bg) / weight_fg
        variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if variance > best_variance:
            best_variance = variance
            best_threshold = float(bin_edges[idx])
    return max(8.0, best_threshold)


def _binary_dilate(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    result = mask.astype(bool)
    for _ in range(iterations):
        padded = np.pad(result, 1, mode="constant", constant_values=False)
        result = np.zeros_like(result, dtype=bool)
        for y in range(3):
            for x in range(3):
                result |= padded[y : y + mask.shape[0], x : x + mask.shape[1]]
    return result


def _binary_erode(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    result = mask.astype(bool)
    for _ in range(iterations):
        padded = np.pad(result, 1, mode="constant", constant_values=False)
        result = np.ones_like(result, dtype=bool)
        for y in range(3):
            for x in range(3):
                result &= padded[y : y + mask.shape[0], x : x + mask.shape[1]]
    return result


def _binary_close(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    return _binary_erode(_binary_dilate(mask, iterations), iterations)


def _binary_open(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    return _binary_dilate(_binary_erode(mask, iterations), iterations)


def _seeded_body_candidate(arr: np.ndarray, seed: np.ndarray) -> np.ndarray:
    seed = _binary_close(seed, iterations=2)
    seed = _binary_open(seed, iterations=1)
    if not seed.any():
        return seed

    weak_threshold = max(10.0, float(np.percentile(arr, 70)), float(arr.mean() + 0.12 * arr.std()))
    weak = arr >= weak_threshold
    weak = _binary_close(weak, iterations=2)
    weak = _body_components_near_seed(weak, seed)
    weak = _binary_close(weak, iterations=3)
    return weak


def _body_components_near_seed(mask: np.ndarray, seed: np.ndarray) -> np.ndarray:
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    result = np.zeros_like(mask, dtype=bool)
    seeded_result = np.zeros_like(mask, dtype=bool)
    best: list[tuple[int, int]] = []
    detached: list[list[tuple[int, int]]] = []

    for start_y, start_x in np.argwhere(mask):
        y = int(start_y)
        x = int(start_x)
        if visited[y, x]:
            continue
        stack = [(y, x)]
        visited[y, x] = True
        component: list[tuple[int, int]] = []
        touches_seed = False
        while stack:
            cy, cx = stack.pop()
            component.append((cy, cx))
            touches_seed = touches_seed or bool(seed[cy, cx])
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((ny, nx))
        if len(component) > len(best):
            best = component
        if touches_seed:
            for cy, cx in component:
                result[cy, cx] = True
                seeded_result[cy, cx] = True
        else:
            detached.append(component)

    if result.any():
        _add_nearby_detached_components(result, seeded_result, detached, mask.shape)
        return result

    fallback = np.zeros_like(mask, dtype=bool)
    for y, x in best:
        fallback[y, x] = True
    return fallback


def _add_nearby_detached_components(
    result: np.ndarray,
    seeded_result: np.ndarray,
    detached: list[list[tuple[int, int]]],
    shape: tuple[int, int],
) -> None:
    coords = np.argwhere(seeded_result)
    if coords.size == 0:
        return

    height, width = shape
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0)
    body_width = int(x1 - x0 + 1)
    body_height = int(y1 - y0 + 1)
    x_margin = max(35, int(body_width * 0.38))
    y_margin = max(85, int(body_height * 0.22))
    search_x0 = max(0, int(x0) - x_margin)
    search_x1 = min(width - 1, int(x1) + x_margin)
    search_y0 = max(0, int(y0) - y_margin)
    search_y1 = min(height - 1, int(y1) + y_margin)
    min_area = max(180, int(height * width * 0.004))
    border_margin = max(12, int(width * 0.03))

    for component in detached:
        if len(component) < min_area:
            continue
        ys = [point[0] for point in component]
        xs = [point[1] for point in component]
        comp_x0 = min(xs)
        comp_x1 = max(xs)
        comp_y0 = min(ys)
        comp_y1 = max(ys)
        if comp_x0 <= border_margin or comp_x1 >= width - 1 - border_margin:
            continue
        center_x = sum(xs) / len(xs)
        center_y = sum(ys) / len(ys)
        if not (search_x0 <= center_x <= search_x1 and search_y0 <= center_y <= search_y1):
            continue
        comp_width = comp_x1 - comp_x0 + 1
        comp_height = comp_y1 - comp_y0 + 1
        if comp_height > body_height * 0.75 and comp_width < max(8, body_width * 0.08):
            continue
        for y, x in component:
            result[y, x] = True


def _largest_component(mask: np.ndarray) -> np.ndarray:
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    best: list[tuple[int, int]] = []

    for start_y, start_x in np.argwhere(mask):
        y = int(start_y)
        x = int(start_x)
        if visited[y, x]:
            continue
        stack = [(y, x)]
        visited[y, x] = True
        component: list[tuple[int, int]] = []
        while stack:
            cy, cx = stack.pop()
            component.append((cy, cx))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    stack.append((ny, nx))
        if len(component) > len(best):
            best = component

    result = np.zeros_like(mask, dtype=bool)
    for y, x in best:
        result[y, x] = True
    return result


def _laplacian(arr: np.ndarray) -> np.ndarray:
    padded = np.pad(arr, 1, mode="edge")
    center = padded[1:-1, 1:-1]
    return (
        -4 * center
        + padded[:-2, 1:-1]
        + padded[2:, 1:-1]
        + padded[1:-1, :-2]
        + padded[1:-1, 2:]
    )


def _gradient_magnitude(arr: np.ndarray) -> np.ndarray:
    gy, gx = np.gradient(arr)
    return np.sqrt(gx * gx + gy * gy)


def _mask_fill_ratio(mask: np.ndarray) -> float:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return 0.0
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0)
    box_area = max(1, int((y1 - y0 + 1) * (x1 - x0 + 1)))
    return float(mask.sum() / box_area)


def _histogram(arr: np.ndarray, bins: int) -> list[int]:
    hist, _ = np.histogram(arr.ravel(), bins=bins, range=(0, 256))
    return [int(value) for value in hist]
