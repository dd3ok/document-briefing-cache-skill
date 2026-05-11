from document_briefing_cache.evidence import extract_protected_values, validate_summary_evidence
from document_briefing_cache.models import (
    ActionItem,
    DocumentSection,
    DocumentSummaryState,
    EvidenceRef,
    Metric,
    Risk,
    SectionDigest,
)


def test_extract_protected_values_from_text_and_raw_paths():
    text = "INC-2026-042 reached 2.4% on 2026-05-07 with latency 183 ms."
    raw = {"ticket": {"id": "INC-2026-042", "amount": "12,500 KRW"}}

    values = extract_protected_values(text, raw=raw)
    by_value = {value.value: value for value in values}

    assert "INC-2026-042" in by_value
    assert "2.4%" in by_value
    assert "2026-05-07" in by_value
    assert "183 ms" in by_value
    assert by_value["12,500 KRW"].path == "$.ticket.amount"


def test_validate_summary_accepts_source_backed_values_and_evidence():
    source = (
        "Payment API incident INC-2026-042 happened on 2026-05-07. "
        "Payment API error rate reached 2.4%. "
        "Action: Backend should patch INC-2026-042 by 2026-05-07. Owner: Backend."
    )
    sections = [DocumentSection(section_id="s1", order=0, text=source)]
    summary = DocumentSummaryState(
        document_id="incident",
        content_fingerprint="abc",
        summary="Payment API incident INC-2026-042 had 2.4% errors.",
        metrics=[
            Metric(
                name="payment_error_rate",
                value="2.4",
                unit="%",
                evidence=[
                    EvidenceRef(
                        document_id="incident",
                        section_id="s1",
                        quote="Payment API error rate reached 2.4%.",
                    )
                ],
            )
        ],
        actions=[
            ActionItem(
                action="Backend should patch INC-2026-042 by 2026-05-07.",
                owner="Backend",
                due="2026-05-07",
                evidence=[
                    EvidenceRef(
                        document_id="incident",
                        section_id="s1",
                        quote="Action: Backend should patch INC-2026-042 by 2026-05-07.",
                    )
                ],
            )
        ],
    )

    assert validate_summary_evidence(summary, source, sections=sections) == []


def test_validate_summary_rejects_hallucinated_values_and_bad_quotes():
    source = "Payment API incident INC-2026-042 happened on 2026-05-07. Error rate reached 2.4%."
    sections = [DocumentSection(section_id="s1", order=0, text=source)]
    summary = DocumentSummaryState(
        document_id="incident",
        content_fingerprint="abc",
        summary="Payment API incident INC-2026-043 had 2.5% errors.",
        metrics=[
            Metric(
                name="payment_error_rate",
                value="2.5",
                unit="%",
                evidence=[EvidenceRef(document_id="incident", section_id="s1", quote="Error rate reached 2.5%.")],
            )
        ],
        actions=[
            ActionItem(
                action="Backend should patch INC-2026-043 by 2026-05-08.",
                owner="Backend",
                due="2026-05-08",
                evidence=[EvidenceRef(document_id="incident", section_id="missing", quote="Not in source.")],
            )
        ],
    )

    errors = validate_summary_evidence(summary, source, sections=sections)

    assert any("2.5%" in error for error in errors)
    assert any("INC-2026-043" in error for error in errors)
    assert any("2026-05-08" in error for error in errors)
    assert any("quote" in error for error in errors)
    assert any("section_id" in error for error in errors)


def test_validate_summary_normalizes_quote_whitespace():
    source = "Action: Backend should patch\nby 2026-05-07."
    sections = [DocumentSection(section_id="s1", order=0, text=source)]
    summary = DocumentSummaryState(
        document_id="incident",
        content_fingerprint="abc",
        actions=[
            ActionItem(
                action="Backend should patch by 2026-05-07.",
                due="2026-05-07",
                evidence=[
                    EvidenceRef(
                        document_id="incident",
                        section_id="s1",
                        quote="Action: Backend should patch by 2026-05-07.",
                    )
                ],
            )
        ],
    )

    assert validate_summary_evidence(summary, source, sections=sections) == []


def test_validate_summary_rejects_hallucinated_plain_numbers_and_names():
    source = "Kim Minji approved 42 seats for project ALPHA-123."
    summary = DocumentSummaryState(
        document_id="approval",
        content_fingerprint="abc",
        summary="Lee Sora approved 43 seats for project ALPHA-123.",
    )

    errors = validate_summary_evidence(summary, source)

    assert any("Lee Sora" in error for error in errors)
    assert any("43" in error for error in errors)


def test_validate_summary_rejects_missing_evidence_quote_for_claims():
    source = "Payment API error rate reached 2.4%."
    summary = DocumentSummaryState(
        document_id="incident",
        content_fingerprint="abc",
        metrics=[
            Metric(
                name="payment_error_rate",
                value="2.4",
                unit="%",
                evidence=[EvidenceRef(document_id="incident", section_id=None, quote=None)],
            )
        ],
    )

    errors = validate_summary_evidence(summary, source)

    assert any("evidence quote is required" in error for error in errors)


def test_validate_summary_checks_owner_risk_reason_questions_and_section_digest():
    source = "Kim Minji owns the rollout. Risk: delay by 2026-05-07. Section one says 12 services are affected."
    summary = DocumentSummaryState(
        document_id="incident",
        content_fingerprint="abc",
        actions=[ActionItem(action="Rollout follow-up.", owner="Lee Sora")],
        risks=[Risk(title="Delay risk", reason="May slip until 2026-05-08")],
        open_questions=["Can Park Joon approve 13 services?"],
        sections_digest=[SectionDigest(section_id="s1", summary="13 services affected.")],
    )

    errors = validate_summary_evidence(summary, source)

    assert any("Lee Sora" in error for error in errors)
    assert any("2026-05-08" in error for error in errors)
    assert any("Park Joon" in error for error in errors)
    assert any("13" in error for error in errors)
