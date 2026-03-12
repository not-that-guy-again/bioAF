output "cluster_name" {
  value       = google_container_cluster.bioaf.name
  description = "Name of the GKE cluster"
}

output "cluster_endpoint" {
  value       = google_container_cluster.bioaf.endpoint
  description = "GKE cluster API endpoint URL"
}

output "cluster_ca_cert" {
  value       = google_container_cluster.bioaf.master_auth[0].cluster_ca_certificate
  description = "GKE cluster CA certificate (base64)"
  sensitive   = true
}
