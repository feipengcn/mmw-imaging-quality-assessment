import { describe, expect, it } from 'vitest';
import { histogramAreaPath, histogramPath } from './histogram';

describe('histogramPath', () => {
  it('creates a stable svg path scaled to the requested box', () => {
    const path = histogramPath([0, 2, 4, 2], 100, 40);

    expect(path).toBe('M 0 40 L 33.33 20 L 66.67 0 L 100 20');
  });

  it('handles empty and flat histograms without NaN values', () => {
    expect(histogramPath([], 100, 40)).toBe('');
    expect(histogramPath([3, 3, 3], 90, 30)).toBe('M 0 0 L 45 0 L 90 0');
  });

  it('can log-scale dominant dark bins so smaller peaks remain visible', () => {
    const path = histogramPath([10000, 100, 0], 100, 40, 'log');

    expect(path).toBe('M 0 0 L 50 19.96 L 100 40');
  });

  it('creates a closed area path for filled histogram previews', () => {
    const path = histogramAreaPath([0, 2, 4, 2], 100, 40);

    expect(path).toBe('M 0 40 L 33.33 20 L 66.67 0 L 100 20 L 100 40 L 0 40 Z');
  });
});
