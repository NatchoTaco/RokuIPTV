import type { SourceState, SourceType } from "./api";

export function sourceStatusLabel(status: SourceState): string {
  const labels: Record<SourceState, string> = {
    healthy: "Healthy",
    importing: "Importing",
    warning: "Warning",
    offline: "Offline",
    failed: "Failed",
    disabled: "Disabled",
    pending: "Pending",
  };
  return labels[status];
}

export function sourceTypeLabel(sourceType: SourceType): string {
  const labels: Record<SourceType, string> = {
    m3u_url: "Remote M3U URL",
    m3u_upload: "Uploaded M3U file",
    demo_playlist: "Synthetic demo",
  };
  return labels[sourceType];
}

export function sourceStatusClass(status: SourceState): string {
  const classes: Record<SourceState, string> = {
    healthy: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
    importing: "border-forge-300/30 bg-forge-500/10 text-forge-100",
    warning: "border-amber-500/30 bg-amber-500/10 text-amber-100",
    offline: "border-zinc-500/30 bg-zinc-500/10 text-zinc-200",
    failed: "border-red-500/30 bg-red-500/10 text-red-100",
    disabled: "border-zinc-700 bg-zinc-900 text-zinc-400",
    pending: "border-zinc-700 bg-zinc-900 text-zinc-300",
  };
  return classes[status];
}

export function formatDateTime(value: string | null): string {
  if (!value) {
    return "Never";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatDuration(durationMs: number | null): string {
  if (durationMs === null) {
    return "Not complete";
  }
  if (durationMs < 1000) {
    return `${durationMs} ms`;
  }
  return `${Math.round(durationMs / 1000)} sec`;
}
