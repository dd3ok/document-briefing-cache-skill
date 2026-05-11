from document_briefing_cache.hashing import document_content_fingerprint, document_summary_cache_key, output_cache_key
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


def test_cache_keys_change_by_redaction_policy():
    docs = [DocumentInput(document_id="x", text="Action: email alice@example.com.")]
    fingerprint = document_content_fingerprint(docs[0])

    raw_summary_key = document_summary_cache_key(docs[0], fingerprint, "rules", "0.2", redaction_policy_id="none")
    redacted_summary_key = document_summary_cache_key(docs[0], fingerprint, "rules", "0.2", redaction_policy_id="basic-contact-v1")
    raw_output_key = output_cache_key(docs, "brief", "general", "ko-KR", "0.2", "t1", "rules", redaction_policy_id="none")
    redacted_output_key = output_cache_key(docs, "brief", "general", "ko-KR", "0.2", "t1", "rules", redaction_policy_id="basic-contact-v1")

    assert raw_summary_key != redacted_summary_key
    assert raw_output_key != redacted_output_key
