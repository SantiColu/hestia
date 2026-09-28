import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  component: Home,
});

function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-2 p-8">
      <h1 className="text-3xl font-semibold tracking-tight">Hestia</h1>
      <p className="text-muted-foreground">Thermal control system preliminary design.</p>
    </main>
  );
}
