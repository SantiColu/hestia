import type { ComponentProps } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

/** Underlined tabs for panels (inputs / results / history / provenance). */
export const PanelTabs = Tabs;
export const PanelTabsContent = TabsContent;

export function PanelTabsList({ className, ...props }: ComponentProps<typeof TabsList>) {
  return (
    <TabsList
      variant="line"
      className={cn(
        "h-9! w-full shrink-0 items-end! justify-start gap-1 border-b border-border px-2 py-0",
        className,
      )}
      {...props}
    />
  );
}

export function PanelTabsTrigger({ className, ...props }: ComponentProps<typeof TabsTrigger>) {
  return (
    <TabsTrigger
      className={cn(
        "h-8 flex-none rounded-none px-3 text-ui font-normal text-muted-foreground data-active:font-medium data-active:text-foreground",
        "after:-bottom-px! after:bg-primary",
        className,
      )}
      {...props}
    />
  );
}
