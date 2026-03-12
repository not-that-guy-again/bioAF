terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {} # Configured dynamically by the executor
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  bucket_prefix = "bioaf"
}

resource "google_storage_bucket" "ingest" {
  name          = "${local.bucket_prefix}-ingest-${var.org_slug}"
  project       = var.project_id
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true
  versioning { enabled = true }

  labels = {
    managed_by = "bioaf"
    purpose    = "ingest"
  }
}

resource "google_storage_bucket" "raw" {
  name          = "${local.bucket_prefix}-raw-${var.org_slug}"
  project       = var.project_id
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true
  versioning { enabled = true }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  labels = {
    managed_by = "bioaf"
    purpose    = "raw-data"
  }
}

resource "google_storage_bucket" "working" {
  name          = "${local.bucket_prefix}-working-${var.org_slug}"
  project       = var.project_id
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true
  versioning { enabled = true }

  labels = {
    managed_by = "bioaf"
    purpose    = "working-data"
  }
}

resource "google_storage_bucket" "results" {
  name          = "${local.bucket_prefix}-results-${var.org_slug}"
  project       = var.project_id
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true
  versioning { enabled = true }

  labels = {
    managed_by = "bioaf"
    purpose    = "results"
  }
}

resource "google_storage_bucket" "config_backups" {
  name          = "${local.bucket_prefix}-config-backups-${var.org_slug}"
  project       = var.project_id
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true
  versioning { enabled = true }

  labels = {
    managed_by = "bioaf"
    purpose    = "config-backups"
  }
}
