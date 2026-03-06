# bioAF - Bioinformatics Application Framework

A turnkey computational biology platform for small biotech companies (5-50 researchers), deployed on Google Cloud Platform. bioAF provides a web-based control plane for managing HPC clusters, notebook environments, pipeline engines, and data visualization tools -- all provisioned through UI-driven Terraform.

## Features

- **Experiment Tracking** - MINSEQE-compliant metadata, sample management, batch processing, project organization
- **Compute Orchestration** - SLURM HPC cluster, JupyterHub/RStudio notebooks, auto-scaling, quota management
- **Pipeline Engine** - Nextflow and Snakemake integration, pipeline catalog, run monitoring, parameter management
- **Data Management** - File upload/download, dataset browser, GCS storage integration, GEO export
- **Results & Visualization** - QC dashboards, cellxgene single-cell viewer, plot archive, search
- **Notifications** - Event-driven alerts via in-app, email (SMTP), and Slack webhooks
- **Cost Center** - GCP billing integration, budget alerts, component cost breakdown, projections
- **Backup & Recovery** - Tiered backups (Cloud SQL PITR, Filestore snapshots, config exports), one-click restore
- **Role-Based Access** - Four roles (admin, comp_bio, bench, viewer) with granular permissions
- **Upgrade System** - GitHub-based version checking, managed upgrade flow with rollback
- **Activity Feed & Access Logs** - Full audit trail and team activity tracking
- **GitOps** - Version-controlled platform configuration with diff and rollback

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
- Email-based authentication ([ADR-003](decisions/ADR-003-email-based-auth.md))
- Tiered backup strategy ([ADR-004](decisions/ADR-004-tiered-backup-strategy.md))
- UI-driven Terraform -- users never touch HCL ([ADR-007](decisions/ADR-007-ui-driven-terraform.md))
- All secrets in Secret Manager ([ADR-008](decisions/ADR-008-secret-manager.md))
- Immutable audit log ([ADR-009](decisions/ADR-009-immutable-audit-log.md))
- Event-driven notifications ([ADR-010](decisions/ADR-010-notification-system.md))
- Data portability guarantees ([ADR-012](decisions/ADR-012-data-portability.md))

See all ADRs in [docs/adr-index.md](docs/adr-index.md).

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

See the full [Deployment Guide](docs/deployment-guide.md) for detailed instructions.

## Documentation

- [Quickstart](docs/README.md) - Documentation hub
- [Deployment Guide](docs/deployment-guide.md) - Full deployment walkthrough
- [Bench Scientist Guide](docs/user-guide-bench.md) - Experiments, samples, results
- [Computational Biologist Guide](docs/user-guide-compbio.md) - Pipelines, notebooks, environments
- [Admin Guide](docs/user-guide-admin.md) - User management, costs, backups, notifications
- [Life After bioAF](docs/life-after-bioaf.md) - Data portability after teardown
- [ADR Index](docs/adr-index.md) - Architecture Decision Records

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
  docs/           User-facing documentation
  scripts/        Database and utility scripts
```

## Contributing

See the ADRs in [decisions/](decisions/) for architectural context before making changes. All infrastructure changes must go through the UI-driven Terraform workflow (ADR-007). The audit log is immutable by design (ADR-009).
