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
      setError(err instanceof ApiError ? err.message : "E-posta veya şifre hatalı");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      display: "flex",
      minHeight: "100vh",
      background: "var(--bg-base)",
    }}>
      {/* Left panel — branding */}
      <div style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "60px 64px",
        background: "linear-gradient(135deg, #08111e 0%, #0d1f38 60%, #102744 100%)",
        borderRight: "1px solid var(--border-1)",
      }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 40 }}>
          <div style={{
            width: 52,
            height: 52,
            borderRadius: "var(--r-lg)",
            background: "var(--accent-muted)",
            border: "1px solid var(--accent-border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 26,
          }}>🔬</div>
          <div>
            <div style={{ fontSize: 22, fontWeight: 800, color: "var(--text-1)", letterSpacing: "-0.4px" }}>
              AbdomenDetect
            </div>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.8px", color: "var(--text-3)", marginTop: 2 }}>
              Research Platform
            </div>
          </div>
        </div>

        <h1 style={{
          fontSize: 32,
          fontWeight: 800,
          color: "var(--text-1)",
          letterSpacing: "-0.5px",
          lineHeight: 1.25,
          marginBottom: 16,
          maxWidth: 380,
        }}>
          İnsan-Döngülü<br />Lezyon Tespiti
        </h1>

        <p style={{ fontSize: 14, color: "var(--text-3)", lineHeight: 1.7, maxWidth: 360, marginBottom: 40 }}>
          Karın BT serisi yükleyin, YOLO/RF-DETR modellerini inference edin,
          annotasyonları düzeltin ve model yeniden eğitim döngüsünü yönetin.
        </p>

        {/* Feature tags */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {["KVKK Uyumlu", "DICOM İşleme", "Multi-Model", "Human-in-the-Loop"].map(tag => (
            <span key={tag} className="tag">{tag}</span>
          ))}
        </div>

        {/* Citation info */}
        <div style={{
          marginTop: "auto",
          paddingTop: 32,
          borderTop: "1px solid var(--border-1)",
        }}>
          <p style={{ fontSize: 11, color: "var(--text-3)", lineHeight: 1.6 }}>
            Akut karın patolojisi araştırma projesi · 6 sınıf lezyon tespiti<br />
            Akut kolesistit · Böbrek/üreter taşı · Akut pankreatit<br />
            Aort anevrizma/diseksiyon · Akut apandisit · Akut divertikülit
          </p>
        </div>
      </div>

      {/* Right panel — login form */}
      <div style={{
        width: 440,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "60px 48px",
        flexShrink: 0,
      }}>
        <div style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 22, fontWeight: 800, color: "var(--text-1)", marginBottom: 6 }}>
            Giriş Yap
          </h2>
          <p style={{ fontSize: 13, color: "var(--text-3)" }}>
            Doktor veya yönetici hesabınızla devam edin
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div className="form-group">
            <label className="form-label" htmlFor="email">E-posta adresi</label>
            <input
              id="email"
              type="email"
              required
              value={email}
              autoComplete="email"
              onChange={(e) => setEmail(e.target.value)}
              className="form-input"
              placeholder="doktor@kurum.edu.tr"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">Şifre</label>
            <input
              id="password"
              type="password"
              required
              value={password}
              autoComplete="current-password"
              onChange={(e) => setPassword(e.target.value)}
              className="form-input"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div className="alert alert-danger" role="alert">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary btn-block btn-lg"
            disabled={loading}
            style={{ marginTop: 4 }}
          >
            {loading ? (
              <>
                <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                Giriş yapılıyor…
              </>
            ) : (
              "Giriş Yap"
            )}
          </button>
        </form>

        <p style={{ marginTop: 32, fontSize: 11.5, color: "var(--text-3)", textAlign: "center", lineHeight: 1.6 }}>
          Bu sisteme erişim yetkisi olmayan kişilerin girişi yasaktır.<br />
          Hesap talebi için sistem yöneticinize başvurun.
        </p>
      </div>
    </div>
  );
}
