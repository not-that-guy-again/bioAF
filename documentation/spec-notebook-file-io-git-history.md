# Spec: Notebook File I/O with Git-Backed History

**Status:** Draft
**Date:** 2026-03-27
**Depends on:** ADR-039 (Notebook Output Provenance), notebook output provenance branch work

---

## Overview

Notebook sessions (Jupyter, RStudio) need managed file I/O: users select input files at launch, those files are mounted into the session, files created during the session are persisted and tracked, and the notebook itself is version-controlled via GitHub. This replaces the current behavior where sessions have no access to experiment data and no durable record of work.

---

## 1. GitHub App Integration

### Admin Setup Flow

1. The platform settings page (Settings > GitHub Integration) displays a "Install GitHub App" button.
2. Clicking it opens a GitHub App manifest URL that creates the app in one click on the user's GitHub org.
3. After installation, the admin enters the GitHub App ID and uploads the private key (.pem file) in the settings page.
4. The platform stores the App ID in `platform_config` and the private key in Google Secret Manager (or `platform_config` encrypted).
5. The platform validates the connection by listing repos in the org via the GitHub API.
6. The settings page shows a green "Connected" status with the org name.

### GitHub App Permissions Required

- Repository: Contents (read/write), Administration (read/write -- for repo creation)
- Organization: Members (read -- for validating org membership)

### Backend Implementation

- New model: `GitHubAppConfig` or store in `platform_config` keys: `github_app_id`, `github_app_installation_id`, `github_org_name`, `github_private_key_secret_name`
- New service: `GitHubService` with methods:
  - `create_repo(name, private=True)` -- creates a private repo in the org
  - `repo_exists(name)` -- checks if a repo exists
  - `get_clone_url(name)` -- returns the SSH clone URL
  - `list_branches(name)` -- lists branches for conflict detection
  - `get_installation_token()` -- generates a short-lived token from the App credentials
- API endpoints under `/api/v1/settings/github`:
  - `POST /connect` -- stores App ID and private key, validates connection
  - `GET /status` -- returns connection status
  - `DELETE /disconnect` -- removes credentials

### Frontend Implementation

- New section in Settings page: "GitHub Integration"
- Install button with link to GitHub App manifest creation URL
- Form fields for App ID and private key upload
- Connection status indicator
- "Disconnect" button

---

## 2. Per-Project/Experiment Repository Management

### Repo Naming

- If the session is scoped to a single experiment: `{experiment-code}-notebooks`
- If the session includes files from multiple experiments (project-scoped): `{project-code}-notebooks`
- Repo is always private to the organization

### Repo Lifecycle

- **Creation:** On first notebook session launch for an experiment/project that has no repo yet.
- **Initialization:** README.md describing the experiment/project, `.gitignore` excluding `/data/`, common large formats (`.fastq`, `.fastq.gz`, `.bam`, `.bai`, `.cram`), and environment files (`.Rhistory`, `.bash_history`, `__pycache__/`, `.ipynb_checkpoints/`).
- **File inventory:** A `FILE_INVENTORY.md` (or `.csv`) is auto-generated at session start listing all mounted input files with their relative paths and GCS source URIs. Committed on first session commit.

### Data Model Changes

- Add `github_repo_name` column (nullable) to `experiments` table
- Add `github_repo_name` column (nullable) to `projects` table
- These are set when the repo is first created

---

## 3. File Tree Selector in Launch Modal

### UI Design

The notebook launch modal gains a file selection step after choosing session type and resource profile.

- **Scope selector:** Radio buttons for "Project" or "Experiment" scope. Selecting Project shows all experiments in the project.
- **File tree:** Collapsible tree structure:
  ```
  [v] Experiment: EXP-001 - scRNA-seq Treatment Study
      [v] Sample: SAMP-001 - Control Day 0
          [ ] filtered_matrix.h5ad (450 MB)
          [ ] raw_counts.csv (12 MB)
          [x] FASTQ - sample_R1.fastq.gz (28 GB)  <-- hidden by default
      [v] Sample: SAMP-002 - Treatment Day 7
          [ ] filtered_matrix.h5ad (520 MB)
  [ ] Experiment: EXP-002 - Spatial Transcriptomics
      ...
  ```
