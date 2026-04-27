export type MetricKey =
  | 'sharpness'
  | 'local_contrast'
  | 'snr'
  | 'structure_continuity'
  | 'artifact_strength'
  | 'body_area_ratio'
  | 'background_noise'
  | 'subjective_rating';

export type MetricMap = Record<string, number>;
export type Weights = Record<MetricKey, number>;
export type SubjectiveScoreKey =
  | 'contour_clarity'
  | 'structure_integrity'
  | 'background_cleanliness'
  | 'artifact_acceptability'
  | 'practical_usability';
export type SubjectiveScores = Record<SubjectiveScoreKey, number | null>;

export interface ImageRecord {
  id: string;
  filename: string;
  experiment_group: string;
  algorithm: string;
  parameters: string;
  batch: string;
  metrics: MetricMap;
  normalized_metrics?: MetricMap;
  features?: ImageFeatures;
  subjective_scores?: SubjectiveScores;
  subjective_rating: number | null;
  subjective_rating_complete?: boolean;
  notes: string;
  quality_score: number;
  image_url: string;
  mask_url: string;
  uploaded_at: string;
}

export interface ImageFeatures {
  width: number;
  height: number;
  mode: string;
  histograms: {
    gray: number[];
    red: number[];
    green: number[];
    blue: number[];
  };
}

export interface ImageResponse {
  images: ImageRecord[];
  weights?: Weights;
}
