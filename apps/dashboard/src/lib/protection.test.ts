import { describe, expect, it } from "vitest";

import {
  channelProtectionActionLabel,
  clearProtectionsConfirmation,
  duplicateProtectionAction,
  duplicateProtectionActionLabel,
  nextChannelProtectionState,
  visibilityFilterOptions,
} from "./protection";

describe("protection helpers", () => {
  it("reflects channel protection state in row actions", () => {
    expect(channelProtectionActionLabel({ protected_from_auto_merge: false })).toBe("Protect");
    expect(nextChannelProtectionState({ protected_from_auto_merge: false })).toBe(true);

    expect(channelProtectionActionLabel({ protected_from_auto_merge: true })).toBe("Unprotect");
    expect(nextChannelProtectionState({ protected_from_auto_merge: true })).toBe(false);
  });

  it("includes protected as a visibility filter option", () => {
    expect(visibilityFilterOptions).toContain("protected");
  });

  it("reflects duplicate cluster protection state in actions", () => {
    expect(duplicateProtectionActionLabel({ review_status: "pending_review" })).toBe("Protect");
    expect(duplicateProtectionAction({ review_status: "pending_review" })).toBe("protect");

    expect(duplicateProtectionActionLabel({ review_status: "protected" })).toBe("Unprotect");
    expect(duplicateProtectionAction({ review_status: "protected" })).toBe("unprotect");
  });

  it("shows the affected count and preserves visibility in clear-all confirmation text", () => {
    const message = clearProtectionsConfirmation(1200);

    expect(message).toContain("1,200");
    expect(message).toContain("only removes protection overrides");
    expect(message).toContain("preserves Allow/Hide visibility decisions");
  });
});
