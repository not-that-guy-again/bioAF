# =============================================================================
# Filestore NFS (optional, enable_filestore — depends on SLURM)
# =============================================================================

resource "google_filestore_instance" "bioaf_nfs" {
  count    = var.enable_filestore ? 1 : 0
  name     = "bioaf-nfs"
  location = var.zone
  tier     = "BASIC_HDD"

  file_shares {
    name       = "bioaf_shared"
    capacity_gb = 1024
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
