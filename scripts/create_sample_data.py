"""Generate fictional Vortex Digital sample data into data/seed/.

Produces:
  data/seed/employees.json
  data/seed/customers.json
  data/seed/documents.json           (metadata only)
  data/seed/blobs/<container>/<id>.md (document content, one file per document)

This script is local-only: it does not touch Azure. Run
scripts/import_documents.py / scripts/seed_blob_storage.py afterwards to load
this data into a provisioned Azure SQL Database / Blob Storage account.
"""

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.models.document import DocumentType

random.seed(42)

COMPANY = "Vortex Digital"

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
BLOB_DIR = SEED_DIR / "blobs"

DEPARTMENTS = {
    "Engineering": [
        "Software Engineer",
        "Senior Software Engineer",
        "Engineering Manager",
        "Principal Engineer",
    ],
    "Sales": ["Account Executive", "Sales Development Rep", "Sales Manager", "VP of Sales"],
    "Marketing": ["Marketing Specialist", "Content Strategist", "Marketing Manager", "CMO"],
    "Finance": ["Financial Analyst", "Accountant", "Finance Manager", "CFO"],
    "Human Resources": ["HR Generalist", "Recruiter", "HR Manager", "VP of People"],
    "Customer Success": ["Customer Success Manager", "Support Engineer", "CS Team Lead"],
    "Product": ["Product Manager", "Senior Product Manager", "VP of Product"],
    "Legal": ["Corporate Counsel", "Compliance Analyst", "General Counsel"],
    "IT": ["IT Support Specialist", "Systems Administrator", "IT Manager"],
    "Operations": ["Operations Analyst", "Operations Manager", "COO"],
    "Design": ["UX Designer", "Product Designer", "Design Lead", "Head of Design"],
}

LOCATIONS = ["Melbourne, VIC", "Sydney, NSW", "Brisbane, QLD", "Perth, WA", "Remote - AU"]

FIRST_NAMES = [
    "Ava",
    "Liam",
    "Noah",
    "Emma",
    "Oliver",
    "Sophia",
    "Elijah",
    "Mia",
    "Lucas",
    "Isabella",
    "Mason",
    "Amelia",
    "Ethan",
    "Harper",
    "James",
    "Evelyn",
    "Benjamin",
    "Abigail",
    "Henry",
    "Ella",
    "Alexander",
    "Grace",
    "Sebastian",
    "Chloe",
    "Jack",
    "Victoria",
    "Owen",
    "Riley",
    "Daniel",
    "Zoey",
    "Matthew",
    "Lily",
    "Aiden",
    "Hannah",
    "Samuel",
    "Layla",
    "David",
    "Nora",
    "Joseph",
    "Addison",
    "Carter",
    "Aubrey",
    "Wyatt",
    "Savannah",
    "John",
    "Brooklyn",
    "Luke",
    "Bella",
    "Jayden",
    "Claire",
]
LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Hernandez",
    "Lopez",
    "Gonzalez",
    "Wilson",
    "Anderson",
    "Thomas",
    "Taylor",
    "Moore",
    "Jackson",
    "Martin",
    "Lee",
    "Perez",
    "Thompson",
    "White",
    "Harris",
    "Sanchez",
    "Clark",
    "Ramirez",
    "Lewis",
    "Robinson",
    "Walker",
    "Young",
    "Allen",
    "King",
    "Wright",
    "Scott",
    "Torres",
    "Nguyen",
    "Hill",
    "Flores",
]

INDUSTRIES = [
    "Financial Services",
    "Fintech",
    "Healthcare",
    "Retail",
    "Manufacturing",
    "Logistics",
    "Higher Education",
    "Media & Entertainment",
    "Energy",
    "Insurance",
    "Telecommunications",
]
REGIONS = ["Victoria", "New South Wales", "Queensland", "Western Australia", "South Australia"]
CUSTOMER_WORDS_A = [
    "North",
    "Summit",
    "Blue",
    "River",
    "Cascade",
    "Harbor",
    "Union",
    "Silver",
    "Cedar",
    "Vista",
]
CUSTOMER_WORDS_B = [
    "Peak",
    "Works",
    "Systems",
    "Holdings",
    "Partners",
    "Group",
    "Dynamics",
    "Ventures",
    "Labs",
    "Networks",
]

