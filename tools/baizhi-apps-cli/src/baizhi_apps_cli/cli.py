from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path
from typing import Any, TextIO
from urllib.parse import quote

from .archive import package_static_directory
from .client import ApiClient, ApiError
from .config import HostConfig, HostConfigError
from .credentials import CredentialError, CredentialStore
from .policy import ConfirmationRequired, require_confirmation


class CommandError(RuntimeError):
    def __init__(self, code: str, message: str, http_status: int | None = None) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def _add_api_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--env", required=True, choices=("production", "staging", "test"))
    parser.add_argument("--json", action="store_true", dest="json_output")


def _add_confirm(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--confirm", action="store_true")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="baizhi-apps", description="Safely access Baizhi Apps.")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    groups = parser.add_subparsers(dest="group", required=True)

    env_group = groups.add_parser("env", help="Configure named platform hosts")
    env_commands = env_group.add_subparsers(dest="action", required=True)
    env_list = env_commands.add_parser("list")
    env_list.add_argument("--json", action="store_true", dest="json_output")
    env_set = env_commands.add_parser("set")
    env_set.add_argument("environment", choices=("production", "staging", "test"))
    env_set.add_argument("host")
    env_set.add_argument("--json", action="store_true", dest="json_output")

    login = groups.add_parser("login", help="Sign in with local platform credentials")
    _add_api_options(login)
    login.add_argument("--email")
    logout = groups.add_parser("logout", help="Clear the token for a named host")
    _add_api_options(logout)
    whoami = groups.add_parser("whoami", help="Show the authenticated platform user")
    _add_api_options(whoami)

    apps = groups.add_parser("apps", help="Inspect or create Apps")
    app_commands = apps.add_subparsers(dest="action", required=True)
    app_list = app_commands.add_parser("list")
    _add_api_options(app_list)
    app_show = app_commands.add_parser("show")
    app_show.add_argument("app_id")
    _add_api_options(app_show)
    app_create = app_commands.add_parser("create")
    app_create.add_argument("app_id")
    app_create.add_argument("--name")
    _add_confirm(app_create)
    _add_api_options(app_create)

    manifest = groups.add_parser("manifest", help="Inspect the current App Manifest")
    manifest_commands = manifest.add_subparsers(dest="action", required=True)
    manifest_inspect = manifest_commands.add_parser("inspect")
    manifest_inspect.add_argument("app_id")
    _add_api_options(manifest_inspect)

    schema = groups.add_parser("schema", help="Inspect and apply versioned schema proposals")
    schema_commands = schema.add_subparsers(dest="action", required=True)
    schema_inspect = schema_commands.add_parser("inspect")
    schema_inspect.add_argument("app_id")
    _add_api_options(schema_inspect)
    schema_propose = schema_commands.add_parser("propose")
    schema_propose.add_argument("app_id")
    schema_propose.add_argument("--file", required=True, type=Path)
    _add_confirm(schema_propose)
    _add_api_options(schema_propose)
    schema_proposal = schema_commands.add_parser("proposal")
    schema_proposal.add_argument("app_id")
    schema_proposal.add_argument("change_id")
    _add_api_options(schema_proposal)
    schema_apply = schema_commands.add_parser("apply")
    schema_apply.add_argument("app_id")
    schema_apply.add_argument("change_id")
    _add_confirm(schema_apply)
    _add_api_options(schema_apply)

    data = groups.add_parser("data", help="Read and mutate Manifest-governed records")
    data_commands = data.add_subparsers(dest="action", required=True)
    data_list = data_commands.add_parser("list")
    data_list.add_argument("app_id")
    data_list.add_argument("resource")
    data_list.add_argument("--page", type=int, default=1)
    data_list.add_argument("--page-size", type=int, default=50)
    data_list.add_argument("--search", default="")
    data_list.add_argument("--filters", default="[]", help="JSON array of Manifest field filters")
    data_list.add_argument("--sort", default="[]", help="JSON array of Manifest field sort rules")
    _add_api_options(data_list)
    data_get = data_commands.add_parser("get")
    data_get.add_argument("app_id")
    data_get.add_argument("resource")
    data_get.add_argument("record_id")
    _add_api_options(data_get)
    for action in ("create", "bulk-create", "update"):
        command = data_commands.add_parser(action)
        command.add_argument("app_id")
        command.add_argument("resource")
        if action == "update":
            command.add_argument("record_id")
            command.add_argument("--expected-updated-at")
        command.add_argument("--file", required=True, type=Path)
        _add_confirm(command)
        _add_api_options(command)
    data_delete = data_commands.add_parser("delete")
    data_delete.add_argument("app_id")
    data_delete.add_argument("resource")
    data_delete.add_argument("record_id")
    _add_confirm(data_delete)
    _add_api_options(data_delete)

    h5 = groups.add_parser("h5", help="Package and release static H5 content")
    h5_commands = h5.add_subparsers(dest="action", required=True)
    package = h5_commands.add_parser("package")
    package.add_argument("--dir", required=True, type=Path)
    package.add_argument("--output", required=True, type=Path)
    package.add_argument("--overwrite", action="store_true")
    package.add_argument("--json", action="store_true", dest="json_output")
    current = h5_commands.add_parser("current")
    current.add_argument("app_id")
    _add_api_options(current)
    releases = h5_commands.add_parser("releases")
    release_commands = releases.add_subparsers(dest="release_action", required=True)
    release_list = release_commands.add_parser("list")
    release_list.add_argument("app_id")
    _add_api_options(release_list)
    release_create = release_commands.add_parser("create")
    release_create.add_argument("app_id")
    _add_confirm(release_create)
    _add_api_options(release_create)
    release_upload = release_commands.add_parser("upload")
    release_upload.add_argument("app_id")
    release_upload.add_argument("release_id")
    release_upload.add_argument("--file", required=True, type=Path)
    _add_confirm(release_upload)
    _add_api_options(release_upload)
    for action in ("preview", "publish", "rollback"):
        command = h5_commands.add_parser(action)
        command.add_argument("app_id")
        command.add_argument("release_id")
        if action in {"publish", "rollback"}:
            _add_confirm(command)
        _add_api_options(command)
    return parser


def _emit_success(data: Any, *, environment: str | None, host: str | None, json_output: bool, stdout: TextIO) -> None:
    if json_output:
        payload = {"ok": True, "data": data, "meta": {}}
        if environment is not None:
            payload["meta"].update({"environment": environment, "host": host})
        else:
            payload["meta"]["operation"] = "local"
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), file=stdout)
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str), file=stdout)


