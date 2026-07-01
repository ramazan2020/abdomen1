import { getToken } from "./auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

async function requestRaw(path: string): Promise<string> {
  const token = getToken();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API_BASE_URL}${path}`, { headers });
  if (!res.ok) {
    throw new ApiError(res.status, res.statusText);
  }
  return res.text();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  getRaw: (path: string) => requestRaw(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  postForm: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form }),
};

export async function loginRequest(email: string, password: string): Promise<{ access_token: string }> {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
  if (!res.ok) {
    throw new ApiError(res.status, "E-posta veya şifre hatalı");
  }
  return res.json();
}

/**
 * PNG endpoint'i JWT bearer auth gerektirir (Bölüm 3: her okuma RBAC'tan geçer).
 * Düz bir <img src> bunu karşılayamaz (header gönderemez), bu yüzden token'ı
 * URL'e koymak yerine (loglarda/tarayıcı geçmişinde iz bırakır) blob olarak
 * fetch edip object URL'e çeviriyoruz — çağıran taraf işi bitince
 * URL.revokeObjectURL ile temizlemeli.
 */
export async function fetchSlicePngBlobUrl(caseId: string, imageId: number): Promise<string> {
  const token = getToken();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API_BASE_URL}/cases/${caseId}/slices/${imageId}/png`, { headers });
  if (!res.ok) throw new ApiError(res.status, "Dilim görüntüsü alınamadı");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}
