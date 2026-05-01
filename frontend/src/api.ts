import type { ImageResponse, Weights } from './types';

const jsonHeaders = { 'Content-Type': 'application/json' };

export async function fetchImages(): Promise<ImageResponse> {
  const response = await fetch('/api/images');
  return ensureOk(response);
}

export async function uploadImages(form: FormData): Promise<ImageResponse & { imported: number }> {
  const response = await fetch('/api/import', { method: 'POST', body: form });
  return ensureOk(response);
}

export type ImportProgress = {
  completed: number;
  total: number;
  filename: string;
};

type ImportProgressEvent =
  | ({ type: 'progress' } & ImportProgress)
  | ({ type: 'complete'; imported: number } & ImageResponse);

export async function uploadImagesWithProgress(
  form: FormData,
  onProgress: (progress: ImportProgress) => void,
): Promise<ImageResponse & { imported: number }> {
  const response = await fetch('/api/import/progress', { method: 'POST', body: form });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  if (!response.body) {
    return response.json();
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let complete: (ImageResponse & { imported: number }) | null = null;

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const event = JSON.parse(trimmed) as ImportProgressEvent;
      if (event.type === 'progress') {
        onProgress({ completed: event.completed, total: event.total, filename: event.filename });
      } else {
        complete = { imported: event.imported, images: event.images, weights: event.weights };
      }
    }

    if (done) break;
  }

  if (buffer.trim()) {
    const event = JSON.parse(buffer.trim()) as ImportProgressEvent;
    if (event.type === 'progress') {
      onProgress({ completed: event.completed, total: event.total, filename: event.filename });
    } else {
      complete = { imported: event.imported, images: event.images, weights: event.weights };
    }
  }

  if (!complete) {
    throw new Error('导入计算未返回完成事件。');
  }
  return complete;
}

export async function rescoreImages(weights: Weights): Promise<ImageResponse> {
  const response = await fetch('/api/images/score', {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ weights }),
  });
  return ensureOk(response);
}

export async function resetImages(): Promise<ImageResponse> {
  const response = await fetch('/api/images', { method: 'DELETE' });
  return ensureOk(response);
}

export async function deleteImage(imageId: string): Promise<ImageResponse> {
  const response = await fetch(`/api/images/${imageId}`, { method: 'DELETE' });
  return ensureOk(response);
}

async function ensureOk<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  return response.json();
}
