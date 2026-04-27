import { describe, expect, it } from 'vitest';
import {
  defaultSubjectiveScores,
  getCompletedSubjectiveCount,
  getSubjectiveAverage,
  isSubjectiveRatingComplete,
} from './subjectiveRating';

describe('subjective rating helpers', () => {
  it('starts with empty dimension scores', () => {
    expect(defaultSubjectiveScores()).toEqual({
      contour_clarity: null,
      structure_integrity: null,
      background_cleanliness: null,
      artifact_acceptability: null,
      practical_usability: null,
    });
  });

  it('calculates the average from completed dimensions only', () => {
    const scores = {
      contour_clarity: 5,
      structure_integrity: 4,
      background_cleanliness: null,
      artifact_acceptability: 3,
      practical_usability: null,
    };

    expect(getCompletedSubjectiveCount(scores)).toBe(3);
    expect(getSubjectiveAverage(scores)).toBe(4);
    expect(isSubjectiveRatingComplete(scores)).toBe(false);
  });

  it('detects complete five-dimension ratings', () => {
    const scores = {
      contour_clarity: 5,
      structure_integrity: 4,
      background_cleanliness: 3,
      artifact_acceptability: 2,
      practical_usability: 1,
    };

    expect(getCompletedSubjectiveCount(scores)).toBe(5);
    expect(getSubjectiveAverage(scores)).toBe(3);
    expect(isSubjectiveRatingComplete(scores)).toBe(true);
  });
});
