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

// Phase 3 — Compute + Notebooks

export type SlurmJobStatus = "pending" | "running" | "completed" | "failed" | "cancelled" | "timeout";
export type SessionStatus = "pending" | "starting" | "running" | "idle" | "stopping" | "stopped" | "failed";
export type SessionType = "jupyter" | "rstudio";
export type ResourceProfile = "small" | "medium" | "large";

export interface ExperimentSummary {
  id: number;
  name: string;
}

export const RESOURCE_PROFILES: Record<ResourceProfile, { cpu: number; memory: number }> = {
  small: { cpu: 2, memory: 4 },
  medium: { cpu: 4, memory: 8 },
  large: { cpu: 8, memory: 16 },
};

export interface PartitionStatus {
  name: string;
  max_nodes: number;
  active_nodes: number;
  idle_nodes: number;
  queue_depth: number;
  instance_type: string;
  use_spot: boolean;
}

export interface ClusterStatus {
  controller_status: string;
  partitions: PartitionStatus[];
  total_nodes: number;
  active_nodes: number;
  queue_depth: number;
  cost_burn_rate_hourly: number | null;
}

export interface SlurmJob {
  id: number;
  slurm_job_id: string;
  job_name: string | null;
  partition: string;
  status: SlurmJobStatus;
  user: UserSummary | null;
  experiment: ExperimentSummary | null;
  cpu_requested: number | null;
  memory_gb_requested: number | null;
  cpu_used: number | null;
  memory_gb_used: number | null;
  exit_code: number | null;
  cost_estimate: number | null;
  submitted_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface SlurmJobListResponse {
  jobs: SlurmJob[];
  total: number;
  page: number;
  page_size: number;
}

export interface NotebookSession {
  id: number;
  session_type: SessionType;
  user: UserSummary | null;
  experiment: ExperimentSummary | null;
  resource_profile: ResourceProfile;
  cpu_cores: number;
  memory_gb: number;
  status: SessionStatus;
  idle_since: string | null;
  proxy_url: string | null;
  started_at: string | null;
  stopped_at: string | null;
  created_at: string;
}

export interface SessionListResponse {
  sessions: NotebookSession[];
  total: number;
}

export interface SessionLaunchRequest {
  session_type: SessionType;
  resource_profile: ResourceProfile;
  experiment_id?: number | null;
}

export interface UserQuota {
  user_id: number;
  user_name: string | null;
  user_email: string | null;
  user_role: string | null;
  cpu_hours_limit: number | null;
  cpu_hours_used: number;
  quota_reset_at: string;
}

export interface QuotaUpdateRequest {
  cpu_hours_monthly_limit: number | null;
}

export interface BudgetInfo {
  monthly_budget: number | null;
  current_spend: number;
  projected_spend: number;
  threshold_alerts: string[];
}

// Phase 4 — Pipeline Orchestration

export type PipelineRunStatus = "pending" | "running" | "completed" | "failed" | "cancelled";
export type PipelineProcessStatus = "pending" | "running" | "completed" | "failed" | "cached";

export interface ParameterSchema {
  definitions?: Record<string, {
    title?: string;
    properties?: Record<string, {
      type?: string;
      description?: string;
      default?: unknown;
      enum?: string[];
      hidden?: boolean;
      format?: string;
      minimum?: number;
      maximum?: number;
      fa_icon?: string;
    }>;
    required?: string[];
  }>;
}

export interface PipelineCatalog {
  id: number;
  pipeline_key: string;
  name: string;
  description: string | null;
  source_type: string;
  source_url: string | null;
  version: string | null;
  parameter_schema: ParameterSchema | null;
  default_params: Record<string, unknown> | null;
  is_builtin: boolean;
  enabled: boolean;
}

export interface PipelineCatalogListResponse {
  pipelines: PipelineCatalog[];
  total: number;
}

export interface PipelineProgress {
  total_processes: number;
  completed: number;
  running: number;
  failed: number;
  cached: number;
  percent_complete: number;
}

export interface PipelineProcess {
  id: number;
  process_name: string;
  task_id: string | null;
  status: PipelineProcessStatus;
  exit_code: number | null;
  cpu_usage: number | null;
  memory_peak_gb: number | null;
  duration_seconds: number | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface PipelineRun {
  id: number;
  pipeline_key: string | null;
  pipeline_name: string;
  pipeline_version: string | null;
  experiment: ExperimentSummary | null;
  submitted_by: UserSummary | null;
  status: PipelineRunStatus;
  parameters: Record<string, unknown> | null;
  input_files: Record<string, unknown> | null;
  output_files: Record<string, unknown> | null;
  progress: PipelineProgress | null;
  cost_estimate: number | null;
  error_message: string | null;
  work_dir: string | null;
  slurm_job_id: string | null;
  resume_from_run_id: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string | null;
}

export interface PipelineRunDetail extends PipelineRun {
  processes: PipelineProcess[];
  samples: Array<{
    id: number;
    sample_id_external: string | null;
    organism: string | null;
  }>;
}

export interface PipelineRunListResponse {
  runs: PipelineRun[];
  total: number;
  page: number;
  page_size: number;
}

export interface PipelineRunLaunchRequest {
  pipeline_key: string;
  experiment_id: number;
  sample_ids?: number[] | null;
  parameters: Record<string, unknown>;
  resume_from_run_id?: number | null;
}

export interface PipelineRunCompareResponse {
  runs: PipelineRun[];
  parameter_diffs: Record<string, Record<string, unknown>>;
}

export interface PipelineAddRequest {
  name: string;
  source_url: string;
  version?: string | null;
  description?: string | null;
}
