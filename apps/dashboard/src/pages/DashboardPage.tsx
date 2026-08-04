import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";

import { AppShell } from "../components/AppShell";
import { Button } from "../components/Button";
import { HealthCards } from "../components/HealthCards";
import { getHealth, type User } from "../lib/api";

export function DashboardPage({ user }: { user: User }) {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 30000,
  });

  return (
    <AppShell user={user}>
      <div className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="text-sm font-medium uppercase text-forge-300">Dashboard</p>
          <h1 className="mt-2 text-3xl font-semibold">Server health</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-400">
            Live foundation status from the StreamForge API.
          </p>
        </div>
        <Button
          tone="secondary"
          icon={<RefreshCw aria-hidden className="h-4 w-4" />}
          onClick={() => void healthQuery.refetch()}
        >
          Refresh
        </Button>
      </div>

      {healthQuery.isLoading ? (
        <StatusPanel title="Loading health data" detail="Waiting for the API response." />
      ) : null}

      {healthQuery.isError ? (
        <StatusPanel title="Health unavailable" detail="The API health endpoint did not respond." />
      ) : null}

      {healthQuery.data ? <HealthCards health={healthQuery.data} /> : null}

      <section className="mt-8 rounded-lg border border-zinc-800 bg-zinc-900 p-5">
        <h2 className="text-lg font-semibold">Milestone 1 boundary</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-400">
          Playlist ingestion, cleanup, guide data, Roku pairing, playback, recording, and timeshift
          remain deferred until their planned milestones.
        </p>
      </section>
    </AppShell>
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
