import type {
  ManualDataset,
  ManualRatingForm,
  ManualTaskListItem,
  ManualTaskSummary,
  ManualUser,
  ReviewerImageDetail,
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

export async function logoutManualUser(): Promise<{ ok: boolean }> {
  const response = await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
  return ensureOk(response);
}

export async function fetchManualUsers(): Promise<{ users: ManualUser[] }> {
  const response = await fetch('/api/manual/users', { credentials: 'include' });
  return ensureOk(response);
}

export async function fetchManualDatasets(): Promise<{ datasets: ManualDataset[] }> {
  const response = await fetch('/api/manual/datasets', { credentials: 'include' });
  return ensureOk(response);
}

export async function createManualDataset(payload: {
  name: string;
  image_ids: string[];
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
