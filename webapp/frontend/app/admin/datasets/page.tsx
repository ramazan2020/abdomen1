"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { CaseListItem, DatasetDto } from "@/lib/types";

const SOURCE_OPTIONS = ["webapp", "external", "mixed"];

const REVIEW_BADGE: Record<string, { bg: string; color: string }> = {
  unreviewed:            { bg: "var(--bg-elevated)",   color: "var(--text-3)" },
  in_review:             { bg: "var(--info-muted)",    color: "var(--info)" },
  reviewed:              { bg: "var(--warning-muted)", color: "var(--warning)" },
  approved_for_training: { bg: "var(--success-muted)", color: "var(--success)" },
  excluded:              { bg: "var(--danger-muted)",  color: "var(--danger)" },
};
const REVIEW_TR: Record<string, string> = {
  unreviewed: "İncelenmedi", in_review: "İncelemede", reviewed: "İncelendi",
  approved_for_training: "Onaylı", excluded: "Hariç",
};

export default function AdminDatasetsPage() {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const [name, setName]               = useState("");
  const [description, setDescription] = useState("");
  const [source, setSource]           = useState("webapp");
  const [notes, setNotes]             = useState("");
  const [formError, setFormError]     = useState<string | null>(null);

  const { data: datasets = [], isLoading } = useQuery<DatasetDto[]>({
    queryKey: ["datasets"],
    queryFn: () => api.get<DatasetDto[]>("/datasets"),
  });

  const { data: cases = [], isLoading: casesLoading } = useQuery<CaseListItem[]>({
    queryKey: ["cases-by-dataset", selectedId],
    queryFn: () => api.get<CaseListItem[]>(`/cases?dataset_id=${selectedId}`),
    enabled: !!selectedId,
  });

  const createMutation = useMutation({
    mutationFn: (body: object) => api.post<DatasetDto>("/datasets", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["datasets"] });
      setName(""); setDescription(""); setSource("webapp"); setNotes("");
      setFormError(null); setShowForm(false);
    },
    onError: (err: unknown) => {
      setFormError(err instanceof Error ? err.message : "Hata oluştu");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.del(`/datasets/${id}`),
    onSuccess: (_: unknown, id: string) => {
      qc.invalidateQueries({ queryKey: ["datasets"] });
      if (selectedId === id) setSelectedId(null);
    },
  });

  const unassignMutation = useMutation({
    mutationFn: (caseId: string) => api.patch(`/cases/${caseId}/dataset`, { dataset_id: null }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cases-by-dataset", selectedId] });
      qc.invalidateQueries({ queryKey: ["datasets"] });
    },
  });

  const deleteCaseMutation = useMutation({
    mutationFn: (caseId: string) => api.del(`/cases/${caseId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cases-by-dataset", selectedId] });
      qc.invalidateQueries({ queryKey: ["datasets"] });
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) { setFormError("Ad zorunludur"); return; }
    createMutation.mutate({
      name: name.trim(),
      description: description.trim() || null,
      source,
      notes: notes.trim() || null,
    });
  };

  const totalCases   = datasets.reduce((s, d) => s + d.case_count, 0);
  const selectedDs   = datasets.find(d => d.id === selectedId);

  return (
    <div style={{ display: "grid", gap: 24, maxWidth: 1100 }}>
      {/* ── Başlık ── */}
      <div className="page-header" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <h1 className="page-title">Veri Setleri</h1>
          <p className="page-subtitle">Veri setleri tanımlayın ve vakaları bu setlere atayın.</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => { setShowForm(f => !f); setFormError(null); }}
        >
          {showForm ? "İptal" : "+ Yeni Veri Seti"}
        </button>
      </div>

      {/* ── Özet kartlar ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
        {[
          { label: "Toplam Veri Seti", value: datasets.length,         color: "var(--accent)" },
          { label: "Atanmış Vaka",     value: totalCases,               color: "var(--success)" },
          { label: "Seçili Veri Seti", value: selectedDs?.name ?? "—", color: "var(--text-2)", small: true },
        ].map(({ label, value, color, small }) => (
          <div key={label} className="stat-card">
            <div className="stat-label">{label}</div>
            <div className="stat-value" style={{ color, fontSize: small ? 18 : 28, letterSpacing: small ? 0 : -0.5 }}>
              {value}
            </div>
          </div>
        ))}
      </div>

      {/* ── Oluşturma formu (toggle) ── */}
      {showForm && (
        <section className="card">
          <h2 style={{ marginTop: 0, marginBottom: 16, fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>
            Yeni Veri Seti Oluştur
          </h2>
          <form onSubmit={handleCreate}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div className="form-group">
                <label className="form-label">Ad *</label>
                <input
                  className="form-input"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="örn. Kardiyoloji Vakaları"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Kaynak</label>
                <select
                  className="form-input"
                  value={source}
                  onChange={e => setSource(e.target.value)}
                >
                  {SOURCE_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Açıklama</label>
                <input
                  className="form-input"
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  placeholder="Kısa açıklama (opsiyonel)"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Notlar</label>
                <input
                  className="form-input"
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  placeholder="Serbest metin (opsiyonel)"
                />
              </div>
            </div>
            {formError && (
              <div className="alert alert-danger" style={{ marginTop: 12 }}>{formError}</div>
            )}
            <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={createMutation.isPending}
              >
                {createMutation.isPending ? <><span className="spinner" />Oluşturuluyor…</> : "Oluştur"}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>
                Vazgeç
              </button>
            </div>
          </form>
        </section>
      )}

      {/* ── Dataset listesi ── */}
      <section className="card" style={{ padding: 0 }}>
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border-1)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h2 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>
            Veri Setleri
            {datasets.length > 0 && (
              <span style={{ marginLeft: 8, fontSize: 12, fontWeight: 600, color: "var(--text-3)" }}>
                {datasets.length} adet
              </span>
            )}
          </h2>
          {selectedId && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setSelectedId(null)}
            >
              Seçimi kaldır
            </button>
          )}
        </div>

        {isLoading ? (
          <div className="empty-state">
            <span className="spinner" style={{ width: 24, height: 24 }} />
          </div>
        ) : datasets.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🗂️</div>
            <div className="empty-state-title">Henüz veri seti yok</div>
            <div className="empty-state-sub">Yukarıdaki "Yeni Veri Seti" butonuyla oluşturun.</div>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Ad</th>
                <th>Kaynak</th>
                <th>Açıklama</th>
                <th>Vaka</th>
                <th>Oluşturulma</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {datasets.map(ds => {
                const isSelected = selectedId === ds.id;
                return (
                  <tr
                    key={ds.id}
                    onClick={() => setSelectedId(isSelected ? null : ds.id)}
                    style={{
                      cursor: "pointer",
                      outline: isSelected ? `2px solid var(--accent-border)` : "none",
                      outlineOffset: -1,
                      background: isSelected ? "var(--accent-muted)" : undefined,
                    }}
                  >
                    <td>
                      <span style={{ fontWeight: 700, color: "var(--text-1)" }}>{ds.name}</span>
                    </td>
                    <td>
                      <span
                        className="badge"
                        style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-2)", color: "var(--text-2)" }}
                      >
                        {ds.source}
                      </span>
                    </td>
                    <td style={{ color: "var(--text-3)", fontSize: 12 }}>
                      {ds.description ?? <span style={{ fontStyle: "italic" }}>—</span>}
                    </td>
                    <td>
                      <span style={{
                        fontWeight: 700,
                        color: ds.case_count > 0 ? "var(--success)" : "var(--text-3)",
                      }}>
                        {ds.case_count}
                      </span>
                    </td>
                    <td style={{ fontSize: 11, color: "var(--text-3)" }}>
                      {new Date(ds.created_at).toLocaleDateString("tr-TR")}
                    </td>
                    <td>
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={e => { e.stopPropagation(); deleteMutation.mutate(ds.id); }}
                        disabled={deleteMutation.isPending}
                      >
                        Sil
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>

      {/* ── Seçili dataset'in vakaları ── */}
      {selectedId && selectedDs && (
        <section className="card" style={{ padding: 0 }}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border-1)" }}>
            <h2 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>
              Vakalar
              <span style={{ marginLeft: 8, color: "var(--accent)", fontWeight: 600 }}>
                {selectedDs.name}
              </span>
              {cases.length > 0 && (
                <span style={{ marginLeft: 8, fontSize: 12, color: "var(--text-3)", fontWeight: 400 }}>
                  {cases.length} vaka
                </span>
              )}
            </h2>
            <p style={{ marginTop: 4, fontSize: 12, color: "var(--text-3)" }}>
              Bir vakayı bu veri setinden çıkarmak için "Kaldır" butonunu kullanın (vaka silinmez, sadece set ataması kaldırılır).
            </p>
          </div>

          {casesLoading ? (
            <div className="empty-state"><span className="spinner" style={{ width: 24, height: 24 }} /></div>
          ) : cases.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📂</div>
              <div className="empty-state-title">Bu veri setinde vaka yok</div>
              <div className="empty-state-sub">
                Doktor yükleme ekranında veya vaka detayında bu veri setini seçin.
              </div>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Etiket</th>
                  <th>Durum</th>
                  <th>İnceleme</th>
                  <th>Dilim</th>
                  <th>Yüklenme</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {cases.map(c => {
                  const rb = REVIEW_BADGE[c.review_status] ?? REVIEW_BADGE.unreviewed;
                  return (
                    <tr key={c.id}>
                      <td style={{ fontWeight: 600, color: "var(--text-1)" }}>
                        {c.case_label ?? <span style={{ color: "var(--text-3)", fontStyle: "italic" }}>{c.id.slice(0, 8)}</span>}
                      </td>
                      <td>
                        <span
                          className="badge"
                          style={{
                            background: c.status === "ready" ? "var(--success-muted)" : "var(--bg-elevated)",
                            color: c.status === "ready" ? "var(--success)" : "var(--text-3)",
                            border: "1px solid transparent",
                          }}
                        >
                          {c.status}
                        </span>
                      </td>
                      <td>
                        <span
                          className="badge"
                          style={{ background: rb.bg, color: rb.color, border: "1px solid transparent" }}
                        >
                          {REVIEW_TR[c.review_status] ?? c.review_status}
                        </span>
                      </td>
                      <td style={{ color: "var(--text-3)" }}>{c.n_slices ?? "—"}</td>
                      <td style={{ fontSize: 11, color: "var(--text-3)" }}>
                        {new Date(c.created_at).toLocaleDateString("tr-TR")}
                      </td>
                      <td>
                        <div style={{ display: "flex", gap: 6 }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => unassignMutation.mutate(c.id)}
                            disabled={unassignMutation.isPending || deleteCaseMutation.isPending}
                          >
                            Kaldır
                          </button>
                          <button
                            className="btn btn-danger btn-sm"
                            onClick={() => {
                              if (window.confirm(`"${c.case_label ?? c.id.slice(0, 8)}" vakası kalıcı olarak silinecek. Emin misiniz?`))
                                deleteCaseMutation.mutate(c.id);
                            }}
                            disabled={deleteCaseMutation.isPending || unassignMutation.isPending}
                          >
                            Sil
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>
      )}
    </div>
  );
}
