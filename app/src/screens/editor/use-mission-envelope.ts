import { useEffect, useState } from "react";
import { api, unwrap, type CellContext } from "@/api/client";
import { useProject } from "@/project/store";
import type { Vec3 } from "./orbit-profile";

/**
 * Sizes of the envelope (x, y, z, m) of the mission in a cell's context, to draw the satellite
 * with its shape. Null without a mission in the context or without its three sizes.
 */
export function useMissionEnvelope(context: CellContext | null, revision: number): Vec3 | null {
  const { fail } = useProject();
  const [envelope, setEnvelope] = useState<Vec3 | null>(null);
  const missionId = context?.entries.find((e) => e.stage === "mission")?.cell_id ?? null;

  useEffect(() => {
    if (!missionId) return;
    let live = true;
    unwrap(
      api.GET("/project/cells/{cell_id}/artifact", { params: { path: { cell_id: missionId } } }),
    )
      .then(({ artifact }) => {
        if (!live) return;
        const sizes = "envelope" in artifact ? artifact.envelope : null;
        const { size_x: x, size_y: y, size_z: z } = sizes ?? {};
        setEnvelope(x && y && z ? [x, y, z] : null);
      })
      .catch(fail);
    return () => {
      live = false;
    };
  }, [missionId, revision, fail]);

  return missionId ? envelope : null;
}
