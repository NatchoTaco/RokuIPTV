import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, GitMerge, Scissors, ShieldCheck, ShieldOff, Wand2 } from "lucide-react";
import { useState } from "react";

import { AppShell } from "../components/AppShell";
import { Button } from "../components/Button";
import {
  applyCleanupProfile,
  clearManualProtections,
  getProtectionSummary,
  listCleanupQueues,
  listDuplicateClusters,
  mergeDuplicateCluster,
  previewCleanupProfile,
  protectDuplicateCluster,
  splitDuplicateCluster,
  unprotectDuplicateCluster,
  type CleanupPreview,
  type DuplicateCluster,
  type FilterProfile,
  type User,
} from "../lib/api";
import {
  clearProtectionsConfirmation,
  duplicateProtectionAction,
  duplicateProtectionActionLabel,
} from "../lib/protection";

type DuplicateAction = "merge" | "split" | "protect" | "unprotect";

export function CleanupCenterPage({ user }: { user: User }) {
  const queryClient = useQueryClient();
  const [profile, setProfile] = useState<FilterProfile>("recommended");
  const queuesQuery = useQuery({
    queryKey: ["cleanup", "queues"],
    queryFn: listCleanupQueues,
    refetchInterval: 5000,
  });
  const duplicatesQuery = useQuery({
    queryKey: ["cleanup", "duplicates"],
    queryFn: listDuplicateClusters,
    refetchInterval: 5000,
  });
  const protectionsQuery = useQuery({
    queryKey: ["cleanup", "protections"],
    queryFn: getProtectionSummary,
    refetchInterval: 5000,
  });
  const previewMutation = useMutation({
    mutationFn: previewCleanupProfile,
  });
  const applyMutation = useMutation({
    mutationFn: applyCleanupProfile,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["channels"] });
      await queryClient.invalidateQueries({ queryKey: ["cleanup"] });
    },
  });
  function refreshPreviewIfVisible() {
    if (previewMutation.data ?? applyMutation.data) {
      previewMutation.mutate(profile);
    }
  }

  const duplicateMutation = useMutation({
    mutationFn: ({ clusterId, action }: { clusterId: string; action: DuplicateAction }) => {
      if (action === "merge") {
        return mergeDuplicateCluster(clusterId);
      }
      if (action === "split") {
        return splitDuplicateCluster(clusterId);
      }
      if (action === "unprotect") {
        return unprotectDuplicateCluster(clusterId);
      }
      return protectDuplicateCluster(clusterId);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["channels"] });
      await queryClient.invalidateQueries({ queryKey: ["cleanup"] });
      refreshPreviewIfVisible();
    },
  });
  const clearProtectionsMutation = useMutation({
    mutationFn: clearManualProtections,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["channels"] });
      await queryClient.invalidateQueries({ queryKey: ["cleanup"] });
      refreshPreviewIfVisible();
    },
  });

  const activePreview = applyMutation.data ?? previewMutation.data;
  const totalProtectionCount = protectionsQuery.data?.total_protection_count ?? 0;

  function confirmClearProtections() {
    if (totalProtectionCount === 0) {
      return;
    }
    if (window.confirm(clearProtectionsConfirmation(totalProtectionCount))) {
      clearProtectionsMutation.mutate();
    }
  }

  return (
    <AppShell user={user}>
      <div className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="text-sm font-medium uppercase text-forge-300">Cleanup Center</p>
          <h1 className="mt-2 text-3xl font-semibold">Review normalization decisions</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-400">
            Preview profile effects, resolve duplicate clusters, and protect channels before hiding anything.
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
            tone="secondary"
            icon={<Wand2 aria-hidden className="h-4 w-4" />}
            onClick={() => previewMutation.mutate(profile)}
            disabled={previewMutation.isPending}
          >
            Preview
          </Button>
          <Button
            icon={<CheckCircle2 aria-hidden className="h-4 w-4" />}
            onClick={() => applyMutation.mutate(profile)}
            disabled={applyMutation.isPending}
          >
            Apply profile
          </Button>
          <Button
            tone="secondary"
            icon={<ShieldOff aria-hidden className="h-4 w-4" />}
            onClick={confirmClearProtections}
            disabled={totalProtectionCount === 0 || clearProtectionsMutation.isPending}
          >
            Clear protections ({totalProtectionCount.toLocaleString()})
          </Button>
        </div>
      </div>

      {activePreview ? <PreviewPanel preview={activePreview} applied={"applied" in activePreview && activePreview.applied} /> : null}

      <section className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {(queuesQuery.data?.queues ?? []).map((queue) => (
          <article key={queue.key} className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <p className="text-2xl font-semibold">{queue.count.toLocaleString()}</p>
            <h2 className="mt-2 text-sm font-semibold">{queue.label}</h2>
            <p className="mt-2 text-xs leading-5 text-zinc-500">{queue.description}</p>
          </article>
        ))}
      </section>

      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-5">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold">Duplicate clusters</h2>
            <p className="mt-1 text-sm text-zinc-400">Conservative clusters only; ambiguous matches stay reviewable.</p>
          </div>
          <Button tone="secondary" onClick={() => void duplicatesQuery.refetch()}>
            Refresh
          </Button>
        </div>
        <div className="space-y-3">
          {(duplicatesQuery.data?.clusters ?? []).map((cluster) => (
            <DuplicateClusterCard
              key={cluster.id}
              cluster={cluster}
              onAction={(action) => duplicateMutation.mutate({ clusterId: cluster.id, action })}
            />
          ))}
          {!duplicatesQuery.isLoading && !duplicatesQuery.data?.clusters.length ? (
            <p className="rounded-md border border-zinc-800 bg-zinc-950 p-4 text-sm text-zinc-500">
              No duplicate clusters have been generated yet. Queue channel normalization first.
            </p>
          ) : null}
        </div>
      </section>
    </AppShell>
  );
}

