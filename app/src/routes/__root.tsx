import { createRootRoute, Outlet, type ErrorComponentProps } from "@tanstack/react-router";
import { RotateCw, TriangleAlert } from "lucide-react";
import { EmptyState } from "@/components/data/empty-state";
import { Button } from "@/components/ui/button";
import { TooltipProvider } from "@/components/ui/tooltip";

/** A render error shows a message instead of leaving the window blank. */
function RenderError({ error }: ErrorComponentProps) {
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div className="flex h-screen items-center justify-center bg-background p-6">
      <EmptyState
        icon={TriangleAlert}
        title="Algo falló al mostrar la pantalla"
        description={`${message} El proyecto sigue abierto en la API; recargar no pierde cambios.`}
        action={
          <Button size="sm" onClick={() => window.location.reload()}>
            <RotateCw data-icon="inline-start" /> Recargar
          </Button>
        }
      />
    </div>
  );
}

export const Route = createRootRoute({
  component: () => (
    <TooltipProvider>
      <Outlet />
    </TooltipProvider>
  ),
  errorComponent: RenderError,
});
