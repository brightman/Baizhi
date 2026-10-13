---
name: baizhi-apps
description: Use the standalone baizhi-apps CLI to inspect and safely operate Baizhi Apps, Manifest schemas, records, and static H5 releases.
---

# Baizhi Apps

Use the installed `baizhi-apps` CLI as the only transport for Baizhi Apps work. Never fall back to MCP, App Runtime Session tokens, GraphQL, SQL, direct PostgreSQL/Supabase access, or browser-local credentials. The CLI authenticates as the platform user and leaves authorization, Manifest validation, row visibility, and audit to the server.

## Start safely

1. Resolve an explicitly named environment (`production`, `staging`, or `test`) using [hosts.md](references/hosts.md). If none is named, ask; do not guess or fall back to another environment.
2. Confirm `baizhi-apps` is available (`baizhi-apps --help`). If missing, follow [cli-reference.md](references/cli-reference.md) to install it.
3. Use `baizhi-apps login --env <environment>` only when the user directs you to authenticate or the current token is missing/expired. Never ask the user to paste a password or token into chat. V1 supports local email/password login only; if the platform returns `OIDC_ONLY`, stop and report that this host requires unsupported OIDC.
4. Before any App operation, require the exact `APPID`; do not infer it from a display name. Load [app-lifecycle.md](references/app-lifecycle.md) and inspect the App first.

## APPID-first lifecycle

- Inspect the App and current Manifest/schema before using tables or fields. Only use declared fields and operations. System-managed `id`, `owner_id`, `created_at`, `updated_at`, `created_by`, and `permission` are not business fields.
- Use `apps create` only for the exact missing APPID when the user has asked for an App operation. It creates an empty user-owned App; it does not create schema, records, or H5 releases.
- Use schema proposals against the current version. Apply only the exact proposal after explicit user approval; inspect the version again after apply.
- For data writes, summarize the exact App, table, fields, count, and relevant filters when the operation is bulk or ambiguous. Deletes, schema apply, production writes, H5 publish, and H5 rollback require `--confirm` under the CLI policy. A CLI confirmation flag is only valid after the user has authorized that exact effect; do not invent approval.
- Use [manifest-rules.md](references/manifest-rules.md) and [cli-reference.md](references/cli-reference.md) for operation semantics and command syntax.

## H5 lifecycle

H5 is static content only. The CLI packages an already-built directory; it does not run package managers, builds, or scripts. Follow [h5-hosting.md](references/h5-hosting.md): package, create an explicit Draft, upload and validate, inspect the server-issued preview, and publish only after explicit confirmation. Always name the exact APPID and release ID. Never silently publish the latest Draft.

## Reporting

Report the selected environment and Host, exact App ID, Manifest version, affected record IDs/counts, or H5 release state/URL. Distinguish a successful upload/Draft Preview from a Published release. Preserve machine-readable error codes and never claim an operation succeeded if the CLI returned a non-zero exit or `ok: false`.
