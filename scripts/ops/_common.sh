# shellcheck shell=bash disable=SC2034  # vars are used by the sourcing scripts
# Shared config + helpers for hibernate.sh / wake.sh / status.sh.
# Sourced, not executed. See docs/operations.md.

RG="mcp-app-demo"
SWA="mcp-app-demo-swa"
FUNC="mcp-app-demo-func"
SQL_SERVER="mcp-app-demo-sql"
SQL_DB="enterprise-knowledge-db"
SITE_URL="https://vortex-mcp.carlovinci.com.au"
SITE_CONFIG="web/staticwebapp.config.json"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_ROOT="$REPO_ROOT/backups"

cd "$REPO_ROOT" || exit 1

step() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
info() { printf '    %s\n' "$*"; }
warn() { printf '\033[1;33m    ! %s\033[0m\n' "$*"; }
die() {
  printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2
  exit 1
}

confirm() {
  local reply
  read -r -p "    $1 [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]]
}

require_az_login() {
  az account show --query name -o tsv >/dev/null 2>&1 ||
    die "Not logged in to Azure - run 'az login' first."
  info "Azure subscription: $(az account show --query name -o tsv)"
}

# Backup folders (UTC timestamps, so lexical order is chronological), newest first.
backups_newest_first() {
  local dirs=("$BACKUP_ROOT"/*/) i
  [[ -d "${dirs[0]}" ]] || return 0
  for ((i = ${#dirs[@]} - 1; i >= 0; i--)); do
    printf '%s\n' "${dirs[i]%/}"
  done
}

site_mode() { uv run python scripts/ops/site_mode.py "$@"; }

db_exists() {
  az sql db show -g "$RG" -s "$SQL_SERVER" -n "$SQL_DB" --query name -o tsv >/dev/null 2>&1
}

# Commit + push only the SWA config, so the Static Web Apps workflow deploys
# the mode switch. Leaves any other local changes alone.
push_site_config() {
  local message="$1"
  if git diff --quiet -- "$SITE_CONFIG"; then
    info "No site config change to push."
    return
  fi
  [[ "$(git branch --show-current)" == "main" ]] ||
    die "Not on main - the Static Web Apps workflow only deploys from main."
  git --no-pager diff --stat -- "$SITE_CONFIG"
  if ! confirm "Commit and push $SITE_CONFIG to main now?"; then
    die "Aborted. Push the change yourself, then re-run."
  fi
  git commit -m "$message" -- "$SITE_CONFIG"
  git push origin main
}

# Poll the live site until `path` returns `status` with `marker` in the body
# (i.e. the Static Web Apps deploy for the pushed config has landed).
wait_for_site() {
  local path="$1" status="$2" marker="$3" timeout="${4:-600}" waited=0
  info "Waiting for $SITE_URL$path to return $status (up to ${timeout}s)..."
  while ((waited < timeout)); do
    local body code
    body="$(curl -s -w '\n%{http_code}' "$SITE_URL$path?ts=$(date +%s)" || true)"
    code="${body##*$'\n'}"
    if [[ "$code" == "$status" && "$body" == *"$marker"* ]]; then
      info "Live: $path -> $code"
      return 0
    fi
    sleep 15
    waited=$((waited + 15))
  done
  return 1
}
