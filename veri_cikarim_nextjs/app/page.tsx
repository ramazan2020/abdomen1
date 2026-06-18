import { pool, type Study } from "@/lib/db";
import StudyList from "@/components/StudyList";

export const dynamic = "force-dynamic";

export default async function Page() {
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
      <h1>Makalelerden Çıkarılan Çalışmalar — Veri Listesi</h1>
      <p className="sub">
        Karın Ağrısı için BT'de Yapay Zeka: Çoklu Veritabanı Kapsam Belirleme İncelemesi ·
        Yönergeye uygun {rows.length} çalışma · PostgreSQL kaynaklı
      </p>
      {error ? (
        <div className="card" style={{ color: "#b91c1c" }}>
          <strong>Veritabanına bağlanılamadı.</strong>
          <p>Önce PostgreSQL'i başlatıp şema/seed yükleyin (README). Hata: {error}</p>
        </div>
      ) : (
        <StudyList rows={rows} />
      )}
    </main>
  );
}
