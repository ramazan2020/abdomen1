import { pool, type Study } from "@/lib/db";
import AnalyticsCharts from "@/components/AnalyticsCharts";

export const dynamic = "force-dynamic";

export default async function GrafiklerPage() {
  let rows: Study[] = [];
  let error: string | null = null;
  try {
    const r = await pool.query("SELECT * FROM extracted_studies ORDER BY ref_no ASC");
    rows = r.rows;
  } catch (e) {
    error = String(e);
  }
  return (
    <main className="wrap">
      <h1>Analitik Grafikler</h1>
      <p className="sub">
        Karın Ağrısı için BT&apos;de Yapay Zeka · Çoklu Veritabanı Kapsam Belirleme İncelemesi ·{" "}
        {rows.length} çalışma · 6 grafik paneli
      </p>
      {error ? (
        <div className="card" style={{ color: "#b91c1c" }}>
          <strong>Veritabanına bağlanılamadı.</strong>
          <p>Önce PostgreSQL&apos;i başlatıp şema/seed yükleyin (README). Hata: {error}</p>
        </div>
      ) : (
        <AnalyticsCharts rows={rows} />
      )}
    </main>
  );
}
