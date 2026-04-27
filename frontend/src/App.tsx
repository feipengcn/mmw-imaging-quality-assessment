import {
  FormEvent,
  InputHTMLAttributes,
  KeyboardEvent,
  useEffect,
  useMemo,
  useState,
} from 'react';
import {
  BarChart3,
  Download,
  FileSpreadsheet,
  FolderOpen,
  ImageUp,
  RefreshCw,
  RotateCcw,
  Save,
  SlidersHorizontal,
} from 'lucide-react';
import {
  fetchImages,
  resetImages,
  rescoreImages,
  saveRating,
  uploadImages,
} from './api';
import {
  defaultWeights,
  formatMetric,
  metricKeys,
  metricLabels,
  normalizeWeights,
} from './scoring';
import {
  filesToImportEntries,
  formatBytes,
  getNextImportSelectionIndex,
  getSelectedImportEntries,
  summarizeImportSelection,
  type ImportEntry,
} from './importSelection';
import { histogramPath } from './histogram';
import {
  defaultSubjectiveScores,
  getCompletedSubjectiveCount,
  getSubjectiveAverage,
  subjectiveScoreKeys,
  subjectiveScoreLabels,
} from './subjectiveRating';
import type { ImageRecord, MetricKey, SubjectiveScoreKey, SubjectiveScores, Weights } from './types';

type DirectoryInputProps = InputHTMLAttributes<HTMLInputElement> & {
  webkitdirectory?: string;
  directory?: string;
};

const apiExportLinks = [
  { href: '/api/export/csv', label: 'CSV', icon: FileSpreadsheet },
  { href: '/api/export/excel', label: 'Excel', icon: Download },
  { href: '/api/report/html', label: 'HTML Report', icon: BarChart3 },
];

