import { afterEach, describe, expect, it, vi } from 'vitest';

import { fetchManualTasks, fetchReviewerTaskImages, loginManualUser, uploadManualDataset } from './manualRatingApi';

describe('manual rating api', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('logs in and fetches tasks with credentials', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            user: {
              id: 'u1',
              username: 'admin',
              display_name: 'Admin',
              role: 'admin',
              active: true,
            },
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ tasks: [] }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );

    await loginManualUser('admin', 'secret123');
    await fetchManualTasks();

    expect(globalThis.fetch).toHaveBeenNthCalledWith(
      1,
      '/api/auth/login',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username: 'admin', password: 'secret123' }),
      }),
    );
    expect(globalThis.fetch).toHaveBeenNthCalledWith(
      2,
      '/api/manual/tasks',
      expect.objectContaining({ credentials: 'include' }),
    );
  });

  it('uploads dataset files with optional metadata', async () => {
    const calls: Array<[RequestInfo | URL, RequestInit | undefined]> = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      calls.push([input, init]);
      return Promise.resolve(
        new Response(
          JSON.stringify({
            dataset: {
              id: 'd1',
              name: '数据集',
              source: 'folder-a',
              source_label: '现场采集',
              batch_label: '第1批',
              note_label: '夜班',
              experiment_group: 'manual-rating',
              batch: 'manual-upload',
              created_by: 'u1',
              created_at: '2026-05-07T00:00:00Z',
              image_ids: ['img-1'],
              image_count: 1,
            },
            imported: 1,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      );
    });

    const file = new File(['abc'], 'a.png', { type: 'image/png' });
    Object.defineProperty(file, 'webkitRelativePath', { value: 'folder-a/a.png' });

    await uploadManualDataset('数据集', [file], {
      source_label: '现场采集',
      batch_label: '第1批',
      note_label: '夜班',
    });

    expect(calls).toHaveLength(1);
    expect(calls[0][0]).toBe('/api/manual/datasets/upload');
    expect(calls[0][1]).toEqual(expect.objectContaining({ method: 'POST', credentials: 'include' }));
    const form = calls[0][1]?.body as FormData;
    expect(form.get('name')).toBe('数据集');
    expect(form.get('source_label')).toBe('现场采集');
    expect(form.get('batch_label')).toBe('第1批');
    expect(form.get('note_label')).toBe('夜班');
    expect(form.getAll('files')).toHaveLength(1);
  });

  it('fetches reviewer task image list with credentials', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ images: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    await fetchReviewerTaskImages('task-1');

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/manual/tasks/task-1/images',
      expect.objectContaining({ credentials: 'include' }),
    );
  });
});
