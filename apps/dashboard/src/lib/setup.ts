import type { SetupState } from "./api";

export type SetupStep = "account" | "installation_mode" | "dashboard";

export function nextSetupStep(setupState: SetupState): SetupStep {
  if (!setupState.administrator_exists || !setupState.completed_steps.includes("account")) {
    return "account";
  }
  if (!setupState.installation_mode) {
    return "installation_mode";
  }
  return "dashboard";
}

export function setupProgressPercent(setupState: SetupState): number {
  const completedCount = new Set(setupState.completed_steps).size;
  return Math.min(100, Math.round((completedCount / 2) * 100));
}
