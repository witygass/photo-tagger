import json

from cryptography.fernet import Fernet
from google.oauth2.credentials import Credentials

from app.config import settings


def _get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    if not key:
        # Dev fallback: generate a key and warn. In production ENCRYPTION_KEY must be set.
        import warnings
        warnings.warn("ENCRYPTION_KEY not set — generating ephemeral key. Tokens will not survive restart.")
        key = Fernet.generate_key().decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def credentials_to_dict(creds: Credentials) -> dict:
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or []),
    }


def credentials_from_dict(d: dict) -> Credentials:
    return Credentials(
        token=d.get("token"),
        refresh_token=d.get("refresh_token"),
        token_uri=d.get("token_uri"),
        client_id=d.get("client_id"),
        client_secret=d.get("client_secret"),
        scopes=d.get("scopes"),
    )


def encrypt_token(credentials_dict: dict) -> bytes:
    return _get_fernet().encrypt(json.dumps(credentials_dict).encode())


def decrypt_token(encrypted: bytes) -> dict:
    return json.loads(_get_fernet().decrypt(encrypted))
