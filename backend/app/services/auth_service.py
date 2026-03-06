import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=settings.bcrypt_rounds)


class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_token(user_id: int, email: str, role: str, org_id: int) -> str:
        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "org_id": org_id,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours),
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def validate_token(token: str) -> dict:
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            return payload
        except JWTError as e:
            raise ValueError(f"Invalid token: {e}") from e

    @staticmethod
    def generate_verification_code() -> tuple[str, str]:
        """Generate a 6-digit verification code. Returns (plain_code, hashed_code)."""
        code = f"{secrets.randbelow(1000000):06d}"
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        return code, code_hash

    @staticmethod
    def verify_code(plain_code: str, code_hash: str) -> bool:
        return hashlib.sha256(plain_code.encode()).hexdigest() == code_hash

    @staticmethod
    def generate_invite_token(user_id: int, email: str) -> str:
        payload = {
            "sub": str(user_id),
            "email": email,
            "purpose": "invite",
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def validate_invite_token(token: str) -> dict:
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            if payload.get("purpose") != "invite":
                raise ValueError("Not an invite token")
            return payload
        except JWTError as e:
            raise ValueError(f"Invalid invite token: {e}") from e
