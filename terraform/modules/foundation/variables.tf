variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "us-central1"
}

variable "state_bucket_name" {
  description = "Name of the GCS bucket to store Terraform state"
  type        = string
}

variable "bucket_location" {
  description = "GCS bucket location (region or multi-region)"
  type        = string
  default     = "US"
}