MEETING_TOPICS = [
    "Quarterly Business Review",
    "Sprint Planning",
    "Customer Escalation Review",
    "Product Roadmap Sync",
    "Budget Planning",
    "Hiring Committee",
    "Vendor Evaluation",
    "Incident Postmortem",
    "All-Hands Prep",
    "Cross-Team Sync",
]
POLICY_TOPICS = [
    "Remote Work Policy",
    "Expense Reimbursement Policy",
    "Code of Conduct",
    "Data Retention Policy",
    "Information Security Policy",
    "Paid Time Off Policy",
    "Travel Policy",
    "Anti-Harassment Policy",
    "Acceptable Use Policy",
    "Vendor Risk Policy",
    "Password and Access Policy",
    "Client Confidentiality Policy",
    "Equipment Policy",
    "Performance Review Policy",
    "Business Continuity Policy",
]
PROJECT_TOPICS = [
    "Platform Migration",
    "Customer Portal Redesign",
    "Data Warehouse Modernization",
    "Mobile App Launch",
    "API Gateway Rollout",
    "Billing System Upgrade",
    "Onboarding Automation",
    "Analytics Dashboard",
    "Search Relevance Improvements",
    "Support Chatbot Pilot",
]
DOCUMENT_TOPICS = [
    "Onboarding Guide",
    "Architecture Overview",
    "Runbook",
    "FAQ",
    "Style Guide",
    "Release Notes",
    "Post-Incident Report",
    "Competitive Analysis",
    "Customer Case Study",
    "Team Charter",
]


