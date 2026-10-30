
from pathlib import Path
from datetime import date, datetime
import re

import pymupdf
import yaml


KB_DIR = Path(__file__).resolve().parent.parent / "dataset" / "knowledge_base"

SUPPORTED_EXTENSIONS = {".md", ".pdf"}
ALLOWED_STATUSES = {"current", "deprecated", "draft"}
DOCUMENT_ID_PATTERN = re.compile(r"^(KB|SP)-\d{3}$")

# Match a YAML block at the start of a document, allowing a PDF
# DOCUMENT CONTROL label before the metadata.
YAML_BLOCK_PATTERN = re.compile(
    r"(?m)^---[ \t]*\r?\n(.*?)^---[ \t]*$",
    flags=re.DOTALL,
)


def validate_metadata(metadata: dict, source: str) -> dict:
    """Validate fields needed for trustworthy document ingestion."""

    required_fields = {
        "id",
        "status",
        "authoritative",
        "version",
        "last_updated",
    }

    missing = required_fields - metadata.keys()

    if missing:
        raise ValueError(
            f"{source}: Missing metadata fields: {sorted(missing)}"
        )

    document_id = metadata["id"]

    if not isinstance(document_id, str) or not DOCUMENT_ID_PATTERN.fullmatch(document_id):
        raise ValueError(
            f"{source}: Invalid document ID: {document_id!r}"
        )

    status = metadata["status"]

    if not isinstance(status, str) or status not in ALLOWED_STATUSES:
        raise ValueError(
            f"{source}: Invalid document status: {status!r}"
        )

    if type(metadata["authoritative"]) is not bool:
        raise ValueError(
            f"{source}: 'authoritative' must be a boolean"
        )

    version = metadata["version"]

    if (
        isinstance(version, bool)
        or not isinstance(version, (str, int, float))
        or not str(version).strip()
    ):
        raise ValueError(
            f"{source}: Invalid document version: {version!r}"
        )

    updated = metadata["last_updated"]

    if isinstance(updated, datetime):
        updated = updated.date()

    if isinstance(updated, date):
        metadata["last_updated"] = updated.isoformat()

    elif isinstance(updated, str):
        try:
            metadata["last_updated"] = date.fromisoformat(updated).isoformat()
        except ValueError as error:
            raise ValueError(
                f"{source}: Invalid last_updated date: {updated!r}"
            ) from error

    else:
        raise ValueError(
            f"{source}: Invalid last_updated type: {type(updated).__name__}"
        )

    return metadata


def parse_document(text: str, source: str) -> dict:
    """Extract, validate and normalize document metadata and content."""

    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"{source}: Document text is empty")

    match = YAML_BLOCK_PATTERN.search(text)

    if not match:
        raise ValueError(f"{source}: Missing YAML metadata block")

    try:
        metadata = yaml.safe_load(match.group(1))
    except yaml.YAMLError as error:
        raise ValueError(
            f"{source}: Invalid YAML metadata"
        ) from error

    if not isinstance(metadata, dict):
        raise ValueError(
            f"{source}: YAML metadata must be a dictionary"
        )

    metadata = validate_metadata(metadata, source)

    content = text[match.end():].strip()

    if not content:
        raise ValueError(f"{source}: Empty document content")

    return {
        "id": metadata["id"],
        "metadata": metadata,
        "content": content,
        "source": source,
    }


def load_document(path: Path) -> dict:
    """Read a Markdown or PDF document with explicit error handling."""

    if not path.is_file():
        raise ValueError(f"Not a valid file: {path}")

    suffix = path.suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {path.name}")

    try:
        if suffix == ".md":
            text = path.read_text(encoding="utf-8-sig")

        else:
            with pymupdf.open(path) as pdf:
                if pdf.needs_pass:
                    raise ValueError(
                        f"{path.name}: Password-protected PDF"
                    )

                if pdf.page_count == 0:
                    raise ValueError(
                        f"{path.name}: PDF has no pages"
                    )

                text = "\n".join(
                    page.get_text(sort=True) for page in pdf
                )

                if not text.strip():
                    raise ValueError(
                        f"{path.name}: PDF has no extractable text"
                    )

    except (OSError, UnicodeError, pymupdf.FileDataError) as error:
        raise ValueError(
            f"Failed to read {path.name}: {error}"
        ) from error

    return parse_document(text, path.name)


def is_eligible(document: dict) -> bool:
    """Only current documents are eligible as operational sources."""
    return document["metadata"]["status"] == "current"


def load_knowledge_base() -> list[dict]:
    """Load and validate all supported knowledge-base documents."""

    if not KB_DIR.is_dir():
        raise FileNotFoundError(
            f"Knowledge-base directory not found: {KB_DIR}"
        )

    paths = sorted(
        path for path in KB_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not paths:
        raise ValueError(
            f"No supported knowledge-base documents found in {KB_DIR}"
        )

    documents = []
    seen_ids = {}

    for path in paths:
        document = load_document(path)
        document_id = document["id"]

        if document_id in seen_ids:
            raise ValueError(
                f"Duplicate document ID {document_id}: "
                f"{seen_ids[document_id]} and {path.name}"
            )

        seen_ids[document_id] = path.name
        documents.append(document)

    return documents


if __name__ == "__main__":
    documents = load_knowledge_base()

    markdown_count = sum(
        doc["source"].lower().endswith(".md")
        for doc in documents
    )
    pdf_count = sum(
        doc["source"].lower().endswith(".pdf")
        for doc in documents
    )

    print(f"Total documents loaded: {len(documents)}")
    print(f"Markdown documents: {markdown_count}")
    print(f"PDF documents: {pdf_count}")

    print("\nDocument summary:")

    for document in documents:
        metadata = document["metadata"]

        print(
            f"{document['id']}: "
            f"status={metadata['status']}, "
            f"authoritative={metadata['authoritative']}, "
            f"eligible={is_eligible(document)}"
        )
