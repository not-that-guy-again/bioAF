# =============================================================================
# Meilisearch (optional, enable_meilisearch)
# Deployed on GKE — Terraform manages service account and persistent disk
# =============================================================================

resource "google_service_account" "meilisearch" {
  count        = var.enable_meilisearch ? 1 : 0
  account_id   = "bioaf-meilisearch"
  display_name = "bioAF Meilisearch"
}

resource "google_service_account_iam_member" "meilisearch_workload_identity" {
  count              = var.enable_meilisearch ? 1 : 0
  service_account_id = google_service_account.meilisearch[0].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[bioaf-meilisearch/meilisearch]"
}

resource "google_compute_disk" "meilisearch_data" {
  count = var.enable_meilisearch ? 1 : 0
  name  = "bioaf-meilisearch-data"
  type  = "pd-ssd"
  zone  = var.zone
  size  = 20

  labels = {
    component   = "meilisearch"
    environment = var.environment
  }
}
