import { createFileRoute, notFound } from "@tanstack/react-router";
import { Showcase } from "./-showcase";

/** Development-only catalog to compare components against app/design/hestia.lib.pen. */
export const Route = createFileRoute("/dev/components")({
  beforeLoad: () => {
    if (!import.meta.env.DEV) throw notFound();
  },
  component: Showcase,
});
