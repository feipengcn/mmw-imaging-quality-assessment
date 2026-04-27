import type { SubjectiveScoreKey, SubjectiveScores } from './types';

export const subjectiveScoreKeys: SubjectiveScoreKey[] = [
  'contour_clarity',
  'structure_integrity',
  'background_cleanliness',
  'artifact_acceptability',
  'practical_usability',
];

export const subjectiveScoreLabels: Record<SubjectiveScoreKey, string> = {
  contour_clarity: '人体轮廓清晰度',
  structure_integrity: '结构完整性',
  background_cleanliness: '背景干扰控制',
  artifact_acceptability: '伪影可接受度',
  practical_usability: '识别可用性',
};

export function defaultSubjectiveScores(): SubjectiveScores {
  return {
    contour_clarity: null,
    structure_integrity: null,
    background_cleanliness: null,
    artifact_acceptability: null,
    practical_usability: null,
  };
}

export function getCompletedSubjectiveCount(scores: SubjectiveScores): number {
  return subjectiveScoreKeys.filter((key) => scores[key] !== null && scores[key] !== undefined).length;
}

export function getSubjectiveAverage(scores: SubjectiveScores): number | null {
  const values = subjectiveScoreKeys
    .map((key) => scores[key])
    .filter((value): value is number => value !== null && value !== undefined);
  if (!values.length) return null;
  return Number((values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(2));
}

export function isSubjectiveRatingComplete(scores: SubjectiveScores): boolean {
  return getCompletedSubjectiveCount(scores) === subjectiveScoreKeys.length;
}
