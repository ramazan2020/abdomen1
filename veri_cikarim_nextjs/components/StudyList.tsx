"use client";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { Study } from "@/lib/db";
import { FIELDS, CATEGORIES } from "@/lib/fields";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LabelList } from "recharts";
import StudyForm from "./StudyForm";

const PCOLORS: Record<string, string> = {
  URO: "#0f766e", "AAA/AORT": "#2563eb", PAN: "#7c3aed", APP: "#db2777",
  CHO: "#ea580c", DIV: "#16a34a", MIX: "#0891b2", "APP+DIV": "#9333ea", OTHER: "#64748b",
};

function parsePerf(p: string | null): Record<string, string> {
  if (!p) return {};
  try {
    const o = JSON.parse(p);
    if (o && typeof o === "object") {
      const out: Record<string, string> = {};
      for (const k of Object.keys(o)) {
        let v = String(o[k]);
        if (["ACC", "SEN", "SPE", "F1"].includes(k) && /^\d{2,3}(\.\d+)?$/.test(v)) v = v + "%";
        out[k] = v;
      }
      return out;
    }
  } catch {}
  return {};
}

function valueFor(code: string, s: Study, perf: Record<string, string>): string | null {
  switch (code) {
    case "AUTH": return s.authors_full || s.first_author;
    case "YEAR": return s.year ? String(s.year) : null;
    case "TITLE": return s.title;
    case "VENUE": return s.venue;
    case "CNTRY": return s.country;
    case "DSET": return s.dataset_name;
    case "NPAT": return s.patient_count != null ? String(s.patient_count) : null;
    case "NIMG": return s.image_count != null ? String(s.image_count) : null;
    case "LIMIT": return s.limitations;
    case "PATH": return s.pathology ? `${s.pathology} (${s.pathology_code})` : null;
    case "MOD": return s.modality;
    case "TASK": return s.task;
    case "MFAM": return s.model;
    case "ARCH": return s.method_detail;
    case "DACC": return s.dataset_access;
    case "EXTV": return s.ext_validation;
    case "RADC": return s.radiologist_comparison;
    case "CODE": return s.open_code;
    case "DATA": return s.open_data;
    case "FIND": return s.summary;
    case "AUC": case "ACC": case "SEN": case "SPE":
    case "F1": case "DICE": case "IOU": case "MAP": return perf[code] || null;
    default: return null;
  }
}

