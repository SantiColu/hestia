import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

/** Mono uppercase label for panel sections and workflow phases. */
export function SectionLabel({ className, ...props }: ComponentProps<"h3">) {
  return (
    <h3
      className={cn(
        "font-mono text-2xs font-medium tracking-label text-subtle-foreground uppercase",
        className,
      )}
      {...props}
    />
  );
}
