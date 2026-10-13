from __future__ import annotations

import json
import time
from typing import Any


SERVICE_NAME = "baizhi-apps-cli"
_OS_BACKEND_PREFIXES = (
    "keyring.backends.macos.",
    "keyring.backends.secretservice.",
    "keyring.backends.libsecret.",
    "keyring.backends.windows.",
    "keyring.backends.kwallet",
)


class CredentialError(RuntimeError):
    pass


class CredentialStore:
    """Store platform tokens in the OS credential manager; never use a file fallback."""

    def __init__(self, *, backend: Any = None, now=time.time) -> None:
        if backend is None:
            try:
                import keyring
                backend = keyring.get_keyring()
            except Exception as exc:
                raise CredentialError(
                    "CREDENTIAL_STORE_UNAVAILABLE: install/configure an OS secure credential store"
                ) from exc
        try:
            priority = float(backend.priority)
        except (AttributeError, TypeError, ValueError):
            priority = 0
        backend_name = f"{type(backend).__module__}.{type(backend).__name__}".lower()
        secure_os_backend = backend_name.startswith(_OS_BACKEND_PREFIXES)
        if priority <= 0 or (backend is not None and not secure_os_backend):
            raise CredentialError(
                "CREDENTIAL_STORE_UNAVAILABLE: install/configure an OS secure credential store; plaintext fallback is disabled"
            )
        self.backend = backend
        self.now = now

    def save(self, host: str, credential: dict[str, Any]) -> None:
        token = credential.get("token")
        expires_at = credential.get("expires_at")
        if not isinstance(token, str) or not token or not isinstance(expires_at, (int, float)):
            raise CredentialError("LOGIN_RESPONSE_INVALID: token or expires_at is missing")
        serialized = json.dumps({"token": token, "expires_at": int(expires_at)}, separators=(",", ":"))
        try:
            self.backend.set_password(SERVICE_NAME, host, serialized)
        except Exception as exc:
            raise CredentialError("CREDENTIAL_STORE_WRITE_FAILED: OS credential store rejected the token") from exc

    def load(self, host: str) -> dict[str, Any]:
        try:
            serialized = self.backend.get_password(SERVICE_NAME, host)
        except Exception as exc:
            raise CredentialError("CREDENTIAL_STORE_READ_FAILED: cannot read the OS credential store") from exc
        if not serialized:
            raise CredentialError("NOT_LOGGED_IN: run baizhi-apps login --env <name>")
        try:
            credential = json.loads(serialized)
            token = credential["token"]
            expires_at = int(credential["expires_at"])
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise CredentialError("CREDENTIAL_STORE_INVALID: log in again") from exc
        if not isinstance(token, str) or not token:
            raise CredentialError("CREDENTIAL_STORE_INVALID: log in again")
        if expires_at <= int(self.now()):
            raise CredentialError("TOKEN_EXPIRED: token expired; run baizhi-apps login --env <name>")
        return {"token": token, "expires_at": expires_at}

    def delete(self, host: str) -> None:
        try:
            self.backend.delete_password(SERVICE_NAME, host)
        except Exception as exc:
            # keyring uses a backend-specific exception for a key not present.
            if exc.__class__.__name__ not in {"PasswordDeleteError", "PasswordNotFoundError"}:
                raise CredentialError("CREDENTIAL_STORE_DELETE_FAILED: cannot clear the OS credential store") from exc
