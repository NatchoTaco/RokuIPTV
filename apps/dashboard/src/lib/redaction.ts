const sensitiveQueryKeys = [
  "access_token",
  "api_key",
  "apikey",
  "auth",
  "credential",
  "key",
  "login",
  "pass",
  "password",
  "secret",
  "session",
  "sig",
  "signature",
  "token",
  "user",
  "username",
];

export function redactUrlForDisplay(rawUrl: string): string {
  try {
    const url = new URL(rawUrl);
    if (url.username || url.password) {
      url.username = "********";
      url.password = "";
    }
    url.searchParams.forEach((_value, key) => {
      const normalized = key.toLowerCase().replaceAll("-", "_");
      const compact = normalized.replaceAll("_", "");
      if (
        sensitiveQueryKeys.some(
          (sensitiveKey) => normalized.includes(sensitiveKey) || compact.includes(sensitiveKey),
        )
      ) {
        url.searchParams.set(key, "********");
      }
    });
    return url.toString();
  } catch {
    return "Credentials hidden";
  }
}
