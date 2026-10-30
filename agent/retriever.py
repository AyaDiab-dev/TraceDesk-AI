
"""ResolveAI - Hybrid semantic and error-code-aware KB retrieval."""

import math
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

from chunker import chunk_knowledge_base
from embedder import (
    PROJECT_ROOT,
    chunk_fingerprint,
    load_cache,
    validate_vector,
)


ERROR_CODE_PATTERN = re.compile(
    r"\b(?:NX|NID|SWC|CRM)-\d{3,4}\b",
    re.IGNORECASE,
)

PRIORITY_TERMS = (
    "priority",
    "priorities",
    "p1",
    "p2",
    "p3",
    "p4",
    "escalation",
    "major incident",
)


def cosine_similarity(vector_a, vector_b):
    """Calculate cosine similarity between two embeddings."""
    if len(vector_a) != len(vector_b):
        raise ValueError("Embedding dimensions do not match.")

    dot_product = sum(
        a * b for a, b in zip(vector_a, vector_b)
    )

    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def load_search_index():
    """Load eligible KB chunks and their cached embeddings."""
    load_dotenv(PROJECT_ROOT / ".env", override=True)

    model = os.getenv(
        "EMBEDDING_MODEL",
        "openai/text-embedding-3-small",
    )

    cache = load_cache()
    index = []

    for chunk in chunk_knowledge_base():
        metadata = chunk.get("metadata", {})

        # Never retrieve draft or deprecated documents.
        if metadata.get("status") != "current":
            continue

        fingerprint = chunk_fingerprint(chunk, model)

        if fingerprint not in cache:
            raise RuntimeError(
                f"Missing cached embedding: {chunk['chunk_id']}. "
                "Run python agent/embedder.py first."
            )

        vector = cache[fingerprint]
        validate_vector(vector)

        index.append({
            **chunk,
            "embedding": vector,
        })

    return index


def extract_error_codes(text):
    """Extract supported error codes from text."""
    if not isinstance(text, str):
        return set()

    return {
        code.upper()
        for code in ERROR_CODE_PATTERN.findall(text)
    }


def get_metadata_error_codes(chunk):
    """Read error codes declared in chunk metadata."""
    metadata = chunk.get("metadata", {})
    codes = set()

    values = [
        chunk.get("error_code"),
        metadata.get("error_code"),
        metadata.get("error_codes"),
    ]

    for value in values:
        if isinstance(value, str):
            codes.update(extract_error_codes(value))

        elif isinstance(value, (list, tuple, set)):
            for item in value:
                codes.update(extract_error_codes(item))

    return codes


def exact_code_boost(query, chunk):
    """Boost chunks that explicitly match the requested error."""
    query_codes = extract_error_codes(query)

    if not query_codes:
        return 0.0

    metadata_codes = get_metadata_error_codes(chunk)
    text_codes = extract_error_codes(chunk.get("text", ""))

    if query_codes & metadata_codes:
        return 0.30

    if query_codes & text_codes:
        return 0.30

    return 0.0


def required_policy_chunks(query, index):
    """Retrieve authoritative priority policy when relevant."""
    normalized_query = query.lower()

    is_priority_question = any(
        term in normalized_query
        for term in PRIORITY_TERMS
    )

    if not is_priority_question:
        return []

    return [
        chunk
        for chunk in index
        if chunk["document_id"] == "KB-015"
        and chunk["metadata"].get("authoritative") is True
        and chunk["section"] == "2. Priorities"
    ]


def find_error_code_documents(query, index):
    """
    Identify authoritative documents directly associated
    with an error code.

    Prefer document-level metadata over incidental mentions
    in unrelated KB articles.
    """
    query_codes = extract_error_codes(query)

    if not query_codes:
        return set()

    matching_documents = set()

    # First pass: explicit document metadata.
    for chunk in index:
        metadata = chunk.get("metadata", {})

        if metadata.get("authoritative") is not True:
            continue

        declared_codes = get_metadata_error_codes(chunk)

        if query_codes & declared_codes:
            matching_documents.add(chunk["document_id"])

    if matching_documents:
        return matching_documents

    # Fallback: exact mentions within authoritative KB text.
    # Use the best matching chunk rather than expanding
    # every document that happens to mention the code.
    candidates = []

    for chunk in index:
        metadata = chunk.get("metadata", {})

        if metadata.get("authoritative") is not True:
            continue

        text_codes = extract_error_codes(
            chunk.get("text", "")
        )

        if query_codes & text_codes:
            candidates.append(chunk)

    if not candidates:
        return set()

    # Prefer a KB whose title/section is directly about
    # the requested code.
    def candidate_rank(chunk):
        section = chunk.get("section", "")
        text = chunk.get("text", "")
        codes = extract_error_codes(query)

        title_match = any(
            code in section.upper()
            for code in codes
        )

        return (
            int(title_match),
            int(bool(codes & get_metadata_error_codes(chunk))),
            -len(text),
        )

    best = max(candidates, key=candidate_rank)

    return {best["document_id"]}


