// ── Model Registry (Faz 2) ─────────────────────────────────────────────────
export interface ModelOutputDto {
  id: string;
  output_type: "bbox" | "mask" | "classification";
  class_set: Record<string, unknown> | unknown[] | null;
  postprocess_config: Record<string, unknown> | null;
}

export interface ModelVersionDto {
  id: string;
  name: string;
  architecture: string;
  run_mode: "default" | "comparison";
  base_weights: string | null;
  metrics: Record<string, unknown> | null;
  fold: number | null;
  status: "inactive" | "active" | "archived";
  created_at: string;
  outputs: ModelOutputDto[];
}

// ── Inference (Faz 2) ──────────────────────────────────────────────────────
export interface InferenceRunDto {
  id: string;
  model_version_id: string;
  model_name: string;
  architecture: string;
  conf_threshold: number;
  min_slice_run: number;
  status: "queued" | "running" | "succeeded" | "failed";
  error_message: string | null;
  created_at: string;
}

export interface InferenceBatchDto {
  id: string;
  case_id: string;
  batch_type: "default" | "comparison";
  status: string;
  created_at: string;
  runs: InferenceRunDto[];
}

// ── Case list/detail ───────────────────────────────────────────────────────
export interface CaseListItem {
  id: string;
  case_label: string | null;
  status: "uploaded" | "validating" | "ready" | "failed";
  review_status: "unreviewed" | "in_review" | "reviewed" | "approved_for_training" | "excluded";
  n_slices: number | null;
  created_at: string;
}

export interface ValidationReport {
  total_dicom_count: number;
  valid_slice_count: number;
  invalid_file_count: number;
  slice_thickness_mm: number | null;
  pixel_spacing_mm: number[] | null;
  series_description: string | null;
  sort_key: string;
  deidentification_status: string;
}

export interface CaseDetail extends CaseListItem {
  deidentified: boolean;
  validation_report: ValidationReport | null;
}

export interface SliceInfo {
  image_id: number;
  z_index: number;
  png_ready: boolean;
}

export interface AnnotationZipImportDetail {
  case_num: string;
  prefix: string;
  matched: boolean | null;
  case_id?: string | null;
  sent: number;
  skipped: number;
  note?: string | null;
}

export interface AnnotationZipImportResponse {
  total_sent: number;
  total_skipped: number;
  details: AnnotationZipImportDetail[];
}

export interface AnnotationDto {
  id: string;
  case_id: string;
  image_id: number;
  class_type: "lesion" | "organ";
  class_id: number;
  geometry_type: "bbox" | "polygon";
  geometry: { x1: number; y1: number; x2: number; y2: number } | { points: number[][] };
  source: "prediction" | "manual" | "corrected";
  confidence: number | null;
  status: string;
  derived_from_annotation_id: string | null;
  included_in_training_pool: boolean;
  created_at: string;
}

// ── Training / Dataset Snapshot (Faz 3) ───────────────────────────────────
export interface SnapshotDto {
  id: string;
  snapshot_name: string;
  description: string | null;
  notes: string | null;
  included_cases_count: number | null;
  included_annotations_count: number | null;
  source: string;
  manifest_storage_key: string | null;
  created_at: string;
}

export interface TrainingJobDto {
  id: string;
  job_type: string;
  architecture: string;
  params: Record<string, unknown>;
  dataset_snapshot_id: string;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  progress_percent: number | null;
  current_epoch: number | null;
  best_metric: Record<string, number> | null;
  error_message: string | null;
  cancel_requested: boolean;
  log_storage_key: string | null;
  queue_job_id: string | null;
  started_at: string | null;
  finished_at: string | null;
  heartbeat_at: string | null;
  result_model_version_id: string | null;
  created_at: string;
}

// ── src/config.py SUPER_CLASSES ile birebir (plan Bölüm "Kritik dosyalar") ─
export const LESION_CLASSES = [
  "acute_cholecystitis",
  "kidney_ureter_stone",
  "acute_pancreatitis",
  "aortic_aneurysm_dissection",
  "acute_appendicitis",
  "acute_diverticulitis",
] as const;

export const LESION_CLASS_LABELS_TR = [
  "Akut kolesistit",
  "Böbrek/üreter taşı",
  "Akut pankreatit",
  "Aort anevrizma/diseksiyon",
  "Akut apandisit",
  "Akut divertikülit",
];

export const CLASS_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"];
