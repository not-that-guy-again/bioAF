"""CRUD service for naming profiles."""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file_parse_result import FileParseResult
from app.models.naming_profile import NamingProfile
from app.schemas.naming_profile import NamingProfileCreate, NamingProfileUpdate
from app.services.audit_service import log_action
from app.services.naming_profile_parser import match_filename


class NamingProfileService:
    @staticmethod
    async def create_profile(
        session: AsyncSession,
        org_id: int,
        user_id: int,
        data: NamingProfileCreate,
    ) -> NamingProfile:
        profile = NamingProfile(
            organization_id=org_id,
            name=data.name,
            description=data.description,
            delimiter=data.delimiter,
            strip_extension=data.strip_extension,
            segments_json=[seg.model_dump() for seg in data.segments],
            project_code_mappings=data.project_code_mappings,
            experiment_code_mappings=data.experiment_code_mappings,
            status="active",
            created_by=user_id,
        )
        session.add(profile)
        await session.flush()

        await log_action(
            session,
            user_id=user_id,
            entity_type="naming_profile",
            entity_id=profile.id,
            action="create",
            details={"name": data.name, "delimiter": data.delimiter},
        )
        return profile

    @staticmethod
    async def get_profile(session: AsyncSession, profile_id: int) -> NamingProfile | None:
        result = await session.execute(select(NamingProfile).where(NamingProfile.id == profile_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_profiles(
        session: AsyncSession,
        org_id: int,
        status_filter: str | None = None,
    ) -> list[NamingProfile]:
        query = select(NamingProfile).where(NamingProfile.organization_id == org_id)
        if status_filter:
            query = query.where(NamingProfile.status == status_filter)
        query = query.order_by(NamingProfile.created_at.desc())
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_profile(
        session: AsyncSession,
        profile_id: int,
        user_id: int,
        data: NamingProfileUpdate,
    ) -> NamingProfile | None:
        result = await session.execute(select(NamingProfile).where(NamingProfile.id == profile_id))
        profile = result.scalar_one_or_none()
        if not profile:
            return None

        previous = {}
        updates = {}
        for field in ["name", "description", "delimiter", "strip_extension"]:
            new_val = getattr(data, field, None)
            if new_val is not None:
                old_val = getattr(profile, field)
                previous[field] = str(old_val) if old_val is not None else None
                setattr(profile, field, new_val)
                updates[field] = str(new_val)

        if data.segments is not None:
            previous["segments_json"] = "updated"
            profile.segments_json = [seg.model_dump() for seg in data.segments]
            updates["segments_json"] = "updated"

        if data.project_code_mappings is not None:
            profile.project_code_mappings = data.project_code_mappings
            updates["project_code_mappings"] = "updated"

        if data.experiment_code_mappings is not None:
            profile.experiment_code_mappings = data.experiment_code_mappings
            updates["experiment_code_mappings"] = "updated"

        if updates:
            await session.flush()
            await log_action(
                session,
                user_id=user_id,
                entity_type="naming_profile",
                entity_id=profile.id,
                action="update",
                details=updates,
                previous_value=previous,
            )
        return profile

    @staticmethod
    async def deactivate_profile(
        session: AsyncSession,
        profile_id: int,
        user_id: int,
    ) -> NamingProfile | None:
        result = await session.execute(select(NamingProfile).where(NamingProfile.id == profile_id))
        profile = result.scalar_one_or_none()
        if not profile:
            return None

        old_status = profile.status
        profile.status = "inactive"
        await session.flush()

        await log_action(
            session,
            user_id=user_id,
            entity_type="naming_profile",
            entity_id=profile.id,
            action="deactivate",
            details={"status": "inactive"},
            previous_value={"status": old_status},
        )
        return profile

    @staticmethod
    async def test_profiles(
        session: AsyncSession,
        org_id: int,
        filenames: list[str],
    ) -> list[dict]:
        """Run parser against all active profiles for a list of filenames."""
        profiles = await NamingProfileService.list_profiles(session, org_id, status_filter="active")
        results = []
        for filename in filenames:
            match = match_filename(filename, profiles)
            entry: dict = {
                "filename": filename,
                "match_status": match.status,
                "matched_profile_id": None,
                "matched_profile_name": None,
                "parsed_segments": None,
                "candidate_profile_ids": None,
            }
            if match.status == "matched" and match.parse_result:
                entry["matched_profile_id"] = match.parse_result.profile_id
                entry["matched_profile_name"] = match.parse_result.profile_name
                entry["parsed_segments"] = match.parse_result.segments
            elif match.status == "multiple_matches":
                entry["candidate_profile_ids"] = match.candidate_profile_ids
            results.append(entry)
        return results

    @staticmethod
    async def get_match_statistics(
        session: AsyncSession,
        profile_id: int,
        days: int = 30,
    ) -> int:
        """Count files matched by this profile in the last N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await session.execute(
            select(func.count(FileParseResult.id)).where(
                FileParseResult.naming_profile_id == profile_id,
                FileParseResult.match_status == "matched",
                FileParseResult.created_at >= cutoff,
            )
        )
        return result.scalar_one()