def required_error_code_chunks(query, index):
    """
    Expand an exact error-code match to the complete
    eligible authoritative KB article.

    This allows the response model to see both the
    explanation and the documented resolution steps.
    """
    document_ids = find_error_code_documents(
        query,
        index,
    )

    if not document_ids:
        return []

    return [
        chunk
        for chunk in index
        if chunk["document_id"] in document_ids
        and chunk["metadata"].get("status") == "current"
        and chunk["metadata"].get("authoritative") is True
    ]


def retrieve(query, top_k=5):
    """
    Retrieve KB evidence using semantic similarity,
    exact error-code matching, and context expansion.
    """
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty.")

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    index = load_search_index()

    load_dotenv(PROJECT_ROOT / ".env", override=True)

    client = OpenAI(
        api_key=os.environ["OPENROUTER_API_KEY"].strip(),
        base_url=os.getenv(
            "OPENROUTER_BASE_URL",
            "https://openrouter.ai/api/v1",
        ),
    )

    response = client.embeddings.create(
        model=os.getenv(
            "EMBEDDING_MODEL",
            "openai/text-embedding-3-small",
        ),
        input=query,
    )

    query_vector = response.data[0].embedding
    validate_vector(query_vector)

    results = []

    for chunk in index:
        semantic_score = cosine_similarity(
            query_vector,
            chunk["embedding"],
        )

        boost = exact_code_boost(query, chunk)
        score = semantic_score + boost

        results.append({
            "chunk_id": chunk["chunk_id"],
            "document_id": chunk["document_id"],
            "section": chunk["section"],
            "source": chunk["source"],
            "metadata": chunk["metadata"],
            "text": chunk["text"],
            "score": score,
            "semantic_score": semantic_score,
            "exact_code_boost": boost,
        })

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    selected = results[:top_k]
    selected_ids = {
        item["chunk_id"]
        for item in selected
    }

    # Map scored chunks by ID for efficient lookup.
    scored_by_id = {
        item["chunk_id"]: item
        for item in results
    }

    # Add mandatory priority-policy evidence.
    for chunk in required_policy_chunks(query, index):
        chunk_id = chunk["chunk_id"]

        if chunk_id in selected_ids:
            continue

        matching_result = scored_by_id.get(chunk_id)

        if matching_result is None:
            continue

        if len(selected) >= top_k:
            removed = selected.pop()
            selected_ids.discard(removed["chunk_id"])

        selected.append(matching_result)
        selected_ids.add(chunk_id)

    # Expand directly matched error-code documents.
    error_chunks = required_error_code_chunks(
        query,
        index,
    )

    for chunk in error_chunks:
        chunk_id = chunk["chunk_id"]

        if chunk_id in selected_ids:
            continue

        matching_result = scored_by_id.get(chunk_id)

        if matching_result is None:
            continue

        selected.append(matching_result)
        selected_ids.add(chunk_id)

    return selected


if __name__ == "__main__":
    question = (
        "NakhlaID says NID-423 when I try to sign in. "
        "What should I do?"
    )

    print("Question:", question)
    print()

    results = retrieve(question)

    for rank, result in enumerate(results, start=1):
        print(
            f"{rank}. {result['document_id']} "
            f"| {result['section']} "
            f"| score={result['score']:.4f}"
        )
        print("Chunk:", result["chunk_id"])
        print(
            "Text:",
            result["text"][:200].replace("\n", " "),
        )
        print()

    has_unlock_instructions = any(
        item["document_id"] == "KB-006"
        and "30 minutes" in item["text"].lower()
        and "/unlock" in item["text"].lower()
        for item in results
    )

    print(
        "KB-006 unlock instructions retrieved:",
        has_unlock_instructions,
    )
