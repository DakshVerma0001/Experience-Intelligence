export type Role = "CONTRIBUTOR" | "REVIEWER" | "ADMIN";

export interface AuthUser {
  email: string;
  full_name: string;
  role: Role;
}

export interface ImportBatch {
  id: string;
  batch_number: number;
  status: string;
  created_by: string;
  projects_detected: number;
  projects_auto_imported: number;
  projects_review_required: number;
  projects_duplicate: number;
  projects_failed: number;
  cancel_requested: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProcessingProgress {
  batch_id: string;
  status: string;
  documents_uploaded: number;
  documents_processed: number;
  projects_detected: number;
  projects_processed: number;
  current_step: string | null;
  warnings: string[];
  failures: string[];
}

export interface ProjectSummary {
  id: string;
  project_name: string | null;
  client_name: string | null;
  project_status: string | null;
  workflow_state: string;
  extraction_confidence: number | null;
  duplicate_status: string;
  validation_status: string;
  source_assignment_number: string | null;
  created_at: string;
}

export interface KeywordOut {
  id: string;
  keyword: string;
  category: string | null;
  description: string | null;
  aliases: string[];
  source_supported: boolean;
}

export interface FieldProvenance {
  field: string;
  value: string | null;
  source_text: string | null;
  source_location: string | null;
  confidence: number | null;
  extraction_type: string | null;
  edited_by_human: boolean;
}

export interface ProjectDetail extends ProjectSummary {
  import_batch_id: string;
  source_document_id: string;
  short_form: string | null;
  contract_value_crore: number | null;
  contract_value_original_text: string | null;
  country: string | null;
  state_ut: string | null;
  client_type: string | null;
  client_address: string | null;
  contact_person: string | null;
  designation: string | null;
  telephone: string | null;
  email: string | null;
  start_date: string | null;
  completion_date: string | null;
  duration_months: number | null;
  total_staff_months: number | null;
  professional_staff_months: number | null;
  associated_consultants: string | null;
  senior_professional_staff: string | null;
  project_description: string | null;
  actual_services: string | null;
  ai_search_summary: string | null;
  source_filename: string | null;
  source_page: string | null;
  source_text: string | null;
  source_location: string | null;
  extraction_type: string | null;
  duplicate_of_project_id: string | null;
  duplicate_similarity: number | null;
  ai_model: string | null;
  embedding_model: string | null;
  validation_warnings: string[];
  failure_reason: string | null;
  edited_by_human: boolean;
  portal_project_id: string | null;
  imported_at: string | null;
  keywords: KeywordOut[];
  field_provenance: FieldProvenance[];
  updated_at: string;
}

export interface SearchResultItem {
  project_id: string;
  project_name: string | null;
  client_name: string | null;
  country: string | null;
  state_ut: string | null;
  ai_search_summary: string | null;
  score: number;
  matched_keywords: string[];
  match_reasons: string[];
}

export interface AuditLogEntry {
  id: string;
  actor_label: string | null;
  application: string;
  action: string;
  import_batch_id: string | null;
  project_id: string | null;
  source_document: string | null;
  ai_model: string | null;
  embedding_model: string | null;
  result: string | null;
  created_at: string;
}

export interface HealthStatus {
  application: boolean;
  database: boolean;
  ollama: boolean;
  ollama_message: string;
  llm_model: boolean;
  embedding_model: boolean;
  embedding_message: string;
  portal: boolean;
  portal_message: string;
  environment: string;
}
