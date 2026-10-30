
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agent"))

from chunker import (
    chunk_knowledge_base,
    split_into_sections,
    split_error_code_table,
)


def make_document(content, document_id="KB-099"):
    """Create a synthetic document without modifying real KB files."""
    return {
        "id": document_id,
        "source": f"{document_id}.md",
        "metadata": {
            "id": document_id,
            "status": "current",
            "authoritative": True,
        },
        "content": content,
    }


def test_document_without_headings():
    document = make_document("Simple troubleshooting instructions.")

    chunks = split_into_sections(document)

    assert len(chunks) == 1
    assert chunks[0]["chunk_id"] == "KB-099-001"
    assert chunks[0]["section"] == "Full document"
    assert chunks[0]["text"] == "Simple troubleshooting instructions."


def test_document_with_multiple_sections():
    document = make_document(
        "# VPN Guide\n"
        "Introduction text.\n"
        "## Troubleshooting\n"
        "Restart the VPN client.\n"
        "## Escalation\n"
        "Contact IT support."
    )

    chunks = split_into_sections(document)

    assert len(chunks) == 3
    assert chunks[0]["section"] == "VPN Guide"
    assert chunks[1]["section"] == "Troubleshooting"
    assert chunks[2]["section"] == "Escalation"


def test_preamble_is_preserved():
    document = make_document(
        "Important introduction.\n\n"
        "# Instructions\n"
        "Follow these steps."
    )

    chunks = split_into_sections(document)

    assert len(chunks) == 2
    assert chunks[0]["section"] == "Preamble"
    assert "Important introduction." in chunks[0]["text"]


def test_chunk_ids_are_unique():
    chunks = chunk_knowledge_base()
    ids = [chunk["chunk_id"] for chunk in chunks]

    assert len(ids) == len(set(ids))


def test_chunk_metadata_is_preserved():
    document = make_document(
        "# VPN Instructions\n"
        "Restart the VPN client."
    )

    chunks = split_into_sections(document)

    assert chunks[0]["document_id"] == "KB-099"
    assert chunks[0]["source"] == "KB-099.md"
    assert chunks[0]["metadata"]["status"] == "current"
    assert chunks[0]["metadata"]["authoritative"] is True


def test_all_real_documents_have_chunks():
    chunks = chunk_knowledge_base()

    expected_ids = {
        f"KB-{number:03d}" for number in range(1, 19)
    } | {"SP-001", "SP-002"}

    actual_ids = {chunk["document_id"] for chunk in chunks}

    assert expected_ids == actual_ids
    assert all(chunk["text"].strip() for chunk in chunks)


def test_vpn_error_codes_are_separated():
    chunks = chunk_knowledge_base()

    vpn_chunks = [
        chunk for chunk in chunks
        if chunk["document_id"] == "KB-002"
    ]

    expected_codes = {
        "NX-112",
        "NX-403",
        "NX-503",
        "NX-781",
        "NX-905",
    }

    actual_codes = {
        chunk["error_code"]
        for chunk in vpn_chunks
        if "error_code" in chunk
    }

    assert actual_codes == expected_codes

    for code in expected_codes:
        matching = [
            chunk for chunk in vpn_chunks
            if chunk.get("error_code") == code
        ]
        assert len(matching) == 1


def test_nx781_fix_is_preserved():
    chunks = chunk_knowledge_base()

    nx781 = next(
        chunk for chunk in chunks
        if chunk.get("error_code") == "NX-781"
    )

    text = nx781["text"].lower()

    assert "nx-781" in text
    assert "5.4" in text


def test_error_code_table_preserves_other_text():
    document = make_document(
        "# Error codes\n"
        "Read the policy first."
    )

    chunk = {
        "chunk_id": "KB-099-001",
        "document_id": "KB-099",
        "section": "Error codes",
        "text": (
            "Read the policy first.\n"
            "| Code | Meaning | Fix |\n"
            "| --- | --- | --- |\n"
            "| NX-781 | Old client | Update the client |\n"
            "Escalate if the problem continues."
        ),
        "source": document["source"],
        "metadata": document["metadata"],
    }

    result = split_error_code_table(chunk)

    combined_text = "\n".join(item["text"] for item in result)

    assert "Read the policy first." in combined_text
    assert "Escalate if the problem continues." in combined_text
    assert "Update the client" in combined_text
    assert any(item.get("error_code") == "NX-781" for item in result)


@pytest.mark.parametrize(
    "document_id",
    ["KB-001", "KB-005", "KB-018"],
)
def test_non_current_documents_remain_loaded(document_id):
    """Loader/chunker retain documents; retrieval must filter them."""
    chunks = chunk_knowledge_base()

    assert any(
        chunk["document_id"] == document_id
        for chunk in chunks
    )
