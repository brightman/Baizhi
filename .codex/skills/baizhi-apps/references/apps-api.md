# Apps API and authentication boundary

The CLI uses the platform-user Bearer token returned by local `/v1/auth/login` for authenticated `/v1/apps` management APIs. It does not use an App Runtime Session token. H5 frontend code must not receive platform-user tokens or client secrets.

The Runtime API and GraphQL API are separate H5/runtime interfaces. GraphQL is mounted under `/v1/runtime/apps/{app_id}/graphql` and requires an App Runtime Session with the appropriate data scope. Do not use it as a shortcut for CLI operations. The platform Bearer single-record route is `GET /v1/apps/{app_id}/records/{resource}/{record_id}`; it delegates to the Apps service and preserves Manifest, App access, and row-visibility checks. Missing and policy-invisible records both return 404.

The server is authoritative for identity, ownership, App access, schema, record policy, and audit. The CLI never sends service-role credentials, directly accesses PostgreSQL/Supabase, or reproduces row authorization locally. It disables redirects on authenticated requests so the platform Bearer token is not forwarded to another origin.

V1 login is local email/password only. If a host is configured for OIDC and returns `OIDC_ONLY`, stop. Do not switch to browser OAuth, MCP authorization, or a different stored credential.
