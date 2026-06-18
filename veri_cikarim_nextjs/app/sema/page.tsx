"use client";
import { useMemo, useState } from "react";
import { FIELDS, CATEGORIES } from "@/lib/fields";
import CategoryChart from "@/components/CategoryChart";

const CAT_COLORS: Record<string, string> = {
  "Bibliyografik": "#0f766e", "Patoloji": "#2563eb", "Görüntüleme & Veri Seti": "#7c3aed",
  "Yöntem & Model": "#db2777", "Doğrulama": "#ea580c", "Performans Ölçütleri": "#16a34a",
  "Açık Bilim & Klinik": "#0891b2",
};

export default function SemaPage() {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("Tümü");
  const [view, setView] = useState<"tablo" | "grafik">("tablo");
  const rows = useMemo(() => {
    const ql = q.toLowerCase();
    return FIELDS.filter(
      (f) => (cat === "Tümü" || f.category === cat) &&
        (q === "" || f.name.toLowerCase().includes(ql) || f.code.toLowerCase().includes(ql) || f.description.toLowerCase().includes(ql))
    );
  }, [q, cat]);
  return (
    <main className="wrap">
      <h1>Veri Çıkarım Formu — 35 Alan (Şema)</h1>
      <p className="sub">Bölüm 2.6 · standart veri çıkarma formunun alan tanımları</p>
      <div className="tabs">
        <button className={`tab ${view === "tablo" ? "active" : ""}`} onClick={() => setView("tablo")}>Tablo</button>
        <button className={`tab ${view === "grafik" ? "active" : ""}`} onClick={() => setView("grafik")}>Grafik</button>
      </div>
      {view === "grafik" ? <CategoryChart /> : (
        <>
          <div className="toolbar">
            <input placeholder="Alan ara…" value={q} onChange={(e) => setQ(e.target.value)} />
            <select value={cat} onChange={(e) => setCat(e.target.value)}>
              <option>Tümü</option>{CATEGORIES.map((c) => (<option key={c}>{c}</option>))}
            </select>
            <span className="count">{rows.length} / 35 alan</span>
          </div>
          <table>
            <thead><tr><th className="idcol">#</th><th>Kod</th><th>Alan</th><th>Kategori</th><th>Açıklama</th><th>Değer / Kod</th></tr></thead>
            <tbody>
              {rows.map((f) => (
                <tr key={f.id}>
                  <td className="idcol">{f.id}</td>
                  <td><span className="code">{f.code}</span></td>
                  <td><strong>{f.name}</strong></td>
                  <td><span className="cat-badge" style={{ background: CAT_COLORS[f.category] }}>{f.category}</span></td>
                  <td>{f.description}</td>
                  <td className="values">{f.values}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </main>
  );
}
