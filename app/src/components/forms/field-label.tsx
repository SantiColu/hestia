import type { ReactNode } from "react";

/** Field label; a modified field (draft differs from the applied value) shows an accent dot. */
export function FieldLabel({
  htmlFor,
  modified,
  children,
}: {
  htmlFor?: string;
  modified?: boolean;
  children: ReactNode;
}) {
  return (
    <span className="flex items-center gap-1.5">
      <label htmlFor={htmlFor} className="text-xs text-muted-foreground">
        {children}
      </label>
      {modified && (
        <span className="size-1.5 shrink-0 rounded-full bg-primary" aria-label="Modificado" />
      )}
    </span>
  );
}

/** Line under the input: the validation message or else a hint (e.g. the applied value). */
export function FieldFootnote({ error, hint }: { error?: string; hint?: ReactNode }) {
  if (error) return <p className="text-xs text-error">{error}</p>;
  if (hint) return <p className="font-mono text-[11px] text-subtle-foreground">{hint}</p>;
  return null;
}
