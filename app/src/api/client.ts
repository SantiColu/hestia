import createClient from "openapi-fetch";
import type { components, paths } from "./schema.gen";

/** Base URL of the Hestia API (the desktop sidecar or `make dev`). */
export const API_URL: string = import.meta.env.VITE_HESTIA_API_URL ?? "http://127.0.0.1:8000";

/** Typed client generated from shared/openapi.json (ADR 0013). The only way to reach the API. */
export const api = createClient<paths>({ baseUrl: API_URL });

type Schemas = components["schemas"];
export type ApiErrorBody = Schemas["ApiError"];
export type Blueprint = Schemas["Blueprint"];
export type ApplyArtifactResult = Schemas["ApplyArtifactResult"];
export type Catalog = Schemas["Catalog"];
export type Cell = Schemas["Cell"];
export type CellArtifact = Schemas["CellArtifact"];
export type CellContext = Schemas["CellContext"];
export type CellResult = Schemas["CellResult"];
export type CellStatus = Schemas["CellStatus"];
export type Change = Schemas["Change"];
export type EnvironmentCondition = Schemas["Condition"];
export type EnvironmentParameters = Schemas["EnvironmentParameters"];
export type EnvironmentSummary = Schemas["EnvironmentSummary"];
export type FaceFluxes = Schemas["FaceFluxes"];
export type Fragment = Schemas["Fragment-Output"];
export type Link = Schemas["Link"];
export type MissionArtifact = Schemas["MissionArtifact"];
export type MutationResult = Schemas["MutationResult"];
export type OrbitProfile = Schemas["OrbitProfile"];
export type Position = Schemas["Position"];
export type Problem = Schemas["Problem"];
export type Project = Schemas["Project"];
export type ProjectEvent = Schemas["ProjectEvent"];
export type ProjectView = Schemas["ProjectView"];
export type RangeEntry = Schemas["RangeEntry"];
export type RecentProject = Schemas["RecentProject"];
export type StageType = Schemas["StageType"];
export type System = Schemas["System"];
export type TemplateId = Schemas["TemplateId"];
export type UpdateCellResult = Schemas["UpdateCellResult"];

/** An error answered by the API. `code` is stable (e.g. `project_locked`). */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: Record<string, unknown>;

  constructor(status: number, body: Partial<ApiErrorBody> | undefined) {
    super(body?.message ?? `Error ${status} de la API`);
    this.code = body?.code ?? "http_error";
    this.status = status;
    this.details = (body?.details as Record<string, unknown> | undefined) ?? {};
  }
}

/** `error` is an `ApiError` with that stable `code` (e.g. `unsaved_changes`). */
export function isApiError(error: unknown, code: string): error is ApiError {
  return error instanceof ApiError && error.code === code;
}

type FetchResult<T> = { data?: T; error?: unknown; response: Response };

/** Unwrap an openapi-fetch call: the data, or an `ApiError`. */
export async function unwrap<T>(request: Promise<FetchResult<T>>): Promise<T> {
  let result: FetchResult<T>;
  try {
    result = await request;
  } catch (cause) {
    throw new ApiError(0, {
      code: "unreachable",
      message: `No se pudo conectar con la API en ${API_URL}.`,
      details: { cause: String(cause) },
    });
  }
  if (!result.response.ok || result.data === undefined) {
    const body = result.error as Partial<ApiErrorBody> | { detail?: unknown } | undefined;
    if (body && "code" in body) throw new ApiError(result.response.status, body);
    throw new ApiError(result.response.status, {
      code: "http_error",
      message: `Error ${result.response.status} de la API: ${JSON.stringify(body)}`,
    });
  }
  return result.data;
}
