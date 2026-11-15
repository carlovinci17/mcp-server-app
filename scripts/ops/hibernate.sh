#!/usr/bin/env bash
# Take the app offline so it costs ~$0/month, keeping everything needed to
# bring it back with scripts/ops/wake.sh. See docs/operations.md.
#
#   1. Back up Azure config + the SQL database to backups/<timestamp>/
#      (aborts with nothing changed if the export can't be verified)
#   2. Switch the site to the offline page and push (SWA workflow deploys it)
#   3. Unlink the Function App backend, downgrade the Static Web App to Free
#   4. Stop the Function App
#   5. Delete the SQL database (only after the backup is verified + you confirm)
#
# Safe to re-run: every step skips itself if it's already done.
set -euo pipefail
source "$(dirname "$0")/_common.sh"

require_az_login

step "1/5  Back up Azure config and the SQL database"
BACKUP_DIR="$BACKUP_ROOT/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR/azure" "$BACKUP_DIR/sql"
chmod 700 "$BACKUP_ROOT" "$BACKUP_DIR"
info "Backup folder: $BACKUP_DIR"

# App settings can hold connection strings - they stay in this gitignored,
# owner-only folder and never get committed.
az staticwebapp show -n "$SWA" -g "$RG" -o json >"$BACKUP_DIR/azure/swa.json"
swa_backends_json >"$BACKUP_DIR/azure/swa-backends.json"
az staticwebapp appsettings list -n "$SWA" -g "$RG" -o json >"$BACKUP_DIR/azure/swa-appsettings.json"
az functionapp show -n "$FUNC" -g "$RG" -o json >"$BACKUP_DIR/azure/func.json"
az functionapp config appsettings list -n "$FUNC" -g "$RG" -o json \
  >"$BACKUP_DIR/azure/func-appsettings.json"

DB_BACKED_UP=false
if db_exists; then
  az sql db show -g "$RG" -s "$SQL_SERVER" -n "$SQL_DB" -o json >"$BACKUP_DIR/azure/sql-db.json"
  info "Exporting tables (the first connection can take ~1 min while the DB resumes)..."
  if uv run python scripts/ops/export_sql.py --out "$BACKUP_DIR/sql"; then
    DB_BACKED_UP=true
  else
    chmod -R go-rwx "$BACKUP_DIR"
    die "SQL export failed - nothing has been changed. See 'Troubleshooting' in docs/operations.md."
  fi
else
  info "SQL database already deleted - nothing to export."
fi
chmod -R go-rwx "$BACKUP_DIR"

cat >"$BACKUP_DIR/manifest.json" <<EOF
{
  "created_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "git_sha": "$(git rev-parse HEAD)",
  "subscription": "$(az account show --query id -o tsv)",
  "resource_group": "$RG",
  "sql_backed_up": $DB_BACKED_UP
}
EOF

step "2/5  Switch the site to offline mode"
site_mode offline
push_site_config "Take Vera offline (hibernate)"
# Don't unlink the backend while visitors could still be on the console.
# The backup above is complete either way; re-run once the deploy is green.
wait_for_site "/" 200 "Vera is offline" ||
  die "Offline page isn't live - check the GitHub Actions run, then re-run. Nothing else was changed."

step "3/5  Unlink backend and downgrade Static Web App to Free"
if [[ "$(swa_backend_count)" != "0" ]]; then
  az staticwebapp backends unlink -n "$SWA" -g "$RG" -o none
  info "Backend unlinked."
fi
if [[ "$(swa_sku)" != "Free" ]]; then
  az staticwebapp update -n "$SWA" -g "$RG" --sku Free -o none
fi
info "Static Web App SKU: $(swa_sku)"

step "4/5  Stop the Function App"
az functionapp stop -n "$FUNC" -g "$RG" -o none
info "Function App state: $(func_state)"

step "5/5  Delete the SQL database"
if ! db_exists; then
  info "Already deleted."
elif [[ "$DB_BACKED_UP" != true ]]; then
  die "Backup did not verify - the database was NOT deleted. Fix the export and re-run."
else
  info "Backup verified in $BACKUP_DIR/sql"
  if confirm "Permanently delete $SQL_SERVER/$SQL_DB?"; then
    az sql db delete -g "$RG" -s "$SQL_SERVER" -n "$SQL_DB" --yes
    info "Deleted. (Azure can also restore it for 7 days - see docs/operations.md.)"
  else
    warn "Skipped - the database keeps costing ~A\$1.90/month until it's deleted."
  fi
fi

step "Hibernated"
info "Backup: $BACKUP_DIR"
info "Bring it back with: scripts/ops/wake.sh"
