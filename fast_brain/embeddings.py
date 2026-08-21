import httpx

from .config import settings


async def embed(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{settings.embeddings_base_url.rstrip('/')}/embeddings",
            headers={"Authorization": f"Bearer {settings.embeddings_api_key}"},
            json={"model": settings.embeddings_model, "input": text},
        )
        response.raise_for_status()
        vector = response.json()["data"][0]["embedding"]

    if len(vector) != settings.embeddings_dimensions:
        raise ValueError(
            f"Embedding dimensions mismatch: got {len(vector)}, expected {settings.embeddings_dimensions}"
        )
    return vector
