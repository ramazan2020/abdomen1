"use client";

import { CLASS_COLORS, LESION_CLASS_LABELS_TR } from "@/lib/types";

export function ClassPicker({
  value,
  onChange,
}: {
  value: number;
  onChange: (classId: number) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      style={{
        padding: 6,
        borderRadius: 6,
        background: "#0f1115",
        color: "#e6e6e6",
        border: `2px solid ${CLASS_COLORS[value]}`,
      }}
    >
      {LESION_CLASS_LABELS_TR.map((label, idx) => (
        <option key={idx} value={idx}>
          {label}
        </option>
      ))}
    </select>
  );
}
