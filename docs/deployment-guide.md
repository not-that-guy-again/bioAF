# bioAF Deployment Guide

## Prerequisites

- **GCP Project** with billing enabled
- **Google Cloud SDK** (`gcloud`) installed and authenticated
- **Terraform** >= 1.7
- **Python** >= 3.12
- **Node.js** >= 20
- A domain name (optional, for production TLS)

## GCP Project Setup

1. Create a new GCP project or select an existing one:

   ```bash
   gcloud projects create my-bioaf-project
   gcloud config set project my-bioaf-project
   ```

2. Enable required APIs:

   ```bash
   gcloud services enable \
     compute.googleapis.com \
     container.googleapis.com \
     sqladmin.googleapis.com \
     secretmanager.googleapis.com \
     file.googleapis.com \
     storage.googleapis.com
   ```

3. Create a service account for Terraform:

   ```bash
   gcloud iam service-accounts create bioaf-terraform \
     --display-name="bioAF Terraform"
   gcloud projects add-iam-policy-binding my-bioaf-project \
     --member="serviceAccount:bioaf-terraform@my-bioaf-project.iam.gserviceaccount.com" \
     --role="roles/editor"
   ```

## Deploy with the CLI

```bash
# Install the bioAF CLI
pip install ./cli

# Deploy (interactive wizard)
bioaf deploy --project my-bioaf-project --region us-central1

# The CLI will:
# 1. Provision Cloud SQL (PostgreSQL 16)
# 2. Create GKE Autopilot cluster
# 3. Deploy backend and frontend
# 4. Configure networking and secrets
# 5. Print the application URL
```

## Post-Deploy Configuration

### First Login

1. Navigate to the application URL printed by the deploy command
2. The setup wizard detects no admin exists and prompts you to create one
3. Verify your email address
4. Configure your organization name and settings

### SMTP Configuration

For email notifications and user invitations, configure SMTP in Admin > Settings:

- Host, port, username, password, and from address
- Test the configuration with the test email button

### Component Activation

From the Components page, enable the infrastructure components your team needs:

- **SLURM HPC Cluster** - Required for compute workloads
- **Filestore NFS** - Shared storage for notebooks and pipelines
- **JupyterHub / RStudio** - Interactive notebook environments
- **Nextflow / Snakemake** - Pipeline execution engines
- **cellxgene** - Single-cell data visualization

Each component is provisioned via Terraform when enabled through the UI.

### Backup Configuration

Backups are configured automatically with sensible defaults:

- Cloud SQL: Daily snapshots with 30-day retention, 7-day PITR
- Filestore: Daily snapshots with 14-day retention
- Platform config: Nightly exports to GCS

Review and adjust in Admin > Backup & Recovery.

### Budget Alerts

Set up cost monitoring in Admin > Cost Center:

- Set a monthly budget
- Enable threshold alerts at 50%, 80%, 100%
- Optionally enable scale-to-zero when budget is exceeded

## Upgrading

bioAF checks for new versions daily. When an update is available:

1. Go to Admin > Settings
2. Review the changelog
3. Click "Check for updates" to verify
4. Follow the upgrade flow which includes terraform plan review

## Teardown

```bash
bioaf destroy --project my-bioaf-project
```

All user data remains accessible via standard GCP tools. See [Life After bioAF](life-after-bioaf.md).
