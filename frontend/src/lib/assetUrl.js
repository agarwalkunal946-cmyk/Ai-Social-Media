const apiBaseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
const backendBaseURL = apiBaseURL.replace(/\/api\/?$/, "");

export function resolveAssetUrl(path) {
  if (!path) {
    return "";
  }

  if (/^https?:\/\//i.test(path)) {
    return path;
  }

  return `${backendBaseURL}${path.startsWith("/") ? path : `/${path}`}`;
}
