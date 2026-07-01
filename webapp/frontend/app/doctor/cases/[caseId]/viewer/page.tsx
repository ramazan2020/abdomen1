"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, fetchSlicePngBlobUrl } from "@/lib/api-client";
import { AnnotationDto, SliceInfo } from "@/lib/types";
import { SliceScrubber } from "@/components/viewer/SliceScrubber";
import { ClassPicker } from "@/components/viewer/ClassPicker";
import type { Tool } from "@/components/viewer/AnnotationOverlay";

// Konva tarayıcı-only çalışır (canvas API) — SSR'da render edilemez.
const AnnotationOverlay = dynamic(
  () => import("@/components/viewer/AnnotationOverlay").then((m) => m.AnnotationOverlay),
  { ssr: false }
);

export default function ViewerPage({ params }: { params: { caseId: string } }) {
  const { caseId } = params;
  const queryClient = useQueryClient();

  const [z, setZ] = useState(0);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [tool, setTool] = useState<Tool>("select");
  const [activeClassId, setActiveClassId] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: slices } = useQuery({
    queryKey: ["slices", caseId],
    queryFn: () => api.get<SliceInfo[]>(`/cases/${caseId}/slices`),
  });

  const currentImageId = slices && slices.length > 0 ? slices[z]?.image_id : undefined;

  const { data: annotations } = useQuery({
    queryKey: ["annotations", caseId, currentImageId],
    queryFn: () =>
      api.get<AnnotationDto[]>(`/cases/${caseId}/annotations?image_id=${currentImageId}`),
    enabled: currentImageId !== undefined,
  });

  useEffect(() => {
    if (currentImageId === undefined) return;
    let revoked = false;
    let url: string | null = null;
    fetchSlicePngBlobUrl(caseId, currentImageId).then((u) => {
      if (revoked) {
        URL.revokeObjectURL(u);
        return;
      }
      url = u;
      setImageUrl(u);
    });
    return () => {
      revoked = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [caseId, currentImageId]);

  const invalidateAnnotations = () =>
    queryClient.invalidateQueries({ queryKey: ["annotations", caseId, currentImageId] });

  const createMutation = useMutation({
    mutationFn: (vars: { geometryType: "bbox" | "polygon"; geometry: any }) =>
      api.post(`/cases/${caseId}/annotations`, {
        image_id: currentImageId,
        class_type: "lesion",
        class_id: activeClassId,
        geometry_type: vars.geometryType,
        geometry: vars.geometry,
      }),
    onSuccess: invalidateAnnotations,
  });

  const updateMutation = useMutation({
    mutationFn: (vars: { id: string; geometry: any }) =>
      api.put(`/annotations/${vars.id}`, { geometry: vars.geometry }),
    onSuccess: invalidateAnnotations,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.del(`/annotations/${id}`),
    onSuccess: () => {
      setSelectedId(null);
      invalidateAnnotations();
    },
  });

  const acceptMutation = useMutation({
    mutationFn: (id: string) => api.post(`/annotations/${id}/accept`),
    onSuccess: invalidateAnnotations,
  });

  if (!slices) return <p style={{ padding: 24 }}>Yükleniyor...</p>;

  const selected = annotations?.find((a) => a.id === selectedId) ?? null;

  return (
    <div>
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 24px", borderBottom: "1px solid #2a2e38" }}>
        <Link href={`/doctor/cases/${caseId}`} style={{ fontSize: 13 }}>
          ← Vaka detayı
        </Link>
        <div style={{ display: "flex", gap: 8 }}>
          <button className={`btn-secondary`} style={{ background: tool === "select" ? "#3b82f6" : undefined }} onClick={() => setTool("select")}>
            Seç/Düzenle
          </button>
          <button className="btn-secondary" style={{ background: tool === "bbox" ? "#3b82f6" : undefined }} onClick={() => setTool("bbox")}>
            Kutu (bbox)
          </button>
          <button className="btn-secondary" style={{ background: tool === "polygon" ? "#3b82f6" : undefined }} onClick={() => setTool("polygon")}>
            Poligon
          </button>
          <ClassPicker value={activeClassId} onChange={setActiveClassId} />
        </div>
      </header>

      <div style={{ display: "flex", gap: 16, padding: 24 }}>
        <div style={{ flex: 1 }}>
          {imageUrl ? (
            <AnnotationOverlay
              imageUrl={imageUrl}
              annotations={annotations ?? []}
              tool={tool}
              activeClassId={activeClassId}
              selectedId={selectedId}
              onSelect={setSelectedId}
              onCreate={(geometryType, geometry) => createMutation.mutate({ geometryType, geometry })}
              onUpdate={(id, geometry) => updateMutation.mutate({ id, geometry })}
            />
          ) : (
            <p>Dilim yükleniyor...</p>
          )}

          <div style={{ marginTop: 16 }}>
            <SliceScrubber value={z} max={slices.length} onChange={setZ} />
          </div>
        </div>

        <aside className="card" style={{ width: 280 }}>
          <h3 style={{ marginTop: 0 }}>Bu dilimdeki annotasyonlar</h3>
          {(annotations ?? []).filter((a) => a.status === "active").length === 0 && (
            <p style={{ color: "#9aa0ab", fontSize: 13 }}>Bu dilimde annotasyon yok.</p>
          )}
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 6 }}>
            {(annotations ?? [])
              .filter((a) => a.status === "active")
              .map((a) => (
                <li
                  key={a.id}
                  onClick={() => setSelectedId(a.id)}
                  style={{
                    padding: 8,
                    borderRadius: 6,
                    cursor: "pointer",
                    background: a.id === selectedId ? "#2a2e38" : "transparent",
                    border: "1px solid #2a2e38",
                    fontSize: 13,
                  }}
                >
                  <div>{a.geometry_type} · sınıf {a.class_id}</div>
                  <div style={{ color: "#9aa0ab" }}>
                    {a.source}
                    {a.confidence != null ? ` (${(a.confidence * 100).toFixed(0)}%)` : ""}
                  </div>
                </li>
              ))}
          </ul>

          {selected && (
            <div style={{ marginTop: 16, display: "grid", gap: 8 }}>
              {selected.source === "prediction" && (
                <button className="btn-secondary" onClick={() => acceptMutation.mutate(selected.id)}>
                  Tahmini kabul et
                </button>
              )}
              <button className="btn-secondary" style={{ color: "#f87171" }} onClick={() => deleteMutation.mutate(selected.id)}>
                Sil
              </button>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
