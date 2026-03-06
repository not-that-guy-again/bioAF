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

// Phase 5 — Data Management + Visualization

export interface FileResponse {
  id: number;
  filename: string;
  gcs_uri: string;
  size_bytes: number | null;
  md5_checksum: string | null;
  file_type: string;
  tags: string[];
  uploader: UserSummary | null;
  upload_timestamp: string;
  created_at: string;
}

export interface FileListResponse {
  files: FileResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface FileUploadInitiateResponse {
  upload_id: string;
  signed_url: string;
  gcs_uri: string;
}

export interface DatasetExperimentSummary {
  experiment_id: number;
  experiment_name: string;
  status: string;
  organism: string | null;
  tissue: string | null;
  sample_count: number;
  file_count: number;
  total_size_bytes: number;
  pipeline_run_count: number;
  has_qc_dashboard: boolean;
  has_cellxgene: boolean;
  owner: UserSummary | null;
  created_at: string;
}

export interface DatasetSearchResult {
  experiments: DatasetExperimentSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface DocumentResponse {
  id: number;
  title: string | null;
  file: FileResponse | null;
  has_extracted_text: boolean;
  linked_experiment_id: number | null;
  linked_sample_id: number | null;
  linked_pipeline_run_id: number | null;
  created_at: string;
}

export interface DocumentSearchResponse {
  documents: DocumentResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface BucketStats {
  bucket_name: string;
  total_bytes: number;
  object_count: number;
  by_storage_class: Record<string, number>;
  cost_estimate_monthly: number;
}

export interface LifecyclePolicyStatus {
  bucket_name: string;
  rules: Record<string, unknown>[];
  enabled: boolean;
}

export interface StorageDashboard {
  buckets: BucketStats[];
  total_bytes: number;
  total_cost_estimate_monthly: number;
  lifecycle_policies: LifecyclePolicyStatus[];
  last_updated: string;
}

export interface CellxgenePublicationResponse {
  id: number;
  dataset_name: string;
  stable_url: string | null;
  status: string;
  file: FileResponse | null;
  experiment_id: number | null;
  published_by: UserSummary | null;
  published_at: string | null;
  created_at: string;
}

export interface QCMetrics {
  cell_count: number | null;
  median_reads_per_cell: number | null;
  median_genes_per_cell: number | null;
  median_umi_per_cell: number | null;
  mito_pct_median: number | null;
  doublet_score_median: number | null;
  saturation: number | null;
  quality_rating: string;
}

export interface QCPlot {
  plot_type: string;
  title: string;
  file_id: number;
  download_url?: string | null;
}

export interface QCDashboardResponse {
  id: number;
  pipeline_run_id: number;
  experiment_id: number | null;
  metrics: QCMetrics;
  summary_text: string;
  plots: QCPlot[];
  status: string;
  generated_at: string | null;
  created_at: string;
}

export interface QCDashboardSummary {
  id: number;
  pipeline_run_id: number;
  quality_rating: string;
  cell_count: number | null;
  status: string;
  generated_at: string | null;
}

export interface PlotArchiveResponse {
  id: number;
  title: string | null;
  file: FileResponse | null;
  experiment_id: number | null;
  pipeline_run_id: number | null;
  notebook_session_id: number | null;
  tags: string[];
  thumbnail_url: string | null;
  indexed_at: string;
}

export interface PlotArchiveListResponse {
  plots: PlotArchiveResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface SearchHit {
  entity_type: string;
  entity_id: number;
  title: string;
  snippet: string | null;
  experiment_id: number | null;
  relevance_score: number | null;
}

export interface SearchResult {
  results: SearchHit[];
  total: number;
  page: number;
  page_size: number;
}

export interface ProvenanceNode {
  entity_type: string;
  entity_id: number;
  label: string;
  timestamp: string | null;
  children: number[];
  metadata: Record<string, unknown>;
}

export interface ProvenanceChain {
  experiment: ProvenanceNode;
  samples: ProvenanceNode[];
  fastq_uploads: ProvenanceNode[];
  pipeline_runs: ProvenanceNode[];
  outputs: ProvenanceNode[];
  cellxgene_publications: ProvenanceNode[];
  qc_dashboards: ProvenanceNode[];
}

// Phase 6 — GitOps + Package Management

export interface GitOpsRepoStatus {
  initialized: boolean;
  repo_url: string | null;
  repo_name: string | null;
  last_commit_sha: string | null;
  last_commit_at: string | null;
  status: string;
}

export interface GitCommit {
  sha: string;
  message: string;
  author: string;
  timestamp: string;
  files_changed: number | null;
}

export interface GitCommitDetail extends GitCommit {
  diff: string;
  files: string[];
}

export interface GitCommitListResponse {
  commits: GitCommit[];
  total: number;
  page: number;
  page_size: number;
}

export interface PackageSearchResult {
  name: string;
  version: string;
  description: string | null;
  source: string;
  channel: string | null;
  homepage: string | null;
}

export interface PackageSearchResponse {
  results: PackageSearchResult[];
  total: number;
  query: string;
}

export interface DependencyNode {
  name: string;
  version: string;
  source: string;
  action: string;
}

export interface DependencyTree {
  package: string;
  version: string;
  dependencies: DependencyNode[];
  total_new_packages: number;
  estimated_disk_bytes: number | null;
}

export interface InstalledPackage {
  name: string;
  version: string | null;
  source: string;
  pinned: boolean;
  installed_at: string;
}

export interface EnvironmentResponse {
  id: number;
  name: string;
  env_type: string;
  description: string | null;
  is_default: boolean;
  package_count: number;
  jupyter_kernel_name: string | null;
  status: string;
  last_synced_at: string | null;
  created_by: UserSummary | null;
  created_at: string;
}

export interface EnvironmentListResponse {
  environments: EnvironmentResponse[];
  total: number;
}

export interface EnvironmentDetailResponse extends Omit<EnvironmentResponse, "package_count"> {
  packages: InstalledPackage[];
}

export interface EnvironmentChangeResponse {
  id: number;
  change_type: string;
  package_name: string | null;
  old_version: string | null;
  new_version: string | null;
  git_commit_sha: string | null;
  commit_message: string | null;
  reconciled: boolean;
  reconciled_at: string | null;
  error_message: string | null;
  user: UserSummary | null;
  created_at: string;
}

export interface EnvironmentHistoryResponse {
  changes: EnvironmentChangeResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface EnvironmentDiff {
  added: string[];
  removed: string[];
  changed: Array<{ name: string; old_version: string | null; new_version: string | null }>;
}

export interface TemplateNotebookResponse {
  id: number;
  name: string;
  description: string | null;
  category: string | null;
  compatible_with: string | null;
  parameters: Record<string, unknown>;
  is_builtin: boolean;
  created_at: string;
}

export interface TemplateNotebookListResponse {
  notebooks: TemplateNotebookResponse[];
  total: number;
}
