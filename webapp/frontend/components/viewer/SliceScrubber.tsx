"use client";

export function SliceScrubber({
  value,
  max,
  onChange,
}: {
  value: number;
  max: number;
  onChange: (z: number) => void;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <button className="btn-secondary" onClick={() => onChange(Math.max(0, value - 1))} disabled={value <= 0}>
        ◀
      </button>
      <input
        type="range"
        min={0}
        max={Math.max(0, max - 1)}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ flex: 1 }}
      />
      <button className="btn-secondary" onClick={() => onChange(Math.min(max - 1, value + 1))} disabled={value >= max - 1}>
        ▶
      </button>
      <span style={{ fontSize: 13, color: "#9aa0ab", minWidth: 70 }}>
        Dilim {value + 1}/{max}
      </span>
    </div>
  );
}