function PreviewPanel({ preview, applied }: { preview: CleanupPreview; applied: boolean }) {
  return (
    <section className="mb-6 rounded-lg border border-forge-500/30 bg-forge-500/10 p-4 text-sm text-forge-100">
      <div className="grid gap-3 md:grid-cols-4">
        <PreviewStat label="Profile" value={preview.profile} />
        <PreviewStat label={applied ? "Hidden after apply" : "Would hide"} value={preview.would_hide.toLocaleString()} />
        <PreviewStat label="Allowed" value={preview.would_allow.toLocaleString()} />
        <PreviewStat label="Protected" value={preview.protected_count.toLocaleString()} />
      </div>
      {Object.keys(preview.reasons).length ? (
        <p className="mt-3 text-xs text-forge-200">
          Reasons:{" "}
          {Object.entries(preview.reasons)
            .map(([reason, count]) => `${reason} (${count})`)
            .join(", ")}
        </p>
      ) : null}
    </section>
  );
}

function PreviewStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-forge-300/20 bg-zinc-950/50 p-3">
      <p className="text-xs uppercase text-forge-200">{optionLabel(label)}</p>
      <p className="mt-1 text-lg font-semibold">{optionLabel(value)}</p>
    </div>
  );
}

function DuplicateClusterCard({
  cluster,
  onAction,
}: {
  cluster: DuplicateCluster;
  onAction: (action: DuplicateAction) => void;
}) {
  const protectionAction = duplicateProtectionAction(cluster);
  const isProtected = protectionAction === "unprotect";
  return (
    <article className="rounded-md border border-zinc-800 bg-zinc-950 p-4">
      <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
        <div>
          <h3 className="font-semibold">{cluster.label}</h3>
          <p className="mt-1 text-sm text-zinc-500">
            {cluster.candidate_count} candidates · {(cluster.confidence_score * 100).toFixed(0)}% confidence ·{" "}
            {optionLabel(cluster.review_status)}
          </p>
          <ul className="mt-2 space-y-1 text-xs text-zinc-600">
            {cluster.explanations.slice(0, 3).map((item, index) => (
              <li key={`${cluster.id}-${index}`}>{String(item.reason ?? "Duplicate evidence retained.")}</li>
            ))}
          </ul>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button tone="ghost" icon={<GitMerge aria-hidden className="h-4 w-4" />} onClick={() => onAction("merge")}>
            Merge
          </Button>
          <Button tone="ghost" icon={<Scissors aria-hidden className="h-4 w-4" />} onClick={() => onAction("split")}>
            Split
          </Button>
          <Button
            tone="ghost"
            icon={
              isProtected ? (
                <ShieldOff aria-hidden className="h-4 w-4" />
              ) : (
                <ShieldCheck aria-hidden className="h-4 w-4" />
              )
            }
            onClick={() => onAction(protectionAction)}
          >
            {duplicateProtectionActionLabel(cluster)}
          </Button>
        </div>
      </div>
    </article>
  );
}

function optionLabel(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}
