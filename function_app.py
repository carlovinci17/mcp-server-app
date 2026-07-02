import azure.functions as func

from src.core.logging import configure_logging
from src.tools import chat, customers, documents, employees, health, meetings, policies, search

configure_logging()

app = func.FunctionApp()

app.register_functions(documents.bp)
app.register_functions(policies.bp)
app.register_functions(meetings.bp)
app.register_functions(employees.bp)
app.register_functions(customers.bp)
app.register_functions(health.bp)
app.register_functions(search.bp)
app.register_functions(chat.bp)
