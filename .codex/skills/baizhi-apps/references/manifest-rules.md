# Manifest rules

The Manifest is the App's data contract. Inspect it before using a table or field. Current supported field types are `text`, `integer`, `numeric`, `boolean`, `timestamp`, `uuid`, and `json`. Operations are declared per table, commonly `list`, `get`, `create`, `bulk_create`, `update`, and `delete`.

The platform manages `id`, `created_at`, `updated_at`, `created_by`, `owner_id`, and `permission`; none may be declared as a Manifest business field. Do not submit the immutable fields from Codex. An authenticated record owner may set `permission` to `public` or `private`; anonymous creates are forced to `public`, and anonymous owners cannot update or delete records. Row visibility is enforced by the Runtime, not client-side filters.

Schema changes are structured Manifest changes, not SQL. A proposal uses the current `schema_version`/Manifest version and must be applied only after version checking. Prefer additive fields and tables; treat removing fields, changing types, or removing operations as destructive.
