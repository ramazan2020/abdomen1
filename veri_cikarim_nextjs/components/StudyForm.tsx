"use client";
import { useState } from "react";
import type { Study } from "@/lib/db";

type PerfKey = "AUC" | "ACC" | "SEN" | "SPE" | "F1" | "DICE" | "IOU" | "MAP";
type PerfFields = Record<PerfKey, string>;

const PERF_KEYS: PerfKey[] = ["AUC", "ACC", "SEN", "SPE", "F1", "DICE", "IOU", "MAP"];

function parsePerfFields(p: string | null): PerfFields {
  const empty = Object.fromEntries(PERF_KEYS.map((k) => [k, ""])) as PerfFields;
  if (!p) return empty;
  try {
    const obj = JSON.parse(p);
    return { ...empty, ...(typeof obj === "object" ? obj : {}) };
  } catch {
    return empty;
  }
}

function serializePerf(pf: PerfFields): string | null {
  const out: Partial<PerfFields> = {};
  for (const k of PERF_KEYS) {
    if (pf[k].trim()) out[k] = pf[k].trim();
  }
  return Object.keys(out).length ? JSON.stringify(out) : null;
}

const EMPTY: Omit<Study, "id"> = {
  ref_no: 0, first_author: "", authors_full: "", year: 2024, title: "",
  venue: "", country: "", pathology: "", pathology_code: "", modality: "CT",
  dataset_name: "", dataset_access: "Özel", patient_count: null, image_count: null,
  task: "", model: "", method_detail: "", summary: "", performance: null,
  ext_validation: "Yok", radiologist_comparison: "Yok",
  open_code: "Yok", open_data: "Yok", code_url: "",
  depth: "Makale", limitations: "", doi_url: "",
};

const TABS = ["Temel Bilgiler", "Yöntem & Veri", "Sonuç & Doğrulama"];

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="form-field">
      <label className="form-label">{label}</label>
      {children}
    </div>
  );
}

