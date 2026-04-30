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


@dataclass(frozen=True)
class QualityAnalysis:
    mask: np.ndarray
    metrics: dict[str, float]
    overlays: dict[str, np.ndarray]


def load_grayscale(path: Path | str) -> Image.Image:
    return Image.open(path).convert("L")


def normalize_grayscale(image: Image.Image) -> np.ndarray:
    arr = np.asarray(image.convert("L"), dtype=np.float32)
    low, high = np.percentile(arr, [1, 99])
    if high <= low:
        return np.zeros_like(arr, dtype=np.float32)
    return np.clip((arr - low) / (high - low), 0, 1) * 255.0


def extract_body_mask(image: Image.Image) -> np.ndarray:
    norm_arr = normalize_grayscale(image)
    threshold = _otsu_threshold(norm_arr)
    seed = norm_arr >= threshold
    if seed.mean() > 0.65 or seed.mean() < 0.02:
        seed = norm_arr >= (norm_arr.mean() + 0.45 * norm_arr.std())
    seed = _binary_close(seed, iterations=2)
    seed = _fill_holes(seed)
    seed = _largest_component(seed)
    weak_threshold = max(10.0, float(np.percentile(norm_arr, 68)), float(norm_arr.mean() + 0.10 * norm_arr.std()))
    weak = norm_arr >= weak_threshold
    weak = _binary_close(weak, iterations=2)
    mask = _body_components_near_seed(weak, seed)
    mask = _fill_holes(mask)
    mask = _binary_close(mask, iterations=1)
    return mask.astype(bool)


def analyze_quality(image: Image.Image, mask: np.ndarray | None = None) -> QualityAnalysis:
    raw_arr = np.asarray(image.convert("L"), dtype=np.float32)
    norm_arr = normalize_grayscale(image)
    mask = extract_body_mask(image) if mask is None else mask.astype(bool)

    body = raw_arr[mask]
    if body.size == 0:
        body = raw_arr.reshape(-1)

    deep_background_mask = _deep_background_mask(mask)
    if deep_background_mask.sum() < 16:
        deep_background_mask = ~mask
    background = norm_arr[deep_background_mask]
    if background.size < 16:
        background = norm_arr[~mask]
    if background.size < 16:
        background = norm_arr.reshape(-1)

    leakage_ring = _build_leakage_ring(mask, dilation_pixels=_adaptive_leakage_width(mask))
    leakage_values = norm_arr[leakage_ring]
    if leakage_values.size == 0:
        leakage_values = background

    tenengrad_map = _tenengrad_map(norm_arr)
    golden_edge = _find_golden_edge(mask, norm_arr)
    edge_rise_distance = _edge_rise_distance(norm_arr, golden_edge)

    local_std_map = _local_std(norm_arr, window=9)
    component_count = _count_components(mask)
    hull = _convex_hull(np.argwhere(mask))
    hull_area = _polygon_area(hull)
    saturation_ratio = float((raw_arr[mask] > 250).mean()) if mask.any() else 0.0
    roi_entropy = _entropy(raw_arr[mask]) if mask.any() else 0.0
    pai, stripe_mask = _periodic_artifact_index(raw_arr, mask)
    bright_spot_ratio = _background_bright_spot_ratio(norm_arr, deep_background_mask)
    coherent_speckle_index = _coherent_speckle_index(norm_arr, mask)

    bg_energy = float(np.mean(background * background)) + 1e-6
    leakage_energy = float(np.mean(leakage_values * leakage_values))
    cnr = (float(np.mean(norm_arr[mask])) - float(np.mean(background))) / (float(np.std(background)) + 1e-6)

    metrics = {
        "tenengrad_variance": round(float(np.var(tenengrad_map[mask])) if mask.any() else float(np.var(tenengrad_map)), 4),
        "edge_rise_distance": round(edge_rise_distance, 4),
        "cnr": round(cnr, 4),
        "leakage_ratio": round(leakage_energy / bg_energy, 4),
        "background_bright_spot_ratio": round(bright_spot_ratio, 4),
        "background_local_std": round(float(np.mean(local_std_map[deep_background_mask])) if deep_background_mask.any() else float(np.mean(local_std_map)), 4),
        "component_count": round(float(component_count), 4),
        "solidity": round(float(mask.sum()) / max(hull_area, 1.0), 4),
        "saturation_ratio": round(saturation_ratio, 4),
        "roi_entropy": round(roi_entropy, 4),
        "pai": round(pai, 4),
        "coherent_speckle_index": round(coherent_speckle_index, 4),
        "body_area_ratio": round(float(mask.mean()), 4),
    }
    overlays = {
        "aoi": mask,
        "leakage": leakage_ring,
        "stripe": stripe_mask,
    }
    return QualityAnalysis(mask=mask, metrics=metrics, overlays=overlays)


