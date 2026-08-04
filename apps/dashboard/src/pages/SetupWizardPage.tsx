import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check, LockKeyhole, ServerCog } from "lucide-react";
import { FormEvent, useState, type ReactNode } from "react";

import {
  bootstrapAdmin,
  getCurrentUser,
  signIn,
  updateSetupState,
  type SetupState,
} from "../lib/api";
import { nextSetupStep, setupProgressPercent } from "../lib/setup";
import { Button } from "../components/Button";
import { FormField } from "../components/FormField";

export function SetupWizardPage({ setupState }: { setupState: SetupState }) {
  const step = nextSetupStep(setupState);
  const progress = setupProgressPercent(setupState);

  return (
    <main className="min-h-screen bg-zinc-950 px-5 py-8 text-zinc-100">
      <section className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        <div>
          <p className="text-sm font-medium uppercase text-forge-300">StreamForge</p>
          <h1 className="mt-4 max-w-xl text-4xl font-semibold leading-tight md:text-5xl">
            First-run setup
          </h1>
          <p className="mt-5 max-w-xl text-base leading-7 text-zinc-400">
            Create the local administrator account and choose how this installation will operate.
          </p>
          <div className="mt-8 h-2 overflow-hidden rounded-full bg-zinc-800">
            <div className="h-full bg-forge-500 transition-all" style={{ width: `${progress}%` }} />
          </div>
          <p className="mt-3 text-sm text-zinc-500">{progress}% complete</p>
        </div>

        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-5 shadow-panel md:p-7">
          {step === "account" ? <AdminAccountStep /> : null}
          {step === "installation_mode" ? <InstallationModeStep setupState={setupState} /> : null}
          {step === "dashboard" ? <SetupCompleteStep /> : null}
        </div>
      </section>
    </main>
  );
}

function AdminAccountStep() {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const mutation = useMutation({
    mutationFn: bootstrapAdmin,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["setup-state"] });
      await queryClient.invalidateQueries({ queryKey: ["current-user"] });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate({ email, display_name: displayName, password });
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      <StepHeader
        icon={<LockKeyhole aria-hidden />}
        title="Administrator account"
        detail="This account controls the local dashboard."
      />
      <FormField
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        required
      />
      <FormField
        label="Display name"
        name="displayName"
        value={displayName}
        onChange={(event) => setDisplayName(event.target.value)}
        required
      />
      <FormField
        label="Password"
        name="password"
        type="password"
        autoComplete="new-password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        hint="Use at least 12 characters."
        minLength={12}
        required
      />
      <FormError message={mutation.error instanceof Error ? mutation.error.message : null} />
      <Button type="submit" disabled={mutation.isPending} icon={<ArrowRight aria-hidden className="h-4 w-4" />}>
        Create administrator
      </Button>
    </form>
  );
}

function InstallationModeStep({ setupState }: { setupState: SetupState }) {
  const queryClient = useQueryClient();
  const [installationMode, setInstallationMode] = useState<"local_only" | "remote_access">(
    setupState.installation_mode ?? "local_only",
  );
  const currentUserQuery = useQuery({
    queryKey: ["current-user"],
    queryFn: getCurrentUser,
  });
  const mutation = useMutation({
    mutationFn: updateSetupState,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["setup-state"] });
    },
  });

  if (currentUserQuery.isError) {
    return <SetupSignIn />;
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate({ installation_mode: installationMode });
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      <StepHeader
        icon={<ServerCog aria-hidden />}
        title="Installation mode"
        detail="Choose how this server should be treated during Milestone 1."
      />
      <div className="grid gap-3 md:grid-cols-2">
        <ModeOption
          title="Local only"
          detail="Recommended for the first foundation run."
          active={installationMode === "local_only"}
          onClick={() => setInstallationMode("local_only")}
        />
        <ModeOption
          title="Remote access"
          detail="Stores intent; proxy hardening arrives later."
          active={installationMode === "remote_access"}
          onClick={() => setInstallationMode("remote_access")}
        />
      </div>
      <FormError message={mutation.error instanceof Error ? mutation.error.message : null} />
      <Button type="submit" disabled={mutation.isPending} icon={<Check aria-hidden className="h-4 w-4" />}>
        Finish Milestone 1 setup
      </Button>
    </form>
  );
}

function SetupSignIn() {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const mutation = useMutation({
    mutationFn: signIn,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["current-user"] });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate({ email, password });
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      <StepHeader
        icon={<LockKeyhole aria-hidden />}
        title="Sign in"
        detail="Continue first-run setup with the administrator account."
      />
      <FormField
        label="Email"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        required
      />
      <FormField
        label="Password"
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        required
      />
      <FormError message={mutation.error instanceof Error ? mutation.error.message : null} />
      <Button type="submit" disabled={mutation.isPending}>
        Sign in
      </Button>
    </form>
  );
}

function SetupCompleteStep() {
  return (
    <div className="space-y-5">
      <StepHeader
        icon={<Check aria-hidden />}
        title="Setup complete"
        detail="The dashboard is ready to open."
      />
      <Button type="button" onClick={() => window.location.assign("/")}>
        Open dashboard
      </Button>
    </div>
  );
}

function StepHeader({
  icon,
  title,
  detail,
}: {
  icon: ReactNode;
  title: string;
  detail: string;
}) {
  return (
    <div className="flex items-start gap-4">
      <div className="grid h-11 w-11 place-items-center rounded-md bg-forge-500/10 text-forge-300 [&_svg]:h-5 [&_svg]:w-5">
        {icon}
      </div>
      <div>
        <h2 className="text-xl font-semibold">{title}</h2>
        <p className="mt-1 text-sm leading-6 text-zinc-400">{detail}</p>
      </div>
    </div>
  );
}

function ModeOption({
  title,
  detail,
  active,
  onClick,
}: {
  title: string;
  detail: string;
  active: boolean;
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

function FormError({ message }: { message: string | null }) {
  return message ? (
    <p role="alert" className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
      {message}
    </p>
  ) : null;
}
