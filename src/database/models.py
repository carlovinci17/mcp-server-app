from datetime import date, datetime

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    # Plain `str` columns default to VARCHAR(max) on the mssql dialect, which
    # SQL Server refuses to use as a primary/foreign key column. Give every
    # plain string column a bounded length instead.
    type_annotation_map = {
        str: String(255),
    }


class EmployeeRecord(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str]
    title: Mapped[str]
    department: Mapped[str]
    location: Mapped[str]
    manager_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"))


class CustomerRecord(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    industry: Mapped[str]
    region: Mapped[str]
    status: Mapped[str]
    account_owner_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"))
    renewal_date: Mapped[date | None]


class DocumentMetadataRecord(Base):
    __tablename__ = "document_metadata"

    id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    doc_type: Mapped[str]
    blob_container: Mapped[str]
    blob_path: Mapped[str]
    content_type: Mapped[str]
    department: Mapped[str | None]
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    related_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
