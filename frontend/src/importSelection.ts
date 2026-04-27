const IMAGE_EXTENSIONS = new Set(['png', 'jpg', 'jpeg', 'tif', 'tiff', 'bmp']);

export interface ImportEntry {
  id: string;
  file: File;
  name: string;
  displayPath: string;
  extension: string;
  size: number;
}

export interface ImportSelectionSummary {
  count: number;
  totalBytes: number;
  firstPath: string;
}

export function filesToImportEntries(files: Iterable<File>): ImportEntry[] {
  return Array.from(files)
    .map((file, index) => toImportEntry(file, index))
    .filter((entry): entry is ImportEntry => entry !== null)
    .sort((a, b) => a.displayPath.localeCompare(b.displayPath, undefined, { numeric: true }));
}

export function summarizeImportSelection(entries: ImportEntry[]): ImportSelectionSummary {
  return {
    count: entries.length,
    totalBytes: entries.reduce((sum, entry) => sum + entry.size, 0),
    firstPath: entries[0]?.displayPath ?? '',
  };
}

export function getNextImportSelectionIndex(currentIndex: number, key: string, total: number): number {
  if (total <= 0) return -1;
  const current = Math.max(0, Math.min(currentIndex, total - 1));
  if (key === 'ArrowDown') return Math.min(total - 1, current + 1);
  if (key === 'ArrowUp') return Math.max(0, current - 1);
  if (key === 'Home') return 0;
  if (key === 'End') return total - 1;
  return current;
}

export function getSelectedImportEntries(entries: ImportEntry[], selectedIds: Set<string>): ImportEntry[] {
  return entries.filter((entry) => selectedIds.has(entry.id));
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function toImportEntry(file: File, index: number): ImportEntry | null {
  const displayPath = getDisplayPath(file);
  const extension = displayPath.split('.').pop()?.toLowerCase() ?? '';
  if (!IMAGE_EXTENSIONS.has(extension)) return null;
  return {
    id: `${displayPath}-${file.size}-${file.lastModified}-${index}`,
    file,
    name: file.name,
    displayPath,
    extension,
    size: file.size,
  };
}

function getDisplayPath(file: File): string {
  const folderPath = (file as File & { webkitRelativePath?: string }).webkitRelativePath;
  return folderPath || file.name;
}
