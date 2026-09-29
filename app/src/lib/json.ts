/** Plain JSON helpers for form drafts (no domain logic). */

export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
export type JsonObject = { [key: string]: Json };
/** A path into a JSON value: object keys and array indexes. */
export type JsonPath = (string | number)[];

export function deepEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (typeof a !== typeof b || a === null || b === null || typeof a !== "object") return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  if (Array.isArray(a) && Array.isArray(b)) {
    return a.length === b.length && a.every((item, i) => deepEqual(item, b[i]));
  }
  const ao = a as Record<string, unknown>;
  const bo = b as Record<string, unknown>;
  const keys = new Set([...Object.keys(ao), ...Object.keys(bo)]);
  for (const key of keys) if (!deepEqual(ao[key], bo[key])) return false;
  return true;
}

export function getAt(value: Json | undefined, path: JsonPath): Json | undefined {
  let current: Json | undefined = value;
  for (const key of path) {
    if (current === null || typeof current !== "object") return undefined;
    current = Array.isArray(current)
      ? current[key as number]
      : (current as JsonObject)[key as string];
  }
  return current;
}

/** A copy of `value` with `path` set to `next` (structural sharing elsewhere). */
export function setAt(value: Json, path: JsonPath, next: Json): Json {
  if (path.length === 0) return next;
  const [key, ...rest] = path;
  if (Array.isArray(value)) {
    const copy = [...value];
    copy[key as number] = setAt(copy[key as number] ?? {}, rest, next);
    return copy;
  }
  const object = value !== null && typeof value === "object" ? value : {};
  return { ...object, [key as string]: setAt(object[key as string] ?? {}, rest, next) };
}

/** `orbit.altitude`, `attitude_modes[0].name`: the API's field path notation. */
export function formatPath(path: JsonPath): string {
  return path
    .map((key, i) => (typeof key === "number" ? `[${key}]` : i === 0 ? key : `.${key}`))
    .join("");
}
