# =============================================================================
# Filestore NFS (optional, enable_filestore — depends on SLURM)
# =============================================================================

resource "google_filestore_instance" "bioaf_nfs" {
  count    = var.enable_filestore ? 1 : 0
  name     = "bioaf-nfs"
  location = var.zone
  tier     = "BASIC_HDD"

  file_shares {
    name        = "bioaf_shared"
    capacity_gb = var.filestore_capacity_gb
  }

  networks {
    network = google_compute_network.bioaf_vpc.name
    modes   = ["MODE_IPV4"]
  }

  labels = {
    component   = "filestore"
    environment = var.environment
  }
}

# Daily backup for Filestore (ADR-004 Tier 4)
resource "google_filestore_backup" "daily" {
  count             = var.enable_filestore ? 1 : 0
  name              = "bioaf-nfs-daily"
  location          = var.region
  source_instance   = google_filestore_instance.bioaf_nfs[0].name
  source_file_share = "bioaf_shared"
}
