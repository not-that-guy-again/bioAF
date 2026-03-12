output "ingest_bucket_name" {
  description = "Name of the ingest GCS bucket"
  value       = google_storage_bucket.ingest.name
}

output "raw_bucket_name" {
  description = "Name of the raw data GCS bucket"
  value       = google_storage_bucket.raw.name
}

output "working_bucket_name" {
  description = "Name of the working data GCS bucket"
  value       = google_storage_bucket.working.name
}

output "results_bucket_name" {
  description = "Name of the results GCS bucket"
  value       = google_storage_bucket.results.name
}

output "config_backups_bucket_name" {
  description = "Name of the config backups GCS bucket"
  value       = google_storage_bucket.config_backups.name
}
