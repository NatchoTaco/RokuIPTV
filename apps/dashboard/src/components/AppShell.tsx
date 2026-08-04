import { Activity, Database, HardDrive, LogOut, Tv } from "lucide-react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { signOut, type User } from "../lib/api";
import { Button } from "./Button";

const navigationItems = [
  "Dashboard",
  "Live TV",
  "Channels",
  "Cleanup Center",
  "Guide",
  "Recordings",
  "Sources",
  "Devices",
  "Users and Profiles",
  "Storage",
  "Diagnostics",
  "Settings",
];

export function AppShell({ user, children }: { user: User; children: ReactNode }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const signOutMutation = useMutation({
    mutationFn: signOut,
    onSuccess: async () => {
      await queryClient.invalidateQueries();
      navigate("/sign-in", { replace: true });
    },
  });

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col lg:flex-row">
        <aside className="border-b border-zinc-800 bg-zinc-950/95 px-5 py-4 lg:w-72 lg:border-b-0 lg:border-r">
          <div className="flex items-center justify-between gap-4 lg:block">
            <div>
              <p className="text-sm font-medium uppercase text-forge-300">StreamForge</p>
              <p className="mt-1 text-xs text-zinc-500">{user.email}</p>
            </div>
            <Button
              tone="ghost"
              icon={<LogOut aria-hidden className="h-4 w-4" />}
              onClick={() => signOutMutation.mutate()}
            >
              Sign out
            </Button>
          </div>

          <nav className="mt-6 grid grid-cols-2 gap-2 lg:grid-cols-1">
            {navigationItems.map((item, index) => (
              <button
                key={item}
                className={`flex min-h-10 items-center justify-between rounded-md px-3 text-left text-sm transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forge-300 ${
                  index === 0
                    ? "bg-zinc-800 text-white"
                    : "cursor-not-allowed text-zinc-500"
                }`}
                disabled={index !== 0}
              >
                <span>{item}</span>
                {index !== 0 ? <span className="text-[11px] uppercase">Later</span> : null}
              </button>
            ))}
          </nav>
        </aside>

        <main className="flex-1 px-5 py-6 lg:px-8">
          <div className="mb-8 grid gap-4 md:grid-cols-4">
            <Signal icon={<Activity aria-hidden />} label="API" />
            <Signal icon={<Database aria-hidden />} label="Database" />
            <Signal icon={<HardDrive aria-hidden />} label="Storage" deferred />
            <Signal icon={<Tv aria-hidden />} label="Roku" deferred />
          </div>
          {children}
        </main>
      </div>
    </div>
  );
}

function Signal({ icon, label, deferred = false }: { icon: ReactNode; label: string; deferred?: boolean }) {
  return (
    <div className="flex min-h-20 items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-900 px-4">
      <div className="grid h-10 w-10 place-items-center rounded-md bg-zinc-950 text-forge-300 [&_svg]:h-5 [&_svg]:w-5">
        {icon}
      </div>
      <div>
        <p className="text-sm font-semibold">{label}</p>
        <p className="text-xs text-zinc-500">{deferred ? "Deferred" : "Live"}</p>
      </div>
    </div>
  );
}