def compute_quality_metrics(image: Image.Image, mask: np.ndarray | None = None) -> dict[str, float]:
    return analyze_quality(image, mask=mask).metrics


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


def save_overlay_png(mask: np.ndarray, path: Path, rgba: tuple[int, int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    overlay = np.zeros((mask.shape[0], mask.shape[1], 4), dtype=np.uint8)
    overlay[mask.astype(bool)] = np.array(rgba, dtype=np.uint8)
    Image.fromarray(overlay, mode="RGBA").save(path)


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
        next_result = np.zeros_like(result, dtype=bool)
        for y in range(3):
            for x in range(3):
                next_result |= padded[y : y + result.shape[0], x : x + result.shape[1]]
        result = next_result
    return result


def _binary_erode(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    result = mask.astype(bool)
    for _ in range(iterations):
        padded = np.pad(result, 1, mode="constant", constant_values=False)
        next_result = np.ones_like(result, dtype=bool)
        for y in range(3):
            for x in range(3):
                next_result &= padded[y : y + result.shape[0], x : x + result.shape[1]]
        result = next_result
    return result


def _binary_close(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    return _binary_erode(_binary_dilate(mask, iterations), iterations)


def _fill_holes(mask: np.ndarray) -> np.ndarray:
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    stack: list[tuple[int, int]] = []

    for x in range(width):
        if not mask[0, x]:
            stack.append((0, x))
        if not mask[height - 1, x]:
            stack.append((height - 1, x))
    for y in range(height):
        if not mask[y, 0]:
            stack.append((y, 0))
        if not mask[y, width - 1]:
            stack.append((y, width - 1))

    while stack:
        y, x = stack.pop()
        if visited[y, x] or mask[y, x]:
            continue
        visited[y, x] = True
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < height and 0 <= nx < width and not visited[ny, nx] and not mask[ny, nx]:
                stack.append((ny, nx))
    return mask | ~visited


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

    result = np.zeros_like(mask, dtype=bool)
    for y, x in best:
        result[y, x] = True
    return result


def _count_components(mask: np.ndarray) -> int:
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    count = 0
    for start_y, start_x in np.argwhere(mask):
        y = int(start_y)
        x = int(start_x)
        if visited[y, x]:
            continue
        count += 1
        stack = [(y, x)]
        visited[y, x] = True
        while stack:
            cy, cx = stack.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((ny, nx))
    return count


def _deep_background_mask(mask: np.ndarray) -> np.ndarray:
    height, width = mask.shape
    patch_h = max(12, height // 5)
    patch_w = max(12, width // 5)
    corners = np.zeros_like(mask, dtype=bool)
    corners[:patch_h, :patch_w] = True
    corners[:patch_h, width - patch_w :] = True
    corners[height - patch_h :, :patch_w] = True
    corners[height - patch_h :, width - patch_w :] = True
    expanded_body = _binary_dilate(mask, iterations=max(2, min(height, width) // 32))
    return corners & ~expanded_body


def _build_leakage_ring(mask: np.ndarray, dilation_pixels: int) -> np.ndarray:
    dilated = mask.copy()
    for _ in range(max(1, dilation_pixels)):
        dilated = _binary_dilate(dilated, iterations=1)
    return dilated & ~mask


def _adaptive_leakage_width(mask: np.ndarray) -> int:
    if not mask.any():
        return 6
    equivalent_size = float(np.sqrt(mask.sum()))
    return int(max(6, min(40, round(equivalent_size * 0.06))))


def _tenengrad_map(arr: np.ndarray) -> np.ndarray:
    gx = _sobel_x(arr)
    gy = _sobel_y(arr)
    return gx * gx + gy * gy


def _find_golden_edge(mask: np.ndarray, arr: np.ndarray) -> tuple[tuple[float, float], tuple[float, float]] | None:
    contour = _contour_points(mask)
    if len(contour) < 9:
        return None
    grads = np.sqrt(_tenengrad_map(arr))
    grad_threshold = float(np.percentile(grads[mask], 60)) if mask.any() else float(np.percentile(grads, 60))
    best: tuple[float, tuple[tuple[float, float], tuple[float, float]]] | None = None
    for index in range(4, len(contour) - 4):
        prev_point = np.asarray(contour[index - 4], dtype=np.float32)
        point = np.asarray(contour[index], dtype=np.float32)
        next_point = np.asarray(contour[index + 4], dtype=np.float32)
        v1 = point - prev_point
        v2 = next_point - point
        norm1 = float(np.linalg.norm(v1))
        norm2 = float(np.linalg.norm(v2))
        if norm1 < 1e-6 or norm2 < 1e-6:
            continue
        tangent = next_point - prev_point
        tangent_norm = float(np.linalg.norm(tangent))
        if tangent_norm < 1e-6:
            continue
        cross_value = float(v1[0] * v2[1] - v1[1] * v2[0])
        curvature = abs(cross_value / (norm1 * norm2 + 1e-6))
        y = int(np.clip(round(point[0]), 0, grads.shape[0] - 1))
        x = int(np.clip(round(point[1]), 0, grads.shape[1] - 1))
        grad_strength = float(grads[y, x])
        if grad_strength < grad_threshold:
            continue
        tangent = tangent / tangent_norm
        normal = np.asarray([-tangent[1], tangent[0]], dtype=np.float32)
        score = curvature - grad_strength * 1e-3
        candidate = ((float(point[0]), float(point[1])), (float(normal[0]), float(normal[1])))
        if best is None or score < best[0]:
            best = (score, candidate)
    return None if best is None else best[1]


def _edge_rise_distance(arr: np.ndarray, golden_edge: tuple[tuple[float, float], tuple[float, float]] | None) -> float:
    if golden_edge is None:
        return 10.0
    (cy, cx), (ny, nx) = golden_edge
    samples = []
    for step in np.linspace(-8.0, 8.0, 65):
        y = cy + ny * step
        x = cx + nx * step
        samples.append(_bilinear_sample(arr, y, x))
    profile = np.asarray(samples, dtype=np.float32)
    low = float(np.min(profile))
    high = float(np.max(profile))
    if high <= low + 1e-6:
        return 10.0
    normalized = (profile - low) / (high - low)
    idx10 = _first_crossing(normalized, 0.1)
    idx90 = _first_crossing(normalized, 0.9)
    if idx10 is None or idx90 is None or idx90 <= idx10:
        return 10.0
    step_size = 16.0 / 64.0
    return max(0.5, (idx90 - idx10) * step_size)


def _local_std(arr: np.ndarray, window: int) -> np.ndarray:
    mean = _box_filter(arr, window)
    mean_sq = _box_filter(arr * arr, window)
    variance = np.maximum(mean_sq - mean * mean, 0.0)
    return np.sqrt(variance)


def _box_filter(arr: np.ndarray, window: int) -> np.ndarray:
    radius = window // 2
    padded = np.pad(arr, radius, mode="reflect")
    integral = np.pad(padded, ((1, 0), (1, 0)), mode="constant", constant_values=0).cumsum(axis=0).cumsum(axis=1)
    total = (
        integral[window:, window:]
        - integral[:-window, window:]
        - integral[window:, :-window]
        + integral[:-window, :-window]
    )
    return total / float(window * window)


def _convex_hull(points: np.ndarray) -> list[tuple[float, float]]:
    if points.size == 0:
        return []
    unique = sorted({(int(x), int(y)) for y, x in points})
    if len(unique) <= 1:
        return [(float(unique[0][0]), float(unique[0][1]))] if unique else []

    def cross(o: tuple[int, int], a: tuple[int, int], b: tuple[int, int]) -> int:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[int, int]] = []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)

    upper: list[tuple[int, int]] = []
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)

    hull = lower[:-1] + upper[:-1]
    return [(float(x), float(y)) for x, y in hull]


def _polygon_area(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    for index, (x0, y0) in enumerate(points):
        x1, y1 = points[(index + 1) % len(points)]
        area += x0 * y1 - x1 * y0
    return abs(area) * 0.5


def _entropy(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    hist, _ = np.histogram(values, bins=256, range=(0, 256))
    prob = hist.astype(np.float64)
    prob /= prob.sum()
    prob = prob[prob > 0]
    return float(-(prob * np.log2(prob)).sum())


def _periodic_artifact_index(arr: np.ndarray, mask: np.ndarray) -> tuple[float, np.ndarray]:
    if not mask.any():
        return 0.0, np.zeros_like(mask, dtype=bool)
    coords = np.argwhere(mask)
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0)
    crop = arr[int(y0) : int(y1) + 1, int(x0) : int(x1) + 1].astype(np.float32)
    crop_mask = mask[int(y0) : int(y1) + 1, int(x0) : int(x1) + 1]
    fill_value = float(np.mean(crop[crop_mask]))
    crop = np.where(crop_mask, crop, fill_value)
    residual = crop - _box_filter(crop, window=9)
    spectrum = np.fft.fftshift(np.fft.fft2(residual))
    magnitude = np.abs(spectrum)
    height, width = crop.shape
    cy, cx = height // 2, width // 2
    yy, xx = np.indices(magnitude.shape)
    radius = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    valid = radius > max(4.0, min(height, width) * 0.05)
    band = magnitude[valid]
    if band.size == 0:
        return 0.0, np.zeros_like(mask, dtype=bool)
    spectrum_ratio = float(np.percentile(band, 99.5) / (np.mean(band) + 1e-6))
    interior_mask = _binary_erode(crop_mask, iterations=4)
    if interior_mask.any():
        counts = np.maximum(interior_mask.sum(axis=0), 1)
        profile = (crop * interior_mask).sum(axis=0) / counts
    else:
        profile = np.mean(crop, axis=0)
    profile = profile - _smooth_1d(profile, window=9)
    profile_fft = np.abs(np.fft.rfft(profile - np.mean(profile)))
    if profile_fft.size <= 3:
        return spectrum_ratio, np.zeros_like(mask, dtype=bool)
    profile_band = profile_fft[2:]
    profile_ratio = float(np.max(profile_band) / (np.mean(profile_band) + 1e-6))
    stripe_columns = np.abs(profile) >= max(float(np.mean(np.abs(profile)) + 1.5 * np.std(np.abs(profile))), 6.0)
    if stripe_columns.any():
        stripe_columns = np.convolve(stripe_columns.astype(np.uint8), np.ones(5, dtype=np.uint8), mode="same") > 0
    stripe_crop = np.zeros_like(crop_mask, dtype=bool)
    if stripe_columns.any():
        stripe_crop[:, stripe_columns] = True
        stripe_crop &= crop_mask
    stripe_mask = np.zeros_like(mask, dtype=bool)
    stripe_mask[int(y0) : int(y1) + 1, int(x0) : int(x1) + 1] = stripe_crop
    return max(profile_ratio, spectrum_ratio * 0.15), stripe_mask


def _background_bright_spot_ratio(arr: np.ndarray, background_mask: np.ndarray) -> float:
    if not background_mask.any():
        return 0.0
    background = arr[background_mask]
    threshold = float(np.mean(background) + 2.5 * np.std(background))
    return float((background >= threshold).mean())


def _coherent_speckle_index(arr: np.ndarray, mask: np.ndarray) -> float:
    if not mask.any():
        return 0.0
    coords = np.argwhere(mask)
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0)
    crop = arr[int(y0) : int(y1) + 1, int(x0) : int(x1) + 1].astype(np.float32)
    crop_mask = mask[int(y0) : int(y1) + 1, int(x0) : int(x1) + 1]
    interior = _binary_erode(crop_mask, iterations=4)
    if not interior.any():
        interior = crop_mask
    if not interior.any() or crop.shape[0] < 3 or crop.shape[1] < 3:
        return 0.0

    residual = crop - _box_filter(crop, window=9)
    reference = float(np.mean(crop[crop_mask])) + 1e-6
    return float(np.std(residual[interior]) / reference)


def _smooth_1d(values: np.ndarray, window: int) -> np.ndarray:
    radius = window // 2
    padded = np.pad(values.astype(np.float32), radius, mode="edge")
    kernel = np.ones(window, dtype=np.float32) / float(window)
    return np.convolve(padded, kernel, mode="valid")


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


def _contour_points(mask: np.ndarray) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    height, width = mask.shape
    for y, x in np.argwhere(mask):
        iy = int(y)
        ix = int(x)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = iy + dy, ix + dx
            if not (0 <= ny < height and 0 <= nx < width) or not mask[ny, nx]:
                points.append((iy, ix))
                break
    return points


def _first_crossing(profile: np.ndarray, threshold: float) -> float | None:
    for index in range(1, profile.size):
        if profile[index] >= threshold and profile[index - 1] < threshold:
            y0 = float(profile[index - 1])
            y1 = float(profile[index])
            if y1 <= y0:
                return float(index)
            ratio = (threshold - y0) / (y1 - y0)
            return float(index - 1 + ratio)
    return None


def _bilinear_sample(arr: np.ndarray, y: float, x: float) -> float:
    y = float(np.clip(y, 0, arr.shape[0] - 1))
    x = float(np.clip(x, 0, arr.shape[1] - 1))
    y0 = int(np.floor(y))
    x0 = int(np.floor(x))
    y1 = min(y0 + 1, arr.shape[0] - 1)
    x1 = min(x0 + 1, arr.shape[1] - 1)
    dy = y - y0
    dx = x - x0
    top = arr[y0, x0] * (1.0 - dx) + arr[y0, x1] * dx
    bottom = arr[y1, x0] * (1.0 - dx) + arr[y1, x1] * dx
    return float(top * (1.0 - dy) + bottom * dy)


def _sobel_x(arr: np.ndarray) -> np.ndarray:
    padded = np.pad(arr, 1, mode="edge")
    return (
        padded[:-2, 2:]
        + 2.0 * padded[1:-1, 2:]
        + padded[2:, 2:]
        - padded[:-2, :-2]
        - 2.0 * padded[1:-1, :-2]
        - padded[2:, :-2]
    )


def _sobel_y(arr: np.ndarray) -> np.ndarray:
    padded = np.pad(arr, 1, mode="edge")
    return (
        padded[2:, :-2]
        + 2.0 * padded[2:, 1:-1]
        + padded[2:, 2:]
        - padded[:-2, :-2]
        - 2.0 * padded[:-2, 1:-1]
        - padded[:-2, 2:]
    )


def _histogram(arr: np.ndarray, bins: int) -> list[int]:
    hist, _ = np.histogram(arr.ravel(), bins=bins, range=(0, 256))
    return [int(value) for value in hist]
