"""GCP helper utilities for bioAF CLI."""

import json
import subprocess
from dataclasses import dataclass


@dataclass
class GcloudResult:
    """Result of a gcloud command execution."""

    success: bool
    stdout: str
    stderr: str
    returncode: int


def run_gcloud_command(args: list[str], project: str | None = None) -> GcloudResult:
    """Run a gcloud command and return structured result.

    Args:
        args: List of gcloud command arguments (without the 'gcloud' prefix).
        project: Optional GCP project ID to pass as --project flag.

    Returns:
        GcloudResult with success status, stdout, stderr, and return code.
    """
    cmd = ["gcloud"] + args + ["--format=json"]
    if project:
        cmd += [f"--project={project}"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return GcloudResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
        )
    except FileNotFoundError:
        return GcloudResult(
            success=False,
            stdout="",
            stderr="gcloud CLI not found. Install the Google Cloud SDK: https://cloud.google.com/sdk/docs/install",
            returncode=1,
        )
    except subprocess.TimeoutExpired:
        return GcloudResult(
            success=False,
            stdout="",
            stderr="gcloud command timed out after 120 seconds.",
            returncode=1,
        )


def get_project_info(project_id: str) -> dict | None:
    """Get GCP project information.

    Returns:
        Project info dict if successful, None otherwise.
    """
    result = run_gcloud_command(["projects", "describe", project_id])
    if result.success:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None
    return None


def enable_apis(project_id: str, apis: list[str]) -> tuple[bool, list[str]]:
    """Enable a list of GCP APIs for the given project.

    Args:
        project_id: GCP project ID.
        apis: List of API service names to enable (e.g. 'container.googleapis.com').

    Returns:
        Tuple of (overall_success, list_of_failed_apis).
    """
    failed: list[str] = []
    for api in apis:
        result = run_gcloud_command(
            ["services", "enable", api],
            project=project_id,
        )
        if not result.success:
            failed.append(api)
    return len(failed) == 0, failed


REQUIRED_APIS = [
    "compute.googleapis.com",
    "container.googleapis.com",
    "sqladmin.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
    "storage.googleapis.com",
    "cloudbilling.googleapis.com",
    "serviceusage.googleapis.com",
    "file.googleapis.com",
]
