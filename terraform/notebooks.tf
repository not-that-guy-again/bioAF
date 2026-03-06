# =============================================================================
# JupyterHub and RStudio (optional, enable_jupyter / enable_rstudio)
# Deployed via Helm on GKE — Terraform manages the namespace and config
# =============================================================================

resource "google_service_account" "jupyter" {
  count        = var.enable_jupyter ? 1 : 0
  account_id   = "bioaf-jupyter"
  display_name = "bioAF JupyterHub"
}

resource "google_project_iam_member" "jupyter_storage" {
  count   = var.enable_jupyter ? 1 : 0
  project = var.project_id
  role    = "roles/storage.objectUser"
  member  = "serviceAccount:${google_service_account.jupyter[0].email}"
}

resource "google_service_account_iam_member" "jupyter_workload_identity" {
  count              = var.enable_jupyter ? 1 : 0
  service_account_id = google_service_account.jupyter[0].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[bioaf-jupyter/jupyter-hub]"
}

resource "google_service_account" "rstudio" {
  count        = var.enable_rstudio ? 1 : 0
  account_id   = "bioaf-rstudio"
  display_name = "bioAF RStudio Server"
}

resource "google_project_iam_member" "rstudio_storage" {
  count   = var.enable_rstudio ? 1 : 0
  project = var.project_id
  role    = "roles/storage.objectUser"
  member  = "serviceAccount:${google_service_account.rstudio[0].email}"
}

resource "google_service_account_iam_member" "rstudio_workload_identity" {
  count              = var.enable_rstudio ? 1 : 0
  service_account_id = google_service_account.rstudio[0].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[bioaf-rstudio/rstudio]"
}

# Namespace names and resource config for JupyterHub and RStudio.
# Actual namespace creation and Helm deployment is managed by the bioAF
# control plane when the component is enabled, not by Terraform directly.
locals {
  jupyter_namespace = "bioaf-jupyter"
  rstudio_namespace = "bioaf-rstudio"

  jupyter_resource_limits = var.enable_jupyter ? {
    cpu_limit    = var.jupyter_cpu_limit
    memory_limit = var.jupyter_memory_limit
    idle_timeout = var.session_idle_timeout_hours
  } : {}

  rstudio_resource_limits = var.enable_rstudio ? {
    cpu_limit    = var.rstudio_cpu_limit
    memory_limit = var.rstudio_memory_limit
  } : {}
}
