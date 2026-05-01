import { describe, expect, it, vi } from 'vitest';
import { uploadImagesWithProgress } from './api';

describe('api progress helpers', () => {
  it('reports streamed import progress events from newline-delimited JSON', async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('{"type":"progress","completed":1,"total":2,"filename":"a.png"}\n'));
        controller.enqueue(encoder.encode('{"type":"progress","completed":2,"total":2,"filename":"b.png"}\n'));
        controller.enqueue(encoder.encode('{"type":"complete","imported":2,"images":[]}\n'));
        controller.close();
      },
    });
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: { 'Content-Type': 'application/x-ndjson' },
      }),
    );
    const onProgress = vi.fn();

    const result = await uploadImagesWithProgress(new FormData(), onProgress);

    expect(globalThis.fetch).toHaveBeenCalledWith('/api/import/progress', { method: 'POST', body: expect.any(FormData) });
    expect(onProgress).toHaveBeenNthCalledWith(1, { completed: 1, total: 2, filename: 'a.png' });
    expect(onProgress).toHaveBeenNthCalledWith(2, { completed: 2, total: 2, filename: 'b.png' });
    expect(result.imported).toBe(2);
  });
});
