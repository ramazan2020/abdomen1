-- PostgreSQL şeması (PDF tam metinden zenginleştirilmiş)
DROP TABLE IF EXISTS extracted_studies;
CREATE TABLE extracted_studies (
  id SERIAL PRIMARY KEY,
  ref_no INTEGER NOT NULL,
  first_author TEXT,
  authors_full TEXT,
  year INTEGER,
  title TEXT NOT NULL,
  venue TEXT,
  country TEXT,
  pathology TEXT,
  pathology_code TEXT,
  modality TEXT,
  dataset_name TEXT,
  dataset_access TEXT,
  patient_count INTEGER,
  image_count INTEGER,
  task TEXT,
  model TEXT,
  method_detail TEXT,
  summary TEXT,
  performance TEXT,
  ext_validation TEXT,
  radiologist_comparison TEXT,
  open_code TEXT,
  open_data TEXT,
  code_url TEXT,
  depth TEXT,
  limitations TEXT,
  doi_url TEXT
);
CREATE INDEX idx_pathology ON extracted_studies(pathology_code);
CREATE INDEX idx_year ON extracted_studies(year);
