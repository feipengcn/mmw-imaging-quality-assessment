import { afterEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
(globalThis as typeof globalThis & { ResizeObserver?: typeof ResizeObserver }).ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as typeof ResizeObserver;

describe('App mmWave detail panel visibility', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('shows a radar-based quality section and no subjective rating area before an image is calculated', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          images: [],
          weights: {
            sharpness_score: 0.2,
            significance_score: 0.2,
            artifact_suppression_score: 0.15,
            structure_score: 0.1,
            detail_score: 0.25,
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

    expect(document.body.textContent).toContain('质量雷达图');
    expect(document.body.textContent).toContain('样本列表');
    expect(document.body.textContent).toContain('AOI');
    expect(document.body.textContent).toContain('伪影溢出带');
    expect(document.body.textContent).toContain('饱和条纹区');
    expect(document.body.textContent).not.toContain('人工打分');
  });

  it('uses the left sample list as the only ranked browsing surface', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          images: [
            createImageRecord('image-1', 'sample-b.png', 82.5),
            createImageRecord('image-2', 'sample-a.png', 91.2),
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

    expect(document.body.textContent).not.toContain('样本排名');
    expect(document.body.textContent).toContain('样本列表');
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
            images: [createImageRecord('image-1', 'sample.png', 82.5)],
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

    const resetButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent?.includes('清空数据'));
    expect(resetButton).toBeTruthy();

    await act(async () => {
      resetButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(confirmMock).toHaveBeenCalledWith('确定清空所有已导入图像、掩膜和评分记录吗？');
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

    const secondRow = Array.from(document.querySelectorAll('.import-file-row')).find((row) => row.textContent?.includes('example_pic/1093_front.png'));
    expect(secondRow).toBeTruthy();

    await act(async () => {
      secondRow?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(document.querySelector('.visual-panel h2')?.textContent).toBe('example_pic/1093_front.png');
  });

  it('deletes a ranked image on demand', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      if (input === '/api/images/image-2' && init?.method === 'DELETE') {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              images: [createImageRecord('image-1', 'sample-a.png', 82.5)],
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({
            images: [
              createImageRecord('image-1', 'sample-a.png', 82.5),
              createImageRecord('image-2', 'sample-b.png', 76.2),
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

    const deleteButton = document.querySelector('[aria-label="删除 sample-b.png"]');
    expect(deleteButton).toBeTruthy();

    await act(async () => {
      deleteButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(confirmMock).toHaveBeenCalledWith('确定删除 sample-b.png 吗？');
    expect(fetchMock).toHaveBeenCalledWith('/api/images/image-2', { method: 'DELETE' });
    expect(document.querySelector('[aria-label="删除 sample-b.png"]')).toBeNull();
    expect(document.body.textContent).toContain('sample-a.png');
    expect(document.body.textContent).toContain('已删除 sample-b.png。');
  });

  it('shows list sort controls and a settings entry in the top bar', async () => {
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
            createImageRecord('image-1', 'a-sample.png', 82.5),
            createImageRecord('image-2', 'b-sample.png', 91.2),
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

    const firstFile = createImportFile('a-sample.png', 'z-dir/a-sample.png');
    const secondFile = createImportFile('b-sample.png', 'a-dir/b-sample.png');
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    Object.defineProperty(input, 'files', { value: [firstFile, secondFile], configurable: true });

    await act(async () => {
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });

    const scoreSortButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent?.includes('按得分'));
    const nameSortButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent?.includes('按名称'));
    const settingsButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent?.includes('设置'));
    const summaryValues = Array.from(document.querySelectorAll('.summary-strip .metric-tile strong'));
    const rankedTileTitles = Array.from(document.querySelectorAll('.ranking-tiles .image-tile strong'));

    expect(document.body.textContent).toContain('按得分');
    expect(document.body.textContent).toContain('按名称');
    expect(document.body.textContent).toContain('设置');
    expect(scoreSortButton?.className).toContain('active');
    expect(nameSortButton?.className).not.toContain('active');
    expect(summaryValues[2]?.textContent).toBe('91.20');
    expect(rankedTileTitles[0]?.textContent).toBe('b-sample.png');

    await act(async () => {
      settingsButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(document.getElementById('topbar-settings-panel')).toBeTruthy();
    expect(document.body.textContent).toContain('聚焦当前样本');

    await act(async () => {
      nameSortButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    const rankedTileTitlesAfterNameSort = Array.from(document.querySelectorAll('.ranking-tiles .image-tile strong'));
    expect(nameSortButton?.className).toContain('active');
    expect(scoreSortButton?.className).not.toContain('active');
    expect(summaryValues[2]?.textContent).toBe('91.20');
    expect(rankedTileTitlesAfterNameSort[0]?.textContent).toBe('a-sample.png');
  });

  it('focuses the ranked list on the current sample when enabled', async () => {
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
            createImageRecord('image-1', 'dup-sample.png', 91.2),
            createImageRecord('image-2', 'other-sample.png', 82.5),
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

    const firstFile = createImportFile('dup-sample.png', 'first-dir/dup-sample.png');
    const secondFile = createImportFile('dup-sample.png', 'second-dir/dup-sample.png');
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    Object.defineProperty(input, 'files', { value: [firstFile, secondFile], configurable: true });

    await act(async () => {
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });

    const settingsButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent?.includes('设置'));
    expect(document.querySelectorAll('.ranking-tiles .image-tile')).toHaveLength(2);

    await act(async () => {
      settingsButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    const focusCurrentOnlyInput = document.querySelector('#topbar-settings-panel input[type="checkbox"]') as HTMLInputElement;
    expect(focusCurrentOnlyInput).toBeTruthy();

    await act(async () => {
      focusCurrentOnlyInput.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    const rankedTileTitles = Array.from(document.querySelectorAll('.ranking-tiles .image-tile strong'));
    expect(document.querySelectorAll('.ranking-tiles .image-tile')).toHaveLength(1);
    expect(rankedTileTitles[0]?.textContent).toBe('dup-sample.png');
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
    view: 'unknown',
    view_confidence: undefined,
    metrics: {
      tenengrad_variance: 1500,
      edge_rise_distance: 2.4,
      cnr: 6.8,
      leakage_ratio: 0.08,
      background_local_std: 4.0,
      component_count: 1,
      solidity: 0.95,
      saturation_ratio: 0.01,
      roi_entropy: 6.1,
      pai: 0.03,
      body_area_ratio: 0.18,
    },
    metric_scores: {
      tenengrad_variance: 80,
      edge_rise_distance: 92,
      cnr: 81,
      leakage_ratio: 96,
      background_local_std: 97,
      component_count: 100,
      solidity: 97,
      saturation_ratio: 100,
      roi_entropy: 90,
      pai: 100,
      body_area_ratio: 86,
    },
    metric_score_max: 100,
    normalized_metrics: {
      sharpness_score: 0.82,
      significance_score: 0.78,
      artifact_suppression_score: 0.87,
      structure_score: 0.9,
      detail_score: 0.76,
    },
    penalty_flags: {
      saturation: false,
      pai: false,
    },
    valid_sample: true,
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
    quality_score: qualityScore,
    image_url: `/uploads/${id}`,
    mask_url: `/masks/${id}`,
    overlay_urls: {
      aoi: `/overlays/${id}/aoi`,
      leakage: `/overlays/${id}/leakage`,
      stripe: `/overlays/${id}/stripe`,
    },
    uploaded_at: '2026-04-27T00:00:00Z',
  };
}

function createImportFile(name: string, displayPath: string) {
  const file = new File(['image'], name, { type: 'image/png', lastModified: 1 });
  Object.defineProperty(file, 'webkitRelativePath', { value: displayPath, configurable: true });
  return file;
}
