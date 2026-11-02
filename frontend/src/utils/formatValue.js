// Feature values from the real backend arrive as raw floats
// (e.g. 235.62711174009996); show at most two decimals. Strings
// (e.g. "7 / 15"), integers and missing values pass through unchanged.
const formatter = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });

export function formatValue(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return value;
  return formatter.format(value);
}
