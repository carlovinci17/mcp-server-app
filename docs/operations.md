# Operations: hibernate and wake

The app can be taken fully offline ("hibernated") so it costs ~$0/month, and
brought back ("woken") in about 5 minutes. Everything lives in `scripts/ops/`:

```bash
scripts/ops/status.sh      # read-only: is it live or hibernated?
scripts/ops/hibernate.sh   # take it offline (backs up first, asks before deleting)
scripts/ops/wake.sh        # bring it back from the latest backup
```

All three need a live `az login` session, and `hibernate.sh`/`wake.sh` need
to be run from a clean checkout of `main` (they commit and push one file -
see "The offline page" below). Both are safe to re-run: each step skips
itself if it's already done.

## What it costs, and what hibernate changes

Measured from Cost Management for the `mcp-app-demo` resource group,
Aug-Nov 2026 (AUD):

| Resource | Live | Hibernated | What hibernate does |
|---|---|---|---|
| Static Web App `mcp-app-demo-swa` | ~A$13/mo (Standard plan) | $0 (Free plan) | Unlinks the backend, downgrades to Free. Hostname, custom domain, certificate, deployment token and GitHub workflow are all unaffected. |
| SQL Database `enterprise-knowledge-db` | ~A$1.90/mo ("General Purpose Data Stored") | $0 | **Backed up locally, then deleted.** The logical server `mcp-app-demo-sql` (free) is kept. |
| Function App `mcp-app-demo-func` | ~$0 (Flex Consumption, no always-ready) | $0 | Stopped, so nothing can trigger Foundry/OpenAI token spend. |
| Foundry agent, OpenAI embeddings | per-token, cents | $0 | Untouched - nothing calls them while the Function App is stopped. |
| Storage, AI Search (Free), Key Vault, App Insights, Log Analytics | ~$0 | ~$0 | Untouched, so no RBAC, blob content, or search index needs rebuilding. |

Why Standard SWA at all: the linked backend that proxies `/api/*` to the
Function App requires it (see "Deployment" in [azure.md](azure.md)). With
the backend unlinked there's nothing Standard is needed for.

Outside Azure nothing needs to change: the GitHub repo is public (Actions
are free), Google Analytics/Tag Manager are free, and the Crazy Domains
`vortex-mcp` CNAME keeps pointing at the same SWA hostname.

## The offline page

While hibernated, visitors get `web/offline.html` - "Vera is offline",
with a **Contact me for a demo** button (LinkedIn) and a link to the
`/vera-how-it-works` explainer, which stays live.

`scripts/ops/site_mode.py offline|online|status` switches
`web/staticwebapp.config.json` between modes:

- **offline** prepends routes rewriting `/`, `/index.html`, and `/api/*`
  to `/offline.html`, and points `navigationFallback` at `/offline.html`.
  (`/api/*` answers 200 with the page rather than a 503: Azure rejects a
  route that sets both `rewrite` and `statusCode`, even though the local
  SWA CLI emulator accepts it - `tests/unit/test_ops_site_mode.py` checks
  for this.)
- **online** removes exactly those, restoring the original file.

The mode is part of git, not Azure: the Static Web Apps workflow deploys
`web/` on every push to `main`. `hibernate.sh` / `wake.sh` therefore commit
and push **only** `web/staticwebapp.config.json` (after a prompt), then poll
the live site until the deploy lands. To preview locally:

```bash
uv run python scripts/ops/site_mode.py offline
npx @azure/static-web-apps-cli start web     # http://localhost:4280
uv run python scripts/ops/site_mode.py online
```

Ordering matters: hibernate takes the verified backup first (so a broken
local setup aborts with nothing changed), then switches the page **before**
unlinking the backend (so nobody lands on a console whose chat silently
fails). Wake switches the page back **last**, after `/api/health` answers.

## Backups

`hibernate.sh` writes a timestamped folder under `backups/` (gitignored,
owner-only permissions) before touching anything:

