# bioAF - Bioinformatics Application Framework

A turnkey computational biology platform for small biotech companies (5-50 researchers), deployed on Google Cloud Platform. bioAF provides a web-based control plane for managing HPC clusters, notebook environments, pipeline engines, and data visualization tools — all provisioned through UI-driven Terraform.

## Architecture Overview

```text
Frontend (Next.js 14)  -->  Backend (FastAPI)  -->  Cloud SQL PostgreSQL 16
                                |
                         Terraform Runner
                                |
                    GCP Infrastructure
                    (GKE Autopilot, SLURM, Filestore,
                     GCS, Secret Manager, Cloud NAT)
```

**Key design decisions:**

- GCP-only infrastructure ([ADR-001](decisions/ADR-001-gcp-only.md))
- Email-based authentication ([ADR-003](decisions/ADR-003-email-auth.md))
- Tiered backup strategy ([ADR-004](decisions/ADR-004-tiered-backups.md))
- UI-driven Terraform — users never touch HCL ([ADR-007](decisions/ADR-007-ui-driven-terraform.md))
- All secrets in Secret Manager ([ADR-008](decisions/ADR-008-secret-manager.md))
- Immutable audit log ([ADR-009](decisions/ADR-009-immutable-audit.md))
- Data portability guarantees ([ADR-012](decisions/ADR-012-data-portability.md))

See all ADRs in [decisions/](decisions/).

## Quickstart

### Prerequisites

- Google Cloud SDK (`gcloud`) authenticated
- Terraform >= 1.7
- Python >= 3.12
- Node.js >= 20

### Deploy

```bash
# Install the CLI
pip install ./cli

# Deploy infrastructure and application
bioaf deploy --project my-gcp-project --region us-central1

# First login: navigate to the URL printed by the CLI
# The setup wizard walks you through creating the admin account
```

### First Login

1. Open the application URL
2. The setup wizard detects no admin exists and prompts you to create one
3. Verify your email address
4. Configure your organization name
5. Optionally configure SMTP for email invitations
6. Invite your team

## Development Setup

### Using Docker Compose (recommended)

```bash
# Start backend, frontend, and PostgreSQL
docker compose -f docker/docker-compose.dev.yml up

# Backend:  http://localhost:8000
# Frontend: http://localhost:3000
# Postgres: localhost:5432
```

### Manual Setup

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Database (requires PostgreSQL 16)
cd backend
alembic upgrade head
```

### Running Tests

```bash
# Unit tests (no database required)
cd backend && python -m pytest tests/test_terraform_service.py -v

# Full test suite (requires PostgreSQL)
docker compose -f docker/docker-compose.dev.yml up -d db
cd backend && python -m pytest tests/ -v
```

## Component Catalog

bioAF manages these infrastructure components through its UI:

| Component | Category | Dependencies |
|-----------|----------|-------------|
| SLURM HPC Cluster | Compute | None |
| Filestore NFS | Storage | SLURM |
| JupyterHub | Notebooks | SLURM, Filestore |
| RStudio Server | Notebooks | SLURM, Filestore |
| Nextflow | Pipelines | SLURM |
| Snakemake | Pipelines | SLURM |
| cellxgene | Visualization | None |
| QC Dashboard | Visualization | None |
| Meilisearch | Search | None |

## Phase Breakdown

- **Phase 1** (current): Foundation infrastructure + control plane shell
- **Phase 2**: Experiment tracking + data management
- **Phase 3**: Compute orchestration
- **Phase 4**: Pipeline integration
- **Phase 5**: Results and visualization

## Project Structure

```text
bioAF/
  backend/        FastAPI application
  frontend/       Next.js 14 application
  terraform/      GCP infrastructure as code
  helm/           Kubernetes deployment chart
  cli/            Python CLI (bioaf deploy/destroy)
  docker/         Dockerfiles and compose
  decisions/      Architecture Decision Records
  documentation/  Product and architecture specs
  scripts/        Database and utility scripts
```

## Contributing

See the ADRs in [decisions/](decisions/) for architectural context before making changes. All infrastructure changes must go through the UI-driven Terraform workflow (ADR-007). The audit log is immutable by design (ADR-009) — do not add UPDATE or DELETE operations on the audit_logs table.
