import {
  ChartNoAxesColumn,
  Grid3x3,
  Lightbulb,
  Link2,
  Ruler,
  Satellite,
  Scale,
  Sigma,
  Sun,
  Thermometer,
  type LucideIcon,
} from "lucide-react";
import type { StageType } from "@/api/client";

/** Toolbox icon of each stage type (app/design/workspace.pen). Presentation only. */
export const STAGE_ICONS: Record<StageType, LucideIcon> = {
  mission: Satellite,
  environment: Sun,
  global_balance: Scale,
  tcs_concept: Lightbulb,
  discretization: Grid3x3,
  couplings: Link2,
  load_cases: Thermometer,
  solution: Sigma,
  margins: Ruler,
  sensitivity: ChartNoAxesColumn,
};
