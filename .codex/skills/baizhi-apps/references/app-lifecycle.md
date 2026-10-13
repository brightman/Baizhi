# APPID-first lifecycle

Resolve an explicit named environment and the exact `APPID` before starting. Never choose an App from a similar name or switch to another environment when the selected one is unavailable.

1. Run `baizhi-apps apps show <app_id> --env <environment>`.
2. If and only if that exact ID returns HTTP 404, and the user asked you to perform an Apps operation, run `baizhi-apps apps create <app_id> [--name <name>] --env <environment>`. The CLI checks the ID again and creates an empty App owned by the authenticated platform user. It creates no Manifest, table, record, or H5 release.
3. Re-read the App with `apps show`, then inspect `manifest inspect` and `schema inspect` before table/data work.

Report whether the App was inspected or created, the exact APPID, environment/Host, and Manifest version.

## Schema and records

- Inspect current schema before suggesting changes. `schema propose` records a versioned proposal; it does not apply it.
- Show the exact proposal ID and changes. Apply only after the user explicitly approves that proposal, with `schema apply <app_id> <change_id> --confirm`.
- Re-read App/schema after apply and report the new version.
- Before data writes, validate the target table, fields, and operation against the Manifest. Never send system-managed fields or trust `owner_id` from user input.
- Before a bulk write or delete, state exact App, table, count, fields, and filters. `data delete` always requires `--confirm`; production mutations require `--confirm`.
- Single-record reads use the platform Bearer API and return 404 for both missing and row-policy-invisible records.

## H5 release

The exact release ID must be supplied or returned by the immediately preceding create command and confirmed in the release list. Use this sequence:

```text
baizhi-apps h5 package --dir <already-built-static-dir> --output <package.zip>
baizhi-apps h5 releases create <app_id> --env <environment> [--confirm]
baizhi-apps h5 releases upload <app_id> <release_id> --file <package.zip> --env <environment> [--confirm]
baizhi-apps h5 preview <app_id> <release_id> --env <environment>
baizhi-apps h5 publish <app_id> <release_id> --env <environment> --confirm
```

The H5 CLI never builds or executes project code. Preview URLs contain a short-lived ticket; use them only for immediate inspection and never store them in credentials or logs. Production Draft creation/upload require `--confirm`; publish and rollback require it in every environment. Before either publish or rollback, tell the user the exact App/release, current release, Host, and effect, then wait for explicit approval.

Read [cli-reference.md](cli-reference.md) for complete command options and output/error contracts.
