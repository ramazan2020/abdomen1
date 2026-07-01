"use client";

import { RoleGuard } from "@/components/common/RoleGuard";
import { AppSidebar } from "@/components/layout/AppSidebar";

export default function DoctorLayout({ children }: { children: React.ReactNode }) {
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
