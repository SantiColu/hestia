import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";

/** Author of a change. Humans and agents render identically by design. */
export function ActorAvatar({ name, className }: { name: string; className?: string }) {
  const initials = name
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  return (
    <Avatar className={cn("size-6 border border-border-strong", className)}>
      <AvatarFallback className="bg-surface-2 font-mono text-[10px] text-muted-foreground">
        {initials}
      </AvatarFallback>
    </Avatar>
  );
}
