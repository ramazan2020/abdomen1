import "./globals.css";
import type { CSSProperties, ReactNode } from "react";
import Link from "next/link";

export const metadata = {
  title: "Veri Çıkarım Formu — 35 Alan",
  description: "Kapsam belirleme incelemesi veri çıkarım formu (35 alan)",
};

const navLink: CSSProperties = {
  color: "#fff", padding: "11px 16px", display: "inline-block",
  textDecoration: "none", fontSize: 14, fontWeight: 500,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="tr">
      <body>
        <nav style={{ background: "#0f766e", borderBottom: "1px solid #0d9488" }}>
          <div style={{ maxWidth: 1100, margin: "0 auto", padding: "0 20px", display: "flex", gap: 2 }}>
            <Link href="/" style={navLink}>Çalışmalar</Link>
            <Link href="/sema" style={navLink}>Şema</Link>
            <Link href="/grafikler" style={navLink}>Grafikler</Link>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
