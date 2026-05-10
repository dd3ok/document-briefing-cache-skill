from document_briefing_cache.hashing import document_content_fingerprint, output_cache_key
from document_briefing_cache.models import DocumentInput


def test_fingerprint_is_stable_for_whitespace_changes():
    a = DocumentInput(title="A", text="Hello   world\n\n\nNumber: 10")
    b = DocumentInput(title="A", text="Hello world\n\nNumber: 10")
    assert document_content_fingerprint(a) == document_content_fingerprint(b)


def test_fingerprint_changes_when_content_changes():
    a = DocumentInput(title="A", text="Number: 10")
    b = DocumentInput(title="A", text="Number: 11")
    assert document_content_fingerprint(a) != document_content_fingerprint(b)


def test_output_cache_key_changes_by_mode():
    docs = [DocumentInput(document_id="x", text="hello")]
    key1 = output_cache_key(docs, "brief", "general", "ko-KR", "0.1", "t1", "rules")
    key2 = output_cache_key(docs, "digest", "general", "ko-KR", "0.1", "t1", "rules")
    assert key1 != key2
