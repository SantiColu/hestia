import { createFileRoute } from "@tanstack/react-router";
import { App } from "@/screens/app";

export const Route = createFileRoute("/")({
  component: App,
});
