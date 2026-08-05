import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  FileUp,
  Plus,
  RefreshCw,
  Trash2,
  Upload,
  Wifi,
  XCircle,
} from "lucide-react";
import { FormEvent, useMemo, useState } from "react";

import { AppShell } from "../components/AppShell";
import { Button } from "../components/Button";
import { FormField } from "../components/FormField";
import {
  createDemoSource,
  createM3uUploadSource,
  createM3uUrlSource,
  deleteSource,
  listImportHistory,
  listSources,
  refreshSource,
  updateSource,
  validateM3uUpload,
  validateM3uUrl,
  type ContentType,
  type PlaylistImportHistoryItem,
  type SourceSummary,
  type SourceValidation,
  type User,
} from "../lib/api";
import { redactUrlForDisplay } from "../lib/redaction";
import {
  formatDateTime,
  formatDuration,
  sourceStatusClass,
  sourceStatusLabel,
  sourceTypeLabel,
} from "../lib/sourceStatus";

type SourceMethod = "m3u_url" | "m3u_upload";

export function SourcesPage({ user }: { user: User }) {
  const queryClient = useQueryClient();
  const [showWizard, setShowWizard] = useState(false);
  const [activeTab, setActiveTab] = useState<"sources" | "history">("sources");
  const sourcesQuery = useQuery({
    queryKey: ["sources"],
    queryFn: listSources,
    refetchInterval: 2000,
  });
  const historyQuery = useQuery({
    queryKey: ["import-history"],
    queryFn: listImportHistory,
    refetchInterval: 5000,
  });
  const demoMutation = useMutation({
    mutationFn: createDemoSource,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sources"] });
      await queryClient.invalidateQueries({ queryKey: ["import-history"] });
    },
  });

  return (
    <AppShell user={user}>
      <div className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="text-sm font-medium uppercase text-forge-300">Sources</p>
          <h1 className="mt-2 text-3xl font-semibold">Television sources</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-400">
            Add authorized M3U playlists, validate them, and monitor asynchronous imports.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button
            tone="secondary"
            icon={<RefreshCw aria-hidden className="h-4 w-4" />}
            onClick={() => {
              void sourcesQuery.refetch();
              void historyQuery.refetch();
            }}
          >
            Refresh
          </Button>
          <Button
            tone="secondary"
            icon={<FileUp aria-hidden className="h-4 w-4" />}
            onClick={() => demoMutation.mutate()}
            disabled={demoMutation.isPending}
          >
            Add demo
          </Button>
          <Button icon={<Plus aria-hidden className="h-4 w-4" />} onClick={() => setShowWizard(true)}>
            Add Source
          </Button>
        </div>
      </div>

      {showWizard ? <AddSourceWizard onClose={() => setShowWizard(false)} /> : null}

      <div className="mb-5 flex gap-2">
        <TabButton active={activeTab === "sources"} onClick={() => setActiveTab("sources")}>
          Sources
        </TabButton>
        <TabButton active={activeTab === "history"} onClick={() => setActiveTab("history")}>
          Import History
        </TabButton>
      </div>

      {activeTab === "sources" ? (
        <SourcesTable sources={sourcesQuery.data?.sources ?? []} isLoading={sourcesQuery.isLoading} />
      ) : (
        <ImportHistoryTable imports={historyQuery.data?.imports ?? []} isLoading={historyQuery.isLoading} />
      )}
    </AppShell>
  );
}

