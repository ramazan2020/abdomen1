"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { RoleGuard } from "@/components/common/RoleGuard";
import { clearToken, getCurrentRole } from "@/lib/auth";

export default function DoctorLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  function logout() {
    clearToken();
    router.replace("/login");
  }

  return (
    <RoleGuard>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 24px",
          borderBottom: "1px solid #2a2e38",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <Link href="/doctor" style={{ fontWeight: 700, textDecoration: "none" }}>
            Lezyon Tespiti
          </Link>
          {typeof window !== "undefined" && getCurrentRole() === "admin" && (
            <Link href="/admin/models" style={{ fontSize: 13, color: "#93c5fd", textDecoration: "none" }}>
              Model Registry
            </Link>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 13, color: "#9aa0ab" }}>
            {typeof window !== "undefined" ? getCurrentRole() : ""}
          </span>
          <button className="btn-secondary" onClick={logout}>
            Çıkış
          </button>
        </div>
      </header>
      <main style={{ padding: 24 }}>{children}</main>
    </RoleGuard>
  );
}
