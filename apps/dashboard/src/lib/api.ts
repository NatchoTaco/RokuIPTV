import { z } from "zod";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const serviceCheckSchema = z.object({
  status: z.string(),
  detail: z.string(),
});

const sourceTypeSchema = z.enum(["m3u_url", "m3u_upload", "demo_playlist"]);
const sourceStateSchema = z.enum([
  "healthy",
  "importing",
  "warning",
  "offline",
  "failed",
  "disabled",
  "pending",
]);
const importJobStateSchema = z.enum(["queued", "running", "succeeded", "failed"]);
const playlistImportStateSchema = z.enum(["queued", "running", "completed", "warning", "failed"]);
<<<<<<< HEAD
=======
const contentTypeSchema = z.enum(["live_tv", "movie", "series", "unknown"]);
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)

export const setupStateSchema = z.object({
  is_complete: z.boolean(),
  current_step: z.string(),
  completed_steps: z.array(z.string()),
  installation_mode: z.enum(["local_only", "remote_access"]).nullable(),
  administrator_exists: z.boolean(),
});

export const userSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  display_name: z.string(),
  is_admin: z.boolean(),
});

export const authResponseSchema = z.object({
  user: userSchema,
  setup: setupStateSchema,
});

export const healthResponseSchema = z.object({
  status: z.string(),
  service: z.string(),
  version: z.string(),
  environment: z.string(),
  setup_complete: z.boolean(),
  checks: z.record(serviceCheckSchema),
});

export const publicSettingsSchema = z.object({
  app_name: z.string(),
  version: z.string(),
  environment: z.string(),
});

export const sourceValidationSchema = z.object({
  playlist_reachable: z.boolean(),
  channel_count: z.number(),
<<<<<<< HEAD
  group_count: z.number(),
  estimated_import_time_seconds: z.number(),
=======
  total_entry_count: z.number(),
  selected_entry_count: z.number(),
  excluded_entry_count: z.number(),
  group_count: z.number(),
  content_counts: z.record(z.number()),
  selected_content_types: z.array(contentTypeSchema),
  deferred_content_types: z.array(contentTypeSchema),
  estimated_import_time_seconds: z.number(),
  estimated_database_rows: z.number(),
  estimated_database_bytes: z.number(),
  requires_confirmation: z.boolean(),
  confirmation_threshold_entries: z.number().nullable(),
  metadata_samples: z.array(z.record(z.unknown())),
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
  warnings: z.array(z.string()),
  errors: z.array(z.string()),
  checksum: z.string().nullable(),
  source_version: z.string().nullable(),
});

export const playlistImportJobSchema = z.object({
  id: z.string(),
  source_id: z.string(),
  playlist_import_id: z.string().nullable(),
  status: importJobStateSchema,
  progress_percent: z.number(),
  message: z.string(),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  failure_reason: z.string().nullable(),
});

export const sourceSummarySchema = z.object({
  id: z.string(),
  name: z.string(),
  source_type: sourceTypeSchema,
  status: sourceStateSchema,
  status_message: z.string(),
  display_location: z.string(),
  is_enabled: z.boolean(),
<<<<<<< HEAD
=======
  enabled_content_types: z.array(contentTypeSchema),
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
  refresh_interval_minutes: z.number().nullable(),
  last_updated_at: z.string(),
  last_refresh_at: z.string().nullable(),
  next_refresh_at: z.string().nullable(),
  last_error: z.string().nullable(),
  channel_count: z.number(),
  group_count: z.number(),
  active_job: playlistImportJobSchema.nullable(),
});

export const sourceListSchema = z.object({
  sources: z.array(sourceSummarySchema),
});

export const sourceCreatedSchema = z.object({
  source: sourceSummarySchema,
  job: playlistImportJobSchema,
});

export const playlistImportHistoryItemSchema = z.object({
  id: z.string(),
  source_id: z.string(),
  source_name: z.string(),
  source_kind: sourceTypeSchema,
  status: playlistImportStateSchema,
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  duration_ms: z.number().nullable(),
  channel_count: z.number(),
  group_count: z.number(),
  warning_count: z.number(),
  failure_count: z.number(),
  warnings: z.array(z.string()),
  failures: z.array(z.string()),
  failure_reason: z.string().nullable(),
  checksum: z.string().nullable(),
  source_version: z.string().nullable(),
});

export const playlistImportHistorySchema = z.object({
  imports: z.array(playlistImportHistoryItemSchema),
});

export type SetupState = z.infer<typeof setupStateSchema>;
export type User = z.infer<typeof userSchema>;
export type AuthResponse = z.infer<typeof authResponseSchema>;
export type HealthResponse = z.infer<typeof healthResponseSchema>;
export type PublicSettings = z.infer<typeof publicSettingsSchema>;
export type SourceType = z.infer<typeof sourceTypeSchema>;
export type SourceState = z.infer<typeof sourceStateSchema>;
<<<<<<< HEAD
=======
export type ContentType = z.infer<typeof contentTypeSchema>;
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
export type SourceValidation = z.infer<typeof sourceValidationSchema>;
export type PlaylistImportJob = z.infer<typeof playlistImportJobSchema>;
export type SourceSummary = z.infer<typeof sourceSummarySchema>;
export type SourceList = z.infer<typeof sourceListSchema>;
export type SourceCreated = z.infer<typeof sourceCreatedSchema>;
export type PlaylistImportHistoryItem = z.infer<typeof playlistImportHistoryItemSchema>;
export type PlaylistImportHistory = z.infer<typeof playlistImportHistorySchema>;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchJson<T>(
  path: string,
  schema: z.ZodType<T>,
  init: RequestInit = {},
): Promise<T> {
  const isFormData = init.body instanceof FormData;
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    credentials: "include",
    headers: isFormData
      ? init.headers
      : {
          "Content-Type": "application/json",
          ...init.headers,
        },
  });

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : "Request failed.";
    throw new ApiError(detail, response.status);
  }
  return schema.parse(body);
}

