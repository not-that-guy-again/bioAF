# Prompt: Session Reproduction

## Context

Read the following files before starting:
- `documentation/spec-session-reproduction.md` -- the full spec for this change
- `documentation/spec-notebook-file-io-git-history.md` -- the Phase 1 spec this depends on
- `backend/app/models/notebook_session.py` -- ComputeSession model (should now have git_branch_name, git_commit_hash from Phase 1)
- `backend/app/models/notebook_session_file.py` -- NotebookSessionFile model
- `backend/app/services/notebook_service.py` -- notebook launch/stop service (should now have input_file_ids support from Phase 1)
- `backend/app/services/github_service.py` -- GitHub integration service (from Phase 1)
- `backend/app/adapters/notebooks/kubernetes.py` -- K8s adapter (should now have git clone/checkout from Phase 1)
- `frontend/src/app/notebooks/page.tsx` -- notebook UI
- `backend/app/services/provenance/data_gatherer.py` -- provenance data gatherer

Phase 1 (Notebook File I/O with Git-Backed History) must be complete before starting this work. Sessions now have git-backed notebooks, input file mounting, and output file registration. This phase adds the ability to recreate any past session.

## Task

Implement session reproduction: a "Reproduce" button that pre-fills the launch modal with a past session's configuration, checks out the exact git commit, and mounts the same input files.

## Requirements

Work through this in logical chunks, committing and pushing after each chunk passes all tests.

### Chunk 1: Database and Model Changes

1. **Write failing tests** in `backend/tests/test_session_reproduction.py`:
   - Test that a session can be created with `reproduced_from_session_id`
   - Test that the reproduce-config endpoint returns correct config for a past session
   - Test that reproducing a session with deleted input files marks them as unavailable
   - Test that reproducing a session without GitHub integration still works (no git checkout)

2. **Create the migration** (next sequential number):
   - Add `reproduced_from_session_id INTEGER` nullable FK to `compute_sessions.id` on `compute_sessions`

3. **Update `ComputeSession` model**:
   - Add `reproduced_from_session_id` column
   - Add `reproduced_from` relationship (self-referential)

4. **Run tests**, commit and push.

### Chunk 2: Reproduce Config Endpoint

1. **Create the endpoint** in `backend/app/api/notebook_sessions.py`:
   - `GET /api/v1/notebooks/sessions/{session_id}/reproduce-config`
   - Returns: session_type, resource_profile, environment_version_id, experiment_id, project_id, input_file_ids (from NotebookSessionFile where access_type='input'), git_branch_name, git_commit_hash, original_session_id
   - For each input file, include an `available: bool` flag (check if the file still exists)
   - If the environment version is deprecated/deleted, include `environment_available: false`

2. **Update the launch endpoint**:
   - Accept optional `reproduce_from_session_id: int | None` and `reproduce_git_commit: str | None`
   - When set, store `reproduced_from_session_id` on the new session
   - Pass `reproduce_git_commit` to the adapter via session spec

3. **Update the adapter**:
   - When `session_spec["reproduce_git_commit"]` is set, the startup script checks out that commit before creating the new branch
   - New branch name: `reproduce/{original_session_id}-{new_session_id}-{username}-{date}`

4. **Run tests**, commit and push.

### Chunk 3: Frontend - Reproduce Button and Pre-filled Modal

1. **Write failing tests** in `frontend/tests/components/notebooks/ReproduceSession.test.tsx`:
   - Test that the Reproduce button appears on completed sessions
   - Test that clicking Reproduce fetches the config and opens the launch modal
   - Test that the modal is pre-filled with the original session's settings
   - Test that unavailable files are shown grayed out with a warning
   - Test that the user can modify settings before launching

2. **Add the Reproduce button** to the session history table and session detail modal:
   - Only visible for sessions with status "stopped" that have a git_commit_hash
   - On click: fetch `GET /reproduce-config`, open the launch modal pre-filled

3. **Update the launch modal**:
   - Accept optional `reproduceConfig` prop
   - When provided, pre-fill all fields from the config
   - Show a banner: "Reproducing session #{id} from {date}. Notebook state will be restored."
   - File tree has original files pre-checked, with unavailable files grayed out
   - "Reset to original" link to restore pre-filled values
   - On submit, include `reproduce_from_session_id` and `reproduce_git_commit` in the request

4. **Update session detail view**:
   - For reproduced sessions: "Reproduced from: Session #{id}" link
   - For sessions that were reproduced: "Reproduced by: Session #{id}" link

5. **Run tests**, commit and push.

### Chunk 4: Provenance Integration

1. **Update the provenance data gatherer**:
   - In `gather_artifact()`: when a file's source session has `reproduced_from_session_id`, include the original session in the provenance chain
   - Consider adding a `gather_session()` method that traces the full reproduction chain for a session

2. **Add Reproduce button to the provenance view**:
   - When viewing a notebook output file's provenance, show a "Reproduce source session" link
   - This opens the Reproduce flow for the session that produced the file

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
