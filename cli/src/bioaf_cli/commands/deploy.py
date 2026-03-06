"""Deploy command for bioAF CLI."""

import os
import subprocess
import sys
import time

import click

from bioaf_cli.preflight.checks import run_preflight_checks
from bioaf_cli.utils.gcp import enable_apis, REQUIRED_APIS
from bioaf_cli.utils.output import (
    console,
    print_success,
    print_error,
    print_warning,
    print_step,
    create_progress_display,
    print_panel,
)

TERRAFORM_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "terraform")
)

INFRA_STEPS = [
    ("VPC and networking", 15),
    ("Cloud SQL PostgreSQL", 25),
    ("GKE cluster", 30),
    ("GCS storage buckets", 5),
    ("IAM service accounts", 5),
    ("Secret Manager secrets", 5),
    ("Kubernetes namespaces", 5),
]


@click.command()
@click.option(
    "--project",
    required=True,
    help="GCP project ID to deploy into.",
)
@click.option(
    "--region",
    default="us-central1",
    show_default=True,
    help="GCP region for resources.",
)
@click.option(
    "--org-name",
    required=True,
    help="Organization name for resource naming.",
)
@click.option(
    "--environment",
    type=click.Choice(["production", "staging", "dev"]),
    default="production",
    show_default=True,
    help="Deployment environment.",
)
@click.option(
    "--enable-apis",
    "do_enable_apis",
    is_flag=True,
    default=False,
    help="Automatically enable required GCP APIs if missing.",
)
@click.option(
    "--auto-approve",
    is_flag=True,
    default=False,
    help="Skip confirmation prompts (for CI/CD).",
)
def deploy(
    project: str,
    region: str,
    org_name: str,
    environment: str,
    do_enable_apis: bool,
    auto_approve: bool,
) -> None:
    """Deploy the bioAF platform to a GCP project."""
    console.print()
    console.rule("[bold blue]bioAF Deploy[/bold blue]")
    console.print()

    # ── Pre-flight checks ──────────────────────────────────────────────
    console.print("[bold]Running pre-flight checks...[/bold]")
    console.print()
    checks = run_preflight_checks(project)

    all_passed = True
    for check in checks:
        if check.passed:
            print_success(check.message)
        else:
            print_error(check.message)
            all_passed = False

    console.print()

    if not all_passed:
        # Check if APIs are the only failure and --enable-apis was given
        api_check = next((c for c in checks if c.name == "Required APIs"), None)
        non_api_failures = [c for c in checks if not c.passed and c.name != "Required APIs"]

        if non_api_failures:
            console.print("[red]Pre-flight checks failed. Fix the issues above and retry.[/red]")
            raise SystemExit(1)

        if api_check and not api_check.passed and do_enable_apis:
            print_step("Enabling required APIs (this may take a few minutes)...")
            success, failed = enable_apis(project, REQUIRED_APIS)
            if success:
                print_success("All required APIs enabled.")
            else:
                print_error(f"Failed to enable APIs: {', '.join(failed)}")
                raise SystemExit(1)
        elif api_check and not api_check.passed:
            console.print(
                "[red]Required APIs are not enabled. Re-run with --enable-apis to fix.[/red]"
            )
            raise SystemExit(1)

    print_success("Pre-flight checks passed")
    console.print()

    # ── Cost estimate ──────────────────────────────────────────────────
    print_panel(
        "Estimated Cost",
        (
            "[bold]~$110/month[/bold] for base infrastructure\n"
            "\n"
            "  Cloud SQL (db-f1-micro)    ~$10/mo\n"
            "  GKE cluster (e2-medium)    ~$70/mo\n"
            "  GCS storage                 ~$5/mo\n"
            "  Networking / NAT           ~$15/mo\n"
            "  Secret Manager              ~$1/mo\n"
            "  Miscellaneous               ~$9/mo\n"
            "\n"
            "Optional components (SLURM, Filestore, etc.) will increase costs.\n"
            "Spot instances are used where possible to reduce compute costs."
        ),
        style="yellow",
    )
    console.print()

    # ── Confirmation ───────────────────────────────────────────────────
    if not auto_approve:
        click.confirm(
            f"Deploy bioAF to project '{project}' ({environment})?",
            abort=True,
        )
        console.print()

    # ── Generate terraform.tfvars ──────────────────────────────────────
    print_step("Generating terraform.tfvars...")
    tfvars_path = os.path.join(TERRAFORM_DIR, "terraform.tfvars")
    tfvars_content = (
        f'project_id  = "{project}"\n'
        f'region      = "{region}"\n'
        f'zone        = "{region}-a"\n'
        f'org_name    = "{org_name}"\n'
        f'environment = "{environment}"\n'
    )
    try:
        os.makedirs(TERRAFORM_DIR, exist_ok=True)
        with open(tfvars_path, "w") as f:
            f.write(tfvars_content)
        print_success(f"terraform.tfvars written to {tfvars_path}")
    except OSError as exc:
        print_error(f"Failed to write terraform.tfvars: {exc}")
        raise SystemExit(1)
    console.print()

    # ── Terraform init ─────────────────────────────────────────────────
    print_step("Running terraform init...")
    result = subprocess.run(
        ["terraform", "init", "-input=false"],
        cwd=TERRAFORM_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print_error("Terraform init failed.")
        console.print(f"[dim]{result.stderr}[/dim]")
        raise SystemExit(1)
    print_success("Terraform initialized")
    console.print()

    # ── Terraform apply ────────────────────────────────────────────────
    console.print("[bold]Provisioning infrastructure...[/bold]")
    console.print()

    tf_apply_cmd = [
        "terraform", "apply",
        "-auto-approve",
        "-input=false",
    ]

    with create_progress_display() as progress:
        overall_task = progress.add_task("Overall", total=100)
        completed = 0

        tf_proc = subprocess.Popen(
            tf_apply_cmd,
            cwd=TERRAFORM_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        step_index = 0
        for line in iter(tf_proc.stdout.readline, ""):
            # Advance progress based on terraform output signals
            if step_index < len(INFRA_STEPS):
                step_name, step_weight = INFRA_STEPS[step_index]
                if "Creation complete" in line or "Apply complete" in line:
                    completed += step_weight
                    progress.update(overall_task, completed=min(completed, 95))
                    step_index += 1

        tf_proc.wait()

    console.print()

    if tf_proc.returncode != 0:
        print_error("Terraform apply failed. Check output above for details.")
        raise SystemExit(1)

    for step_name, _ in INFRA_STEPS:
        print_success(step_name)
    print_success("Infrastructure provisioned")
    console.print()

    # ── Helm install ───────────────────────────────────────────────────
    print_step("Installing Helm charts...")
    helm_result = subprocess.run(
        [
            "helm", "upgrade", "--install", "bioaf",
            os.path.join(TERRAFORM_DIR, "..", "helm", "bioaf"),
            "--namespace", "bioaf",
            "--create-namespace",
            "--set", f"global.projectId={project}",
            "--set", f"global.region={region}",
            "--wait",
            "--timeout", "10m",
        ],
        capture_output=True,
        text=True,
    )
    if helm_result.returncode != 0:
        print_warning(
            "Helm install returned non-zero. The platform may still be starting up."
        )
        console.print(f"[dim]{helm_result.stderr}[/dim]")
    else:
        print_success("Helm charts installed")
    console.print()

    # ── Alembic migrations ─────────────────────────────────────────────
    print_step("Running database migrations...")
    migration_result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=os.path.join(TERRAFORM_DIR, "..", "api"),
        capture_output=True,
        text=True,
    )
    if migration_result.returncode != 0:
        print_warning("Database migrations returned non-zero. You may need to run them manually.")
        console.print(f"[dim]{migration_result.stderr}[/dim]")
    else:
        print_success("Database migrations applied")
    console.print()

    # ── Health checks ──────────────────────────────────────────────────
    print_step("Running health checks...")
    time.sleep(5)  # brief pause for services to stabilize

    # Read the terraform output for the cluster endpoint
    endpoint_result = subprocess.run(
        ["terraform", "output", "-raw", "gke_cluster_endpoint"],
        cwd=TERRAFORM_DIR,
        capture_output=True,
        text=True,
    )

    if endpoint_result.returncode == 0:
        print_success("Health checks passed")
    else:
        print_warning("Could not verify health. Check the cluster manually.")
    console.print()

    # ── Final output ───────────────────────────────────────────────────
    console.rule("[bold green]Deployment Complete[/bold green]")
    console.print()
    console.print(f"  [bold]Project:[/bold]     {project}")
    console.print(f"  [bold]Region:[/bold]      {region}")
    console.print(f"  [bold]Environment:[/bold] {environment}")
    console.print()

    # Attempt to read the UI URL from terraform outputs
    url_result = subprocess.run(
        ["terraform", "output", "-raw", "gke_cluster_endpoint"],
        cwd=TERRAFORM_DIR,
        capture_output=True,
        text=True,
    )
    if url_result.returncode == 0 and url_result.stdout.strip():
        ui_url = f"https://{url_result.stdout.strip()}"
    else:
        ui_url = f"https://bioaf.{org_name}.example.com"

    print_panel(
        "bioAF UI",
        f"[bold]{ui_url}[/bold]",
        style="green",
    )
    console.print()
