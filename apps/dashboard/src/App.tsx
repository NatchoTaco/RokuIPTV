import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { getCurrentUser, getSetupState } from "./lib/api";
import { DashboardPage } from "./pages/DashboardPage";
import { SignInPage } from "./pages/SignInPage";
import { SetupWizardPage } from "./pages/SetupWizardPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

function AppRoutes() {
  const setupQuery = useQuery({
    queryKey: ["setup-state"],
    queryFn: getSetupState,
  });

  if (setupQuery.isLoading) {
    return <FullScreenStatus title="Starting StreamForge" detail="Checking setup state." />;
  }

  if (setupQuery.isError || !setupQuery.data) {
    return (
      <FullScreenStatus
        title="Backend Unavailable"
        detail="The dashboard could not reach the StreamForge API."
      />
    );
  }

  if (!setupQuery.data.is_complete) {
    return <SetupWizardPage setupState={setupQuery.data} />;
  }

  return (
    <Routes>
      <Route path="/sign-in" element={<SignInPage />} />
      <Route path="/" element={<ProtectedDashboard />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function ProtectedDashboard() {
  const userQuery = useQuery({
    queryKey: ["current-user"],
    queryFn: getCurrentUser,
  });

  if (userQuery.isLoading) {
    return <FullScreenStatus title="Opening Dashboard" detail="Checking your session." />;
  }

  if (userQuery.isError || !userQuery.data) {
    return <Navigate to="/sign-in" replace />;
  }

  return <DashboardPage user={userQuery.data} />;
}

function FullScreenStatus({ title, detail }: { title: string; detail: string }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-950 px-6 text-zinc-100">
      <section className="w-full max-w-md rounded-lg border border-zinc-800 bg-zinc-900 p-6 shadow-panel">
        <p className="text-sm font-medium uppercase text-forge-300">StreamForge</p>
        <h1 className="mt-3 text-2xl font-semibold">{title}</h1>
        <p className="mt-2 text-sm leading-6 text-zinc-400">{detail}</p>
      </section>
    </main>
  );
}
