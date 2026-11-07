
import hashlib
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from chunker import chunk_knowledge_base


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = PROJECT_ROOT / "data" / "embeddings_cache.json"
EXPECTED_DIMENSIONS = 1536


def get_client():
    load_dotenv(PROJECT_ROOT / ".env", override=False)

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing")

    return OpenAI(
        api_key=api_key,
        base_url=os.getenv(
            "OPENROUTER_BASE_URL",
            "https://openrouter.ai/api/v1",
        ),
        timeout=30.0,
        max_retries=2,
    )


def chunk_fingerprint(chunk, model):
    payload = {
        "model": model,
        "text": chunk["text"],
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def load_cache():
    if not CACHE_PATH.exists():
        return {}

    with CACHE_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Embedding cache must be a dictionary")

    return data


def save_cache(cache):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = CACHE_PATH.with_suffix(".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(cache, file, ensure_ascii=False)

    temporary_path.replace(CACHE_PATH)


def validate_vector(vector):
    if len(vector) != EXPECTED_DIMENSIONS:
        raise ValueError(
            f"Invalid embedding dimensions: {len(vector)}"
        )

    if not all(isinstance(value, (int, float)) for value in vector):
        raise ValueError("Embedding contains invalid values")


def embed_chunks(chunks):
    load_dotenv(PROJECT_ROOT / ".env", override=False)

    model = os.getenv(
        "EMBEDDING_MODEL",
        "openai/text-embedding-3-small",
    )

    cache = load_cache()
    results = []
    cache_hits = 0
    client = None

    for index, chunk in enumerate(chunks, start=1):
        fingerprint = chunk_fingerprint(chunk, model)

        if fingerprint in cache:
            vector = cache[fingerprint]
            validate_vector(vector)
            cache_hits += 1
            status = "CACHE"
        else:
            status = "NEW"
            if client is None:
                client = get_client()

            response = client.embeddings.create(
                model=model,
                input=chunk["text"],
            )

            vector = response.data[0].embedding
            validate_vector(vector)

            cache[fingerprint] = vector
            save_cache(cache)

        results.append({
            **chunk,
            "embedding": vector,
        })

    print(
        f"[{index}/{len(chunks)}] "
        f"{chunk['chunk_id']} {status}"
    )

    print(f"\nTotal chunks: {len(results)}")
    print(f"Cache hits: {cache_hits}")
    print(f"New embeddings: {len(results) - cache_hits}")

    return results


if __name__ == "__main__":
    chunks = chunk_knowledge_base()
    embed_chunks(chunks)
