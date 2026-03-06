# Contributing to bioAF

Thanks for your interest in contributing to bioAF! This document covers the process for contributing to the project.

## Getting Started

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Open a pull request against `main`

## Branch Protection

The `main` branch is protected. All changes must go through a pull request with:

- At least 1 approval from a code owner
- All CI checks passing
- Branch up to date with `main`

## Pull Request Process

1. Fill out the PR template completely
2. Ensure all CI checks pass
3. Wait for code owner review
4. Address any review feedback
5. Once approved, the code owner will merge

## Development Setup

See the [README](README.md) for local development instructions.

## Code Style

- **Python (backend):** Formatted with `ruff format`, linted with `ruff check`, typed with `mypy`
- **TypeScript (frontend):** ESLint + Prettier, strict TypeScript
- **Terraform:** `terraform fmt`, `terraform validate`
- **Markdown:** Linted with markdownlint

## Architecture Decisions

Significant architectural decisions are documented as ADRs in the `decisions/` directory. If your contribution involves a meaningful architectural choice, please propose an ADR as part of your PR.

## Commit Messages

Use clear, descriptive commit messages. Prefix with the affected area when possible:

- `backend: add audit log middleware`
- `terraform: add SLURM spot instance toggle`
- `frontend: experiment registration form`
- `docs: update ADR-003 with IAP details`
- `ci: add Terraform validation step`

## Reporting Issues

Use the issue templates in this repository. Please include your bioAF version, the affected component, and steps to reproduce.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
