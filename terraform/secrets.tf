# =============================================================================
# Google Secret Manager (ADR-008)
# =============================================================================

# Auto-generated JWT signing key
resource "random_password" "jwt_signing_key" {
  length  = 32
  special = false
}

# Secret: DB app password
resource "google_secret_manager_secret" "db_app_password" {
  secret_id = "bioaf-db-app-password"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_app_password" {
  secret      = google_secret_manager_secret.db_app_password.id
  secret_data = random_password.db_app_password.result
}

# Secret: DB admin password
resource "google_secret_manager_secret" "db_admin_password" {
  secret_id = "bioaf-db-admin-password"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_admin_password" {
  secret      = google_secret_manager_secret.db_admin_password.id
  secret_data = random_password.db_admin_password.result
}

# Secret: JWT signing key
resource "google_secret_manager_secret" "jwt_signing_key" {
  secret_id = "bioaf-jwt-signing-key"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "jwt_signing_key" {
  secret      = google_secret_manager_secret.jwt_signing_key.id
  secret_data = random_password.jwt_signing_key.result
}

# Secret: SMTP credentials (empty, populated during bootstrap)
resource "google_secret_manager_secret" "smtp_credentials" {
  secret_id = "bioaf-smtp-credentials"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "smtp_credentials" {
  secret      = google_secret_manager_secret.smtp_credentials.id
  secret_data = "{}"
}

# Secret: Slack webhook (empty, populated in admin settings)
resource "google_secret_manager_secret" "slack_webhook" {
  secret_id = "bioaf-slack-webhook"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "slack_webhook" {
  secret      = google_secret_manager_secret.slack_webhook.id
  secret_data = "{}"
}

# Secret: GitHub PAT (empty, populated when GitOps is configured)
resource "google_secret_manager_secret" "github_pat" {
  secret_id = "bioaf-github-pat"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "github_pat" {
  secret      = google_secret_manager_secret.github_pat.id
  secret_data = "{}"
}

# =============================================================================
# Dedicated service account for secret access
# =============================================================================

resource "google_service_account" "secret_accessor" {
  account_id   = "bioaf-secret-accessor"
  display_name = "bioAF Secret Accessor"
  description  = "Service account for bioAF control plane to access secrets"
}

# Per-secret IAM bindings (not project-wide)
resource "google_secret_manager_secret_iam_member" "db_app_password" {
  secret_id = google_secret_manager_secret.db_app_password.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.secret_accessor.email}"
}

resource "google_secret_manager_secret_iam_member" "db_admin_password" {
  secret_id = google_secret_manager_secret.db_admin_password.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.secret_accessor.email}"
}

resource "google_secret_manager_secret_iam_member" "jwt_signing_key" {
  secret_id = google_secret_manager_secret.jwt_signing_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.secret_accessor.email}"
}

resource "google_secret_manager_secret_iam_member" "smtp_credentials" {
  secret_id = google_secret_manager_secret.smtp_credentials.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.secret_accessor.email}"
}

resource "google_secret_manager_secret_iam_member" "slack_webhook" {
  secret_id = google_secret_manager_secret.slack_webhook.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.secret_accessor.email}"
}

resource "google_secret_manager_secret_iam_member" "github_pat" {
  secret_id = google_secret_manager_secret.github_pat.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.secret_accessor.email}"
}
