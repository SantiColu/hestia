import { useEffect, useRef } from "react";

export type Shortcuts = Partial<
  Record<"new" | "open" | "save" | "saveAs" | "close" | "undo" | "redo", () => void>
>;

function isTextInput(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

/** Global keyboard shortcuts of the File and Edit menus (Ctrl or ⌘). */
export function useShortcuts(shortcuts: Shortcuts) {
  const ref = useRef(shortcuts);
  useEffect(() => {
    ref.current = shortcuts;
  });

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey) || event.altKey) return;
      const key = event.key.toLowerCase();
      const map = ref.current;
      let action: (() => void) | undefined;
      if (key === "n" && !event.shiftKey) action = map.new;
      else if (key === "o" && !event.shiftKey) action = map.open;
      else if (key === "s") action = event.shiftKey ? map.saveAs : map.save;
      else if (key === "w" && !event.shiftKey) action = map.close;
      else if (key === "z" || key === "y") {
        // Text fields keep their own undo.
        if (isTextInput(event.target)) return;
        action = key === "y" || event.shiftKey ? map.redo : map.undo;
      }
      if (!action) return;
      event.preventDefault();
      action();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
}
