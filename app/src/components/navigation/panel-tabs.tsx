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
      className={cn("h-auto! w-full justify-start gap-0 border-b border-border p-0", className)}
      {...props}
    />
  );
}

export function PanelTabsTrigger({ className, ...props }: ComponentProps<typeof TabsTrigger>) {
  return (
    <TabsTrigger
      className={cn(
        "h-8 flex-none rounded-none px-3 text-[13px] font-normal data-active:font-medium",
        "after:bottom-[-1px]! after:bg-primary",
        className,
      )}
      {...props}
    />
  );
}