export function getSetupState(): Promise<SetupState> {
  return fetchJson("/api/v1/setup/state", setupStateSchema);
}

export function bootstrapAdmin(payload: {
  email: string;
  password: string;
  display_name: string;
}): Promise<AuthResponse> {
  return fetchJson("/api/v1/auth/bootstrap-admin", authResponseSchema, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function signIn(payload: { email: string; password: string }): Promise<AuthResponse> {
  return fetchJson("/api/v1/auth/sign-in", authResponseSchema, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function signOut(): Promise<{ message: string }> {
  return fetchJson("/api/v1/auth/sign-out", z.object({ message: z.string() }), {
    method: "POST",
  });
}

export function getCurrentUser(): Promise<User> {
  return fetchJson("/api/v1/auth/me", userSchema);
}

export function updateSetupState(payload: {
  installation_mode: "local_only" | "remote_access";
}): Promise<SetupState> {
  return fetchJson("/api/v1/setup/state", setupStateSchema, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getHealth(): Promise<HealthResponse> {
  return fetchJson("/api/v1/health", healthResponseSchema);
}

export function getPublicSettings(): Promise<PublicSettings> {
  return fetchJson("/api/v1/settings/public", publicSettingsSchema);
}

export function listSources(): Promise<SourceList> {
  return fetchJson("/api/v1/sources", sourceListSchema);
}

<<<<<<< HEAD
export function validateM3uUrl(url: string): Promise<SourceValidation> {
  return fetchJson("/api/v1/sources/validate-url", sourceValidationSchema, {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export function validateM3uUpload(file: File): Promise<SourceValidation> {
  const formData = new FormData();
=======
export function validateM3uUrl(url: string, enabledContentTypes: ContentType[]): Promise<SourceValidation> {
  return fetchJson("/api/v1/sources/validate-url", sourceValidationSchema, {
    method: "POST",
    body: JSON.stringify({ url, enabled_content_types: enabledContentTypes }),
  });
}

export function validateM3uUpload(file: File, enabledContentTypes: ContentType[]): Promise<SourceValidation> {
  const formData = new FormData();
  formData.append("enabled_content_types", enabledContentTypes.join(","));
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
  formData.append("file", file);
  return fetchJson("/api/v1/sources/validate-upload", sourceValidationSchema, {
    method: "POST",
    body: formData,
  });
}

export function createM3uUrlSource(payload: {
  name: string;
  url: string;
  refresh_interval_minutes: number | null;
<<<<<<< HEAD
=======
  enabled_content_types: ContentType[];
  confirm_large_import: boolean;
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
}): Promise<SourceCreated> {
  return fetchJson("/api/v1/sources/m3u-url", sourceCreatedSchema, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createM3uUploadSource(payload: {
  name: string;
  file: File;
  refresh_interval_minutes: number | null;
<<<<<<< HEAD
=======
  enabled_content_types: ContentType[];
  confirm_large_import: boolean;
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
}): Promise<SourceCreated> {
  const formData = new FormData();
  formData.append("name", payload.name);
  if (payload.refresh_interval_minutes !== null) {
    formData.append("refresh_interval_minutes", String(payload.refresh_interval_minutes));
  }
<<<<<<< HEAD
=======
  formData.append("enabled_content_types", payload.enabled_content_types.join(","));
  formData.append("confirm_large_import", String(payload.confirm_large_import));
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
  formData.append("file", payload.file);
  return fetchJson("/api/v1/sources/m3u-upload", sourceCreatedSchema, {
    method: "POST",
    body: formData,
  });
}

export function createDemoSource(): Promise<SourceCreated> {
  return fetchJson("/api/v1/sources/demo", sourceCreatedSchema, {
    method: "POST",
<<<<<<< HEAD
    body: JSON.stringify({ name: "Synthetic Demonstration Playlist", refresh_interval_minutes: null }),
=======
    body: JSON.stringify({
      name: "Synthetic Demonstration Playlist",
      refresh_interval_minutes: null,
      enabled_content_types: ["live_tv"],
      confirm_large_import: false,
    }),
>>>>>>> 1a6619e (Harden Milestone 2 playlist ingestion and credential handling)
  });
}

export function refreshSource(sourceId: string): Promise<PlaylistImportJob> {
  return fetchJson(`/api/v1/sources/${sourceId}/refresh`, playlistImportJobSchema, {
    method: "POST",
  });
}

export function updateSource(
  sourceId: string,
  payload: { is_enabled?: boolean; refresh_interval_minutes?: number | null },
): Promise<SourceList> {
  return fetchJson(`/api/v1/sources/${sourceId}`, sourceListSchema, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteSource(sourceId: string): Promise<{ message: string }> {
  return fetchJson(`/api/v1/sources/${sourceId}`, z.object({ message: z.string() }), {
    method: "DELETE",
  });
}

export function listImportHistory(): Promise<PlaylistImportHistory> {
  return fetchJson("/api/v1/playlists/imports", playlistImportHistorySchema);
}

export function getImportJob(jobId: string): Promise<PlaylistImportJob> {
  return fetchJson(`/api/v1/playlists/jobs/${jobId}`, playlistImportJobSchema);
}
