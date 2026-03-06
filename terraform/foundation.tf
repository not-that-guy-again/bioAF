# =============================================================================
# VPC and Networking
# =============================================================================

resource "google_compute_network" "bioaf_vpc" {
  name                    = "bioaf-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "bioaf_subnet" {
  name                     = "bioaf-subnet"
  ip_cidr_range            = "10.0.0.0/20"
  region                   = var.region
  network                  = google_compute_network.bioaf_vpc.id
  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "gke-pods"
    ip_cidr_range = "10.4.0.0/14"
  }

  secondary_ip_range {
    range_name    = "gke-services"
    ip_cidr_range = "10.8.0.0/20"
  }
}

# =============================================================================
# Cloud Router and Cloud NAT
# =============================================================================

resource "google_compute_router" "bioaf_router" {
  name    = "bioaf-router"
  region  = var.region
  network = google_compute_network.bioaf_vpc.id
}

resource "google_compute_router_nat" "bioaf_nat" {
  name                               = "bioaf-nat"
  router                             = google_compute_router.bioaf_router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# =============================================================================
# Firewall Rules
# =============================================================================

resource "google_compute_firewall" "allow_internal" {
  name    = "bioaf-allow-internal"
  network = google_compute_network.bioaf_vpc.id

  allow {
    protocol = "tcp"
  }

  allow {
    protocol = "udp"
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = ["10.0.0.0/20", "10.4.0.0/14", "10.8.0.0/20"]
}

resource "google_compute_firewall" "allow_iap_ssh" {
  name    = "bioaf-allow-iap-ssh"
  network = google_compute_network.bioaf_vpc.id

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  # IAP IP range
  source_ranges = ["35.235.240.0/20"]
}

resource "google_compute_firewall" "deny_all_ingress" {
  name     = "bioaf-deny-all-ingress"
  network  = google_compute_network.bioaf_vpc.id
  priority = 65534

  deny {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/0"]
}

# =============================================================================
# Private Service Connection (for Cloud SQL private IP)
# =============================================================================

resource "google_compute_global_address" "private_ip_range" {
  name          = "bioaf-private-ip-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.bioaf_vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.bioaf_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]
}
