"""Destroy command for bioAF CLI."""

import os
import subprocess

import click

from bioaf_cli.utils.output import (
    console,
    print_success,
    print_error,
    print_warning,
    print_step,
    print_resource_table,
    print_panel,
)

TERRAFORM_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "terraform")
)

# Resources that can be preserved with --keep-data
DATA_RESOURCES = [
    "google_storage_bucket.raw_data",
    "google_storage_bucket.working_data",
    "google_storage_bucket.results",
    "google_storage_bucket.config_backups",
    "google_sql_database_instance.bioaf_db",
    "google_sql_database.bioaf_database",
]

ALL_RESOURCES = [
    {"name": "GKE cluster", "status": "[red]DESTROY[/red]"},
    {"name": "VPC and networking", "status": "[red]DESTROY[/red]"},
    {"name": "IAM service accounts", "status": "[red]DESTROY[/red]"},
    {"name": "Secret Manager secrets", "status": "[red]DESTROY[/red]"},
    {"name": "Cloud SQL PostgreSQL", "status": "[red]DESTROY[/red]"},
    {"name": "GCS buckets (raw, working, results, config)", "status": "[red]DESTROY[/red]"},
    {"name": "Kubernetes workloads", "status": "[red]DESTROY[/red]"},
]

KEEP_DATA_RESOURCES = [
    {"name": "GKE cluster", "status": "[red]DESTROY[/red]"},
    {"name": "VPC and networking", "status": "[red]DESTROY[/red]"},
    {"name": "IAM service accounts", "status": "[red]DESTROY[/red]"},
    {"name": "Secret Manager secrets", "status": "[red]DESTROY[/red]"},
    {"name": "Cloud SQL PostgreSQL", "status": "[green]PRESERVE[/green]"},
    {"name": "GCS buckets (raw, working, results, config)", "status": "[green]PRESERVE[/green]"},
    {"name": "Kubernetes workloads", "status": "[red]DESTROY[/red]"},
]


@click.command()
@click.option(
    "--keep-data",
    is_flag=True,
    default=False,
    help="Preserve GCS buckets and Cloud SQL database.",
)
@click.option(
    "--org-name",
    required=True,
    help="Organization name (required for confirmation).",
)
def destroy(keep_data: bool, org_name: str) -> None:
    """Destroy bioAF platform infrastructure."""
    console.print()
    console.rule("[bold red]bioAF Destroy[/bold red]")
    console.print()

    # ── Show resources ─────────────────────────────────────────────────
    if keep_data:
        print_warning("--keep-data is set. Data resources will be preserved.")
        console.print()
        print_resource_table("Resources", KEEP_DATA_RESOURCES)

        console.print()
        print_panel(
            "Preserved Resources",
            (
                "The following resources will [bold]NOT[/bold] be destroyed:\n"
                "\n"
                "  - GCS buckets (raw_data, working_data, results, config_backups)\n"
                "  - Cloud SQL PostgreSQL instance and database\n"
                "\n"
                "You can re-deploy later and reconnect to these data stores."
            ),
            style="green",
        )
    else:
        print_warning("ALL resources will be permanently destroyed.")
        console.print()
        print_resource_table("Resources", ALL_RESOURCES)

    console.print()

    # ── Confirmation ───────────────────────────────────────────────────
    console.print(
        f"[bold red]To confirm, type the organization name: [/bold red][bold]{org_name}[/bold]"
    )
    confirmation = click.prompt("Organization name")

    if confirmation != org_name:
        print_error(f"Confirmation failed. Expected '{org_name}', got '{confirmation}'.")
        raise SystemExit(1)

    console.print()

    # ── Terraform destroy ──────────────────────────────────────────────
    if keep_data:
        print_step("Running targeted terraform destroy (preserving data)...")
        # Build -target exclusions by destroying everything except data resources
        # Terraform doesn't support --exclude natively, so we remove data resources
        # from state tracking by using -target for non-data resources.
        tf_cmd = ["terraform", "destroy", "-auto-approve", "-input=false"]
        for resource in DATA_RESOURCES:
            tf_cmd += [f"-target={resource}"]

        # First, get the full state list and destroy non-data resources
        state_result = subprocess.run(
            ["terraform", "state", "list"],
            cwd=TERRAFORM_DIR,
            capture_output=True,
            text=True,
        )

        if state_result.returncode == 0:
            all_state_resources = state_result.stdout.strip().split("\n")
            non_data_resources = [
                r for r in all_state_resources
                if r.strip() and not any(r.startswith(d) for d in DATA_RESOURCES)
            ]

            tf_cmd = ["terraform", "destroy", "-auto-approve", "-input=false"]
            for resource in non_data_resources:
                tf_cmd += [f"-target={resource}"]
        else:
            print_warning("Could not read terraform state. Running full destroy with data exclusion.")
            tf_cmd = ["terraform", "destroy", "-auto-approve", "-input=false"]
    else:
        print_step("Running terraform destroy...")
        tf_cmd = ["terraform", "destroy", "-auto-approve", "-input=false"]

    result = subprocess.run(
        tf_cmd,
        cwd=TERRAFORM_DIR,
        capture_output=False,
        text=True,
    )

    console.print()

    if result.returncode != 0:
        print_error("Terraform destroy encountered errors. Check output above.")
        raise SystemExit(1)

    print_success("Terraform destroy completed")
    console.print()

    # ── Post-destroy audit ─────────────────────────────────────────────
    print_step("Running post-destroy audit...")

    # Check if any resources remain in state
    audit_result = subprocess.run(
        ["terraform", "state", "list"],
        cwd=TERRAFORM_DIR,
        capture_output=True,
        text=True,
    )

    if audit_result.returncode == 0 and audit_result.stdout.strip():
        remaining = audit_result.stdout.strip().split("\n")
        remaining = [r for r in remaining if r.strip()]

        if keep_data:
            data_remaining = [
                r for r in remaining
                if any(r.startswith(d) for d in DATA_RESOURCES)
            ]
            other_remaining = [
                r for r in remaining
                if not any(r.startswith(d) for d in DATA_RESOURCES)
            ]

            if data_remaining:
                print_success(f"{len(data_remaining)} data resource(s) preserved as expected.")
            if other_remaining:
                print_warning(
                    f"{len(other_remaining)} non-data resource(s) still in state. "
                    "Manual cleanup may be required."
                )
                for r in other_remaining:
                    console.print(f"    [dim]{r}[/dim]")
        else:
            print_warning(
                f"{len(remaining)} resource(s) still in state. Manual cleanup may be required."
            )
            for r in remaining:
                console.print(f"    [dim]{r}[/dim]")
    else:
        print_success("Post-destroy audit: no resources remain in state.")

    console.print()
    console.rule("[bold green]Destroy Complete[/bold green]")
    console.print()
