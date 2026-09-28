import { Link, type LinkProps } from "@tanstack/react-router";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

type NavItemProps = {
  to: LinkProps["to"];
  icon: LucideIcon;
  label: string;
  active?: boolean;
  /** Short mono counter on the right, e.g. outdated stages. */
  meta?: string;
};

export function NavItem({ to, icon: Icon, label, active, meta }: NavItemProps) {
  return (
    <Link
      to={to}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex h-8 items-center gap-2.5 rounded-lg px-2.5 text-[13px] text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground",
        active && "bg-surface-2 font-medium text-foreground",
      )}
    >
      <Icon className={cn("size-4", active ? "text-foreground" : "text-subtle-foreground")} />
      <span className="flex-1 truncate">{label}</span>
      {meta && <span className="font-mono text-[11px] text-subtle-foreground">{meta}</span>}
    </Link>
  );
}
