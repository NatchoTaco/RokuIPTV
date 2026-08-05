import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Layers3, RefreshCw, Search, ShieldCheck, ShieldOff, SlidersHorizontal } from "lucide-react";
import { useMemo, useState } from "react";

import { AppShell } from "../components/AppShell";
import { Button } from "../components/Button";
import {
  createNormalizationJob,
  listChannelGroups,
  listChannels,
  listChannelSourceCandidates,
  updateChannel,
  type ChannelSummary,
  type ContentType,
  type FilterProfile,
  type User,
} from "../lib/api";
import { channelProtectionActionLabel, nextChannelProtectionState, visibilityFilterOptions } from "../lib/protection";

type DuplicateFilter = "all" | "duplicates" | "unique";

export function ChannelsPage({ user }: { user: User }) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [group, setGroup] = useState("");
  const [visibility, setVisibility] = useState("");
  const [contentType, setContentType] = useState<ContentType | "">("");
  const [duplicateStatus, setDuplicateStatus] = useState<DuplicateFilter>("all");
  const [profile, setProfile] = useState<FilterProfile>("recommended");
  const [cursorStack, setCursorStack] = useState<string[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [candidateChannelId, setCandidateChannelId] = useState<string | null>(null);

  const currentCursor = cursorStack.at(-1) ?? null;
  const channelsQuery = useQuery({
    queryKey: ["channels", currentCursor, search, group, visibility, contentType, duplicateStatus],
    queryFn: () =>
      listChannels({
        cursor: currentCursor,
        page_size: 50,
        search,
        group,
        visibility_status: visibility,
        content_type: contentType || undefined,
        duplicate_status: duplicateStatus === "all" ? undefined : duplicateStatus,
      }),
  });
  const groupsQuery = useQuery({
    queryKey: ["channel-groups"],
    queryFn: listChannelGroups,
  });
  const normalizationMutation = useMutation({
    mutationFn: () => createNormalizationJob({ profile, process_now: false }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["channels"] });
    },
  });
  const updateMutation = useMutation({
    mutationFn: ({ channelId, payload }: { channelId: string; payload: Parameters<typeof updateChannel>[1] }) =>
      updateChannel(channelId, payload),
    onSuccess: async () => {
      setSelectedIds(new Set());
      await queryClient.invalidateQueries({ queryKey: ["channels"] });
      await queryClient.invalidateQueries({ queryKey: ["cleanup"] });
    },
  });

  const channels = channelsQuery.data?.items ?? [];
  const selectedCount = selectedIds.size;
  const selectedProtectedCount = channels.filter(
    (channel) => selectedIds.has(channel.id) && channel.protected_from_auto_merge,
  ).length;
  const allPageSelected = channels.length > 0 && channels.every((channel) => selectedIds.has(channel.id));

  function resetCursor() {
    setCursorStack([]);
    setSelectedIds(new Set());
  }

  async function bulkVisibility(visibilityStatus: "hidden" | "always_visible") {
    await Promise.all(
      [...selectedIds].map((channelId) =>
        updateMutation.mutateAsync({ channelId, payload: { visibility_status: visibilityStatus } }),
      ),
    );
  }

  async function bulkUnprotect() {
    await Promise.all(
      [...selectedIds].map((channelId) =>
        updateMutation.mutateAsync({ channelId, payload: { protected_from_auto_merge: false } }),
      ),
    );
  }

  return (
    <AppShell user={user}>
      <div className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="text-sm font-medium uppercase text-forge-300">Channels</p>
          <h1 className="mt-2 text-3xl font-semibold">Curated channel lineup</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-400">
            Normalize provider names, review duplicates, and curate Live TV without exposing stream URLs.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <select
            className="min-h-11 rounded-md border border-zinc-700 bg-zinc-900 px-3 text-sm text-zinc-100"
            value={profile}
            onChange={(event) => setProfile(event.target.value as FilterProfile)}
            aria-label="Cleanup profile"
          >
            <option value="light">Light</option>
            <option value="recommended">Recommended</option>
            <option value="aggressive">Aggressive</option>
            <option value="custom">Custom</option>
          </select>
          <Button
            icon={<SlidersHorizontal aria-hidden className="h-4 w-4" />}
            onClick={() => normalizationMutation.mutate()}
            disabled={normalizationMutation.isPending}
          >
            Queue normalization
          </Button>
          <Button
            tone="secondary"
            icon={<RefreshCw aria-hidden className="h-4 w-4" />}
            onClick={() => void channelsQuery.refetch()}
          >
            Refresh
          </Button>
        </div>
      </div>

      {normalizationMutation.data ? (
        <StatusPanel
          title="Normalization queued"
          detail={`${normalizationMutation.data.message} Job ${normalizationMutation.data.id.slice(0, 8)} will be processed by the worker.`}
        />
      ) : null}

      <section className="mb-5 grid gap-3 rounded-lg border border-zinc-800 bg-zinc-900 p-4 md:grid-cols-[1.5fr_1fr_1fr_1fr_1fr]">
        <label className="relative block">
          <Search aria-hidden className="absolute left-3 top-3 h-5 w-5 text-zinc-500" />
          <input
            className="min-h-11 w-full rounded-md border border-zinc-700 bg-zinc-950 py-2 pl-10 pr-3 text-sm text-zinc-100 focus:border-forge-300 focus:outline-none focus:ring-2 focus:ring-forge-300/20"
            placeholder="Search original, normalized, or tvg id"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              resetCursor();
            }}
          />
        </label>
        <SelectFilter
          label="Group"
          value={group}
          onChange={(value) => {
            setGroup(value);
            resetCursor();
          }}
          options={(groupsQuery.data?.groups ?? []).map((item) => item.name)}
        />
        <SelectFilter
          label="Visibility"
          value={visibility}
          onChange={(value) => {
            setVisibility(value);
            resetCursor();
          }}
          options={[...visibilityFilterOptions]}
        />
        <SelectFilter
          label="Content"
          value={contentType}
          onChange={(value) => {
            setContentType(value as ContentType | "");
            resetCursor();
          }}
          options={["live_tv", "unknown", "movie", "series"]}
        />
        <SelectFilter
          label="Duplicates"
          value={duplicateStatus === "all" ? "" : duplicateStatus}
          onChange={(value) => {
            setDuplicateStatus((value || "all") as DuplicateFilter);
            resetCursor();
          }}
          options={["duplicates", "unique"]}
        />
      </section>

      {selectedCount ? (
        <section className="mb-5 flex flex-wrap items-center gap-3 rounded-lg border border-forge-500/30 bg-forge-500/10 p-4 text-sm text-forge-100">
          <span>{selectedCount} selected</span>
          <Button tone="secondary" onClick={() => void bulkVisibility("always_visible")}>
            Always allow
          </Button>
          <Button tone="secondary" onClick={() => void bulkVisibility("hidden")}>
            Hide selected
          </Button>
          <Button tone="secondary" onClick={() => void bulkUnprotect()} disabled={selectedProtectedCount === 0}>
            Unprotect selected ({selectedProtectedCount})
          </Button>
          <Button tone="ghost" onClick={() => setSelectedIds(new Set())}>
            Clear
          </Button>
        </section>
      ) : null}

      <ChannelTable
        channels={channels}
        isLoading={channelsQuery.isLoading}
        selectedIds={selectedIds}
        allPageSelected={allPageSelected}
        onToggleAll={() => {
          setSelectedIds(allPageSelected ? new Set() : new Set(channels.map((channel) => channel.id)));
        }}
        onToggle={(channelId) => {
          const next = new Set(selectedIds);
          if (next.has(channelId)) {
            next.delete(channelId);
          } else {
            next.add(channelId);
          }
          setSelectedIds(next);
        }}
        onEdit={(channel) => {
          const displayName = window.prompt("Normalized display name", channel.normalized_name ?? channel.original_name);
          if (!displayName) {
            return;
          }
          const groupName = window.prompt("Standard group", channel.normalized_group ?? "Other") ?? undefined;
          updateMutation.mutate({ channelId: channel.id, payload: { display_name: displayName, group_name: groupName } });
        }}
        onAllow={(channelId) => updateMutation.mutate({ channelId, payload: { visibility_status: "always_visible" } })}
        onHide={(channelId) => updateMutation.mutate({ channelId, payload: { visibility_status: "hidden" } })}
        onToggleProtection={(channel) =>
          updateMutation.mutate({
            channelId: channel.id,
            payload: { protected_from_auto_merge: nextChannelProtectionState(channel) },
          })
        }
        onCandidates={setCandidateChannelId}
      />

      <div className="mt-5 flex justify-between gap-3">
        <Button
          tone="secondary"
          disabled={!cursorStack.length}
          onClick={() => {
            setCursorStack(cursorStack.slice(0, -1));
            setSelectedIds(new Set());
          }}
        >
          Previous
        </Button>
        <p className="text-sm text-zinc-500">
          {channelsQuery.data?.total_count.toLocaleString() ?? "0"} matching channels
        </p>
        <Button
          tone="secondary"
          disabled={!channelsQuery.data?.next_cursor}
          onClick={() => {
            if (channelsQuery.data?.next_cursor) {
              setCursorStack([...cursorStack, channelsQuery.data.next_cursor]);
              setSelectedIds(new Set());
            }
          }}
        >
          Next
        </Button>
      </div>

      {candidateChannelId ? (
        <CandidatePanel channelId={candidateChannelId} onClose={() => setCandidateChannelId(null)} />
      ) : null}
    </AppShell>
  );
}

