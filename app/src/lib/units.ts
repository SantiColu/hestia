/**
 * Display units (ADR 0017): the API stores SI and kelvin; each field's JSON Schema declares
 * `x-unit` and `x-display-unit`. The UI converts only to show and to read back what is typed.
 */

type Conversion = { scale: number; offset: number };

const YEAR_S = 365.25 * 86400;

/** display = si * scale + offset */
const CONVERSIONS: Record<string, Conversion> = {
  "m→km": { scale: 1e-3, offset: 0 },
  "rad→°": { scale: 180 / Math.PI, offset: 0 },
  "s→años": { scale: 1 / YEAR_S, offset: 0 },
  "s→h": { scale: 1 / 3600, offset: 0 },
  // Absolute temperature only: differences (ΔT) declare K → K.
  "K→°C": { scale: 1, offset: -273.15 },
};

function conversion(unit?: string, displayUnit?: string): Conversion {
  if (!unit || !displayUnit || unit === displayUnit) return { scale: 1, offset: 0 };
  return CONVERSIONS[`${unit}→${displayUnit}`] ?? { scale: 1, offset: 0 };
}

export function toDisplay(value: number, unit?: string, displayUnit?: string): number {
  const { scale, offset } = conversion(unit, displayUnit);
  // Round away binary noise (e.g. 98.60000000000001) without losing typed precision.
  return Number((value * scale + offset).toPrecision(12));
}

export function fromDisplay(value: number, unit?: string, displayUnit?: string): number {
  const { scale, offset } = conversion(unit, displayUnit);
  return (value - offset) / scale;
}
