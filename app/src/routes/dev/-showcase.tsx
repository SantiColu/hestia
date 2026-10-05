import { useState, type ReactNode } from "react";
import {
  Copy,
  Ellipsis,
  GitBranch,
  History,
  Play,
  Plus,
  RotateCcw,
  Satellite,
  Trash2,
  Workflow,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { NumberField } from "@/components/forms/number-field";
import { TextField } from "@/components/forms/text-field";
import { CompactSelect } from "@/components/forms/compact-select";
import { SelectField } from "@/components/forms/select-field";
import { CheckboxField, SwitchField } from "@/components/forms/choice-fields";
import { Segmented } from "@/components/forms/segmented";
import { StageStatusBadge } from "@/components/feedback/stage-status";
import { Tag } from "@/components/feedback/tag";
import { Notice } from "@/components/feedback/notice";
import { SectionLabel } from "@/components/navigation/section-label";
import { NavItem } from "@/components/navigation/nav-item";
import {
  PanelTabs,
  PanelTabsContent,
  PanelTabsList,
  PanelTabsTrigger,
} from "@/components/navigation/panel-tabs";
import { DenseTable } from "@/components/data/dense-table";
import { KeyValue, Metric } from "@/components/data/readouts";
import { ActorAvatar } from "@/components/data/actor-avatar";
import { EmptyState } from "@/components/data/empty-state";
import { SegmentMeter } from "@/components/data/segment-meter";
import { HistoryItem } from "@/components/workflow/history-item";
import { ProvenanceRow } from "@/components/workflow/provenance-row";

// Sample data only: this page never talks to the API.
const CASES = [
  { id: "hot", tone: "hot" as const, node: "38.2", limit: "45.0", margin: "6.8" },
  { id: "cold", tone: "cold" as const, node: "-12.4", limit: "-20.0", margin: "7.6" },
];

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section className="flex flex-col gap-6 border-t border-border pt-8">
      <header className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="text-ui text-muted-foreground">{description}</p>
      </header>
      {children}
    </section>
  );
}

function Row({ children }: { children: ReactNode }) {
  return <div className="flex flex-wrap items-start gap-4">{children}</div>;
}

