# ADR-004: Tiered Backup Strategy with Mandatory Database Backups

**Status:** Accepted
**Date:** 2026-03-05
**Deciders:** Brent (product owner)

## Context

bioAF manages several categories of data with different criticality levels, access patterns, and recovery requirements. A one-size-fits-all backup policy would either over-protect low-value data (wasteful) or under-protect high-value data (dangerous).

The experiment tracking database and audit log are the crown jewels — if they're lost, the entire auditability story collapses. GCS data is inherently durable but vulnerable to accidental deletion. Platform configuration should be recoverable but isn't worth the same investment as scientific data.

## Decision

Implement a five-tier backup strategy with different mechanisms and policies per data category. Database backups are mandatory and cannot be disabled. Other tiers have user-configurable retention.

### Tier 1: Database (Cloud SQL) — Mandatory

- Continuous WAL-based point-in-time recovery (PITR)
- Daily automated snapshots via Cloud SQL
- Default retention: 30 days PITR, 90 days snapshots
- Minimum enforceable: 7 days PITR, 30 days snapshots
- **Cannot be disabled.** The audit log's integrity is a core product promise.

### Tier 2: Platform Configuration (GCS JSON snapshots) — Configurable

bioAF exports its own configuration as JSON to a dedicated GCS bucket on a tiered retention schedule:

| Backup | Frequency | Retention |
|---|---|---|
| Nightly | Every night (configurable time) | 7 days rolling |
| Weekly | Final nightly of each week (Sunday) promoted | 1 month |
| Monthly | Final weekly of each month promoted | 1 year |
| After 1 year | Monthly snapshots roll off | Deleted |

Admin can adjust cadence (every 6, 12, or 24 hours) and retention lengths. Admin can disable config backups entirely (with a warning about risk).

### Tier 3: GCS Data Buckets — Always Protected

- Object versioning enabled on all buckets — **cannot be disabled via bioAF**
- Delete protection enabled at bucket level — **cannot be disabled via bioAF**
- Non-current version retention: 30 days default (configurable)
- Cross-region replication: optional toggle (off by default; doubles storage cost)

### Tier 4: Filestore (NFS) — Configurable

- Daily snapshots with 14-day retention (default)
- Frequency and retention configurable by admin
- Can be disabled if Filestore is not in use

### Tier 5: Terraform State — Always Protected

- Stored in GCS backend with object versioning (every apply preserves previous state)
- Not configurable — this is infrastructure state and must always be recoverable

## Rationale

- **Mandatory database backups** prevent the catastrophic scenario where someone disables backups to save a few dollars and then loses the audit trail or experiment history.
- **Tiered config retention (7d/1m/1y)** balances storage cost with recovery window. Most config errors are caught within days; the monthly/yearly snapshots cover "slowly creeping" misconfigurations.
- **GCS versioning + delete protection** is the lightest-weight protection for object storage. It handles both accidental deletion and accidental overwrite without the cost of cross-region replication.
- **User-configurable policies** respect that different teams have different risk tolerances and budgets. A funded Series B biotech handling clinical data wants aggressive retention; a pre-seed startup analyzing mouse data may want minimal.

## Consequences

- The bioAF UI must include a Backup & Recovery admin page with per-tier configuration controls.
- Database backup minimum enforcement must be implemented at the application level (prevent API calls that would set retention below minimums).
- GCS bucket versioning and delete protection are set during Terraform provisioning and are not exposed as toggleable in the UI.
- The config backup system needs a CronJob running on GKE that exports config JSON and manages the tiered promotion/deletion logic.
- Backup monitoring (last successful backup time, failures) must be surfaced in the dashboard and integrated with the notification system.
- Restore workflows must be documented and accessible from the UI: database PITR restore, config snapshot restore, GCS version recovery.
