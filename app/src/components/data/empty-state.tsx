import type { ReactNode } from "react";
import { CircleDashed, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

type EmptyStateProps = {
  title: string;
  description?: string;
  icon?: LucideIcon;
  action?: ReactNode;
  className?: string;
};

export function EmptyState({
  title,
  description,
  icon: Icon = CircleDashed,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-3 rounded-lg border border-border px-6 py-8 text-center",
        className,
      )}
    >
      <Icon className="size-6 text-subtle-foreground" aria-hidden />
      <p className="text-sm font-medium">{title}</p>
      {description && (
        <p className="max-w-sm text-xs leading-relaxed text-muted-foreground">{description}</p>
      )}
      {action}
    </div>
  );
}
