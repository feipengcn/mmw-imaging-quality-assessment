export type ManualRole = 'admin' | 'reviewer';

export interface ManualUser {
  id: string;
  username: string;
  display_name: string;
  role: ManualRole;
  active: boolean;
}

export interface ManualTaskListItem {
  id: string;
  dataset_id: string;
  name: string;
  description: string;
  status: 'draft' | 'active' | 'closed';
  created_by: string;
  created_at: string;
  dataset_name: string;
  total_images: number;
  completed_images: number;
  reviewer_count: number;
}

export interface ManualDataset {
  id: string;
  name: string;
  source: string;
  experiment_group: string;
  batch: string;
  created_by: string;
  created_at: string;
  image_ids: string[];
}

export interface ManualRatingForm {
  sharpness_score: number;
  significance_score: number;
  artifact_suppression_score: number;
  structure_score: number;
  detail_score: number;
  comment: string;
}

export interface ReviewerImageDetail {
  task_id: string;
  image_id: string;
  filename: string;
  image_url: string;
  progress: {
    completed: number;
    total: number;
  };
  rating: (ManualRatingForm & {
    id?: string;
    reviewer_id?: string;
    created_at?: string;
    updated_at?: string;
  }) | null;
}

export interface ManualTaskSummary {
  task_id: string;
  task_name: string;
  dataset_name: string;
  progress: {
    completed: number;
    total: number;
  };
  rating_count: number;
  reviewer_count: number;
  rated_images: number;
}
