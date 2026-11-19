import hashlib
import hmac

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app import config

_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def key_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def get_owner(key: str | None = Security(_header)) -> str:
    """API-key dependency. Returns the key's hash, used as the owner id.
    Raw keys are never stored in the database."""
    if not key or not any(hmac.compare_digest(key, valid) for valid in config.API_KEYS):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return key_hash(key)
