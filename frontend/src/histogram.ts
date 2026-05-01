type HistogramScale = 'linear' | 'log';

export function histogramPath(
  values: number[] | undefined,
  width: number,
  height: number,
  scale: HistogramScale = 'linear',
): string {
  return histogramPoints(values, width, height, scale)
    .map(({ x, y }, index) => `${index === 0 ? 'M' : 'L'} ${x} ${y}`)
    .join(' ');
}

export function histogramAreaPath(
  values: number[] | undefined,
  width: number,
  height: number,
  scale: HistogramScale = 'linear',
): string {
  const points = histogramPoints(values, width, height, scale);
  if (!points.length) return '';
  const line = points.map(({ x, y }, index) => `${index === 0 ? 'M' : 'L'} ${x} ${y}`).join(' ');
  return `${line} L ${round(width)} ${round(height)} L 0 ${round(height)} Z`;
}

function histogramPoints(
  values: number[] | undefined,
  width: number,
  height: number,
  scale: HistogramScale,
): Array<{ x: string; y: string }> {
  if (!values?.length) return [];
  const scaledValues = values.map((value) => scaleValue(value, scale));
  const max = Math.max(...scaledValues);
  const denominator = max > 0 ? max : 1;
  const step = values.length > 1 ? width / (values.length - 1) : 0;
  return scaledValues
    .map((value, index) => {
      const x = round(index * step);
      const y = round(height - (value / denominator) * height);
      return { x, y };
    });
}

function scaleValue(value: number, scale: HistogramScale): number {
  return scale === 'log' ? Math.log1p(Math.max(0, value)) : value;
}

function round(value: number): string {
  return Number(value.toFixed(2)).toString();
}
