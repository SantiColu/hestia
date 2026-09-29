import { useEffect, useRef } from "react";

export type ShortcutAction =
  | "new"
  | "open"
  | "save"
  | "saveAs"
  | "close"
  | "undo"
  | "redo"
  | "cut"
  | "copy"
  | "paste"
  | "duplicate"
  | "rename"
  | "delete"
  | "clearSelection";

export type Shortcuts = Partial<Record<ShortcutAction, () => void>>;

/** Edit shortcuts that text fields, dialogs and open menus keep for themselves. */
const EDIT_ACTIONS = new Set<ShortcutAction>([
  "undo",
  "redo",
  "cut",
  "copy",
  "paste",
  "duplicate",
  "rename",
  "delete",
  "clearSelection",
]);

function isTextInput(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

/** Focus is where the schematic's edit shortcuts must not act (typing, a dialog, a menu). */
function keepsEditKeys(target: EventTarget | null): boolean {
  if (isTextInput(target)) return true;
  return (
    target instanceof Element &&
    target.closest('[role="dialog"], [role="alertdialog"], [role="menu"]') !== null
  );
}

/** Text selected on the page (e.g. in Messages): Ctrl+C / Ctrl+X copy that text natively. */
function hasTextSelection(): boolean {
  const selection = window.getSelection();
  return selection !== null && !selection.isCollapsed && selection.toString().trim() !== "";
}

function actionFor(event: KeyboardEvent): ShortcutAction | undefined {
  const key = event.key.toLowerCase();
  if (event.altKey) return undefined;
  if (!(event.ctrlKey || event.metaKey)) {
    if (event.shiftKey) return undefined;
    if (event.key === "F2") return "rename";
    if (event.key === "Delete") return "delete";
    if (event.key === "Escape") return "clearSelection";
    return undefined;
  }
  if (key === "s") return event.shiftKey ? "saveAs" : "save";
  if (key === "z") return event.shiftKey ? "redo" : "undo";
  if (key === "y" && !event.shiftKey) return "redo";
  if (event.shiftKey) return undefined;
  const plain: Record<string, ShortcutAction> = {
    n: "new",
    o: "open",
    w: "close",
    x: "cut",
    c: "copy",
    v: "paste",
    d: "duplicate",
  };
  return plain[key];
}

/**
 * Global keyboard shortcuts of the File and Edit menus (Ctrl or ⌘; F2, Supr and Esc alone).
 * Only the actions passed are handled; the rest of the keys keep their default behavior.
 */
export function useShortcuts(shortcuts: Shortcuts) {
  const ref = useRef(shortcuts);
  useEffect(() => {
    ref.current = shortcuts;
  });

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const name = actionFor(event);
      const action = name && ref.current[name];
      if (!name || !action) return;
      if (EDIT_ACTIONS.has(name) && keepsEditKeys(event.target)) return;
      if ((name === "copy" || name === "cut") && hasTextSelection()) return;
      event.preventDefault();
      action();
    };
    // Capture phase: decide before an open menu or dialog handles (and closes on) the key.
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, []);
}
