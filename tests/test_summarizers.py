from document_briefing_cache.evidence import validate_summary_evidence
from document_briefing_cache.hashing import document_content_fingerprint
from document_briefing_cache.models import DocumentInput
from document_briefing_cache.normalize import split_into_sections
from document_briefing_cache.summarizers import RuleBasedExtractiveSummarizer


def test_rule_based_summarizer_uses_short_source_text_as_summary_evidence():
    document = DocumentInput(document_id="short", title="Short title", text="OK")
    fingerprint = document_content_fingerprint(document)
    sections = split_into_sections(document.text)

    state = RuleBasedExtractiveSummarizer().summarize(document, sections, fingerprint)

    assert state.summary == "OK"
    assert state.summary_evidence
    assert state.summary_evidence[0].quote == "OK"


def test_rule_based_summarizer_short_section_fallback_evidence_stays_within_section():
    document = DocumentInput(document_id="short-sections", title="Short sections", text="A:\nOK\n\nB:\nNO")
    fingerprint = document_content_fingerprint(document)
    sections = split_into_sections(document.text)

    state = RuleBasedExtractiveSummarizer().summarize(document, sections, fingerprint)

    assert state.summary == "OK"
    assert state.summary_evidence
    assert state.summary_evidence[0].section_id == "s1"
    assert state.summary_evidence[0].quote == "OK"
    assert validate_summary_evidence(state, document.text, sections=sections) == []
