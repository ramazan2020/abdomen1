"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { loginRequest, ApiError } from "@/lib/api-client";
import { saveToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { access_token } = await loginRequest(email, password);
      saveToken(access_token);
      router.replace("/doctor");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Giriş başarısız");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh", alignItems: "center", justifyContent: "center" }}>
      <form onSubmit={handleSubmit} className="card" style={{ width: 360 }}>
        <h1 style={{ fontSize: 20, marginBottom: 4 }}>Lezyon Tespiti Web Uygulaması</h1>
        <p style={{ color: "#9aa0ab", fontSize: 13, marginBottom: 20 }}>
          Doktor / yönetici girişi
        </p>

        <label style={{ display: "block", marginBottom: 12 }}>
          <span style={{ display: "block", fontSize: 13, marginBottom: 4 }}>E-posta</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid #3a3e48", background: "#0f1115", color: "#e6e6e6" }}
          />
        </label>

        <label style={{ display: "block", marginBottom: 20 }}>
          <span style={{ display: "block", fontSize: 13, marginBottom: 4 }}>Şifre</span>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid #3a3e48", background: "#0f1115", color: "#e6e6e6" }}
          />
        </label>

        {error && <p style={{ color: "#f87171", fontSize: 13, marginBottom: 12 }}>{error}</p>}

        <button type="submit" className="btn-primary" disabled={loading} style={{ width: "100%" }}>
          {loading ? "Giriş yapılıyor..." : "Giriş yap"}
        </button>
      </form>
    </div>
  );
}