def _now_minus(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


def _current_quarter_bounds(now: datetime) -> tuple[datetime, datetime]:
    start_month = (now.month - 1) // 3 * 3 + 1
    start = now.replace(month=start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    end = (
        start.replace(year=start.year + 1, month=start_month + 3 - 12)
        if start_month + 3 > 12
        else start.replace(month=start_month + 3)
    )
    return start, end


def _paragraph(topic: str, department: str) -> str:
    return (
        f"This is fictional sample content generated for the {COMPANY} portfolio "
        f"project. It relates to {topic.lower()} within the {department} department. "
        "It exists to exercise document search, retrieval, and summarization tools "
        "end-to-end and does not describe a real company, person, or event."
    )


def generate_employees(count: int = 50) -> list[dict]:
    employees = []
    dept_names = list(DEPARTMENTS.keys())
    managers_by_dept: dict[str, str] = {}

    idx = 1
    # one manager-level employee per department first, so others can report to them
    for dept in dept_names:
        emp_id = f"emp-{idx:03d}"
        title = DEPARTMENTS[dept][-1]
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        employees.append(
            {
                "id": emp_id,
                "name": name,
                "email": f"{name.lower().replace(' ', '.')}@vortexdigital.example",
                "title": title,
                "department": dept,
                "location": random.choice(LOCATIONS),
                "manager_id": None,
            }
        )
        managers_by_dept[dept] = emp_id
        idx += 1

    while idx <= count:
        dept = random.choice(dept_names)
        title = random.choice(DEPARTMENTS[dept][:-1])
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        employees.append(
            {
                "id": f"emp-{idx:03d}",
                "name": name,
                "email": f"{name.lower().replace(' ', '.')}@vortexdigital.example",
                "title": title,
                "department": dept,
                "location": random.choice(LOCATIONS),
                "manager_id": managers_by_dept[dept],
            }
        )
        idx += 1

    return employees


def generate_customers(employees: list[dict], count: int = 25) -> list[dict]:
    account_owners = [
        e["id"] for e in employees if e["department"] in ("Sales", "Customer Success")
    ]
    now = datetime.now(UTC)
    customers = []
    for i in range(1, count + 1):
        name = f"{random.choice(CUSTOMER_WORDS_A)} {random.choice(CUSTOMER_WORDS_B)}"
        status = random.choices(["active", "prospect", "churned"], weights=[0.6, 0.3, 0.1])[0]
        # Only active contracts have an upcoming renewal date.
        renewal_date = (
            (now + timedelta(days=random.randint(-30, 400))).date().isoformat()
            if status == "active"
            else None
        )
        customers.append(
            {
                "id": f"cust-{i:03d}",
                "name": name,
                "industry": random.choice(INDUSTRIES),
                "region": random.choice(REGIONS),
                "status": status,
                "account_owner_id": random.choice(account_owners),
                "renewal_date": renewal_date,
            }
        )

    # Guarantee a few concrete answers for the "try asking" suggestion chips,
    # regardless of what the random draws above happened to produce:
    # - a handful of active customers renewing within the current quarter
    # - at least one churned Fintech customer
    quarter_start, quarter_end = _current_quarter_bounds(now)
    quarter_days = (quarter_end - quarter_start).days
    active_customers = [c for c in customers if c["status"] == "active"]
    for c in active_customers[:3]:
        c["renewal_date"] = (
            (quarter_start + timedelta(days=random.randint(0, quarter_days - 1))).date().isoformat()
        )

    customers[-1]["status"] = "churned"
    customers[-1]["industry"] = "Fintech"
    customers[-1]["renewal_date"] = None

    return customers


def _generate_docs_for_type(
    doc_type: DocumentType,
    topics: list[str],
    container: str,
    count: int,
    employees: list[dict],
    start_index: int,
) -> list[dict]:
    docs = []
    for i in range(count):
        topic = random.choice(topics)
        department = random.choice(list(DEPARTMENTS.keys()))
        owner = random.choice([e for e in employees if e["department"] == department])
        doc_id = f"{doc_type.value}-{start_index + i:03d}"
        title = f"{topic} - {department}" if doc_type != DocumentType.POLICY else topic
        created = _now_minus(random.randint(10, 720))
        docs.append(
            {
                "id": doc_id,
                "title": title,
                "doc_type": doc_type.value,
                "blob_container": container,
                "blob_path": f"{doc_id}.md",
                "content_type": "text/markdown",
                "department": department,
                "owner_id": owner["id"],
                "tags": [department.lower().replace(" ", "-"), doc_type.value],
                "related_document_ids": [],
                "created_at": created.isoformat(),
                "updated_at": created.isoformat(),
                "_content": f"# {title}\n\n{_paragraph(topic, department)}\n",
            }
        )
    return docs


COMPANY_DOCS = [
    (
        "About Vortex Digital",
        "# About Vortex Digital\n\n"
        "Vortex Digital is a fictional digital services company created for this "
        "portfolio project. Vortex Digital provides technology consulting, software "
        "engineering, and digital transformation services to mid-market and "
        "enterprise clients across Australia, spanning financial services, "
        "healthcare, retail, manufacturing, and logistics.\n\n"
        "Founded in 2014 and headquartered in Melbourne, Victoria, with additional "
        "offices in Sydney, Brisbane, and Perth, Vortex Digital employs "
        "approximately 50 people across Engineering, Product, Sales, Marketing, "
        "Customer Success, Finance, Human Resources, Legal, IT, and Operations.\n\n"
        "This content is entirely fictional and exists to demonstrate document "
        "search, retrieval, and summarization tools end-to-end.\n",
    ),
    (
        "Our Mission and Values",
        "# Our Mission and Values\n\n"
        "Vortex Digital's mission is to help organizations modernize their "
        "technology platforms without disrupting the people who depend on them.\n\n"
        "Our values:\n\n"
        "- **Customer obsession** - we measure success by the outcomes our clients "
        "achieve, not the hours we bill.\n"
        "- **Engineering craftsmanship** - we build systems that are simple to "
        "operate and easy to change.\n"
        "- **Radical transparency** - we share progress, risks, and mistakes early "
        "and often.\n"
        "- **Sustainable pace** - we plan for the long term rather than optimizing "
        "for short-term output.\n\n"
        "This is fictional sample content generated for the Vortex Digital "
        "portfolio project.\n",
    ),
    (
        "Company Milestones & History",
        "# Company Milestones & History\n\n"
        "- **2014** - Vortex Digital founded in Melbourne, VIC by a small team of "
        "engineers and consultants.\n"
        "- **2016** - Opened our first interstate office in Sydney, NSW to support "
        "growing Sales and Customer Success teams.\n"
        "- **2018** - Opened an office in Brisbane, QLD to support delivery "
        "capacity across Queensland.\n"
        "- **2020** - Crossed 25 active enterprise customers across financial "
        "services, healthcare, and retail.\n"
        "- **2022** - Opened a Perth, WA office to support delivery capacity "
        "across Western Australia.\n"
        "- **2024** - Began investing in AI-assisted knowledge management tooling "
        "internally - the inspiration for this very project.\n\n"
        "This is fictional sample content generated for the Vortex Digital "
        "portfolio project.\n",
    ),
]


def generate_company_documents(employees: list[dict]) -> list[dict]:
    owner = next(
        e for e in employees if e["department"] == "Operations" and e["manager_id"] is None
    )
    docs = []
    for i, (title, content) in enumerate(COMPANY_DOCS, start=1):
        doc_id = f"company-info-{i:03d}"
        created = _now_minus(random.randint(10, 720))
        docs.append(
            {
                "id": doc_id,
                "title": title,
                "doc_type": DocumentType.DOCUMENT.value,
                "blob_container": "documents",
                "blob_path": f"{doc_id}.md",
                "content_type": "text/markdown",
                "department": None,
                "owner_id": owner["id"],
                "tags": ["company", "about", DocumentType.DOCUMENT.value],
                "related_document_ids": [],
                "created_at": created.isoformat(),
                "updated_at": created.isoformat(),
                "_content": content,
            }
        )
    return docs


def _generate_latest_project_brief(employees: list[dict], doc_index: int) -> dict:
    # A deterministic, always-most-recent project_doc (all others are dated
    # 10-720 days back) so "summarize the latest project brief" always
    # resolves to a real, unambiguous document.
    department = "Product"
    owner = next(e for e in employees if e["department"] == department and e["manager_id"] is None)
    doc_id = f"{DocumentType.PROJECT_DOC.value}-{doc_index:03d}"
    title = "Project Brief - Customer Portal Redesign"
    created = _now_minus(2)
    content = (
        f"# {title}\n\n"
        "This project brief outlines the scope, goals, and timeline for the "
        "Customer Portal Redesign initiative, Vortex Digital's current top "
        "delivery priority.\n\n"
        "**Objective:** Modernize the customer-facing portal to reduce support "
        "ticket volume and improve self-service adoption.\n\n"
        "**Timeline:** Discovery complete; build phase targeted for completion "
        "by the end of this quarter.\n\n"
        "This is fictional sample content generated for the Vortex Digital "
        "portfolio project.\n"
    )
    return {
        "id": doc_id,
        "title": title,
        "doc_type": DocumentType.PROJECT_DOC.value,
        "blob_container": "project-docs",
        "blob_path": f"{doc_id}.md",
        "content_type": "text/markdown",
        "department": department,
        "owner_id": owner["id"],
        "tags": [department.lower(), DocumentType.PROJECT_DOC.value, "project-brief"],
        "related_document_ids": [],
        "created_at": created.isoformat(),
        "updated_at": created.isoformat(),
        "_content": content,
    }


def generate_documents(employees: list[dict]) -> list[dict]:
    docs = []
    docs += generate_company_documents(employees)
    docs += _generate_docs_for_type(
        DocumentType.DOCUMENT, DOCUMENT_TOPICS, "documents", 100, employees, 1
    )
    docs += _generate_docs_for_type(
        DocumentType.POLICY, POLICY_TOPICS, "policies", 15, employees, 1
    )
    docs += _generate_docs_for_type(
        DocumentType.MEETING_NOTE, MEETING_TOPICS, "meeting-notes", 30, employees, 1
    )
    docs += _generate_docs_for_type(
        DocumentType.PROJECT_DOC, PROJECT_TOPICS, "project-docs", 20, employees, 1
    )
    docs.append(_generate_latest_project_brief(employees, doc_index=21))

    # link a few documents within the same department as "related"
    by_department: dict[str, list[dict]] = {}
    for doc in docs:
        by_department.setdefault(doc["department"], []).append(doc)
    for dept_docs in by_department.values():
        for doc in dept_docs:
            candidates = [d["id"] for d in dept_docs if d["id"] != doc["id"]]
            doc["related_document_ids"] = random.sample(candidates, k=min(2, len(candidates)))

    return docs


def main() -> None:
    SEED_DIR.mkdir(parents=True, exist_ok=True)

    employees = generate_employees()
    customers = generate_customers(employees)
    documents = generate_documents(employees)

    (SEED_DIR / "employees.json").write_text(json.dumps(employees, indent=2))
    (SEED_DIR / "customers.json").write_text(json.dumps(customers, indent=2))

    documents_metadata = []
    for doc in documents:
        content = doc.pop("_content")
        documents_metadata.append(doc)
        blob_dir = BLOB_DIR / doc["blob_container"]
        blob_dir.mkdir(parents=True, exist_ok=True)
        (blob_dir / doc["blob_path"]).write_text(content)

    (SEED_DIR / "documents.json").write_text(json.dumps(documents_metadata, indent=2))

    print(
        f"Generated {len(employees)} employees, {len(customers)} customers, "
        f"{len(documents_metadata)} documents into {SEED_DIR}"
    )


if __name__ == "__main__":
    main()
