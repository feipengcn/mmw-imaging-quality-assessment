import { describe, expect, it } from 'vitest';
import { defaultWeights, normalizeWeights, weightSum } from './scoring';

describe('score weight helpers', () => {
  it('keeps default weights normalized for the dashboard sliders', () => {
    expect(weightSum(defaultWeights)).toBeCloseTo(1, 5);
  });

  it('normalizes edited weights without losing metric keys', () => {
    const weights = normalizeWeights({
      sharpness: 4,
      local_contrast: 2,
      snr: 2,
      structure_continuity: 1,
      artifact_strength: 1,
      body_area_ratio: 0,
      background_noise: 0,
      subjective_rating: 0,
    });

    expect(weightSum(weights)).toBeCloseTo(1, 5);
    expect(weights.sharpness).toBeCloseTo(0.4, 5);
    expect(Object.keys(weights)).toEqual(Object.keys(defaultWeights));
  });
});
