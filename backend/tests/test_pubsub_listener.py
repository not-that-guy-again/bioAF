"""Tests for the Pub/Sub listener service (Phase 21).

Tests 1-7: Listener lifecycle, message processing, ack/nack, retry.
"""

import asyncio
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import text


async def _seed_config(session, overrides=None):
    """Insert platform_config keys needed for tests."""
    defaults = {
        "auto_ingest_enabled": "false",
        "pubsub_subscription_name": "null",
        "pubsub_topic_name": "null",
        "ingest_cleanup_policy": "delete_after_copy",
        "storage_deployed": "true",
        "ingest_bucket_name": "bioaf-ingest-testorg",
        "raw_bucket_name": "bioaf-raw-testorg",
    }
    if overrides:
        defaults.update(overrides)
    for key, value in defaults.items():
        await session.execute(
            text(
                "INSERT INTO platform_config (key, value) VALUES (:k, :v) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            ).bindparams(k=key, v=value)
        )
    await session.commit()


def _make_pubsub_message(
    bucket="bioaf-ingest-testorg",
    name="PROJ1_EXP1_S001.fastq.gz",
    size="1048576",
    md5_hash=None,
):
    """Build a mock Pub/Sub ReceivedMessage."""
    if md5_hash is None:
        md5_hash = base64.b64encode(b"\x00" * 16).decode()
    data = json.dumps(
        {
            "bucket": bucket,
            "name": name,
            "size": size,
            "md5Hash": md5_hash,
            "timeCreated": "2026-03-12T10:00:00Z",
            "contentType": "application/gzip",
            "metageneration": "1",
        }
    ).encode()

    msg = MagicMock()
    msg.message.data = data
    msg.ack_id = "ack-id-1"
    return msg


@pytest.mark.asyncio
async def test_listener_starts_when_enabled(session):
    """Listener enters pull loop when auto_ingest_enabled=true and subscription exists."""
    await _seed_config(
        session,
        {
            "auto_ingest_enabled": "true",
            "pubsub_subscription_name": "bioaf-ingest-worker-testorg",
        },
    )

    from app.services.pubsub_listener import PubSubListener

    listener = PubSubListener()

    # Mock the subscriber client to avoid real GCP calls
    mock_subscriber = MagicMock()
    mock_subscriber.pull = MagicMock(return_value=MagicMock(received_messages=[]))

    with patch.object(listener, "_create_subscriber", return_value=mock_subscriber):
        # Run one iteration then cancel
        task = asyncio.create_task(listener.start(session))
        await asyncio.sleep(0.1)
        listener.stop()
        await asyncio.wait_for(task, timeout=2.0)

    # Assert pull was called (listener entered the loop)
    assert mock_subscriber.pull.called


@pytest.mark.asyncio
async def test_listener_skips_when_disabled(session):
    """Listener returns immediately when auto_ingest_enabled=false."""
    await _seed_config(session, {"auto_ingest_enabled": "false"})

    from app.services.pubsub_listener import PubSubListener

    listener = PubSubListener()
    await listener.start(session)
    # Should return without error or starting pull loop
    assert not listener.running


@pytest.mark.asyncio
async def test_listener_skips_when_no_subscription(session):
    """Listener returns when pubsub_subscription_name is null."""
    await _seed_config(
        session,
        {
            "auto_ingest_enabled": "true",
            "pubsub_subscription_name": "null",
        },
    )

    from app.services.pubsub_listener import PubSubListener

    listener = PubSubListener()
    await listener.start(session)
    assert not listener.running


@pytest.mark.asyncio
async def test_listener_processes_message(session):
    """Listener extracts GCS object metadata and calls ingest pipeline."""
    await _seed_config(
        session,
        {
            "auto_ingest_enabled": "true",
            "pubsub_subscription_name": "bioaf-ingest-worker-testorg",
        },
    )

    from app.services.pubsub_listener import PubSubListener

    listener = PubSubListener()
    msg = _make_pubsub_message()
    pull_response = MagicMock()
    pull_response.received_messages = [msg]

    mock_subscriber = MagicMock()
    # First pull returns message, second triggers stop
    call_count = 0

    def pull_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return pull_response
        listener.stop()
        return MagicMock(received_messages=[])

    mock_subscriber.pull = MagicMock(side_effect=pull_side_effect)
    mock_subscriber.acknowledge = MagicMock()

    mock_handler = AsyncMock()

    with (
        patch.object(listener, "_create_subscriber", return_value=mock_subscriber),
        patch.object(listener, "_handle_message", mock_handler),
    ):
        await listener.start(session)

    mock_handler.assert_called_once()
    call_args = mock_handler.call_args
    assert call_args[0][0]["name"] == "PROJ1_EXP1_S001.fastq.gz"


@pytest.mark.asyncio
async def test_listener_acks_on_success(session):
    """Listener acknowledges message after successful processing."""
    await _seed_config(
        session,
        {
            "auto_ingest_enabled": "true",
            "pubsub_subscription_name": "bioaf-ingest-worker-testorg",
        },
    )

    from app.services.pubsub_listener import PubSubListener

    listener = PubSubListener()
    msg = _make_pubsub_message()
    pull_response = MagicMock()
    pull_response.received_messages = [msg]

    mock_subscriber = MagicMock()
    call_count = 0

    def pull_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return pull_response
        listener.stop()
        return MagicMock(received_messages=[])

    mock_subscriber.pull = MagicMock(side_effect=pull_side_effect)
    mock_subscriber.acknowledge = MagicMock()

    with (
        patch.object(listener, "_create_subscriber", return_value=mock_subscriber),
        patch.object(listener, "_handle_message", AsyncMock()),
    ):
        await listener.start(session)

    mock_subscriber.acknowledge.assert_called_once()
    ack_call = mock_subscriber.acknowledge.call_args
    assert msg.ack_id in ack_call[1].get("ack_ids", ack_call[0][1] if len(ack_call[0]) > 1 else [])


@pytest.mark.asyncio
async def test_listener_nacks_on_failure(session):
    """Listener nacks message when processing raises an exception."""
    await _seed_config(
        session,
        {
            "auto_ingest_enabled": "true",
            "pubsub_subscription_name": "bioaf-ingest-worker-testorg",
        },
    )

    from app.services.pubsub_listener import PubSubListener

    listener = PubSubListener()
    msg = _make_pubsub_message()
    pull_response = MagicMock()
    pull_response.received_messages = [msg]

    mock_subscriber = MagicMock()
    call_count = 0

    def pull_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return pull_response
        listener.stop()
        return MagicMock(received_messages=[])

    mock_subscriber.pull = MagicMock(side_effect=pull_side_effect)
    mock_subscriber.modify_ack_deadline = MagicMock()

    with (
        patch.object(listener, "_create_subscriber", return_value=mock_subscriber),
        patch.object(listener, "_handle_message", AsyncMock(side_effect=Exception("processing failed"))),
    ):
        await listener.start(session)

    # Nack is done by setting ack deadline to 0
    mock_subscriber.modify_ack_deadline.assert_called_once()


@pytest.mark.asyncio
async def test_listener_retries_on_connection_error(session):
    """Listener retries with backoff when Pub/Sub client raises connection error."""
    await _seed_config(
        session,
        {
            "auto_ingest_enabled": "true",
            "pubsub_subscription_name": "bioaf-ingest-worker-testorg",
        },
    )

    from app.services.pubsub_listener import PubSubListener

    listener = PubSubListener()

    mock_subscriber = MagicMock()
    call_count = 0

    def pull_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise ConnectionError("Pub/Sub unavailable")
        listener.stop()
        return MagicMock(received_messages=[])

    mock_subscriber.pull = MagicMock(side_effect=pull_side_effect)

    with (
        patch.object(listener, "_create_subscriber", return_value=mock_subscriber),
        patch("app.services.pubsub_listener.RETRY_BASE_SECONDS", 0.01),
    ):
        await listener.start(session)

    # Pull should have been called at least 3 times (2 errors + 1 success)
    assert mock_subscriber.pull.call_count >= 3