function normalizeDisplayPath(path: string): string {
  return path.replace(/\\/g, '/').replace(/^\.\//, '').toLowerCase();
}

function basename(path: string): string {
  return normalizeDisplayPath(path).split('/').pop() ?? '';
}

function findCalculatedImageForImportEntry(entry: ImportEntry | undefined, images: ImageRecord[]): ImageRecord | undefined {
  if (!entry) return undefined;
  const entryPath = normalizeDisplayPath(entry.displayPath);
  const exactMatch = images.find((image) => normalizeDisplayPath(image.filename) === entryPath);
  if (exactMatch) return exactMatch;
  const entryName = basename(entry.displayPath);
  return images.find((image) => basename(image.filename) === entryName);
}

function App() {
  const [images, setImages] = useState<ImageRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [weights, setWeights] = useState<Weights>(defaultWeights);
  const [importMode, setImportMode] = useState<'files' | 'folder'>('files');
  const [importEntries, setImportEntries] = useState<ImportEntry[]>([]);
  const [selectedImportIds, setSelectedImportIds] = useState<Set<string>>(new Set());
  const [selectedImportIndex, setSelectedImportIndex] = useState(0);
  const [selectedImportUrl, setSelectedImportUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [subjectiveScoresDraft, setSubjectiveScoresDraft] = useState<SubjectiveScores>(defaultSubjectiveScores());
  const [notesDraft, setNotesDraft] = useState('');

  useEffect(() => {
    fetchImages()
      .then((data) => {
        setImages(data.images);
        if (data.weights && Object.keys(data.weights).length > 0) setWeights(data.weights);
        setSelectedId(data.images[0]?.id ?? null);
      })
      .catch((error) => setMessage(error.message));
  }, []);

  useEffect(() => {
    if (!selectedId && images.length > 0) {
      setSelectedId(images[0].id);
    }
  }, [images, selectedId]);

  const selected = useMemo(
    () => images.find((image) => image.id === selectedId) ?? images[0],
    [images, selectedId],
  );

  const summary = useMemo(() => {
    const count = images.length;
    const avg = count ? images.reduce((sum, image) => sum + image.quality_score, 0) / count : 0;
    return { count, avg };
  }, [images]);

  const importSummary = useMemo(() => summarizeImportSelection(importEntries), [importEntries]);
  const selectedImportEntry = importEntries[selectedImportIndex] ?? importEntries[0];
  const selectedImportEntries = useMemo(
    () => getSelectedImportEntries(importEntries, selectedImportIds),
    [importEntries, selectedImportIds],
  );
  const directoryInputProps: DirectoryInputProps =
    importMode === 'folder' ? { webkitdirectory: '', directory: '' } : {};

  useEffect(() => {
    setSubjectiveScoresDraft({ ...defaultSubjectiveScores(), ...(selected?.subjective_scores ?? {}) });
    setNotesDraft(selected?.notes ?? '');
  }, [selected?.id, selected?.notes, selected?.subjective_scores]);

  useEffect(() => {
    if (!selectedImportEntry) {
      setSelectedImportUrl(null);
      return;
    }
    const objectUrl = URL.createObjectURL(selectedImportEntry.file);
    setSelectedImportUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedImportEntry]);

  async function handleImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runCalculation(selectedImportEntries, 'selected');
  }

  async function runCalculation(entries: ImportEntry[], mode: 'selected' | 'current') {
    if (!entries.length) {
      setMessage(mode === 'current' ? '请选择一个当前预览文件' : '请至少勾选一个图像文件');
      return;
    }
    const payload = new FormData();
    entries.forEach((entry) => payload.append('files', entry.file, entry.displayPath));
    payload.append('experiment_group', 'default');
    payload.append('algorithm', 'unknown');
    payload.append('parameters', '');
    payload.append('batch', '');
    setBusy(true);
    try {
      const data = await uploadImages(payload);
      setImages(data.images);
      setSelectedId(data.images[0]?.id ?? null);
      setMessage(`已计算 ${data.imported} 张图像`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '计算失败');
    } finally {
      setBusy(false);
    }
  }

  async function handleWeightChange(key: MetricKey, value: number) {
    const next = normalizeWeights({ ...weights, [key]: value });
    setWeights(next);
    const data = await rescoreImages(next);
    setImages(data.images);
  }

  async function handleSaveRating() {
    if (!selected) return;
    setBusy(true);
    try {
      const data = await saveRating(selected.id, subjectiveScoresDraft, notesDraft);
      setImages(data.images);
      setMessage('评分已保存');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '保存失败');
    } finally {
      setBusy(false);
    }
  }

  async function handleReset() {
    const confirmed = window.confirm('确定清空所有已导入图片、ROI mask 和评分记录吗？');
    if (!confirmed) return;

    setBusy(true);
    try {
      const data = await resetImages();
      setImages(data.images);
      setSelectedId(null);
      setMessage('数据已清空');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '清空失败');
    } finally {
      setBusy(false);
    }
  }

  function handleImportFiles(nextFiles: FileList | null) {
    const entries = filesToImportEntries(nextFiles ?? []);
    setImportEntries(entries);
    setSelectedImportIndex(0);
    setSelectedImportIds(new Set(entries.map((entry) => entry.id)));
    setMessage(entries.length ? `已选择 ${entries.length} 个图像文件` : '没有找到可导入的图像文件');
  }

  function handleImportListKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const nextIndex = getNextImportSelectionIndex(selectedImportIndex, event.key, importEntries.length);
    if (nextIndex !== selectedImportIndex) {
      event.preventDefault();
      setSelectedImportIndex(nextIndex);
      selectCalculatedImportEntry(importEntries[nextIndex]);
    }
  }

  function selectCalculatedImportEntry(entry: ImportEntry | undefined) {
    const image = findCalculatedImageForImportEntry(entry, images);
    if (image) setSelectedId(image.id);
  }

  function toggleImportEntry(id: string) {
    setSelectedImportIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function updateSubjectiveScore(key: SubjectiveScoreKey, value: number | null) {
    setSubjectiveScoresDraft((current) => ({ ...current, [key]: value }));
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>毫米波人体成像质量评价</h1>
          <p>科研评测工作台</p>
        </div>
        <div className="actions">
          {apiExportLinks.map(({ href, label, icon: Icon }) => (
            <a className="icon-button text-button" href={href} key={href} target="_blank" rel="noreferrer">
              <Icon size={17} />
              {label}
            </a>
          ))}
          <button className="icon-button text-button danger" onClick={handleReset} disabled={busy} title="清空数据">
            <RotateCcw size={17} />
            清空数据
          </button>
        </div>
      </header>

      <main className="workspace">
        <aside className="side-panel">
          <form className="import-form" onSubmit={handleImport}>
            <div className="panel-title">
              <ImageUp size={18} />
              <h2>导入与计算</h2>
            </div>
            <div className="segmented-control" role="tablist" aria-label="导入模式">
              <button type="button" className={importMode === 'files' ? 'active' : ''} onClick={() => setImportMode('files')}>
                文件导入
              </button>
              <button type="button" className={importMode === 'folder' ? 'active' : ''} onClick={() => setImportMode('folder')}>
                文件夹导入
              </button>
            </div>
            <label className="file-drop">
              <input
                key={importMode}
                type="file"
                accept="image/png,image/jpeg,image/tiff,image/bmp,.tif,.tiff"
                multiple
                {...directoryInputProps}
                onChange={(event) => handleImportFiles(event.target.files)}
              />
              {importMode === 'folder' ? <FolderOpen size={24} /> : <ImageUp size={24} />}
              <span>{importEntries.length ? `${importEntries.length} 个图像文件` : '选择图像'}</span>
            </label>
            <div className="import-selection">
              <div className="import-selection-header">
                <strong>待计算文件</strong>
                <span>
                  勾选 {selectedImportIds.size} / {importSummary.count}，{formatBytes(importSummary.totalBytes)}
                </span>
              </div>
              {selectedImportEntry && selectedImportUrl && (
                <div className="import-preview">
                  <img src={selectedImportUrl} alt={selectedImportEntry.displayPath} />
                  <span>{selectedImportEntry.displayPath}</span>
                </div>
              )}
              <div className="import-toolbar">
                <button type="button" onClick={() => setSelectedImportIds(new Set(importEntries.map((entry) => entry.id)))}>
                  全选
                </button>
                <button type="button" onClick={() => setSelectedImportIds(new Set())}>
                  清空
                </button>
                <button
                  type="button"
                  onClick={() => selectedImportEntry && setSelectedImportIds(new Set([selectedImportEntry.id]))}
                  disabled={!selectedImportEntry}
                >
                  只选当前
                </button>
              </div>
              <div
                className="import-file-list"
                role="listbox"
                tabIndex={0}
                aria-label="待计算文件列表"
                aria-activedescendant={selectedImportEntry ? `import-file-${selectedImportEntry.id}` : undefined}
                onKeyDown={handleImportListKeyDown}
              >
                {importEntries.map((entry, index) => {
                  const calculatedImage = findCalculatedImageForImportEntry(entry, images);
                  const isObserved = calculatedImage?.id === selected?.id;
                  return (
                    <div
                      id={`import-file-${entry.id}`}
                      role="option"
                      aria-selected={index === selectedImportIndex}
                      className={`import-file-row ${index === selectedImportIndex ? 'active' : ''} ${isObserved ? 'observing' : ''}`}
                      key={entry.id}
                      onClick={() => {
                        setSelectedImportIndex(index);
                        selectCalculatedImportEntry(entry);
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={selectedImportIds.has(entry.id)}
                        onChange={() => toggleImportEntry(entry.id)}
                        onClick={(event) => event.stopPropagation()}
                        aria-label={`选择 ${entry.displayPath}`}
                      />
                      <span>{entry.displayPath}</span>
                      <small>{calculatedImage ? '已计算' : formatBytes(entry.size)}</small>
                    </div>
                  );
                })}
                {importEntries.length === 0 && <div className="empty-import-list">还没有选择文件</div>}
              </div>
            </div>
            <div className="compute-actions">
              <button
                type="button"
                className="secondary-button"
                disabled={busy || !selectedImportEntry}
                onClick={() => selectedImportEntry && runCalculation([selectedImportEntry], 'current')}
              >
                单张计算
              </button>
              <button className="primary-button" disabled={busy || !selectedImportIds.size}>
                <RefreshCw size={17} className={busy ? 'spin' : ''} />
                计算勾选
              </button>
            </div>
            {message && <p className="status-line">{message}</p>}
          </form>

          <section className="weights">
            <div className="panel-title">
              <SlidersHorizontal size={18} />
              <h2>权重</h2>
            </div>
            {metricKeys.map((key) => (
              <label className="slider-row" key={key}>
                <span>{metricLabels[key]}</span>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={weights[key]}
                  onChange={(event) => void handleWeightChange(key, Number(event.target.value))}
                />
                <b>{Math.round(weights[key] * 100)}%</b>
              </label>
            ))}
          </section>
        </aside>

        <section className="main-panel">
          <div className="summary-strip">
            <MetricTile label="样本数" value={String(summary.count)} />
            <MetricTile label="平均总分" value={summary.avg.toFixed(2)} />
            <MetricTile label="最高分" value={(images[0]?.quality_score ?? 0).toFixed(2)} />
          </div>

          <div className="content-grid">
            <section className="visual-panel">
              {selected ? (
                <>
                  <div className="section-heading">
                    <div>
                      <h2>{selected.filename}</h2>
                      <span>图像质量观察区</span>
                    </div>
                    <strong className="big-score">{selected.quality_score.toFixed(2)}</strong>
                  </div>
                  <div className="preview-pair large-preview">
                    <figure>
                      <img src={selected.image_url} alt="成像结果" />
                      <figcaption>图像</figcaption>
                    </figure>
                    <figure>
                      <img src={selected.mask_url} alt="人体区域掩膜" />
                      <figcaption>ROI</figcaption>
                    </figure>
                  </div>
                </>
              ) : (
                <div className="empty-state visual-empty">等待计算图像</div>
              )}
            </section>

            <div className="right-stack">
              <section className="detail-panel">
                {selected ? (
                  <>
                  <div className="rating-box">
                    <SubjectiveRatingPanel
                      scores={subjectiveScoresDraft}
                      notes={notesDraft}
                      busy={busy}
                      onScoreChange={updateSubjectiveScore}
                      onNotesChange={setNotesDraft}
                      onSave={handleSaveRating}
                    />
                  </div>
                  <section className="metric-score-panel">
                    <div className="section-heading compact-heading">
                      <h2>指标量化得分</h2>
                      <span>原始值 / 0-100 得分 / 权重</span>
                    </div>
                    <div className="metric-score-grid">
                      {metricKeys.slice(0, 7).map((key) => (
                        <MetricScoreCard image={selected} metric={key} weight={weights[key]} key={key} />
                      ))}
                    </div>
                  </section>
                  <section className="feature-panel">
                    <div className="section-heading compact-heading">
                      <h2>图像特征</h2>
                      <span>
                        {selected.features?.width ?? '-'} x {selected.features?.height ?? '-'} / {selected.features?.mode ?? '-'}
                      </span>
                    </div>
                    <div className="histogram-grid">
                      <Histogram label="灰度" values={selected.features?.histograms.gray} className="gray" />
                      <Histogram label="R" values={selected.features?.histograms.red} className="red" />
                      <Histogram label="G" values={selected.features?.histograms.green} className="green" />
                      <Histogram label="B" values={selected.features?.histograms.blue} className="blue" />
                    </div>
                  </section>
                  </>
                ) : (
                  <EmptyDetailPanel weights={weights} />
                )}
              </section>
              <section className="image-list compact-ranking">
                <div className="section-heading">
                  <h2>样本排名</h2>
                  <span>{images.length} 张</span>
                </div>
                <div className="tiles">
                  {images.map((image, index) => (
                    <button
                      className={`image-tile ${image.id === selected?.id ? 'active' : ''}`}
                      key={image.id}
                      onClick={() => setSelectedId(image.id)}
                    >
                      <img src={image.image_url} alt={image.filename} />
                      <span className="rank">#{index + 1}</span>
                      <span className="score">{image.quality_score.toFixed(1)}</span>
                      <strong>{image.filename}</strong>
                      <small>{image.algorithm}</small>
                      <small className={image.subjective_rating_complete ? 'rating-status done' : 'rating-status'}>
                        人工 {image.subjective_rating_complete ? image.subjective_rating?.toFixed(1) : '未完成'}
                      </small>
                    </button>
                  ))}
                  {images.length === 0 && <div className="empty-state">等待计算图像</div>}
                </div>
              </section>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

function SubjectiveRatingPanel({
  scores,
  notes,
  busy,
  disabled = false,
  onScoreChange,
  onNotesChange,
  onSave,
}: {
  scores: SubjectiveScores;
  notes: string;
  busy?: boolean;
  disabled?: boolean;
  onScoreChange?: (key: SubjectiveScoreKey, value: number | null) => void;
  onNotesChange?: (value: string) => void;
  onSave?: () => void;
}) {
  return (
    <>
      <div className="subjective-rating-panel">
        <div className="section-heading compact-heading">
          <h2>人工分项评分</h2>
          <span>
            {getCompletedSubjectiveCount(scores)} / 5，均分 {getSubjectiveAverage(scores)?.toFixed(2) ?? '-'}
          </span>
        </div>
        <div className="subjective-score-list">
          {subjectiveScoreKeys.map((key) => (
            <SubjectiveScoreRow
              key={key}
              scoreKey={key}
              value={scores[key]}
              disabled={disabled}
              onChange={onScoreChange}
            />
          ))}
        </div>
      </div>
      <label>
        备注
        <textarea
          value={notes}
          disabled={disabled}
          onChange={(event) => onNotesChange?.(event.target.value)}
        />
      </label>
      <button className="primary-button compact" onClick={onSave} disabled={busy || disabled}>
        <Save size={16} />
        保存
      </button>
    </>
  );
}

function SubjectiveScoreRow({
  scoreKey,
  value,
  disabled,
  onChange,
}: {
  scoreKey: SubjectiveScoreKey;
  value: number | null;
  disabled?: boolean;
  onChange?: (key: SubjectiveScoreKey, value: number | null) => void;
}) {
  return (
    <div className="subjective-score-row">
      <span>{subjectiveScoreLabels[scoreKey]}</span>
      <div className="score-buttons" role="radiogroup" aria-label={subjectiveScoreLabels[scoreKey]}>
        {[1, 2, 3, 4, 5].map((score) => (
          <button
            type="button"
            className={value === score ? 'active' : ''}
            disabled={disabled}
            key={score}
            onClick={() => onChange?.(scoreKey, value === score ? null : score)}
          >
            {score}
          </button>
        ))}
      </div>
    </div>
  );
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-tile">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function MetricScoreCard({ image, metric, weight }: { image: ImageRecord; metric: MetricKey; weight: number }) {
  const normalized = (image.normalized_metrics?.[metric] ?? 0) * 100;
  return (
    <div className="metric-score-card">
      <div>
        <strong>{metricLabels[metric]}</strong>
        <span>原始值 {formatMetric(image.metrics[metric])}</span>
      </div>
      <b>{normalized.toFixed(1)}</b>
      <meter min={0} max={100} value={normalized} />
      <small>权重 {Math.round(weight * 100)}%</small>
    </div>
  );
}

function MetricPlaceholderCard({ metric, weight }: { metric: MetricKey; weight: number }) {
  return (
    <div className="metric-score-card placeholder-card">
      <div>
        <strong>{metricLabels[metric]}</strong>
        <span>原始值 -</span>
      </div>
      <b>-</b>
      <meter min={0} max={100} value={0} />
      <small>权重 {Math.round(weight * 100)}%</small>
    </div>
  );
}

function Histogram({ label, values, className }: { label: string; values?: number[]; className: string }) {
  const path = histogramPath(values, 180, 72);
  return (
    <div className={`histogram-card ${className}`}>
      <span>{label}</span>
      <svg viewBox="0 0 180 72" role="img" aria-label={`${label} 直方图`}>
        <path d={path} />
      </svg>
    </div>
  );
}

function EmptyDetailPanel({ weights }: { weights: Weights }) {
  return (
    <div className="detail-placeholder">
      <div className="section-heading">
        <div>
          <h2>等待计算图像</h2>
          <span>选择文件后，可执行单张计算或计算勾选图片。</span>
        </div>
      </div>
      <div className="rating-box">
        <SubjectiveRatingPanel
          scores={defaultSubjectiveScores()}
          notes=""
          disabled
        />
      </div>
      <section className="metric-score-panel">
        <div className="section-heading compact-heading">
          <h2>指标量化得分</h2>
          <span>原始值 / 0-100 得分 / 权重</span>
        </div>
        <div className="metric-score-grid">
          {metricKeys.slice(0, 7).map((key) => (
            <MetricPlaceholderCard metric={key} weight={weights[key]} key={key} />
          ))}
        </div>
      </section>
      <section className="feature-panel">
        <div className="section-heading compact-heading">
          <h2>图像特征</h2>
          <span>- x - / -</span>
        </div>
        <div className="histogram-grid">
          <Histogram label="灰度" className="gray" />
          <Histogram label="R" className="red" />
          <Histogram label="G" className="green" />
          <Histogram label="B" className="blue" />
        </div>
      </section>
    </div>
  );
}

export default App;