function DetailModal({
  study,
  onClose,
  onEdit,
  onDelete,
}: {
  study: Study;
  onClose: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const perf = parsePerf(study.performance);
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <h2>[{study.ref_no}] {study.title}</h2>
            <div className="meta">
              {study.authors_full || study.first_author} · {study.year} · {study.venue || "—"} · {study.pathology}
              {study.depth ? ` · ${study.depth}` : ""}
              {study.doi_url ? <> · <a href={study.doi_url} target="_blank" rel="noreferrer">DOI</a></> : null}
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
            <button className="btn-detay" onClick={onEdit}>Düzenle</button>
            <button className="btn-danger" onClick={onDelete}>Sil</button>
            <button className="modal-close" onClick={onClose}>×</button>
          </div>
        </div>
        <div className="modal-body">
          {CATEGORIES.map((cat) => (
            <div className="cat-group" key={cat}>
              <h4 style={{ color: "#0f766e" }}>{cat}</h4>
              {FIELDS.filter((f) => f.category === cat).map((f) => {
                const v = valueFor(f.code, study, perf);
                const has = v !== undefined && v !== null && String(v).trim() !== "" && v !== "Belirtilmemiş";
                return (
                  <div className="field-row" key={f.code}>
                    <span className="fcode">{f.code}</span>
                    <span className="fname">{f.name}</span>
                    <span className={`fval ${has ? "" : "empty"}`}>
                      {has ? String(v) : "— (kodlanmadı)"}
                    </span>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function StudyList({ rows }: { rows: Study[] }) {
  const router = useRouter();
  const [items, setItems] = useState<Study[]>(rows);
  const [q, setQ] = useState("");
  const [pc, setPc] = useState("Tümü");
  const [view, setView] = useState<"liste" | "grafik">("liste");
  const [sel, setSel] = useState<Study | null>(null);
  const [formTarget, setFormTarget] = useState<Study | "new" | null>(null);

  function handleSaved(saved: Study) {
    setItems((prev) => {
      const idx = prev.findIndex((s) => s.id === saved.id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = saved;
        return next;
      }
      return [...prev, saved].sort((a, b) => a.ref_no - b.ref_no);
    });
    setFormTarget(null);
    setSel(saved);
    router.refresh();
  }

  async function handleDelete(study: Study) {
    if (!window.confirm(`[${study.ref_no}] "${study.title}" silinecek. Emin misiniz?`)) return;
    const res = await fetch(`/api/studies/${study.id}`, { method: "DELETE" });
    if (res.ok) {
      setItems((prev) => prev.filter((s) => s.id !== study.id));
      setSel(null);
      router.refresh();
    } else {
      alert("Silme başarısız.");
    }
  }

  const codes = useMemo(
    () => Array.from(new Set(items.map((r) => r.pathology_code).filter(Boolean))) as string[],
    [items]
  );

  const filtered = useMemo(() => {
    const ql = q.toLowerCase();
    return items.filter(
      (r) =>
        (pc === "Tümü" || r.pathology_code === pc) &&
        (q === "" ||
          (r.title || "").toLowerCase().includes(ql) ||
          (r.authors_full || r.first_author || "").toLowerCase().includes(ql) ||
          (r.model || "").toLowerCase().includes(ql) ||
          (r.task || "").toLowerCase().includes(ql))
    );
  }, [items, q, pc]);

  const dist = useMemo(() => {
    const m: Record<string, number> = {};
    items.forEach((r) => { const k = r.pathology_code || "—"; m[k] = (m[k] || 0) + 1; });
    return Object.entries(m)
      .map(([k, v]) => ({ name: k, adet: v, fill: PCOLORS[k] || "#64748b" }))
      .sort((a, b) => b.adet - a.adet);
  }, [items]);

  return (
    <>
      <div className="tabs">
        <button className={`tab ${view === "liste" ? "active" : ""}`} onClick={() => setView("liste")}>Liste</button>
        <button className={`tab ${view === "grafik" ? "active" : ""}`} onClick={() => setView("grafik")}>Grafik</button>
      </div>

      {view === "grafik" ? (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Patolojiye Göre Çalışma Dağılımı (n={items.length})</h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={dist} layout="vertical" margin={{ left: 30, right: 30 }}>
              <XAxis type="number" allowDecimals={false} />
              <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="adet" radius={[0, 6, 6, 0]}>
                <LabelList dataKey="adet" position="right" />
                {dist.map((d, i) => (<Cell key={i} fill={d.fill} />))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <>
          <div className="toolbar">
            <input
              placeholder="Başlık, yazar, model, görev ara…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <select value={pc} onChange={(e) => setPc(e.target.value)}>
              <option>Tümü</option>
              {codes.map((c) => (<option key={c}>{c}</option>))}
            </select>
            <span className="count">{filtered.length} / {items.length} çalışma</span>
            <button
              className="btn-primary"
              style={{ marginLeft: "auto" }}
              onClick={() => setFormTarget("new")}
            >
              + Yeni Makale Ekle
            </button>
          </div>

          <table>
            <thead>
              <tr>
                <th className="idcol">Atıf</th>
                <th>Yazar</th>
                <th>Yıl</th>
                <th>Başlık</th>
                <th>Patoloji</th>
                <th>Modalite</th>
                <th>Görev</th>
                <th style={{ width: 110 }}>İşlemler</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr key={r.id}>
                  <td className="idcol">{r.ref_no}</td>
                  <td>{r.first_author}</td>
                  <td>{r.year}</td>
                  <td><strong>{r.title}</strong></td>
                  <td>
                    <span
                      className="cat-badge"
                      style={{ background: PCOLORS[r.pathology_code || ""] || "#64748b" }}
                    >
                      {r.pathology_code}
                    </span>
                  </td>
                  <td className="values">{r.modality}</td>
                  <td className="values">{r.task}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <button className="btn-detay" onClick={() => setSel(r)}>Detay</button>
                    {" "}
                    <button className="btn-detay" onClick={() => setFormTarget(r)}>Düzenle</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {/* Detay modal */}
      {sel && (
        <DetailModal
          study={sel}
          onClose={() => setSel(null)}
          onEdit={() => { setFormTarget(sel); setSel(null); }}
          onDelete={() => handleDelete(sel)}
        />
      )}

      {/* Ekle / Düzenle formu */}
      {formTarget !== null && (
        <StudyForm
          study={formTarget === "new" ? undefined : formTarget}
          onClose={() => setFormTarget(null)}
          onSaved={handleSaved}
        />
      )}
    </>
  );
}
