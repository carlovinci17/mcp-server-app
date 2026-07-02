from pydantic import BaseModel


class Employee(BaseModel):
    id: str
    name: str
    email: str
    title: str
    department: str
    location: str
    manager_id: str | None = None


class Department(BaseModel):
    name: str
    head_id: str | None = None
    employee_count: int
