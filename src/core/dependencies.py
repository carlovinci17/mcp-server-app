from functools import lru_cache

from src.azure.blob_client import BlobClient
from src.azure.search_client import get_search_client
from src.services.customer_service import CustomerService
from src.services.document_service import DocumentService
from src.services.employee_service import EmployeeService
from src.services.search_service import SearchService


@lru_cache
def get_document_service() -> DocumentService:
    return DocumentService(blob_client=BlobClient())


@lru_cache
def get_employee_service() -> EmployeeService:
    return EmployeeService()


@lru_cache
def get_customer_service() -> CustomerService:
    return CustomerService()


@lru_cache
def get_search_service() -> SearchService:
    return SearchService(search_client=get_search_client())
