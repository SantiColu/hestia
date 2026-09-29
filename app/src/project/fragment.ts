import type { Fragment } from "@/api/client";
import { readClipboardText, writeClipboardText } from "@/lib/clipboard";

/** Marker of a Hestia fragment (ADR 0014). The API validates everything else on paste. */
const FRAGMENT_KIND = "hestia.fragment";

/** The fragment in `text`, or null if it is not one (plain text, other JSON…). */
export function parseFragment(text: string | null): Fragment | null {
  if (!text) return null;
  try {
    const value: unknown = JSON.parse(text);
    if (typeof value === "object" && value !== null && "kind" in value) {
      return value.kind === FRAGMENT_KIND ? (value as Fragment) : null;
    }
  } catch {
    // Not JSON: not a fragment.
  }
  return null;
}

/** Put a fragment in the system clipboard as JSON text, so it can be pasted in any project. */
export function writeFragment(fragment: Fragment): Promise<void> {
  return writeClipboardText(JSON.stringify(fragment, null, 2));
}

export async function readFragment(): Promise<Fragment | null> {
  return parseFragment(await readClipboardText());
}
