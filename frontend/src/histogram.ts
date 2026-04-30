type HistogramScale = 'linear' | 'log';

export function histogramPath(
  values: number[] | undefined,
  width: number,
  height: number,
  scale: HistogramScale = 'linear',
): string {
  if (!values?.length) return '';
  const scaledValues = values.map((value) => scaleValue(value, scale));
  const max = Math.max(...scaledValues);
  const denominator = max > 0 ? max : 1;
  const step = values.length > 1 ? width / (values.length - 1) : 0;
  return scaledValues
    .map((value, index) => {
      const x = round(index * step);
      const y = round(height - (value / denominator) * height);
      return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
    })
    .join(' ');
}

function scaleValue(value: number, scale: HistogramScale): number {
  return scale === 'log' ? Math.log1p(Math.max(0, value)) : value;
}

function round(value: number): string {
  return Number(value.toFixed(2)).toString();
}
