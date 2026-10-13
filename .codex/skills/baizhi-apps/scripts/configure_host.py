#!/usr/bin/env python3
"""Configure a non-secret Baizhi Apps environment Host."""

from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path
from urllib.parse import urlsplit


ENVIRONMENTS = {"production", "staging", "test"}
DEFAULT_PATH = Path.home() / ".config" / "baizhi-apps" / "hosts.json"


def validate_host(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Host must be an http:// or https:// URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Host must not contain credentials, query parameters, or fragments")
    return value.strip().rstrip("/")


def main() -> int:
    parser = argparse.ArgumentParser(description="Set one Baizhi Apps Host without storing credentials")
    parser.add_argument("environment", choices=sorted(ENVIRONMENTS))
    parser.add_argument("host")
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()

    try:
        host = validate_host(args.host)
    except ValueError as exc:
        parser.error(str(exc))
    path = args.path.expanduser()
    values: dict[str, str] = {}
    if path.exists():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise SystemExit("Host config must be a JSON object")
        for name, configured in loaded.items():
            if name not in ENVIRONMENTS:
                raise SystemExit(f"Unknown environment in config: {name}")
            values[name] = validate_host(str(configured))

    values[args.environment] = host
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(temporary, path)
    print(f"Configured {args.environment} Host in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
