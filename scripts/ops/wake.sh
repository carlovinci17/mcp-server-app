#!/usr/bin/env bash
# Bring a hibernated app back online. See docs/operations.md.
#
#   scripts/ops/wake.sh                      # restore from the latest backup
#   scripts/ops/wake.sh backups/<timestamp>  # restore from a specific one
#
#   1. Recreate the SQL database (serverless, free offer, AutoPause on limit)
#   2. Restore its data and Entra users (incl. the Function App's identity)
#   3. Start the Function App
#   4. Upgrade the Static Web App to Standard and relink the backend
#   5. Switch the site back to the live console and push
#
# Safe to re-run: every step skips itself if it's already done.
set -euo pipefail
source "$(dirname "$0")/_common.sh"

require_az_login

# Latest backup that actually holds a verified SQL export (a re-run of
# hibernate after the DB is gone writes a config-only backup).
if [[ $# -ge 1 ]]; then
  BACKUP_DIR="$(cd "$1" && pwd)"
else
  BACKUP_DIR=""
  while read -r dir; do
    if [[ -f "$dir/sql/employees.json" ]]; then
      BACKUP_DIR="$dir"
      break
    fi
  done < <(backups_newest_first)
fi
[[ -n "$BACKUP_DIR" && -f "$BACKUP_DIR/sql/employees.json" ]] ||
  die "No backup with a SQL export found under $BACKUP_ROOT."
info "Restoring from: $BACKUP_DIR"

step "1/5  Recreate the SQL database"
if db_exists; then
  info "Already exists - skipping create."
else
  # AutoPause (not BillOverUsage): if the free monthly allowance ever runs
  # out, the DB pauses until the 1st instead of billing. See
  # src/database/sql.py's DatabaseUnavailableError for how the app reports it.
  az sql db create -g "$RG" -s "$SQL_SERVER" -n "$SQL_DB" \
    --edition GeneralPurpose --family Gen5 --capacity 1 \
    --compute-model Serverless --min-capacity 0.5 --auto-pause-delay 60 \
    --use-free-limit --free-limit-exhaustion-behavior AutoPause \
    --backup-storage-redundancy Local -o none
  info "Created $SQL_SERVER/$SQL_DB."
fi

step "2/5  Restore data and database users"
uv run python scripts/import_documents.py --from "$BACKUP_DIR/sql"
uv run python scripts/ops/restore_db_principals.py "$BACKUP_DIR/sql/db-principals.json"

step "3/5  Start the Function App"
az functionapp start -n "$FUNC" -g "$RG" -o none
info "Function App state: $(func_state)"

step "4/5  Upgrade Static Web App to Standard and relink the backend"
if [[ "$(az staticwebapp show -n "$SWA" -g "$RG" --query sku.name -o tsv)" != "Standard" ]]; then
  az staticwebapp update -n "$SWA" -g "$RG" --sku Standard -o none
fi
if [[ "$(az staticwebapp backends show -n "$SWA" -g "$RG" --query 'length(@)' -o tsv)" == "0" ]]; then
  BACKEND_ID="$(jq -r '.[0].backendResourceId' "$BACKUP_DIR/azure/swa-backends.json" 2>/dev/null || true)"
  BACKEND_REGION="$(jq -r '.[0].region' "$BACKUP_DIR/azure/swa-backends.json" 2>/dev/null || true)"
  [[ -n "$BACKEND_ID" && "$BACKEND_ID" != null ]] ||
    BACKEND_ID="$(az functionapp show -n "$FUNC" -g "$RG" --query id -o tsv)"
  [[ -n "$BACKEND_REGION" && "$BACKEND_REGION" != null ]] ||
    BACKEND_REGION="$(az functionapp show -n "$FUNC" -g "$RG" --query location -o tsv)"
  az staticwebapp backends link -n "$SWA" -g "$RG" \
    --backend-resource-id "$BACKEND_ID" --backend-region "$BACKEND_REGION" -o none
  info "Backend linked."
fi
info "Static Web App SKU: $(az staticwebapp show -n "$SWA" -g "$RG" --query sku.name -o tsv)"

step "5/5  Switch the site back to the live console"
site_mode online
push_site_config "Bring Vera back online (wake)"
wait_for_site "/api/health" 200 "status" ||
  warn "/api/health not answering yet - check the GitHub Actions run and the Function App."

step "Awake"
info "Console: $SITE_URL"
info "Tip: open the console and ask Vera a question to confirm the MCP tools return data."
