# =============================================================================
# Outputs
# =============================================================================

output "gke_cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.bioaf_cluster.name
}

output "gke_cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = google_container_cluster.bioaf_cluster.endpoint
  sensitive   = true
}

output "cloudsql_connection_name" {
  description = "Cloud SQL connection name for Cloud SQL Proxy"
  value       = google_sql_database_instance.bioaf_db.connection_name
}

output "cloudsql_private_ip" {
  description = "Cloud SQL private IP address"
  value       = google_sql_database_instance.bioaf_db.private_ip_address
  sensitive   = true
}

output "bucket_raw_data" {
  description = "Raw data GCS bucket name"
  value       = google_storage_bucket.raw_data.name
}

output "bucket_working_data" {
  description = "Working data GCS bucket name"
  value       = google_storage_bucket.working_data.name
}

output "bucket_results" {
  description = "Results GCS bucket name"
  value       = google_storage_bucket.results.name
}

output "bucket_config_backups" {
  description = "Config backups GCS bucket name"
  value       = google_storage_bucket.config_backups.name
}

output "control_plane_service_account" {
  description = "Control plane service account email"
  value       = google_service_account.control_plane.email
}

output "terraform_executor_service_account" {
  description = "Terraform executor service account email"
  value       = google_service_account.terraform_executor.email
}

output "db_app_password_secret_id" {
  description = "Secret Manager ID for DB app password"
  value       = google_secret_manager_secret.db_app_password.secret_id
  sensitive   = true
}

output "jwt_signing_key_secret_id" {
  description = "Secret Manager ID for JWT signing key"
  value       = google_secret_manager_secret.jwt_signing_key.secret_id
  sensitive   = true
}
