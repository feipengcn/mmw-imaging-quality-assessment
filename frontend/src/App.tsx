import { FormEvent, InputHTMLAttributes, useEffect, useMemo, useRef, useState } from 'react';
import { BarChart3, Download, FileSpreadsheet, FolderOpen, ImageUp, RotateCcw, Settings2, SlidersHorizontal, Trash2 } from 'lucide-react';
import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer } from 'recharts';
import { deleteImage, fetchImages, resetImages, rescoreImages, uploadImages } from './api';
import { defaultWeights, formatMetric, formatView, metricKeys, metricLabels, normalizeWeights } from './scoring';
import {
  filesToImportEntries,
  formatBytes,
  getSelectedImportEntries,
  type ImportEntry,
} from './importSelection';
import { histogramPath } from './histogram';
import type { ImageRecord, MetricKey, Weights } from './types';

type DirectoryInputProps = InputHTMLAttributes<HTMLInputElement> & {
  webkitdirectory?: string;
  directory?: string;
};

type OverlayMode = 'none' | 'aoi' | 'leakage' | 'stripe';
type SampleSortMode = 'score' | 'name';

type SampleRow = {
  id: string;
  importIndex: number;
  displayLabel: string;
  sortLabel: string;
  importEntry?: ImportEntry;
  image?: ImageRecord;
};

type RawMetricRow = {
  key: string;
  label: string;
  description: string;
};

type RawMetricGroup = {
  dimension: string;
  summary: string;
  items: RawMetricRow[];
};

const apiExportLinks = [
  { href: '/api/export/csv', label: 'CSV', icon: FileSpreadsheet },
  { href: '/api/export/excel', label: 'Excel', icon: Download },
  { href: '/api/report/html', label: 'HTML Report', icon: BarChart3 },
];

const overlayModeLabels: Record<OverlayMode, string> = {
  none: '原图',
  aoi: 'AOI',
  leakage: '伪影溢出带',
  stripe: '饱和条纹区',
};

const rawMetricGroups: RawMetricGroup[] = [
  {
    dimension: '锐度',
    summary: '描述边缘强度和边缘过渡宽度',
    items: [
      {
        key: 'tenengrad_variance',
        label: 'Tenengrad 方差',
        description: '基于 Sobel 梯度能量的方差，反映主体轮廓和局部纹理的清晰程度。原始值越高通常越好。',
      },
      {
        key: 'edge_rise_distance',
        label: '10-90% 上升距离',
        description: '在黄金边缘处统计灰度从 10% 上升到 90% 所跨越的距离。原始值越小越好，分数已转换为越高越好。',
      },
    ],
  },
  {
    dimension: '显著性',
    summary: '描述人体与背景的分离程度',
    items: [
      {
        key: 'cnr',
        label: 'CNR',
        description: '人体区域与深层背景之间的对比噪声比。值越高，说明人体越容易从背景中分离出来。',
      },
    ],
  },
  {
    dimension: '伪影抑制',
    summary: '描述能量外泄、背景脏污和周期条纹',
    items: [
      {
        key: 'leakage_ratio',
        label: '泄漏比',
        description: '人体外环带区域能量相对深层背景能量的比值，用来衡量人体边缘外的能量溢出。原始值越低越好。',
      },
      {
        key: 'background_bright_spot_ratio',
        label: '背景亮点占比',
        description: '深层背景中异常亮点像素的比例，用来量化背景亮斑和散落高亮噪声。原始值越低越好。',
      },
      {
        key: 'background_local_std',
        label: '背景局部标准差',
        description: '深层背景局部标准差的平均值，用来衡量背景均匀性和雾化感。原始值越低越好。',
      },
      {
        key: 'coherent_speckle_index',
        label: '相干斑指数',
        description: '人体内部高频残差的相对强度，用来表征明暗交替的斑马纹和相干斑。原始值越低越好。',
      },
      {
        key: 'pai',
        label: 'PAI',
        description: '频域与列投影联合得到的饱和条纹指数，用来检测接收机饱和引起的周期性条纹。原始值越低越好。',
      },
    ],
  },
  {
    dimension: '结构完整性',
    summary: '描述主体轮廓是否连贯紧凑',
    items: [
      {
        key: 'solidity',
        label: '紧凑度',
        description: '人体掩膜面积与凸包面积之比，越高说明主体越完整，缺口和非物理断裂越少。',
      },
      {
        key: 'component_count',
        label: '连通域数量',
        description: '人体掩膜内部独立连通区域的数量。一般越少越好，1 到 2 个更符合完整人体成像。',
      },
      {
        key: 'body_area_ratio',
        label: '人体面积占比',
        description: '人体掩膜占整幅图像的面积比例。过低通常意味着分割失败或主体过弱。',
      },
    ],
  },
  {
    dimension: '细节保真',
    summary: '描述饱和情况与纹理信息量',
    items: [
      {
        key: 'saturation_ratio',
        label: '饱和占比',
        description: '人体区域中接近饱和的像素占比，用来量化过曝、饱和和强亮斑溢出。原始值越低越好。',
      },
      {
        key: 'roi_entropy',
        label: '信息熵',
        description: '人体 ROI 的灰度直方图熵，用来衡量纹理层次和细节丰富度。原始值通常越高越好。',
      },
    ],
  },
];

