from document_briefing_cache.models import ContentFormat, DocumentInput
from document_briefing_cache.normalize import (
    normalize_payload,
    split_documents_into_incident_records,
    split_documents_into_section_documents,
    split_into_sections,
)


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


def test_split_documents_into_section_documents_preserves_parent_metadata():
    raw = {"source": "system", "content": "# One\nAction: owner should update runbook.\n\n# Two\nRisk: rollout may slip."}
    docs = [
        DocumentInput(
            source="ops.md",
            content_format=ContentFormat.markdown,
            text=raw["content"],
            raw=raw,
        )
    ]

    split_docs = split_documents_into_section_documents(docs)

    assert len(split_docs) == 2
    assert split_docs[0].document_id == "ops.md#section-1"
    assert split_docs[0].title == "One"
    assert split_docs[0].source == "ops.md"
    assert split_docs[0].metadata["parent_document_id"] == "ops.md"
    assert split_docs[0].metadata["section_id"] == "section-1"
    assert "update runbook" in split_docs[0].text
    assert split_docs[0].raw == raw
    assert split_docs[1].document_id == "ops.md#section-2"
    assert split_docs[1].title == "Two"
    assert split_docs[1].raw == raw


def test_split_documents_into_incident_records_uses_stable_ids():
    docs = [
        DocumentInput(
            document_id="feed-1",
            title="Incident Feed",
            content_format=ContentFormat.markdown,
            text=(
                "Incident ID: INC-1\n"
                "Status: open. Risk: checkout errors may continue.\n\n"
                "Incident Update: 2026-07-03 15:30 KST\n"
                "Action: SRE should confirm error rate by 16:00 KST.\n\n"
                "Incident Update: 2026-07-03 16:00 KST\n"
                "Decision: keep monitoring for 30 minutes."
            ),
            raw={"feed": "incident"},
        )
    ]

    split_docs = split_documents_into_incident_records(docs)

    assert [doc.document_id for doc in split_docs] == [
        "INC-1/root",
        "INC-1/update-2026-07-03-15-30-kst",
        "INC-1/update-2026-07-03-16-00-kst",
    ]
    assert split_docs[0].metadata["record_type"] == "incident_root"
    assert split_docs[1].metadata["record_type"] == "incident_update"
    assert split_docs[1].metadata["parent_document_id"] == "INC-1"
    assert split_docs[1].raw == {"feed": "incident"}
    assert "15:30 KST" in split_docs[1].text
    assert "16:00 KST" in split_docs[2].text


def test_split_documents_into_incident_records_disambiguates_duplicate_update_labels():
    docs = [
        DocumentInput(
            document_id="feed-1",
            title="Incident Feed",
            content_format=ContentFormat.markdown,
            text=(
                "Incident ID: INC-1\n\n"
                "Incident Update: follow-up\n"
                "Action: SRE should check logs.\n\n"
                "Incident Update: follow-up\n"
                "Action: support should notify affected users."
            ),
        )
    ]

    split_docs = split_documents_into_incident_records(docs)

    assert split_docs[0].document_id == "INC-1/update-follow-up"
    assert split_docs[1].document_id.startswith("INC-1/update-follow-up-")
    assert split_docs[0].document_id != split_docs[1].document_id


def test_split_documents_into_incident_records_requires_stable_incident_id():
    document = DocumentInput(
        document_id="generic-log",
        title="Generic update log",
        content_format=ContentFormat.markdown,
        text=(
            "Incident Update: 2026-07-03 15:30 KST\n"
            "Action: support should follow up, but no stable incident id is present."
        ),
    )

    assert split_documents_into_incident_records([document]) == [document]


def test_split_documents_into_incident_records_uses_timestamp_prefix_for_one_line_updates():
    docs = [
        DocumentInput(
            document_id="feed-1",
            title="Incident Feed",
            content_format=ContentFormat.markdown,
            text=(
                "Incident ID: INC-1\n"
                "Incident Update: 2026-07-03 15:30 KST. Status: mitigated, not resolved.\n\n"
                "Incident Update: 2026-07-03 16:00 KST. Status: resolved."
            ),
        )
    ]

    split_docs = split_documents_into_incident_records(docs)

    assert [doc.document_id for doc in split_docs] == [
        "INC-1/update-2026-07-03-15-30-kst",
        "INC-1/update-2026-07-03-16-00-kst",
    ]
    assert split_docs[0].metadata["record_label"] == "2026-07-03 15:30 KST"
    assert "Status: mitigated, not resolved" in split_docs[0].text


def test_split_documents_into_incident_records_uses_nearest_incident_id_per_update():
    docs = [
        DocumentInput(
            document_id="feed-1",
            title="Multi incident feed",
            content_format=ContentFormat.markdown,
            text=(
                "Incident ID: INC-1\n"
                "Status: open.\n"
                "Incident Update: 2026-07-03 15:30 KST\n"
                "Action: owner should check the first incident.\n\n"
                "Incident ID: INC-2\n"
                "Status: open.\n"
                "Incident Update: 2026-07-03 16:00 KST\n"
                "Action: owner should check the second incident."
            ),
        )
    ]

    split_docs = split_documents_into_incident_records(docs)

    assert [doc.document_id for doc in split_docs] == [
        "INC-1/root",
        "INC-1/update-2026-07-03-15-30-kst",
        "INC-2/root",
        "INC-2/update-2026-07-03-16-00-kst",
    ]
    assert split_docs[1].metadata["parent_document_id"] == "INC-1"
    assert split_docs[3].metadata["parent_document_id"] == "INC-2"
    assert split_docs[1].text.startswith("Incident ID: INC-1\n")
    assert split_docs[3].text.startswith("Incident ID: INC-2\n")
    assert "INC-2" not in split_docs[1].text
    assert "first incident" in split_docs[1].text
    assert "second incident" in split_docs[3].text


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