export default function StudyForm({
  study,
  onClose,
  onSaved,
}: {
  study?: Study;
  onClose: () => void;
  onSaved: (s: Study) => void;
}) {
  const isEdit = !!study?.id;
  const [form, setForm] = useState<Omit<Study, "id">>(study ? { ...study } : { ...EMPTY });
  const [perf, setPerf] = useState<PerfFields>(parsePerfFields(study?.performance ?? null));
  const [tab, setTab] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set<K extends keyof Study>(k: K, v: Study[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function sp(k: PerfKey, v: string) {
    setPerf((p) => ({ ...p, [k]: v }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    const body = { ...form, performance: serializePerf(perf) };
    try {
      const url = isEdit ? `/api/studies/${study!.id}` : "/api/studies";
      const res = await fetch(url, {
        method: isEdit ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Sunucu hatası");
      onSaved(data as Study);
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  const varYok = (
    <>
      <option>Yok</option>
      <option>Var</option>
    </>
  );

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal"
        style={{ maxWidth: 860 }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Başlık */}
        <div className="modal-head">
          <div>
            <h2 style={{ fontSize: 15 }}>
              {isEdit
                ? `Düzenle — [${study!.ref_no}] ${study!.title}`
                : "Yeni Çalışma Ekle"}
            </h2>
          </div>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        {/* Sekmeler */}
        <div style={{ padding: "6px 20px 0" }}>
          <div className="tabs" style={{ margin: 0 }}>
            {TABS.map((t, i) => (
              <button
                key={i}
                type="button"
                className={`tab ${tab === i ? "active" : ""}`}
                onClick={() => setTab(i)}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={submit}>
          <div className="modal-body">

            {/* ── TAB 0: Temel Bilgiler ── */}
            {tab === 0 && (
              <>
                <p className="form-section">Bibliyografik</p>
                <div className="form-grid" style={{ marginBottom: 12 }}>
                  <Field label="Atıf No (ref_no) *">
                    <input
                      className="form-input"
                      type="number"
                      value={form.ref_no ?? ""}
                      onChange={(e) => set("ref_no", Number(e.target.value))}
                      required
                    />
                  </Field>
                  <Field label="Yıl">
                    <input
                      className="form-input"
                      type="number"
                      min={2000}
                      max={2030}
                      value={form.year ?? ""}
                      onChange={(e) => set("year", e.target.value === "" ? null : Number(e.target.value))}
                    />
                  </Field>
                </div>

                <div className="form-field" style={{ marginBottom: 12 }}>
                  <Field label="Başlık *">
                    <input
                      className="form-input"
                      value={form.title ?? ""}
                      onChange={(e) => set("title", e.target.value)}
                      required
                    />
                  </Field>
                </div>

                <div className="form-grid" style={{ marginBottom: 12 }}>
                  <Field label="İlk Yazar">
                    <input
                      className="form-input"
                      value={form.first_author ?? ""}
                      onChange={(e) => set("first_author", e.target.value)}
                    />
                  </Field>
                  <Field label="Ülke">
                    <input
                      className="form-input"
                      value={form.country ?? ""}
                      onChange={(e) => set("country", e.target.value)}
                    />
                  </Field>
                </div>

                <div className="form-field" style={{ marginBottom: 12 }}>
                  <Field label="Tüm Yazarlar">
                    <textarea
                      className="form-input"
                      rows={2}
                      value={form.authors_full ?? ""}
                      onChange={(e) => set("authors_full", e.target.value)}
                    />
                  </Field>
                </div>

                <div className="form-grid" style={{ marginBottom: 12 }}>
                  <Field label="Dergi / Konferans">
                    <input
                      className="form-input"
                      value={form.venue ?? ""}
                      onChange={(e) => set("venue", e.target.value)}
                    />
                  </Field>
                  <Field label="Çalışma Türü">
                    <select
                      className="form-input"
                      value={form.depth ?? ""}
                      onChange={(e) => set("depth", e.target.value)}
                    >
                      <option value="">—</option>
                      <option>Makale</option>
                      <option>Bildiri</option>
                      <option>Ön baskı</option>
                    </select>
                  </Field>
                </div>

                <div className="form-field" style={{ marginBottom: 12 }}>
                  <Field label="DOI / URL">
                    <input
                      className="form-input"
                      value={form.doi_url ?? ""}
                      onChange={(e) => set("doi_url", e.target.value)}
                      placeholder="https://doi.org/…"
                    />
                  </Field>
                </div>

                <p className="form-section">Patoloji</p>
                <div className="form-grid">
                  <Field label="Patoloji Kodu">
                    <select
                      className="form-input"
                      value={form.pathology_code ?? ""}
                      onChange={(e) => set("pathology_code", e.target.value)}
                    >
                      <option value="">—</option>
                      {["URO", "AAA/AORT", "PAN", "APP", "CHO", "DIV", "MIX", "APP+DIV"].map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Patoloji Adı">
                    <input
                      className="form-input"
                      value={form.pathology ?? ""}
                      onChange={(e) => set("pathology", e.target.value)}
                      placeholder="Ürolitiyazis, Apandisit …"
                    />
                  </Field>
                </div>
              </>
            )}

            {/* ── TAB 1: Yöntem & Veri ── */}
            {tab === 1 && (
              <>
                <p className="form-section">Görüntüleme & Veri Seti</p>
                <div className="form-grid" style={{ marginBottom: 12 }}>
                  <Field label="Modalite">
                    <input
                      className="form-input"
                      value={form.modality ?? ""}
                      onChange={(e) => set("modality", e.target.value)}
                      placeholder="CT / NCCT / CECT / CTA …"
                    />
                  </Field>
                  <Field label="Veri Seti Erişimi">
                    <select
                      className="form-input"
                      value={form.dataset_access ?? ""}
                      onChange={(e) => set("dataset_access", e.target.value)}
                    >
                      <option value="">—</option>
                      <option>Özel</option>
                      <option>Halka açık</option>
                    </select>
                  </Field>
                </div>

                <div className="form-field" style={{ marginBottom: 12 }}>
                  <Field label="Veri Seti Adı">
                    <input
                      className="form-input"
                      value={form.dataset_name ?? ""}
                      onChange={(e) => set("dataset_name", e.target.value)}
                    />
                  </Field>
                </div>

                <div className="form-grid" style={{ marginBottom: 12 }}>
                  <Field label="Hasta Sayısı">
                    <input
                      className="form-input"
                      type="number"
                      min={0}
                      value={form.patient_count ?? ""}
                      onChange={(e) =>
                        set("patient_count", e.target.value === "" ? null : Number(e.target.value))
                      }
                    />
                  </Field>
                  <Field label="Görüntü / BT Serisi Sayısı">
                    <input
                      className="form-input"
                      type="number"
                      min={0}
                      value={form.image_count ?? ""}
                      onChange={(e) =>
                        set("image_count", e.target.value === "" ? null : Number(e.target.value))
                      }
                    />
                  </Field>
                </div>

                <p className="form-section">Yöntem & Model</p>
                <div className="form-grid" style={{ marginBottom: 12 }}>
                  <Field label="Görev (TASK)">
                    <input
                      className="form-input"
                      value={form.task ?? ""}
                      onChange={(e) => set("task", e.target.value)}
                      placeholder="SEG / DET / CLS / PRED …"
                    />
                  </Field>
                  <Field label="Model Ailesi (MFAM)">
                    <input
                      className="form-input"
                      value={form.model ?? ""}
                      onChange={(e) => set("model", e.target.value)}
                      placeholder="CNN / U-Net / Transformer …"
                    />
                  </Field>
                </div>

                <div className="form-field">
                  <Field label="Spesifik Mimari">
                    <input
                      className="form-input"
                      value={form.method_detail ?? ""}
                      onChange={(e) => set("method_detail", e.target.value)}
                      placeholder="ResNet-50, nnU-Net v2 …"
                    />
                  </Field>
                </div>
              </>
            )}

            {/* ── TAB 2: Sonuç & Doğrulama ── */}
            {tab === 2 && (
              <>
                <p className="form-section">Performans Ölçütleri</p>
                <div className="form-grid-4" style={{ marginBottom: 12 }}>
                  {PERF_KEYS.map((k) => (
                    <Field key={k} label={k}>
                      <input
                        className="form-input"
                        value={perf[k]}
                        onChange={(e) => sp(k, e.target.value)}
                        placeholder="0.00"
                      />
                    </Field>
                  ))}
                </div>

                <p className="form-section">Doğrulama</p>
                <div className="form-grid" style={{ marginBottom: 12 }}>
                  <Field label="Harici Doğrulama">
                    <select
                      className="form-input"
                      value={form.ext_validation ?? "Yok"}
                      onChange={(e) => set("ext_validation", e.target.value)}
                    >
                      {varYok}
                    </select>
                  </Field>
                  <Field label="Radyolog Karşılaştırması">
                    <select
                      className="form-input"
                      value={form.radiologist_comparison ?? "Yok"}
                      onChange={(e) => set("radiologist_comparison", e.target.value)}
                    >
                      {varYok}
                    </select>
                  </Field>
                </div>

                <p className="form-section">Açık Bilim</p>
                <div className="form-grid" style={{ marginBottom: 12 }}>
                  <Field label="Açık Kod">
                    <select
                      className="form-input"
                      value={form.open_code ?? "Yok"}
                      onChange={(e) => set("open_code", e.target.value)}
                    >
                      {varYok}
                    </select>
                  </Field>
                  <Field label="Açık Veri">
                    <select
                      className="form-input"
                      value={form.open_data ?? "Yok"}
                      onChange={(e) => set("open_data", e.target.value)}
                    >
                      {varYok}
                    </select>
                  </Field>
                </div>

                <div className="form-field" style={{ marginBottom: 12 }}>
                  <Field label="Kod / Veri URL">
                    <input
                      className="form-input"
                      value={form.code_url ?? ""}
                      onChange={(e) => set("code_url", e.target.value)}
                      placeholder="https://github.com/…"
                    />
                  </Field>
                </div>

                <p className="form-section">Özet & Sınırlılıklar</p>
                <div className="form-field" style={{ marginBottom: 12 }}>
                  <Field label="Ana Bulgular">
                    <textarea
                      className="form-input"
                      rows={3}
                      value={form.summary ?? ""}
                      onChange={(e) => set("summary", e.target.value)}
                    />
                  </Field>
                </div>

                <div className="form-field">
                  <Field label="Sınırlılıklar">
                    <textarea
                      className="form-input"
                      rows={2}
                      value={form.limitations ?? ""}
                      onChange={(e) => set("limitations", e.target.value)}
                    />
                  </Field>
                </div>
              </>
            )}

            {error && (
              <p style={{ color: "#b91c1c", marginTop: 12, fontSize: 13 }}>
                Hata: {error}
              </p>
            )}
          </div>

          {/* Kaydet / İptal */}
          <div
            style={{
              padding: "12px 20px 18px",
              borderTop: "1px solid #eef2f7",
              display: "flex",
              justifyContent: "flex-end",
              gap: 10,
            }}
          >
            <button type="button" className="btn-detay" onClick={onClose}>
              İptal
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? "Kaydediliyor…" : isEdit ? "Güncelle" : "Kaydet"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
