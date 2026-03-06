export interface User {
  id: number;
  email: string;
  name: string | null;
  role: "admin" | "comp_bio" | "bench" | "viewer";
  status: "active" | "invited" | "deactivated";
  organization_id: number;
  created_at: string;
  updated_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface BootstrapStatus {
  setup_complete: boolean;
}

export interface ComponentState {
  key: string;
  name: string;
  description: string;
  category: string;
  enabled: boolean;
  status: string;
  config: Record<string, unknown>;
  dependencies: string[];
  estimated_monthly_cost: string;
  updated_at: string | null;
}

export interface TerraformRun {
  id: number;
  triggered_by_user_id: number;
  action: string;
  component_key: string | null;
  plan_summary: {
    add: Array<{ type: string; name: string; address: string }>;
    change: Array<{ type: string; name: string; address: string }>;
    destroy: Array<{ type: string; name: string; address: string }>;
    add_count: number;
    change_count: number;
    destroy_count: number;
  } | null;
  status: string;
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface HealthStatus {
  status: "healthy" | "degraded" | "unhealthy";
  services: Record<string, { status: string; error?: string }>;
}

export interface NavItem {
  label: string;
  href: string;
  icon: string;
  active: boolean;
  phase?: string;
  adminOnly?: boolean;
}

// Phase 2 — Experiment Tracking

export type ExperimentStatus =
  | "registered"
  | "library_prep"
  | "sequencing"
  | "fastq_uploaded"
  | "processing"
  | "analysis"
  | "complete";

export type QCStatus = "pass" | "warning" | "fail";

export type SampleStatus =
  | "registered"
  | "library_prepped"
  | "sequenced"
  | "fastq_uploaded"
  | "pipeline_complete"
  | "analysis_complete";

export interface UserSummary {
  id: number;
  name: string | null;
  email: string;
}

export interface ProjectSummary {
  id: number;
  name: string;
}

export interface Project {
  id: number;
  name: string;
  description: string | null;
  experiment_count: number;
  created_by_name: string | null;
  created_at: string;
}

export interface ProjectListResponse {
  projects: Project[];
  total: number;
}

export interface Experiment {
  id: number;
  name: string;
  project: ProjectSummary | null;
  hypothesis: string | null;
  description: string | null;
  status: ExperimentStatus;
  start_date: string | null;
  expected_sample_count: number | null;
  owner: UserSummary | null;
  sample_count: number;
  batch_count: number;
  created_at: string;
  updated_at: string;
}

export interface ExperimentListResponse {
  experiments: Experiment[];
  total: number;
  page: number;
  page_size: number;
}

export interface CustomFieldValue {
  field_name: string;
  field_value: string;
  field_type: string;
}

export interface CustomFieldResponse {
  id: number;
  field_name: string;
  field_value: string | null;
  field_type: string;
}

export interface SampleBrief {
  id: number;
  sample_id_external: string | null;
  organism: string | null;
  tissue_type: string | null;
  qc_status: QCStatus | null;
  status: SampleStatus;
  created_at: string;
}

export interface BatchBrief {
  id: number;
  name: string;
  sample_count: number;
  created_at: string;
}

export interface ExperimentDetail extends Experiment {
  samples: SampleBrief[];
  batches: BatchBrief[];
  custom_fields: CustomFieldResponse[];
  audit_trail_count: number;
}

export interface BatchSummary {
  id: number;
  name: string;
}

export interface Sample {
  id: number;
  sample_id_external: string | null;
  organism: string | null;
  tissue_type: string | null;
  donor_source: string | null;
  treatment_condition: string | null;
  chemistry_version: string | null;
  batch: BatchSummary | null;
  viability_pct: number | null;
  cell_count: number | null;
  prep_notes: string | null;
  qc_status: QCStatus | null;
  qc_notes: string | null;
  status: SampleStatus;
  created_at: string;
  updated_at: string;
}

export interface Batch {
  id: number;
  name: string;
  prep_date: string | null;
  operator: UserSummary | null;
  sequencer_run_id: string | null;
  notes: string | null;
  sample_count: number;
  created_at: string;
  updated_at: string;
}

export interface ExperimentTemplate {
  id: number;
  name: string;
  description: string | null;
  required_fields_json: Record<string, unknown> | null;
  custom_fields_schema_json: Record<string, unknown> | null;
  created_by: UserSummary | null;
  created_at: string;
}

export interface AuditLogEntry {
  id: number;
  timestamp: string;
  user: UserSummary | null;
  entity_type: string;
  entity_id: number;
  action: string;
  details: Record<string, unknown> | null;
  previous_value: Record<string, unknown> | null;
}

export interface AuditLogResponse {
  entries: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface ExperimentCreateRequest {
  name: string;
  project_id?: number | null;
  template_id?: number | null;
  hypothesis?: string | null;
  description?: string | null;
  start_date?: string | null;
  expected_sample_count?: number | null;
  custom_fields?: CustomFieldValue[];
}

export interface SampleCreateRequest {
  sample_id_external?: string | null;
  organism?: string | null;
  tissue_type?: string | null;
  donor_source?: string | null;
  treatment_condition?: string | null;
  chemistry_version?: string | null;
  batch_id?: number | null;
  viability_pct?: number | null;
  cell_count?: number | null;
  prep_notes?: string | null;
  qc_status?: string | null;
  qc_notes?: string | null;
}

export interface BatchCreateRequest {
  name: string;
  prep_date?: string | null;
  operator_user_id?: number | null;
  sequencer_run_id?: string | null;
  notes?: string | null;
}

export interface TemplateCreateRequest {
  name: string;
  description?: string | null;
  required_fields_json?: Record<string, unknown> | null;
  custom_fields_schema_json?: Record<string, unknown> | null;
}
