export type MetricKey =
  | 'sharpness_score'
  | 'significance_score'
  | 'artifact_suppression_score'
  | 'structure_score'
  | 'detail_score';

export type MetricMap = Record<string, number>;
export type Weights = Record<MetricKey, number>;

export interface ImageRecord {
  id: string;
  filename: string;
  experiment_group: string;
  algorithm: string;
  parameters: string;
  batch: string;
  view?: 'front' | 'back' | 'unknown' | string;
  view_confidence?: number;
  metrics: MetricMap;
  metric_scores?: MetricMap;
  metric_score_max?: number;
  normalized_metrics?: MetricMap;
  features?: ImageFeatures;
  overlay_urls?: {
    aoi: string;
    leakage: string;
    stripe: string;
  };
  penalty_flags?: {
    saturation?: boolean;
    pai?: boolean;
  };
  valid_sample?: boolean;
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