export function Showcase() {
  const [mode, setMode] = useState<"steady" | "transient">("steady");

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-8 py-12">
      <header className="flex flex-col gap-2">
        <span className="font-mono text-xs tracking-widest text-primary">DEV</span>
        <h1 className="text-3xl font-semibold tracking-tight">Componentes</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Catálogo de la librería Graphite. Fuente de diseño:{" "}
          <code className="font-mono">app/design/hestia.lib.pen</code>.
        </p>
      </header>

      <Section
        title="Buttons"
        description="Acción primaria única por sección. Alto 32 (default) y 28 (sm)."
      >
        <Row>
          <Button>
            <Play data-icon="inline-start" />
            Correr etapa
          </Button>
          <Button variant="secondary">
            <GitBranch data-icon="inline-start" />
            Procedencia
          </Button>
          <Button variant="ghost">
            <History data-icon="inline-start" />
            Historial
          </Button>
          <Button variant="destructive">
            <Trash2 data-icon="inline-start" />
            Eliminar
          </Button>
          <Button variant="outline" size="icon" aria-label="Más acciones">
            <Ellipsis />
          </Button>
        </Row>
        <Row>
          <Button size="sm">
            <Play data-icon="inline-start" />
            Correr
          </Button>
          <Button size="sm" variant="secondary">
            <Plus data-icon="inline-start" />
            Agregar
          </Button>
          <Button size="sm" variant="ghost">
            <Copy data-icon="inline-start" />
            Duplicar
          </Button>
          <Button size="sm" variant="destructive">
            <Trash2 data-icon="inline-start" />
            Eliminar
          </Button>
          <Button size="icon-sm" variant="outline" aria-label="Cerrar">
            <X />
          </Button>
        </Row>
      </Section>

      <Section
        title="Forms"
        description="Valores numéricos en mono con unidad. Internamente SI/K; la UI muestra °C."
      >
        <div className="grid grid-cols-4 gap-6">
          <NumberField label="Área de radiador" unit="m²" defaultValue={0.48} step={0.01} min={0} />
          <SelectField
            label="Caso de carga"
            defaultValue="hot_op"
            options={[
              { value: "hot_op", label: "Hot operativo" },
              { value: "cold_op", label: "Cold operativo" },
              { value: "safe", label: "Modo seguro" },
            ]}
          />
          <TextField label="Nombre del proyecto" defaultValue="SAT-M1" />
          <NumberField
            label="Emisividad radiador"
            defaultValue={1.2}
            error="Fuera de rango: 0 – 1"
          />
        </div>
        <Row>
          <CheckboxField label="Incluir modo seguro" defaultChecked />
          <CheckboxField label="Incluir transitorios" />
          <SwitchField label="Recalcular al cambiar" defaultChecked />
          <SwitchField label="Mostrar en Kelvin" />
          <CompactSelect
            label="Modo de actitud"
            icon={Satellite}
            value="nadir"
            onValueChange={() => undefined}
            options={[
              { value: "nadir", label: "Apuntado nadir" },
              { value: "sun", label: "Apuntado al Sol" },
            ]}
          />
          <Segmented
            aria-label="Tipo de solución"
            value={mode}
            onValueChange={setMode}
            options={[
              { value: "steady", label: "Estacionario" },
              { value: "transient", label: "Transitorio" },
            ]}
          />
        </Row>
      </Section>

      <Section title="Feedback" description="Estados de etapa, casos térmicos, alertas y tooltips.">
        <Row>
          {(["up_to_date", "outdated", "failed", "never_run", "running"] as const).map((status) => (
            <StageStatusBadge key={status} status={status} />
          ))}
        </Row>
        <Row>
          <Tag tone="hot">HOT</Tag>
          <Tag tone="cold">COLD</Tag>
          <Tag>ECSS-E-ST-31C</Tag>
          <Tooltip>
            <TooltipTrigger render={<Button size="sm" variant="outline" />}>Tooltip</TooltipTrigger>
            <TooltipContent>Q̇ disipada total en modo operativo</TooltipContent>
          </Tooltip>
        </Row>
        <div className="flex max-w-xl flex-col gap-3">
          <Notice tone="info" title="Celda alimentada por un vínculo">
            Las entradas de Casos de carga vienen de «Entorno · LEO 600». Editalas ahí o desvinculá
            la celda.
          </Notice>
          <Notice tone="warning" title="3 etapas desactualizadas">
            Cambió Misión. Actualizá Entorno y lo que sigue para ver resultados consistentes.
          </Notice>
          <Notice tone="error" title="La solución no convergió">
            Solución: residuo 3.2e-2 tras 500 iteraciones. Revisá acoplamientos de los nodos 12–14.
          </Notice>
          <Notice tone="success" title="Etapa actualizada">
            Balance global corrió en 0.8 s sin advertencias.
          </Notice>
        </div>
      </Section>

      <Section
        title="Navigation"
        description="Tabs, etiquetas de sección, navegación lateral y breadcrumb."
      >
        <div className="grid grid-cols-2 gap-10">
          <div className="flex flex-col gap-6">
            <PanelTabs defaultValue="inputs">
              <PanelTabsList>
                <PanelTabsTrigger value="inputs">Entradas</PanelTabsTrigger>
                <PanelTabsTrigger value="results">Resultados</PanelTabsTrigger>
                <PanelTabsTrigger value="history">Historial</PanelTabsTrigger>
                <PanelTabsTrigger value="provenance">Procedencia</PanelTabsTrigger>
              </PanelTabsList>
              <PanelTabsContent value="inputs" className="pt-3 text-muted-foreground">
                Contenido de entradas.
              </PanelTabsContent>
              <PanelTabsContent value="results" className="pt-3 text-muted-foreground">
                Contenido de resultados.
              </PanelTabsContent>
            </PanelTabs>
            <SectionLabel>Entradas</SectionLabel>
            <Breadcrumb>
              <BreadcrumbList className="text-ui">
                <BreadcrumbItem className="font-mono">SAT-M1</BreadcrumbItem>
                <BreadcrumbSeparator />
                <BreadcrumbItem>Fase 0</BreadcrumbItem>
                <BreadcrumbSeparator />
                <BreadcrumbItem>
                  <BreadcrumbPage>Balance global</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          </div>
          <nav className="flex w-60 flex-col gap-0.5 rounded-lg border border-border bg-surface p-2">
            <NavItem to="/dev/components" icon={Workflow} label="Workflow" meta="3" active />
            <NavItem to="/" icon={History} label="Historial" />
          </nav>
        </div>
      </Section>

      <Section title="Data" description="Tablas densas, lecturas de valores y estados vacíos.">
        <div className="flex flex-wrap gap-10">
          <DenseTable
            className="w-full max-w-lg"
            rowKey={(row) => row.id}
            rows={CASES}
            columns={[
              {
                key: "case",
                header: "Caso",
                cell: (row) => <Tag tone={row.tone}>{row.id.toUpperCase()}</Tag>,
              },
              { key: "node", header: "T nodo [°C]", numeric: true, cell: (row) => row.node },
              { key: "limit", header: "Límite [°C]", numeric: true, cell: (row) => row.limit },
              { key: "margin", header: "Margen [K]", numeric: true, cell: (row) => row.margin },
            ]}
          />
          <div className="flex items-start gap-10">
            <Metric
              label="Área de radiador"
              value="0.48"
              unit="m²"
              detail="+0.06 vs. corrida anterior"
            />
            <div className="flex w-56 flex-col">
              <KeyValue label="Ángulo β máx." value="72.0°" />
              <KeyValue label="Eclipse máx." value="35.4 min" />
            </div>
            <ActorAvatar name="Ana Ruiz" />
            <div className="flex flex-col gap-2 font-mono text-xs">
              {[45, 20, 3, 0].map((watts) => (
                <span key={watts} className="flex items-center gap-2">
                  <SegmentMeter value={watts} max={45} />Σ {watts} W
                </span>
              ))}
            </div>
          </div>
        </div>
        <EmptyState
          className="max-w-md"
          title="Esta etapa nunca se corrió"
          description="Completá las entradas y corré la etapa para ver resultados."
          action={
            <Button>
              <Play data-icon="inline-start" />
              Correr etapa
            </Button>
          }
        />
      </Section>

      <Section title="Workflow" description="Historial con autor y justificación, procedencia.">
        <div className="grid max-w-4xl grid-cols-2 gap-10">
          <HistoryItem
            author="Stefan"
            action="modificó Balance global"
            time="14:32"
            changes={[{ field: "radiator_area_m2", from: "0.42", to: "0.48" }]}
            justification="Margen cold < 5 K en modo seguro; se amplía el radiador y se recalcula heater."
          />
          <div>
            <ProvenanceRow
              artifact="environment.load_cases"
              source="de Entorno · esquema v3 · hace 5 min"
              status="up_to_date"
            />
            <ProvenanceRow
              artifact="mission.dissipation"
              source="de Misión · esquema v2 · hace 2 h"
              status="up_to_date"
            />
          </div>
        </div>
      </Section>

      <Section title="Overlays" description="Menús y confirmación de cambios con justificación.">
        <Row>
          <DropdownMenu>
            <DropdownMenuTrigger
              render={<Button variant="outline" size="icon" aria-label="Acciones de etapa" />}
            >
              <Ellipsis />
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56">
              <DropdownMenuItem>
                <Play />
                Correr etapa
                <DropdownMenuShortcut>R</DropdownMenuShortcut>
              </DropdownMenuItem>
              <DropdownMenuItem>
                <GitBranch />
                Ver procedencia
                <DropdownMenuShortcut>P</DropdownMenuShortcut>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem variant="destructive">
                <RotateCcw />
                Deshacer último cambio
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </Row>
      </Section>
    </main>
  );
}
