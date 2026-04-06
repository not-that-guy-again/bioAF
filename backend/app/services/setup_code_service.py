"""Service for generating and verifying terminal-issued setup codes."""

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization

# Unambiguous charset: no 0/O, 1/l/I
SETUP_CODE_CHARSET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
SETUP_CODE_LENGTH = 6
SETUP_CODE_TTL = timedelta(hours=1)


class SetupCodeService:
    @staticmethod
    async def generate_code(session: AsyncSession, org: Organization) -> str:
        """Generate a setup code, store its bcrypt hash and expiry on the org.

        Returns the plaintext code (shown in the terminal).
        """
        code = "".join(secrets.choice(SETUP_CODE_CHARSET) for _ in range(SETUP_CODE_LENGTH))
        code_hash = bcrypt.hashpw(code.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        org.setup_code_hash = code_hash
        org.setup_code_expires_at = datetime.now(timezone.utc) + SETUP_CODE_TTL
        session.add(org)
        await session.flush()

        return code

    @staticmethod
    async def verify_code(session: AsyncSession, org: Organization, code: str) -> bool:
        """Verify a setup code against the stored hash.

        Returns True if valid and not expired. On success, nulls the hash
        so the code is single-use.
        """
        if org.setup_code_hash is None:
            return False

        if org.setup_code_expires_at is None or org.setup_code_expires_at < datetime.now(timezone.utc):
            return False

        if not bcrypt.checkpw(code.encode("utf-8"), org.setup_code_hash.encode("utf-8")):
            return False

        # Single-use: null the hash and expiry
        org.setup_code_hash = None
        org.setup_code_expires_at = None
        session.add(org)
        await session.flush()

        return True
