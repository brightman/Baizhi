# Baizhi Apps Host configuration

The Skill supports three named environments:

| Name | Meaning | Safe default |
|---|---|---|
| `production` | Live business data and live H5 | Never guess; require explicit selection for writes |
| `staging` | Pre-release validation environment | Use only when explicitly selected |
| `test` | Automated/local integration environment | Use only when explicitly selected |

Configure Hosts without credentials. The recommended environment variables are:

```text
BAIZHI_APPS_HOST_PRODUCTION=https://<production-host>
BAIZHI_APPS_HOST_STAGING=https://<staging-host>
BAIZHI_APPS_HOST_TEST=https://<test-host>
```

For local Codex sessions, an equivalent non-secret JSON file may be used at `~/.config/baizhi-apps/hosts.json`. Configure it with the CLI:

```bash
baizhi-apps env set production https://apps.example.com
```

Environment variables take precedence over the JSON file. Do not put Authorization headers, API keys, passwords, OIDC secrets, Supabase keys, or App Runtime secrets in this file. Credentials belong in the operating system credential store managed by the CLI.

Selection rules:

1. An explicit user environment name wins.
2. A Host explicitly supplied for the current task wins over the configured value, but must not be persisted automatically.
3. If a named environment has no configured Host, stop and ask the user to configure it; do not fall back to another environment.
4. Include the selected environment and Host origin in the operation summary, but never print credentials.
5. There is no configured default Host. If neither a named environment nor a full Host is supplied, ask the user to select an environment before calling an Apps API.
