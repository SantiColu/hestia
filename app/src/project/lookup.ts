import type { Catalog, Cell, Project, StageType, System } from "@/api/client";

/** Read-only lookups on the API's view of the project (no workflow rules). */

export function findCell(project: Project | undefined, cellId: string): Cell | undefined {
  return project?.cells.find((cell) => cell.id === cellId);
}

export function findSystem(project: Project | undefined, systemId: string): System | undefined {
  return project?.systems.find((system) => system.id === systemId);
}

export function stageInfo(catalog: Catalog | null, stage: StageType) {
  return catalog?.stages.find((entry) => entry.stage === stage);
}

/** The stage's display name from the catalog; the id while the catalog loads. */
export function stageName(catalog: Catalog | null, stage: StageType): string {
  return stageInfo(catalog, stage)?.name ?? stage;
}

/** The stage has a computation that Update runs (ADR 0021). */
export function isComputation(catalog: Catalog | null, stage: StageType): boolean {
  const info = stageInfo(catalog, stage);
  return info?.kind === "computation" && info.implemented;
}
