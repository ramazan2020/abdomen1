"use client";

import { RoleGuard } from "@/components/common/RoleGuard";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { getCurrentRole } from "@/lib/auth";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const role = typeof window !== "undefined" ? getCurrentRole() : null;

  if (role !== "admin") {
    return (
      <RoleGuard>
        <div style={{ display: "flex", minHeight: "100vh", alignItems: "center", justifyContent: "center" }}>
          <div className="card" style={{ maxWidth: 380, textAlign: "center", padding: 40 }}>
            <div style={{ fontSize: 32, marginBottom: 16 }}>🔒</div>
            <h2 style={{ color: "var(--text-1)", marginBottom: 8 }}>Yetkisiz Erişim</h2>
            <p style={{ color: "var(--text-3)", fontSize: 13 }}>Bu alan yalnızca yönetici rolüne açıktır.</p>
          </div>
        </div>
      </RoleGuard>
    );
  }

  return (
    <RoleGuard>
      <div className="app-shell">
        <AppSidebar />
        <main className="app-main">
          <div className="app-content">{children}</div>
        </main>
      </div>
    </RoleGuard>
  );
}
