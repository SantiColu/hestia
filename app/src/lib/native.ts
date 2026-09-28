import { isTauri } from "@tauri-apps/api/core";
import { open, save } from "@tauri-apps/plugin-dialog";

const FILTERS = [{ name: "Proyecto Hestia", extensions: ["hestia"] }];

/**
 * Native file dialogs (Tauri). In a plain browser (`make dev`) there is no file picker that
 * returns a path, so we fall back to asking for the path.
 */
export async function pickProjectToOpen(): Promise<string | null> {
  if (isTauri()) {
    const path = await open({ multiple: false, directory: false, filters: FILTERS });
    return typeof path === "string" ? path : null;
  }
  return window.prompt("Ruta del archivo .hestia a abrir")?.trim() || null;
}

export async function pickProjectToSave(defaultName: string): Promise<string | null> {
  if (isTauri()) {
    return await save({ defaultPath: `${defaultName}.hestia`, filters: FILTERS });
  }
  return (
    window.prompt("Ruta donde guardar el proyecto (.hestia)", `${defaultName}.hestia`)?.trim() ||
    null
  );
}

export { isTauri };