def _emit_error(error: Exception, *, json_output: bool, stdout: TextIO, stderr: TextIO) -> int:
    if isinstance(error, ApiError):
        code, message, status = error.code, error.message, error.http_status
    elif isinstance(error, CommandError):
        code, message, status = error.code, error.message, error.http_status
    elif isinstance(error, (CredentialError, HostConfigError, ConfirmationRequired)):
        raw = str(error)
        code, _, message = raw.partition(":")
        message = message.strip() or raw
        status = None
    elif isinstance(error, ValueError):
        raw = str(error)
        code, _, message = raw.partition(":")
        message = message.strip() or raw
        status = None
    elif isinstance(error, FileNotFoundError):
        code, message, status = "FILE_NOT_FOUND", "The specified input file or directory was not found.", None
    elif isinstance(error, (OSError, json.JSONDecodeError)):
        code, message, status = "LOCAL_INPUT_INVALID", "Could not read or write the requested local file.", None
    else:
        code, message, status = "CLI_ERROR", "The requested command did not complete.", None
    payload = {"ok": False, "error": {"code": code, "message": message, "http_status": status}}
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), file=stdout)
    else:
        print(f"{code}: {message}", file=stderr)
    return 1


def _escape(*segments: str) -> str:
    return "/".join(quote(str(segment), safe="") for segment in segments)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON_INVALID: {path.name} is not valid JSON") from exc


def _json_array(raw: str, name: str) -> list[dict[str, Any]]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name.upper()}_INVALID: expected a JSON array") from exc
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(f"{name.upper()}_INVALID: expected an array of JSON objects")
    return value