- **FASTQ/BAM toggle:** Checkbox at the top: "Include FASTQ and BAM files" -- unchecked by default. When unchecked, FASTQ/BAM/CRAM files are hidden from the tree.
- **Select all:** Clicking an experiment checkbox selects all files under it. Clicking a sample checkbox selects all files under that sample.
- **Size estimate:** Total selected file size shown at the bottom. Warning if > 10 GB.
- **No selection is valid:** If nothing is selected, the session launches with an empty `/data` directory.

### API

- Reuse existing `GET /api/experiments/{id}/files` endpoint
- For project scope, call it for each experiment in the project
- Frontend assembles the tree client-side

---

## 4. Input File Mounting

### Mechanism

Input files are synced into the pod via `gsutil cp` in an init container (same pattern as the home directory sync-in). This is simpler than GCS FUSE and sufficient for the expected file sizes (< 5 GB typical working set).

### Pod Changes

- New init container: `gcs-data-sync` that runs after `gcs-sync-in` (home dir)
- Command: for each selected file, `gsutil cp {gcs_uri} /data/{relative_path}`
- The `/data` volume is a separate `emptyDir` mounted read-only in the main container
- The file list is passed to the adapter via `session_spec["input_files"]` -- a list of `{gcs_uri, relative_path, file_id}` dicts

### Data Flow

1. Frontend sends `input_file_ids: [1, 5, 12]` in the launch request
2. Backend queries File records for those IDs, builds the GCS URI list
3. Adapter constructs the init container with `gsutil cp` commands
4. Init container copies files to `/data/`
5. Backend creates `NotebookSessionFile` rows with `access_type='input'` for each file

### Service Changes

- `NotebookService.launch_session()` accepts `input_file_ids: list[int]`
- Queries `File` records for those IDs, validates org ownership
- Passes `input_files` list to adapter via spec
- After launch, creates `NotebookSessionFile` input rows

### Adapter Changes

- `_k8s_launch_session()` reads `session_spec["input_files"]`
- Builds a second init container that copies files to `/data/`
- Adds a second volume mount (`/data`, read-only in main container)

---

## 5. Git Integration in Sessions

### Pod Startup

After the data sync init containers, the main container startup script:

1. Configures git with the session owner's name and email
2. Configures SSH with the GitHub App deploy key (mounted as a secret or env var)
3. Clones the experiment/project repo into `/home/jovyan/notebooks/` (or the home directory root)
4. Creates a session branch: `session/{session_id}-{username}-{YYYY-MM-DD}`
5. Generates `FILE_INVENTORY.md` listing all mounted input files
6. Commits the inventory file as the initial commit on the branch

### Periodic Auto-Commit (Sidecar)

A lightweight sidecar container (or cron job in the main container) runs every 15 minutes:

1. Check if there are uncommitted changes: `git status --porcelain`
2. If changes exist AND the last commit was > 15 minutes ago:
   - `git add -A`
   - `git commit -m "Auto-save: {timestamp}"`
   - `git push origin {branch}`
3. If no changes, do nothing

Implementation options:
- **Sidecar container:** Runs a simple shell loop. Shares the home volume with the main container. Cleanest separation.
- **Cron in main container:** Add a crontab entry in the startup script. Simpler but couples git logic to the notebook image.

Recommended: sidecar container using `alpine/git` image with the SSH key mounted.

### Session Stop

On session stop, before the home directory sync-out:

1. `git add -A`
2. `git commit -m "Session {session_id} stopped: {timestamp}"` (skip if nothing to commit)
3. `git push origin {branch}`
4. Scan `/home/jovyan/` for new/modified files (compare against the file inventory)
5. For each new file that is not in `.gitignore`:
   - Upload to GCS: `gs://{working_bucket}/outputs/{session_id}/{filename}`
   - Create a `File` record with `source_type='notebook_output'`, `source_notebook_session_id={session_id}`
   - Create a `NotebookSessionFile` row with `access_type='output'`
   - Link to experiment/project from the session context

