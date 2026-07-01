"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type {
  EvaluationCompareResult,
  EvaluationModelDto,
  SnapshotDto,
} from "@/lib/types";

const CLASS_NAME_MAP: Record<string, string> = {
  acute_cholecystitis:        "Akut Kolesistit",
  kidney_ureter_stone:        "Böbrek/Üreter Taşı",
  acute_pancreatitis:         "Akut Pankreatit",
  aortic_aneurysm_dissection: "Aort Anevrizma/Dis.",
  acute_appendicitis:         "Akut Apandisit",
  acute_diverticulitis:       "Akut Divertikülit",
};

function fmtPct(v: number | undefined) {
  if (v == null) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

export default function EvaluationPage() {
  const [selSnapshot, setSelSnapshot] = useState("");
  const [selModels, setSelModels] = useState<Set<string>>(new Set());
  const [iouThr, setIouThr] = useState(0.3);
  const [expandedModel, setExpandedModel] = useState<string | null>(null);

  const { data: snapshots = [] } = useQuery<SnapshotDto[]>({
    queryKey: ["training-snapshots"],
    queryFn: () => api.get<SnapshotDto[]>("/training/snapshots"),
  });

  const { data: models = [] } = useQuery<EvaluationModelDto[]>({
    queryKey: ["evaluation-models"],
    queryFn: () => api.get<EvaluationModelDto[]>("/evaluation/models"),
  });

  const compareMutation = useMutation({
    mutationFn: () =>
      api.post<EvaluationCompareResult>("/evaluation/compare", {
        snapshot_id: selSnapshot,
        model_ids: selModels.size > 0 ? [...selModels] : null,
        iou_threshold: iouThr,
      }),
  });

  function toggleModel(id: string) {
    setSelModels(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  const result = compareMutation.data;
  const comparisonCols = result?.comparison.length
    ? Object.keys(result.comparison[0]).filter(k => k !== "model")
    : [];

  return (
    <div style={{ display: "grid", gap: 24, maxWidth: 1100 }}>
      <div className="page-header">
        <h1 className="page-title">Model Değerlendirme</h1>
        <p className="page-subtitle">Snapshot GT üzerinde model tahminlerini karşılaştır.</p>
      </div>

      {/* ── Karşılaştırma formu ── */}
      <section className="card">
        <h2 style={{ marginTop: 0, marginBottom: 16, fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>
          Karşılaştırma Ayarları
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, alignItems: "start" }}>
          <div style={{ display: "grid", gap: 12 }}>
            <div className="form-group">
              <label className="form-label">Snapshot (GT kaynağı) *</label>
              <select
                className="form-input"
                value={selSnapshot}
                onChange={e => setSelSnapshot(e.target.value)}
              >
                <option value="">— Snapshot seçin —</option>
                {snapshots.map(s => (
                  <option key={s.id} value={s.id}>
                    {s.snapshot_name} ({s.included_annotations_count ?? 0} ann)
                  </option>
                ))}
              </select>
              <span className="form-hint">
                Sadece bbox annotasyonu olan snapshot'lar kullanılabilir.
              </span>
            </div>
            <div className="form-group">
              <label className="form-label">IoU Eşiği</label>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <input
                  type="range"
                  min={0.1}
                  max={0.9}
                  step={0.05}
                  value={iouThr}
                  onChange={e => setIouThr(parseFloat(e.target.value))}
                  style={{ flex: 1 }}
                />
                <span style={{ fontSize: 14, fontWeight: 700, color: "var(--accent)", minWidth: 36 }}>
                  {iouThr.toFixed(2)}
                </span>
              </div>
              <span className="form-hint">TP sayımı için GT ile tahmin çakışma eşiği (yaygın: 0.30 veya 0.50).</span>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">
              Modeller ({selModels.size === 0 ? "tümü" : `${selModels.size} seçili`})
            </label>
            {models.length === 0 ? (
              <p style={{ fontSize: 12, color: "var(--text-3)" }}>
                Henüz bbox tahmini olan aktif model yok.
              </p>
            ) : (
              <div style={{ display: "grid", gap: 6, maxHeight: 220, overflowY: "auto" }}>
                {models.map(m => (
                  <label
                    key={m.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: "8px 10px",
                      borderRadius: "var(--r-sm)",
                      border: `1px solid ${selModels.has(m.id) ? "var(--accent-border)" : "var(--border-1)"}`,
                      background: selModels.has(m.id) ? "var(--accent-muted)" : "var(--bg-surface)",
                      cursor: "pointer",
                      transition: "all 0.12s",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={selModels.has(m.id)}
                      onChange={() => toggleModel(m.id)}
                      style={{ accentColor: "var(--accent)" }}
                    />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-1)" }}>{m.name}</div>
                      <div style={{ fontSize: 11, color: "var(--text-3)" }}>
                        {m.architecture} · {m.prediction_count} tahmin
                      </div>
                    </div>
                    <span className={`badge ${m.run_mode === "default" ? "badge-success" : "badge-neutral"}`}>
                      {m.run_mode}
                    </span>
                  </label>
                ))}
              </div>
            )}
            <span className="form-hint" style={{ marginTop: 4 }}>
              Hiç seçilmezse tüm aktif modeller karşılaştırılır.
            </span>
          </div>
        </div>

        {compareMutation.error && (
          <div className="alert alert-danger" style={{ marginTop: 12 }}>
            {(compareMutation.error as Error).message}
          </div>
        )}

        <div style={{ marginTop: 16 }}>
          <button
            className="btn btn-primary"
            disabled={!selSnapshot || compareMutation.isPending}
            onClick={() => compareMutation.mutate()}
          >
            {compareMutation.isPending
              ? <><span className="spinner" />Karşılaştırılıyor…</>
              : "Karşılaştır"
            }
          </button>
        </div>
      </section>

      {/* ── Sonuçlar ── */}
      {result && (
        <>
          {/* Özet KPI kartları */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
            {[
              { label: "Snapshot",       value: result.snapshot_name,           color: "var(--text-1)" },
              { label: "GT Vaka",        value: result.gt_case_count,            color: "var(--accent)" },
              { label: "GT Annotasyon",  value: result.gt_annotation_count,      color: "var(--accent)" },
              { label: "IoU Eşiği",      value: result.iou_threshold.toFixed(2), color: "var(--warning)" },
            ].map(({ label, value, color }) => (
              <div key={label} className="stat-card">
                <div className="stat-label">{label}</div>
                <div className="stat-value" style={{ color, fontSize: typeof value === "string" && value.length > 8 ? 14 : undefined }}>
                  {value}
                </div>
              </div>
            ))}
          </div>

          {/* Karşılaştırma tablosu (Evaluator.compare() çıktısı) */}
          {result.comparison.length > 0 && (
            <section className="card">
              <h2 style={{ marginTop: 0, marginBottom: 12, fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>
                Model Karşılaştırma Özeti
              </h2>
              <div style={{ overflowX: "auto" }}>
                <table>
                  <thead>
                    <tr>
                      <th>Model</th>
                      {comparisonCols.map(c => (
                        <th key={c} style={{ textAlign: "right" }}>{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.comparison.map((row, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: 600, color: "var(--text-1)" }}>
                          {String(row.model ?? `Model ${i + 1}`)}
                        </td>
                        {comparisonCols.map(c => (
                          <td key={c} style={{ textAlign: "right", fontFamily: "var(--font-mono)", fontSize: 12 }}>
                            {typeof row[c] === "number"
                              ? (row[c] as number).toFixed(4)
                              : String(row[c] ?? "—")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Detaylı per-class metrikleri */}
          <section className="card">
            <h2 style={{ marginTop: 0, marginBottom: 12, fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>
              Detaylı Metrikler (IoU={result.iou_threshold.toFixed(2)})
            </h2>
            {Object.entries(result.detailed).map(([modelName, detail]) => (
              <div key={modelName} style={{ marginBottom: 12 }}>
                <button
                  className="btn btn-secondary"
                  style={{ width: "100%", textAlign: "left", justifyContent: "space-between", display: "flex" }}
                  onClick={() => setExpandedModel(expandedModel === modelName ? null : modelName)}
                >
                  <span style={{ fontWeight: 700 }}>{modelName}</span>
                  <span style={{ display: "flex", gap: 16, fontSize: 12 }}>
                    {detail.error ? (
                      <span style={{ color: "var(--danger)" }}>{detail.error}</span>
                    ) : (
                      <>
                        <span>Macro F1: <strong>{fmtPct(detail.macro_f1)}</strong></span>
                        <span>Micro F1: <strong>{fmtPct(detail.micro_f1)}</strong></span>
                      </>
                    )}
                    <span>{expandedModel === modelName ? "▲" : "▼"}</span>
                  </span>
                </button>

                {expandedModel === modelName && !detail.error && detail.per_class && (
                  <div style={{ marginTop: 8, border: "1px solid var(--border-1)", borderRadius: "var(--r-md)", overflow: "hidden" }}>
                    <table>
                      <thead>
                        <tr>
                          <th>Sınıf</th>
                          <th style={{ textAlign: "right" }}>Precision</th>
                          <th style={{ textAlign: "right" }}>Recall</th>
                          <th style={{ textAlign: "right" }}>F1</th>
                          <th style={{ textAlign: "right" }}>TP</th>
                          <th style={{ textAlign: "right" }}>FP</th>
                          <th style={{ textAlign: "right" }}>FN</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(detail.per_class).map(([cls, m]) => {
                          const label = CLASS_NAME_MAP[cls] ?? cls;
                          const f1Color =
                            (m.f1 ?? 0) >= 0.7 ? "var(--success)"
                            : (m.f1 ?? 0) >= 0.4 ? "var(--warning)"
                            : "var(--danger)";
                          return (
                            <tr key={cls}>
                              <td style={{ fontSize: 12, color: "var(--text-2)" }}>{label}</td>
                              <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", fontSize: 12 }}>
                                {fmtPct(m.precision)}
                              </td>
                              <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", fontSize: 12 }}>
                                {fmtPct(m.recall)}
                              </td>
                              <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", fontSize: 12, color: f1Color, fontWeight: 700 }}>
                                {fmtPct(m.f1)}
                              </td>
                              <td style={{ textAlign: "right", fontSize: 12, color: "var(--success)" }}>{m.tp}</td>
                              <td style={{ textAlign: "right", fontSize: 12, color: "var(--danger)" }}>{m.fp}</td>
                              <td style={{ textAlign: "right", fontSize: 12, color: "var(--warning)" }}>{m.fn}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                      <tfoot>
                        <tr style={{ borderTop: "2px solid var(--border-1)" }}>
                          <td style={{ fontSize: 12, fontWeight: 700, color: "var(--text-1)" }}>Ortalama</td>
                          <td />
                          <td />
                          <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 700, color: "var(--accent)" }}>
                            {fmtPct(detail.macro_f1)}
                          </td>
                          <td colSpan={3} />
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                )}
              </div>
            ))}
          </section>
        </>
      )}

      {/* Boş başlangıç durumu */}
      {!result && !compareMutation.isPending && (
        <section className="card">
          <div className="empty-state">
            <div className="empty-state-icon">📊</div>
            <div className="empty-state-title">Henüz karşılaştırma yapılmadı</div>
            <div className="empty-state-sub">
              Bir snapshot ve modeller seçip &ldquo;Karşılaştır&rdquo; butonuna tıklayın.
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
