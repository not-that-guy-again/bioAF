# =============================================================================
# cellxgene + QC Dashboard (optional)
# Deployed on GKE — Terraform manages service accounts and storage access
# =============================================================================

resource "google_service_account" "cellxgene" {
  count        = var.enable_cellxgene ? 1 : 0
  account_id   = "bioaf-cellxgene"
  display_name = "bioAF cellxgene"
}

resource "google_project_iam_member" "cellxgene_storage" {
  count   = var.enable_cellxgene ? 1 : 0
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.cellxgene[0].email}"
}

resource "google_service_account_iam_member" "cellxgene_workload_identity" {
  count              = var.enable_cellxgene ? 1 : 0
  service_account_id = google_service_account.cellxgene[0].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[bioaf-cellxgene/cellxgene]"
}

resource "google_service_account" "qc_dashboard" {
  count        = var.enable_qc_dashboard ? 1 : 0
  account_id   = "bioaf-qc-dashboard"
  display_name = "bioAF QC Dashboard"
}

resource "google_project_iam_member" "qc_dashboard_storage" {
  count   = var.enable_qc_dashboard ? 1 : 0
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.qc_dashboard[0].email}"
}

resource "google_service_account_iam_member" "qc_dashboard_workload_identity" {
  count              = var.enable_qc_dashboard ? 1 : 0
  service_account_id = google_service_account.qc_dashboard[0].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[bioaf-qc/qc-dashboard]"
}

# GKE namespace for cellxgene
resource "kubernetes_namespace" "cellxgene" {
  count = var.enable_cellxgene ? 1 : 0

  metadata {
    name = "bioaf-cellxgene"
    labels = {
      component   = "cellxgene"
      environment = var.environment
    }
  }
}

# GKE namespace for QC dashboard
resource "kubernetes_namespace" "qc_dashboard" {
  count = var.enable_qc_dashboard ? 1 : 0

  metadata {
    name = "bioaf-qc"
    labels = {
      component   = "qc-dashboard"
      environment = var.environment
    }
  }
}

# QC dashboard needs write access for generating plot images
resource "google_project_iam_member" "qc_dashboard_storage_write" {
  count   = var.enable_qc_dashboard ? 1 : 0
  project = var.project_id
  role    = "roles/storage.objectCreator"
  member  = "serviceAccount:${google_service_account.qc_dashboard[0].email}"
}
