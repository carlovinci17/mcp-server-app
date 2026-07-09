import json

from src.tools import search


def _unreachable_search_service():
    raise AssertionError("get_search_service() should not be called for an invalid doc_type")


def test_keyword_search_reports_invalid_doc_type_as_json_error(monkeypatch):
    monkeypatch.setattr(search, "get_search_service", _unreachable_search_service)

    result = search._keyword_search("onboarding", doc_type="not-a-real-type")

    payload = json.loads(result)
    assert "not-a-real-type" in payload["error"]


def test_semantic_search_reports_invalid_doc_type_as_json_error(monkeypatch):
    monkeypatch.setattr(search, "get_search_service", _unreachable_search_service)

    result = search._semantic_search("onboarding", doc_type="not-a-real-type")

    payload = json.loads(result)
    assert "not-a-real-type" in payload["error"]
