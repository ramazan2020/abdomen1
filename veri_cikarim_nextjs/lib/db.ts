import { Pool, PoolConfig } from "pg";

// DATABASE_URL varsa onu kullan; yoksa docker-compose varsayılanlarına düş.
// (Parolanın her zaman string olmasını garanti eder; SASL "password must be a string" hatasını önler.)
const config: PoolConfig = process.env.DATABASE_URL
  ? { connectionString: process.env.DATABASE_URL }
  : {
      host: process.env.PGHOST || "localhost",
      port: Number(process.env.PGPORT || 5432),
      user: process.env.PGUSER || "postgres",
      password: String(process.env.PGPASSWORD || "postgres"),
      database: process.env.PGDATABASE || "veri_cikarim",
    };

const globalForPg = global as unknown as { pgPool?: Pool };
export const pool = globalForPg.pgPool ?? new Pool(config);
if (process.env.NODE_ENV !== "production") globalForPg.pgPool = pool;

export type Study = {
  id: number; ref_no: number; first_author: string|null; authors_full: string|null;
  year: number|null; title: string; venue: string|null; country: string|null;
  pathology: string|null; pathology_code: string|null; modality: string|null;
  dataset_name: string|null; dataset_access: string|null;
  patient_count: number|null; image_count: number|null;
  task: string|null; model: string|null; method_detail: string|null; summary: string|null;
  performance: string|null; ext_validation: string|null; radiologist_comparison: string|null;
  open_code: string|null; open_data: string|null; code_url: string|null;
  depth: string|null; limitations: string|null; doi_url: string|null;
};
