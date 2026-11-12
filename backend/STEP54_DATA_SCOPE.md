# Step 54 — Data Scope

- Adds persisted user data-scope grants for `global`, `company`, `department`, and `owner` scopes.
- Company/department scope values are opaque identifiers until their domain tables are introduced.
- Adds reusable SQLAlchemy statement filtering. No grants means deny all; `global` grants allow all; multiple non-global grants are OR-combined.
- Owner scope is always tied to the authenticated user's ID and can only match `owner_id` or `created_by_id` columns.
- Adds IAM API to list, grant, and revoke a user's data scopes; protected by `users.scopes.manage`.
- Adds Alembic migration `20261110_0003`.
- Existing business tables do not yet exist, so scope predicates are exposed as a reusable repository/query helper and are tested against representative models. Domain repositories must call `apply_data_scope` when introduced.