def _run(args: argparse.Namespace, *, stdout: TextIO) -> tuple[Any, str | None, str | None]:
    if args.group == "env":
        config = HostConfig()
        if args.action == "set":
            configured_host = config.set(args.environment, args.host)
            data = {
                "environment": args.environment,
                "configured_host": configured_host,
                "active_host": config.resolve(args.environment),
            }
        else:
            data = {"environments": config.list()}
        return data, None, None

    if args.group == "h5" and args.action == "package":
        return package_static_directory(args.dir, args.output, overwrite=args.overwrite), None, None

    config = HostConfig()
    host = config.resolve(args.env)
    if args.group == "login":
        try:
            email = (args.email or input("Email: ")).strip()
            password = getpass.getpass("Password: ")
        except (EOFError, KeyboardInterrupt) as exc:
            raise CommandError("LOGIN_INPUT_REQUIRED", "Login requires an interactive terminal; credentials were not stored.") from exc
        client = ApiClient(host)
        try:
            result = client.request("POST", "/v1/auth/login", json={"email": email, "password": password})
        finally:
            client.close()
        if not isinstance(result, dict):
            raise ValueError("LOGIN_RESPONSE_INVALID: platform returned an invalid login response")
        token = result.get("token")
        expires_at = result.get("expires_at")
        CredentialStore().save(host, {"token": token, "expires_at": expires_at})
        public_result = {key: value for key, value in result.items() if key not in {"token", "expires_at"}}
        public_result["expires_at"] = expires_at
        return public_result, args.env, host

    credentials = CredentialStore()
    if args.group == "logout":
        credentials.delete(host)
        return {"logged_out": True, "host": host}, args.env, host
    token = credentials.load(host)["token"]
    api = ApiClient(host, token)
    try:
        return _dispatch_api(args, api, host), args.env, host
    finally:
        api.close()


