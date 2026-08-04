#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${DB_NAME:-finam_core}"

echo "=== AUDIT_FEATURE_STORE_HISTORICAL_CORRECTION_ROLE_OWNERSHIP_V1 ==="

sudo -u postgres psql -X -d "$DB_NAME" -P pager=off -c "
SELECT
    n.nspname AS schema_name,
    c.relname AS object_name,
    c.relkind,
    pg_get_userbyid(c.relowner) AS owner
FROM pg_class c
JOIN pg_namespace n
  ON n.oid = c.relnamespace
WHERE n.nspname='analytics'
  AND c.relname IN (
      'feature_store_watermark_v1',
      'feature_store_historical_correction_audit_v1'
  )
ORDER BY c.relname;
"

sudo -u postgres psql -X -d "$DB_NAME" -P pager=off -c "
SELECT
    member_role.rolname AS member_role,
    granted_role.rolname AS granted_role,
    membership.admin_option
FROM pg_auth_members membership
JOIN pg_roles member_role
  ON member_role.oid = membership.member
JOIN pg_roles granted_role
  ON granted_role.oid = membership.roleid
WHERE member_role.rolname IN ('alex','finam')
ORDER BY member_role.rolname, granted_role.rolname;
"

sudo -u postgres psql -X -d "$DB_NAME" -P pager=off -c "
SELECT
    grantee,
    table_schema,
    table_name,
    privilege_type,
    is_grantable
FROM information_schema.role_table_grants
WHERE table_schema='analytics'
  AND table_name IN (
      'feature_store_watermark_v1',
      'feature_store_historical_correction_audit_v1'
  )
  AND grantee IN ('alex','finam')
ORDER BY table_name, grantee, privilege_type;
"

echo "VERDICT=FEATURE_STORE_ROLE_OWNERSHIP_AUDIT_V1_COMPLETE"