function ChannelTable({
  channels,
  isLoading,
  selectedIds,
  allPageSelected,
  onToggleAll,
  onToggle,
  onEdit,
  onAllow,
  onHide,
  onToggleProtection,
  onCandidates,
}: {
  channels: ChannelSummary[];
  isLoading: boolean;
  selectedIds: Set<string>;
  allPageSelected: boolean;
  onToggleAll: () => void;
  onToggle: (channelId: string) => void;
  onEdit: (channel: ChannelSummary) => void;
  onAllow: (channelId: string) => void;
  onHide: (channelId: string) => void;
  onToggleProtection: (channel: ChannelSummary) => void;
  onCandidates: (channelId: string) => void;
}) {
  if (isLoading) {
    return <StatusPanel title="Loading channels" detail="Fetching a bounded page from the API." />;
  }
  if (!channels.length) {
    return <StatusPanel title="No channels found" detail="Import a Live TV source, then queue normalization." />;
  }
  return (
    <section className="overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900">
      <div className="grid gap-4 border-b border-zinc-800 px-4 py-3 text-xs font-semibold uppercase text-zinc-500 md:grid-cols-[0.2fr_1.4fr_1fr_1fr_0.7fr_0.8fr_1.4fr]">
        <label className="sr-only" htmlFor="select-page">
          Select page
        </label>
        <input id="select-page" type="checkbox" checked={allPageSelected} onChange={onToggleAll} />
        <span>Channel</span>
        <span>Group</span>
        <span>Source</span>
        <span>Quality</span>
        <span>Status</span>
        <span>Actions</span>
      </div>
      <div className="divide-y divide-zinc-800">
        {channels.map((channel) => (
          <article
            key={channel.id}
            className="grid gap-4 px-4 py-4 md:grid-cols-[0.2fr_1.4fr_1fr_1fr_0.7fr_0.8fr_1.4fr] md:items-start"
          >
            <input
              type="checkbox"
              checked={selectedIds.has(channel.id)}
              onChange={() => onToggle(channel.id)}
              aria-label={`Select ${channel.original_name}`}
            />
            <div>
              <h2 className="font-semibold">{channel.normalized_name ?? channel.original_name}</h2>
              <p className="mt-1 text-xs text-zinc-500">Original: {channel.original_name}</p>
              <p className="mt-1 text-xs text-zinc-600">tvg-id: {channel.original_tvg_id ?? "missing"}</p>
            </div>
            <div className="text-sm text-zinc-400">
              <p>{channel.normalized_group ?? "Unclassified"}</p>
              <p className="mt-1 text-xs text-zinc-600">
                {channel.inferred_country ?? "No country"} · {channel.inferred_language ?? "No language"}
              </p>
            </div>
            <div className="text-sm text-zinc-400">
              <p>{channel.source_name ?? "Unknown source"}</p>
              <p className="mt-1 text-xs text-zinc-600">{contentTypeLabel(channel.content_type)}</p>
            </div>
            <p className="text-sm text-zinc-400">{channel.claimed_quality ?? "Unknown"}</p>
            <div className="space-y-2">
              <Badge label={channel.visibility_status} />
              {channel.duplicate_cluster_id ? <Badge label="duplicate" tone="amber" /> : null}
              {channel.protected_from_auto_merge ? <Badge label="protected" tone="forge" /> : null}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button tone="ghost" onClick={() => onEdit(channel)}>
                Rename
              </Button>
              <Button tone="ghost" icon={<Check aria-hidden className="h-4 w-4" />} onClick={() => onAllow(channel.id)}>
                Allow
              </Button>
              <Button tone="ghost" onClick={() => onHide(channel.id)}>
                Hide
              </Button>
              <Button
                tone="ghost"
                icon={
                  channel.protected_from_auto_merge ? (
                    <ShieldOff aria-hidden className="h-4 w-4" />
                  ) : (
                    <ShieldCheck aria-hidden className="h-4 w-4" />
                  )
                }
                onClick={() => onToggleProtection(channel)}
              >
                {channelProtectionActionLabel(channel)}
              </Button>
              <Button tone="ghost" icon={<Layers3 aria-hidden className="h-4 w-4" />} onClick={() => onCandidates(channel.id)}>
                Candidates
              </Button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function CandidatePanel({ channelId, onClose }: { channelId: string; onClose: () => void }) {
  const candidatesQuery = useQuery({
    queryKey: ["channel-candidates", channelId],
    queryFn: () => listChannelSourceCandidates(channelId),
  });
  return (
    <section className="mt-6 rounded-lg border border-zinc-800 bg-zinc-900 p-5 shadow-panel">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">Source candidates</h2>
          <p className="mt-1 text-sm text-zinc-400">Credentials stay hidden; only checksums and metadata are shown.</p>
        </div>
        <Button tone="ghost" onClick={onClose}>
          Close
        </Button>
      </div>
      <div className="mt-4 space-y-3">
        {(candidatesQuery.data?.candidates ?? []).map((candidate) => (
          <article key={candidate.id} className="rounded-md border border-zinc-800 bg-zinc-950 p-3 text-sm text-zinc-300">
            <div className="flex flex-wrap items-center gap-2">
              <Badge label={candidate.role} />
              <span>Rank {candidate.rank + 1}</span>
              <span>{candidate.claimed_quality ?? "Unknown quality"}</span>
            </div>
            <p className="mt-2 font-semibold">{candidate.normalized_name ?? candidate.original_name}</p>
            <p className="mt-1 text-xs text-zinc-600">URL checksum: {candidate.url_checksum ?? "missing"}</p>
            <p className="mt-1 text-xs text-zinc-500">{candidate.selection_reason ?? "No selection reason."}</p>
          </article>
        ))}
        {!candidatesQuery.isLoading && !candidatesQuery.data?.candidates.length ? (
          <p className="text-sm text-zinc-500">No candidate rows have been generated yet.</p>
        ) : null}
      </div>
    </section>
  );
}

function SelectFilter({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  const uniqueOptions = useMemo(() => [...new Set(options)], [options]);
  return (
    <label className="block text-xs font-semibold uppercase text-zinc-500">
      <span>{label}</span>
      <select
        className="mt-2 min-h-11 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 text-sm normal-case text-zinc-100 focus:border-forge-300 focus:outline-none focus:ring-2 focus:ring-forge-300/20"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">Any</option>
        {uniqueOptions.map((option) => (
          <option key={option} value={option}>
            {optionLabel(option)}
          </option>
        ))}
      </select>
    </label>
  );
}

function Badge({ label, tone = "zinc" }: { label: string; tone?: "zinc" | "amber" | "forge" }) {
  const className =
    tone === "forge"
      ? "border-forge-500/30 bg-forge-500/10 text-forge-100"
      : tone === "amber"
        ? "border-amber-500/30 bg-amber-500/10 text-amber-100"
        : "border-zinc-700 bg-zinc-950 text-zinc-300";
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${className}`}>{optionLabel(label)}</span>;
}

function StatusPanel({ title, detail }: { title: string; detail: string }) {
  return (
    <section className="mb-5 rounded-lg border border-zinc-800 bg-zinc-900 p-5">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-2 text-sm text-zinc-400">{detail}</p>
    </section>
  );
}

function optionLabel(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function contentTypeLabel(contentType: ContentType): string {
  const labels: Record<ContentType, string> = {
    live_tv: "Live TV",
    movie: "Movie",
    series: "Series",
    unknown: "Unknown",
  };
  return labels[contentType];
}
