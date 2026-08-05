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
const contentTypeSchema = z.enum(["live_tv", "movie", "series", "unknown"]);
const filterProfileSchema = z.enum(["light", "recommended", "aggressive", "custom"]);
const normalizationJobStateSchema = z.enum(["queued", "running", "succeeded", "failed", "canceled"]);

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
  enabled_content_types: z.array(contentTypeSchema),
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

export const channelSummarySchema = z.object({
  id: z.string(),
  source_id: z.string(),
  source_name: z.string().nullable(),
  original_name: z.string(),
  normalized_name: z.string().nullable(),
  normalized_group: z.string().nullable(),
  content_type: contentTypeSchema,
  inferred_country: z.string().nullable(),
  inferred_language: z.string().nullable(),
  inferred_category: z.string().nullable(),
  claimed_quality: z.string().nullable(),
  visibility_status: z.string(),
  duplicate_cluster_id: z.string().nullable(),
  url_checksum: z.string().nullable(),
  original_tvg_id: z.string().nullable(),
  original_tvg_name: z.string().nullable(),
  original_logo_url: z.string().nullable(),
  line_number: z.number().nullable(),
  normalized_at: z.string().nullable(),
  explanations: z.array(z.record(z.string())),
  filtering_reasons: z.array(z.record(z.unknown())),
});

export const channelListSchema = z.object({
  items: z.array(channelSummarySchema),
  next_cursor: z.string().nullable(),
  total_count: z.number(),
  page_size: z.number(),
});

export const channelGroupSchema = z.object({
  id: z.string(),
  name: z.string(),
  normalized_name: z.string(),
  sort_order: z.number(),
  is_visible: z.boolean(),
});

export const channelGroupListSchema = z.object({
  groups: z.array(channelGroupSchema),
});

export const channelSourceCandidateSchema = z.object({
  id: z.string(),
  raw_channel_id: z.string(),
  curated_channel_id: z.string(),
  role: z.string(),
  rank: z.number(),
  selection_reason: z.string().nullable(),
  original_name: z.string(),
  normalized_name: z.string().nullable(),
  normalized_group: z.string().nullable(),
  content_type: contentTypeSchema,
  claimed_quality: z.string().nullable(),
  url_checksum: z.string().nullable(),
  attributes: z.record(z.unknown()),
});

export const channelSourceCandidateListSchema = z.object({
  candidates: z.array(channelSourceCandidateSchema),
});

export const normalizationJobSchema = z.object({
  id: z.string(),
  source_id: z.string().nullable(),
  status: normalizationJobStateSchema,
  profile: filterProfileSchema,
  progress_percent: z.number(),
  message: z.string(),
  total_raw_channels: z.number(),
  processed_raw_channels: z.number(),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  canceled_at: z.string().nullable(),
  failure_reason: z.string().nullable(),
  stats: z.record(z.unknown()),
});

export const cleanupQueueSchema = z.object({
  key: z.string(),
  label: z.string(),
  count: z.number(),
  description: z.string(),
});

export const cleanupQueuesSchema = z.object({
  queues: z.array(cleanupQueueSchema),
});

export const cleanupPreviewSchema = z.object({
  profile: filterProfileSchema,
  source_id: z.string().nullable(),
  total_channels: z.number(),
  would_hide: z.number(),
  would_allow: z.number(),
  protected_count: z.number(),
  sample_channel_ids: z.array(z.string()),
  reasons: z.record(z.number()),
});

export const cleanupApplySchema = cleanupPreviewSchema.extend({
  applied: z.boolean(),
});

export const duplicateClusterSchema = z.object({
  id: z.string(),
  label: z.string(),
  confidence_score: z.number(),
  review_status: z.string(),
  candidate_count: z.number(),
  primary_raw_channel_id: z.string().nullable(),
  explanations: z.array(z.record(z.unknown())),
});

export const duplicateClusterListSchema = z.object({
  clusters: z.array(duplicateClusterSchema),
});

export const duplicateActionSchema = z.object({
  cluster: duplicateClusterSchema,
  message: z.string(),
});

export type SetupState = z.infer<typeof setupStateSchema>;
export type User = z.infer<typeof userSchema>;
export type AuthResponse = z.infer<typeof authResponseSchema>;
export type HealthResponse = z.infer<typeof healthResponseSchema>;
export type PublicSettings = z.infer<typeof publicSettingsSchema>;
export type SourceType = z.infer<typeof sourceTypeSchema>;
export type SourceState = z.infer<typeof sourceStateSchema>;
export type ContentType = z.infer<typeof contentTypeSchema>;
export type SourceValidation = z.infer<typeof sourceValidationSchema>;
export type PlaylistImportJob = z.infer<typeof playlistImportJobSchema>;
export type SourceSummary = z.infer<typeof sourceSummarySchema>;
export type SourceList = z.infer<typeof sourceListSchema>;
export type SourceCreated = z.infer<typeof sourceCreatedSchema>;
export type PlaylistImportHistoryItem = z.infer<typeof playlistImportHistoryItemSchema>;
export type PlaylistImportHistory = z.infer<typeof playlistImportHistorySchema>;
export type FilterProfile = z.infer<typeof filterProfileSchema>;
export type ChannelSummary = z.infer<typeof channelSummarySchema>;
export type ChannelList = z.infer<typeof channelListSchema>;
export type ChannelGroup = z.infer<typeof channelGroupSchema>;
export type ChannelSourceCandidate = z.infer<typeof channelSourceCandidateSchema>;
export type NormalizationJob = z.infer<typeof normalizationJobSchema>;
export type CleanupQueue = z.infer<typeof cleanupQueueSchema>;
export type CleanupPreview = z.infer<typeof cleanupPreviewSchema>;
export type CleanupApply = z.infer<typeof cleanupApplySchema>;
export type DuplicateCluster = z.infer<typeof duplicateClusterSchema>;

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

