# Prompt: Notebook File I/O with Git-Backed History

## Context

Read the following files before starting:

- `documentation/spec-notebook-file-io-git-history.md` -- the full spec for this change
- `decisions/ADR-039-notebook-output-provenance.md` -- the provenance ADR this builds on
- `backend/app/models/notebook_session_file.py` -- the NotebookSessionFile model (already exists)
- `backend/app/models/notebook_session.py` -- the ComputeSession model
- `backend/app/models/file.py` -- the File model with source_notebook_session_id
- `backend/app/adapters/notebooks/kubernetes.py` -- the K8s notebook adapter
- `backend/app/services/notebook_service.py` -- the notebook launch/stop service
- `backend/app/services/session_persistence.py` -- the sync command generators
- `docker/Dockerfile.bioaf-scrna` -- the notebook container image
- `frontend/src/app/notebooks/page.tsx` -- the notebook launch UI

Notebook sessions currently have no access to experiment files and no durable record of work. The home directory syncs to GCS but files are never registered in the DB, notebooks have no version history, and the provenance system has no data to work with. This change adds managed file I/O, git-backed notebook history via GitHub, and automatic output registration.

## Task

Implement the full notebook file I/O system with GitHub integration, input file mounting, git-backed history, periodic auto-commit, and output file discovery.

## Requirements

This is a large feature. Work through it in logical chunks, committing and pushing after each chunk passes all tests. Do not batch everything into one commit.

### Chunk 1: GitHub App Integration (Backend)

1. **Create a feature branch** if not already on one. All work goes on the current branch `bmills-notebook-output-provenance`.

2. **Write failing tests first** in `backend/tests/test_github_integration.py`:
   - Test storing GitHub App credentials in platform_config
   - Test validating a GitHub connection (mock the GitHub API)
   - Test creating a private repo (mock)
   - Test checking if a repo exists (mock)
   - Test generating an installation token (mock)
   - Run tests and verify they fail

3. **Create the GitHub service** (`backend/app/services/github_service.py`):
   - `GitHubService` class with static methods
   - `connect(session, app_id, installation_id, org_name, private_key)` -- stores credentials
   - `get_status(session)` -- returns connection status
   - `disconnect(session)` -- removes credentials
   - `create_repo(session, name)` -- creates a private repo in the org
   - `repo_exists(session, name)` -- checks existence
   - `get_clone_url(session, name)` -- returns SSH clone URL
   - `list_branches(session, name)` -- lists branches
   - `get_installation_token(session)` -- generates short-lived token
   - All methods read credentials from platform_config
   - Use the `PyGithub` library or direct GitHub REST API via `httpx`

4. **Create API endpoints** (`backend/app/api/github_settings.py`):
   - `POST /api/v1/settings/github/connect` -- store credentials, validate
   - `GET /api/v1/settings/github/status` -- connection status
   - `DELETE /api/v1/settings/github/disconnect` -- remove credentials
   - Require `settings:configure` permission

5. **Register the router** in `backend/app/api/router.py`

6. **Run tests**, verify they pass, commit and push.

### Chunk 2: Database Changes

1. **Write failing tests** for the new columns and migration.

2. **Create the migration** (next sequential number):
   - Add `github_repo_name VARCHAR(200)` nullable to `experiments`
   - Add `github_repo_name VARCHAR(200)` nullable to `projects`
   - Add `git_branch_name VARCHAR(200)` nullable to `compute_sessions`
   - Add `git_commit_hash VARCHAR(64)` nullable to `compute_sessions`

3. **Update models**:
   - Add the new columns to `Experiment`, `Project`, and `ComputeSession` models

4. **Run tests**, commit and push.

### Chunk 3: File Tree Selector (Frontend)

1. **Write failing tests** in `frontend/tests/components/notebooks/FileTreeSelector.test.tsx`:
   - Test rendering experiment > sample > file tree structure
   - Test checkbox selection propagation (selecting experiment selects all children)
   - Test FASTQ/BAM toggle hides/shows large files
   - Test total size calculation
   - Test empty selection is valid

2. **Create the FileTreeSelector component** (`frontend/src/components/notebooks/FileTreeSelector.tsx`):
   - Accepts `projectId` or `experimentId` prop
   - Fetches files via existing `GET /api/experiments/{id}/files` endpoint
   - Renders collapsible tree with checkboxes
   - Groups files by experiment > sample
   - FASTQ/BAM toggle checkbox (unchecked by default, hides files with extensions `.fastq`, `.fastq.gz`, `.bam`, `.bai`, `.cram`)
   - Shows total selected size at bottom with warning if > 10 GB
   - Emits `onSelectionChange(fileIds: number[])` callback

3. **Integrate into the launch modal** on the notebooks page:
   - Add the FileTreeSelector after resource profile selection
   - Pass selected file IDs to the launch API call
   - Only show if an experiment is selected

