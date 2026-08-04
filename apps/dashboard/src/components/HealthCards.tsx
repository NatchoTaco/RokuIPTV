import { CheckCircle2, Server, ShieldAlert, Wifi } from "lucide-react";
import type { ReactNode } from "react";

import type { HealthResponse } from "../lib/api";

export function HealthCards({ health }: { health: HealthResponse }) {
  const checks = Object.entries(health.checks);
  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <HealthCard
        title="Service"
        value={health.status}
        detail={`${health.service} ${health.version}`}
        icon={<Server aria-hidden />}
      />
      <HealthCard
        title="Setup"
        value={health.setup_complete ? "Complete" : "First run"}
        detail={health.environment}
        icon={<ShieldAlert aria-hidden />}
      />
      {checks.map(([name, check]) => (
        <HealthCard
          key={name}
          title={titleCase(name)}
          value={check.status}
          detail={check.detail}
          icon={check.status === "ok" ? <CheckCircle2 aria-hidden /> : <Wifi aria-hidden />}
        />
      ))}
    </section>
  );
}

function HealthCard({
  title,
  value,
  detail,
  icon,
}: {
  title: string;
  value: string;
  detail: string;
  icon: ReactNode;
}) {
  const isOk = ["ok", "complete"].includes(value.toLowerCase());
  return (
    <article className="min-h-36 rounded-lg border border-zinc-800 bg-zinc-900 p-5 shadow-panel">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-medium text-zinc-400">{title}</h2>
          <p className="mt-3 text-2xl font-semibold capitalize">{value.replace("_", " ")}</p>
        </div>
        <div
          className={`grid h-10 w-10 place-items-center rounded-md ${
            isOk ? "bg-emerald-500/10 text-emerald-300" : "bg-amber-500/10 text-amber-300"
          } [&_svg]:h-5 [&_svg]:w-5`}
        >
          {icon}
        </div>
      </div>
      <p className="mt-4 text-sm leading-6 text-zinc-500">{detail}</p>
    </article>
  );
}

function titleCase(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
