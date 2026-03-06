# Architecture Decision Records

This directory contains the architectural decision records (ADRs) for the bioAF project. Each ADR documents a significant architectural decision, its context, rationale, and consequences.

## Index

| ADR | Title | Status |
|---|---|---|
| [ADR-001](ADR-001-gcp-only.md) | GCP as Sole Supported Cloud Provider | Accepted |
| [ADR-002](ADR-002-mandatory-optional-split.md) | Mandatory Foundation with Optional Components | Accepted |
| [ADR-003](ADR-003-email-based-auth.md) | Email-Based Authentication as Primary Auth Method | Accepted |
| [ADR-004](ADR-004-tiered-backup-strategy.md) | Tiered Backup Strategy with Mandatory Database Backups | Accepted |
| [ADR-005](ADR-005-github-based-upgrades.md) | GitHub-Based Versioning and Upgrade System | Accepted |
| [ADR-006](ADR-006-experiment-tracking-as-foundation.md) | Experiment Tracking as Architectural Foundation | Accepted |
| [ADR-007](ADR-007-ui-driven-terraform.md) | UI-Driven Terraform Execution for Infrastructure Management | Accepted |
| [ADR-008](ADR-008-secret-manager.md) | Google Secret Manager for All Secrets | Accepted |
| [ADR-009](ADR-009-immutable-audit-log.md) | Immutable Audit Log via Database-Level Enforcement | Accepted |
| [ADR-010](ADR-010-notification-system.md) | Built-in Notification System with Email and Slack Connectors | Accepted |
| [ADR-011](ADR-011-scrna-seq-initial-scope.md) | Single-Cell RNA-seq as Initial Workflow Scope | Accepted |
| [ADR-012](ADR-012-data-portability.md) | Customer Owns All Data and Infrastructure State | Accepted |

## How to Use This Directory

- **New decisions** should be added as `ADR-NNN-short-title.md` and registered in this index.
- **Superseded decisions** should have their status changed to "Superseded by ADR-NNN" rather than being deleted.
- **Proposed decisions** that haven't been accepted yet should use status "Proposed".

## Template

```markdown
# ADR-NNN: Title

**Status:** Proposed | Accepted | Superseded by ADR-NNN
**Date:** YYYY-MM-DD
**Deciders:** Names

## Context
What is the issue that we're seeing that is motivating this decision?

## Decision
What is the change that we're proposing and/or doing?

## Rationale
Why is this the best choice among the alternatives considered?

## Consequences
What becomes easier or more difficult to do because of this change?
```
