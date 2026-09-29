import { cn } from "@/lib/utils";

/** Classes of the input box shared by the form fields (`Field/*` in the library). */
export function fieldBoxClass({ error, modified }: { error?: boolean; modified?: boolean }) {
  return cn(
    "flex h-8 items-center gap-2 rounded-lg border border-input bg-background px-2.5 transition-colors",
    "focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/30",
    "data-disabled:opacity-50",
    modified && "border-primary",
    error && "border-error focus-within:border-error focus-within:ring-error/20",
  );
}
