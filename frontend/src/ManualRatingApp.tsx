import { FormEvent, useEffect, useMemo, useState } from 'react';

import {
  createManualTask,
  createManualUser,
  fetchCurrentManualUser,
  fetchManualAdminImageDetail,
  fetchManualBootstrapStatus,
  fetchManualDatasets,
  fetchManualTaskSummary,
  fetchManualTasks,
  fetchManualUsers,
  fetchReviewerImageDetail,
  fetchReviewerTaskImages,
  loginManualUser,
  logoutManualUser,
  submitManualRating,
  uploadManualDataset,
} from './manualRatingApi';
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

type ManualMetricKey = Exclude<keyof ManualRatingForm, 'comment'>;

const 评分指标: Array<{ key: ManualMetricKey; label: string; info: string }> = [
  { key: 'sharpness_score', label: '清晰度', info: '边缘、轮廓和主体纹理是否清楚，是否便于观察。' },
  { key: 'significance_score', label: '显著性', info: '目标区域与背景是否容易区分，主体是否突出。' },
  { key: 'artifact_suppression_score', label: '伪影抑制', info: '条纹、亮斑、噪声、泄漏等干扰是否少。' },
  { key: 'structure_score', label: '结构完整性', info: '人体或目标结构是否连续、完整，是否缺失或变形。' },
  { key: 'detail_score', label: '细节保真', info: '细小结构和局部层次是否保留，是否过度平滑或失真。' },
];

function createEmptyRating(): ManualRatingForm {
  return {
    sharpness_score: 10,
    significance_score: 10,
    artifact_suppression_score: 10,
    structure_score: 10,
    detail_score: 10,
    comment: '',
  };
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
}

function formatScore(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '-';
  return Number(value).toFixed(1);
}

function ratingOverallScore(rating: ManualRatingForm): number {
  const total = 评分指标.reduce((sum, metric) => sum + Number(rating[metric.key] || 0), 0);
  return Math.round((total / 评分指标.length) * 10) / 10;
}

function normalizeScoreInput(value: string): number {
  const parsed = Number(value);
  if (Number.isNaN(parsed)) return 0;
  return Math.min(10, Math.max(0, parsed));
}

function buildDatasetNameFromFiles(files: File[]): string {
  const first = files[0];
  if (!first) return '';

  const relativePath = first.webkitRelativePath || '';
  if (relativePath) {
    const normalized = relativePath.replace(/\\/g, '/');
    const parts = normalized.split('/').filter(Boolean);
    if (parts.length >= 3) {
      return `${parts[0]}-${parts[1]}`;
    }
    if (parts.length >= 2) {
      return parts[0];
    }
  }

  const filename = first.name || '';
  const dotIndex = filename.lastIndexOf('.');
  return dotIndex > 0 ? filename.slice(0, dotIndex) : filename;
}

function 数据集标签列表({ dataset }: { dataset: ManualDataset }) {
  const items = [
    dataset.source_label ? `来源标签：${dataset.source_label}` : '',
    dataset.batch_label ? `批次标签：${dataset.batch_label}` : '',
    dataset.note_label ? `备注标签：${dataset.note_label}` : '',
  ].filter(Boolean);

  if (!items.length) {
    return <span>未填写可选标签</span>;
  }

  return (
    <>
      {items.map((item) => <span key={item}>{item}</span>)}
    </>
  );
}

function ManualSessionBar({ user, onLogout }: { user: ManualUser; onLogout: () => void }) {
  return (
    <div className="manual-session-bar">
      <div className="manual-session-meta">
        <strong>{user.display_name}</strong>
        <span>{user.username}</span>
      </div>
      <button type="button" className="secondary-button manual-logout-button" onClick={onLogout}>
        退出登录
      </button>
    </div>
  );
}

