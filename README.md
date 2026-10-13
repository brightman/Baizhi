# Baizhi Apps CLI and Codex Skill

Install the standalone `baizhi-apps` command and the `baizhi-apps` Codex Skill to inspect and safely operate Baizhi Apps. The CLI talks to the platform Apps API with a platform-user Bearer token; it does not use MCP, App Runtime Session tokens, GraphQL, or direct database access.

## Install with an AI agent

Copy this prompt into Codex or another coding agent:

> 请帮我从 <https://github.com/brightman/Baizhi> 安装 Baizhi Apps CLI 和 `baizhi-apps` Skill，并验证 `baizhi-apps --help` 可用。先不要登录或访问、修改业务数据；等我指定环境和操作后再继续。

The Skill is in the [`baizhi-apps` directory](https://github.com/brightman/Baizhi/tree/main/.codex/skills/baizhi-apps). It contains the safety rules and links to the complete command reference.

## Manual installation

Requirements: Python 3.11 or later, [`uv`](https://docs.astral.sh/uv/), and a supported operating-system credential store (macOS Keychain, Windows Credential Manager, or a secure Linux keyring).

### Install the CLI

```bash
uv tool install --from 'git+https://github.com/brightman/Baizhi.git#subdirectory=tools/baizhi-apps-cli' baizhi-apps-cli
baizhi-apps --help
```

### Install the Codex Skill

```bash
git clone --depth 1 https://github.com/brightman/Baizhi.git
mkdir -p ~/.codex/skills
cp -R Baizhi/.codex/skills/baizhi-apps ~/.codex/skills/
```

Restart or refresh Codex so it discovers the Skill. If the Skill is already present, update that directory from the repository rather than creating a nested copy.

## Configure and sign in

Configure a named environment with the origin of your Baizhi Agent Platform. Host configuration contains no credentials.

```bash
baizhi-apps env set test https://<your-test-host>
baizhi-apps env list
baizhi-apps login --env test
baizhi-apps whoami --env test
```

`login` prompts for the password without echoing it and stores only the returned token and expiry in the OS credential store. The CLI never writes credentials to a plaintext config file. V1 supports local email/password login; it does not support OIDC. If the platform requires OIDC, stop rather than using another credential path.

Use `--env production`, `--env staging`, or `--env test` on every API operation. There is no implicit environment fallback.

## Common commands

```bash
# List Apps visible to the signed-in platform user
baizhi-apps apps list --env test

# Inspect one exact App ID and its schema
baizhi-apps apps show <app_id> --env test
baizhi-apps schema inspect <app_id> --env test

# Read rows from a declared Manifest resource
baizhi-apps data list <app_id> <resource> --env test
baizhi-apps data get <app_id> <resource> <record_id> --env test
```

Use `--json` for machine-readable output. Mutating commands are subject to explicit confirmation gates; the Skill explains which operations require `--confirm` and when user approval is required. H5 commands package an already-built static directory and never execute project build scripts.

The platform must expose the Apps API used by the CLI, including the platform-authenticated single-record route `GET /v1/apps/{app_id}/records/{resource}/{record_id}` for `data get`.

## Security boundaries

- The server remains authoritative for App ownership, Manifest validation, row visibility, and audit.
- Never paste passwords or tokens into an agent conversation. Authenticate through the CLI's local hidden prompt.
- Do not use this CLI as a route to direct PostgreSQL/Supabase access or App Runtime Session tokens.
- Publish, rollback, schema apply, deletes, production writes, and production H5 release operations remain approval-gated.

For all command options and response/error formats, see [the CLI reference](https://github.com/brightman/Baizhi/blob/main/.codex/skills/baizhi-apps/references/cli-reference.md).
