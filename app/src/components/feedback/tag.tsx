import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

const TONE = {
  hot: "border-hot text-hot",
  cold: "border-cold text-cold",
  neutral: "border-border-strong text-muted-foreground",
} as const;

type TagProps = {
  tone?: keyof typeof TONE;
  children: ReactNode;
  className?: string;
};

/** Outlined mono tag: thermal cases (HOT/COLD) and neutral references (e.g. ECSS standards). */
export function Tag({ tone = "neutral", children, className }: TagProps) {
  return (
    <span
      className={cn(
        "inline-flex h-5 w-fit shrink-0 items-center rounded-lg border px-1.5 font-mono text-2xs font-medium tracking-wide whitespace-nowrap",
        TONE[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
