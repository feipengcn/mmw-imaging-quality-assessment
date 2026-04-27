import { afterEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

describe('App detail panel visibility', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('shows the subjective rating area even before an image is calculated', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          images: [],
          weights: {
            sharpness: 0.2,
            local_contrast: 0.15,
            snr: 0.15,
            structure_continuity: 0.15,
            artifact_strength: 0.12,
            body_area_ratio: 0.08,
            background_noise: 0.1,
            subjective_rating: 0.05,
          },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const rootElement = document.createElement('div');
    document.body.appendChild(rootElement);

    await act(async () => {
      createRoot(rootElement).render(<App />);
    });

    expect(document.body.textContent).toContain('人工分项评分');
  });

  it('removes metadata inputs from the import sidebar', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ images: [], weights: {} }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const rootElement = document.createElement('div');
    document.body.appendChild(rootElement);

    await act(async () => {
      createRoot(rootElement).render(<App />);
    });

    expect(document.body.textContent).not.toContain('实验组');
    expect(document.body.textContent).not.toContain('算法');
    expect(document.body.textContent).not.toContain('参数');
    expect(document.body.textContent).not.toContain('批次');
  });

  it('shows a discoverable reset action that clears imported images after confirmation', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      if (input === '/api/images' && init?.method === 'DELETE') {
        return Promise.resolve(
          new Response(JSON.stringify({ images: [] }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({
            images: [
              {
                id: 'image-1',
                filename: 'sample.png',
                experiment_group: 'default',
                algorithm: 'unknown',
                parameters: '',
                batch: '',
                metrics: {},
                normalized_metrics: {},
                subjective_scores: {},
                subjective_rating: null,
                subjective_rating_complete: false,
                notes: '',
                quality_score: 82.5,
                image_url: '/uploads/image-1',
                mask_url: '/masks/image-1',
                uploaded_at: '2026-04-27T00:00:00Z',
              },
            ],
            weights: {},
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      );
    });
    const confirmMock = vi.spyOn(globalThis, 'confirm').mockReturnValue(true);
    const rootElement = document.createElement('div');
    document.body.appendChild(rootElement);

    await act(async () => {
      createRoot(rootElement).render(<App />);
    });

    const resetButton = Array.from(document.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('清空数据'),
    );
    expect(resetButton).toBeTruthy();

    await act(async () => {
      resetButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(confirmMock).toHaveBeenCalledWith('确定清空所有已导入图片、ROI mask 和评分记录吗？');
    expect(fetchMock).toHaveBeenCalledWith('/api/images', { method: 'DELETE' });
    expect(document.body.textContent).toContain('等待计算图像');
  });

  it('switches the observation image when a calculated file is clicked in the pending file list', async () => {
    Object.defineProperty(globalThis.URL, 'createObjectURL', {
      value: vi.fn(() => 'blob:preview'),
      configurable: true,
    });
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', {
      value: vi.fn(),
      configurable: true,
    });
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          images: [
            createImageRecord('image-1', 'example_pic/1000_front.png', 90),
            createImageRecord('image-2', 'example_pic/1093_front.png', 75),
          ],
          weights: {},
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const rootElement = document.createElement('div');
    document.body.appendChild(rootElement);

    await act(async () => {
      createRoot(rootElement).render(<App />);
    });

    const firstFile = createImportFile('1000_front.png', 'example_pic/1000_front.png');
    const secondFile = createImportFile('1093_front.png', 'example_pic/1093_front.png');
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    Object.defineProperty(input, 'files', { value: [firstFile, secondFile], configurable: true });

    await act(async () => {
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });

    expect(document.querySelector('.visual-panel h2')?.textContent).toBe('example_pic/1000_front.png');

    const secondRow = Array.from(document.querySelectorAll('.import-file-row')).find((row) =>
      row.textContent?.includes('example_pic/1093_front.png'),
    );
    expect(secondRow).toBeTruthy();

    await act(async () => {
      secondRow?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(document.querySelector('.visual-panel h2')?.textContent).toBe('example_pic/1093_front.png');
  });
});

function createImageRecord(id: string, filename: string, qualityScore: number) {
  return {
    id,
    filename,
    experiment_group: 'default',
    algorithm: 'unknown',
    parameters: '',
    batch: '',
    metrics: {
      sharpness: 1,
      local_contrast: 1,
      snr: 1,
      structure_continuity: 1,
      artifact_strength: 1,
      body_area_ratio: 1,
      background_noise: 1,
    },
    normalized_metrics: {
      sharpness: 0.5,
      local_contrast: 0.5,
      snr: 0.5,
      structure_continuity: 0.5,
      artifact_strength: 0.5,
      body_area_ratio: 0.5,
      background_noise: 0.5,
    },
    features: {
      width: 8,
      height: 8,
      mode: 'RGB',
      histograms: {
        gray: [1, 2, 3],
        red: [1, 2, 3],
        green: [1, 2, 3],
        blue: [1, 2, 3],
      },
    },
    subjective_scores: {},
    subjective_rating: null,
    subjective_rating_complete: false,
    notes: '',
    quality_score: qualityScore,
    image_url: `/uploads/${id}`,
    mask_url: `/masks/${id}`,
    uploaded_at: '2026-04-27T00:00:00Z',
  };
}

function createImportFile(name: string, displayPath: string) {
  const file = new File(['image'], name, { type: 'image/png', lastModified: 1 });
  Object.defineProperty(file, 'webkitRelativePath', { value: displayPath, configurable: true });
  return file;
}
