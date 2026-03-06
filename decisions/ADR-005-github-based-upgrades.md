# ADR-005: GitHub-Based Versioning and Upgrade System

**Status:** Accepted
**Date:** 2026-03-05
**Deciders:** Brent (product owner)

## Context

bioAF is a self-hosted platform deployed into customer GCP projects. Unlike a SaaS product, updates cannot be pushed centrally. Customers need a reliable, transparent mechanism to discover and apply updates to their bioAF instances.

Options considered:

1. **Container registry polling:** bioAF checks a container registry for new tags. Simple but doesn't communicate what changed.
2. **GitHub releases:** bioAF checks the GitHub repo for new release tags. Provides changelogs, release notes, and community transparency.
3. **Apt/yum-style package repository:** Over-engineered for this use case.
4. **Auto-update (pull and apply automatically):** Dangerous for infrastructure-managing software. A bad auto-update could destroy a customer's compute environment.

## Decision

bioAF versions are published as tagged releases on the bioAF GitHub repository. Each release publishes a container image to GitHub Container Registry (ghcr.io). The bioAF control plane queries the GitHub API for new release tags to detect available updates. All upgrades are admin-initiated and require explicit confirmation.

### Release Artifacts

Each GitHub release includes:

- Tagged container image on ghcr.io (e.g., `ghcr.io/bioaf/bioaf:v1.3.0`)
- Updated Terraform templates (if infrastructure changes are needed)
- Database migration scripts (if schema changes are needed)
- Changelog in the release body

### Update Detection

- bioAF control plane queries the GitHub Releases API on startup and on a daily schedule (configurable)
- Compares current running version tag against latest release tag
- When a newer version exists, displays a non-intrusive banner in the UI
- Admin settings page shows: current version, latest available, changelog diff, and upgrade history

### Upgrade Flow

1. Admin reviews changelog in the UI
2. Admin clicks "Upgrade" (or runs `bioaf upgrade` from CLI)
3. bioAF pulls new container image from ghcr.io
4. GKE performs a rolling update of control plane pods (zero downtime)
5. Database migrations run automatically with rollback support
6. If the new version includes Terraform template changes, bioAF generates a Terraform plan and presents it for admin review and confirmation before applying
7. Running SLURM jobs and notebook sessions are not interrupted
8. Upgrade event recorded in audit log

### Rollback

- Admin can revert to the previous version from the UI or via `bioaf rollback`
- Rollback reverts the control plane container image
- If Terraform changes were applied during upgrade, admin is prompted to confirm infrastructure rollback
- Database migration rollback is supported for one version back

## Rationale

- **GitHub is where the project lives.** bioAF is open-source. Users already interact with the GitHub repo for issues, discussions, and contributions. Using GitHub releases as the version source is natural.
- **ghcr.io is free for public repos.** No need for a separate container registry service.
- **Explicit admin confirmation prevents accidents.** Infrastructure-managing software should never auto-update. A Terraform change applied without review could destroy a running SLURM cluster.
- **Terraform plan review is critical.** Some bioAF updates may change infrastructure (e.g., new GKE config, new Cloud SQL settings). Showing the plan before applying gives admins confidence and control.
- **Rolling updates on GKE provide zero-downtime upgrades** for the control plane without complexity.

## Consequences

- The bioAF container image must be published to ghcr.io as part of the release CI pipeline.
- The control plane needs network egress to ghcr.io (for pulling images) and api.github.com (for version checks). This is already available via Cloud NAT.
- Semantic versioning should be used (MAJOR.MINOR.PATCH) with clear policies: MAJOR = breaking changes or major Terraform changes, MINOR = new features, PATCH = bug fixes and security patches.
- Version pinning must be supported for teams that want to control their upgrade cadence.
- Air-gapped deployments (no internet egress) would need a manual upgrade path: download the image, load it into a private registry, and run `bioaf upgrade --image=<local-registry>/bioaf:v1.3.0`. This is a v2 concern.
