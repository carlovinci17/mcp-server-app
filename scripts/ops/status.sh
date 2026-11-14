#!/usr/bin/env bash
# Read-only snapshot of whether the app is hibernated or live.
# See docs/operations.md.
set -euo pipefail
source "$(dirname "$0")/_common.sh"

require_az_login

swa_sku="$(az staticwebapp show -n "$SWA" -g "$RG" --query sku.name -o tsv)"
backends="$(az staticwebapp backends show -n "$SWA" -g "$RG" --query 'length(@)' -o tsv)"
func="$(func_state)"
if db_exists; then
  db="$(az sql db show -g "$RG" -s "$SQL_SERVER" -n "$SQL_DB" --query status -o tsv)"
else
  db="deleted"
fi
latest_backup="$(backups_newest_first | head -1)"

echo
printf '  %-26s %s\n' \
  "Static Web App SKU" "$swa_sku   (Standard ~A\$13/mo, Free \$0)" \
  "Linked backend" "$([[ "$backends" == 0 ]] && echo none || echo "$FUNC")" \
  "Function App" "$func" \
  "SQL database" "$db" \
  "Site config (in git)" "$(site_mode status)" \
  "Latest local backup" "${latest_backup:-none}"
echo
