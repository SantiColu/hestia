/** Hex digits of an id: as many as the backend generates (`hestia_project.schematic.new_id`). */
const ID_HEX_DIGITS = 10;

/**
 * A new id for an item of an artifact's list, `<prefix>_<hex>` (ADR 0025). The client proposes
 * it so the draft can reference the item before it is applied; the API keeps it if it is valid
 * and unique. A format, not a domain rule.
 */
export function newId(prefix: string): string {
  const bytes = crypto.getRandomValues(new Uint8Array(Math.ceil(ID_HEX_DIGITS / 2)));
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${prefix}_${hex.slice(0, ID_HEX_DIGITS)}`;
}
