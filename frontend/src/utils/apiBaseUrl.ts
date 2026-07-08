export function getApiBaseUrl() {
  // Explicit env var wins (set NEXT_PUBLIC_API_URL in Vercel / production).
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && envUrl.trim().length > 0) {
    return envUrl.replace(/\/$/, "");
  }
  // Local dev fallback.
  return "http://127.0.0.1:8000";
}
