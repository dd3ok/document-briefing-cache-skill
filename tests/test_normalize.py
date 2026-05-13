from document_briefing_cache.models import ContentFormat, DocumentType
from document_briefing_cache.normalize import normalize_payload, split_into_sections


def test_json_documents_are_normalized():
    payload = {
        "documents": [
            {"id": "a", "title": "Meeting", "content": "Decision: ship it. Action: owner should deploy by 2026-05-07."},
            {"id": "b", "title": "Policy", "content": "Policy: receipts within 14 days."},
        ]
    }
    docs = normalize_payload(payload)
    assert len(docs) == 2
    assert docs[0].document_id == "a"
    assert docs[0].content_format == ContentFormat.json
    assert "ship it" in docs[0].text


def test_html_is_stripped_to_text():
    html = "<html><head><title>Doc</title><script>x()</script></head><body><h1>Hello</h1><p>World</p></body></html>"
    docs = normalize_payload(html)
    assert len(docs) == 1
    assert docs[0].title == "Doc"
    assert docs[0].content_format == ContentFormat.html
    assert "World" in docs[0].text
    assert "x()" not in docs[0].text


def test_xml_is_flattened():
    docs = normalize_payload("<root><title>API</title><metric unit='%'>2.4</metric></root>")
    assert len(docs) == 1
    assert docs[0].content_format == ContentFormat.xml
    assert "metric" in docs[0].text
    assert "2.4" in docs[0].text


def test_sections_split_on_markdown_headings():
    sections = split_into_sections("# One\nA paragraph.\n\n# Two\nAnother paragraph.")
    assert len(sections) == 2
    assert sections[0].heading == "One"
    assert sections[1].heading == "Two"


def test_url_fields_are_preserved_as_source_metadata_without_fetching():
    docs = normalize_payload(
        {"documents": [{"id": "u1", "title": "Remote Copy", "url": "https://example.com/report", "content": "Decision: keep local copy."}]}
    )

    assert docs[0].source == "https://example.com/report"
    assert docs[0].metadata["url"] == "https://example.com/report"
    assert "keep local copy" in docs[0].text


def test_unknown_payload_records_normalization_unknowns_metadata():
    docs = normalize_payload(object(), source="opaque")

    assert docs[0].source == "opaque"
    assert docs[0].metadata["normalization_unknowns"]
    assert "Unsupported payload type" in docs[0].metadata["normalization_unknowns"][0]
