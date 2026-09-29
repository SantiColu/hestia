import { CircleX, Info, TriangleAlert } from "lucide-react";
import { HistoryItem } from "@/components/workflow/history-item";
import {
  PanelTabs,
  PanelTabsContent,
  PanelTabsList,
  PanelTabsTrigger,
} from "@/components/navigation/panel-tabs";
import { cn } from "@/lib/utils";
import { useProject } from "@/project/store";

const timeFormat = new Intl.DateTimeFormat("es-AR", {
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

/** Messages (project events from every actor, and errors) and the project history. */
export function BottomPanel() {
  const { messages, history } = useProject();

  return (
    <section className="flex h-[168px] shrink-0 flex-col border-t border-border bg-surface">
      <PanelTabs defaultValue="messages" className="min-h-0 flex-1 gap-0">
        <PanelTabsList>
          <PanelTabsTrigger value="messages">Mensajes</PanelTabsTrigger>
          <PanelTabsTrigger value="runs" disabled>
            Corridas
          </PanelTabsTrigger>
          <PanelTabsTrigger value="history">Historial</PanelTabsTrigger>
        </PanelTabsList>
        <PanelTabsContent value="messages" className="min-h-0 overflow-y-auto px-4 py-2">
          {messages.length === 0 && (
            <p className="py-1 text-xs text-subtle-foreground">Sin mensajes.</p>
          )}
          <ul className="flex flex-col-reverse gap-0.5">
            {messages.map((message) => {
              const error = message.tone === "error";
              const warning = message.tone === "warning";
              const Icon = error ? CircleX : warning ? TriangleAlert : Info;
              return (
                <li key={message.id} className="flex min-h-6 items-center gap-2.5 text-xs">
                  <time className="font-mono text-[11px] text-subtle-foreground tabular-nums">
                    {timeFormat.format(message.time)}
                  </time>
                  <Icon
                    className={cn(
                      "size-3.5 shrink-0",
                      error ? "text-error" : warning ? "text-warn" : "text-subtle-foreground",
                    )}
                    aria-hidden
                  />
                  <span className={cn("text-muted-foreground", error && "text-error")}>
                    {message.author && (
                      <span className="font-medium text-foreground">{message.author} · </span>
                    )}
                    {message.text}
                  </span>
                </li>
              );
            })}
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
