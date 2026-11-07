
import re

from kb_loader import load_knowledge_base


HEADING_PATTERN = re.compile(r"(?m)^(#{1,6})\s+(.+?)\s*$")
ERROR_CODE_PATTERN = re.compile(r"^NX-\d{3}$")


def make_chunk(document: dict, section: str, text: str) -> dict:
    """Create a chunk while preserving source metadata."""
    return {
        "chunk_id": "",
        "document_id": document["id"],
        "section": section,
        "text": text.strip(),
        "source": document["source"],
        "metadata": document["metadata"],
    }


def split_error_code_table(chunk: dict) -> list[dict]:
    """Split VPN error-code table into one chunk per error code."""
    lines = chunk["text"].splitlines()
    error_chunks = []
    remaining_lines = []

    for line in lines:
        stripped = line.strip()

        if not stripped.startswith("|"):
            remaining_lines.append(line)
            continue

        cells = [cell.strip() for cell in stripped.strip("|").split("|")]

        if len(cells) != 3:
            remaining_lines.append(line)
            continue

        code = cells[0].replace("`", "").strip()

        if not ERROR_CODE_PATTERN.fullmatch(code):
            # Skip the table header and separator.
            if code.lower() == "code" or re.fullmatch(r":?-+:?", code):
                continue
            remaining_lines.append(line)
            continue

        meaning = cells[1]
        fix = cells[2]

        error_chunks.append({
            **chunk,
            "chunk_id": "",
            "section": f"Error codes / {code}",
            "text": (
                f"VPN error code: {code}\n"
                f"Meaning: {meaning}\n"
                f"Fix: {fix}"
            ),
            "error_code": code,
        })

    if not error_chunks:
        return [chunk]

    result = []

    remaining_text = "\n".join(remaining_lines).strip()

    if remaining_text:
        result.append({
            **chunk,
            "text": remaining_text,
        })

    result.extend(error_chunks)
    return result

def split_hardware_problems(chunk: dict) -> list[dict]:
    """Split independent hardware policies into separate evidence chunks."""
    lines = chunk["text"].splitlines()

    items = []
    current_item = []

    for line in lines:
        if line.lstrip().startswith("- **"):
            if current_item:
                items.append("\n".join(current_item).strip())
            current_item = [line]
        elif current_item:
            current_item.append(line)
        elif line.strip():
            # Preserve introductory text if present.
            current_item = [line]

    if current_item:
        items.append("\n".join(current_item).strip())

    if len(items) <= 1:
        return [chunk]

    return [
        {
            **chunk,
            "chunk_id": "",
            "text": item,
        }
        for item in items
    ]

def split_into_sections(document: dict) -> list[dict]:
    """Split a document by headings and selected structured tables."""
    content = document["content"]
    matches = list(HEADING_PATTERN.finditer(content))

    if not matches:
        chunk = make_chunk(document, "Full document", content)
        chunk["chunk_id"] = f"{document['id']}-001"
        return [chunk]

    chunks = []

    # Preserve text before the first heading.
    preamble = content[:matches[0].start()].strip()

    if preamble:
        chunks.append(make_chunk(document, "Preamble", preamble))

    for index, match in enumerate(matches):
        start = match.end()
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(content)
        )

        section_title = match.group(2).strip()
        section_text = content[start:end].strip()

        if not section_text:
            continue

        chunk = make_chunk(document, section_title, section_text)

        # Special handling for the structured VPN error-code table.
        if document["id"] == "KB-002" and section_title.lower() == "error codes":
            chunks.extend(split_error_code_table(chunk))

        elif (
            document["id"] == "KB-010"
            and section_title.lower() == "hardware problems"
        ):
            chunks.extend(split_hardware_problems(chunk))

        else:
            chunks.append(chunk)

    # Assign unique IDs after all splitting is complete.
    for index, chunk in enumerate(chunks, start=1):
        chunk["chunk_id"] = f"{document['id']}-{index:03d}"

    return chunks


def chunk_knowledge_base() -> list[dict]:
    """Create structured chunks for all KB documents."""
    documents = load_knowledge_base()
    all_chunks = []

    for document in documents:
        all_chunks.extend(split_into_sections(document))

    ids = [chunk["chunk_id"] for chunk in all_chunks]

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate chunk IDs detected")

    return all_chunks


if __name__ == "__main__":
    chunks = chunk_knowledge_base()

    print(f"Total chunks: {len(chunks)}")
    print("\nKB-002 chunks:")

    for chunk in chunks:
        if chunk["document_id"] == "KB-002":
            print(
                f"{chunk['chunk_id']} | "
                f"{chunk['section']} | "
                f"{len(chunk['text'])} characters"
            )

    codes = {
        chunk.get("error_code")
        for chunk in chunks
        if chunk["document_id"] == "KB-002"
        and chunk.get("error_code")
    }

    expected_codes = {
        "NX-112", "NX-403", "NX-503", "NX-781", "NX-905"
    }

    assert codes == expected_codes, (
        f"Error-code chunks mismatch: {codes}"
    )

    print("\nAll five VPN error-code chunks verified.")
