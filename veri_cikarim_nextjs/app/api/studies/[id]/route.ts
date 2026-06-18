import { pool } from "@/lib/db";

const COLS = [
  "ref_no","first_author","authors_full","year","title","venue","country",
  "pathology","pathology_code","modality","dataset_name","dataset_access",
  "patient_count","image_count","task","model","method_detail","summary",
  "performance","ext_validation","radiologist_comparison","open_code","open_data",
  "code_url","depth","limitations","doi_url",
] as const;

export async function PUT(
  req: Request,
  { params }: { params: { id: string } }
) {
  try {
    const id = Number(params.id);
    const b = await req.json();
    const set = COLS.map((c, i) => `${c}=$${i + 1}`).join(", ");
    const vals = [...COLS.map((c) => b[c] ?? null), id];
    const { rows } = await pool.query(
      `UPDATE extracted_studies SET ${set} WHERE id=$${COLS.length + 1} RETURNING *`,
      vals
    );
    if (!rows.length) return Response.json({ error: "Kayıt bulunamadı" }, { status: 404 });
    return Response.json(rows[0]);
  } catch (e) {
    return Response.json({ error: String(e) }, { status: 500 });
  }
}

export async function DELETE(
  _req: Request,
  { params }: { params: { id: string } }
) {
  try {
    await pool.query("DELETE FROM extracted_studies WHERE id=$1", [Number(params.id)]);
    return Response.json({ ok: true });
  } catch (e) {
    return Response.json({ error: String(e) }, { status: 500 });
  }
}
