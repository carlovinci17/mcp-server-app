"""Back up the Azure SQL Database to local JSON before hibernate deletes it.

Writes `<out>/employees.json`, `customers.json`, and `documents.json` in the
exact layout of `data/seed/`, so `scripts/import_documents.py --from <out>`
restores them unchanged. Also writes `db-principals.json` (the Microsoft
Entra users - e.g. the Function App's managed identity - and their role
memberships) for `restore_db_principals.py`.

Exits non-zero unless every exported table's row count matches a live
`COUNT(*)`, which `hibernate.sh` relies on as the gate before deleting the
database. See docs/operations.md.
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.database.models import Base, CustomerRecord, DocumentMetadataRecord, EmployeeRecord
from src.database.sql import get_session

# Output filename -> model. Filenames match data/seed/ so import_documents.py
# can load a backup directly.
TABLES: dict[str, type[Base]] = {
    "employees.json": EmployeeRecord,
    "customers.json": CustomerRecord,
    "documents.json": DocumentMetadataRecord,
}

_PRINCIPALS_QUERY = text("""
    SELECT p.name, p.type_desc, r.name AS role_name
    FROM sys.database_principals p
    LEFT JOIN sys.database_role_members m ON m.member_principal_id = p.principal_id
    LEFT JOIN sys.database_principals r ON r.principal_id = m.role_principal_id
    WHERE p.type IN ('E', 'X')
    ORDER BY p.name, r.name
    """)


def _row_to_dict(record: Base) -> dict:
    row = {}
    for column in record.__table__.columns:
        value = getattr(record, column.key)
        if isinstance(value, datetime | date):
            value = value.isoformat()
        row[column.key] = value
    return row


def _managers_first(employees: list[dict]) -> list[dict]:
    # import_documents.py merges employees one by one; a manager has to exist
    # before anyone whose manager_id FK points at them.
    by_id = {e["id"]: e for e in employees}
    ordered: list[dict] = []
    placed: set[str] = set()

    def place(employee: dict) -> None:
        if employee["id"] in placed:
            return
        manager = by_id.get(employee["manager_id"])
        if manager is not None:
            place(manager)
        placed.add(employee["id"])
        ordered.append(employee)

    for employee in employees:
        place(employee)
    return ordered


def export_tables(session: Session) -> dict[str, list[dict]]:
    exported = {}
    for filename, model in TABLES.items():
        records = session.scalars(select(model).order_by(model.id)).all()
        exported[filename] = [_row_to_dict(r) for r in records]
    exported["employees.json"] = _managers_first(exported["employees.json"])
    return exported


def live_counts(session: Session) -> dict[str, int]:
    return {
        filename: session.scalar(select(func.count()).select_from(model))
        for filename, model in TABLES.items()
    }


def export_principals(session: Session) -> list[dict]:
    principals: dict[str, dict] = {}
    for name, type_desc, role_name in session.execute(_PRINCIPALS_QUERY):
        entry = principals.setdefault(name, {"name": name, "type": type_desc, "roles": []})
        if role_name:
            entry["roles"].append(role_name)
    return list(principals.values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    out_dir = parser.parse_args().out
    out_dir.mkdir(parents=True, exist_ok=True)

    with get_session() as session:
        exported = export_tables(session)
        counts = live_counts(session)
        principals = export_principals(session)

    for filename, rows in exported.items():
        (out_dir / filename).write_text(json.dumps(rows, indent=2))
    (out_dir / "db-principals.json").write_text(json.dumps(principals, indent=2))

    mismatched = False
    for filename, rows in exported.items():
        status = "ok" if len(rows) == counts[filename] else "MISMATCH"
        mismatched |= status != "ok"
        print(f"  {filename:16} exported={len(rows):<5} live={counts[filename]:<5} {status}")
    print(f"  db-principals    {', '.join(p['name'] for p in principals) or '(none)'}")

    if mismatched or not all(counts.values()):
        print("Export verification FAILED - do not delete the database.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
