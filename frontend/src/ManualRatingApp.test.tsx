import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from './App';
import ManualRatingApp from './ManualRatingApp';

describe('人工评分模块', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('切换到人工评分后显示登录表单', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      if (input === '/api/auth/bootstrap-status') {
        return Promise.resolve(new Response(JSON.stringify({ needs_setup: false }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      if (input === '/api/auth/me') {
        return Promise.resolve(new Response('not authenticated', { status: 401 }));
      }
      if (input === '/api/images') {
        return Promise.resolve(
          new Response(JSON.stringify({ images: [], weights: {} }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }
      return Promise.resolve(
        new Response(JSON.stringify({ tasks: [] }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    });

    const rootElement = document.createElement('div');
    document.body.appendChild(rootElement);

    await act(async () => {
      createRoot(rootElement).render(<App />);
    });

    const manualButton = Array.from(document.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('人工评分'),
    );

    await act(async () => {
      manualButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(document.body.textContent).toContain('人工评分登录');
    expect(document.body.textContent).toContain('用户名');
    expect(document.body.textContent).toContain('密码');
  });

  it('管理员登录后显示数据集、看图员、任务和图片明细区域', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      if (input === '/api/auth/bootstrap-status') {
        return Promise.resolve(new Response(JSON.stringify({ needs_setup: false }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      if (input === '/api/auth/me') {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              user: { id: 'u1', username: 'admin', display_name: '管理员', role: 'admin', active: true },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }
      if (input === '/api/manual/tasks') {
        return Promise.resolve(
          new Response(JSON.stringify({
            tasks: [{
              id: 'task-1',
              dataset_id: 'dataset-1',
              name: '任务 A',
              description: '',
              status: 'active',
              created_by: 'u1',
              created_at: '2026-05-07T00:00:00Z',
              dataset_name: '数据集 A',
              total_images: 12,
              completed_images: 4,
              reviewer_count: 2,
            }],
          }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }
      if (input === '/api/manual/users') {
        return Promise.resolve(
          new Response(JSON.stringify({
            users: [
              { id: 'u2', username: 'reviewer1', display_name: '看图员甲', role: 'reviewer', active: true },
              { id: 'u3', username: 'reviewer2', display_name: '看图员乙', role: 'reviewer', active: true },
            ],
          }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }
      if (input === '/api/manual/datasets') {
        return Promise.resolve(
          new Response(JSON.stringify({
            datasets: [{
              id: 'dataset-1',
              name: '数据集 A',
              source: 'session-1/front',
              source_label: '现场采集',
              batch_label: '第1批',
              note_label: '',
              experiment_group: 'manual-rating',
              batch: 'manual-upload',
              created_by: 'u1',
              created_at: '2026-05-07T00:00:00Z',
              image_ids: ['img-1', 'img-2'],
              image_count: 2,
            }],
          }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }
      if (input === '/api/manual/tasks/task-1/summary') {
        return Promise.resolve(
          new Response(JSON.stringify({
            summary: {
              task_id: 'task-1',
              task_name: '任务 A',
              dataset_name: '数据集 A',
              progress: { completed: 4, total: 12 },
              rating_count: 8,
              reviewer_count: 2,
              rated_images: 4,
              reviewer_progress: [
                {
                  reviewer_id: 'u2',
                  reviewer_username: 'reviewer1',
                  reviewer_display_name: '看图员甲',
                  weight: 1,
                  completed_images: 3,
                  total_images: 12,
                },
              ],
              image_summaries: [
                {
                  image_id: 'img-1',
                  sort_order: 0,
                  rating_count: 2,
                  average_overall_score: 7.1,
                  weighted_overall_score: 7.3,
                },
              ],
            },
          }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }
      if (input === '/api/manual/tasks/task-1/images/img-1/admin-detail') {
        return Promise.resolve(
          new Response(JSON.stringify({
            image: {
              task_id: 'task-1',
              image_id: 'img-1',
              sort_order: 0,
              filename: 'img-1.png',
              image_url: '/uploads/img-1',
              ratings: [
                {
                  id: 'r1',
                  task_id: 'task-1',
                  image_id: 'img-1',
                  reviewer_id: 'u2',
                  reviewer_username: 'reviewer1',
                  reviewer_display_name: '看图员甲',
                  weight: 1,
                  sharpness_score: 8,
                  significance_score: 8,
                  artifact_suppression_score: 7,
                  structure_score: 7,
                  detail_score: 6,
                  comment: '稳定',
                  created_at: '2026-05-07T00:00:00Z',
                  updated_at: '2026-05-07T00:00:00Z',
                  overall_score: 7.2,
                },
              ],
              aggregates: {
                average: {
                  sharpness_score: 8,
                  significance_score: 8,
                  artifact_suppression_score: 7,
                  structure_score: 7,
                  detail_score: 6,
                  overall_score: 7.2,
                },
                weighted: {
                  sharpness_score: 8,
                  significance_score: 8,
                  artifact_suppression_score: 7,
                  structure_score: 7,
                  detail_score: 6,
                  overall_score: 7.2,
                },
              },
            },
          }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }
      return Promise.resolve(new Response('[]', { status: 200 }));
    });

    const rootElement = document.createElement('div');
    document.body.appendChild(rootElement);

    await act(async () => {
      createRoot(rootElement).render(<ManualRatingApp />);
    });

    expect(document.body.textContent).toContain('创建数据集');
    expect(document.body.textContent).toContain('选择本地文件夹');
    expect(document.body.textContent).toContain('已创建看图员');
    expect(document.body.textContent).toContain('任务情况');
    expect(document.body.textContent).toContain('图片评分明细');
    expect(document.body.textContent).toContain('现场采集');
    expect(document.body.textContent).toContain('看图员甲');
    expect(document.body.textContent).toContain('加权均分');
    expect(document.body.textContent).toContain('退出登录');
  });

  it('看图员登录后显示盲评界面', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      if (input === '/api/auth/bootstrap-status') {
        return Promise.resolve(new Response(JSON.stringify({ needs_setup: false }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      if (input === '/api/auth/me') {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              user: { id: 'u2', username: 'reviewer', display_name: '看图员', role: 'reviewer', active: true },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }
      if (input === '/api/manual/tasks') {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              tasks: [
                {
                  id: 'task-1',
                  dataset_id: 'dataset-1',
                  name: '任务 A',
                  description: '',
                  dataset_name: '数据集 A',
                  status: 'active',
                  total_images: 10,
                  completed_images: 2,
                  reviewer_count: 2,
                  created_by: 'u1',
                  created_at: '2026-05-07T00:00:00Z',
                },
              ],
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }
      if (input === '/api/manual/tasks/task-1/next') {
        return Promise.resolve(
          new Response(JSON.stringify({ image_id: 'img-1' }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }
      if (input === '/api/manual/tasks/task-1/images/img-1') {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              image: {
                task_id: 'task-1',
                image_id: 'img-1',
                filename: 'a.png',
                image_url: '/uploads/img-1',
                progress: { completed: 2, total: 10 },
                rating: null,
              },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }
      return Promise.resolve(new Response('[]', { status: 200 }));
    });

    const rootElement = document.createElement('div');
    document.body.appendChild(rootElement);

    await act(async () => {
      createRoot(rootElement).render(<ManualRatingApp />);
    });

    expect(document.body.textContent).toContain('清晰度');
    expect(document.body.textContent).toContain('显著性');
    expect(document.body.textContent).toContain('伪影抑制');
    expect(document.body.textContent).toContain('结构完整性');
    expect(document.body.textContent).toContain('细节保真');
    expect(document.body.textContent).toContain('退出登录');
    expect(document.body.textContent).not.toContain('AOI');
  });

  it('点击退出登录后回到登录页', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      if (input === '/api/auth/bootstrap-status') {
        return Promise.resolve(new Response(JSON.stringify({ needs_setup: false }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      if (input === '/api/auth/me') {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              user: { id: 'u1', username: 'admin', display_name: '管理员', role: 'admin', active: true },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }
      if (input === '/api/manual/tasks') {
        return Promise.resolve(new Response(JSON.stringify({ tasks: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      if (input === '/api/manual/users') {
        return Promise.resolve(new Response(JSON.stringify({ users: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      if (input === '/api/manual/datasets') {
        return Promise.resolve(new Response(JSON.stringify({ datasets: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      if (input === '/api/auth/logout' && init?.method === 'POST') {
        return Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      return Promise.resolve(new Response('[]', { status: 200 }));
    });

    const rootElement = document.createElement('div');
    document.body.appendChild(rootElement);

    await act(async () => {
      createRoot(rootElement).render(<ManualRatingApp />);
    });

    const logoutButton = Array.from(document.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('退出登录'),
    );

    await act(async () => {
      logoutButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/auth/logout',
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    );
    expect(document.body.textContent).toContain('人工评分登录');
    expect(document.body.textContent).toContain('用户名');
  });

  it('看图员提交评分后切到下一张图', async () => {
    const nextImageIds = ['img-1', 'img-2', null];
    vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      if (input === '/api/auth/bootstrap-status') {
        return Promise.resolve(new Response(JSON.stringify({ needs_setup: false }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      if (input === '/api/auth/me') {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              user: { id: 'u2', username: 'reviewer', display_name: '看图员', role: 'reviewer', active: true },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }
      if (input === '/api/manual/tasks') {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              tasks: [
                {
                  id: 'task-1',
                  dataset_id: 'dataset-1',
                  name: '任务 A',
                  description: '',
                  dataset_name: '数据集 A',
                  status: 'active',
                  total_images: 2,
                  completed_images: 0,
                  reviewer_count: 1,
                  created_by: 'u1',
                  created_at: '2026-05-07T00:00:00Z',
                },
              ],
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }
      if (input === '/api/manual/tasks/task-1/next') {
        return Promise.resolve(
          new Response(JSON.stringify({ image_id: nextImageIds.shift() ?? null }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }
      if (input === '/api/manual/tasks/task-1/images') {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              images: [
                { image_id: 'img-1', sort_order: 0, filename: 'a.png', image_url: '/uploads/img-1', rating: null, overall_score: null },
                { image_id: 'img-2', sort_order: 1, filename: 'b.png', image_url: '/uploads/img-2', rating: null, overall_score: null },
              ],
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }
      if (input === '/api/manual/tasks/task-1/images/img-1') {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              image: {
                task_id: 'task-1',
                image_id: 'img-1',
                filename: 'a.png',
                image_url: '/uploads/img-1',
                progress: { completed: 0, total: 2 },
                rating: null,
              },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }
      if (input === '/api/manual/tasks/task-1/images/img-2') {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              image: {
                task_id: 'task-1',
                image_id: 'img-2',
                filename: 'b.png',
                image_url: '/uploads/img-2',
                progress: { completed: 1, total: 2 },
                rating: null,
              },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }
      if (input === '/api/manual/tasks/task-1/images/img-1/rating' && init?.method === 'PUT') {
        return Promise.resolve(
          new Response(JSON.stringify({ rating: { comment: '' } }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }
      return Promise.resolve(new Response('[]', { status: 200 }));
    });

    const rootElement = document.createElement('div');
    document.body.appendChild(rootElement);

    await act(async () => {
      createRoot(rootElement).render(<ManualRatingApp />);
    });

    const submitButton = Array.from(document.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('提交本张评分'),
    );

    await act(async () => {
      submitButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(document.body.textContent).toContain('b.png');
  });

  it('看图员可以列表导航、保留草稿、按总分排序并提交本次任务分数', async () => {
    const calls: Array<[RequestInfo | URL, RequestInit | undefined]> = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      calls.push([input, init]);
      if (input === '/api/auth/bootstrap-status') {
        return Promise.resolve(new Response(JSON.stringify({ needs_setup: false }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      if (input === '/api/auth/me') {
        return Promise.resolve(
          new Response(JSON.stringify({ user: { id: 'u2', username: 'reviewer', display_name: '看图员', role: 'reviewer', active: true } }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }
      if (input === '/api/manual/tasks') {
        return Promise.resolve(
          new Response(JSON.stringify({
            tasks: [{
              id: 'task-1',
              dataset_id: 'dataset-1',
              name: '任务 A',
              description: '',
              dataset_name: '数据集 A',
              status: 'active',
              total_images: 2,
              completed_images: 1,
              reviewer_count: 1,
              created_by: 'u1',
              created_at: '2026-05-07T00:00:00Z',
            }],
          }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
        );
      }
      if (input === '/api/manual/tasks/task-1/images') {
        return Promise.resolve(
          new Response(JSON.stringify({
            images: [
              {
                image_id: 'img-1',
                sort_order: 0,
                filename: 'b.png',
                image_url: '/uploads/img-1',
                rating: null,
                overall_score: null,
              },
              {
                image_id: 'img-2',
                sort_order: 1,
                filename: 'a.png',
                image_url: '/uploads/img-2',
                rating: {
                  sharpness_score: 8,
                  significance_score: 8,
                  artifact_suppression_score: 8,
                  structure_score: 8,
                  detail_score: 8,
                  comment: '',
                },
                overall_score: 8,
              },
            ],
          }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
        );
      }
      if (input === '/api/manual/tasks/task-1/images/img-1') {
        return Promise.resolve(
          new Response(JSON.stringify({
            image: {
              task_id: 'task-1',
              image_id: 'img-1',
              filename: 'b.png',
              image_url: '/uploads/img-1',
              progress: { completed: 1, total: 2 },
              rating: null,
            },
          }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
        );
      }
      if (input === '/api/manual/tasks/task-1/images/img-2') {
        return Promise.resolve(
          new Response(JSON.stringify({
            image: {
              task_id: 'task-1',
              image_id: 'img-2',
              filename: 'a.png',
              image_url: '/uploads/img-2',
              progress: { completed: 1, total: 2 },
              rating: {
                sharpness_score: 8,
                significance_score: 8,
                artifact_suppression_score: 8,
                structure_score: 8,
                detail_score: 8,
                comment: '',
              },
            },
          }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
        );
      }
      if (String(input).includes('/rating') && init?.method === 'PUT') {
        return Promise.resolve(new Response(JSON.stringify({ rating: JSON.parse(String(init.body)) }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      return Promise.resolve(new Response('[]', { status: 200 }));
    });

    const rootElement = document.createElement('div');
    document.body.appendChild(rootElement);

    await act(async () => {
      createRoot(rootElement).render(<ManualRatingApp />);
    });

    expect(document.body.textContent).toContain('图片列表');
    expect(document.body.textContent).toContain('当前总分');
    expect(document.body.textContent).toContain('10.0');
    expect(document.querySelectorAll('input[type="range"]')).toHaveLength(5);
    expect(document.querySelectorAll('.manual-info-button')).toHaveLength(0);
    expect(document.body.textContent).toContain('边缘、轮廓和主体纹理是否清楚');
    expect(document.body.textContent).toContain('目标区域与背景是否容易区分');
    expect(document.body.textContent).toContain('条纹、亮斑、噪声、泄漏等干扰是否少');

    const firstNumberInput = document.querySelector('input[type="number"]') as HTMLInputElement;
    await act(async () => {
      firstNumberInput.value = '9';
      firstNumberInput.dispatchEvent(new Event('input', { bubbles: true }));
    });

    expect(document.body.textContent).toContain('草稿');
    expect(document.body.textContent).toContain('9.8');

    const nextButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent?.includes('下一张'));
    await act(async () => {
      nextButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(document.body.textContent).toContain('a.png');
    expect(document.body.textContent).toContain('修改分数');

    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true }));
    });

    expect((document.querySelector('input[type="number"]') as HTMLInputElement).value).toBe('9');

    const numberInput = document.querySelector('input[type="number"]') as HTMLInputElement;
    await act(async () => {
      numberInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    });

    expect(document.body.textContent).toContain('b.png');

    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    });

    expect((document.querySelector('.manual-review-image') as HTMLImageElement).alt).toBe('a.png');

    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp', bubbles: true }));
    });

    expect((document.querySelector('.manual-review-image') as HTMLImageElement).alt).toBe('b.png');

    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
    });

    expect((document.querySelector('.manual-review-image') as HTMLImageElement).alt).toBe('a.png');

    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'w', bubbles: true }));
    });

    expect((document.querySelector('.manual-review-image') as HTMLImageElement).alt).toBe('b.png');

    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'd', bubbles: true }));
    });

    expect((document.querySelector('.manual-review-image') as HTMLImageElement).alt).toBe('a.png');

    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'a', bubbles: true }));
    });

    expect((document.querySelector('.manual-review-image') as HTMLImageElement).alt).toBe('b.png');

    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 's', bubbles: true }));
    });

    expect((document.querySelector('.manual-review-image') as HTMLImageElement).alt).toBe('a.png');

    const sortSelect = document.querySelector('select[aria-label="图片排序"]') as HTMLSelectElement;
    await act(async () => {
      sortSelect.value = 'score';
      sortSelect.dispatchEvent(new Event('change', { bubbles: true }));
    });

    const imageButtons = Array.from(document.querySelectorAll('.manual-image-nav-row'));
    expect(imageButtons[0].textContent).toContain('b.png');

    const submitTaskButton = Array.from(document.querySelectorAll('button')).find((button) => button.textContent?.includes('提交本次任务分数'));
    await act(async () => {
      submitTaskButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    const ratingCalls = calls.filter(([input, init]) => String(input).includes('/rating') && init?.method === 'PUT');
    expect(ratingCalls).toHaveLength(1);
    expect(ratingCalls[0][0]).toBe('/api/manual/tasks/task-1/images/img-1/rating');
  });
  it('folder upload can submit dataset creation', async () => {
    const calls: Array<[RequestInfo | URL, RequestInit | undefined]> = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      calls.push([input, init]);
      if (input === '/api/auth/bootstrap-status') {
        return Promise.resolve(new Response(JSON.stringify({ needs_setup: false }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      if (input === '/api/auth/me') {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              user: { id: 'u1', username: 'admin', display_name: 'Admin', role: 'admin', active: true },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }
      if (input === '/api/manual/tasks') {
        return Promise.resolve(new Response(JSON.stringify({ tasks: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      if (input === '/api/manual/users') {
        return Promise.resolve(new Response(JSON.stringify({ users: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      if (input === '/api/manual/datasets') {
        return Promise.resolve(new Response(JSON.stringify({ datasets: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      if (input === '/api/manual/datasets/upload' && init?.method === 'POST') {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              dataset: {
                id: 'd1',
                name: 'session-1-front',
                source: 'session-1/front',
                source_label: '',
                batch_label: '',
                note_label: '',
                experiment_group: 'manual-rating',
                batch: 'manual-upload',
                created_by: 'u1',
                created_at: '2026-05-07T00:00:00Z',
                image_ids: ['img-1', 'img-2'],
                image_count: 2,
              },
              imported: 2,
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }
      return Promise.resolve(new Response('[]', { status: 200 }));
    });

    const rootElement = document.createElement('div');
    document.body.appendChild(rootElement);

    await act(async () => {
      createRoot(rootElement).render(<ManualRatingApp />);
    });

    const folderInput = Array.from(document.querySelectorAll('input')).find((input) =>
      input.getAttribute('webkitdirectory') === 'true',
    ) as HTMLInputElement | undefined;
    expect(folderInput).toBeTruthy();

    const fileA = new File(['a'], 'a.png', { type: 'image/png' });
    const fileB = new File(['b'], 'b.png', { type: 'image/png' });
    Object.defineProperty(fileA, 'webkitRelativePath', { value: 'session-1/front/a.png' });
    Object.defineProperty(fileB, 'webkitRelativePath', { value: 'session-1/front/b.png' });

    await act(async () => {
      Object.defineProperty(folderInput!, 'files', {
        configurable: true,
        value: [fileA, fileB],
      });
      folderInput!.dispatchEvent(new Event('change', { bubbles: true }));
    });

    const uploadButton = Array.from(document.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('上传并创建数据集') || button.textContent?.includes('涓婁紶骞跺垱寤烘暟鎹泦'),
    );

    await act(async () => {
      uploadButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    const uploadCall = calls.find(([input]) => input === '/api/manual/datasets/upload');
    expect(uploadCall).toBeTruthy();
    const form = uploadCall?.[1]?.body as FormData;
    expect(form.getAll('files')).toHaveLength(2);
    expect(String(form.get('name') ?? '')).not.toBe('');
  });

  it('folder upload failure is shown to the user', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      if (input === '/api/auth/bootstrap-status') {
        return Promise.resolve(new Response(JSON.stringify({ needs_setup: false }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      if (input === '/api/auth/me') {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              user: { id: 'u1', username: 'admin', display_name: 'Admin', role: 'admin', active: true },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }
      if (input === '/api/manual/tasks') {
        return Promise.resolve(new Response(JSON.stringify({ tasks: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      if (input === '/api/manual/users') {
        return Promise.resolve(new Response(JSON.stringify({ users: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      if (input === '/api/manual/datasets') {
        return Promise.resolve(new Response(JSON.stringify({ datasets: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
      }
      if (input === '/api/manual/datasets/upload' && init?.method === 'POST') {
        return Promise.resolve(new Response('no valid image files uploaded', { status: 400 }));
      }
      return Promise.resolve(new Response('[]', { status: 200 }));
    });

    const rootElement = document.createElement('div');
    document.body.appendChild(rootElement);

    await act(async () => {
      createRoot(rootElement).render(<ManualRatingApp />);
    });

    const folderInput = Array.from(document.querySelectorAll('input')).find((input) =>
      input.getAttribute('webkitdirectory') === 'true',
    ) as HTMLInputElement | undefined;
    expect(folderInput).toBeTruthy();

    const fileA = new File(['a'], 'a.png', { type: 'image/png' });
    Object.defineProperty(fileA, 'webkitRelativePath', { value: 'session-1/front/a.png' });

    await act(async () => {
      Object.defineProperty(folderInput!, 'files', {
        configurable: true,
        value: [fileA],
      });
      folderInput!.dispatchEvent(new Event('change', { bubbles: true }));
    });

    const uploadButton = Array.from(document.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('上传并创建数据集') || button.textContent?.includes('涓婁紶骞跺垱寤烘暟鎹泦'),
    );

    await act(async () => {
      uploadButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(document.body.textContent).toContain('no valid image files uploaded');
  });
});
