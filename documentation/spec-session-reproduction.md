# Spec: Session Reproduction

**Status:** Draft
**Date:** 2026-03-27
**Depends on:** Notebook File I/O with Git-Backed History (Phase 1)

---

## Overview

Users need to recreate any past notebook session to continue analysis, verify results, or iterate on earlier work. Since notebook sessions are ephemeral (pods are deleted on stop), reproduction means launching a new session with the same configuration, the same input files, the same notebook state (via git checkout), and the same compute environment -- with the option to adjust settings before launch.

---

## 1. Session Reproduction Flow

### User Experience

1. User navigates to a past session (via session history, experiment detail, or provenance view)
2. Clicks "Reproduce" button
3. A pre-filled launch modal appears with:
   - **Session type:** pre-selected (jupyter/rstudio) matching the original
   - **Resource profile:** pre-selected (small/medium/large) matching the original, editable
   - **Environment version:** pre-selected matching the original, editable (dropdown shows available versions)
   - **Input files:** pre-checked in the file tree matching the original session's input files
   - **Git branch/commit:** displayed as read-only context ("Will restore notebook state from session #{id}")
4. User can modify any of these settings before launching
5. Click "Launch" starts the session

### What Happens on Launch

1. Normal session launch flow (create pod, sync home directory)
2. Input files from the original session are mounted (user can add/remove before launch)
3. Git clone + checkout the specific commit from the original session's last commit
4. The notebook files appear exactly as they were when the original session stopped
5. A new branch is created from that commit: `reproduce/{original_session_id}-{new_session_id}`

---

## 2. Data Model

### Existing Fields Used

The `compute_sessions` table already stores everything needed for reproduction:

| Field | Use in Reproduction |
|-------|-------------------|
| `session_type` | Pre-fill session type selector |
| `resource_profile` | Pre-fill resource profile selector |
| `cpu_cores`, `memory_gb` | Display original resources |
| `environment_version_id` | Pre-fill environment version selector |
| `experiment_id`, `project_id` | Scope the file tree |
| `git_branch_name` | Identify the branch to checkout |
| `git_commit_hash` | Identify the exact commit to restore |

### Input Files

The `notebook_session_files` junction table with `access_type='input'` stores the original input file IDs. These are used to pre-check files in the file tree.

### New Fields

- `compute_sessions.reproduced_from_session_id` -- nullable FK to `compute_sessions.id`. Set when a session was launched via reproduction. Creates a lineage chain.

---

## 3. API

### Get Reproduction Config

```text
GET /api/v1/notebooks/sessions/{session_id}/reproduce-config
```

Returns the original session's configuration formatted for the launch modal:

```json
{
  "session_type": "rstudio",
  "resource_profile": "medium",
  "environment_version_id": 3,
  "experiment_id": 1,
  "project_id": null,
  "input_file_ids": [5, 12, 18],
  "git_branch_name": "session/42-bmills-2026-03-27",
  "git_commit_hash": "a1b2c3d4",
  "original_session_id": 42
}
```

### Launch Reproduced Session

Uses the existing launch endpoint with additional fields:

```json
{
  "session_type": "rstudio",
  "resource_profile": "large",
  "environment_version_id": 4,
  "experiment_id": 1,
  "input_file_ids": [5, 12, 18],
  "reproduce_from_session_id": 42,
  "reproduce_git_commit": "a1b2c3d4"
}
```

The backend:

1. Creates the session with `reproduced_from_session_id = 42`
2. Passes the git commit hash to the adapter
3. Adapter clones the repo, checks out the commit, creates a new branch from it
4. Normal flow continues (input file sync, sidecar setup, etc.)

---

## 4. Frontend

### Reproduce Button Locations

- **Session history table:** Action column on each completed session row
- **Session detail modal:** Button in the header area
- **Provenance view:** On the artifact detail when viewing a notebook output file, a "Reproduce source session" link

### Pre-filled Launch Modal

The existing launch modal is extended:

- When opened via "Reproduce," all fields are pre-filled from the original session
- A banner at the top: "Reproducing session #{id} from {date}. Notebook state will be restored from that session."
- File tree has the original files pre-checked but remains fully editable
- Resource profile and environment version dropdowns are editable
- A "Reset to original" link restores the pre-filled values if the user changes them

### Session Detail Additions

For reproduced sessions, the detail view shows:

- "Reproduced from: Session #{id}" with a link to the original
- The git commit that was checked out

For sessions that have been reproduced:

- "Reproduced by: Session #{id1}, #{id2}" with links

---

## 5. Git Behavior

### Branch Creation

When reproducing session 42 as session 55:

1. Clone the repo
2. `git checkout a1b2c3d4` (the original session's last commit)
3. `git checkout -b reproduce/42-55-{username}-{date}`
4. Continue with normal session flow (auto-commits go to this branch)

### Lineage

The git history naturally shows the fork point:

```text
main
  |
  +-- session/42-bmills-2026-03-27 (original)
  |     |
  |     +-- reproduce/42-55-bmills-2026-03-28 (reproduction)
  |
  +-- session/43-jdoe-2026-03-27
```

---

## 6. Provenance Integration

### Reproduction Chain

The provenance data gatherer can follow `reproduced_from_session_id` to build a reproduction chain:

- Session 55 was reproduced from Session 42
- Session 42 used input files [5, 12, 18]
- Session 42 produced output files [20, 21]
- Session 55 used the same inputs plus file [25]
- Session 55 produced output files [30, 31]

This chain is surfaced in the provenance report for any file that traces back through notebook sessions.

### Provenance Gatherer Changes

- `gather_artifact()`: when a file's source session has `reproduced_from_session_id`, include the original session in the lineage
- New provenance entity type consideration: "notebook_session" as a first-class provenance entity (currently sessions are referenced from artifacts, not queried directly)

---

## 7. Edge Cases

### Original Session's Files No Longer Exist

If an input file from the original session was deleted, the reproduce config should still return the file IDs but mark them as unavailable. The UI shows them as grayed out in the file tree with a warning: "This file is no longer available."

### Original Environment Version Deprecated

If the environment version from the original session is no longer available (deprecated or deleted), the UI should show a warning and default to the latest version: "The original environment (v1.2) is no longer available. Defaulting to v1.4."

### Git Repo Deleted

If the GitHub repo was deleted externally, reproduction fails at clone time. The error should be surfaced clearly: "The notebook repository for this experiment no longer exists on GitHub."

### No Git Integration Configured

If GitHub is not set up, the "Reproduce" button should still work but without the git checkout step. The session launches with the same config and input files but no notebook state. A warning explains: "GitHub integration is not configured. Notebook files from the original session will not be restored."

---

## 8. Database Changes

### New Columns

- `compute_sessions.reproduced_from_session_id` -- INTEGER, nullable, FK to `compute_sessions.id`

### Migration

Single migration adding the column and FK constraint.

---

## 9. API Changes Summary

| Endpoint | Change |
|----------|--------|
| `GET /api/v1/notebooks/sessions/{id}/reproduce-config` | New -- returns reproduction config |
| `POST /api/v1/notebooks/sessions` | Add optional `reproduce_from_session_id`, `reproduce_git_commit` |
| `GET /api/v1/notebooks/sessions/{id}` | Add `reproduced_from_session_id` to response |
