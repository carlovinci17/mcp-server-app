import json
from datetime import date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, CustomerRecord, DocumentMetadataRecord, EmployeeRecord
from tests.unit._script_loader import load_script

export_sql = load_script("scripts/ops/export_sql.py")
restore_db_principals = load_script("scripts/ops/restore_db_principals.py")


def test_export_matches_live_counts(seeded_session_factory):
    with seeded_session_factory() as session:
        exported = export_sql.export_tables(session)
        counts = export_sql.live_counts(session)

    assert {name: len(rows) for name, rows in exported.items()} == counts
    assert counts == {"employees.json": 2, "customers.json": 1, "documents.json": 3}


def test_export_is_json_serialisable_in_seed_format(seeded_session_factory):
    with seeded_session_factory() as session:
        exported = export_sql.export_tables(session)

    doc = exported["documents.json"][0]
    json.dumps(exported)
    assert isinstance(doc["created_at"], str)
    assert doc["tags"] == ["engineering", "document"]


def test_employees_exported_managers_first():
    employees = [
        {"id": "emp-001", "manager_id": "emp-003"},
        {"id": "emp-002", "manager_id": "emp-001"},
        {"id": "emp-003", "manager_id": None},
    ]

    ordered = [e["id"] for e in export_sql._managers_first(employees)]

    assert ordered == ["emp-003", "emp-001", "emp-002"]


def test_export_restores_into_empty_database(seeded_session_factory):
    with seeded_session_factory() as session:
        backup_text = json.dumps(export_sql.export_tables(session))

    # A fresh database, loaded the way scripts/import_documents.py loads a
    # backup directory.
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    restored_db = sessionmaker(bind=engine)
    rows = json.loads(backup_text)
    with restored_db.begin() as session:
        for e in rows["employees.json"]:
            session.merge(EmployeeRecord(**e))
        for c in rows["customers.json"]:
            if c["renewal_date"]:
                c["renewal_date"] = date.fromisoformat(c["renewal_date"])
            session.merge(CustomerRecord(**c))
        for d in rows["documents.json"]:
            d["created_at"] = datetime.fromisoformat(d["created_at"])
            d["updated_at"] = datetime.fromisoformat(d["updated_at"])
            session.merge(DocumentMetadataRecord(**d))

    with restored_db() as session:
        restored = export_sql.export_tables(session)
    assert restored == json.loads(backup_text)


def test_restore_principal_statements_are_idempotent_and_quoted():
    statements = restore_db_principals.restore_statements(
        [{"name": "mcp-app-demo-func", "type": "EXTERNAL_USER", "roles": ["db_datareader"]}]
    )

    assert statements == [
        (
            "IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = :name) "
            "CREATE USER [mcp-app-demo-func] FROM EXTERNAL PROVIDER",
            {"name": "mcp-app-demo-func"},
        ),
        (
            "IF IS_ROLEMEMBER(:role, :name) = 0 ALTER ROLE [db_datareader] "
            "ADD MEMBER [mcp-app-demo-func]",
            {"role": "db_datareader", "name": "mcp-app-demo-func"},
        ),
    ]


def test_restore_quotes_closing_brackets_in_identifiers():
    [(create_user, _)] = restore_db_principals.restore_statements(
        [{"name": "odd]name", "type": "EXTERNAL_USER", "roles": []}]
    )

    assert "CREATE USER [odd]]name]" in create_user
