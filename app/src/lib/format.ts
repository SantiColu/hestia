/** Text formatting for the UI (Spanish copy). Presentation only: no domain values. */

/** "14:32". */
export const timeFormat = new Intl.DateTimeFormat("es-AR", {
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

/** "12 sep. 2026". */
export const dateFormat = new Intl.DateTimeFormat("es-AR", { dateStyle: "medium" });

/** "1 cambio" / "3 cambios". */
export function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

/** "A", "A y B", "A, B y C"; past `max` items, "A, B, C y 6 más". */
export function joinList(items: string[], max = Infinity): string {
  if (items.length > max) return `${items.slice(0, max).join(", ")} y ${items.length - max} más`;
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} y ${items[items.length - 1]}`;
}
