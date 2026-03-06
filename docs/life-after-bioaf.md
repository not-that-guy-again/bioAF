# Life After bioAF

bioAF is designed with data portability as a core principle (see [ADR-012](../decisions/ADR-012-data-portability.md)). If you stop using the platform, all your data remains accessible through standard tools.

## Preserved Assets

### Database (Cloud SQL PostgreSQL)

Your experiment metadata, sample records, pipeline configurations, and audit logs remain in Cloud SQL:

- Connect with any PostgreSQL client: `psql`, DBeaver, pgAdmin
- Export with `pg_dump` for migration to another database
- PITR backups are retained per your configured retention policy

### Files (Filestore / GCS)

All uploaded data files, pipeline outputs, and notebook files are stored in GCS buckets and Filestore:

- Access via `gsutil`, the GCP Console, or any S3-compatible client
- Bucket names follow the pattern: `bioaf-{org}-{type}` (e.g., `bioaf-myorg-data`, `bioaf-myorg-results`)
- Filestore NFS exports can be mounted from any GCE instance

### Notebooks

JupyterHub and RStudio notebooks are stored on Filestore:

- Mount the Filestore share on any compute instance
- Notebooks are standard `.ipynb` and `.Rmd` files
- Conda/pip environments are defined in standard `environment.yml` / `requirements.txt` files

### Pipeline Definitions

Nextflow and Snakemake pipeline definitions are standard workflow files:

- Nextflow: `*.nf` files with `nextflow.config`
- Snakemake: `Snakefile` with config YAML
- Run them directly on any compatible compute environment

### Terraform State

Infrastructure state is stored in a GCS backend bucket:

- Import into your own Terraform workspace
- Or use `terraform state list` to see all managed resources

### Platform Configuration

Nightly config backups in GCS contain:

- Component configuration
- User and organization settings
- Notification rules and preferences
- Exportable as JSON

## Recommended Migration Steps

1. **Export database**: `pg_dump -h <cloud-sql-ip> -U bioaf_app bioaf > bioaf_backup.sql`
2. **Copy files**: `gsutil -m cp -r gs://bioaf-myorg-data/ ./local-backup/`
3. **Download notebooks**: Mount Filestore or use `gcloud filestore` commands
4. **Save pipeline configs**: Copy from GCS results bucket
5. **Run teardown**: `bioaf destroy` removes only bioAF-managed infrastructure, not your data buckets (unless explicitly requested)
