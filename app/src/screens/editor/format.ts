/**
 * Presentation helpers for computed results: values arrive in SI from the API. Technical
 * numbers use a decimal point, as the number fields do.
 */
const numberFormats = new Map<number, Intl.NumberFormat>();

export function fmt(value: number, digits = 1): string {
  let format = numberFormats.get(digits);
  if (!format) {
    format = new Intl.NumberFormat("en-US", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
      useGrouping: false,
    });
    numberFormats.set(digits, format);
  }
  return format.format(value);
}

/** Up to `digits` decimals, without trailing zeros: "8", "2.5". */
export function fmtUpTo(value: number, digits = 1): string {
  return Number(value.toFixed(digits)).toString();
}

export const deg = (rad: number, digits = 1) => fmt((rad * 180) / Math.PI, digits);
export const km = (m: number, digits = 0) => fmt(m / 1000, digits);
export const minutes = (s: number, digits = 1) => fmt(s / 60, digits);

/** "23:40": minutes and seconds of a time within an orbit. */
export function clock(s: number): string {
  const total = Math.floor(s);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

export function date(iso: string): string {
  return iso.slice(0, 10);
}
