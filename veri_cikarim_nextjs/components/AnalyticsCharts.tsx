"use client";
import { useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, LabelList, CartesianGrid, Legend,
} from "recharts";
import type { Study } from "@/lib/db";

const PCOLORS: Record<string, string> = {
  URO: "#0f766e", "AAA/AORT": "#2563eb", PAN: "#7c3aed", APP: "#db2777",
  CHO: "#ea580c", DIV: "#16a34a", MIX: "#0891b2", "APP+DIV": "#9333ea", OTHER: "#64748b",
};

const PALETTE = [
  "#0f766e","#2563eb","#7c3aed","#db2777","#ea580c",
  "#16a34a","#0891b2","#9333ea","#64748b","#d97706",
];

function isVar(v: string | null): boolean {
  if (!v) return false;
  return ["var", "yes", "evet", "true", "1"].includes(v.trim().toLowerCase());
}

function countByField(values: (string | null)[], sep?: RegExp): { name: string; count: number }[] {
  const m: Record<string, number> = {};
  values.forEach((v) => {
    if (!v?.trim() || v.toLowerCase().includes("belirtilmem")) return;
    const parts = sep ? v.split(sep).map((p) => p.trim()).filter(Boolean) : [v.trim()];
    parts.forEach((p) => { if (p) m[p] = (m[p] || 0) + 1; });
  });
  return Object.entries(m)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card">
      <h3 style={{ margin: "0 0 16px", fontSize: 15, color: "#0f172a" }}>{title}</h3>
      {children}
    </div>
  );
}

