# Baizhi Apps CLI reference

Install the standalone package from the repository root:

```bash
uv tool install --from ./tools/baizhi-apps-cli baizhi-apps-cli
baizhi-apps --help
```

The CLI has no dependency on the Agent runtime or MCP SDK. `httpx` performs HTTPS requests; `keyring` stores the platform token in the operating system credential manager. If a secure backend is unavailable, authentication fails closed; do not create a plaintext token file.

## Host and login

```text
baizhi-apps env list [--json]
baizhi-apps env set <production|staging|test> <http(s)-origin> [--json]
baizhi-apps login --env <name> [--email <email>] [--json]
baizhi-apps whoami --env <name> [--json]
baizhi-apps logout --env <name> [--json]
```

Host values come from `BAIZHI_APPS_HOST_PRODUCTION`, `BAIZHI_APPS_HOST_STAGING`, or `BAIZHI_APPS_HOST_TEST`, which take precedence over `~/.config/baizhi-apps/hosts.json` (or `$XDG_CONFIG_HOME/baizhi-apps/hosts.json`). Only an origin is allowed: no path, credentials, query, or fragment; production requires HTTPS. `env set` writes mode-0600 configuration and reports both the saved and currently active Host, so environment-variable overrides are visible. Never put a token, password, or secret in host configuration.

`login` prompts for a hidden password. Only the returned platform token and expiry are stored, keyed by canonical Host; the password is not retained. One account is active per Host. `logout` removes the credential locally; it does not require or send a token. V1 does not support OIDC. An expired or rejected token is not refreshed automatically; log in again. Writes are never automatically retried.

## Apps, Manifest, and schema

```text
baizhi-apps apps list --env <name> [--json]
baizhi-apps apps show <app_id> --env <name> [--json]
baizhi-apps apps create <app_id> [--name <name>] --env <name> [--confirm] [--json]
baizhi-apps manifest inspect <app_id> --env <name> [--json]
baizhi-apps schema inspect <app_id> --env <name> [--json]
baizhi-apps schema propose <app_id> --file <manifest.json> --env <name> [--confirm] [--json]
baizhi-apps schema proposal <app_id> <change_id> --env <name> [--json]
baizhi-apps schema apply <app_id> <change_id> --env <name> --confirm [--json]
```

`apps create` checks that the exact App ID is missing and creates only an empty user-owned App. The CLI gets the caller identity from `/v1/auth/me`; the server remains authoritative and does not accept a caller-selected owner. Schema proposals are based on the current App version. Apply uses the exact proposal ID.

## Data

JSON input files use UTF-8. Create/update accept one JSON object. Bulk-create accepts either a JSON array of objects or `{"records": [...]}`; the server enforces its 100-record limit and Manifest validation.

```text
baizhi-apps data list <app_id> <resource> --env <name> [--page 1] [--page-size 50] [--search <text>] [--filters '<json-array>'] [--sort '<json-array>'] [--json]
baizhi-apps data get <app_id> <resource> <record_id> --env <name> [--json]
baizhi-apps data create <app_id> <resource> --file <record.json> --env <name> [--confirm] [--json]
baizhi-apps data bulk-create <app_id> <resource> --file <records.json> --env <name> [--confirm] [--json]
baizhi-apps data update <app_id> <resource> <record_id> --file <patch.json> --env <name> [--expected-updated-at <timestamp>] [--confirm] [--json]
baizhi-apps data delete <app_id> <resource> <record_id> --env <name> --confirm [--json]
```

Filters and sort are arrays of JSON objects validated by the platform against the Manifest. Do not submit system-managed fields such as `id`, `owner_id`, `created_at`, `updated_at`, or `created_by`. Production data mutations require `--confirm`; delete requires it in every environment.

## Static H5

```text
baizhi-apps h5 package --dir <already-built-dir> --output <package.zip> [--overwrite] [--json]
baizhi-apps h5 current <app_id> --env <name> [--json]
baizhi-apps h5 releases list <app_id> --env <name> [--json]
baizhi-apps h5 releases create <app_id> --env <name> [--confirm] [--json]
baizhi-apps h5 releases upload <app_id> <release_id> --file <package.zip> --env <name> [--confirm] [--json]
baizhi-apps h5 preview <app_id> <release_id> --env <name> [--json]
baizhi-apps h5 publish <app_id> <release_id> --env <name> --confirm [--json]
baizhi-apps h5 rollback <app_id> <release_id> --env <name> --confirm [--json]
```

`h5 package` archives files at the ZIP root and requires `index.html` or `dist/index.html`. It rejects symlinks, an output path inside the source directory, and packages above the platform's current size/file-count limits. It never runs a build or any file contents. The server still performs the authoritative ZIP validation. Production Draft creation/upload require `--confirm`; publish and rollback require it everywhere. Preview returns the server-issued short-lived URL for immediate use; do not log or persist its ticket.

## Output and exit behavior

With `--json`, stdout is one JSON object:

```json
{"ok":true,"data":{},"meta":{"environment":"test","host":"http://127.0.0.1:8787"}}
```

Failures use `{"ok":false,"error":{"code":"...","message":"...","http_status":null}}` and a non-zero exit code. Human mode prints a readable JSON result to stdout and diagnostics to stderr. Platform machine error codes and HTTP status are preserved when available. Credentials, passwords, and preview tickets are not printed by login or diagnostics.
