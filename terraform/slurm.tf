# =============================================================================
# SLURM HPC Cluster (optional, enable_slurm)
# =============================================================================

resource "google_service_account" "slurm_controller" {
  count        = var.enable_slurm ? 1 : 0
  account_id   = "bioaf-slurm-controller"
  display_name = "bioAF SLURM Controller"
}

resource "google_service_account" "slurm_compute" {
  count        = var.enable_slurm ? 1 : 0
  account_id   = "bioaf-slurm-compute"
  display_name = "bioAF SLURM Compute Nodes"
}

# SLURM controller node
resource "google_compute_instance" "slurm_controller" {
  count        = var.enable_slurm ? 1 : 0
  name         = "bioaf-slurm-controller"
  machine_type = "e2-standard-4"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 50
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.bioaf_subnet.id
  }

  service_account {
    email  = google_service_account.slurm_controller[0].email
    scopes = ["cloud-platform"]
  }

  metadata = {
    enable-oslogin = "TRUE"
  }

  metadata_startup_script = templatefile("../scripts/slurm/controller-startup.sh.tpl", {
    munge_key_secret            = google_secret_manager_secret.slurm_munge_key[0].secret_id
    project_id                  = var.project_id
    controller_hostname         = "bioaf-slurm-controller"
    standard_partition_nodes    = var.slurm_max_nodes_standard
    interactive_partition_nodes = var.slurm_max_nodes_interactive
    standard_instance_type      = var.slurm_instance_type_standard
    interactive_instance_type   = var.slurm_instance_type_interactive
  })

  tags = ["bioaf-slurm-controller"]

  labels = {
    component   = "slurm"
    role        = "controller"
    environment = var.environment
  }
}

# SLURM login node
resource "google_compute_instance" "slurm_login" {
  count        = var.enable_slurm ? 1 : 0
  name         = "bioaf-slurm-login"
  machine_type = "e2-standard-2"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 30
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.bioaf_subnet.id
  }

  service_account {
    email  = google_service_account.slurm_controller[0].email
    scopes = ["cloud-platform"]
  }

  metadata = {
    enable-oslogin = "TRUE"
  }

  metadata_startup_script = templatefile("../scripts/slurm/login-startup.sh.tpl", {
    munge_key_secret    = google_secret_manager_secret.slurm_munge_key[0].secret_id
    project_id          = var.project_id
    controller_hostname = "bioaf-slurm-controller"
    filestore_ip        = var.enable_filestore ? google_filestore_instance.bioaf_nfs[0].networks[0].ip_addresses[0] : ""
    raw_bucket          = google_storage_bucket.raw_data.name
    working_bucket      = google_storage_bucket.working_data.name
    results_bucket      = google_storage_bucket.results.name
  })

  tags = ["bioaf-slurm-login"]

  labels = {
    component   = "slurm"
    role        = "login"
    environment = var.environment
  }
}