### Adapter Changes

- Startup script extended with git clone, branch creation, SSH config
- New sidecar container spec for auto-commit
- Terminate flow extended with final commit + push + output discovery

---

## 6. Output File Discovery and Registration

### What Gets Registered

On session stop (and during periodic auto-commits), the system scans for files that:
- Are in the home directory but NOT in `/data/` (inputs are read-only, not outputs)
- Are not in `.gitignore` patterns
- Are not system files (`.bash_history`, `.Rhistory`, `__pycache__/`, `.ipynb_checkpoints/`)
- Were created or modified during this session (compare mtime against session start time)

### Registration Flow

For each discovered output file:

1. Upload to GCS: `gs://{working_bucket}/notebook-outputs/{experiment_code}/{session_id}/{filename}`
2. Create `File` record:
   - `source_type = "notebook_output"`
   - `source_notebook_session_id = session.id`
   - `experiment_id = session.experiment_id`
   - `file_type` derived from extension
   - `gcs_uri` pointing to the uploaded location
3. Create `NotebookSessionFile` row: `(session_id, file_id, access_type='output')`

### Periodic Registration (During Auto-Commit)

During the 15-minute auto-commit cycle, also scan for new output files and register them in the DB. This ensures outputs are tracked even if the pod crashes before a clean stop.

This requires the sidecar (or cron) to call a backend API endpoint to register files, since it doesn't have DB access. New endpoint:

- `POST /api/v1/notebooks/sessions/{session_id}/register-outputs`
- Accepts a list of `{filename, size_bytes, gcs_uri}`
- Creates File records and NotebookSessionFile rows

---

## 7. Branch Conflict Alerting

### Detection

When a user launches a session for an experiment/project that already has open branches from other sessions:

- Query GitHub API for branches matching `session/*` pattern
- If any exist, show a warning in the launch modal: "There are {N} active branches for this experiment's notebooks. You may need to merge changes on GitHub after your session."
- Link to the GitHub repo's branches page

### Session Detail

The session detail view shows:
- Git branch name
- Last commit hash and message
- Link to the branch on GitHub

---

## 8. Notebook Image Changes

### Dockerfile.bioaf-scrna

Add to the system dependencies install:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    git openssh-client \
    && rm -rf /var/lib/apt/lists/*
```

This enables `git clone`, `git commit`, `git push` and SSH-based GitHub auth inside the container.

---

## 9. Database Changes

### New Columns

- `experiments.github_repo_name` -- VARCHAR(200), nullable
- `projects.github_repo_name` -- VARCHAR(200), nullable
- `compute_sessions.git_branch_name` -- VARCHAR(200), nullable
- `compute_sessions.git_commit_hash` -- VARCHAR(64), nullable

### New platform_config Keys

- `github_app_id` -- GitHub App ID
- `github_app_installation_id` -- Installation ID for the org
- `github_org_name` -- GitHub organization name
- `github_private_key_secret` -- Secret Manager path or encrypted key

### Migration

Single migration adding the new columns and creating the platform_config entries.

---

## 10. API Changes Summary

| Endpoint | Change |
|----------|--------|
| `POST /api/notebooks/sessions` | Add `input_file_ids: list[int]` to request body |
| `POST /api/v1/notebooks/sessions` | Add `input_file_ids: list[int]` to request body |
| `POST /api/v1/notebooks/sessions/{id}/register-outputs` | New -- register output files from sidecar |
| `GET /api/v1/settings/github` | New -- GitHub connection status |
| `POST /api/v1/settings/github/connect` | New -- store GitHub App credentials |
| `DELETE /api/v1/settings/github/disconnect` | New -- remove credentials |
| `GET /api/v1/notebooks/sessions/{id}` | Add `git_branch_name`, `git_commit_hash` to response |

---

## 11. Security Considerations

- GitHub App private key stored in Secret Manager, never in plain text in the DB
- SSH key injected into pods via Kubernetes Secret, not baked into the image
- Input files mounted read-only -- users cannot corrupt source data
- Output file registration validates org ownership before creating records
- Auto-commit uses the session owner's identity, creating an audit trail in git