export function validateM3uUrl(url: string, enabledContentTypes: ContentType[]): Promise<SourceValidation> {
  return fetchJson("/api/v1/sources/validate-url", sourceValidationSchema, {
    method: "POST",
    body: JSON.stringify({ url, enabled_content_types: enabledContentTypes }),
  });
}

export function validateM3uUpload(file: File, enabledContentTypes: ContentType[]): Promise<SourceValidation> {
  const formData = new FormData();
  formData.append("enabled_content_types", enabledContentTypes.join(","));
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
  enabled_content_types: ContentType[];
  confirm_large_import: boolean;
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
  enabled_content_types: ContentType[];
  confirm_large_import: boolean;
}): Promise<SourceCreated> {
  const formData = new FormData();
  formData.append("name", payload.name);
  if (payload.refresh_interval_minutes !== null) {
    formData.append("refresh_interval_minutes", String(payload.refresh_interval_minutes));
  }
  formData.append("enabled_content_types", payload.enabled_content_types.join(","));
  formData.append("confirm_large_import", String(payload.confirm_large_import));
  formData.append("file", payload.file);
  return fetchJson("/api/v1/sources/m3u-upload", sourceCreatedSchema, {
    method: "POST",
    body: formData,
  });
}

export function createDemoSource(): Promise<SourceCreated> {
  return fetchJson("/api/v1/sources/demo", sourceCreatedSchema, {
    method: "POST",
    body: JSON.stringify({
      name: "Synthetic Demonstration Playlist",
      refresh_interval_minutes: null,
      enabled_content_types: ["live_tv"],
      confirm_large_import: false,
    }),
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

export function listChannels(params: {
  cursor?: string | null;
  page_size?: number;
  search?: string;
  source_id?: string;
  group?: string;
  visibility_status?: string;
  content_type?: ContentType;
  duplicate_status?: "duplicates" | "unique";
} = {}): Promise<ChannelList> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  });
  const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return fetchJson(`/api/v1/channels${suffix}`, channelListSchema);
}

export function listChannelGroups(): Promise<{ groups: ChannelGroup[] }> {
  return fetchJson("/api/v1/channels/groups", channelGroupListSchema);
}

export function createNormalizationJob(payload: {
  source_id?: string | null;
  profile: FilterProfile;
  process_now: boolean;
}): Promise<NormalizationJob> {
  return fetchJson("/api/v1/channels/normalization-jobs", normalizationJobSchema, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getNormalizationJob(jobId: string): Promise<NormalizationJob> {
  return fetchJson(`/api/v1/channels/normalization-jobs/${jobId}`, normalizationJobSchema);
}

export function updateChannel(
  channelId: string,
  payload: {
    display_name?: string;
    group_name?: string;
    visibility_status?: "visible" | "hidden" | "always_visible";
    protected_from_auto_merge?: boolean;
  },
): Promise<ChannelSummary> {
  return fetchJson(`/api/v1/channels/${channelId}`, channelSummarySchema, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function listChannelSourceCandidates(channelId: string): Promise<{ candidates: ChannelSourceCandidate[] }> {
  return fetchJson(`/api/v1/channels/${channelId}/candidates`, channelSourceCandidateListSchema);
}

export function listCleanupQueues(): Promise<{ queues: CleanupQueue[] }> {
  return fetchJson("/api/v1/cleanup/queues", cleanupQueuesSchema);
}

export function previewCleanupProfile(profile: FilterProfile): Promise<CleanupPreview> {
  return fetchJson("/api/v1/cleanup/preview", cleanupPreviewSchema, {
    method: "POST",
    body: JSON.stringify({ profile }),
  });
}

export function applyCleanupProfile(profile: FilterProfile): Promise<CleanupApply> {
  return fetchJson("/api/v1/cleanup/apply", cleanupApplySchema, {
    method: "POST",
    body: JSON.stringify({ profile }),
  });
}

export function listDuplicateClusters(): Promise<{ clusters: DuplicateCluster[] }> {
  return fetchJson("/api/v1/cleanup/duplicates", duplicateClusterListSchema);
}

export function protectDuplicateCluster(clusterId: string): Promise<{ cluster: DuplicateCluster; message: string }> {
  return fetchJson(`/api/v1/cleanup/duplicates/${clusterId}/protect`, duplicateActionSchema, {
    method: "POST",
  });
}

export function mergeDuplicateCluster(clusterId: string): Promise<{ cluster: DuplicateCluster; message: string }> {
  return fetchJson(`/api/v1/cleanup/duplicates/${clusterId}/merge`, duplicateActionSchema, {
    method: "POST",
  });
}

export function splitDuplicateCluster(clusterId: string): Promise<{ cluster: DuplicateCluster; message: string }> {
  return fetchJson(`/api/v1/cleanup/duplicates/${clusterId}/split`, duplicateActionSchema, {
    method: "POST",
  });
}
