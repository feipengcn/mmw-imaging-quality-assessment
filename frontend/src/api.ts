import type { ImageResponse, SubjectiveScores, Weights } from './types';

const jsonHeaders = { 'Content-Type': 'application/json' };

export async function fetchImages(): Promise<ImageResponse> {
  const response = await fetch('/api/images');
  return ensureOk(response);
}

export async function uploadImages(form: FormData): Promise<ImageResponse & { imported: number }> {
  const response = await fetch('/api/import', { method: 'POST', body: form });
  return ensureOk(response);
}

export async function rescoreImages(weights: Weights): Promise<ImageResponse> {
  const response = await fetch('/api/images/score', {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ weights }),
  });
  return ensureOk(response);
}

export async function saveRating(
  imageId: string,
  subjectiveScores: SubjectiveScores,
  notes: string,
): Promise<ImageResponse> {
  const response = await fetch(`/api/images/${imageId}/rating`, {
    method: 'PATCH',
    headers: jsonHeaders,
    body: JSON.stringify({ subjective_scores: subjectiveScores, notes }),
  });
  return ensureOk(response);
}

export async function resetImages(): Promise<ImageResponse> {
  const response = await fetch('/api/images', { method: 'DELETE' });
  return ensureOk(response);
}

async function ensureOk<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  return response.json();
}
