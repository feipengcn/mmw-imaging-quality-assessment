import type { MetricKey, Weights } from './types';

export const metricKeys: MetricKey[] = [
  'sharpness',
  'local_contrast',
  'snr',
  'structure_continuity',
  'artifact_strength',
  'body_area_ratio',
  'background_noise',
  'subjective_rating',
];

export const metricLabels: Record<MetricKey, string> = {
  sharpness: '清晰度',
  local_contrast: '局部对比',
  snr: '信噪比',
  structure_continuity: '结构连续',
  artifact_strength: '伪影强度',
  body_area_ratio: '人体占比',
  background_noise: '背景噪声',
  subjective_rating: '人工评分',
};

export const defaultWeights: Weights = {
  sharpness: 0.2,
  local_contrast: 0.15,
  snr: 0.15,
  structure_continuity: 0.15,
  artifact_strength: 0.12,
  body_area_ratio: 0.08,
  background_noise: 0.1,
  subjective_rating: 0.05,
};

export function weightSum(weights: Weights): number {
  return metricKeys.reduce((sum, key) => sum + weights[key], 0);
}

export function normalizeWeights(input: Partial<Weights>): Weights {
  const raw = metricKeys.reduce((acc, key) => {
    acc[key] = Math.max(0, Number(input[key] ?? defaultWeights[key]));
    return acc;
  }, {} as Weights);
  const total = weightSum(raw);
  if (total <= 0) {
    return { ...defaultWeights };
  }
  return metricKeys.reduce((acc, key) => {
    acc[key] = raw[key] / total;
    return acc;
  }, {} as Weights);
}

export function formatMetric(value: number | undefined): string {
  if (value === undefined || Number.isNaN(value)) return '-';
  if (Math.abs(value) < 1) return value.toFixed(4);
  if (Math.abs(value) < 100) return value.toFixed(2);
  return value.toFixed(1);
}
