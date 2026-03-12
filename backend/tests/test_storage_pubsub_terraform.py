"""Tests for Terraform storage module Pub/Sub resources (Phase 21).

Tests:
23. Storage module includes Pub/Sub topic, subscription, notification, dead letter
24. Storage module outputs include pubsub_topic_name and pubsub_subscription_name
"""

from pathlib import Path


STORAGE_MODULE_DIR = Path(__file__).resolve().parent.parent / "terraform" / "modules" / "storage"


def test_storage_module_includes_pubsub_resources():
    """Verify storage module defines Pub/Sub topic, subscription, notification, and dead letter."""
    main_tf = STORAGE_MODULE_DIR / "main.tf"
    content = main_tf.read_text()

    assert 'resource "google_pubsub_topic" "ingest_events"' in content, (
        "main.tf should define google_pubsub_topic.ingest_events"
    )
    assert 'resource "google_pubsub_subscription" "ingest_worker"' in content, (
        "main.tf should define google_pubsub_subscription.ingest_worker"
    )
    assert 'resource "google_pubsub_topic" "ingest_dead_letter"' in content, (
        "main.tf should define google_pubsub_topic.ingest_dead_letter"
    )
    assert 'resource "google_pubsub_subscription" "ingest_dead_letter_sub"' in content, (
        "main.tf should define google_pubsub_subscription.ingest_dead_letter_sub"
    )
    assert 'resource "google_storage_notification" "ingest_notification"' in content, (
        "main.tf should define google_storage_notification.ingest_notification"
    )
    assert 'resource "google_pubsub_topic_iam_member" "gcs_publisher"' in content, (
        "main.tf should define IAM binding for GCS publisher"
    )
    assert "OBJECT_FINALIZE" in content, "Notification should filter on OBJECT_FINALIZE events"
    assert "ack_deadline_seconds" in content, "Subscription should set ack_deadline_seconds"


def test_storage_module_pubsub_outputs():
    """Verify outputs for Pub/Sub topic and subscription names exist."""
    outputs_tf = STORAGE_MODULE_DIR / "outputs.tf"
    content = outputs_tf.read_text()

    assert 'output "pubsub_topic_name"' in content, "outputs.tf should define pubsub_topic_name"
    assert 'output "pubsub_subscription_name"' in content, "outputs.tf should define pubsub_subscription_name"
