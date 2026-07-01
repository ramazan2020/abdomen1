"use client";

import { useEffect, useRef, useState } from "react";
import { Stage, Layer, Image as KonvaImage, Rect, Line, Circle, Transformer } from "react-konva";
import Konva from "konva";
import { AnnotationDto, CLASS_COLORS } from "@/lib/types";

export type Tool = "select" | "bbox" | "polygon";

interface Props {
  imageUrl: string;
  annotations: AnnotationDto[];
  tool: Tool;
  activeClassId: number;
  onCreate: (geometryType: "bbox" | "polygon", geometry: any) => void;
  onUpdate: (id: string, geometry: any) => void;
  onSelect: (id: string | null) => void;
  selectedId: string | null;
}

function colorFor(ann: AnnotationDto): string {
  return CLASS_COLORS[ann.class_id % CLASS_COLORS.length];
}

function opacityFor(ann: AnnotationDto): number {
  if (ann.source === "prediction") {
    return ann.confidence != null ? Math.max(0.35, Math.min(1, ann.confidence)) : 0.6;
  }
  return 1;
}

export function AnnotationOverlay({
  imageUrl,
  annotations,
  tool,
  activeClassId,
  onCreate,
  onUpdate,
  onSelect,
  selectedId,
}: Props) {
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  const [size, setSize] = useState({ width: 512, height: 512 });
  const stageRef = useRef<Konva.Stage>(null);
  const trRef = useRef<Konva.Transformer>(null);
  const shapeRefs = useRef<Record<string, Konva.Node | null>>({});

  // Çizim sırasında geçici durum
  const [draftRect, setDraftRect] = useState<{ x1: number; y1: number; x2: number; y2: number } | null>(null);
  const [draftPolygon, setDraftPolygon] = useState<number[][]>([]);
  const isDrawingRect = useRef(false);

  useEffect(() => {
    const img = new window.Image();
    img.onload = () => {
      setImage(img);
      setSize({ width: img.naturalWidth, height: img.naturalHeight });
    };
    img.src = imageUrl;
  }, [imageUrl]);

  useEffect(() => {
    if (!trRef.current) return;
    if (selectedId && shapeRefs.current[selectedId]) {
      trRef.current.nodes([shapeRefs.current[selectedId]!]);
      trRef.current.getLayer()?.batchDraw();
    } else {
      trRef.current.nodes([]);
    }
  }, [selectedId, annotations]);

  function getPointerPos() {
    const stage = stageRef.current;
    if (!stage) return null;
    return stage.getPointerPosition();
  }

  function handleStageMouseDown(e: Konva.KonvaEventObject<MouseEvent>) {
    const clickedOnEmpty = e.target === e.target.getStage() || e.target.id() === "base-image";
    if (tool === "select") {
      if (clickedOnEmpty) onSelect(null);
      return;
    }
    if (tool === "bbox" && clickedOnEmpty) {
      const pos = getPointerPos();
      if (!pos) return;
      isDrawingRect.current = true;
      setDraftRect({ x1: pos.x, y1: pos.y, x2: pos.x, y2: pos.y });
    }
  }

  function handleStageMouseMove() {
    if (tool === "bbox" && isDrawingRect.current && draftRect) {
      const pos = getPointerPos();
      if (!pos) return;
      setDraftRect({ ...draftRect, x2: pos.x, y2: pos.y });
    }
  }

  function handleStageMouseUp() {
    if (tool === "bbox" && isDrawingRect.current && draftRect) {
      isDrawingRect.current = false;
      const x1 = Math.min(draftRect.x1, draftRect.x2);
      const y1 = Math.min(draftRect.y1, draftRect.y2);
      const x2 = Math.max(draftRect.x1, draftRect.x2);
      const y2 = Math.max(draftRect.y1, draftRect.y2);
      setDraftRect(null);
      if (x2 - x1 > 4 && y2 - y1 > 4) {
        onCreate("bbox", { x1, y1, x2, y2 });
      }
    }
  }

  function handleStageClick() {
    if (tool !== "polygon") return;
    const pos = getPointerPos();
    if (!pos) return;
    setDraftPolygon((prev) => [...prev, [pos.x, pos.y]]);
  }

  function handleStageDblClick() {
    if (tool !== "polygon") return;
    if (draftPolygon.length >= 3) {
      onCreate("polygon", { points: draftPolygon });
    }
    setDraftPolygon([]);
  }

  return (
    <Stage
      width={size.width}
      height={size.height}
      ref={stageRef}
      onMouseDown={handleStageMouseDown}
      onMouseMove={handleStageMouseMove}
      onMouseUp={handleStageMouseUp}
      onClick={handleStageClick}
      onDblClick={handleStageDblClick}
      style={{ background: "#000", cursor: tool === "select" ? "default" : "crosshair" }}
    >
      <Layer>
        {image && <KonvaImage id="base-image" image={image} width={size.width} height={size.height} />}
      </Layer>

      <Layer>
        {annotations
          .filter((a) => a.status === "active")
          .map((ann) => {
            const color = colorFor(ann);
            const opacity = opacityFor(ann);
            const isSelected = ann.id === selectedId;

            if (ann.geometry_type === "bbox") {
              const g = ann.geometry as { x1: number; y1: number; x2: number; y2: number };
              return (
                <Rect
                  key={ann.id}
                  ref={(node) => {
                    shapeRefs.current[ann.id] = node;
                  }}
                  x={g.x1}
                  y={g.y1}
                  width={g.x2 - g.x1}
                  height={g.y2 - g.y1}
                  stroke={color}
                  strokeWidth={isSelected ? 3 : 2}
                  opacity={opacity}
                  draggable={tool === "select"}
                  onClick={() => tool === "select" && onSelect(ann.id)}
                  onDragEnd={(e) => {
                    const node = e.target;
                    onUpdate(ann.id, {
                      x1: node.x(),
                      y1: node.y(),
                      x2: node.x() + node.width(),
                      y2: node.y() + node.height(),
                    });
                  }}
                  onTransformEnd={(e) => {
                    const node = e.target as Konva.Rect;
                    const scaleX = node.scaleX();
                    const scaleY = node.scaleY();
                    node.scaleX(1);
                    node.scaleY(1);
                    onUpdate(ann.id, {
                      x1: node.x(),
                      y1: node.y(),
                      x2: node.x() + node.width() * scaleX,
                      y2: node.y() + node.height() * scaleY,
                    });
                  }}
                />
              );
            }

            const g = ann.geometry as { points: number[][] };
            const flat = g.points.flat();
            return (
              <PolygonShape
                key={ann.id}
                annId={ann.id}
                points={flat}
                color={color}
                opacity={opacity}
                isSelected={isSelected}
                selectable={tool === "select"}
                registerRef={(node) => {
                  shapeRefs.current[ann.id] = node;
                }}
                onSelect={() => tool === "select" && onSelect(ann.id)}
                onPointsChange={(newPoints) =>
                  onUpdate(ann.id, {
                    points: chunk(newPoints, 2),
                  })
                }
              />
            );
          })}

        {/* Çizim aşamasındaki taslak şekiller */}
        {draftRect && (
          <Rect
            x={Math.min(draftRect.x1, draftRect.x2)}
            y={Math.min(draftRect.y1, draftRect.y2)}
            width={Math.abs(draftRect.x2 - draftRect.x1)}
            height={Math.abs(draftRect.y2 - draftRect.y1)}
            stroke={CLASS_COLORS[activeClassId % CLASS_COLORS.length]}
            dash={[6, 4]}
            strokeWidth={2}
          />
        )}
        {draftPolygon.length > 0 && (
          <Line
            points={draftPolygon.flat()}
            stroke={CLASS_COLORS[activeClassId % CLASS_COLORS.length]}
            strokeWidth={2}
            dash={[6, 4]}
          />
        )}

        <Transformer ref={trRef} rotateEnabled={false} />
      </Layer>
    </Stage>
  );
}

function chunk(arr: number[], size: number): number[][] {
  const out: number[][] = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

function PolygonShape({
  annId,
  points,
  color,
  opacity,
  isSelected,
  selectable,
  registerRef,
  onSelect,
  onPointsChange,
}: {
  annId: string;
  points: number[];
  color: string;
  opacity: number;
  isSelected: boolean;
  selectable: boolean;
  registerRef: (node: Konva.Node | null) => void;
  onSelect: () => void;
  onPointsChange: (points: number[]) => void;
}) {
  const vertices = chunk(points, 2);

  return (
    <>
      <Line
        ref={registerRef as any}
        points={points}
        closed
        stroke={color}
        strokeWidth={isSelected ? 3 : 2}
        fill={`${color}33`}
        opacity={opacity}
        onClick={onSelect}
      />
      {isSelected &&
        selectable &&
        vertices.map(([x, y], idx) => (
          <Circle
            key={idx}
            x={x}
            y={y}
            radius={5}
            fill={color}
            draggable
            onDragMove={(e) => {
              const next = [...vertices];
              next[idx] = [e.target.x(), e.target.y()];
              onPointsChange(next.flat());
            }}
          />
        ))}
    </>
  );
}