4. **Run tests**, commit and push.

### Chunk 4: Input File Mounting (Backend)

1. **Write failing tests** in `backend/tests/test_notebook_file_mounting.py`:
   - Test that launch with `input_file_ids` creates NotebookSessionFile input rows
   - Test that the adapter spec includes input files with GCS URIs
   - Test org isolation: cannot mount files from another org
   - Test that files are mounted read-only in `/data/`

2. **Update the launch request schema**:
   - Add `input_file_ids: list[int] = []` to `SessionLaunchRequest` and `NotebookLaunchRequest`

3. **Update `NotebookService.launch_session()`**:
   - Accept `input_file_ids` parameter
   - Query File records for those IDs, validate org ownership
   - Build `input_files` list: `[{gcs_uri, relative_path, file_id}, ...]`
   - Pass to adapter via `spec["input_files"]`
   - After launch, create `NotebookSessionFile` rows with `access_type='input'`

4. **Update the K8s adapter**:
   - Read `session_spec["input_files"]`
   - Add a second init container `gcs-data-sync` that runs `gsutil cp` for each file into `/data/`
   - Add a second volume (`data`, emptyDir) mounted read-only in the main container at `/data/`
   - Generate `FILE_INVENTORY.md` content and pass it to the startup script

5. **Run tests**, commit and push.

### Chunk 5: Git Integration in Pod (Backend + Docker)

1. **Update `Dockerfile.bioaf-scrna`**:
   - Add `git openssh-client` to the apt-get install

2. **Update the K8s adapter startup script**:
   - After home dir sync and data sync, run git setup:
     - Configure git user.name and user.email from session owner
     - Write SSH key to `~/.ssh/id_rsa` (from Kubernetes Secret or env var)
     - Clone the experiment/project repo (create if doesn't exist)
     - Create session branch: `session/{session_id}-{username}-{YYYY-MM-DD}`
     - Write and commit `FILE_INVENTORY.md`

3. **Add git auto-commit sidecar**:
   - New container in the pod spec: `git-autocommit`
   - Image: `alpine/git` with openssh-client
   - Shares the home volume with the main container
   - Runs a shell loop: every 60 seconds, check if 15 minutes have passed since last commit AND there are uncommitted changes. If so, `git add -A && git commit -m "Auto-save: {timestamp}" && git push origin {branch}`
   - The SSH key is mounted from the same secret

4. **Update the terminate flow**:
   - Before home dir sync-out, run final git commit + push
   - Store the branch name and commit hash on the session record
   - Then proceed with output file discovery (Chunk 6)

5. **Write tests** for the git-related adapter changes (mock git commands)

6. **Run tests**, commit and push.

### Chunk 6: Output File Discovery and Registration

1. **Write failing tests** in `backend/tests/test_notebook_output_discovery.py`:
   - Test that stopping a session discovers new files
   - Test that discovered files get File records with source_type='notebook_output'
   - Test that NotebookSessionFile output rows are created
   - Test that system files (.bash_history, etc.) are excluded
   - Test that files in /data/ (inputs) are excluded

2. **Create the output registration endpoint**:
   - `POST /api/v1/notebooks/sessions/{session_id}/register-outputs`
   - Accepts list of `{filename, size_bytes, gcs_uri}`
   - Creates File records and NotebookSessionFile rows
   - Called by the sidecar during periodic commits and by the terminate flow

3. **Update the terminate flow in the adapter**:
   - After final git commit, scan home directory for new/modified files
   - Exclude: `/data/` contents, `.git/`, system files, `.gitignore` patterns
   - Upload each output to `gs://{working_bucket}/notebook-outputs/{experiment_code}/{session_id}/{filename}`
   - Call the register-outputs endpoint (or do it directly in the service layer)

4. **Update the sidecar** to also call register-outputs during periodic commits

5. **Run tests**, commit and push.

### Chunk 7: Branch Conflict Alerting (Frontend)

1. **Update the launch modal**:
   - When an experiment is selected, query GitHub for open `session/*` branches on that repo
   - If branches exist, show a warning: "There are N active notebook branches for this experiment. You may need to merge changes on GitHub after your session."
   - Include a link to the GitHub repo's branches page

2. **Update the session detail view**:
   - Show git branch name and last commit hash
   - Link to the branch on GitHub

3. **Run tests**, commit and push.

### Final: Pre-PR Checklist

Run ALL of the following and fix any issues:

```bash
cd backend && python3 -m pytest tests/ -x -q
cd backend && python3 -m ruff format --check .
cd backend && python3 -m ruff check .
cd backend && python3 -m mypy . --ignore-missing-imports
cd frontend && npx tsc --noEmit
cd frontend && npm test -- --passWithNoTests
npx markdownlint-cli decisions/*.md docs/*.md docs/guides/*.md
```

Do not open a PR. Commit and push after all checks pass.
