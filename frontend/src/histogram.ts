export function histogramPath(values: number[] | undefined, width: number, height: number): string {
  if (!values?.length) return '';
  const max = Math.max(...values);
  const denominator = max > 0 ? max : 1;
  const step = values.length > 1 ? width / (values.length - 1) : 0;
  return values
    .map((value, index) => {
      const x = round(index * step);
      const y = round(height - (value / denominator) * height);
      return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
    })
    .join(' ');
}

function round(value: number): string {
  return Number(value.toFixed(2)).toString();
}
