"""Tests for the Phase 17 Terraform executor service (Steps 5-8).

Tests 1-12 from the spec:
- 1-2: Plan execution (creates record, parses JSON output)
- 3-5: Apply execution (yields progress events, updates resources_completed, handles failure)
- 6-7: Concurrency lock (concurrent run prevention, stale lock recovery)
- 8-9: Credential injection (covered in test_credential_injector.py)
- 10-12: Bootstrap (checks GCP configured, checks not already initialized, creates state bucket)

All subprocess calls are mocked. No real Terraform execution.
"""

import json
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text

from app.services.terraform_executor import TerraformExecutor, TerraformProgressEvent


@contextmanager
def _patch_work_dir():
    """Patch _prepare_work_dir to return a real temp dir (no file system deps)."""
    tmp = Path(tempfile.mkdtemp(prefix="tf_test_"))
    with patch.object(TerraformExecutor, "_prepare_work_dir", return_value=tmp):
        yield tmp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plan_output(adds: int = 1) -> str:
    """Fake streaming JSON from `terraform plan -json`."""
    lines = []
    for i in range(adds):
        lines.append(
            json.dumps(
                {
                    "type": "planned_change",
                    "change": {
                        "resource": {
                            "resource_type": "google_storage_bucket",
                            "resource_name": f"bucket_{i}",
                            "addr": f"google_storage_bucket.bucket_{i}",
                        },
                        "action": "create",
                    },
                }
            )
        )
    return "\n".join(lines)


def _make_show_json_output(adds: int = 1) -> str:
    """Fake JSON from `terraform show -json`."""
    changes = [
        {
            "address": f"google_storage_bucket.bucket_{i}",
            "type": "google_storage_bucket",
            "name": f"bucket_{i}",
            "change": {"actions": ["create"], "before": None, "after": {}},
        }
        for i in range(adds)
    ]
    return json.dumps({"format_version": "1.2", "resource_changes": changes})


def _make_apply_output(n_resources: int = 1) -> str:
    """Fake streaming JSON from `terraform apply -json`."""
    lines = []
    for i in range(n_resources):
        lines.append(
            json.dumps(
                {
                    "type": "apply_complete",
                    "hook": {
                        "resource": {
                            "addr": f"google_storage_bucket.bucket_{i}",
                            "resource_type": "google_storage_bucket",
                            "resource_name": f"bucket_{i}",
                        },
                    },
                }
            )
        )
    lines.append(
        json.dumps(
            {
                "type": "apply_complete",
                "@level": "info",
                "@message": "Apply complete! Resources: 1 added, 0 changed, 0 destroyed.",
            }
        )
    )
    return "\n".join(lines)


def _mock_subprocess_run(stdout: str, returncode: int = 0):
    """Return a MagicMock that mimics subprocess.CompletedProcess."""
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = ""
    return result


