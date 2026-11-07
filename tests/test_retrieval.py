
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agent"))

from retriever import (
    exact_code_boost,
    load_search_index,
    retrieve,
)
from evidence_filter import filter_relevant_evidence


def test_search_index_excludes_inactive_documents():
    index = load_search_index()

    document_ids = {item["document_id"] for item in index}

    assert "KB-001" not in document_ids
    assert "KB-005" not in document_ids
    assert "KB-018" not in document_ids
    assert "KB-002" in document_ids

    assert all(
        item["metadata"]["status"] == "current"
        for item in index
    )


def test_search_index_preserves_sources():
    index = load_search_index()

    assert index
    assert all(item["chunk_id"] for item in index)
    assert all(item["source"] for item in index)
    assert all(len(item["embedding"]) == 1536 for item in index)


def test_exact_code_boost():
    chunk = {"error_code": "NX-781"}

    assert exact_code_boost("VPN error NX-781", chunk) == pytest.approx(0.30)
    assert exact_code_boost("VPN error NX-112", chunk) == 0.0
    assert exact_code_boost("VPN is not working", chunk) == 0.0


def test_empty_query_rejected():
    with pytest.raises(ValueError, match="cannot be empty"):
        retrieve("   ")


def test_invalid_top_k_rejected():
    with pytest.raises(ValueError, match="at least 1"):
        retrieve("VPN issue", top_k=0)


@pytest.mark.integration
def test_vpn_exact_code_retrieval():
    results = retrieve(
        "My VPN shows NX-781. How do I fix it?",
        top_k=5,
    )

    assert results
    assert results[0]["document_id"] == "KB-002"
    assert "NX-781" in results[0]["section"]
    assert results[0]["exact_code_boost"] == pytest.approx(0.30)

    assert all(
        result["metadata"]["status"] == "current"
        for result in results
    )


@pytest.mark.integration
def test_authoritative_priority_policy_is_included():
    query = "Four employees have the same IT problem. Is this P1 or P2?"

    results = retrieve(query, top_k=3)

    assert len(results) == 3

    assert any(
        item["document_id"] == "KB-015"
        and item["section"] == "2. Priorities"
        and item["metadata"]["authoritative"] is True
        for item in results
    )

    assert len(
        {item["chunk_id"] for item in results}
    ) == len(results)


@pytest.mark.integration
def test_nx781_retrieval_excludes_unrelated_error_codes():
    query = (
        "NakhlaConnect shows NX-781. "
        "My VPN client version is 5.1. What should I do?"
    )

    results = retrieve(query, top_k=5)

    sections = {item["section"] for item in results}

    assert "Error codes / NX-781" in sections
    assert "Supported versions" in sections

    unrelated_sections = {
        "Error codes / NX-112",
        "Error codes / NX-403",
        "Error codes / NX-503",
        "Error codes / NX-905",
    }

    assert sections.isdisjoint(unrelated_sections)


@pytest.mark.integration
def test_battery_question_excludes_unrelated_procedures():
    query = (
        "My laptop battery drains very quickly. "
        "What should I do?"
    )

    # Stage 1: Retrieve candidate evidence.
    candidates = retrieve(query, top_k=5)

    assert candidates

    assert any(
        item["section"] == "Hardware problems"
        for item in candidates
    )

    # Stage 2: Filter evidence for relevance.
    evidence = filter_relevant_evidence(query, candidates)

    assert evidence, "No relevant evidence survived filtering"

    unrelated_sections = {
        "Compliance rules",
        "Nakhla-Corp does not connect",
        "Push prompt not received (`MFA-201`)",
        "Install from the catalogue",
    }

    # Unrelated procedures must not survive filtering.
    assert all(
        item["section"] not in unrelated_sections
        for item in evidence
    )

    # Final evidence must originate from retrieved candidates.
    candidate_ids = {
        item["chunk_id"]
        for item in candidates
    }

    assert all(
        item["chunk_id"] in candidate_ids
        for item in evidence
    )
