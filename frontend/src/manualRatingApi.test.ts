import { afterEach, describe, expect, it, vi } from 'vitest';

import { fetchManualTasks, loginManualUser } from './manualRatingApi';

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
});