function AddSourceWizard({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [step, setStep] = useState(1);
  const [name, setName] = useState("");
  const [method, setMethod] = useState<SourceMethod>("m3u_url");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [refreshInterval, setRefreshInterval] = useState("1440");
  const [enabledContentTypes, setEnabledContentTypes] = useState<ContentType[]>(["live_tv"]);
  const [confirmLargeImport, setConfirmLargeImport] = useState(false);
  const [validation, setValidation] = useState<SourceValidation | null>(null);

  const parsedRefreshInterval = useMemo(() => {
    const trimmed = refreshInterval.trim();
    if (!trimmed) {
      return null;
    }
    return Number(trimmed);
  }, [refreshInterval]);

  const validateMutation = useMutation({
    mutationFn: () => {
      if (method === "m3u_url") {
        return validateM3uUrl(url, enabledContentTypes);
      }
      if (!file) {
        throw new Error("Choose an M3U file before validating.");
      }
      return validateM3uUpload(file, enabledContentTypes);
    },
    onSuccess: (result) => setValidation(result),
  });
  const createMutation = useMutation({
    mutationFn: () => {
      if (!validation?.playlist_reachable) {
        throw new Error("Validate the playlist before creating the source.");
      }
      if (parsedRefreshInterval !== null && Number.isNaN(parsedRefreshInterval)) {
        throw new Error("Refresh interval must be a number of minutes.");
      }
      if (method === "m3u_url") {
        return createM3uUrlSource({
          name,
          url,
          refresh_interval_minutes: parsedRefreshInterval,
          enabled_content_types: enabledContentTypes,
          confirm_large_import: confirmLargeImport,
        });
      }
      if (!file) {
        throw new Error("Choose an M3U file before creating the source.");
      }
      return createM3uUploadSource({
        name,
        file,
        refresh_interval_minutes: parsedRefreshInterval,
        enabled_content_types: enabledContentTypes,
        confirm_large_import: confirmLargeImport,
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sources"] });
      await queryClient.invalidateQueries({ queryKey: ["import-history"] });
      onClose();
    },
  });

  function submitStepOne(event: FormEvent) {
    event.preventDefault();
    setStep(2);
  }

  function submitStepTwo(event: FormEvent) {
    event.preventDefault();
    setValidation(null);
    setStep(3);
  }

  return (
    <section className="mb-6 rounded-lg border border-zinc-800 bg-zinc-900 p-5 shadow-panel">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">Add Source</h2>
          <p className="mt-1 text-sm text-zinc-400">Step {step} of 3</p>
        </div>
        <Button tone="ghost" onClick={onClose}>
          Close
        </Button>
      </div>

      {step === 1 ? (
        <form onSubmit={submitStepOne} className="space-y-5">
          <FormField
            label="Source name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
          />
          <Button type="submit" disabled={!name.trim()}>
            Continue
          </Button>
        </form>
      ) : null}

      {step === 2 ? (
        <form onSubmit={submitStepTwo} className="space-y-5">
          <div className="grid gap-3 md:grid-cols-2">
            <ChoiceButton
              active={method === "m3u_url"}
              title="Remote M3U URL"
              detail="Fetches an authorized playlist from HTTP or HTTPS."
              onClick={() => {
                setMethod("m3u_url");
                setValidation(null);
              }}
            />
            <ChoiceButton
              active={method === "m3u_upload"}
              title="Upload M3U file"
              detail="Stores a local uploaded playlist for imports."
              onClick={() => {
                setMethod("m3u_upload");
                setValidation(null);
              }}
            />
          </div>
          {method === "m3u_url" ? (
            <FormField
              label="M3U URL"
              type="url"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              required
            />
          ) : (
            <label className="block space-y-2 text-sm font-medium text-zinc-200">
              <span>M3U file</span>
              <input
                className="block w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-3 text-sm text-zinc-300 file:mr-4 file:rounded-md file:border-0 file:bg-forge-500 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white focus:border-forge-300 focus:outline-none focus:ring-2 focus:ring-forge-300/20"
                type="file"
                accept=".m3u,.m3u8,audio/mpegurl,application/vnd.apple.mpegurl,text/plain"
                onChange={(event) => {
                  setFile(event.target.files?.[0] ?? null);
                  setValidation(null);
                }}
                required
              />
            </label>
          )}
          <FormField
            label="Refresh interval minutes"
            type="number"
            min={15}
            max={43200}
            value={refreshInterval}
            onChange={(event) => setRefreshInterval(event.target.value)}
            hint="Leave blank to disable scheduled refresh."
          />
          <ContentTypeOptions
            selected={enabledContentTypes}
            onChange={(nextTypes) => {
              setEnabledContentTypes(nextTypes);
              setValidation(null);
              setConfirmLargeImport(false);
            }}
          />
          <div className="flex gap-3">
            <Button type="button" tone="secondary" onClick={() => setStep(1)}>
              Back
            </Button>
            <Button type="submit" disabled={method === "m3u_url" ? !url.trim() : !file}>
              Continue
            </Button>
          </div>
        </form>
      ) : null}

      {step === 3 ? (
        <div className="space-y-5">
          <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
            <p className="text-sm font-semibold">{name}</p>
            <p className="mt-1 text-sm text-zinc-500">
              {method === "m3u_url" ? redactUrlForDisplay(url) : file?.name ?? "No file selected"}
            </p>
            <p className="mt-1 text-xs text-zinc-600">
              Importing: {enabledContentTypes.map(contentTypeLabel).join(", ")}
            </p>
          </div>
          {validation?.requires_confirmation ? (
            <label className="flex items-start gap-3 rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">
              <input
                className="mt-1"
                type="checkbox"
                checked={confirmLargeImport}
                onChange={(event) => setConfirmLargeImport(event.target.checked)}
              />
              <span>
                I understand this playlist has {validation.total_entry_count.toLocaleString()} entries and
                confirm importing {validation.selected_entry_count.toLocaleString()} selected entries.
              </span>
            </label>
          ) : null}
          <div className="flex flex-wrap gap-3">
            <Button
              tone="secondary"
              icon={<Wifi aria-hidden className="h-4 w-4" />}
              onClick={() => validateMutation.mutate()}
              disabled={validateMutation.isPending}
            >
              Validate source
            </Button>
            <Button
              icon={<Upload aria-hidden className="h-4 w-4" />}
              onClick={() => createMutation.mutate()}
              disabled={
                !validation?.playlist_reachable ||
                validation.selected_entry_count === 0 ||
                (validation.requires_confirmation && !confirmLargeImport) ||
                createMutation.isPending
              }
            >
              Create and import
            </Button>
          </div>
          <ValidationResult validation={validation} error={validateMutation.error ?? createMutation.error} />
          <Button type="button" tone="ghost" onClick={() => setStep(2)}>
            Back
          </Button>
        </div>
      ) : null}
    </section>
  );
}

function ValidationResult({
  validation,
  error,
}: {
  validation: SourceValidation | null;
  error: unknown;
}) {
  if (error instanceof Error) {
    return (
      <p role="alert" className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-100">
        {error.message}
      </p>
    );
  }
  if (!validation) {
    return null;
  }
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
      <div className="grid gap-3 md:grid-cols-4">
        <ValidationStat
          ok={validation.playlist_reachable}
          label="Playlist reachable"
          value={validation.playlist_reachable ? "Yes" : "No"}
        />
        <ValidationStat ok label="Selected entries" value={validation.selected_entry_count.toLocaleString()} />
        <ValidationStat ok label="Group count" value={String(validation.group_count)} />
        <ValidationStat
          ok
          label="Estimated import time"
          value={`${validation.estimated_import_time_seconds} sec`}
        />
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <ValidationStat ok label="Total entries" value={validation.total_entry_count.toLocaleString()} />
        <ValidationStat ok label="Excluded entries" value={validation.excluded_entry_count.toLocaleString()} />
        <ValidationStat
          ok
          label="Database impact"
          value={`${validation.estimated_database_rows.toLocaleString()} rows / ${formatBytes(
            validation.estimated_database_bytes,
          )}`}
        />
      </div>
      <ContentCounts counts={validation.content_counts} />
      {validation.metadata_samples.length ? <MetadataSamples samples={validation.metadata_samples} /> : null}
      {validation.errors.length ? (
        <MessageList tone="error" messages={validation.errors} />
      ) : null}
      {validation.warnings.length ? (
        <MessageList tone="warning" messages={validation.warnings} />
      ) : null}
    </div>
  );
}

function ValidationStat({ ok, label, value }: { ok: boolean; label: string; value: string }) {
  return (
    <div className="flex min-h-20 gap-3 rounded-md border border-zinc-800 bg-zinc-900 p-3">
      {ok ? (
        <CheckCircle2 aria-hidden className="mt-0.5 h-5 w-5 text-emerald-300" />
      ) : (
        <XCircle aria-hidden className="mt-0.5 h-5 w-5 text-red-300" />
      )}
      <div>
        <p className="text-xs text-zinc-500">{label}</p>
        <p className="mt-1 text-sm font-semibold">{value}</p>
      </div>
    </div>
  );
}

function ContentTypeOptions({
  selected,
  onChange,
}: {
  selected: ContentType[];
  onChange: (contentTypes: ContentType[]) => void;
}) {
  function toggle(contentType: ContentType) {
    const next = selected.includes(contentType)
      ? selected.filter((item) => item !== contentType)
      : [...selected, contentType];
    onChange(next.length ? next : ["live_tv"]);
  }

  return (
    <fieldset className="space-y-3 rounded-lg border border-zinc-800 bg-zinc-950 p-4">
      <legend className="text-sm font-semibold text-zinc-200">Import content types</legend>
      <div className="grid gap-3 md:grid-cols-4">
        <ContentTypeCheckbox
          checked={selected.includes("live_tv")}
          label="Live TV"
          detail="Default IPTV setup"
          onChange={() => toggle("live_tv")}
        />
        <ContentTypeCheckbox
          checked={selected.includes("unknown")}
          label="Unknown"
          detail="Store only if you choose it"
          onChange={() => toggle("unknown")}
        />
        <ContentTypeCheckbox checked={false} label="Movies" detail="Deferred; excluded" disabled />
        <ContentTypeCheckbox checked={false} label="Series" detail="Deferred; excluded" disabled />
      </div>
    </fieldset>
  );
}

function ContentTypeCheckbox({
  checked,
  label,
  detail,
  disabled = false,
  onChange,
}: {
  checked: boolean;
  label: string;
  detail: string;
  disabled?: boolean;
  onChange?: () => void;
}) {
  return (
    <label className="flex min-h-20 gap-3 rounded-md border border-zinc-800 bg-zinc-900 p-3 text-sm">
      <input
        className="mt-1"
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={onChange}
      />
      <span>
        <span className="block font-semibold text-zinc-100">{label}</span>
        <span className="mt-1 block text-xs text-zinc-500">{detail}</span>
      </span>
    </label>
  );
}

function ContentCounts({ counts }: { counts: Record<string, number> }) {
  return (
    <div className="mt-4 rounded-md border border-zinc-800 bg-zinc-900 p-3 text-sm text-zinc-300">
      <p className="font-semibold">Detected content</p>
      <p className="mt-2 text-zinc-400">
        Live TV: {(counts.live_tv ?? 0).toLocaleString()} - Movies:{" "}
        {(counts.movie ?? 0).toLocaleString()} - Series: {(counts.series ?? 0).toLocaleString()} - Unknown:{" "}
        {(counts.unknown ?? 0).toLocaleString()}
      </p>
    </div>
  );
}

function MetadataSamples({ samples }: { samples: Array<Record<string, unknown>> }) {
  return (
    <div className="mt-4 rounded-md border border-zinc-800 bg-zinc-900 p-3 text-sm text-zinc-300">
      <p className="font-semibold">Metadata sample</p>
      <ul className="mt-2 space-y-1 text-xs text-zinc-500">
        {samples.slice(0, 5).map((sample) => (
          <li key={`${String(sample.line_number)}-${String(sample.name)}`}>
            Line {String(sample.line_number)} - {String(sample.name)} - {String(sample.group ?? "No group")} -{" "}
            {contentTypeLabel(sample.content_type as ContentType)}
          </li>
        ))}
      </ul>
    </div>
  );
}

function contentTypeLabel(contentType: ContentType): string {
  const labels: Record<ContentType, string> = {
    live_tv: "Live TV",
    movie: "Movies",
    series: "Series",
    unknown: "Unknown",
  };
  return labels[contentType];
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} KB`;
  }
  return `${Math.round(bytes / (1024 * 1024))} MB`;
}

function SourcesTable({ sources, isLoading }: { sources: SourceSummary[]; isLoading: boolean }) {
  const queryClient = useQueryClient();
  const refreshMutation = useMutation({
    mutationFn: refreshSource,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sources"] });
      await queryClient.invalidateQueries({ queryKey: ["import-history"] });
    },
  });
  const updateMutation = useMutation({
    mutationFn: ({ sourceId, enabled }: { sourceId: string; enabled: boolean }) =>
      updateSource(sourceId, { is_enabled: enabled }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
  });
  const deleteMutation = useMutation({
    mutationFn: deleteSource,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sources"] });
      await queryClient.invalidateQueries({ queryKey: ["import-history"] });
    },
  });

  if (isLoading) {
    return <StatusPanel title="Loading sources" detail="Checking configured television sources." />;
  }
  if (!sources.length) {
    return (
      <StatusPanel
        title="No sources yet"
        detail="Add a remote M3U URL, upload a synthetic playlist, or create the built-in demo source."
      />
    );
  }

  return (
    <section className="overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900">
      <div className="grid gap-4 border-b border-zinc-800 px-4 py-3 text-xs font-semibold uppercase text-zinc-500 md:grid-cols-[1.3fr_0.8fr_0.7fr_0.8fr_0.8fr_1.1fr]">
        <span>Sources</span>
        <span>Status</span>
        <span>Refresh</span>
        <span>Last Updated</span>
        <span>Channels</span>
        <span>Actions</span>
      </div>
      <div className="divide-y divide-zinc-800">
        {sources.map((source) => (
          <article
            key={source.id}
            className="grid gap-4 px-4 py-4 md:grid-cols-[1.3fr_0.8fr_0.7fr_0.8fr_0.8fr_1.1fr] md:items-center"
          >
            <div>
              <h2 className="font-semibold">{source.name}</h2>
              <p className="mt-1 text-sm text-zinc-500">{sourceTypeLabel(source.source_type)}</p>
              <p className="mt-1 text-xs text-zinc-500">
                Importing {source.enabled_content_types.map(contentTypeLabel).join(", ")}
              </p>
              <p className="mt-1 break-words text-xs text-zinc-600">{source.display_location}</p>
              {source.active_job ? <ProgressBar source={source} /> : null}
            </div>
            <div>
              <StatusBadge status={source.status} />
              <p className="mt-2 text-xs leading-5 text-zinc-500">{source.status_message}</p>
            </div>
            <p className="text-sm text-zinc-400">
              {source.refresh_interval_minutes ? `${source.refresh_interval_minutes} min` : "Manual"}
            </p>
            <p className="text-sm text-zinc-400">{formatDateTime(source.last_updated_at)}</p>
            <p className="text-sm text-zinc-400">
              {source.channel_count} channels
              <span className="block text-xs text-zinc-600">{source.group_count} groups</span>
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
                tone="secondary"
                onClick={() => refreshMutation.mutate(source.id)}
                disabled={!source.is_enabled || source.active_job !== null}
              >
                Manual Refresh
              </Button>
              <Button
                tone="ghost"
                onClick={() => updateMutation.mutate({ sourceId: source.id, enabled: !source.is_enabled })}
              >
                {source.is_enabled ? "Disable Source" : "Enable Source"}
              </Button>
              <Button
                tone="ghost"
                icon={<Trash2 aria-hidden className="h-4 w-4" />}
                onClick={() => {
                  if (window.confirm(`Delete ${source.name}? Import records will remain in history.`)) {
                    deleteMutation.mutate(source.id);
                  }
                }}
              >
                Delete Source
              </Button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function ImportHistoryTable({
  imports,
  isLoading,
}: {
  imports: PlaylistImportHistoryItem[];
  isLoading: boolean;
}) {
  if (isLoading) {
    return <StatusPanel title="Loading import history" detail="Checking completed and failed imports." />;
  }
  if (!imports.length) {
    return <StatusPanel title="No import history" detail="Create a source to start recording import runs." />;
  }
  return (
    <section className="overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900">
      <div className="grid gap-4 border-b border-zinc-800 px-4 py-3 text-xs font-semibold uppercase text-zinc-500 md:grid-cols-[1fr_0.7fr_0.8fr_0.8fr_0.8fr_1.1fr]">
        <span>Import History</span>
        <span>Status</span>
        <span>Started</span>
        <span>Duration</span>
        <span>Imported</span>
        <span>Errors</span>
      </div>
      <div className="divide-y divide-zinc-800">
        {imports.map((item) => (
          <article
            key={item.id}
            className="grid gap-4 px-4 py-4 md:grid-cols-[1fr_0.7fr_0.8fr_0.8fr_0.8fr_1.1fr] md:items-start"
          >
            <div>
              <h2 className="font-semibold">{item.source_name}</h2>
              <p className="mt-1 text-xs text-zinc-500">{item.source_version ?? "No version"}</p>
              <p className="mt-1 text-xs text-zinc-600">{item.checksum ?? "No checksum"}</p>
            </div>
            <span className="text-sm capitalize text-zinc-300">{item.status}</span>
            <p className="text-sm text-zinc-400">{formatDateTime(item.started_at)}</p>
            <p className="text-sm text-zinc-400">{formatDuration(item.duration_ms)}</p>
            <p className="text-sm text-zinc-400">
              {item.channel_count} channels
              <span className="block text-xs text-zinc-600">{item.group_count} groups</span>
            </p>
            <div className="text-sm text-zinc-400">
              {item.failure_reason ?? `${item.warning_count} warnings, ${item.failure_count} failures`}
              {item.warnings.length ? <MessageList tone="warning" messages={item.warnings.slice(0, 2)} /> : null}
              {item.failures.length ? <MessageList tone="error" messages={item.failures.slice(0, 2)} /> : null}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function ProgressBar({ source }: { source: SourceSummary }) {
  const progress = source.active_job?.progress_percent ?? 0;
  return (
    <div className="mt-3">
      <div className="h-2 overflow-hidden rounded-full bg-zinc-800">
        <div className="h-full bg-forge-500 transition-all" style={{ width: `${progress}%` }} />
      </div>
      <p className="mt-1 text-xs text-zinc-500">{source.active_job?.message ?? "Importing"}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: SourceSummary["status"] }) {
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${sourceStatusClass(status)}`}>
      {sourceStatusLabel(status)}
    </span>
  );
}

