import { ArrowRight } from "lucide-react";
import { ActorAvatar } from "@/components/data/actor-avatar";
import { cn } from "@/lib/utils";

export type FieldChange = {
  field: string;
  from: string;
  to: string;
  /** Pre-formatted change, e.g. "550 → 600 km" (the unit once). Defaults to "from → to". */
  value?: string;
};

type HistoryItemProps = {
  /** Human or agent; rendered the same way. */
  author: string;
  action: string;
  time: string;
  /** Empty when none was given (people are not asked, ADR 0024). */
  justification?: string;
  changes?: FieldChange[];
  className?: string;
};

export function HistoryItem({
  author,
  action,
  time,
  justification,
  changes = [],
  className,
}: HistoryItemProps) {
  return (
    <article className={cn("flex gap-2.5 py-2.5", className)}>
      <ActorAvatar name={author} />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <header className="flex items-center gap-1.5 text-ui">
          <span className="font-medium">{author}</span>
          <span className="truncate text-muted-foreground">{action}</span>
          <time className="ml-auto font-mono text-2xs text-subtle-foreground">{time}</time>
        </header>
        {changes.map((change) => (
          <p key={change.field} className="flex items-center gap-2 font-mono text-xs">
            <span className="text-muted-foreground">{change.field}</span>
            <span className="text-subtle-foreground line-through">{change.from}</span>
            <ArrowRight className="size-3 text-subtle-foreground" aria-hidden />
            <span>{change.to}</span>
          </p>
        ))}
        {justification && (
          <p className="text-xs leading-relaxed text-muted-foreground">{justification}</p>
        )}
      </div>
    </article>
  );
}
