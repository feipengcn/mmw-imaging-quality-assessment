import { describe, expect, it } from 'vitest';
import {
  filesToImportEntries,
  getNextImportSelectionIndex,
  getSelectedImportEntries,
  summarizeImportSelection,
} from './importSelection';

function makeFile(name: string, size = 128, path = '') {
  const file = new File(['x'.repeat(size)], name, { type: 'image/png' });
  Object.defineProperty(file, 'webkitRelativePath', {
    value: path,
    configurable: true,
  });
  return file;
}

describe('import selection helpers', () => {
  it('keeps folder relative paths and filters non-image files', () => {
    const files = [
      makeFile('a.png', 100, 'group-a/a.png'),
      new File(['notes'], 'notes.txt', { type: 'text/plain' }),
      makeFile('b.tif', 200, 'group-a/nested/b.tif'),
    ];

    const entries = filesToImportEntries(files);

    expect(entries).toHaveLength(2);
    expect(entries.map((entry) => entry.displayPath)).toEqual([
      'group-a/a.png',
      'group-a/nested/b.tif',
    ]);
    expect(entries[1].extension).toBe('tif');
  });

  it('summarizes large folder selections for the import panel', () => {
    const entries = filesToImportEntries([
      makeFile('a.png', 100, 'g/a.png'),
      makeFile('b.png', 300, 'g/b.png'),
    ]);

    expect(summarizeImportSelection(entries)).toEqual({
      count: 2,
      totalBytes: 400,
      firstPath: 'g/a.png',
    });
  });

  it('supports keyboard movement through the full selected file list', () => {
    expect(getNextImportSelectionIndex(1, 'ArrowDown', 4)).toBe(2);
    expect(getNextImportSelectionIndex(3, 'ArrowDown', 4)).toBe(3);
    expect(getNextImportSelectionIndex(1, 'ArrowUp', 4)).toBe(0);
    expect(getNextImportSelectionIndex(0, 'ArrowUp', 4)).toBe(0);
    expect(getNextImportSelectionIndex(2, 'Home', 4)).toBe(0);
    expect(getNextImportSelectionIndex(2, 'End', 4)).toBe(3);
  });

  it('returns only checked files for single or multi-image calculation', () => {
    const entries = filesToImportEntries([
      makeFile('a.png', 100, 'g/a.png'),
      makeFile('b.png', 100, 'g/b.png'),
      makeFile('c.png', 100, 'g/c.png'),
    ]);

    const selected = getSelectedImportEntries(entries, new Set([entries[0].id, entries[2].id]));

    expect(selected.map((entry) => entry.displayPath)).toEqual(['g/a.png', 'g/c.png']);
  });
});
