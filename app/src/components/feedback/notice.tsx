import type { ReactNode } from "react";
import { CircleCheck, CircleX, Info, TriangleAlert, type LucideIcon } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { cn } from "@/lib/utils";

const TONE: Record<
  "info" | "warning" | "error" | "success",
  { icon: LucideIcon; className: string }
> = {
  info: { icon: Info, className: "border-l-primary bg-primary-soft *:[svg]:text-primary" },
  warning: { icon: TriangleAlert, className: "border-l-warn bg-warn-soft *:[svg]:text-warn" },
  error: { icon: CircleX, className: "border-l-error bg-error-soft *:[svg]:text-error" },
  success: { icon: CircleCheck, className: "border-l-ok bg-ok-soft *:[svg]:text-ok" },
};

type NoticeProps = {
  tone: keyof typeof TONE;
  title: string;
  children?: ReactNode;
  className?: string;
};

/** Inline status message with a colored left rule. */
export function Notice({ tone, title, children, className }: NoticeProps) {
  const { icon: Icon, className: toneClass } = TONE[tone];
  return (
    <Alert
      className={cn(
        "rounded-none border-0 border-l-2 px-3 py-2.5 text-[13px] text-foreground",
        toneClass,
        className,
      )}
    >
      <Icon />
      <AlertTitle>{title}</AlertTitle>
      {children && (
        <AlertDescription className="text-xs leading-relaxed">{children}</AlertDescription>
      )}
    </Alert>
  );
}
