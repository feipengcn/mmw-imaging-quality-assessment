import type {
  ManualAdminImageDetail,
  ManualDataset,
  ManualRatingForm,
  ManualTaskListItem,
  ManualTaskSummary,
  ManualUser,
  ReviewerImageDetail,
  ReviewerTaskImageListItem,
} from './manualRatingTypes';

const jsonHeaders = { 'Content-Type': 'application/json' };

async function ensureOk<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function loginManualUser(username: string, password: string): Promise<{ user: ManualUser }> {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: jsonHeaders,
    credentials: 'include',
    body: JSON.stringify({ username, password }),
  });
  return ensureOk(response);
}

export async function fetchCurrentManualUser(): Promise<{ user: ManualUser }> {
  const response = await fetch('/api/auth/me', { credentials: 'include' });
  return ensureOk(response);
}

export async function fetchManualBootstrapStatus(): Promise<{ needs_setup: boolean }> {
  const response = await fetch('/api/auth/bootstrap-status', { credentials: 'include' });
  return ensureOk(response);
}

export async function logoutManualUser(): Promise<{ ok: boolean }> {
  const response = await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
  return ensureOk(response);
}

export async function fetchManualUsers(): Promise<{ users: ManualUser[] }> {
  const response = await fetch('/api/manual/users', { credentials: 'include' });
  return ensureOk(response);
}

export async function createManualUser(payload: {
  username: string;
  display_name: string;
  password: string;
  role: 'admin' | 'reviewer';
  active?: boolean;
}): Promise<{ user: ManualUser }> {
  const response = await fetch('/api/manual/users', {
    method: 'POST',
    headers: jsonHeaders,
    credentials: 'include',
    body: JSON.stringify(payload),
  });
  return ensureOk(response);
}

export async function fetchManualDatasets(): Promise<{ datasets: ManualDataset[] }> {
  const response = await fetch('/api/manual/datasets', { credentials: 'include' });
  return ensureOk(response);
}

export async function createManualDataset(payload: {
  name: string;
  image_ids: string[];
  source_label?: string;
  batch_label?: string;
  note_label?: string;
  experiment_group?: string;
  batch?: string;
}): Promise<{ dataset: ManualDataset }> {
  const response = await fetch('/api/manual/datasets', {
    method: 'POST',
    headers: jsonHeaders,
    credentials: 'include',
    body: JSON.stringify(payload),
  });
  return ensureOk(response);
}

export async function uploadManualDataset(
  name: string,
  files: File[],
  metadata?: {
    source_label?: string;
    batch_label?: string;
    note_label?: string;
  },
): Promise<{ dataset: ManualDataset; imported: number }> {
  const form = new FormData();
  form.append('name', name);
  if (metadata?.source_label) form.append('source_label', metadata.source_label);
  if (metadata?.batch_label) form.append('batch_label', metadata.batch_label);
  if (metadata?.note_label) form.append('note_label', metadata.note_label);
  files.forEach((file) => form.append('files', file, file.webkitRelativePath || file.name));
  const response = await fetch('/api/manual/datasets/upload', {
    method: 'POST',
    credentials: 'include',
    body: form,
  });
  return ensureOk(response);
}

export async function createManualTask(payload: {
  dataset_id: string;
  name: string;
  description?: string;
  reviewer_ids: string[];
}): Promise<{ task: ManualTaskListItem }> {
  const response = await fetch('/api/manual/tasks', {
    method: 'POST',
    headers: jsonHeaders,
    credentials: 'include',
    body: JSON.stringify(payload),
  });
  return ensureOk(response);
}

export async function fetchManualTasks(): Promise<{ tasks: ManualTaskListItem[] }> {
  const response = await fetch('/api/manual/tasks', { credentials: 'include' });
  return ensureOk(response);
}

export async function fetchManualTaskSummary(taskId: string): Promise<{ summary: ManualTaskSummary }> {
  const response = await fetch(`/api/manual/tasks/${taskId}/summary`, { credentials: 'include' });
  return ensureOk(response);
}

export async function fetchManualAdminImageDetail(
  taskId: string,
  imageId: string,
): Promise<{ image: ManualAdminImageDetail }> {
  const response = await fetch(`/api/manual/tasks/${taskId}/images/${imageId}/admin-detail`, {
    credentials: 'include',
  });
  return ensureOk(response);
}

export async function fetchNextManualImage(taskId: string): Promise<{ image_id: string | null }> {
  const response = await fetch(`/api/manual/tasks/${taskId}/next`, { credentials: 'include' });
  return ensureOk(response);
}

export async function fetchReviewerImageDetail(
  taskId: string,
  imageId: string,
): Promise<{ image: ReviewerImageDetail }> {
  const response = await fetch(`/api/manual/tasks/${taskId}/images/${imageId}`, {
    credentials: 'include',
  });
  return ensureOk(response);
}

export async function fetchReviewerTaskImages(taskId: string): Promise<{ images: ReviewerTaskImageListItem[] }> {
  const response = await fetch(`/api/manual/tasks/${taskId}/images`, { credentials: 'include' });
  return ensureOk(response);
}

export async function submitManualRating(
  taskId: string,
  imageId: string,
  payload: ManualRatingForm,
): Promise<{ rating: ReviewerImageDetail['rating'] }> {
  const response = await fetch(`/api/manual/tasks/${taskId}/images/${imageId}/rating`, {
    method: 'PUT',
    headers: jsonHeaders,
    credentials: 'include',
    body: JSON.stringify(payload),
  });
  return ensureOk(response);
}