```
backups/20261114T093000Z/
  manifest.json            created time, git SHA, subscription, sql_backed_up
  sql/employees.json       same layout as data/seed/ - import_documents.py --from loads it
  sql/customers.json
  sql/documents.json
  sql/db-principals.json   Entra DB users + roles (incl. the Function App's managed identity)
  azure/sql-db.json        full `az ... show` output for each resource,
  azure/swa.json           so anything wake.sh doesn't recreate can be
  azure/swa-backends.json  done by hand from the original config
  azure/swa-appsettings.json
  azure/func.json
  azure/func-appsettings.json   may contain connection strings - never commit
```

The database is only deleted when **both** `scripts/ops/export_sql.py`
verifies every table's exported row count against a live `COUNT(*)`, **and**
you confirm at the prompt. If the export fails, hibernate stops with the
database intact.

Copy `backups/` somewhere safe (e.g. a cloud drive) if this laptop is the
only copy - it's the only full copy of the database while hibernated.

### If the local backup is lost

- **Don't count on Azure's deleted-database restore.** Azure normally
  keeps deleted databases restorable for a few days, but after the
  2026-11-15 hibernate `az sql db list-deleted -g mcp-app-demo -s
  mcp-app-demo-sql` listed nothing for this free-offer database. Worth a
  look if a hibernate was very recent, but treat `backups/` as the only copy.
- **Otherwise:** the sample data is deterministic (`random.seed(42)` in
  `scripts/create_sample_data.py`), so `create_sample_data.py` +
  `import_documents.py` rebuilds identical rows. Then recreate the Function
  App's DB user by hand (these roles are the usual read/write pair - check
  an older `db-principals.json` if you have one):
  ```sql
  CREATE USER [mcp-app-demo-func] FROM EXTERNAL PROVIDER;
  ALTER ROLE db_datareader ADD MEMBER [mcp-app-demo-func];
  ALTER ROLE db_datawriter ADD MEMBER [mcp-app-demo-func];
  ```

## What wake.sh does

1. Recreates the database: serverless Gen5, free offer, 60-min auto-pause,
   and **`--free-limit-exhaustion-behavior AutoPause`** (the original was
   `BillOverUsage`) - if the monthly free allowance runs out, the DB pauses
   until the 1st instead of billing, and the app reports it via
   `DatabaseUnavailableError` (`src/database/sql.py`).
2. Loads the latest backup with a SQL export (`import_documents.py --from`)
   and recreates DB users (`restore_db_principals.py`, idempotent). Pass a
   specific backup folder as the first argument to use an older one.
3. Starts the Function App.
4. Upgrades the SWA to Standard and relinks the Function App backend.
5. Switches the site back online, pushes, and waits for `/api/health`.

Then open the console and ask Vera something to confirm the tools return
data. Blob content and the search index were never touched, so search
works immediately.

## Troubleshooting

### `SSL Provider: OpenSSL library could not be loaded` / `Client unable to establish connection`

Every local SQL step (`export_sql.py`, `import_documents.py`, `func start`)
goes through Microsoft ODBC Driver 18, which loads OpenSSL from the
hard-coded path `/opt/homebrew/opt/openssl/lib/` and only supports OpenSSL
1.1/3.x. When Homebrew moves its `openssl` alias to OpenSSL 4 (it did on
this machine in Oct 2026), the driver can't load TLS and every connection
fails before reaching Azure. Setting `DYLD_*` variables doesn't help because
the path is absolute.

Fix by pointing the alias back at OpenSSL 3 (OpenSSL 4 stays installed for
anything that needs it; Homebrew may re-point the alias on a future
`brew upgrade`, in which case re-run this):

```bash
brew install openssl@3
ln -sfn ../Cellar/openssl@3/$(brew list --versions openssl@3 | awk '{print $2}') \
  /opt/homebrew/opt/openssl
```

`hibernate.sh` runs the export before changing anything, so hitting this
mid-hibernate leaves everything as it was.
