import { useEffect, useState } from "react";
import { api, unwrap, type CellContext } from "@/api/client";
import { useProject } from "@/project/store";

/** The resolved context of a cell (ADR 0016), refetched on every project change. */
export function useCellContext(cellId: string, revision: number): CellContext | null {
  const { fail } = useProject();
  const [context, setContext] = useState<CellContext | null>(null);
  useEffect(() => {
    let live = true;
    unwrap(api.GET("/project/cells/{cell_id}/context", { params: { path: { cell_id: cellId } } }))
      .then((result) => live && setContext(result))
      .catch(fail);
    return () => {
      live = false;
    };
  }, [cellId, revision, fail]);
  return context;
}
