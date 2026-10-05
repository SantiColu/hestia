import type { Problem } from "@/api/client";

/**
 * The problems of a list of the artifact under its table, one line per item:
 * «Rueda de reacción: Falta la masa. Falta la ubicación.» Problems of the list itself go first,
 * without a name.
 */
export function ProblemLines({
  problems,
  list,
  nameOf,
}: {
  problems: Problem[];
  /** Path of the list: `items`, `operating_modes`. */
  list: string;
  /** Name of the item at an index, if it exists. */
  nameOf: (index: number) => string | undefined;
}) {
  const lines = new Map<string, string[]>();
  const pattern = new RegExp(`^${list}(?:\\[(\\d+)\\])?(?:$|[.[])`);
  for (const problem of problems) {
    const match = pattern.exec(problem.path);
    if (!match) continue;
    const name = match[1] === undefined ? undefined : nameOf(Number(match[1]));
    const prefix = name ? `${name}: ` : "";
    lines.set(prefix, [...(lines.get(prefix) ?? []), problem.message]);
  }
  return [...lines].map(([prefix, messages]) => (
    <p key={prefix} className="-mt-1.5 text-xs text-error">
      {prefix}
      {messages.join(" ")}
    </p>
  ));
}
