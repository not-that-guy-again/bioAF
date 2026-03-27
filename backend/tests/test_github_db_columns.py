"""Tests for GitHub-related database columns on experiments, projects, and compute_sessions."""

import pytest
import pytest_asyncio
from sqlalchemy import text


class TestGitHubDatabaseColumns:
    @pytest.mark.asyncio
    async def test_experiments_has_github_repo_name(self, session, admin_user):
        """Experiment model should have github_repo_name column."""
        from app.models.experiment import Experiment

        exp = Experiment(
            organization_id=admin_user.organization_id,
            name="Test Exp",
            github_repo_name="EXP-001-notebooks",
        )
        session.add(exp)
        await session.flush()

        result = await session.execute(
            text("SELECT github_repo_name FROM experiments WHERE id = :id"),
            {"id": exp.id},
        )
        assert result.scalar() == "EXP-001-notebooks"

    @pytest.mark.asyncio
    async def test_experiments_github_repo_name_nullable(self, session, admin_user):
        """github_repo_name should be nullable."""
        from app.models.experiment import Experiment

        exp = Experiment(
            organization_id=admin_user.organization_id,
            name="Test Exp No Repo",
        )
        session.add(exp)
        await session.flush()

        result = await session.execute(
            text("SELECT github_repo_name FROM experiments WHERE id = :id"),
            {"id": exp.id},
        )
        assert result.scalar() is None

    @pytest.mark.asyncio
    async def test_projects_has_github_repo_name(self, session, admin_user):
        """Project model should have github_repo_name column."""
        from app.models.project import Project

        proj = Project(
            organization_id=admin_user.organization_id,
            name="Test Project",
            github_repo_name="PROJ-001-notebooks",
        )
        session.add(proj)
        await session.flush()

        result = await session.execute(
            text("SELECT github_repo_name FROM projects WHERE id = :id"),
            {"id": proj.id},
        )
        assert result.scalar() == "PROJ-001-notebooks"

    @pytest.mark.asyncio
    async def test_compute_sessions_has_git_branch_name(self, session, admin_user):
        """ComputeSession should have git_branch_name column."""
        from app.models.notebook_session import ComputeSession

        cs = ComputeSession(
            user_id=admin_user.id,
            organization_id=admin_user.organization_id,
            session_type="jupyter",
            resource_profile="small",
            cpu_cores=2,
            memory_gb=4,
            git_branch_name="session/42-alice-2026-03-27",
        )
        session.add(cs)
        await session.flush()

        result = await session.execute(
            text("SELECT git_branch_name FROM compute_sessions WHERE id = :id"),
            {"id": cs.id},
        )
        assert result.scalar() == "session/42-alice-2026-03-27"

    @pytest.mark.asyncio
    async def test_compute_sessions_has_git_commit_hash(self, session, admin_user):
        """ComputeSession should have git_commit_hash column."""
        from app.models.notebook_session import ComputeSession

        cs = ComputeSession(
            user_id=admin_user.id,
            organization_id=admin_user.organization_id,
            session_type="jupyter",
            resource_profile="small",
            cpu_cores=2,
            memory_gb=4,
            git_commit_hash="abc123def456",
        )
        session.add(cs)
        await session.flush()

        result = await session.execute(
            text("SELECT git_commit_hash FROM compute_sessions WHERE id = :id"),
            {"id": cs.id},
        )
        assert result.scalar() == "abc123def456"
