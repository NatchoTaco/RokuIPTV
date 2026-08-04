import { describe, expect, it } from "vitest";

import { nextSetupStep, setupProgressPercent } from "./setup";
import type { SetupState } from "./api";

const baseState: SetupState = {
  is_complete: false,
  current_step: "account",
  completed_steps: [],
  installation_mode: null,
  administrator_exists: false,
};

describe("setup helpers", () => {
  it("starts with account creation", () => {
    expect(nextSetupStep(baseState)).toBe("account");
    expect(setupProgressPercent(baseState)).toBe(0);
  });

  it("moves to installation mode after account creation", () => {
    const state = {
      ...baseState,
      current_step: "installation_mode",
      completed_steps: ["account"],
      administrator_exists: true,
    };

    expect(nextSetupStep(state)).toBe("installation_mode");
    expect(setupProgressPercent(state)).toBe(50);
  });

  it("finishes the Milestone 1 wizard after installation mode", () => {
    const state = {
      ...baseState,
      is_complete: true,
      current_step: "dashboard",
      completed_steps: ["account", "installation_mode"],
      installation_mode: "local_only",
      administrator_exists: true,
    } satisfies SetupState;

    expect(nextSetupStep(state)).toBe("dashboard");
    expect(setupProgressPercent(state)).toBe(100);
  });
});