# Standard compute partition — instance template
resource "google_compute_instance_template" "slurm_standard" {
  count        = var.enable_slurm ? 1 : 0
  name_prefix  = "bioaf-slurm-standard-"
  machine_type = var.slurm_instance_type_standard

  scheduling {
    preemptible       = var.slurm_use_spot_standard
    automatic_restart = !var.slurm_use_spot_standard
  }

  disk {
    source_image = "ubuntu-os-cloud/ubuntu-2204-lts"
    auto_delete  = true
    disk_size_gb = 100
  }

  network_interface {
    subnetwork = google_compute_subnetwork.bioaf_subnet.id
  }

  service_account {
    email  = google_service_account.slurm_compute[0].email
    scopes = ["cloud-platform"]
  }

  metadata = {
    enable-oslogin     = "TRUE"
    slurm-idle-timeout = var.slurm_idle_timeout_minutes
    startup-script = templatefile("../scripts/slurm/compute-startup.sh.tpl", {
      munge_key_secret    = google_secret_manager_secret.slurm_munge_key[0].secret_id
      project_id          = var.project_id
      controller_hostname = "bioaf-slurm-controller"
      filestore_ip        = var.enable_filestore ? google_filestore_instance.bioaf_nfs[0].networks[0].ip_addresses[0] : ""
      raw_bucket          = google_storage_bucket.raw_data.name
      working_bucket      = google_storage_bucket.working_data.name
      results_bucket      = google_storage_bucket.results.name
    })
  }

  labels = {
    component   = "slurm"
    partition   = "standard"
    environment = var.environment
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Standard compute partition — managed instance group
resource "google_compute_instance_group_manager" "slurm_standard" {
  count              = var.enable_slurm ? 1 : 0
  name               = "bioaf-slurm-standard-mig"
  base_instance_name = "bioaf-slurm-standard"
  zone               = var.zone
  target_size        = 0

  version {
    instance_template = google_compute_instance_template.slurm_standard[0].id
  }
}

# Interactive compute partition — instance template
resource "google_compute_instance_template" "slurm_interactive" {
  count        = var.enable_slurm ? 1 : 0
  name_prefix  = "bioaf-slurm-interactive-"
  machine_type = var.slurm_instance_type_interactive

  scheduling {
    preemptible       = false
    automatic_restart = true
  }

  disk {
    source_image = "ubuntu-os-cloud/ubuntu-2204-lts"
    auto_delete  = true
    disk_size_gb = 50
  }

  network_interface {
    subnetwork = google_compute_subnetwork.bioaf_subnet.id
  }

  service_account {
    email  = google_service_account.slurm_compute[0].email
    scopes = ["cloud-platform"]
  }

  metadata = {
    enable-oslogin = "TRUE"
    startup-script = templatefile("../scripts/slurm/compute-startup.sh.tpl", {
      munge_key_secret    = google_secret_manager_secret.slurm_munge_key[0].secret_id
      project_id          = var.project_id
      controller_hostname = "bioaf-slurm-controller"
      filestore_ip        = var.enable_filestore ? google_filestore_instance.bioaf_nfs[0].networks[0].ip_addresses[0] : ""
      raw_bucket          = google_storage_bucket.raw_data.name
      working_bucket      = google_storage_bucket.working_data.name
      results_bucket      = google_storage_bucket.results.name
    })
  }

  labels = {
    component   = "slurm"
    partition   = "interactive"
    environment = var.environment
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Interactive compute partition — managed instance group
resource "google_compute_instance_group_manager" "slurm_interactive" {
  count              = var.enable_slurm ? 1 : 0
  name               = "bioaf-slurm-interactive-mig"
  base_instance_name = "bioaf-slurm-interactive"
  zone               = var.zone
  target_size        = 0

  version {
    instance_template = google_compute_instance_template.slurm_interactive[0].id
  }
}

# Firewall rules for SLURM internal communication
resource "google_compute_firewall" "slurm_internal" {
  count   = var.enable_slurm ? 1 : 0
  name    = "bioaf-slurm-internal"
  network = google_compute_network.bioaf_vpc.id

  allow {
    protocol = "tcp"
    ports    = ["6817", "6818", "6819", "7321"]
  }

  source_tags = ["bioaf-slurm-controller", "bioaf-slurm-login", "bioaf-slurm-compute"]
  target_tags = ["bioaf-slurm-controller", "bioaf-slurm-login", "bioaf-slurm-compute"]
}

# Munge authentication key (shared secret for SLURM cluster)
resource "google_secret_manager_secret" "slurm_munge_key" {
  count     = var.enable_slurm ? 1 : 0
  secret_id = "bioaf-slurm-munge-key"

  replication {
    auto {}
  }

  labels = {
    component   = "slurm"
    environment = var.environment
  }
}

# IAP SSH firewall rule for login node access
resource "google_compute_firewall" "slurm_ssh_iap" {
  count   = var.enable_slurm ? 1 : 0
  name    = "bioaf-slurm-ssh-iap"
  network = google_compute_network.bioaf_vpc.id

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["bioaf-slurm-login"]
}

# Autoscaler for standard partition MIG
resource "google_compute_autoscaler" "slurm_standard" {
  count  = var.enable_slurm ? 1 : 0
  name   = "bioaf-slurm-standard-autoscaler"
  zone   = var.zone
  target = google_compute_instance_group_manager.slurm_standard[0].id

  autoscaling_policy {
    max_replicas    = var.slurm_max_nodes_standard
    min_replicas    = 0
    cooldown_period = 120
  }
}

# Autoscaler for interactive partition MIG
resource "google_compute_autoscaler" "slurm_interactive" {
  count  = var.enable_slurm ? 1 : 0
  name   = "bioaf-slurm-interactive-autoscaler"
  zone   = var.zone
  target = google_compute_instance_group_manager.slurm_interactive[0].id

  autoscaling_policy {
    max_replicas    = var.slurm_max_nodes_interactive
    min_replicas    = 0
    cooldown_period = 120
  }
}
