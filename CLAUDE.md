# bioAF Project Rules

## Text Rules
- Never use em dashes.
- Use sentence fragments where they fit and tell the full story. These can be used in commit messages or in bullet points, but only if you don't need multiple sentences to explain what is / was done.

## Git Workflow

- **Never work directly on main.** Always create a feature branch first.
- Branch names: start with `bmills-`, use hyphens between words, max 7 words total. Examples: `bmills-add-pipeline-triggers`, `bmills-fix-compute-metrics`. Branch names must not reference a "phase".
- Commit messages: Commit messages must be descriptive, but must not include "bmills" like our branches or include references to a "phase".
- Commit and push frequently. After completing a logical unit of work (a passing test, a feature slice, a bug fix), commit and push immediately rather than batching.
- When creating PRs, target `main` as the base branch.
- **Do not open a PR until explicitly asked.** Commit and push to the branch, but wait for the user to request the PR to conserve GitHub Actions minutes.

## Test-Driven Development

- Write tests first. Before implementing a feature or fix, write a failing test that captures the expected behavior.
- Verify the test fails before writing implementation code.
- Implement until the test passes.
- Commit the test and implementation together, then push to remote.

## Pre-PR Checklist

Before opening any PR, run ALL of the following and fix any issues. Do not open a PR with known failures. All tests must pass, even pre-existing failures -- resolve them before creating the PR.

### 0. README Review (required)

Check all README files for accuracy against the current state of the code. Update any outdated sections before proceeding.

### 1. Backend Tests (required -- run from backend/)

```bash
cd backend && python3 -m pytest tests/ -x -q
```

All tests must pass. The `-x` flag stops on first failure for fast feedback.

### 2. Frontend Tests (required -- run from frontend/)

```bash
cd frontend && npm test -- --passWithNoTests
```

All tests must pass.

### 3. Linting and Formatting (required -- run from backend/)

```bash
# Python formatting (must pass with zero reformats)
cd backend && python3 -m ruff format --check .

# Python linting (must pass with zero errors)
cd backend && python3 -m ruff check .

# Type checking (must pass with zero errors)
cd backend && python3 -m mypy . --ignore-missing-imports
```

### 4. Frontend Type Check (required -- run from frontend/)

```bash
cd frontend && npx tsc --noEmit
```

Must complete with zero errors.

### 5. Markdown linting (required)

```bash
# From repo root -- includes ADRs, docs, and guides
npx markdownlint-cli decisions/*.md docs/*.md docs/guides/*.md
```

Must complete with zero errors.

## Backend Conventions

- Python formatter/linter: `ruff` (format + check)
- Type checker: `mypy --ignore-missing-imports`
- Test runner: `pytest` with `pytest-asyncio`
- Markdown linter: `markdownlint-cli`
