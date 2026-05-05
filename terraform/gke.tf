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

# =============================================================================
# bioaf-managed tag binding (SA hardening)
# =============================================================================
# Attaches the project-scoped bioaf-managed=true Resource Manager tag created
# by the installer. The IAM Condition on bioaf-app's roles/container.admin
# binding only permits operations on resources carrying this tag, scoping
# the runtime SA to bioAF-managed clusters.
#
# Skipped when bioaf_bootstrap_sa_email is unset (e.g. dev plans against an
# uninitialised manifest). The tag value is referenced by namespaced name to
# match the installer's `<project_id>/bioaf-managed/true` form.

data "google_tags_tag_value" "bioaf_managed" {
  count       = var.bioaf_bootstrap_sa_email != "" ? 1 : 0
  parent      = "tagKeys/${data.google_tags_tag_key.bioaf_managed[0].name}"
  short_name  = "true"
}

data "google_tags_tag_key" "bioaf_managed" {
  count      = var.bioaf_bootstrap_sa_email != "" ? 1 : 0
  parent     = "projects/${var.project_id}"
  short_name = "bioaf-managed"
}

resource "google_tags_tag_binding" "bioaf_cluster_managed" {
  count     = var.bioaf_bootstrap_sa_email != "" ? 1 : 0
  parent    = "//container.googleapis.com/${google_container_cluster.bioaf_cluster.id}"
  tag_value = data.google_tags_tag_value.bioaf_managed[0].id
}
