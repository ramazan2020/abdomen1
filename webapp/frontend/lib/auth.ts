"use client";

const TOKEN_KEY = "lezyon_webapp_token";

export function saveToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export interface JwtPayload {
  sub: string;
  role: "admin" | "doctor";
  exp: number;
}

/** Sadece UI rolüne göre gösterim/gizleme için — gerçek yetkilendirme her zaman backend'de. */
export function decodeToken(token: string): JwtPayload | null {
  try {
    const payload = token.split(".")[1];
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json) as JwtPayload;
  } catch {
    return null;
  }
}

export function getCurrentRole(): "admin" | "doctor" | null {
  const token = getToken();
  if (!token) return null;
  return decodeToken(token)?.role ?? null;
}
