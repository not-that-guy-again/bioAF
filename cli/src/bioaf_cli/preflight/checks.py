"""Pre-flight checks for bioAF deployment."""

import json
from dataclasses import dataclass

from bioaf_cli.utils.gcp import run_gcloud_command, REQUIRED_APIS


@dataclass
class CheckResult:
    """Result of a single pre-flight check."""

    name: str
    passed: bool
    message: str


def check_project_exists(project_id: str) -> CheckResult:
    """Verify the GCP project exists and is accessible."""
    result = run_gcloud_command(["projects", "describe", project_id])
    if result.success:
        return CheckResult(
            name="Project exists",
            passed=True,
            message=f"Project '{project_id}' is accessible.",
        )
    return CheckResult(
        name="Project exists",
        passed=False,
        message=f"Project '{project_id}' not found or not accessible: {result.stderr.strip()}",
    )


def check_billing_enabled(project_id: str) -> CheckResult:
    """Verify billing is enabled on the project."""
    result = run_gcloud_command(
        ["billing", "projects", "describe", project_id],
    )
    if result.success:
        try:
            info = json.loads(result.stdout)
            if info.get("billingEnabled", False):
                return CheckResult(
                    name="Billing enabled",
                    passed=True,
                    message="Billing is enabled on the project.",
                )
            return CheckResult(
                name="Billing enabled",
                passed=False,
                message="Billing is not enabled. Enable billing at https://console.cloud.google.com/billing",
            )
        except json.JSONDecodeError:
            pass
    return CheckResult(
        name="Billing enabled",
        passed=False,
        message=f"Could not verify billing status: {result.stderr.strip()}",
    )


def check_apis_enabled(project_id: str) -> CheckResult:
    """Check that all required GCP APIs are enabled."""
    result = run_gcloud_command(
        ["services", "list", "--enabled"],
        project=project_id,
    )
    if not result.success:
        return CheckResult(
            name="Required APIs",
            passed=False,
            message=f"Could not list enabled APIs: {result.stderr.strip()}",
        )

    try:
        enabled_services = json.loads(result.stdout)
        enabled_names = {
            svc.get("config", {}).get("name", "")
            for svc in enabled_services
        }
    except json.JSONDecodeError:
        return CheckResult(
            name="Required APIs",
            passed=False,
            message="Could not parse API list response.",
        )

    missing = [api for api in REQUIRED_APIS if api not in enabled_names]
    if not missing:
        return CheckResult(
            name="Required APIs",
            passed=True,
            message=f"All {len(REQUIRED_APIS)} required APIs are enabled.",
        )
    return CheckResult(
        name="Required APIs",
        passed=False,
        message=f"Missing APIs: {', '.join(missing)}. Run 'bioaf deploy' with --enable-apis to enable them.",
    )


def check_iam_permissions(project_id: str) -> CheckResult:
    """Check that the current user has sufficient IAM permissions."""
    required_permissions = [
        "compute.networks.create",
        "container.clusters.create",
        "cloudsql.instances.create",
        "iam.serviceAccounts.create",
        "storage.buckets.create",
        "secretmanager.secrets.create",
    ]

    result = run_gcloud_command([
        "projects",
        "test-iam-permissions",
        project_id,
        f"--permissions={','.join(required_permissions)}",
    ])

    if not result.success:
        return CheckResult(
            name="IAM permissions",
            passed=False,
            message=f"Could not verify permissions: {result.stderr.strip()}",
        )

    try:
        response = json.loads(result.stdout)
        granted = set(response.get("permissions", []))
        missing = [p for p in required_permissions if p not in granted]
        if not missing:
            return CheckResult(
                name="IAM permissions",
                passed=True,
                message="All required IAM permissions are granted.",
            )
        return CheckResult(
            name="IAM permissions",
            passed=False,
            message=f"Missing permissions: {', '.join(missing)}. You need at least Editor or Owner role.",
        )
    except json.JSONDecodeError:
        return CheckResult(
            name="IAM permissions",
            passed=False,
            message="Could not parse IAM permissions response.",
        )


def run_preflight_checks(project_id: str) -> list[CheckResult]:
    """Run all pre-flight checks and return results.

    Args:
        project_id: GCP project ID to check.

    Returns:
        List of CheckResult objects for each check performed.
    """
    checks = [
        check_project_exists(project_id),
        check_billing_enabled(project_id),
        check_apis_enabled(project_id),
        check_iam_permissions(project_id),
    ]
    return checks
