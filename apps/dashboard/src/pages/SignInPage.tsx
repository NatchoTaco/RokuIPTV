import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LogIn } from "lucide-react";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "../components/Button";
import { FormField } from "../components/FormField";
import { signIn } from "../lib/api";

export function SignInPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const mutation = useMutation({
    mutationFn: signIn,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["current-user"] });
      navigate("/", { replace: true });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate({ email, password });
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-950 px-5 text-zinc-100">
      <form
        onSubmit={submit}
        className="w-full max-w-md rounded-lg border border-zinc-800 bg-zinc-900 p-6 shadow-panel"
      >
        <p className="text-sm font-medium uppercase text-forge-300">StreamForge</p>
        <h1 className="mt-3 text-2xl font-semibold">Sign in</h1>
        <div className="mt-6 space-y-5">
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
          {mutation.error instanceof Error ? (
            <p role="alert" className="text-sm text-red-200">
              {mutation.error.message}
            </p>
          ) : null}
          <Button type="submit" disabled={mutation.isPending} icon={<LogIn aria-hidden className="h-4 w-4" />}>
            Sign in
          </Button>
        </div>
      </form>
    </main>
  );
}
