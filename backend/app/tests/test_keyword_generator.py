from app.services.enrichment.keyword_generator import generate_keywords
from app.services.enrichment.search_summary import generate_search_summary
from app.tests.fakes import FakeLLMProvider


def test_generate_keywords_only_source_supported():
    provider = FakeLLMProvider()
    text = "This project used GIS and ERP technology for NABARD under the PACS scheme."
    keywords = generate_keywords(provider, text)
    kw_names = {k["keyword"] for k in keywords}
    assert "GIS" in kw_names
    assert "ERP" in kw_names
    assert "PACS" in kw_names
    assert all(k["source_supported"] for k in keywords)


def test_generate_keywords_drops_unsupported_and_generic():
    provider = FakeLLMProvider()
    text = "Just a general consulting engagement."
    keywords = generate_keywords(provider, text)
    assert all(k["keyword"].lower() not in {"project", "company", "client", "india", "work"} for k in keywords)


def test_generate_search_summary():
    provider = FakeLLMProvider()
    summary = generate_search_summary(provider, "Government project involving ERP implementation for NABARD.")
    assert summary
    assert "government" in summary.lower()
