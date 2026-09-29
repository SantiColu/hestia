import { readText, writeText } from "@tauri-apps/plugin-clipboard-manager";
import { isTauri } from "./native";

/**
 * Plain-text system clipboard: the Tauri plugin on the desktop, `navigator.clipboard` in the
 * browser. The last text written is also kept in memory, so copy and paste inside the app
 * work even when the browser denies clipboard access.
 */
let lastWritten: string | null = null;

export async function writeClipboardText(text: string): Promise<void> {
  lastWritten = text;
  try {
    if (isTauri()) await writeText(text);
    else await navigator.clipboard.writeText(text);
  } catch {
    // Kept in memory: pasting inside this window still works.
  }
}

/** The clipboard text, or the last text written by the app if the clipboard can't be read. */
export async function readClipboardText(): Promise<string | null> {
  try {
    return isTauri() ? await readText() : await navigator.clipboard.readText();
  } catch {
    return lastWritten;
  }
}
