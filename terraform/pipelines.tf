# =============================================================================
# Nextflow + Snakemake configuration (optional)
# Pipeline orchestration runs on SLURM — Terraform manages service accounts
# =============================================================================

resource "google_service_account" "nextflow" {
  count        = var.enable_nextflow ? 1 : 0
  account_id   = "bioaf-nextflow"
  display_name = "bioAF Nextflow Executor"
}

resource "google_project_iam_member" "nextflow_storage" {
  count   = var.enable_nextflow ? 1 : 0
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.nextflow[0].email}"
}

resource "google_project_iam_member" "nextflow_logging" {
  count   = var.enable_nextflow ? 1 : 0
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.nextflow[0].email}"
}

resource "google_service_account" "snakemake" {
  count        = var.enable_snakemake ? 1 : 0
  account_id   = "bioaf-snakemake"
  display_name = "bioAF Snakemake Executor"
}

resource "google_project_iam_member" "snakemake_storage" {
  count   = var.enable_snakemake ? 1 : 0
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.snakemake[0].email}"
}

resource "google_project_iam_member" "snakemake_logging" {
  count   = var.enable_snakemake ? 1 : 0
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.snakemake[0].email}"
}
