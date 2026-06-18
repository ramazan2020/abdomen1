import { pool } from "@/lib/db";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const { rows } = await pool.query(
      "SELECT * FROM extracted_studies ORDER BY ref_no ASC"
    );
    return Response.json(rows);
  } catch (e) {
    return Response.json({ error: String(e) }, { status: 500 });
  }
}

const COLS = [
  "ref_no","first_author","authors_full","year","title","venue","country",
  "pathology","pathology_code","modality","dataset_name","dataset_access",
  "patient_count","image_count","task","model","method_detail","summary",
  "performance","ext_validation","radiologist_comparison","open_code","open_data",
  "code_url","depth","limitations","doi_url",
] as const;

export async function POST(req: Request) {
  try {
    const b = await req.json();
    const vals = COLS.map((c) => b[c] ?? null);
    const placeholders = COLS.map((_, i) => `$${i + 1}`).join(", ");
    const { rows } = await pool.query(
      `INSERT INTO extracted_studies (${COLS.join(", ")}) VALUES (${placeholders}) RETURNING *`,
      vals
    );
    return Response.json(rows[0], { status: 201 });
  } catch (e) {
    return Response.json({ error: String(e) }, { status: 500 });
  }
}
