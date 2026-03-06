# =============================================================================
# Service Accounts and IAM Bindings
# =============================================================================

# Control plane service account (used by bioAF backend pods via Workload Identity)
resource "google_service_account" "control_plane" {
  account_id   = "bioaf-control-plane"
  display_name = "bioAF Control Plane"
  description  = "Service account for bioAF backend pods"
}

# Terraform executor service account (used for plan/apply operations)
resource "google_service_account" "terraform_executor" {
  account_id   = "bioaf-terraform-executor"
  display_name = "bioAF Terraform Executor"
  description  = "Service account for Terraform operations"
}

# Control plane IAM bindings
resource "google_project_iam_member" "control_plane_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.control_plane.email}"
}

resource "google_project_iam_member" "control_plane_monitoring" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.control_plane.email}"
}

# Terraform executor IAM bindings
resource "google_project_iam_member" "terraform_executor_compute" {
  project = var.project_id
  role    = "roles/compute.admin"
  member  = "serviceAccount:${google_service_account.terraform_executor.email}"
}

resource "google_project_iam_member" "terraform_executor_container" {
  project = var.project_id
  role    = "roles/container.admin"
  member  = "serviceAccount:${google_service_account.terraform_executor.email}"
}

resource "google_project_iam_member" "terraform_executor_sql" {
  project = var.project_id
  role    = "roles/cloudsql.admin"
  member  = "serviceAccount:${google_service_account.terraform_executor.email}"
}

resource "google_project_iam_member" "terraform_executor_storage" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.terraform_executor.email}"
}

resource "google_project_iam_member" "terraform_executor_iam" {
  project = var.project_id
  role    = "roles/iam.serviceAccountAdmin"
  member  = "serviceAccount:${google_service_account.terraform_executor.email}"
}

resource "google_project_iam_member" "terraform_executor_secretmanager" {
  project = var.project_id
  role    = "roles/secretmanager.admin"
  member  = "serviceAccount:${google_service_account.terraform_executor.email}"
}

# Workload Identity binding for control plane
resource "google_service_account_iam_member" "control_plane_workload_identity" {
  service_account_id = google_service_account.control_plane.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[bioaf/bioaf-backend]"
}

# Workload Identity binding for secret accessor
resource "google_service_account_iam_member" "secret_accessor_workload_identity" {
  service_account_id = google_service_account.secret_accessor.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[bioaf/bioaf-backend]"
}