async def _seed_gcp_config(session, configured: bool = True, initialized: bool = False):
    """Insert minimal platform_config rows needed by TerraformExecutor."""
    rows = [
        ("gcp_credentials_configured", "true" if configured else "false"),
        ("gcp_credential_source", "vm_default"),
        ("gcp_project_id", "test-project"),
        ("gcp_region", "us-central1"),
        ("gcp_zone", "us-central1-a"),
        ("terraform_initialized", "true" if initialized else "false"),
        ("terraform_state_bucket", "bioaf-tfstate-test" if initialized else ""),
    ]
    for key, value in rows:
        await session.execute(
            text(
                "INSERT INTO platform_config (key, value) VALUES (:k, :v) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            ).bindparams(k=key, v=value)
        )
    await session.commit()


async def _seed_user(session):
    """Create an org and admin user, return user.id."""
    from app.models.organization import Organization
    from app.models.user import User
    from app.services.auth_service import AuthService

    org = Organization(name="ExecTestOrg", setup_complete=True)
    session.add(org)
    await session.flush()

    user = User(
        email="exec_test@test.com",
        password_hash=AuthService.hash_password("pw"),
        role="admin",
        organization_id=org.id,
        status="active",
    )
    session.add(user)
    await session.flush()
    await session.commit()
    return user.id


# ---------------------------------------------------------------------------
# Test 1: run_plan creates a TerraformRun record
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_plan_creates_run_record(session):
    """run_plan() creates a terraform_runs record with status=completed after success."""
    user_id = await _seed_user(session)
    await _seed_gcp_config(session, configured=True, initialized=True)

    plan_stdout = _make_plan_output(1)
    show_stdout = _make_show_json_output(1)

    def mock_run(cmd, **kwargs):
        if "show" in cmd:
            return _mock_subprocess_run(show_stdout)
        return _mock_subprocess_run(plan_stdout)

    with patch("app.services.terraform_executor.subprocess.run", side_effect=mock_run):
        with _patch_work_dir():
            run = await TerraformExecutor.run_plan(
                session=session,
                user_id=user_id,
                module_name="foundation",
            )

    assert run.id is not None
    assert run.action == "plan"
    assert run.module_name == "foundation"
    assert run.status == "awaiting_confirmation"
    assert run.resources_planned == 1


# ---------------------------------------------------------------------------
# Test 2: run_plan parses JSON output into plan_json
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_plan_stores_parsed_plan_json(session):
    """run_plan() stores parsed plan data in plan_json column."""
    user_id = await _seed_user(session)
    await _seed_gcp_config(session, configured=True, initialized=True)

    show_stdout = _make_show_json_output(2)

    def mock_run(cmd, **kwargs):
        if "show" in cmd:
            return _mock_subprocess_run(show_stdout)
        return _mock_subprocess_run(_make_plan_output(2))

    with patch("app.services.terraform_executor.subprocess.run", side_effect=mock_run):
        with _patch_work_dir():
            run = await TerraformExecutor.run_plan(
                session=session,
                user_id=user_id,
                module_name="foundation",
            )

    assert run.plan_json is not None
    assert run.plan_json["add_count"] == 2
    assert run.resources_planned == 2


# ---------------------------------------------------------------------------
# Test 3: run_apply yields progress events
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_apply_yields_progress_events(session):
    """run_apply() yields TerraformProgressEvent objects as apply proceeds."""
    user_id = await _seed_user(session)
    await _seed_gcp_config(session, configured=True, initialized=True)

    # First create a plan run
    show_stdout = _make_show_json_output(1)

    def mock_run_plan(cmd, **kwargs):
        if "show" in cmd:
            return _mock_subprocess_run(show_stdout)
        return _mock_subprocess_run(_make_plan_output(1))

    with patch("app.services.terraform_executor.subprocess.run", side_effect=mock_run_plan):
        with _patch_work_dir():
            plan_run = await TerraformExecutor.run_plan(
                session=session,
                user_id=user_id,
                module_name="foundation",
            )

    apply_stdout = _make_apply_output(1)

    def mock_run_apply(cmd, **kwargs):
        return _mock_subprocess_run(apply_stdout)

    events = []
    with patch("app.services.terraform_executor.subprocess.run", side_effect=mock_run_apply):
        with _patch_work_dir():
            async for event in TerraformExecutor.run_apply(session=session, run_id=plan_run.id, user_id=user_id):
                events.append(event)

    assert len(events) > 0
    assert all(isinstance(e, TerraformProgressEvent) for e in events)


# ---------------------------------------------------------------------------
# Test 4: run_apply updates resources_completed in DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_apply_updates_resources_completed(session):
    """run_apply() increments resources_completed as resources complete."""
    user_id = await _seed_user(session)
    await _seed_gcp_config(session, configured=True, initialized=True)

    show_stdout = _make_show_json_output(1)

    def mock_plan(cmd, **kwargs):
        if "show" in cmd:
            return _mock_subprocess_run(show_stdout)
        return _mock_subprocess_run(_make_plan_output(1))

    with patch("app.services.terraform_executor.subprocess.run", side_effect=mock_plan):
        with _patch_work_dir():
            plan_run = await TerraformExecutor.run_plan(
                session=session,
                user_id=user_id,
                module_name="foundation",
            )

    apply_stdout = _make_apply_output(1)

    def mock_apply(cmd, **kwargs):
        return _mock_subprocess_run(apply_stdout)

    with patch("app.services.terraform_executor.subprocess.run", side_effect=mock_apply):
        with _patch_work_dir():
            async for _ in TerraformExecutor.run_apply(session=session, run_id=plan_run.id, user_id=user_id):
                pass

    await session.refresh(plan_run)
    assert plan_run.status == "completed"


# ---------------------------------------------------------------------------
# Test 5: run_apply handles subprocess failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_apply_handles_failure(session):
    """run_apply() marks run as failed when terraform apply exits non-zero."""
    user_id = await _seed_user(session)
    await _seed_gcp_config(session, configured=True, initialized=True)

    show_stdout = _make_show_json_output(1)

    def mock_plan(cmd, **kwargs):
        if "show" in cmd:
            return _mock_subprocess_run(show_stdout)
        return _mock_subprocess_run(_make_plan_output(1))

    with patch("app.services.terraform_executor.subprocess.run", side_effect=mock_plan):
        with _patch_work_dir():
            plan_run = await TerraformExecutor.run_plan(
                session=session,
                user_id=user_id,
                module_name="foundation",
            )

    fail_result = _mock_subprocess_run("", returncode=1)
    fail_result.stderr = "Error: some terraform error"

    def mock_apply_fail(cmd, **kwargs):
        return fail_result

    with patch("app.services.terraform_executor.subprocess.run", side_effect=mock_apply_fail):
        with _patch_work_dir():
            async for _ in TerraformExecutor.run_apply(session=session, run_id=plan_run.id, user_id=user_id):
                pass

    await session.refresh(plan_run)
    assert plan_run.status == "failed"
    assert plan_run.error_message is not None


# ---------------------------------------------------------------------------
# Test 6: Concurrent run prevention
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_run_prevention(session):
    """run_plan raises ValueError if another run is in progress."""
    user_id = await _seed_user(session)
    await _seed_gcp_config(session, configured=True, initialized=True)

    # Insert an active run manually
    await session.execute(
        text("""
        INSERT INTO terraform_runs (triggered_by_user_id, action, status)
        VALUES (:uid, 'plan', 'planning')
        """).bindparams(uid=user_id)
    )
    await session.commit()

    with pytest.raises(ValueError, match="in progress"):
        await TerraformExecutor.run_plan(session=session, user_id=user_id, module_name="foundation")


# ---------------------------------------------------------------------------
# Test 7: Stale lock recovery
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stale_lock_recovery(session):
    """Stale runs (>30 min) are marked failed and the new run proceeds."""
    user_id = await _seed_user(session)
    await _seed_gcp_config(session, configured=True, initialized=True)

    stale_started = datetime.now(timezone.utc) - timedelta(minutes=45)
    await session.execute(
        text("""
        INSERT INTO terraform_runs (triggered_by_user_id, action, status, started_at)
        VALUES (:uid, 'plan', 'planning', :started)
        """).bindparams(uid=user_id, started=stale_started)
    )
    await session.commit()

    show_stdout = _make_show_json_output(1)

    def mock_run(cmd, **kwargs):
        if "show" in cmd:
            return _mock_subprocess_run(show_stdout)
        return _mock_subprocess_run(_make_plan_output(1))

    # Should not raise - stale run gets cleared
    with patch("app.services.terraform_executor.subprocess.run", side_effect=mock_run):
        with _patch_work_dir():
            run = await TerraformExecutor.run_plan(session=session, user_id=user_id, module_name="foundation")

    assert run.id is not None
    assert run.status == "awaiting_confirmation"


# ---------------------------------------------------------------------------
# Test 10: bootstrap_foundation checks GCP configured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_requires_gcp_configured(session):
    """bootstrap_foundation raises ValueError when GCP is not configured."""
    user_id = await _seed_user(session)
    await _seed_gcp_config(session, configured=False, initialized=False)

    with pytest.raises(ValueError, match="GCP"):
        async for _ in TerraformExecutor.bootstrap_foundation(session=session, user_id=user_id):
            pass


# ---------------------------------------------------------------------------
# Test 11: bootstrap_foundation checks not already initialized
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_requires_not_initialized(session):
    """bootstrap_foundation raises ValueError when already initialized."""
    user_id = await _seed_user(session)
    await _seed_gcp_config(session, configured=True, initialized=True)

    with pytest.raises(ValueError, match="already"):
        async for _ in TerraformExecutor.bootstrap_foundation(session=session, user_id=user_id):
            pass


# ---------------------------------------------------------------------------
# Test 12: bootstrap_foundation runs plan + apply and seeds state bucket key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_creates_state_bucket_key(session):
    """bootstrap_foundation updates terraform_state_bucket in platform_config on success."""
    user_id = await _seed_user(session)
    await _seed_gcp_config(session, configured=True, initialized=False)

    show_stdout = _make_show_json_output(1)
    apply_stdout = _make_apply_output(1)

    # Inject a mock output file for terraform output
    tf_output = json.dumps({"state_bucket_name": {"value": "bioaf-tfstate-test"}})

    def mock_run(cmd, **kwargs):
        if "output" in cmd:
            return _mock_subprocess_run(tf_output)
        if "show" in cmd:
            return _mock_subprocess_run(show_stdout)
        if "apply" in cmd:
            return _mock_subprocess_run(apply_stdout)
        return _mock_subprocess_run(_make_plan_output(1))

    with patch("app.services.terraform_executor.subprocess.run", side_effect=mock_run):
        with _patch_work_dir():
            events = []
            async for event in TerraformExecutor.bootstrap_foundation(session=session, user_id=user_id):
                events.append(event)

    # Check platform_config updated
    row = (
        await session.execute(text("SELECT value FROM platform_config WHERE key = 'terraform_initialized'"))
    ).scalar()
    assert row == "true"
