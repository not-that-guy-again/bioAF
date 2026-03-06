# =============================================================================
# GKE Autopilot Cluster
# =============================================================================

resource "google_container_cluster" "bioaf_cluster" {
  name     = "bioaf-cluster"
  location = var.region

  # Autopilot mode
  enable_autopilot = true

  network    = google_compute_network.bioaf_vpc.id
  subnetwork = google_compute_subnetwork.bioaf_subnet.id

  ip_allocation_policy {
    cluster_secondary_range_name  = "gke-pods"
    services_secondary_range_name = "gke-services"
  }

  # Private cluster configuration
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  # Authorized networks for control plane access
  dynamic "master_authorized_networks_config" {
    for_each = length(var.gke_authorized_networks) > 0 ? [1] : []
    content {
      dynamic "cidr_blocks" {
        for_each = var.gke_authorized_networks
        content {
          cidr_block   = cidr_blocks.value.cidr_block
          display_name = cidr_blocks.value.display_name
        }
      }
    }
  }

  # Workload Identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Release channel
  release_channel {
    channel = "REGULAR"
  }

  # Deletion protection
  deletion_protection = false
}
