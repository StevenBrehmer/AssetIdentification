export function getApiBase(): string {
  const host = window.location.hostname;

  // Tunnel / public
  if (host === "assets.brehfamily.com") {
    return "https://api-assets.brehfamily.com";
  }

  // Local dev (you can add more cases)
  if (host === "localhost" || host === "127.0.0.1") {
    return "http://localhost:8000";
  }

  // If you're accessing the web UI via LAN IP, reuse that same host for API
  // (works if api is on same box and reachable on 8000)
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(host)) {
    return `http://${host}:8000`;
  }

  // Fallback to your known LAN API
  return "http://192.168.1.114:8000";
}