def _dispatch_api(args: argparse.Namespace, api: ApiClient, host: str) -> Any:
    group, action = args.group, getattr(args, "action", None)
    if group == "whoami":
        return api.request("GET", "/v1/auth/me")
    if group == "apps":
        if action == "list":
            return api.request("GET", "/v1/apps")
        app_id = args.app_id
        if action == "show":
            return api.request("GET", f"/v1/apps/{_escape(app_id)}")
        require_confirmation(args.env, "apps.create", app_id, confirmed=args.confirm)
        existing = None
        try:
            existing = api.request("GET", f"/v1/apps/{_escape(app_id)}")
        except ApiError as exc:
            if exc.http_status != 404:
                raise
        if existing is not None:
            raise ApiError("APP_ALREADY_EXISTS", "The exact App ID already exists.", 409)
        identity = api.request("GET", "/v1/auth/me")
        return api.request("POST", "/v1/apps", json={
            "app_id": app_id, "name": args.name or app_id,
            "owner_type": "user", "owner_id": identity["user_id"],
        })
    if group == "manifest":
        app = api.request("GET", f"/v1/apps/{_escape(args.app_id)}")
        return {"app_id": args.app_id, "version": app.get("version"), "manifest": app.get("manifest") or {}}
    if group == "schema":
        app_path = f"/v1/apps/{_escape(args.app_id)}"
        if action == "inspect":
            return api.request("GET", app_path + "/schema")
        if action == "propose":
            require_confirmation(args.env, "schema.propose", args.app_id, confirmed=args.confirm)
            app = api.request("GET", app_path)
            return api.request("POST", app_path + "/schema/proposals", json={
                "manifest": _read_json(args.file), "expected_version": app["version"],
            })
        change_path = app_path + f"/schema/proposals/{_escape(args.change_id)}"
        if action == "proposal":
            return api.request("GET", change_path)
        require_confirmation(args.env, "schema.apply", f"{args.app_id}/{args.change_id}", confirmed=args.confirm)
        return api.request("POST", change_path + "/apply")
    if group == "data":
        app_id, resource = _escape(args.app_id), _escape(args.resource)
        records_path = f"/v1/apps/{app_id}/tables/{resource}/records"
        if action == "list":
            if args.page < 1 or not 1 <= args.page_size <= 100:
                raise ValueError("GRID_QUERY_INVALID: page must be positive and page-size must be from 1 to 100")
            return api.request("GET", records_path, params={
                "page": args.page,
                "page_size": args.page_size,
                "search": args.search,
                "filters": json.dumps(_json_array(args.filters, "filters"), separators=(",", ":")),
                "sort": json.dumps(_json_array(args.sort, "sort"), separators=(",", ":")),
            })
        record_path = f"/v1/apps/{app_id}/records/{resource}"
        if action == "get":
            return api.request("GET", record_path + "/" + _escape(args.record_id))
        if action == "create":
            require_confirmation(args.env, "data.create", f"{args.app_id}/{args.resource}", confirmed=args.confirm)
            payload = _read_json(args.file)
            if not isinstance(payload, dict):
                raise ValueError("RECORD_INVALID: expected a JSON object")
            return api.request("POST", record_path, json={"data": payload})
        if action == "bulk-create":
            require_confirmation(args.env, "data.bulk_create", f"{args.app_id}/{args.resource}", confirmed=args.confirm)
            payload = _read_json(args.file)
            records = payload.get("records") if isinstance(payload, dict) else payload
            if not isinstance(records, list):
                raise ValueError("RECORDS_INVALID: expected a JSON array or an object with records")
            return api.request("POST", record_path + "/bulk", json={"records": records})
        if action == "update":
            require_confirmation(args.env, "data.update", f"{args.app_id}/{args.resource}/{args.record_id}", confirmed=args.confirm)
            payload = _read_json(args.file)
            if not isinstance(payload, dict):
                raise ValueError("RECORD_INVALID: expected a JSON object")
            body = {"data": payload}
            if args.expected_updated_at:
                body["expected_updated_at"] = args.expected_updated_at
            return api.request("PATCH", record_path + "/" + _escape(args.record_id), json=body)
        require_confirmation(args.env, "data.delete", f"{args.app_id}/{args.resource}/{args.record_id}", confirmed=args.confirm)
        return api.request("DELETE", record_path + "/" + _escape(args.record_id))
    if group == "h5":
        app_path = f"/v1/apps/{_escape(args.app_id)}/h5"
        if action == "current":
            return api.request("GET", app_path)
        if action == "releases":
            if args.release_action == "list":
                return api.request("GET", app_path + "/releases")
            if args.release_action == "create":
                require_confirmation(args.env, "h5.release.create", args.app_id, confirmed=args.confirm)
                return api.request("POST", app_path + "/releases")
            require_confirmation(args.env, "h5.upload", f"{args.app_id}/{args.release_id}", confirmed=args.confirm)
            with args.file.open("rb") as package:
                return api.request(
                    "POST", app_path + f"/releases/{_escape(args.release_id)}/upload",
                    files={"file": (args.file.name, package, "application/zip")},
                )
        release_id = _escape(args.release_id)
        releases_path = app_path + "/releases"
        if action == "preview":
            response = api.request("GET", releases_path)
            matches = [item for item in response.get("items", []) if item.get("release_id") == args.release_id]
            if not matches:
                raise ApiError("H5_RELEASE_NOT_FOUND", "The exact release was not found.", 404)
            preview_url = matches[0].get("preview_url")
            if not preview_url:
                raise ApiError("H5_PREVIEW_UNAVAILABLE", "This release has no preview URL.")
            return {"app_id": args.app_id, "release_id": args.release_id, "preview_url": preview_url}
        if action == "publish":
            require_confirmation(args.env, "h5.publish", f"{args.app_id}/{args.release_id}", confirmed=args.confirm)
            return api.request("POST", releases_path + f"/{release_id}/publish")
        require_confirmation(args.env, "h5.rollback", f"{args.app_id}/{args.release_id}", confirmed=args.confirm)
        return api.request("POST", releases_path + f"/{release_id}/rollback")
    raise CommandError("COMMAND_UNSUPPORTED", "The requested command is not supported.")


def main(argv: list[str] | None = None, *, stdout: TextIO | None = None, stderr: TextIO | None = None) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
        data, environment, host = _run(args, stdout=stdout)
        _emit_success(
            data,
            environment=environment,
            host=host,
            json_output=getattr(args, "json_output", False),
            stdout=stdout,
        )
        return 0
    except SystemExit as exc:
        return int(exc.code or 0)
    except Exception as exc:
        return _emit_error(
            exc,
            json_output=bool(locals().get("args") and getattr(args, "json_output", False)),
            stdout=stdout,
            stderr=stderr,
        )