function 管理员工作台({ user, onLogout }: { user: ManualUser; onLogout: () => void }) {
  const [任务列表, set任务列表] = useState<ManualTaskListItem[]>([]);
  const [用户列表, set用户列表] = useState<ManualUser[]>([]);
  const [数据集列表, set数据集列表] = useState<ManualDataset[]>([]);
  const [当前任务摘要, set当前任务摘要] = useState<ManualTaskSummary | null>(null);
  const [当前图片明细, set当前图片明细] = useState<ManualAdminImageDetail | null>(null);
  const [选中任务, set选中任务] = useState('');
  const [选中图片, set选中图片] = useState('');
  const [看图员用户名, set看图员用户名] = useState('');
  const [看图员显示名, set看图员显示名] = useState('');
  const [看图员密码, set看图员密码] = useState('');
  const [数据集名称, set数据集名称] = useState('');
  const [来源标签, set来源标签] = useState('');
  const [批次标签, set批次标签] = useState('');
  const [备注标签, set备注标签] = useState('');
  const [数据集文件, set数据集文件] = useState<File[]>([]);
  const [任务名称, set任务名称] = useState('');
  const [任务数据集, set任务数据集] = useState('');
  const [任务看图员, set任务看图员] = useState<string[]>([]);
  const [提示, set提示] = useState('');

  const 看图员列表 = useMemo(
    () => 用户列表.filter((item) => item.role === 'reviewer'),
    [用户列表],
  );

  async function 刷新管理数据(preserveSelection = true) {
    const [任务结果, 用户结果, 数据集结果] = await Promise.all([
      fetchManualTasks(),
      fetchManualUsers(),
      fetchManualDatasets(),
    ]);
    set任务列表(任务结果.tasks);
    set用户列表(用户结果.users);
    set数据集列表(数据集结果.datasets);

    const nextTaskId = preserveSelection
      ? 任务结果.tasks.find((item) => item.id === 选中任务)?.id ?? 任务结果.tasks[0]?.id ?? ''
      : 任务结果.tasks[0]?.id ?? '';
    set选中任务(nextTaskId);
  }

  useEffect(() => {
    void 刷新管理数据(false);
  }, []);

  useEffect(() => {
    if (!任务数据集 && 数据集列表[0]) {
      set任务数据集(数据集列表[0].id);
    }
  }, [任务数据集, 数据集列表]);

  useEffect(() => {
    if (!任务看图员.length && 看图员列表[0]) {
      set任务看图员([看图员列表[0].id]);
    }
  }, [任务看图员, 看图员列表]);

  useEffect(() => {
    if (!选中任务) {
      set当前任务摘要(null);
      set当前图片明细(null);
      set选中图片('');
      return;
    }

    fetchManualTaskSummary(选中任务)
      .then(({ summary }) => {
        set当前任务摘要(summary);
        set选中图片(summary.image_summaries[0]?.image_id ?? '');
      })
      .catch(() => {
        set当前任务摘要(null);
        set选中图片('');
      });
  }, [选中任务]);

  useEffect(() => {
    if (!选中任务 || !选中图片) {
      set当前图片明细(null);
      return;
    }

    fetchManualAdminImageDetail(选中任务, 选中图片)
      .then(({ image }) => set当前图片明细(image))
      .catch(() => set当前图片明细(null));
  }, [选中任务, 选中图片]);

  function 处理数据集文件变更(files: File[]) {
    set数据集文件(files);
    set提示('');
    if (!数据集名称.trim()) {
      set数据集名称(buildDatasetNameFromFiles(files));
    }
  }

  async function 创建看图员(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await createManualUser({
        username: 看图员用户名,
        display_name: 看图员显示名,
        password: 看图员密码,
        role: 'reviewer',
        active: true,
      });
      set看图员用户名('');
      set看图员显示名('');
      set看图员密码('');
      set提示('看图员已创建');
      await 刷新管理数据();
    } catch (error) {
      set提示(error instanceof Error ? error.message : '看图员创建失败');
    }
  }

  async function 创建数据集(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!数据集文件.length) {
      set提示('请先选择图片或文件夹');
      return;
    }

    const finalName = 数据集名称.trim() || buildDatasetNameFromFiles(数据集文件);
    if (!finalName) {
      set提示('请填写数据集名称');
      return;
    }

    try {
      const result = await uploadManualDataset(finalName, 数据集文件, {
        source_label: 来源标签,
        batch_label: 批次标签,
        note_label: 备注标签,
      });
      set数据集名称('');
      set来源标签('');
      set批次标签('');
      set备注标签('');
      set数据集文件([]);
      set提示(`数据集已创建，已导入 ${result.imported} 张图片`);
      await 刷新管理数据();
    } catch (error) {
      set提示(error instanceof Error ? error.message : '数据集创建失败');
    }
  }

  async function 创建任务(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await createManualTask({
        dataset_id: 任务数据集,
        name: 任务名称,
        description: '',
        reviewer_ids: 任务看图员,
      });
      set任务名称('');
      set提示('任务已创建');
      await 刷新管理数据(false);
    } catch (error) {
      set提示(error instanceof Error ? error.message : '任务创建失败');
    }
  }

  return (
    <section className="manual-rating-shell">
      <div className="manual-admin-layout enhanced">
        <ManualSessionBar user={user} onLogout={onLogout} />

        <section className="manual-panel">
          <div className="manual-panel-heading">
            <h2>任务情况</h2>
            <span>{user.display_name}</span>
          </div>
          <div className="manual-task-list">
            {任务列表.map((任务) => (
              <button
                type="button"
                key={任务.id}
                className={`manual-task-row ${选中任务 === 任务.id ? 'selected' : ''}`}
                onClick={() => set选中任务(任务.id)}
              >
                <strong>{任务.name}</strong>
                <span>{任务.dataset_name}</span>
                <span>{`整体进度：${任务.completed_images} / ${任务.total_images}`}</span>
                <span>{`看图员数量：${任务.reviewer_count}`}</span>
              </button>
            ))}
          </div>
          {当前任务摘要 ? (
            <section className="manual-detail-block">
              <h3>看图员任务进度</h3>
              <div className="manual-list-rows">
                {当前任务摘要.reviewer_progress.map((item) => (
                  <div key={item.reviewer_id} className="manual-list-row">
                    <strong>{item.reviewer_display_name}</strong>
                    <span>{item.reviewer_username}</span>
                    <span>{`进度：${item.completed_images} / ${item.total_images}`}</span>
                    <span>{`权重：${formatScore(item.weight)}`}</span>
                  </div>
                ))}
              </div>
            </section>
          ) : null}
        </section>

        <section className="manual-panel">
          <div className="manual-panel-heading">
            <h2>创建看图员</h2>
            <span>{`共 ${看图员列表.length} 人`}</span>
          </div>
          <form className="manual-admin-form" onSubmit={创建看图员}>
            <input placeholder="用户名" value={看图员用户名} onChange={(event) => set看图员用户名(event.target.value)} />
            <input placeholder="显示名称" value={看图员显示名} onChange={(event) => set看图员显示名(event.target.value)} />
            <input placeholder="密码" type="password" value={看图员密码} onChange={(event) => set看图员密码(event.target.value)} />
            <button type="submit" className="secondary-button">创建看图员</button>
          </form>
          <section className="manual-list-panel">
            <h3>已创建看图员</h3>
            <div className="manual-list-rows">
              {看图员列表.map((item) => (
                <div key={item.id} className="manual-list-row">
                  <strong>{item.display_name}</strong>
                  <span>{item.username}</span>
                </div>
              ))}
            </div>
          </section>
        </section>

        <section className="manual-panel">
          <div className="manual-panel-heading">
            <h2>创建数据集</h2>
            <span>{`共 ${数据集列表.length} 个`}</span>
          </div>
          <form className="manual-admin-form" onSubmit={创建数据集}>
            <input placeholder="数据集名称（必填）" value={数据集名称} onChange={(event) => set数据集名称(event.target.value)} />
            <input placeholder="来源标签（选填）" value={来源标签} onChange={(event) => set来源标签(event.target.value)} />
            <input placeholder="批次标签（选填）" value={批次标签} onChange={(event) => set批次标签(event.target.value)} />
            <input placeholder="备注标签（选填）" value={备注标签} onChange={(event) => set备注标签(event.target.value)} />
            <label className="manual-file-picker">
              <span>选择本地图片</span>
              <input
                type="file"
                multiple
                accept="image/*"
                onChange={(event) => 处理数据集文件变更(Array.from(event.target.files ?? []))}
              />
            </label>
            <label className="manual-file-picker">
              <span>选择本地文件夹</span>
              <input
                type="file"
                multiple
                // @ts-expect-error webkitdirectory is supported by target browsers but not in standard typing.
                webkitdirectory="true"
                accept="image/*"
                onChange={(event) => 处理数据集文件变更(Array.from(event.target.files ?? []))}
              />
            </label>
            <span>{数据集文件.length ? `已选择 ${数据集文件.length} 张图片` : '可直接选择图片或整个文件夹导入'}</span>
            <button type="submit" className="secondary-button">上传并创建数据集</button>
          </form>
          <section className="manual-list-panel">
            <h3>已创建数据集</h3>
            <div className="manual-list-rows">
              {数据集列表.map((数据集) => (
                <div key={数据集.id} className="manual-list-row">
                  <strong>{数据集.name}</strong>
                  <span>{`图片数量：${数据集.image_count}`}</span>
                  <span>{`来源目录：${数据集.source}`}</span>
                  <span>{`创建时间：${formatDate(数据集.created_at)}`}</span>
                  <数据集标签列表 dataset={数据集} />
                </div>
              ))}
            </div>
          </section>
        </section>

        <section className="manual-panel">
          <div className="manual-panel-heading">
            <h2>创建任务</h2>
            <span>可为同一数据集分配多个看图员</span>
          </div>
          <form className="manual-admin-form" onSubmit={创建任务}>
            <input placeholder="任务名称" value={任务名称} onChange={(event) => set任务名称(event.target.value)} />
            <select value={任务数据集} onChange={(event) => set任务数据集(event.target.value)}>
              <option value="">选择数据集</option>
              {数据集列表.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
            <select
              multiple
              value={任务看图员}
              onChange={(event) =>
                set任务看图员(Array.from(event.target.selectedOptions).map((option) => option.value))
              }
            >
              {看图员列表.map((item) => (
                <option key={item.id} value={item.id}>{item.display_name}</option>
              ))}
            </select>
            <button type="submit" className="secondary-button">创建任务</button>
          </form>
          {提示 ? <p className="manual-admin-message">{提示}</p> : null}
        </section>

        <section className="manual-panel manual-wide-panel">
          <div className="manual-panel-heading">
            <h2>图片评分明细</h2>
            <span>{当前任务摘要 ? 当前任务摘要.task_name : '请先选择任务'}</span>
          </div>
          {当前任务摘要 ? (
            <div className="manual-admin-detail-layout">
              <aside className="manual-image-summary-list">
                {当前任务摘要.image_summaries.map((item) => (
                  <button
                    type="button"
                    key={item.image_id}
                    className={`manual-task-row ${选中图片 === item.image_id ? 'selected' : ''}`}
                    onClick={() => set选中图片(item.image_id)}
                  >
                    <strong>{`图片 ${item.sort_order + 1}`}</strong>
                    <span>{item.image_id}</span>
                    <span>{`评分人数：${item.rating_count}`}</span>
                    <span>{`均分：${formatScore(item.average_overall_score)}`}</span>
                    <span>{`加权均分：${formatScore(item.weighted_overall_score)}`}</span>
                  </button>
                ))}
              </aside>

              <section className="manual-image-detail-panel">
                {当前图片明细 ? (
                  <>
                    <div className="manual-image-detail-header">
                      <div>
                        <strong>{当前图片明细.filename}</strong>
                        <span>{当前图片明细.image_id}</span>
                      </div>
                      <div className="manual-aggregate-grid">
                        <div className="metric-tile compact-tile">
                          <span>平均总分</span>
                          <strong>{formatScore(当前图片明细.aggregates.average.overall_score as number | null)}</strong>
                        </div>
                        <div className="metric-tile compact-tile">
                          <span>加权均分</span>
                          <strong>{formatScore(当前图片明细.aggregates.weighted.overall_score as number | null)}</strong>
                        </div>
                      </div>
                    </div>
                    <img src={当前图片明细.image_url} alt={当前图片明细.filename} className="manual-review-image manual-admin-image-preview" />
                    <section className="manual-detail-block">
                      <h3>各看图员评分</h3>
                      <div className="manual-list-rows">
                        {当前图片明细.ratings.map((item) => (
                          <div key={item.id} className="manual-list-row">
                            <strong>{item.reviewer_display_name}</strong>
                            <span>{`${item.reviewer_username} / 权重 ${formatScore(item.weight)}`}</span>
                            <span>{`清晰度 ${formatScore(item.sharpness_score)}，显著性 ${formatScore(item.significance_score)}`}</span>
                            <span>{`伪影抑制 ${formatScore(item.artifact_suppression_score)}，结构完整性 ${formatScore(item.structure_score)}`}</span>
                            <span>{`细节保真 ${formatScore(item.detail_score)}，总分 ${formatScore(item.overall_score)}`}</span>
                            {item.comment ? <span>{`备注：${item.comment}`}</span> : null}
                          </div>
                        ))}
                      </div>
                    </section>
                  </>
                ) : (
                  <div className="empty-state">当前没有图片评分明细</div>
                )}
              </section>
            </div>
          ) : (
            <div className="empty-state">请选择左侧任务查看图片评分明细</div>
          )}
        </section>
      </div>
    </section>
  );
}

