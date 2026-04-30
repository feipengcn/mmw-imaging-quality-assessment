import { describe, expect, it } from 'vitest';
import { defaultWeights, normalizeWeights, weightSum } from './scoring';

describe('score weight helpers', () => {
  it('keeps default weights normalized for the dashboard sliders', () => {
    expect(weightSum(defaultWeights)).toBeCloseTo(1, 5);
  });

  it('normalizes edited weights without losing metric keys', () => {
    const weights = normalizeWeights({
      sharpness_score: 4,
      significance_score: 2,
      artifact_suppression_score: 2,
      structure_score: 1,
      detail_score: 1,
    });

    expect(weightSum(weights)).toBeCloseTo(1, 5);
    expect(weights.sharpness_score).toBeCloseTo(0.4, 5);
    expect(Object.keys(weights)).toEqual(Object.keys(defaultWeights));
  });
});
