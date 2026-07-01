"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { CaseListItem, DatasetDto, ModelVersionDto, SnapshotDto, TrainingJobDto, TrainingStatsDto } from "@/lib/types";
import { LESION_CLASS_LABELS_TR } from "@/lib/types";

const ARCH_LABELS: Record<string, string> = {
  yolo_det: "YOLO Detection",
  yolo_seg: "YOLO Segmentation",
};

const STATUS_BADGE: Record<string, string> = {
  queued:    "badge badge-neutral",
  running:   "badge badge-accent",
  succeeded: "badge badge-success",
  failed:    "badge badge-danger",
  cancelled: "badge badge-warning",
};

const REVIEW_LABEL: Record<string, string> = {
  unreviewed:            "İncelenmedi",
  in_review:             "İnceleniyor",
  reviewed:              "İncelendi",
  approved_for_training: "Onaylı",
  excluded:              "Dışlandı",
};

const REVIEW_BADGE: Record<string, string> = {
  unreviewed:            "badge badge-neutral",
  in_review:             "badge badge-accent",
  reviewed:              "badge badge-warning",
  approved_for_training: "badge badge-success",
  excluded:              "badge badge-danger",
};

const DEFAULT_PARAMS = {
  model: "yolov8s.pt",
  epochs: 50,
  imgsz: 512,
  batch: 16,
  patience: 20,
};

