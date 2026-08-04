import { z } from "zod";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const serviceCheckSchema = z.object({
  status: z.string(),
  detail: z.string(),
});

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

export type SetupState = z.infer<typeof setupStateSchema>;
export type User = z.infer<typeof userSchema>;
export type AuthResponse = z.infer<typeof authResponseSchema>;
export type HealthResponse = z.infer<typeof healthResponseSchema>;
export type PublicSettings = z.infer<typeof publicSettingsSchema>;

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
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    credentials: "include",
    headers: {
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
