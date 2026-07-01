"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken, getCurrentRole } from "@/lib/auth";

/* ── Inline SVG icon helpers ─────────────────────────────────────────── */
function Icon({ path, size = 16 }: { path: string; size?: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="sidebar-nav-icon"
      aria-hidden="true"
    >
      <path d={path} />
    </svg>
  );
}

/* Feather-compatible path strings */
const ICONS = {
  list:     "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  cpu:      "M18 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zM9 9h6M9 15h6",
  layers:   "M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5",
  database: "M12 2C6.477 2 2 4.477 2 7s4.477 5 10 5 10-2.477 10-5-4.477-5-10-5zM2 17c0 2.523 4.477 5 10 5s10-2.477 10-5M2 12c0 2.523 4.477 5 10 5s10-2.477 10-5",
  activity: "M22 12h-4l-3 9L9 3l-3 9H2",
  settings: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z",
  logout:   "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9",
  chevronLeft:  "M15 18l-6-6 6-6",
  chevronRight: "M9 18l6-6-6-6",
  eye: "M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
  zap: "M13 2L3 14h9l-1 8 10-12h-9l1-8z",
};

interface NavItem {
  href: string;
  label: string;
  icon: keyof typeof ICONS;
}

const DOCTOR_NAV: NavItem[] = [
  { href: "/doctor",        label: "Vaka Listesi",     icon: "list" },
];

const ADMIN_NAV: NavItem[] = [
  { href: "/admin/models",  label: "Model Registry",   icon: "cpu" },
];

export function AppSidebar() {
  const pathname = usePathname();
  const router   = useRouter();
  const role = typeof window !== "undefined" ? getCurrentRole() : null;
  const [collapsed, setCollapsed] = useState(false);

  function logout() {
    clearToken();
    router.replace("/login");
  }

  function isActive(href: string) {
    if (href === "/doctor") return pathname === "/doctor";
    return pathname.startsWith(href);
  }

  const initials = role === "admin" ? "AD" : "DR";

  return (
    <>
      {/* Sidebar panel */}
      <aside className={`app-sidebar${collapsed ? " collapsed" : ""}`}>
        {/* Brand */}
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">🔬</div>
          {!collapsed && (
            <div className="sidebar-brand-text">
              <div className="sidebar-brand-title">AbdomenDetect</div>
              <div className="sidebar-brand-sub">Research Platform</div>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          {/* Core (all roles) */}
          <div className="sidebar-nav-group">
            {!collapsed && <div className="sidebar-nav-label">Genel</div>}
            {DOCTOR_NAV.map(item => (
              <Link
                key={item.href}
                href={item.href}
                className={`sidebar-nav-item${isActive(item.href) ? " active" : ""}`}
                title={collapsed ? item.label : undefined}
              >
                <Icon path={ICONS[item.icon]} />
                {!collapsed && item.label}
              </Link>
            ))}
          </div>

          {/* Admin only */}
          {role === "admin" && (
            <div className="sidebar-nav-group">
              {!collapsed && <div className="sidebar-nav-label">Yönetim</div>}
              {ADMIN_NAV.map(item => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`sidebar-nav-item${isActive(item.href) ? " active" : ""}`}
                  title={collapsed ? item.label : undefined}
                >
                  <Icon path={ICONS[item.icon]} />
                  {!collapsed && item.label}
                </Link>
              ))}
            </div>
          )}
        </nav>

        {/* User footer */}
        <div className="sidebar-footer">
          <div className="sidebar-user">
            <div className="sidebar-avatar">{initials}</div>
            {!collapsed && (
              <div className="sidebar-user-info">
                <div className="sidebar-user-role">{role}</div>
                <div className="sidebar-user-email">&mdash;</div>
              </div>
            )}
            <button
              className="sidebar-logout"
              onClick={logout}
              title="Çıkış yap"
            >
              <Icon path={ICONS.logout} size={14} />
            </button>
          </div>
        </div>

        {/* Collapse toggle */}
        <button
          className="sidebar-toggle"
          onClick={() => setCollapsed(c => !c)}
          title={collapsed ? "Genişlet" : "Daralt"}
        >
          <Icon path={collapsed ? ICONS.chevronRight : ICONS.chevronLeft} size={14} />
        </button>
      </aside>

      {/* Spacer that pushes main content — synced via CSS class on app-main */}
      <style>{`
        .app-main { margin-left: ${collapsed ? "60px" : "var(--sidebar-w)"}; }
      `}</style>
    </>
  );
}
