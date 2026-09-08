import axios, { AxiosError } from "axios";

/**
 * Every backend route lives under /api. The env var may be given as either
 * "http://localhost:8002" or "http://localhost:8002/api" (or left empty when
 * the backend serves the built frontend itself) - all three resolve the same.
 */
function normaliseBaseUrl(raw: string | undefined): string {
  const trimmed = (raw ?? "").trim().replace(/\/+$/, "");
  const origin = trimmed || (import.meta.env.DEV ? "http://localhost:8002" : "");
  return origin.endsWith("/api") ? origin : `${origin}/api`;
}

export const API_BASE_URL: string = normaliseBaseUrl(import.meta.env.VITE_API_BASE_URL as string | undefined);

export const TOKEN_STORAGE_KEY = "aikyam_access_token";

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token);
    else localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // ignore storage errors (private mode, etc.)
  }
}

export const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// A listener the auth context registers so the interceptor can trigger a
// clean logout + redirect without importing React state directly here.
let onUnauthorized: (() => void) | null = null;
export function registerUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      setStoredToken(null);
      onUnauthorized?.();
    }
    return Promise.reject(error);
  }
);

/**
 * Fetch a protected file with the bearer token attached and hand it to the
 * browser as a download. Files are never served from a public URL, so a plain
 * <a href> cannot be used.
 */
export async function downloadFile(path: string, fallbackName = "download"): Promise<void> {
  const response = await api.get<Blob>(path, { responseType: "blob" });
  const disposition = String(response.headers["content-disposition"] ?? "");
  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  const plain = /filename="?([^";]+)"?/i.exec(disposition);
  const name = utf8 ? decodeURIComponent(utf8[1]) : plain ? plain[1] : fallbackName;
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function apiErrorMessage(error: unknown, fallback = "Something went wrong. Please try again."): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { detail?: unknown; message?: unknown } | undefined;
    if (data) {
      if (typeof data.detail === "string") return data.detail;
      if (Array.isArray(data.detail)) {
        const first = data.detail[0] as { msg?: string } | undefined;
        if (first?.msg) return first.msg;
      }
      if (typeof data.message === "string") return data.message;
    }
    if (error.message === "Network Error") {
      return "Can't reach the server. Is the backend running at " + API_BASE_URL + "?";
    }
  }
  if (error instanceof Error) return error.message;
  return fallback;
}
