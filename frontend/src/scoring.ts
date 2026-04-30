import type { MetricKey, Weights } from './types';

export const metricKeys: MetricKey[] = [
  'sharpness_score',
  'significance_score',
  'artifact_suppression_score',
  'structure_score',
  'detail_score',
];

export const metricLabels: Record<MetricKey, string> = {
  sharpness_score: '锐度',
  significance_score: '显著性',
  artifact_suppression_score: '伪影抑制',
  structure_score: '结构完整性',
  detail_score: '细节保真',
};

export const defaultWeights: Weights = {
  sharpness_score: 0.07,
  significance_score: 0.1,
  artifact_suppression_score: 0.45,
  structure_score: 0.08,
  detail_score: 0.3,
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

export function formatView(view: string | undefined): string {
  if (view === 'front') return '正面';
  if (view === 'back') return '背面';
  return '未确定';
}
