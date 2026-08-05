import { describe, expect, it } from "vitest";

import { sourceStatusLabel, sourceTypeLabel } from "./sourceStatus";

describe("source status helpers", () => {
  it("formats all Milestone 2 source statuses", () => {
    expect(sourceStatusLabel("healthy")).toBe("Healthy");
    expect(sourceStatusLabel("importing")).toBe("Importing");
    expect(sourceStatusLabel("warning")).toBe("Warning");
    expect(sourceStatusLabel("offline")).toBe("Offline");
    expect(sourceStatusLabel("failed")).toBe("Failed");
  });

  it("formats source types without exposing raw URLs", () => {
    expect(sourceTypeLabel("m3u_url")).toBe("Remote M3U URL");
    expect(sourceTypeLabel("m3u_upload")).toBe("Uploaded M3U file");
    expect(sourceTypeLabel("demo_playlist")).toBe("Synthetic demo");
  });
});