function normalizeDisplayPath(path: string): string {
  return path.replace(/\\/g, '/').replace(/^\.\//, '').toLowerCase();
}

function basename(path: string): string {
  return normalizeDisplayPath(path).split('/').pop() ?? '';
}

export function buildSampleRows(
  importEntries: ImportEntry[],
  images: ImageRecord[],
  previousBindings: Map<string, string>,
): { rows: SampleRow[]; bindings: Map<string, string> } {
  const matchedImageIds = new Set<string>();
  const imagesByPath = new Map<string, ImageRecord[]>();
  const imagesByName = new Map<string, ImageRecord[]>();
  const imagesById = new Map<string, ImageRecord>();
  const matchedImagesByEntryId = new Map<string, ImageRecord | undefined>();
  const nextBindings = new Map<string, string>();

  images.forEach((image) => {
    const imagePath = normalizeDisplayPath(image.filename);
    const imageName = basename(image.filename);
    imagesById.set(image.id, image);
    imagesByPath.set(imagePath, [...(imagesByPath.get(imagePath) ?? []), image]);
    imagesByName.set(imageName, [...(imagesByName.get(imageName) ?? []), image]);
  });

  function isExactPathMatch(entry: ImportEntry, image: ImageRecord): boolean {
    const entryPath = normalizeDisplayPath(entry.displayPath);
    return normalizeDisplayPath(image.filename) === entryPath;
  }

  function isBasenameMatch(entry: ImportEntry, image: ImageRecord): boolean {
    return basename(image.filename) === basename(entry.displayPath);
  }

  function assignImage(entry: ImportEntry, image: ImageRecord | undefined) {
    if (!image || matchedImageIds.has(image.id)) return;
    matchedImageIds.add(image.id);
    matchedImagesByEntryId.set(entry.id, image);
    nextBindings.set(entry.id, image.id);
  }

  function takeExactMatch(entry: ImportEntry): ImageRecord | undefined {
    const entryPath = normalizeDisplayPath(entry.displayPath);
    return imagesByPath.get(entryPath)?.find((image) => !matchedImageIds.has(image.id));
  }

  function takeBasenameMatch(entry: ImportEntry): ImageRecord | undefined {
    const entryName = basename(entry.displayPath);
    return imagesByName.get(entryName)?.find((image) => !matchedImageIds.has(image.id));
  }

  importEntries.forEach((entry) => {
    const previousImageId = previousBindings.get(entry.id);
    const previousImage = previousImageId ? imagesById.get(previousImageId) : undefined;
    if (previousImage && isExactPathMatch(entry, previousImage)) {
      assignImage(entry, previousImage);
    }
  });

  importEntries.forEach((entry) => {
    if (matchedImagesByEntryId.get(entry.id)) return;
    const image = takeExactMatch(entry);
    assignImage(entry, image);
  });

  importEntries.forEach((entry) => {
    const previousImageId = previousBindings.get(entry.id);
    const previousImage = previousImageId ? imagesById.get(previousImageId) : undefined;
    if (previousImage && isBasenameMatch(entry, previousImage)) {
      assignImage(entry, previousImage);
    }
  });

  importEntries.forEach((entry) => {
    if (matchedImagesByEntryId.get(entry.id)) return;
    const image = takeBasenameMatch(entry);
    assignImage(entry, image);
  });

  const importRows = importEntries.map((entry, importIndex) => {
    const image = matchedImagesByEntryId.get(entry.id);
    return {
      id: entry.id,
      importIndex,
      displayLabel: entry.displayPath,
      sortLabel: image?.filename ?? entry.displayPath,
      importEntry: entry,
      image,
    };
  });

  const imageRows = images
    .filter((image) => !matchedImageIds.has(image.id))
    .map((image, imageIndex) => ({
      id: image.id,
      importIndex: importEntries.length + imageIndex,
      displayLabel: image.filename,
      sortLabel: image.filename,
      image,
    }));

  return { rows: [...importRows, ...imageRows], bindings: nextBindings };
}

function findCalculatedImageForImportEntry(entry: ImportEntry, rows: SampleRow[]): ImageRecord | undefined {
  return rows.find((row) => row.importEntry?.id === entry.id)?.image;
}

function App() {
  const [images, setImages] = useState<ImageRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeSampleRowId, setActiveSampleRowId] = useState<string | null>(null);
  const [sampleSortMode, setSampleSortMode] = useState<SampleSortMode>('score');
  const [focusCurrentOnly, setFocusCurrentOnly] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [weights, setWeights] = useState<Weights>(defaultWeights);
  const [importMode, setImportMode] = useState<'files' | 'folder'>('files');
  const [importEntries, setImportEntries] = useState<ImportEntry[]>([]);
  const [selectedImportIds, setSelectedImportIds] = useState<Set<string>>(new Set());
  const [overlayMode, setOverlayMode] = useState<OverlayMode>('none');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const sampleRowBindingsRef = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    fetchImages()
      .then((data) => {
        setImages(data.images);
        setWeights(data.weights && Object.keys(data.weights).length > 0 ? normalizeWeights(data.weights) : defaultWeights);
        setSelectedId(data.images[0]?.id ?? null);
      })
      .catch((error) => setMessage(error.message));
  }, []);

  useEffect(() => {
    if (!selectedId && !activeSampleRowId && images.length > 0) {
      setSelectedId(images[0].id);
    }
  }, [activeSampleRowId, images, selectedId]);

  const sampleRowDerivation = useMemo(
    () => buildSampleRows(importEntries, images, sampleRowBindingsRef.current),
    [images, importEntries],
  );
  const sampleRows = sampleRowDerivation.rows;

  useEffect(() => {
    sampleRowBindingsRef.current = sampleRowDerivation.bindings;
  }, [sampleRowDerivation]);
  useEffect(() => {
    if (sampleRows.length === 0) {
      setActiveSampleRowId(null);
      return;
    }

    setActiveSampleRowId((current) => {
      if (current) {
        const currentRow = sampleRows.find((row) => row.id === current);
        if (currentRow && (currentRow.image || !selectedId)) return current;
      }
      if (selectedId) {
        const matchedRow = sampleRows.find((row) => row.image?.id === selectedId);
        if (matchedRow) return matchedRow.id;
      }
      return sampleRows[0].id;
    });
  }, [sampleRows, selectedId]);

  const selected = useMemo(() => {
    if (activeSampleRowId) {
      const activeRow = sampleRows.find((row) => row.id === activeSampleRowId);
      if (activeRow) return activeRow.image;
    }
    return selectedId ? images.find((image) => image.id === selectedId) ?? images[0] : undefined;
  }, [activeSampleRowId, images, sampleRows, selectedId]);
  const orderedRows = useMemo(() => {
    return [...sampleRows].sort((left, right) => {
      if (sampleSortMode === 'name') {
        return left.sortLabel.localeCompare(right.sortLabel, 'zh-CN');
      }
      return (right.image?.quality_score ?? -1) - (left.image?.quality_score ?? -1);
    });
  }, [sampleRows, sampleSortMode]);
  const visibleRows = useMemo(() => {
    if (!focusCurrentOnly || !activeSampleRowId) return orderedRows;
    return orderedRows.filter((row) => row.id === activeSampleRowId);
  }, [activeSampleRowId, focusCurrentOnly, orderedRows]);
  const summary = useMemo(() => {
    const count = images.length;
    const avg = count ? images.reduce((sum, image) => sum + image.quality_score, 0) / count : 0;
    const best = count ? images.reduce((max, image) => Math.max(max, image.quality_score), Number.NEGATIVE_INFINITY) : 0;
    return { count, avg, best };
  }, [images]);
  const selectedImportEntries = useMemo(() => getSelectedImportEntries(importEntries, selectedImportIds), [importEntries, selectedImportIds]);
  const directoryInputProps: DirectoryInputProps = importMode === 'folder' ? { webkitdirectory: '', directory: '' } : {};

  async function handleImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await handleCalculateSelected();
  }

  async function handleCalculateSelected() {
    await runCalculation(getSelectedImportEntries(importEntries, selectedImportIds), 'selected');
  }

  async function runCalculation(entries: ImportEntry[], mode: 'selected' | 'current') {
    if (!entries.length) {
      setMessage(mode === 'current' ? '请先选择当前预览文件。' : '请至少勾选一个图像文件。');
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
      setMessage(`已完成 ${data.imported} 张图像的质量计算。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '计算失败。');
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

  async function handleReset() {
    const confirmed = window.confirm('确定清空所有已导入图像、掩膜和评分记录吗？');
    if (!confirmed) return;

    setBusy(true);
    try {
      const data = await resetImages();
      setImages(data.images);
      setSelectedId(null);
      setMessage('数据已清空。');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '清空失败。');
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteImage(image: ImageRecord) {
    const confirmed = window.confirm(`确定删除 ${image.filename} 吗？`);
    if (!confirmed) return;

    setBusy(true);
    try {
      const data = await deleteImage(image.id);
      setImages(data.images);
      setSelectedId((current) => {
        if (current && data.images.some((item) => item.id === current)) return current;
        return data.images[0]?.id ?? null;
      });
      setMessage(`已删除 ${image.filename}。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '删除失败。');
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteSelectedImages() {
    const ids = getSelectedImportEntries(importEntries, selectedImportIds)
      .map((entry) => findCalculatedImageForImportEntry(entry, sampleRows)?.id)
      .filter((id): id is string => Boolean(id));

    if (!ids.length) return;

    setBusy(true);
    try {
      for (const id of ids) {
        await deleteImage(id);
      }

      const data = await fetchImages();
      setImages(data.images);
      setSelectedImportIds(new Set());
      setSelectedId((current) => (current && data.images.some((item) => item.id === current) ? current : data.images[0]?.id ?? null));
      setMessage(`已删除 ${ids.length} 个选中样本。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '删除失败。');
    } finally {
      setBusy(false);
    }
  }

  function handleImportFiles(nextFiles: FileList | null) {
    const entries = filesToImportEntries(nextFiles ?? []);
    setImportEntries(entries);
    setSelectedImportIds(new Set(entries.map((entry) => entry.id)));
    setMessage(entries.length ? `已选择 ${entries.length} 个图像文件。` : '没有找到可导入的图像文件。');
  }

  function handleSelectAllImportEntries() {
    setSelectedImportIds(new Set(importEntries.map((entry) => entry.id)));
  }

  function handleClearSelectedImportEntries() {
    setSelectedImportIds(new Set());
  }

  function handleToggleFocusCurrentOnly() {
    setFocusCurrentOnly((current) => !current);
  }

  function handleSampleRowSelect(row: SampleRow) {
    setActiveSampleRowId(row.id);
    if (row.image) {
      setSelectedId(row.image.id);
      return;
    }
    setSelectedId(null);
  }

  function toggleImportEntry(id: string) {
    setSelectedImportIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>毫米波人体成像质量评估</h1>
          <p>面向 mmWave 图像的物理指标评分与样本排序</p>
        </div>
        <div className="actions">
          {apiExportLinks.map(({ href, label, icon: Icon }) => (
            <a className="icon-button text-button" href={href} key={href} target="_blank" rel="noreferrer">
              <Icon size={17} />
              {label}
            </a>
          ))}
          <div className="settings-menu">
            <button
              type="button"
              className={`icon-button text-button ${settingsOpen ? 'active' : ''}`}
              onClick={() => setSettingsOpen((current) => !current)}
              aria-expanded={settingsOpen}
              aria-controls="topbar-settings-panel"
              title="设置"
            >
              <Settings2 size={17} />
              设置
            </button>
            {settingsOpen && (
              <div className="settings-panel" id="topbar-settings-panel">
                <div className="settings-panel-heading">
                  <SlidersHorizontal size={17} />
                  <strong>权重控制</strong>
                </div>
                <div className="settings-weight-list">
                  {metricKeys.map((key) => (
                    <label className="slider-row" key={key}>
                      <span>{metricLabels[key]}</span>
                      <input type="range" min="0" max="1" step="0.01" value={weights[key] ?? 0} onChange={(event) => void handleWeightChange(key, Number(event.target.value))} />
                      <b>{Math.round((weights[key] ?? 0) * 100)}%</b>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
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
            {message && <p className="status-line">{message}</p>}
          </form>

          <section className="sample-list">
            <div className="section-heading compact-heading">
              <div>
                <h2>样本列表</h2>
                <span>按综合质量分从高到低排序，直接在左侧浏览和切换当前样本。</span>
              </div>
              <div className="sample-list-toolbar">
                <div className="segmented-control" role="tablist" aria-label="样本列表">
                  <button type="button" className={sampleSortMode === 'score' ? 'active' : ''} onClick={() => setSampleSortMode('score')}>
                    按得分
                  </button>
                  <button type="button" className={sampleSortMode === 'name' ? 'active' : ''} onClick={() => setSampleSortMode('name')}>
                    按名称
                  </button>
                </div>
                <span>{visibleRows.length} 张</span>
              </div>
            </div>
            <div className="sample-list-action-bar">
              <button type="button" className="secondary-button" disabled={busy || !selectedImportEntries.length} onClick={() => void handleCalculateSelected()}>
                计算选中
              </button>
              <button type="button" className={focusCurrentOnly ? 'active' : ''} aria-pressed={focusCurrentOnly} onClick={handleToggleFocusCurrentOnly}>
                只看当前
              </button>
              <button type="button" onClick={handleSelectAllImportEntries} disabled={!importEntries.length}>
                全选
              </button>
              <button type="button" onClick={handleClearSelectedImportEntries} disabled={!selectedImportIds.size}>
                清空
              </button>
              <button
                type="button"
                className="danger"
                disabled={busy || !selectedImportEntries.some((entry) => findCalculatedImageForImportEntry(entry, sampleRows))}
                onClick={() => void handleDeleteSelectedImages()}
              >
                删除选中
              </button>
            </div>
            <div className="tiles ranking-tiles">
              {visibleRows.map((row, index) => {
                const image = row.image;
                const importEntry = row.importEntry;
                const isSelected = row.id === activeSampleRowId;
                const isImportChecked = importEntry ? selectedImportIds.has(importEntry.id) : false;

                return (
                  <div className="ranking-tile-shell" key={row.id}>
                    {importEntry && (
                      <input
                        type="checkbox"
                        checked={isImportChecked}
                        onChange={() => toggleImportEntry(importEntry.id)}
                        onClick={(event) => event.stopPropagation()}
                        aria-label={`选择 ${row.displayLabel}`}
                      />
                    )}
                    {image ? (
                      <>
                        <button
                          type="button"
                          className="tile-delete-button"
                          aria-label={`删除 ${image.filename}`}
                          onClick={() => void handleDeleteImage(image)}
                          disabled={busy}
                        >
                          <Trash2 size={14} />
                        </button>
                        <button
                          type="button"
                          className={`image-tile sample-row-card ${isSelected ? 'active' : ''}`}
                          aria-label={row.displayLabel}
                          onClick={() => handleSampleRowSelect(row)}
                          disabled={busy}
                        >
                          <img src={image.image_url} alt={image.filename} />
                          <RadarSpark image={image} />
                          <span className="rank">#{index + 1}</span>
                          <span className="score">{image.quality_score.toFixed(1)}</span>
                          <strong title={row.displayLabel}>{row.displayLabel}</strong>
                          <small>{formatView(image.view)} 路 {formatConfidence(image.view_confidence)}</small>
                          <small className={image.valid_sample ? 'rating-status done' : 'rating-status'}>{image.valid_sample ? '链路有效' : '链路无效'}</small>
                        </button>
                      </>
                    ) : (
                        <button
                          type="button"
                          className={`image-tile sample-row-card ${isSelected ? 'active' : ''}`}
                          aria-label={row.displayLabel}
                          onClick={() => handleSampleRowSelect(row)}
                          disabled={busy}
                        >
                        <span className="rank">#{index + 1}</span>
                        <strong title={row.displayLabel}>{row.displayLabel}</strong>
                        <small>{row.importEntry ? formatBytes(row.importEntry.size) : ''}</small>
                        <small className="rating-status">等待计算</small>
                      </button>
                    )}
                  </div>
                );
              })}
              {visibleRows.length === 0 && <div className="empty-state">等待计算图像</div>}
            </div>
          </section>
        </aside>

        <section className="main-panel">
          <div className="content-grid">
            <section className="visual-panel">
              <div className="section-heading visual-heading">
                <div>
                  <h2>{selected?.filename ?? '等待计算图像'}</h2>
                  <span>图像质量观察区</span>
                </div>
                <div className="visual-heading-meta">
                  <div className="summary-strip compact-summary">
                    <MetricTile label="样本数" value={String(summary.count)} />
                    <MetricTile label="平均总分" value={summary.avg.toFixed(2)} />
                    <MetricTile label="最高分" value={summary.best.toFixed(2)} />
                  </div>
                  <strong className="big-score">{selected ? selected.quality_score.toFixed(2) : '--'}</strong>
                </div>
              </div>
              {!selected && (
                <div className="overlay-toggle-row" role="tablist" aria-label="观察图层">
                  {(['none', 'aoi', 'leakage', 'stripe'] as OverlayMode[]).map((mode) => (
                    <button type="button" key={mode} className={overlayMode === mode ? 'active' : ''} disabled>
                      {overlayModeLabels[mode]}
                    </button>
                  ))}
                </div>
              )}
              {selected ? (
                <>
                  <div className="viewer-layout">
                    <div className="overlay-panel-shell portrait-viewer">
                      <div className="overlay-toggle-row" role="tablist" aria-label="观察图层">
                        {(['none', 'aoi', 'leakage', 'stripe'] as OverlayMode[]).map((mode) => (
                          <button
                            type="button"
                            key={mode}
                            className={overlayMode === mode ? 'active' : ''}
                            onClick={() => setOverlayMode(mode)}
                            disabled={!selected}
                          >
                            {overlayModeLabels[mode]}
                          </button>
                        ))}
                      </div>
                      <div className="single-preview-shell">
                        <div className="single-preview-stage">
                          <img src={selected.image_url} alt="成像结果" className="single-preview-image" />
                          {overlayMode !== 'none' && selected.overlay_urls?.[overlayMode] && (
                            <img src={selected.overlay_urls[overlayMode]} alt={overlayModeLabels[overlayMode]} className="single-preview-overlay" />
                          )}
                        </div>
                        <span className="overlay-caption">{overlayMode === 'none' ? '当前显示：原图' : `当前叠加：${overlayModeLabels[overlayMode]}`}</span>
                      </div>
                    </div>
                    <FeaturePanel image={selected} />
                  </div>
                </>
              ) : (
                <div className="empty-state visual-empty">等待计算图像</div>
              )}

            </section>

            <section className="detail-panel">
              {selected ? (
                <>
                  <StatusChips image={selected} />
                  <section className="radar-panel">
                    <div className="section-heading compact-heading">
                      <div>
                        <h2>质量雷达图</h2>
                        <span>所有维度都已转换为“越高越好”。</span>
                      </div>
                    </div>
                    <RadarScoreChart image={selected} />
                  </section>
                  <section className="metric-score-panel">
                    <div className="section-heading compact-heading">
                      <div>
                        <h2>物理指标</h2>
                        <span>左侧是原始计量值，右侧是换算后的得分 / 满分。</span>
                      </div>
                    </div>
                    <RawMetricTable image={selected} />
                  </section>
                </>
              ) : (
                <EmptyDetailPanel weights={weights} />
              )}
            </section>
          </div>
        </section>
      </main>
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

function RadarScoreChart({ image }: { image: ImageRecord }) {
  const data = metricKeys.map((key) => ({
    metric: metricLabels[key],
    score: Math.round((image.normalized_metrics?.[key] ?? 0) * 100),
  }));
  return (
    <div className="radar-chart-shell">
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={data} outerRadius="72%">
          <PolarGrid stroke="#d0d5dd" />
          <PolarAngleAxis dataKey="metric" tick={{ fill: '#475467', fontSize: 12 }} />
          <Radar dataKey="score" stroke="#0f766e" fill="#14b8a6" fillOpacity={0.28} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

function RadarSpark({ image }: { image: ImageRecord }) {
  const values = metricKeys.map((key) => image.normalized_metrics?.[key] ?? 0);
  const center = 24;
  const radius = 19;
  const points = values
    .map((value, index) => {
      const angle = (-Math.PI / 2) + (index / values.length) * Math.PI * 2;
      const x = center + Math.cos(angle) * radius * value;
      const y = center + Math.sin(angle) * radius * value;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  return (
    <svg className="tile-radar" viewBox="0 0 48 48" aria-hidden="true">
      <circle cx="24" cy="24" r="19" className="tile-radar-ring" />
      <polygon points={points} className="tile-radar-fill" />
    </svg>
  );
}

function RawMetricTable({ image }: { image: ImageRecord }) {
  const maxScore = image.metric_score_max ?? 100;
  return (
    <div className="raw-metric-table">
      {rawMetricGroups.map((group) => (
        <section className="raw-metric-group" key={group.dimension}>
          <div className="raw-metric-group-header">
            <strong>{group.dimension}</strong>
            <span>{group.summary}</span>
          </div>
          <div className="raw-metric-group-body">
            {group.items.map((row) => (
              <div className="raw-metric-row" key={row.key}>
                <div className="raw-metric-name">
                  <span className="metric-tooltip">
                    <span className="metric-tooltip-label" tabIndex={0}>
                      {row.label}
                    </span>
                    <span className="metric-tooltip-bubble" role="tooltip">
                      {row.description}
                    </span>
                  </span>
                </div>
                <div className="raw-metric-values">
                  <strong>{formatMetric(image.metrics[row.key])}</strong>
                  <small>
                    {formatMetric(image.metric_scores?.[row.key])} / {maxScore}
                  </small>
                </div>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function StatusChips({ image }: { image: ImageRecord }) {
  return (
    <div className="status-chip-row">
      <span className={`status-chip ${image.valid_sample ? 'ok' : 'warn'}`}>{image.valid_sample ? '有效样本' : '无效样本'}</span>
      <span className="status-chip">{`视角：${formatView(image.view)}`}</span>
      <span className="status-chip">{formatConfidence(image.view_confidence)}</span>
      {image.penalty_flags?.saturation && <span className="status-chip danger">饱和惩罚</span>}
      {image.penalty_flags?.pai && <span className="status-chip danger">条纹惩罚</span>}
    </div>
  );
}

function FeaturePanel({ image }: { image: ImageRecord }) {
  return (
    <section className="feature-observer-panel">
      <div className="section-heading compact-heading">
        <h2>图像特征</h2>
        <span>
          {image.features?.width ?? '-'} x {image.features?.height ?? '-'} / {image.features?.mode ?? '-'}
        </span>
      </div>
      <div className="feature-summary-grid">
        <div className="feature-stat-card">
          <span>分辨率</span>
          <strong>
            {image.features?.width ?? '-'} x {image.features?.height ?? '-'}
          </strong>
        </div>
        <div className="feature-stat-card">
          <span>颜色模式</span>
          <strong>{image.features?.mode ?? '-'}</strong>
        </div>
      </div>
      <div className="feature-histogram-grid">
        <Histogram label="灰度" values={image.features?.histograms.gray} className="gray compact" />
        <Histogram label="R" values={image.features?.histograms.red} className="red compact" />
        <Histogram label="G" values={image.features?.histograms.green} className="green compact" />
        <Histogram label="B" values={image.features?.histograms.blue} className="blue compact" />
      </div>
    </section>
  );
}

function Histogram({ label, values, className }: { label: string; values?: number[]; className: string }) {
  const path = histogramPath(values, 180, 72, 'log');
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
          <span>选择文件后，可以执行单张计算或计算勾选图像。</span>
        </div>
      </div>
      <section className="radar-panel">
        <div className="section-heading compact-heading">
          <h2>质量雷达图</h2>
          <span>五维评分</span>
        </div>
        <div className="radar-chart-shell placeholder-shell">
          {metricKeys.map((key) => (
            <div className="placeholder-weight-row" key={key}>
              <span>{metricLabels[key]}</span>
              <strong>{Math.round((weights[key] ?? 0) * 100)}%</strong>
            </div>
          ))}
        </div>
      </section>
      <section className="metric-score-panel">
        <div className="section-heading compact-heading">
          <h2>物理指标</h2>
          <span>原始 mmWave 计量值</span>
        </div>
        <div className="raw-metric-table">
          {rawMetricGroups.map((group) => (
            <section className="raw-metric-group" key={group.dimension}>
              <div className="raw-metric-group-header">
                <strong>{group.dimension}</strong>
                <span>{group.summary}</span>
              </div>
              <div className="raw-metric-group-body">
                {group.items.map((row) => (
                  <div className="raw-metric-row" key={row.key}>
                    <div className="raw-metric-name">
                      <span>{row.label}</span>
                    </div>
                    <div className="raw-metric-values">
                      <strong>-</strong>
                      <small>- / 100</small>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      </section>
    </div>
  );
}

function formatConfidence(confidence: number | undefined): string {
  if (confidence === undefined || Number.isNaN(confidence)) return '置信度 -';
  return `置信度 ${(confidence * 100).toFixed(1)}%`;
}

export default App;
