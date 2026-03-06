# =============================================================================
# Cloud SQL PostgreSQL Instance
# =============================================================================

resource "google_sql_database_instance" "bioaf_db" {
  name             = "bioaf-db-${random_id.suffix.hex}"
  database_version = "POSTGRES_16"
  region           = var.region

  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier              = var.db_tier
    availability_type = "ZONAL"
    disk_autoresize   = true

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.bioaf_vpc.id
      enable_private_path_for_google_cloud_services = true
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = var.db_pitr_retention_days
      backup_retention_settings {
        retained_backups = var.db_backup_retention_days
        retention_unit   = "COUNT"
      }
    }

    maintenance_window {
      day          = 7 # Sunday
      hour         = 3 # 3 AM
      update_track = "stable"
    }

    database_flags {
      name  = "log_checkpoints"
      value = "on"
    }

    database_flags {
      name  = "log_connections"
      value = "on"
    }

    database_flags {
      name  = "log_disconnections"
      value = "on"
    }
  }

  deletion_protection = true
}

resource "google_sql_database" "bioaf" {
  name     = "bioaf"
  instance = google_sql_database_instance.bioaf_db.name
}

# Application user
resource "random_password" "db_app_password" {
  length  = 32
  special = true
}

resource "google_sql_user" "bioaf_app" {
  name     = "bioaf_app"
  instance = google_sql_database_instance.bioaf_db.name
  password = random_password.db_app_password.result
}

# Admin user (for migrations)
resource "random_password" "db_admin_password" {
  length  = 32
  special = true
}

resource "google_sql_user" "bioaf_admin" {
  name     = "bioaf_admin"
  instance = google_sql_database_instance.bioaf_db.name
  password = random_password.db_admin_password.result
}
