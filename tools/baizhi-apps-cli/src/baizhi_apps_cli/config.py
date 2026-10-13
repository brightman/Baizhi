from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit, urlunsplit


ENVIRONMENTS = ("production", "staging", "test")


class HostConfigError(ValueError):
    pass


def normalize_host(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HostConfigError("HOST_INVALID: host must be an http(s) origin")
    try:
        parts = urlsplit(value.strip())
        port = parts.port
    except ValueError as exc:
        raise HostConfigError("HOST_INVALID: host must be an http(s) origin") from exc
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.path not in {"", "/"}
        or parts.query
        or parts.fragment
    ):
        raise HostConfigError("HOST_INVALID: provide only an http(s) origin without credentials, path, query, or fragment")
    hostname = parts.hostname.lower()
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = hostname + (f":{port}" if port is not None else "")
    return urlunsplit((parts.scheme.lower(), netloc, "", "", ""))


def _validate_environment(name: str) -> str:
    normalized = str(name).strip().lower()
    if normalized not in ENVIRONMENTS:
        raise HostConfigError(f"ENVIRONMENT_INVALID: choose one of {', '.join(ENVIRONMENTS)}")
    return normalized


class HostConfig:
    def __init__(
        self,
        *,
        environ: Mapping[str, str] | None = None,
        config_path: Path | None = None,
    ) -> None:
        self.environ = os.environ if environ is None else environ
        if config_path is not None:
            self.config_path = Path(config_path)
        else:
            root = self.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
            self.config_path = Path(root) / "baizhi-apps" / "hosts.json"

    def _read(self) -> dict[str, str]:
        if not self.config_path.exists():
            return {}
        try:
            raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HostConfigError(f"HOST_CONFIG_INVALID: cannot read {self.config_path}") from exc
        if not isinstance(raw, dict):
            raise HostConfigError("HOST_CONFIG_INVALID: expected a JSON object")
        values: dict[str, str] = {}
        for key, value in raw.items():
            env = _validate_environment(key)
            values[env] = self._for_environment(env, value)
        return values

    def resolve(self, environment: str) -> str:
        environment = _validate_environment(environment)
        env_value = self.environ.get(f"BAIZHI_APPS_HOST_{environment.upper()}")
        if env_value:
            return self._for_environment(environment, env_value)
        host = self._read().get(environment)
        if not host:
            raise HostConfigError(
                f"HOST_NOT_CONFIGURED: run baizhi-apps env set {environment} <https-origin>"
            )
        return self._for_environment(environment, host)

    @staticmethod
    def _for_environment(environment: str, value: str) -> str:
        host = normalize_host(value)
        if environment == "production" and not host.startswith("https://"):
            raise HostConfigError("HOST_HTTPS_REQUIRED: production Hosts must use HTTPS")
        return host

    def set(self, environment: str, host: str) -> str:
        environment = _validate_environment(environment)
        normalized = self._for_environment(environment, host)
        values = self._read()
        values[environment] = normalized
        self.config_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, temporary = tempfile.mkstemp(prefix=".hosts.", dir=self.config_path.parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(values, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.config_path)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return normalized

    def list(self) -> dict[str, str | None]:
        configured = self._read()
        return {
            environment: (
                self._for_environment(environment, self.environ[f"BAIZHI_APPS_HOST_{environment.upper()}"])
                if self.environ.get(f"BAIZHI_APPS_HOST_{environment.upper()}")
                else configured.get(environment)
            )
            for environment in ENVIRONMENTS
        }
