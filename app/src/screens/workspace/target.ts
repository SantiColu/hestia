/** A system or a cell of the schematic. */
export type Target = { kind: "system" | "cell"; id: string };

export function includesTarget(targets: readonly Target[], target: Target): boolean {
  return targets.some((t) => t.kind === target.kind && t.id === target.id);
}