export default function TrainingPage() {
  const queryClient = useQueryClient();

  // ── Snapshot form ─────────────────────────────────────────────────────────
  const [snapName, setSnapName] = useState("");
  const [snapDesc, setSnapDesc] = useState("");
  const [snapNotes, setSnapNotes] = useState("");
  const [snapDatasetId, setSnapDatasetId] = useState<string>("");
  const [snapError, setSnapError] = useState<string | null>(null);

  // ── Job form ──────────────────────────────────────────────────────────────
  const [selSnapId, setSelSnapId] = useState<string>("");
  const [arch, setArch] = useState("yolo_det");
  const [paramsJson, setParamsJson] = useState(JSON.stringify(DEFAULT_PARAMS, null, 2));
  const [jobError, setJobError] = useState<string | null>(null);

  // ── Log + activation ──────────────────────────────────────────────────────
  const [viewLogId, setViewLogId] = useState<string | null>(null);
  const [activatingJobId, setActivatingJobId] = useState<string | null>(null);
  const [activateRunMode, setActivateRunMode] = useState<"default" | "comparison">("comparison");

  // ── Queries ───────────────────────────────────────────────────────────────
  const { data: stats } = useQuery({
    queryKey: ["training-stats"],
    queryFn: () => api.get<TrainingStatsDto>("/training/stats"),
    refetchInterval: 30_000,
  });

  const { data: datasets = [] } = useQuery<DatasetDto[]>({
    queryKey: ["datasets"],
    queryFn: () => api.get<DatasetDto[]>("/datasets"),
  });

  const { data: reviewedCases } = useQuery({
    queryKey: ["cases-reviewed"],
    queryFn: () => api.get<CaseListItem[]>("/cases?review_status=reviewed"),
    refetchInterval: 20_000,
  });

  const { data: snapshots } = useQuery({
    queryKey: ["training-snapshots"],
    queryFn: () => api.get<SnapshotDto[]>("/training/snapshots"),
  });

  const { data: jobs } = useQuery({
    queryKey: ["training-jobs"],
    queryFn: () => api.get<TrainingJobDto[]>("/training/jobs"),
    refetchInterval: (query) => {
      const active = query.state.data?.some(j => j.status === "queued" || j.status === "running");
      return active ? 4000 : false;
    },
  });

  const { data: logText } = useQuery({
    queryKey: ["training-log", viewLogId],
    queryFn: () => viewLogId ? api.getRaw(`/training/jobs/${viewLogId}/logs`) : Promise.resolve(""),
    enabled: !!viewLogId,
    refetchInterval: (query) => {
      const job = jobs?.find(j => j.id === viewLogId);
      return job?.status === "running" ? 3000 : false;
    },
  });

  // ── Mutations ─────────────────────────────────────────────────────────────
  const approveMutation = useMutation({
    mutationFn: (caseId: string) =>
      api.patch(`/cases/${caseId}/review-status`, { review_status: "approved_for_training" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cases-reviewed"] });
      queryClient.invalidateQueries({ queryKey: ["training-stats"] });
    },
  });

  const excludeMutation = useMutation({
    mutationFn: (caseId: string) =>
      api.patch(`/cases/${caseId}/review-status`, { review_status: "excluded" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cases-reviewed"] });
      queryClient.invalidateQueries({ queryKey: ["training-stats"] });
    },
  });

  const createSnapMutation = useMutation({
    mutationFn: () => api.post<SnapshotDto>("/training/snapshots", {
      snapshot_name: snapName,
      description: snapDesc || null,
      notes: snapNotes || null,
      dataset_id: snapDatasetId || null,
    }),
    onSuccess: (snap) => {
      setSnapName(""); setSnapDesc(""); setSnapNotes(""); setSnapDatasetId(""); setSnapError(null);
      setSelSnapId(snap.id);
      queryClient.invalidateQueries({ queryKey: ["training-snapshots"] });
    },
    onError: (err: Error) => setSnapError(err.message),
  });

  const launchJobMutation = useMutation({
    mutationFn: () => {
      let params: Record<string, unknown>;
      try { params = JSON.parse(paramsJson); }
      catch { throw new Error("Params JSON formatı hatalı"); }
      return api.post<TrainingJobDto>("/training/jobs", {
        snapshot_id: selSnapId,
        architecture: arch,
        params,
      });
    },
    onSuccess: (job) => {
      setJobError(null);
      setViewLogId(job.id);
      queryClient.invalidateQueries({ queryKey: ["training-jobs"] });
    },
    onError: (err: Error) => setJobError(err.message),
  });

  const cancelMutation = useMutation({
    mutationFn: (jobId: string) => api.post(`/training/jobs/${jobId}/cancel`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["training-jobs"] }),
  });

  const activateMutation = useMutation({
    mutationFn: async (modelId: string) => {
      await api.patch(`/models/${modelId}/run-mode`, { run_mode: activateRunMode });
      return api.post<ModelVersionDto>(`/models/${modelId}/activate`);
    },
    onSuccess: () => {
      setActivatingJobId(null);
      queryClient.invalidateQueries({ queryKey: ["training-jobs"] });
    },
  });

  const activeJob = jobs?.find(j => j.id === viewLogId) ?? null;
  const activatingJob = jobs?.find(j => j.id === activatingJobId) ?? null;

  const approvedCount = stats?.review_status_counts?.approved_for_training ?? 0;
  const reviewedCount = stats?.review_status_counts?.reviewed ?? 0;

  return (
    <div style={{ display: "grid", gap: 24, maxWidth: 1100 }}>
      <div className="page-header">
        <h1 className="page-title">Eğitim Yönetimi</h1>
        <p className="page-subtitle">Vaka QA, dataset snapshot ve model eğitimi.</p>
      </div>

      {/* ── Havuz istatistikleri ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        {[
          { label: "Onaylı Vaka",       value: approvedCount,                       color: "var(--success)" },
          { label: "QA Bekleyen",        value: reviewedCount,                       color: "var(--warning)" },
          { label: "Havuz Annotasyon",   value: stats?.pool_annotation_count ?? 0,   color: "var(--accent)" },
          { label: "Toplam Vaka",        value: Object.values(stats?.review_status_counts ?? {}).reduce((a, b) => a + b, 0), color: "var(--text-2)" },
        ].map(({ label, value, color }) => (
          <div key={label} className="stat-card">
            <div className="stat-label">{label}</div>
            <div className="stat-value" style={{ color }}>{value}</div>
          </div>
        ))}
      </div>

      {/* ── QA bekleyen vakalar ── */}
      {(reviewedCases && reviewedCases.length > 0) && (
        <section className="card">
          <h2 style={{ marginTop: 0, marginBottom: 12, fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>
            QA Bekleyen Vakalar
            <span className="badge badge-warning" style={{ marginLeft: 8 }}>{reviewedCases.length}</span>
          </h2>
          <p style={{ fontSize: 12, color: "var(--text-3)", marginBottom: 12 }}>
            Doktorlar tarafından <strong>reviewed</strong> olarak işaretlendi, eğitime dahil/hariç tutulması için onayınız bekleniyor.
          </p>
          <table>
            <thead>
              <tr>
                <th>Vaka Etiketi</th>
                <th>Durum</th>
                <th>Dilim Sayısı</th>
                <th>Yüklenme Tarihi</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {reviewedCases.map(c => (
                <tr key={c.id}>
                  <td style={{ fontWeight: 600, color: "var(--text-1)" }}>{c.case_label ?? c.id.slice(0, 8)}</td>
                  <td><span className={REVIEW_BADGE[c.review_status]}>{REVIEW_LABEL[c.review_status]}</span></td>
                  <td style={{ color: "var(--text-3)" }}>{c.n_slices ?? "—"}</td>
                  <td style={{ fontSize: 11, color: "var(--text-3)" }}>
                    {new Date(c.created_at).toLocaleDateString("tr-TR")}
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 6 }}>
                      <button
                        className="btn btn-sm btn-primary"
                        disabled={approveMutation.isPending}
                        onClick={() => approveMutation.mutate(c.id)}
                      >
                        Onayla
                      </button>
                      <button
                        className="btn btn-sm btn-danger"
                        disabled={excludeMutation.isPending}
                        onClick={() => excludeMutation.mutate(c.id)}
                      >
                        Hariç tut
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* ── Sınıf dağılımı ── */}
      {stats && Object.keys(stats.class_distribution).length > 0 && (
        <section className="card">
          <h2 style={{ marginTop: 0, marginBottom: 12, fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>
            Eğitim Havuzu — Sınıf Dağılımı
          </h2>
          <div style={{ display: "grid", gap: 8 }}>
            {LESION_CLASS_LABELS_TR.map((label, idx) => {
              const count = stats.class_distribution[String(idx)] ?? 0;
              const total = stats.pool_annotation_count || 1;
              const pct = Math.round((count / total) * 100);
              return (
                <div key={idx} style={{ display: "grid", gridTemplateColumns: "180px 1fr 40px", gap: 10, alignItems: "center" }}>
                  <span style={{ fontSize: 12, color: "var(--text-2)" }}>{label}</span>
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${pct}%` }} />
                  </div>
                  <span style={{ fontSize: 12, color: "var(--text-3)", textAlign: "right" }}>{count}</span>
                </div>
              );
            })}
          </div>
        </section>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, alignItems: "start" }}>
        {/* ── Dataset Snapshot ── */}
        <section className="card">
          <h2 style={{ marginTop: 0, marginBottom: 16, fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>
            Dataset Snapshot Oluştur
          </h2>
          {approvedCount === 0 && (
            <div className="alert alert-warning" style={{ marginBottom: 12 }}>
              Henüz <strong>approved_for_training</strong> vakası yok. Yukarıdaki QA bölümünden vakalar onaylandıktan sonra snapshot oluşturun.
            </div>
          )}
          <div style={{ display: "grid", gap: 12 }}>
            <div className="form-group">
              <label className="form-label">Snapshot adı *</label>
              <input
                className="form-input"
                value={snapName}
                onChange={e => setSnapName(e.target.value)}
                placeholder="örn. abdomen-v1-2026q2"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Açıklama</label>
              <input
                className="form-input"
                value={snapDesc}
                onChange={e => setSnapDesc(e.target.value)}
                placeholder="Kısa açıklama (opsiyonel)"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Notlar</label>
              <textarea
                className="form-input"
                rows={2}
                value={snapNotes}
                onChange={e => setSnapNotes(e.target.value)}
                placeholder="Serbest metin notlar..."
                style={{ resize: "vertical" }}
              />
              <span className="form-hint">
                Yalnızca <strong>approved_for_training</strong> vakalar ve havuzdaki annotasyonlar dahil edilir.
              </span>
            </div>
            <div className="form-group">
              <label className="form-label">Veri seti filtresi (opsiyonel)</label>
              <select
                className="form-input"
                value={snapDatasetId}
                onChange={e => setSnapDatasetId(e.target.value)}
              >
                <option value="">Tüm veri setleri</option>
                {datasets.map(ds => (
                  <option key={ds.id} value={ds.id}>{ds.name}</option>
                ))}
              </select>
              <span className="form-hint">Seçilirse yalnızca bu veri setine ait onaylı vakalar dahil edilir.</span>
            </div>
            {snapError && <div className="alert alert-danger">{snapError}</div>}
            <button
              className="btn btn-primary"
              disabled={!snapName || createSnapMutation.isPending}
              onClick={() => createSnapMutation.mutate()}
            >
              {createSnapMutation.isPending
                ? <><span className="spinner" />Oluşturuluyor…</>
                : "Snapshot Oluştur"
              }
            </button>
          </div>

          {snapshots && snapshots.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <div className="divider" />
              <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-3)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                Mevcut Snapshotlar
              </p>
              {snapshots.map(s => (
                <div
                  key={s.id}
                  onClick={() => setSelSnapId(s.id)}
                  style={{
                    padding: "10px 12px",
                    borderRadius: "var(--r-md)",
                    border: `1px solid ${selSnapId === s.id ? "var(--accent-border)" : "var(--border-1)"}`,
                    background: selSnapId === s.id ? "var(--accent-muted)" : "var(--bg-surface)",
                    cursor: "pointer",
                    marginBottom: 6,
                    transition: "border-color 0.12s, background 0.12s",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: selSnapId === s.id ? "var(--accent)" : "var(--text-1)" }}>
                      {s.snapshot_name}
                    </span>
                    <span style={{ fontSize: 11, color: "var(--text-3)" }}>
                      {new Date(s.created_at).toLocaleDateString("tr-TR")}
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 3 }}>
                    {s.included_cases_count ?? 0} vaka · {s.included_annotations_count ?? 0} annotasyon
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ── Eğitim başlat ── */}
        <section className="card">
          <h2 style={{ marginTop: 0, marginBottom: 16, fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>
            Eğitim Başlat
          </h2>
          <div style={{ display: "grid", gap: 12 }}>
            <div className="form-group">
              <label className="form-label">Seçili snapshot</label>
              {selSnapId
                ? <div className="tag" style={{ display: "inline-flex" }}>
                    {snapshots?.find(s => s.id === selSnapId)?.snapshot_name ?? selSnapId.slice(0, 8)}
                  </div>
                : <p style={{ fontSize: 12, color: "var(--text-3)" }}>Soldan bir snapshot seçin</p>
              }
            </div>
            <div className="form-group">
              <label className="form-label">Mimari</label>
              <select className="form-input" value={arch} onChange={e => setArch(e.target.value)}>
                {Object.entries(ARCH_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Parametreler (JSON)</label>
              <textarea
                className="form-input"
                rows={8}
                value={paramsJson}
                onChange={e => setParamsJson(e.target.value)}
                style={{ fontFamily: "var(--font-mono)", fontSize: 12, resize: "vertical" }}
              />
              <span className="form-hint">
                model, epochs, imgsz, batch, patience — ultralytics YOLO.train() parametreleri
              </span>
            </div>
            {jobError && <div className="alert alert-danger">{jobError}</div>}
            <button
              className="btn btn-primary"
              disabled={!selSnapId || launchJobMutation.isPending}
              onClick={() => launchJobMutation.mutate()}
            >
              {launchJobMutation.isPending
                ? <><span className="spinner" />Kuyruğa alınıyor…</>
                : "Eğitimi Başlat"
              }
            </button>
          </div>
        </section>
      </div>

      {/* ── Job listesi ── */}
      <section className="card">
        <h2 style={{ marginTop: 0, marginBottom: 16, fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>
          Eğitim İşleri
        </h2>
        {(!jobs || jobs.length === 0) && (
          <div className="empty-state">
            <div className="empty-state-icon">🏋️</div>
            <div className="empty-state-title">Henüz eğitim işi yok</div>
            <div className="empty-state-sub">Yukarıdan bir snapshot seçip eğitimi başlatın.</div>
          </div>
        )}
        {jobs && jobs.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Mimari</th>
                <th>Durum</th>
                <th>İlerleme</th>
                <th>Epoch</th>
                <th>Başlangıç</th>
                <th>Süre</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(job => {
                const start = job.started_at ? new Date(job.started_at) : null;
                const end   = job.finished_at ? new Date(job.finished_at) : null;
                const durationMin = start && end
                  ? Math.round((end.getTime() - start.getTime()) / 60000)
                  : null;

                return (
                  <tr
                    key={job.id}
                    style={{ cursor: "pointer", background: viewLogId === job.id ? "rgba(59,130,246,0.05)" : undefined }}
                    onClick={() => setViewLogId(job.id === viewLogId ? null : job.id)}
                  >
                    <td>
                      <div style={{ fontWeight: 600, color: "var(--text-1)", fontSize: 13 }}>
                        {ARCH_LABELS[job.architecture] ?? job.architecture}
                      </div>
                      <div style={{ fontSize: 11, color: "var(--text-3)" }}>
                        {(job.params as {model?: string}).model ?? ""}
                      </div>
                    </td>
                    <td>
                      <span className={STATUS_BADGE[job.status] ?? "badge badge-neutral"}>
                        {job.status}
                      </span>
                      {job.error_message && (
                        <div style={{ fontSize: 11, color: "var(--danger)", marginTop: 4, maxWidth: 200 }}
                             title={job.error_message}>
                          {job.error_message.slice(0, 60)}{job.error_message.length > 60 ? "…" : ""}
                        </div>
                      )}
                    </td>
                    <td style={{ minWidth: 120 }}>
                      {job.progress_percent != null ? (
                        <div>
                          <div className="progress-bar" style={{ marginBottom: 3 }}>
                            <div className="progress-fill" style={{ width: `${job.progress_percent}%` }} />
                          </div>
                          <span style={{ fontSize: 11, color: "var(--text-3)" }}>
                            {job.progress_percent.toFixed(0)}%
                          </span>
                        </div>
                      ) : "—"}
                    </td>
                    <td style={{ color: "var(--text-3)", fontSize: 12 }}>
                      {job.current_epoch ?? "—"}
                    </td>
                    <td style={{ fontSize: 11, color: "var(--text-3)" }}>
                      {start ? start.toLocaleString("tr-TR") : "—"}
                    </td>
                    <td style={{ fontSize: 11, color: "var(--text-3)" }}>
                      {durationMin != null ? `${durationMin}dk` : job.status === "running" ? "devam ediyor" : "—"}
                    </td>
                    <td onClick={e => e.stopPropagation()}>
                      <div style={{ display: "flex", gap: 4, flexDirection: "column" }}>
                        {(job.status === "queued" || job.status === "running") && (
                          <button
                            className="btn btn-sm btn-danger"
                            onClick={() => cancelMutation.mutate(job.id)}
                            disabled={cancelMutation.isPending}
                          >
                            İptal
                          </button>
                        )}
                        {job.status === "succeeded" && job.result_model_version_id && (
                          <button
                            className="btn btn-sm btn-primary"
                            onClick={() => {
                              setActivatingJobId(job.id);
                              setActivateRunMode("comparison");
                            }}
                          >
                            Aktifleştir
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>

      {/* ── Model aktivasyon modalı ── */}
      {activatingJob?.result_model_version_id && (
        <section className="card" style={{ border: "1px solid var(--accent-border)", background: "var(--accent-muted)" }}>
          <h2 style={{ marginTop: 0, marginBottom: 12, fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>
            Model Aktivasyonu
          </h2>
          <p style={{ fontSize: 13, color: "var(--text-2)", marginBottom: 16 }}>
            Eğitim tamamlandı. Model ID: <code>{activatingJob.result_model_version_id.slice(0, 8)}…</code>
            — aktifleştirmek, bu modelin inference'da kullanılmasını sağlar.
          </p>
          <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Run modu</label>
              <select
                className="form-input"
                value={activateRunMode}
                onChange={e => setActivateRunMode(e.target.value as "default" | "comparison")}
                style={{ width: 180 }}
              >
                <option value="comparison">comparison — doktor isteğiyle</option>
                <option value="default">default — otomatik çalışır</option>
              </select>
            </div>
            <button
              className="btn btn-primary"
              disabled={activateMutation.isPending}
              onClick={() => activateMutation.mutate(activatingJob.result_model_version_id!)}
            >
              {activateMutation.isPending
                ? <><span className="spinner" />Aktifleştiriliyor…</>
                : "Aktifleştir"
              }
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => setActivatingJobId(null)}
            >
              İptal
            </button>
          </div>
        </section>
      )}

      {/* ── Log viewer ── */}
      {viewLogId && (
        <section className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h2 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>
              Eğitim Logu
              {activeJob && (
                <span className={`badge ${STATUS_BADGE[activeJob.status] ?? "badge-neutral"}`}
                      style={{ marginLeft: 10, verticalAlign: "middle" }}>
                  {activeJob.status}
                </span>
              )}
            </h2>
            <button className="btn btn-sm btn-secondary" onClick={() => setViewLogId(null)}>
              Kapat
            </button>
          </div>
          {activeJob?.best_metric && Object.keys(activeJob.best_metric).length > 0 && (
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 12 }}>
              {Object.entries(activeJob.best_metric).slice(0, 6).map(([k, v]) => (
                <div key={k} className="stat-card" style={{ padding: "8px 14px", minWidth: 100 }}>
                  <div className="stat-label">{k}</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text-1)" }}>
                    {typeof v === "number" ? v.toFixed(4) : String(v)}
                  </div>
                </div>
              ))}
            </div>
          )}
          <pre style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-1)",
            borderRadius: "var(--r-md)",
            padding: 14,
            fontFamily: "var(--font-mono)",
            fontSize: 11.5,
            color: "var(--text-2)",
            maxHeight: 400,
            overflow: "auto",
            whiteSpace: "pre-wrap",
            wordBreak: "break-all",
          }}>
            {logText || "Log bekleniyor…"}
          </pre>
        </section>
      )}
    </div>
  );
}
