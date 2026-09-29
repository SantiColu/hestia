import {
  PanelTabs,
  PanelTabsContent,
  PanelTabsList,
  PanelTabsTrigger,
} from "@/components/navigation/panel-tabs";

/** Right dock: Properties and Agents. Content pending (docs/ux-workspace.md). */
export function Dock() {
  return (
    <aside className="flex w-[340px] shrink-0 flex-col border-l border-border bg-surface">
      <PanelTabs defaultValue="properties" className="gap-0">
        <PanelTabsList>
          <PanelTabsTrigger value="properties">Propiedades</PanelTabsTrigger>
          <PanelTabsTrigger value="agents">Agentes</PanelTabsTrigger>
        </PanelTabsList>
        <PanelTabsContent value="properties" />
        <PanelTabsContent value="agents" />
      </PanelTabs>
    </aside>
  );
}
