"""Event type string constants for the bioAF notification system."""

# Pipeline events
PIPELINE_COMPLETED = "pipeline.completed"
PIPELINE_FAILED = "pipeline.failed"
PIPELINE_STAGE_ERROR = "pipeline.stage_error"
PIPELINE_RUN_REVIEWED = "pipeline_run.reviewed"
PIPELINE_RUN_REVIEW_REMINDER = "pipeline_run.review_reminder"

# QC events
QC_RESULTS_READY = "qc.results_ready"

# Experiment events
EXPERIMENT_STATUS_CHANGED = "experiment.status_changed"

# Budget events
BUDGET_THRESHOLD_50 = "budget.threshold_50"
BUDGET_THRESHOLD_80 = "budget.threshold_80"
BUDGET_THRESHOLD_100 = "budget.threshold_100"

# Compute events
COMPUTE_NODE_FAILURE = "compute.node_failure"

# Component health events
COMPONENT_HEALTH_DEGRADED = "component.health_degraded"
COMPONENT_HEALTH_DOWN = "component.health_down"

# Backup events
BACKUP_FAILURE = "backup.failure"

# Quota events
QUOTA_WARNING = "quota.warning"

# Session events
SESSION_IDLE = "session.idle"

# Results events
RESULTS_PUBLISHED = "results.published"

# Data events
DATA_UPLOADED = "data.uploaded"

# Platform events
PLATFORM_UPDATE_AVAILABLE = "platform.update_available"

# Storage events
STORAGE_THRESHOLD = "storage.threshold"

# User events
USER_INVITATION_ACCEPTED = "user.invitation_accepted"

# Terraform events
TERRAFORM_APPLY_FAILURE = "terraform.apply_failure"

ALL_EVENT_TYPES = [
    PIPELINE_COMPLETED,
    PIPELINE_FAILED,
    PIPELINE_STAGE_ERROR,
    QC_RESULTS_READY,
    EXPERIMENT_STATUS_CHANGED,
    BUDGET_THRESHOLD_50,
    BUDGET_THRESHOLD_80,
    BUDGET_THRESHOLD_100,
    COMPUTE_NODE_FAILURE,
    COMPONENT_HEALTH_DEGRADED,
    COMPONENT_HEALTH_DOWN,
    BACKUP_FAILURE,
    QUOTA_WARNING,
    SESSION_IDLE,
    RESULTS_PUBLISHED,
    DATA_UPLOADED,
    PLATFORM_UPDATE_AVAILABLE,
    STORAGE_THRESHOLD,
    USER_INVITATION_ACCEPTED,
    TERRAFORM_APPLY_FAILURE,
    PIPELINE_RUN_REVIEWED,
    PIPELINE_RUN_REVIEW_REMINDER,
]

# Severity mapping for event types
EVENT_SEVERITY = {
    PIPELINE_COMPLETED: "info",
    PIPELINE_FAILED: "critical",
    PIPELINE_STAGE_ERROR: "warning",
    QC_RESULTS_READY: "info",
    EXPERIMENT_STATUS_CHANGED: "info",
    BUDGET_THRESHOLD_50: "info",
    BUDGET_THRESHOLD_80: "warning",
    BUDGET_THRESHOLD_100: "critical",
    COMPUTE_NODE_FAILURE: "critical",
    COMPONENT_HEALTH_DEGRADED: "warning",
    COMPONENT_HEALTH_DOWN: "critical",
    BACKUP_FAILURE: "critical",
    QUOTA_WARNING: "warning",
    SESSION_IDLE: "info",
    RESULTS_PUBLISHED: "info",
    DATA_UPLOADED: "info",
    PLATFORM_UPDATE_AVAILABLE: "info",
    STORAGE_THRESHOLD: "warning",
    USER_INVITATION_ACCEPTED: "info",
    TERRAFORM_APPLY_FAILURE: "critical",
    PIPELINE_RUN_REVIEWED: "info",
    PIPELINE_RUN_REVIEW_REMINDER: "warning",
}
