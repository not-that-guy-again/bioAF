# =============================================================================
# Nextflow + Snakemake configuration (optional)
# Pipeline orchestration runs on SLURM — Terraform manages service accounts
# and deploys pipeline config files to the login node.
# =============================================================================

resource "google_service_account" "nextflow" {
  count        = var.enable_nextflow ? 1 : 0
  account_id   = "bioaf-nextflow"
  display_name = "bioAF Nextflow Executor"
}

resource "google_project_iam_member" "nextflow_storage" {
  count   = var.enable_nextflow ? 1 : 0
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.nextflow[0].email}"
}

resource "google_project_iam_member" "nextflow_logging" {
  count   = var.enable_nextflow ? 1 : 0
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.nextflow[0].email}"
}

# Deploy Nextflow config to login node when enabled
resource "null_resource" "nextflow_config" {
  count = var.enable_nextflow ? 1 : 0

  triggers = {
    slurm_controller = google_compute_instance.slurm_controller[0].id
  }

  provisioner "remote-exec" {
    inline = [
      "mkdir -p /etc/bioaf/pipelines",
      "cat > /etc/bioaf/pipelines/nextflow.config << 'CONFIGEOF'",
      templatefile("${path.module}/../scripts/pipelines/nextflow.config.tpl", {
        slurm_queue    = "standard"
        slurm_account  = "bioaf-default"
        container_cache = "/data/containers"
        results_dir    = "/data/results"
        work_dir       = "/data/working/nextflow"
      }),
      "CONFIGEOF",
    ]

    connection {
      type        = "ssh"
      host        = google_compute_instance.slurm_login[0].network_interface[0].network_ip
      user        = "bioaf"
      private_key = data.google_secret_manager_secret_version.slurm_ssh_key[0].secret_data
    }
  }
}

resource "google_service_account" "snakemake" {
  count        = var.enable_snakemake ? 1 : 0
  account_id   = "bioaf-snakemake"
  display_name = "bioAF Snakemake Executor"
}

resource "google_project_iam_member" "snakemake_storage" {
  count   = var.enable_snakemake ? 1 : 0
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.snakemake[0].email}"
}

resource "google_project_iam_member" "snakemake_logging" {
  count   = var.enable_snakemake ? 1 : 0
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.snakemake[0].email}"
}

# Deploy Snakemake SLURM profile to login node when enabled
resource "null_resource" "snakemake_profile" {
  count = var.enable_snakemake ? 1 : 0

  triggers = {
    slurm_controller = google_compute_instance.slurm_controller[0].id
  }

  provisioner "remote-exec" {
    inline = [
      "mkdir -p /etc/bioaf/pipelines/snakemake-profile",
      "cat > /etc/bioaf/pipelines/snakemake-profile/config.yaml << 'PROFILEEOF'",
      file("${path.module}/../scripts/pipelines/snakemake-profile/config.yaml"),
      "PROFILEEOF",
    ]

    connection {
      type        = "ssh"
      host        = google_compute_instance.slurm_login[0].network_interface[0].network_ip
      user        = "bioaf"
      private_key = data.google_secret_manager_secret_version.slurm_ssh_key[0].secret_data
    }
  }
}