function ChoiceButton({
  active,
  title,
  detail,
  onClick,
}: {
  active: boolean;
  title: string;
  detail: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`min-h-32 rounded-lg border p-4 text-left transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forge-300 ${
        active ? "border-forge-300 bg-forge-500/10" : "border-zinc-800 bg-zinc-950 hover:border-zinc-600"
      }`}
    >
      <span className="block text-base font-semibold">{title}</span>
      <span className="mt-2 block text-sm leading-6 text-zinc-400">{detail}</span>
    </button>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`min-h-10 rounded-md px-4 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forge-300 ${
        active ? "bg-zinc-800 text-white" : "text-zinc-400 hover:bg-zinc-900"
      }`}
    >
      {children}
    </button>
  );
}

function MessageList({ tone, messages }: { tone: "warning" | "error"; messages: string[] }) {
  const className =
    tone === "warning"
      ? "border-amber-500/30 bg-amber-500/10 text-amber-100"
      : "border-red-500/30 bg-red-500/10 text-red-100";
  return (
    <ul className={`mt-3 space-y-1 rounded-md border px-3 py-2 text-sm ${className}`}>
      {messages.map((message) => (
        <li key={message}>{message}</li>
      ))}
    </ul>
  );
}

function StatusPanel({ title, detail }: { title: string; detail: string }) {
  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-5">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-2 text-sm text-zinc-400">{detail}</p>
    </section>
  );
}