function 看图员工作台({ user, onLogout }: { user: ManualUser; onLogout: () => void }) {
  const [任务列表, set任务列表] = useState<ManualTaskListItem[]>([]);
  const [当前任务, set当前任务] = useState<string | null>(null);
  const [图片列表, set图片列表] = useState<ReviewerTaskImageListItem[]>([]);
  const [当前图片ID, set当前图片ID] = useState<string | null>(null);
  const [当前图片, set当前图片] = useState<ReviewerImageDetail | null>(null);
  const [草稿, set草稿] = useState<Record<string, ManualRatingForm>>({});
  const [已编辑图片, set已编辑图片] = useState<Record<string, boolean>>({});
  const [可编辑图片, set可编辑图片] = useState<Record<string, boolean>>({});
  const [排序方式, set排序方式] = useState<'name' | 'score'>('name');
  const [提示, set提示] = useState('');

  const 当前草稿 = 当前图片ID ? 草稿[当前图片ID] ?? 当前图片?.rating ?? createEmptyRating() : createEmptyRating();
  const 当前索引 = 图片列表.findIndex((image) => image.image_id === 当前图片ID);
  const 当前图片已提交 = Boolean(当前图片?.rating);
  const 当前图片可编辑 = 当前图片ID ? 可编辑图片[当前图片ID] ?? !当前图片已提交 : false;
  const 当前总分 = ratingOverallScore(当前草稿);

  const 排序图片列表 = useMemo(() => [...图片列表].sort((a, b) => {
    if (排序方式 === 'score') {
      const aScore = 草稿[a.image_id] ? ratingOverallScore(草稿[a.image_id]) : a.overall_score;
      const bScore = 草稿[b.image_id] ? ratingOverallScore(草稿[b.image_id]) : b.overall_score;
      if (aScore !== null && bScore !== null && aScore !== bScore) return bScore - aScore;
      if (aScore !== null && bScore === null) return -1;
      if (aScore === null && bScore !== null) return 1;
    }
    return a.filename.localeCompare(b.filename, 'zh-CN', { numeric: true });
  }), [图片列表, 排序方式, 草稿]);

  useEffect(() => {
    fetchManualTasks()
      .then((payload) => {
        set任务列表(payload.tasks);
        set当前任务(payload.tasks[0]?.id ?? null);
      })
      .catch(() => {
        set任务列表([]);
        set当前任务(null);
      });
  }, []);

  useEffect(() => {
    if (!当前任务) {
      set图片列表([]);
      set当前图片ID(null);
      return;
    }
    fetchReviewerTaskImages(当前任务)
      .then(({ images }) => {
        const taskImages = Array.isArray(images) ? images : [];
        set图片列表(taskImages);
        set草稿((current) => {
          const next = { ...current };
          taskImages.forEach((image) => {
            if (image.rating && !next[image.image_id]) next[image.image_id] = image.rating;
          });
          return next;
        });
        set可编辑图片((current) => {
          const next = { ...current };
          taskImages.forEach((image) => {
            if (!(image.image_id in next)) next[image.image_id] = !image.rating;
          });
          return next;
        });
        set当前图片ID(taskImages[0]?.image_id ?? null);
      })
      .catch(() => {
        set图片列表([]);
        set当前图片ID(null);
      });
  }, [当前任务]);

  useEffect(() => {
    if (!当前任务 || !当前图片ID) {
      set当前图片(null);
      return;
    }
    fetchReviewerImageDetail(当前任务, 当前图片ID)
      .then(({ image }) => {
        set当前图片(image);
        set草稿((current) => (current[image.image_id]
          ? current
          : { ...current, [image.image_id]: image.rating ?? createEmptyRating() }));
      })
      .catch(() => set当前图片(null));
  }, [当前任务, 当前图片ID]);

  function 更新草稿(field: keyof ManualRatingForm, value: number | string) {
    if (!当前图片ID || !当前图片可编辑) return;
    set草稿((current) => ({
      ...current,
      [当前图片ID]: {
        ...(current[当前图片ID] ?? 当前图片?.rating ?? createEmptyRating()),
        [field]: value,
      },
    }));
    set已编辑图片((current) => ({ ...current, [当前图片ID]: true }));
  }

  function 切换图片(imageId: string | undefined) {
    if (!imageId) return;
    set提示('');
    set当前图片ID(imageId);
  }

  useEffect(() => {
    function 处理键盘导航(event: KeyboardEvent) {
      if (event.defaultPrevented) return;
      const target = event.target as HTMLElement | null;
      const tagName = target?.tagName;
      if (
        target?.isContentEditable
        || tagName === 'INPUT'
        || tagName === 'TEXTAREA'
        || tagName === 'SELECT'
      ) {
        return;
      }

      const key = event.key.toLowerCase();
      const direction = key === 'arrowleft' || key === 'arrowup' || key === 'a' || key === 'w'
        ? -1
        : key === 'arrowright' || key === 'arrowdown' || key === 'd' || key === 's'
          ? 1
          : 0;
      if (!direction) return;
      event.preventDefault();
      const nextImageId = 图片列表[当前索引 + direction]?.image_id;
      if (!nextImageId) return;
      set提示('');
      set当前图片ID(nextImageId);
    }

    window.addEventListener('keydown', 处理键盘导航);
    return () => window.removeEventListener('keydown', 处理键盘导航);
  }, [图片列表, 当前索引]);

  async function 提交单张评分() {
    if (!当前任务 || !当前图片ID) return;
    const payload = 草稿[当前图片ID] ?? 当前图片?.rating ?? createEmptyRating();
    await submitManualRating(当前任务, 当前图片ID, payload);
    set提示('本张评分已提交');
    set已编辑图片((current) => ({ ...current, [当前图片ID]: false }));
    set可编辑图片((current) => ({ ...current, [当前图片ID]: false }));
    set图片列表((current) => current.map((image) => (
      image.image_id === 当前图片ID ? { ...image, rating: payload, overall_score: ratingOverallScore(payload) } : image
    )));
    set当前图片((current) => (current ? { ...current, rating: payload } : current));
    切换图片(图片列表[当前索引 + 1]?.image_id);
  }

  async function 提交本次任务分数() {
    if (!当前任务) return;
    const imageIds = Object.keys(已编辑图片).filter((imageId) => 已编辑图片[imageId] && 草稿[imageId]);
    await Promise.all(imageIds.map((imageId) => submitManualRating(当前任务, imageId, 草稿[imageId])));
    set提示(`本次任务已提交 ${imageIds.length} 张评分`);
    set已编辑图片((current) => {
      const next = { ...current };
      imageIds.forEach((imageId) => { next[imageId] = false; });
      return next;
    });
    set可编辑图片((current) => {
      const next = { ...current };
      imageIds.forEach((imageId) => { next[imageId] = false; });
      return next;
    });
    set图片列表((current) => current.map((image) => (
      草稿[image.image_id]
        ? { ...image, rating: 草稿[image.image_id], overall_score: ratingOverallScore(草稿[image.image_id]) }
        : image
    )));
  }

  return (
    <section className="manual-rating-shell">
      <div className="manual-review-layout enhanced-review-layout">
        <aside className="manual-task-sidebar">
          <ManualSessionBar user={user} onLogout={onLogout} />
          <h2>我的任务</h2>
          {任务列表.map((任务) => (
            <button
              type="button"
              key={任务.id}
              onClick={() => {
                set当前任务(任务.id);
                set提示('');
              }}
              className={`manual-task-row ${当前任务 === 任务.id ? 'selected' : ''}`}
            >
              <strong>{任务.name}</strong>
              <span>{任务.dataset_name}</span>
            </button>
          ))}

          <div className="manual-list-toolbar">
            <strong>图片列表</strong>
            <select value={排序方式} onChange={(event) => set排序方式(event.target.value as 'name' | 'score')} aria-label="图片排序">
              <option value="name">按名称排序</option>
              <option value="score">按总分排序</option>
            </select>
          </div>
          <div className="manual-image-nav-list">
            {排序图片列表.map((image) => {
              const draft = 草稿[image.image_id];
              const score = draft
                ? ratingOverallScore(draft)
                : image.overall_score ?? (image.rating ? ratingOverallScore(image.rating) : ratingOverallScore(createEmptyRating()));
              return (
                <button
                  type="button"
                  key={image.image_id}
                  onClick={() => 切换图片(image.image_id)}
                  className={`manual-image-nav-row ${当前图片ID === image.image_id ? 'selected' : ''}`}
                >
                  <span>{image.filename}</span>
                  <small>{score === null ? '未提交' : `总分 ${formatScore(score)}`}</small>
                  {已编辑图片[image.image_id] ? <em>草稿</em> : null}
                </button>
              );
            })}
          </div>
        </aside>

        <section className="manual-review-stage">
          {当前图片 ? (
            <>
              <div className="manual-review-stage-header">
                <button type="button" onClick={() => 切换图片(图片列表[当前索引 - 1]?.image_id)} disabled={当前索引 <= 0}>上一张</button>
                <strong>{当前图片.filename}</strong>
                <button type="button" onClick={() => 切换图片(图片列表[当前索引 + 1]?.image_id)} disabled={当前索引 < 0 || 当前索引 >= 图片列表.length - 1}>下一张</button>
              </div>
              <img src={当前图片.image_url} alt={当前图片.filename} className="manual-review-image" />
            </>
          ) : <p>当前没有待评分图片</p>}
        </section>

        <section className="manual-rating-form reviewer-rating-panel">
          <div className="manual-rating-total">
            <span>当前总分</span>
            <strong>{formatScore(当前总分)}</strong>
          </div>
          {当前图片已提交 && !当前图片可编辑 ? (
            <button type="button" className="secondary-button" onClick={() => 当前图片ID && set可编辑图片((current) => ({ ...current, [当前图片ID]: true }))}>
              修改分数
            </button>
          ) : null}
          {评分指标.map((metric) => (
            <label key={metric.key} className="manual-score-control">
              <span className="manual-score-label">{metric.label}</span>
              <span className="manual-score-description">{metric.info}</span>
              <div className="manual-score-inputs">
                <input
                  type="range"
                  min="0"
                  max="10"
                  step="0.5"
                  value={当前草稿[metric.key]}
                  disabled={!当前图片可编辑}
                  onInput={(event) => 更新草稿(metric.key, normalizeScoreInput(event.currentTarget.value))}
                  onChange={(event) => 更新草稿(metric.key, normalizeScoreInput(event.target.value))}
                />
                <input
                  type="number"
                  min="0"
                  max="10"
                  step="0.5"
                  value={当前草稿[metric.key]}
                  disabled={!当前图片可编辑}
                  onInput={(event) => 更新草稿(metric.key, normalizeScoreInput(event.currentTarget.value))}
                  onChange={(event) => 更新草稿(metric.key, normalizeScoreInput(event.target.value))}
                />
              </div>
            </label>
          ))}
          <label>
            备注
            <textarea disabled={!当前图片可编辑} value={当前草稿.comment} onChange={(event) => 更新草稿('comment', event.target.value)} />
          </label>
          <div className="manual-rating-actions">
            <button type="button" className="primary-button" disabled={!当前图片 || !当前图片可编辑} onClick={提交单张评分}>提交本张评分</button>
            <button type="button" className="secondary-button" disabled={!Object.values(已编辑图片).some(Boolean)} onClick={提交本次任务分数}>提交本次任务分数</button>
          </div>
          {提示 ? <p className="manual-admin-message">{提示}</p> : null}
        </section>
      </div>
    </section>
  );
}