export default function AnalyticsCharts({ rows }: { rows: Study[] }) {
  const n = rows.length;

  const yearData = useMemo(() => {
    const m: Record<number, number> = {};
    rows.forEach((r) => { if (r.year) m[r.year] = (m[r.year] || 0) + 1; });
    return [2021, 2022, 2023, 2024, 2025, 2026].map((y) => ({
      year: String(y),
      count: m[y] || 0,
    }));
  }, [rows]);

  const pathData = useMemo(() => {
    const m: Record<string, number> = {};
    rows.forEach((r) => {
      const k = r.pathology_code || "DİĞER";
      m[k] = (m[k] || 0) + 1;
    });
    return Object.entries(m)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);
  }, [rows]);

  const taskData = useMemo(() => countByField(rows.map((r) => r.task), /[,/;|]+/), [rows]);

  const modelData = useMemo(() => countByField(rows.map((r) => r.model), /[,/;|]+/), [rows]);

  const openSciData = useMemo(() => {
    const indicators = [
      { name: "Açık Kod",             vals: rows.map((r) => r.open_code) },
      { name: "Açık Veri",            vals: rows.map((r) => r.open_data) },
      { name: "Rad. Karşılaştırması", vals: rows.map((r) => r.radiologist_comparison) },
      { name: "Harici Doğrulama",     vals: rows.map((r) => r.ext_validation) },
    ];
    return indicators.map(({ name, vals }) => {
      const varCount = vals.filter(isVar).length;
      return {
        name,
        var: varCount,
        yok: n - varCount,
        pct: n > 0 ? +(varCount / n * 100).toFixed(1) : 0,
      };
    });
  }, [rows, n]);

  const extValByPath = useMemo(() => {
    const m: Record<string, { total: number; extv: number }> = {};
    rows.forEach((r) => {
      const k = r.pathology_code || "DİĞER";
      if (!m[k]) m[k] = { total: 0, extv: 0 };
      m[k].total++;
      if (isVar(r.ext_validation)) m[k].extv++;
    });
    return Object.entries(m)
      .map(([path, { total, extv }]) => ({
        path, total, extv,
        hayir: total - extv,
        pct: total > 0 ? Math.round(extv / total * 100) : 0,
      }))
      .sort((a, b) => b.total - a.total);
  }, [rows]);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(440px, 1fr))", gap: 20 }}>

      {/* 1 — Yıllara göre yayın dağılımı */}
      <Card title={`1 · Yıllara Göre Yayın Dağılımı  (n=${n})`}>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={yearData} margin={{ top: 16, right: 24, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="year" tick={{ fontSize: 12 }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
            <Tooltip formatter={(v) => [`${v} çalışma`, "Yayın"]} />
            <Bar dataKey="count" fill="#0f766e" radius={[6, 6, 0, 0]}>
              <LabelList dataKey="count" position="top" style={{ fontSize: 11 }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* 2 — Patolojiye göre kanıt dağılımı */}
      <Card title={`2 · Patolojiye Göre Kanıt Dağılımı  (n=${n})`}>
        <ResponsiveContainer width="100%" height={Math.max(220, pathData.length * 40)}>
          <BarChart data={pathData} layout="vertical" margin={{ top: 0, right: 44, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
            <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 12 }} />
            <Tooltip formatter={(v) => [`${v} çalışma`, "Çalışma Sayısı"]} />
            <Bar dataKey="count" radius={[0, 6, 6, 0]}>
              <LabelList dataKey="count" position="right" style={{ fontSize: 11 }} />
              {pathData.map((d, i) => (
                <Cell key={i} fill={PCOLORS[d.name] || PALETTE[i % PALETTE.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* 3 — Görev türlerine göre dağılım */}
      <Card title="3 · Görev Türlerine Göre Çalışma Dağılımı">
        <ResponsiveContainer width="100%" height={Math.max(220, taskData.length * 42)}>
          <BarChart data={taskData} layout="vertical" margin={{ top: 0, right: 44, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
            <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 12 }} />
            <Tooltip formatter={(v) => [`${v} çalışma`, "Çalışma Sayısı"]} />
            <Bar dataKey="count" radius={[0, 6, 6, 0]}>
              <LabelList dataKey="count" position="right" style={{ fontSize: 11 }} />
              {taskData.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* 4 — Model ailesi dağılımı */}
      <Card title="4 · Model Ailelerinin Dağılımı">
        <ResponsiveContainer width="100%" height={Math.max(220, modelData.length * 42)}>
          <BarChart data={modelData} layout="vertical" margin={{ top: 0, right: 44, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
            <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 12 }} />
            <Tooltip formatter={(v) => [`${v} çalışma`, "Çalışma Sayısı"]} />
            <Bar dataKey="count" radius={[0, 6, 6, 0]}>
              <LabelList dataKey="count" position="right" style={{ fontSize: 11 }} />
              {modelData.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* 5 — Açık bilim ve kanıt kalitesi göstergeleri (full width) */}
      <div style={{ gridColumn: "1 / -1" }}>
        <Card title={`5 · Açık Bilim ve Kanıt Kalitesi Göstergeleri  (n=${n})`}>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={openSciData}
              layout="vertical"
              margin={{ top: 0, right: 70, left: 10, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} domain={[0, n]} />
              <YAxis type="category" dataKey="name" width={165} tick={{ fontSize: 13 }} />
              <Tooltip
                formatter={(v, name) => [`${v} çalışma`, name === "var" ? "Var" : "Yok"]}
              />
              <Legend formatter={(v) => v === "var" ? "✓ Var" : "✗ Yok"} />
              <Bar dataKey="var" name="var" stackId="a" fill="#0f766e">
                <LabelList
                  dataKey="var"
                  position="insideLeft"
                  style={{ fontSize: 12, fill: "#fff", fontWeight: 600 }}
                  formatter={(v: unknown) => Number(v) > 0 ? String(v) : ""}
                />
              </Bar>
              <Bar dataKey="yok" name="yok" stackId="a" fill="#e2e8f0" radius={[0, 6, 6, 0]}>
                <LabelList
                  dataKey="pct"
                  position="right"
                  style={{ fontSize: 12, fill: "#475569" }}
                  formatter={(v: unknown) => `${v}% var`}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* 6 — Patoloji bazında harici doğrulama (full width) */}
      <div style={{ gridColumn: "1 / -1" }}>
        <Card title="6 · Patoloji Bazında Harici Doğrulama — Sayı ve Yüzde">
          <ResponsiveContainer width="100%" height={Math.max(260, extValByPath.length * 46)}>
            <BarChart
              data={extValByPath}
              layout="vertical"
              margin={{ top: 0, right: 100, left: 0, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
              <YAxis type="category" dataKey="path" width={80} tick={{ fontSize: 12 }} />
              <Tooltip
                formatter={(v, name) => [
                  `${v} çalışma`,
                  name === "extv" ? "Harici Doğrulama Var" : "Harici Doğrulama Yok",
                ]}
              />
              <Legend
                formatter={(v) =>
                  v === "extv" ? "✓ Harici Doğrulama Var" : "✗ Harici Doğrulama Yok"
                }
              />
              <Bar dataKey="extv" name="extv" stackId="a" fill="#0f766e">
                <LabelList
                  dataKey="extv"
                  position="insideLeft"
                  style={{ fontSize: 12, fill: "#fff", fontWeight: 600 }}
                  formatter={(v: unknown) => Number(v) > 0 ? String(v) : ""}
                />
              </Bar>
              <Bar dataKey="hayir" name="hayir" stackId="a" fill="#e2e8f0" radius={[0, 6, 6, 0]}>
                <LabelList
                  dataKey="pct"
                  position="right"
                  style={{ fontSize: 12, fill: "#475569" }}
                  formatter={(v: unknown) => `${v}% doğr.`}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          {/* Tablo özeti */}
          <div style={{ marginTop: 20, overflowX: "auto" }}>
            <table style={{ fontSize: 13 }}>
              <thead>
                <tr>
                  <th>Patoloji</th>
                  <th style={{ textAlign: "right" }}>Toplam</th>
                  <th style={{ textAlign: "right" }}>Harici Doğrulama Var</th>
                  <th style={{ textAlign: "right" }}>Harici Doğrulama Yok</th>
                  <th style={{ textAlign: "right" }}>Doğrulama Oranı</th>
                </tr>
              </thead>
              <tbody>
                {extValByPath.map((d) => (
                  <tr key={d.path}>
                    <td>
                      <span
                        className="cat-badge"
                        style={{ background: PCOLORS[d.path] || "#64748b" }}
                      >
                        {d.path}
                      </span>
                    </td>
                    <td style={{ textAlign: "right" }}>{d.total}</td>
                    <td style={{ textAlign: "right", color: "#0f766e", fontWeight: 600 }}>
                      {d.extv}
                    </td>
                    <td style={{ textAlign: "right", color: "#94a3b8" }}>{d.hayir}</td>
                    <td style={{ textAlign: "right", fontWeight: 600 }}>
                      {d.pct}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
