"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { AnnotationZipImportResponse, CaseListItem, DatasetDto } from "@/lib/types";

const REVIEW_STATUS_LABELS: Record<string, string> = {
  unreviewed: "İncelenmedi",
  in_review: "İncelemede",
  reviewed: "İncelendi",
  approved_for_training: "Eğitime onaylandı",
  excluded: "Hariç tutuldu",
};

const STATUS_LABELS: Record<string, string> = {
  uploaded: "Yüklendi",
  validating: "Doğrulanıyor",
  ready: "Hazır",
  failed: "Başarısız",
};

export default function DoctorWorklistPage() {
  const queryClient = useQueryClient();
  const [reviewFilter, setReviewFilter] = useState<string>("");
  const [datasetFilter, setDatasetFilter] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [caseLabel, setCaseLabel] = useState("");
  const [uploadDatasetId, setUploadDatasetId] = useState<string>("");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const { data: datasets = [] } = useQuery<DatasetDto[]>({
    queryKey: ["datasets"],
    queryFn: () => api.get<DatasetDto[]>("/datasets"),
  });

  const { data: cases, isLoading } = useQuery({
    queryKey: ["cases", reviewFilter, datasetFilter],
    queryFn: () => {
      const params = new URLSearchParams();
      if (reviewFilter) params.set("review_status", reviewFilter);
      if (datasetFilter) params.set("dataset_id", datasetFilter);
      const qs = params.toString();
      return api.get<CaseListItem[]>(`/cases${qs ? `?${qs}` : ""}`);
    },
    refetchInterval: 5000, // ingest arka planda çalışırken status değişimini yakalamak için
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.del(`/cases/${id}`),
    onSuccess: () => {
      setDeletingId(null);
      queryClient.invalidateQueries({ queryKey: ["cases"] });
    },
  });

  function handleDelete(c: CaseListItem) {
    const label = c.case_label ?? "(etiketsiz)";
    if (window.confirm(`"${label}" vakasını kalıcı olarak silmek istediğinizden emin misiniz?\n\nBu işlem geri alınamaz.`)) {
      setDeletingId(c.id);
      deleteMutation.mutate(c.id);
    }
  }

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Lütfen bir .zip dosyası seçin");
      const form = new FormData();
      form.append("file", file);
      if (caseLabel) form.append("case_label", caseLabel);
      if (uploadDatasetId) form.append("dataset_id", uploadDatasetId);
      return api.postForm(`/cases/upload`, form);
    },
    onSuccess: () => {
      setFile(null);
      setCaseLabel("");
      setUploadDatasetId("");
      setUploadError(null);
      queryClient.invalidateQueries({ queryKey: ["cases"] });
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
    },
    onError: (err: Error) => setUploadError(err.message),
  });

  const [annotationZip, setAnnotationZip] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<AnnotationZipImportResponse | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  const importZipMutation = useMutation({
    mutationFn: async () => {
      if (!annotationZip) throw new Error("Lütfen bir annotation .zip dosyası seçin");
      const form = new FormData();
      form.append("file", annotationZip);
      return api.postForm<AnnotationZipImportResponse>(`/annotations/import-zip`, form);
    },
    onSuccess: (result) => {
      setAnnotationZip(null);
      setImportError(null);
      setImportResult(result);
      queryClient.invalidateQueries({ queryKey: ["annotations"] });
    },
    onError: (err: Error) => {
      setImportError(err.message);
      setImportResult(null);
    },
  });

  return (
    <div style={{ display: "grid", gap: 24, maxWidth: 1000 }}>
      <div className="page-header">
        <h1 className="page-title">Vaka Listesi</h1>
        <p className="page-subtitle">DICOM serisi yükleyin, annotasyon ZIP içe aktarın ve vakaları yönetin.</p>
      </div>

      <section className="card">
        <h2 style={{ marginTop: 0, marginBottom: 16, fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>
          Yeni DICOM Serisi Yükle
        </h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            uploadMutation.mutate();
          }}
          style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}
        >
          <input
            type="file"
            accept=".zip"
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null;
              setFile(f);
              // make_sample_zips.py çıktısı T_20001.zip / C_20001.zip şeklinde —
              // etiket boşsa dosya adını öneri olarak kullan.
              if (f && !caseLabel) setCaseLabel(f.name.replace(/\.zip$/i, ""));
            }}
          />
          <input
            type="text"
            placeholder="Vaka etiketi, örn. T_20001"
            value={caseLabel}
            onChange={(e) => setCaseLabel(e.target.value)}
            style={{ padding: 8, borderRadius: 6, border: "1px solid #3a3e48", background: "#0f1115", color: "#e6e6e6" }}
          />
          <select
            value={uploadDatasetId}
            onChange={(e) => setUploadDatasetId(e.target.value)}
            style={{ padding: 8, borderRadius: 6, border: "1px solid #3a3e48", background: "#0f1115", color: "#e6e6e6" }}
          >
            <option value="">Veri seti seç (opsiyonel)</option>
            {datasets.map((ds) => (
              <option key={ds.id} value={ds.id}>{ds.name}</option>
            ))}
          </select>
          <button type="submit" className="btn-primary" disabled={!file || uploadMutation.isPending}>
            {uploadMutation.isPending ? "Yükleniyor..." : "Yükle"}
          </button>
        </form>
        {uploadError && <p style={{ color: "#f87171", marginTop: 8 }}>{uploadError}</p>}
        <p style={{ fontSize: 12, color: "#9aa0ab", marginTop: 8 }}>
          Yükleme sonrası de-identifikasyon, doğrulama ve dilim önbellekleme arka planda
          çalışır; vaka birkaç saniye içinde &quot;Hazır&quot; durumuna geçer. Vaka etiketini{" "}
          <strong>T_</strong> (Egitim Verisi) veya <strong>C_</strong> (Test/Yarışma Verisi)
          prefix&apos;iyle girin — aynı case numarası iki sette farklı vakalara karşılık
          gelebildiğinden annotasyon importu bu prefix&apos;e göre eşleştirme yapar.
        </p>
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0, marginBottom: 16, fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>
          Annotasyon ZIP İçe Aktar
        </h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            importZipMutation.mutate();
          }}
          style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}
        >
          <input
            type="file"
            accept=".zip"
            onChange={(e) => setAnnotationZip(e.target.files?.[0] ?? null)}
          />
          <button type="submit" className="btn-primary" disabled={!annotationZip || importZipMutation.isPending}>
            {importZipMutation.isPending ? "İçe aktarılıyor..." : "İçe aktar"}
          </button>
        </form>
        {importError && <p style={{ color: "#f87171", marginTop: 8 }}>{importError}</p>}
        {importResult && (
          <div style={{ marginTop: 12 }}>
            <p style={{ fontSize: 13 }}>
              <strong>{importResult.total_sent}</strong> annotasyon eklendi,{" "}
              <strong>{importResult.total_skipped}</strong> atlandı.
            </p>
            <table>
              <thead>
                <tr>
                  <th>Vaka</th>
                  <th>Eşleşme</th>
                  <th>Eklendi</th>
                  <th>Atlandı</th>
                  <th>Not</th>
                </tr>
              </thead>
              <tbody>
                {importResult.details.map((d, i) => (
                  <tr key={i}>
                    <td>{d.prefix}_{d.case_num}</td>
                    <td>
                      {d.matched === true && <span className="badge" style={{ background: "#16a34a22", color: "#4ade80" }}>bulundu</span>}
                      {d.matched === false && <span className="badge" style={{ background: "#dc262622", color: "#f87171" }}>bulunamadı</span>}
                      {d.matched === null && <span style={{ color: "#9aa0ab" }}>—</span>}
                    </td>
                    <td>{d.sent}</td>
                    <td>{d.skipped}</td>
                    <td style={{ fontSize: 12, color: "#9aa0ab" }}>{d.note ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p style={{ fontSize: 12, color: "#9aa0ab", marginTop: 8 }}>
          <code>webapp/scripts/make_annotation_zip.py</code> ile üretilen zip&apos;i yükleyin. Vakalar,
          listede aşağıdaki vaka etiketleri içinde geçen <strong>T_</strong>/<strong>C_</strong> prefix&apos;li
          tam anahtara göre eşleştirilir (örn. &quot;T_20001&quot; etiketi yalnızca T_20001 ile eşleşir,
          C_20001 ile karışmaz) — eşleşecek vaka önce, aynı etiketle yüklenmiş olmalıdır.
        </p>
      </section>

      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
          <h2 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>Vakalar</h2>
          <div style={{ display: "flex", gap: 8 }}>
            <select
              value={datasetFilter}
              onChange={(e) => setDatasetFilter(e.target.value)}
              style={{ padding: 6, borderRadius: 6, background: "#0f1115", color: "#e6e6e6", border: "1px solid #3a3e48" }}
            >
              <option value="">Tüm veri setleri</option>
              {datasets.map((ds) => (
                <option key={ds.id} value={ds.id}>{ds.name}</option>
              ))}
            </select>
            <select
              value={reviewFilter}
              onChange={(e) => setReviewFilter(e.target.value)}
              style={{ padding: 6, borderRadius: 6, background: "#0f1115", color: "#e6e6e6", border: "1px solid #3a3e48" }}
            >
              <option value="">Tüm review durumları</option>
              {Object.entries(REVIEW_STATUS_LABELS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </div>
        </div>

        {isLoading && <p>Yükleniyor...</p>}
        {cases && cases.length === 0 && <p style={{ color: "#9aa0ab" }}>Henüz vaka yok.</p>}
        {cases && cases.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Etiket</th>
                <th>Durum</th>
                <th>Review</th>
                <th>Dilim</th>
                <th>Yüklenme</th>
                <th style={{ width: 110 }}></th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.id} style={{ opacity: deletingId === c.id ? 0.4 : 1 }}>
                  <td>{c.case_label ?? <span style={{ color: "#9aa0ab" }}>(etiketsiz)</span>}</td>
                  <td>
                    <span
                      className="badge"
                      style={{
                        background: c.status === "ready" ? "#16a34a22" : c.status === "failed" ? "#dc262622" : "#71717a22",
                        color: c.status === "ready" ? "#4ade80" : c.status === "failed" ? "#f87171" : "#a1a1aa",
                      }}
                    >
                      {STATUS_LABELS[c.status] ?? c.status}
                    </span>
                  </td>
                  <td style={{ fontSize: 12, color: "#9aa0ab" }}>
                    {REVIEW_STATUS_LABELS[c.review_status] ?? c.review_status}
                  </td>
                  <td style={{ color: "#9aa0ab" }}>{c.n_slices ?? "-"}</td>
                  <td style={{ fontSize: 12, color: "#9aa0ab" }}>{new Date(c.created_at).toLocaleString("tr-TR")}</td>
                  <td>
                    <div style={{ display: "flex", gap: 6 }}>
                      <Link
                        href={`/doctor/cases/${c.id}`}
                        className="btn-secondary"
                        style={{ textDecoration: "none", display: "inline-block", padding: "4px 10px", fontSize: 13 }}
                      >
                        Aç
                      </Link>
                      <button
                        className="btn-secondary"
                        style={{ padding: "4px 8px", fontSize: 13, color: "#f87171", borderColor: "#7f1d1d" }}
                        disabled={deletingId === c.id}
                        onClick={() => handleDelete(c)}
                        title="Vakayı kalıcı sil"
                      >
                        Sil
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
