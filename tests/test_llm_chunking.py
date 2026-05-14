from document_briefing_cache.llm import LLMConfig, chunk_sections_by_budget, estimate_tokens, merge_document_states
from document_briefing_cache.models import DocumentSection, DocumentSummaryState, EvidenceRef, KeyPoint


def test_estimate_tokens_is_deterministic_char_based_floor():
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 400) == 100


def test_chunk_sections_by_budget_preserves_order():
    sections = [
        DocumentSection(section_id="s1", order=0, text="a" * 80),
        DocumentSection(section_id="s2", order=1, text="b" * 80),
        DocumentSection(section_id="s3", order=2, text="c" * 80),
    ]

    chunks = chunk_sections_by_budget(sections, LLMConfig(max_input_tokens=25))

    assert [[section.section_id for section in chunk] for chunk in chunks] == [["s1"], ["s2"], ["s3"]]


def test_chunk_sections_by_budget_splits_oversized_sections_with_stable_section_id():
    section = DocumentSection(section_id="s1", order=0, text="a" * 13 + "b" * 13)

    chunks = chunk_sections_by_budget([section], LLMConfig(max_input_tokens=4))
    chunked_sections = [chunk_section for chunk in chunks for chunk_section in chunk]

    assert "".join(chunk_section.text for chunk_section in chunked_sections) == section.text
    assert {chunk_section.section_id for chunk_section in chunked_sections} == {"s1"}
    assert all(estimate_tokens(chunk_section.text) <= 4 for chunk_section in chunked_sections)
    assert all(sum(estimate_tokens(chunk_section.text) for chunk_section in chunk) <= 4 for chunk in chunks)


def test_merge_document_states_deduplicates_evidence_backed_items():
    evidence = [EvidenceRef(document_id="doc", section_id="s1", quote="Decision: proceed.")]
    left = DocumentSummaryState(
        document_id="doc",
        content_fingerprint="abc",
        summary="Decision: proceed.",
        summary_evidence=evidence,
        key_points=[KeyPoint(text="Decision: proceed.", evidence=evidence)],
        summarizer_id="openai-test",
    )
    right = DocumentSummaryState(
        document_id="doc",
        content_fingerprint="abc",
        summary="Decision: proceed.",
        summary_evidence=evidence,
        key_points=[KeyPoint(text="Decision: proceed.", evidence=evidence)],
        summarizer_id="openai-test",
    )

    merged = merge_document_states([left, right])

    assert merged.document_id == "doc"
    assert len(merged.key_points) == 1
    assert merged.content_fingerprint == "abc"
