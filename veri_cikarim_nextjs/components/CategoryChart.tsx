"use client";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LabelList } from "recharts";
import { FIELDS, CATEGORIES } from "@/lib/fields";

const COLORS = ["#0f766e","#2563eb","#7c3aed","#db2777","#ea580c","#16a34a","#0891b2"];

export default function CategoryChart() {
  const data = CATEGORIES.map((c, i) => ({
    name: c,
    adet: FIELDS.filter((f) => f.category === c).length,
    fill: COLORS[i % COLORS.length],
  }));
  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Kategoriye Göre Alan Dağılımı (toplam 35 alan)</h3>
      <ResponsiveContainer width="100%" height={340}>
        <BarChart data={data} layout="vertical" margin={{ left: 40, right: 30 }}>
          <XAxis type="number" allowDecimals={false} domain={[0, 9]} />
          <YAxis type="category" dataKey="name" width={170} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="adet" radius={[0, 6, 6, 0]}>
            <LabelList dataKey="adet" position="right" />
            {data.map((d, i) => (<Cell key={i} fill={d.fill} />))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
