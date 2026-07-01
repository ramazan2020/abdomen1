"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { CaseDetail, InferenceBatchDto, ModelVersionDto } from "@/lib/types";
import { getCurrentRole } from "@/lib/auth";

const REVIEW_OPTIONS = ["unreviewed", "in_review", "reviewed", "approved_for_training", "excluded"];

const RUN_STATUS_STYLE: Record<string, React.CSSProperties> = {
  queued:    { color: "#a1a1aa" },
  running:   { color: "#93c5fd" },
  succeeded: { color: "#4ade80" },
  failed:    { color: "#f87171" },
};

export default function CaseDetailPage({ params }: { params: { caseId: string } }) {
  const { caseId } = params;
  const queryClient = useQueryClient();
  const role = typeof window !== "undefined" ? getCurrentRole() : null;

  const { data: caseDetail, isLoading } = useQuery({
    queryKey: ["case", caseId],
    queryFn: () => api.get<CaseDetail>(`/cases/${caseId}`),
    refetchInterval: (query) => (query.state.data?.status === "ready" ? false : 3000),
  });

  // Aktif modeller (model seçici için)
  const { data: activeModels } = useQuery({
    queryKey: ["models-active"],
    queryFn: () => api.get<ModelVersionDto[]>("/models/active"),
    enabled: caseDetail?.status === "ready",
  });

  // Bu case'deki inference batch'leri
  const { data: batches } = useQuery({
    queryKey: ["inference-batches", caseId],
    queryFn: () => api.get<InferenceBatchDto[]>(`/inference/cases/${caseId}/batches`),
    enabled: caseDetail?.status === "ready",
    refetchInterval: (query) => {
      const bs = query.state.data;
      if (!bs || bs.length === 0) return false;
      const hasActive = bs.some(b => b.runs.some(r => r.status === "queued" || r.status === "running"));
      return hasActive ? 3000 : false;
    },
  });

  const reviewMutation = useMutation({
    mutationFn: (review_status: string) =>
      api.patch(`/cases/${caseId}/review-status`, { review_status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["case", caseId] }),
  });

  const runDefaultMutation = useMutation({
    mutationFn: () => api.post(`/inference/run-default`, { case_id: caseId }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["inference-batches", caseId] }),
  });

  const runComparisonMutation = useMutation({
    mutationFn: () => api.post(`/inference/run-comparison`, { case_id: caseId }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["inference-batches", caseId] }),
  });

  if (isLoading || !caseDetail) return <p>Yükleniyor...</p>;

  const report = caseDetail.validation_report;
  const adminOnlyStatuses = ["approved_for_training", "excluded"];
  const defaultModels = activeModels?.filter(m => m.run_mode === "default") ?? [];
  const compModels = activeModels?.filter(m => m.run_mode === "comparison") ?? [];

  return (
    <div style={{ display: "grid", gap: 16, maxWidth: 800 }}>
      <Link href="/doctor" style={{ fontSize: 13 }}>← Vaka listesi</Link>

      {/* Vaka özeti */}
      <section className="card">
        <h2 style={{ marginTop: 0 }}>{caseDetail.case_label ?? "(etiketsiz vaka)"}</h2>
        <p>
          Durum: <strong>{caseDetail.status}</strong> · Dilim: {caseDetail.n_slices ?? "-"} ·
          De-identifiye: {caseDetail.deidentified ? "evet" : "hayır"}
        </p>

        <label style={{ display: "block", marginTop: 12 }}>
          <span style={{ display: "block", fontSize: 13, marginBottom: 4 }}>Review durumu</span>
          <select
            value={caseDetail.review_status}
            onChange={(e) => reviewMutation.mutate(e.target.value)}
            style={{ padding: 6, borderRadius: 6, background: "#0f1115", color: "#e6e6e6", border: "1px solid #3a3e48" }}
          >
            {REVIEW_OPTIONS.map((opt) => (
              <option key={opt} value={opt} disabled={adminOnlyStatuses.includes(opt) && role !== "admin"}>
                {opt}{adminOnlyStatuses.includes(opt) ? " (admin)" : ""}
              </option>
            ))}
          </select>
        </label>

        {caseDetail.status === "ready" && (
          <Link href={`/doctor/cases/${caseId}/viewer`} className="btn-primary"
            style={{ display: "inline-block", marginTop: 16, textDecoration: "none" }}>
            Görüntüleyiciyi aç
          </Link>
        )}
      </section>

      {/* Inference — sadece ready case'lerde */}
      {caseDetail.status === "ready" && (
        <section className="card">
          <h3 style={{ marginTop: 0 }}>Model Inference</h3>

          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 12 }}>
            <div>
              <button
                className="btn-primary"
                disabled={runDefaultMutation.isPending || defaultModels.length === 0}
                onClick={() => runDefaultMutation.mutate()}
              >
                Varsayılan model çalıştır
              </button>
              {defaultModels.length > 0 && (
                <p style={{ fontSize: 12, color: "#9aa0ab", margin: "4px 0 0" }}>
                  {defaultModels.map(m => m.name).join(", ")}
                </p>
              )}
              {defaultModels.length === 0 && (
                <p style={{ fontSize: 12, color: "#f87171", margin: "4px 0 0" }}>
                  Aktif "default" model yok — admin'den kayıt isteyin
                </p>
              )}
            </div>

            {compModels.length > 0 && (
              <div>
                <button
                  className="btn-secondary"
                  disabled={runComparisonMutation.isPending}
                  onClick={() => runComparisonMutation.mutate()}
                >
                  Karşılaştırma modelleri ({compModels.length})
                </button>
                <p style={{ fontSize: 12, color: "#9aa0ab", margin: "4px 0 0" }}>
                  {compModels.map(m => m.name).join(", ")}
                </p>
              </div>
            )}
          </div>

          {/* Batch geçmişi */}
          {batches && batches.length > 0 && (
            <div>
              <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Çalışma geçmişi</p>
              {batches.map(batch => (
                <div key={batch.id} className="card" style={{ marginBottom: 8, background: "#0f1115" }}>
                  <p style={{ margin: "0 0 6px", fontSize: 13 }}>
                    <span className="badge" style={{ background: batch.batch_type === "default" ? "#1d4ed822" : "#71717a22", color: batch.batch_type === "default" ? "#93c5fd" : "#a1a1aa", marginRight: 8 }}>
                      {batch.batch_type}
                    </span>
                    {new Date(batch.created_at).toLocaleString("tr-TR")}
                  </p>
                  {batch.runs.map(run => (
                    <div key={run.id} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, padding: "3px 0", borderBottom: "1px solid #2a2e38" }}>
                      <span>{run.model_name} ({run.architecture})</span>
                      <span style={RUN_STATUS_STYLE[run.status] ?? {}}>
                        {run.status}
                        {run.error_message && <span title={run.error_message}> ⚠</span>}
                      </span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* DICOM doğrulama raporu */}
      {report && (
        <section className="card">
          <h3 style={{ marginTop: 0 }}>DICOM doğrulama raporu</h3>
          <table>
            <tbody>
              <tr><td>Toplam dosya</td><td>{report.total_dicom_count}</td></tr>
              <tr><td>Geçerli dilim</td><td>{report.valid_slice_count}</td></tr>
              <tr><td>Bozuk/eksik dosya</td><td>{report.invalid_file_count}</td></tr>
              <tr><td>Slice thickness (mm)</td><td>{report.slice_thickness_mm ?? "-"}</td></tr>
              <tr><td>Pixel spacing (mm)</td><td>{report.pixel_spacing_mm?.join(" × ") ?? "-"}</td></tr>
              <tr><td>Series description</td><td>{report.series_description ?? "-"}</td></tr>
              <tr><td>De-identification</td><td>{report.deidentification_status}</td></tr>
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
