import { useCallback } from "react";
import { useProject } from "@/project/store";

/** Centered column of the editor (`Form` in the design: 760 px). */
export const column = "mx-auto flex w-full max-w-[760px] flex-col";

export function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

/** "A, B, C y 6 más" / "A y B". */
export function listNames(names: string[], shown = 3): string {
  if (names.length > shown) {
    return `${names.slice(0, shown).join(", ")} y ${names.length - shown} más`;
  }
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")} y ${names[names.length - 1]}`;
}

export function useStageNames() {
  const { catalog } = useProject();
  return useCallback(
    (stage: string) => catalog?.stages.find((s) => s.stage === stage)?.name ?? stage,
    [catalog],
  );
}