function ManualRatingApp() {
  const [当前用户, set当前用户] = useState<ManualUser | null>(null);
  const [用户名, set用户名] = useState('');
  const [密码, set密码] = useState('');
  const [错误信息, set错误信息] = useState('');
  const [需要初始化, set需要初始化] = useState(false);

  useEffect(() => {
    fetchManualBootstrapStatus()
      .then((payload) => set需要初始化(payload.needs_setup))
      .catch(() => set需要初始化(false));
    fetchCurrentManualUser()
      .then((payload) => set当前用户(payload.user))
      .catch(() => set当前用户(null));
  }, []);

  async function 登录(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    set错误信息('');
    try {
      const payload = await loginManualUser(用户名, 密码);
      set当前用户(payload.user);
      set密码('');
    } catch {
      set错误信息('登录失败');
    }
  }

  async function 退出登录() {
    try {
      await logoutManualUser();
    } finally {
      set当前用户(null);
      set用户名('');
      set密码('');
      set错误信息('');
    }
  }

  if (!当前用户) {
    return (
      <section className="manual-login-shell">
        <form className="manual-login-form" onSubmit={登录}>
          <h2>人工评分登录</h2>
          <label>
            用户名
            <input value={用户名} onChange={(event) => set用户名(event.target.value)} />
          </label>
          <label>
            密码
            <input type="password" value={密码} onChange={(event) => set密码(event.target.value)} />
          </label>
          {需要初始化 ? (
            <div className="manual-bootstrap-note">
              <strong>首次使用需要先初始化管理员</strong>
              <code>python .\scripts\bootstrap-manual-rating-admin.py --username admin --display-name 管理员 --password secret123</code>
            </div>
          ) : null}
          {错误信息 ? <p className="manual-login-error">{错误信息}</p> : null}
          <button type="submit" className="primary-button">登录</button>
        </form>
      </section>
    );
  }

  if (当前用户.role === 'admin') {
    return <管理员工作台 user={当前用户} onLogout={退出登录} />;
  }

  return <看图员工作台 user={当前用户} onLogout={退出登录} />;
}

export default ManualRatingApp;
