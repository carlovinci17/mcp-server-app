"""Recreate the Microsoft Entra database users saved by export_sql.py.

A freshly created database only knows its server-level Entra admin, so the
Function App's managed identity needs its contained user and role
memberships back before the deployed app can query anything. Idempotent:
safe to re-run against a database that already has some or all of them.

Must be run as the server's Entra admin (your `az login` session).
"""

import argparse
import json
from pathlib import Path

from sqlalchemy import text

from src.database.sql import get_session


def _quote(identifier: str) -> str:
    return "[" + identifier.replace("]", "]]") + "]"


# T-SQL can't bind a user/role name as a parameter in CREATE USER / ALTER
# ROLE, so those are []-quoted identifiers; the comparisons are bound params.
# Names come from our own export of sys.database_principals, not user input.
def restore_statements(principals: list[dict]) -> list[tuple[str, dict]]:
    statements = []
    for principal in principals:
        user = _quote(principal["name"])
        create_user = (
            "IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = :name) "  # noqa: S608
            f"CREATE USER {user} FROM EXTERNAL PROVIDER"
        )
        statements.append((create_user, {"name": principal["name"]}))
        for role in principal["roles"]:
            statements.append(
                (
                    f"IF IS_ROLEMEMBER(:role, :name) = 0 ALTER ROLE {_quote(role)} "
                    f"ADD MEMBER {user}",
                    {"role": role, "name": principal["name"]},
                )
            )
    return statements


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("principals_file", type=Path)
    principals = json.loads(parser.parse_args().principals_file.read_text())

    with get_session() as session:
        for statement, params in restore_statements(principals):
            session.execute(text(statement), params)

    for principal in principals:
        print(f"  {principal['name']}: {', '.join(principal['roles']) or '(no roles)'}")


if __name__ == "__main__":
    main()
