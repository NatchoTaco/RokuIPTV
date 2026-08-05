import { describe, expect, it } from "vitest";

import { redactUrlForDisplay } from "./redaction";

describe("redactUrlForDisplay", () => {
  it("hides URL user info and sensitive query values", () => {
    const redacted = redactUrlForDisplay(
      "http://viewer:secret@example.com/get.php?username=bob&password=hunter2&type=m3u&token=abc",
    );

    expect(redacted).not.toContain("viewer");
    expect(redacted).not.toContain("secret");
    expect(redacted).not.toContain("hunter2");
    expect(redacted).not.toContain("abc");
    expect(redacted).toContain("type=m3u");
  });
});
