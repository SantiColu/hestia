import type { CellArtifact, EquipmentArtifact } from "@/api/client";
import { itemsOf, modesOf } from "./edits";

/**
 * What the dissipation indicators compare against (presentation only): the totals of the
 * operating modes come from the API (`derived`); the meters show each value relative to the
 * largest one visible.
 */
export type DissipationScale = {
  /** Total of an operating mode, W. Null: the API cannot add it up (invalid or missing
   * values); undefined: not known yet. */
  totalOf: (operatingModeId: string | null | undefined) => number | null | undefined;
  /** Largest total among the operating modes, W. */
  maxTotal: number;
  /** Largest dissipation per item among the modes of every item, W. */
  maxPerItem: number;
};

export function dissipationScale(
  derived: CellArtifact["derived"],
  artifact: EquipmentArtifact,
): DissipationScale {
  const totals = new Map(
    (derived?.operating_mode_dissipation ?? []).map((t) => [t.operating_mode_id, t.dissipation]),
  );
  const perItem = itemsOf(artifact).flatMap((item) =>
    modesOf(item).flatMap((mode) =>
      typeof mode.dissipation === "number" ? [mode.dissipation] : [],
    ),
  );
  return {
    totalOf: (id) => (id ? totals.get(id) : undefined),
    maxTotal: Math.max(0, ...[...totals.values()].filter((t) => typeof t === "number")),
    maxPerItem: Math.max(0, ...perItem),
  };
}
