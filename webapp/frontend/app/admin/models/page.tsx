"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api-client";
import { getCurrentRole } from "@/lib/auth";
import { RoleGuard } from "@/components/common/RoleGuard";
import type { ModelVersionDto } from "@/lib/types";

const ARCHITECTURE_LABELS: Record<string, string> = {
  yolo_det: "YOLO Detection", yolo_seg: "YOLO Segmentation", rfdetr: "RF-DETR",
  dfine: "D-FINE", nnunet: "nnU-Net", mednext: "MedNeXt",
  organ_bag_transformer: "OrganBagTransformer", cls_timm: "Sınıflandırma (timm)",
};

const STATUS_STYLE: Record<string, React.CSSProperties> = {
  active: { background: "#16a34a22", color: "#4ade80" },
  inactive: { background: "#71717a22", color: "#a1a1aa" },
  archived: { background: "#dc262622", color: "#f87171" },
};

function AdminGuard({ children }: { children: React.ReactNode }) {
  const role = typeof window !== "undefined" ? getCurrentRole() : null;
  if (role !== "admin") return <p style={{ padding: 24, color: "#f87171" }}>Bu sayfa sadece admin'e açıktır.</p>;
  return <>{children}</>;
}

export default function AdminModelsPage() {
  const queryClient = useQueryClient();
  const [registerError, setRegisterError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [formName, setFormName] = useState("");
  const [formArch, setFormArch] = useState("yolo_det");
  const [formRunMode, setFormRunMode] = useState("comparison");
  const [formBaseWeights, setFormBaseWeights] = useState("");
  const [formOutputs, setFormOutputs] = useState(
    JSON.stringify([{ output_type: "bbox", class_set: null, postprocess_config: { conf_threshold: 0.2, min_slice_run: 3 } }], null, 2)
  );

  const { data: models, isLoading } = useQuery({
    queryKey: ["models"],
    queryFn: () => api.get<ModelVersionDto[]>("/models"),
  });

  const activateMutation = useMutation({
    mutationFn: (id: string) => api.post(`/models/${id}/activate`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["models"] }),
  });
  const deactivateMutation = useMutation({
    mutationFn: (id: string) => api.post(`/models/${id}/deactivate`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["models"] }),
  });

  const registerMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Ağırlık dosyası (.pt) seçin");
      const form = new FormData();
      form.append("file", file);
      form.append("name", formName);
      form.append("architecture", formArch);
      form.append("run_mode", formRunMode);
      if (formBaseWeights) form.append("base_weights", formBaseWeights);
      form.append("outputs_json", formOutputs);
      return api.postForm("/models/register", form);
    },
    onSuccess: () => {
      setFile(null); setFormName(""); setRegisterError(null);
      queryClient.invalidateQueries({ queryKey: ["models"] });
    },
    onError: (err: Error) => setRegisterError(err instanceof ApiError ? err.message : err.message),
  });

  return (
    <RoleGuard>
      <AdminGuard>
        <div style={{ display: "grid", gap: 24, maxWidth: 900, padding: 24 }}>
          <h1 style={{ margin: 0 }}>Model Registry</h1>

          {/* Model listesi */}
          <section className="card">
            <h2 style={{ marginTop: 0 }}>Kayıtlı modeller</h2>
            {isLoading && <p>Yükleniyor...</p>}
            {models?.length === 0 && <p style={{ color: "#9aa0ab" }}>Henüz kayıtlı model yok.</p>}
            {models && models.length > 0 && (
              <table>
                <thead>
                  <tr><th>Ad</th><th>Mimari</th><th>Mod</th><th>Durum</th><th>Çıktılar</th><th></th></tr>
                </thead>
                <tbody>
                  {models.map((m) => (
                    <tr key={m.id}>
                      <td><strong>{m.name}</strong><br /><span style={{ fontSize: 11, color: "#9aa0ab" }}>{m.base_weights}</span></td>
                      <td>{ARCHITECTURE_LABELS[m.architecture] ?? m.architecture}</td>
                      <td><span className="badge" style={{ background: m.run_mode === "default" ? "#1d4ed822" : "#71717a22", color: m.run_mode === "default" ? "#93c5fd" : "#a1a1aa" }}>{m.run_mode}</span></td>
                      <td><span className="badge" style={STATUS_STYLE[m.status] ?? {}}>{m.status}</span></td>
                      <td style={{ fontSize: 12 }}>{m.outputs.map(o => o.output_type).join(", ")}</td>
                      <td>
                        <div style={{ display: "flex", gap: 6 }}>
                          {m.status !== "active" && (
                            <button className="btn-secondary" style={{ padding: "3px 8px", fontSize: 12, color: "#4ade80", borderColor: "#166534" }} onClick={() => activateMutation.mutate(m.id)}>Aktifleştir</button>
                          )}
                          {m.status === "active" && (
                            <button className="btn-secondary" style={{ padding: "3px 8px", fontSize: 12 }} onClick={() => deactivateMutation.mutate(m.id)}>Devre dışı</button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          {/* Yeni model kaydet */}
          <section className="card">
            <h2 style={{ marginTop: 0 }}>Yeni model kaydet (.pt yükle)</h2>
            <form
              onSubmit={(e) => { e.preventDefault(); registerMutation.mutate(); }}
              style={{ display: "grid", gap: 12 }}
            >
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <label style={{ flex: 1, minWidth: 200 }}>
                  <span style={{ display: "block", fontSize: 13, marginBottom: 4 }}>Model adı</span>
                  <input value={formName} onChange={e => setFormName(e.target.value)} required
                    style={{ width: "100%", padding: 6, borderRadius: 6, border: "1px solid #3a3e48", background: "#0f1115", color: "#e6e6e6" }} />
                </label>
                <label style={{ flex: 1, minWidth: 160 }}>
                  <span style={{ display: "block", fontSize: 13, marginBottom: 4 }}>Mimari</span>
                  <select value={formArch} onChange={e => setFormArch(e.target.value)}
                    style={{ width: "100%", padding: 6, borderRadius: 6, border: "1px solid #3a3e48", background: "#0f1115", color: "#e6e6e6" }}>
                    {Object.entries(ARCHITECTURE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </label>
                <label style={{ flex: 1, minWidth: 140 }}>
                  <span style={{ display: "block", fontSize: 13, marginBottom: 4 }}>Çalışma modu</span>
                  <select value={formRunMode} onChange={e => setFormRunMode(e.target.value)}
                    style={{ width: "100%", padding: 6, borderRadius: 6, border: "1px solid #3a3e48", background: "#0f1115", color: "#e6e6e6" }}>
                    <option value="default">default (otomatik)</option>
                    <option value="comparison">comparison (isteğe bağlı)</option>
                  </select>
                </label>
              </div>
              <label>
                <span style={{ display: "block", fontSize: 13, marginBottom: 4 }}>Temel ağırlık adı (opsiyonel, örn. yolov8s.pt)</span>
                <input value={formBaseWeights} onChange={e => setFormBaseWeights(e.target.value)}
                  style={{ width: "100%", padding: 6, borderRadius: 6, border: "1px solid #3a3e48", background: "#0f1115", color: "#e6e6e6" }} />
              </label>
              <label>
                <span style={{ display: "block", fontSize: 13, marginBottom: 4 }}>
                  model_outputs (JSON — bkz. plan Bölüm 2: output_type, class_set, postprocess_config)
                </span>
                <textarea value={formOutputs} onChange={e => setFormOutputs(e.target.value)} rows={6}
                  style={{ width: "100%", padding: 6, borderRadius: 6, border: "1px solid #3a3e48", background: "#0f1115", color: "#e6e6e6", fontFamily: "monospace", fontSize: 12 }} />
              </label>
              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                <input type="file" accept=".pt,.pth,.onnx" onChange={e => setFile(e.target.files?.[0] ?? null)} />
                <button type="submit" className="btn-primary" disabled={!file || !formName || registerMutation.isPending}>
                  {registerMutation.isPending ? "Kaydediliyor..." : "Kaydet"}
                </button>
              </div>
              {registerError && <p style={{ color: "#f87171" }}>{registerError}</p>}
            </form>
          </section>
        </div>
      </AdminGuard>
    </RoleGuard>
  );
}
