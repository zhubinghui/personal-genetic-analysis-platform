export interface User {
  id: string;
  email: string;
  is_admin: boolean;
  consent_version: string | null;
  consent_given_at: string | null;
  created_at: string;
}

export interface AdminUser {
  id: string;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  consent_version: string | null;
  consent_given_at: string | null;
  created_at: string;
}

export interface AdminUserList {
  total: number;
  items: AdminUser[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface Sample {
  id: string;
  array_type: string;
  upload_status: string;
  chronological_age: number | null;
  uploaded_at: string;
  deleted_at: string | null;
  latest_job_id: string | null;
  latest_job_status: string | null;
}

export interface SampleUploadResponse {
  sample_id: string;
  job_id: string;
  array_type: string;
  status: string;
  message: string;
}

export interface JobStatus {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  stage: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface DunedinPaceDimensions {
  cardiovascular: Record<string, number | null>;
  metabolic: Record<string, number | null>;
  renal: Record<string, number | null>;
  hepatic: Record<string, number | null>;
  pulmonary: Record<string, number | null>;
  immune: Record<string, number | null>;
  periodontal: Record<string, number | null>;
  cognitive: Record<string, number | null>;
  physical: Record<string, number | null>;
}

export interface AnalysisResult {
  id: string;
  job_id: string;
  sample_id: string;
  qc_passed: boolean | null;
  n_probes_before: number | null;
  n_probes_after: number | null;
  detection_p_failed_fraction: number | null;
  chronological_age: number | null;
  horvath_age: number | null;
  grimage_age: number | null;
  phenoage_age: number | null;
  dunedinpace: number | null;
  biological_age_acceleration: number | null;
  dunedinpace_dimensions: DunedinPaceDimensions | null;
  computed_at: string;
}

export interface LiteratureReference {
  document_title: string;
  excerpt: string;
  page_number: number | null;
  relevance_score: number;
}

export interface Recommendation {
  dimension: string;
  dimension_score: number;
  priority: number;
  title: string;
  summary: string;
  evidence_level: "A" | "B" | "C";
  pmids: string[];
  pubmed_urls: string[];
  category: "diet" | "exercise" | "supplement" | "lifestyle";
  timeframe_weeks: number;
  literature_references: LiteratureReference[];
}

// ── 知识库（管理员）────────────────────────────────────────

export type DocumentStatus = "pending" | "processing" | "ready" | "failed";
export type DocumentFileType = "pdf" | "docx" | "txt" | "md";

export interface KnowledgeDocument {
  id: string;
  title: string;
  description: string | null;
  authors: string | null;
  journal: string | null;
  published_year: number | null;
  doi: string | null;
  tags: string[] | null;
  file_name: string;
  file_type: DocumentFileType;
  file_size_bytes: number | null;
  status: DocumentStatus;
  error_message: string | null;
  chunk_count: number;
  uploaded_by: string;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeDocumentList {
  total: number;
  items: KnowledgeDocument[];
}

export interface SearchResultChunk {
  document_id: string;
  document_title: string;
  chunk_index: number;
  chunk_text: string;
  page_number: number | null;
  score: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResultChunk[];
}

// ── 纵向对比 ────────────────────────────────────────────

export interface TrendPoint {
  sample_id: string;
  job_id: string;
  uploaded_at: string;
  chronological_age: number | null;
  horvath_age: number | null;
  grimage_age: number | null;
  phenoage_age: number | null;
  dunedinpace: number | null;
  biological_age_acceleration: number | null;
  dimension_summary: Record<string, number | null>;
}

export interface TrendResponse {
  points: TrendPoint[];
  total_samples: number;
}

// ── 同龄对标 ────────────────────────────────────────────

export interface BenchmarkMetric {
  value: number | null;
  percentile: number | null;
  cohort_mean: number | null;
  cohort_std: number | null;
}

export interface BenchmarkData {
  age_group: string;
  cohort_size: number;
  dunedinpace: BenchmarkMetric;
  horvath_acceleration: BenchmarkMetric;
  grimage_acceleration: BenchmarkMetric;
  phenoage_acceleration: BenchmarkMetric;
}

export interface ReportData {
  job_id: string;
  generated_at: string;
  summary: string;
  clocks: {
    horvath_age: number | null;
    grimage_age: number | null;
    phenoage_age: number | null;
    dunedinpace: number | null;
    chronological_age: number | null;
    biological_age_acceleration: number | null;
  };
  dimensions: DunedinPaceDimensions | null;
  recommendations: Recommendation[];
  qc_summary: {
    qc_passed: boolean | null;
    n_probes_before: number | null;
    n_probes_after: number | null;
  };
  benchmark: BenchmarkData | null;
  pdf_available?: boolean;
}
