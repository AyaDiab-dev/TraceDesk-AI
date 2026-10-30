
import sys
from pathlib import Path

import pytest

# Allow tests to import modules from the agent directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agent"))

import kb_loader


VALID_METADATA = """---
id: KB-099
status: current
authoritative: true
version: "1.0"
last_updated: 2026-10-20
---
"""


def make_document(content="Example troubleshooting instructions."):
    return VALID_METADATA + "\n" + content


def test_valid_document():
    document = kb_loader.parse_document(
        make_document(), "valid.md"
    )

    assert document["id"] == "KB-099"
    assert document["metadata"]["status"] == "current"
    assert document["content"] == "Example troubleshooting instructions."


def test_missing_yaml():
    with pytest.raises(ValueError, match="Missing YAML"):
        kb_loader.parse_document(
            "Document without metadata", "missing.md"
        )


def test_invalid_yaml():
    text = """---
id: [broken
---
Document content
"""

    with pytest.raises(ValueError, match="Invalid YAML"):
        kb_loader.parse_document(text, "invalid.md")


def test_missing_required_metadata():
    text = make_document().replace(
        "authoritative: true\n", ""
    )

    with pytest.raises(ValueError, match="Missing metadata fields"):
        kb_loader.parse_document(text, "missing_field.md")


def test_invalid_document_id():
    text = make_document().replace("KB-099", "INVALID-099")

    with pytest.raises(ValueError, match="Invalid document ID"):
        kb_loader.parse_document(text, "bad_id.md")


def test_invalid_status():
    text = make_document().replace("status: current", "status: archived")

    with pytest.raises(ValueError, match="Invalid document status"):
        kb_loader.parse_document(text, "bad_status.md")


def test_invalid_authoritative_type():
    text = make_document().replace(
        "authoritative: true",
        'authoritative: "true"'
    )

    with pytest.raises(ValueError, match="must be a boolean"):
        kb_loader.parse_document(text, "bad_boolean.md")


def test_invalid_date():
    text = make_document().replace(
        "2026-10-20", '"2026-13-45"'
    )

    with pytest.raises(ValueError, match="Invalid last_updated date"):
        kb_loader.parse_document(text, "bad_date.md")


def test_empty_content():
    with pytest.raises(ValueError, match="Empty document content"):
        kb_loader.parse_document(VALID_METADATA, "empty.md")


@pytest.mark.parametrize(
    "status, expected",
    [
        ("current", True),
        ("deprecated", False),
        ("draft", False),
    ],
)
def test_document_eligibility(status, expected):
    document = {
        "metadata": {"status": status}
    }

    assert kb_loader.is_eligible(document) is expected


def test_duplicate_document_ids(tmp_path, monkeypatch):
    kb_dir = tmp_path / "knowledge_base"
    kb_dir.mkdir()

    (kb_dir / "first.md").write_text(
        make_document(), encoding="utf-8"
    )
    (kb_dir / "second.md").write_text(
        make_document(), encoding="utf-8"
    )

    monkeypatch.setattr(kb_loader, "KB_DIR", kb_dir)

    with pytest.raises(ValueError, match="Duplicate document ID"):
        kb_loader.load_knowledge_base()


def test_real_knowledge_base():
    documents = kb_loader.load_knowledge_base()

    assert len(documents) == 20
    assert len({doc["id"] for doc in documents}) == 20

    assert sum(
        doc["source"].lower().endswith(".pdf")
        for doc in documents
    ) == 2

    assert all(doc["content"].strip() for doc in documents)

    assert kb_loader.is_eligible(
        next(doc for doc in documents if doc["id"] == "KB-017")
    )

    assert not kb_loader.is_eligible(
        next(doc for doc in documents if doc["id"] == "KB-018")
    )
