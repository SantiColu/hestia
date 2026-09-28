import { HistoryItem } from "@/components/workflow/history-item";
import {
  PanelTabs,
  PanelTabsContent,
  PanelTabsList,
  PanelTabsTrigger,
} from "@/components/navigation/panel-tabs";
import { cn } from "@/lib/utils";
import { useProject } from "@/project/store";

const timeFormat = new Intl.DateTimeFormat("es-AR", { timeStyle: "medium" });

/** Messages (project events from every actor, and errors) and the project history. */
export function BottomPanel() {
  const { messages, history } = useProject();

  return (
    <section className="flex h-48 shrink-0 flex-col border-t border-border bg-surface">
      <PanelTabs defaultValue="messages" className="min-h-0 flex-1 gap-0">
        <PanelTabsList>
          <PanelTabsTrigger value="messages">Mensajes</PanelTabsTrigger>
          <PanelTabsTrigger value="history">Historial</PanelTabsTrigger>
          <PanelTabsTrigger value="runs" disabled>
            Corridas
          </PanelTabsTrigger>
        </PanelTabsList>
        <PanelTabsContent value="messages" className="min-h-0 overflow-y-auto px-3 py-1">
          {messages.length === 0 && (
            <p className="py-2 text-xs text-subtle-foreground">Sin mensajes.</p>
          )}
          <ul className="flex flex-col-reverse">
            {messages.map((message) => (
              <li key={message.id} className="flex gap-3 py-0.5 text-xs">
                <time className="font-mono text-subtle-foreground tabular-nums">
                  {timeFormat.format(message.time)}
                </time>
                {message.author && <span className="font-medium">{message.author}</span>}
                <span className={cn(message.tone === "error" && "text-error")}>{message.text}</span>
              </li>
            ))}
          </ul>
        </PanelTabsContent>
        <PanelTabsContent value="history" className="min-h-0 overflow-y-auto px-3">
          {history.length === 0 && (
            <p className="py-2 text-xs text-subtle-foreground">Sin cambios todavía.</p>
          )}
          {[...history].reverse().map((change) => (
            <HistoryItem
              key={change.id}
              author={change.author.name}
              action={change.summary}
              time={timeFormat.format(new Date(change.timestamp))}
              justification={change.justification || "Sin justificación."}
              className="border-b border-border"
            />
          ))}
        </PanelTabsContent>
      </PanelTabs>
    </section>
  );
}
