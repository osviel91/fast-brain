import httpx

from .config import settings


def mock_embed(text: str) -> list[float]:
    data = text.encode()
    return [((data[i % len(data)] if data else i) % 101) / 100 for i in range(settings.embeddings_dimensions)]


async def embed(text: str) -> list[float]:
    if settings.embeddings_base_url == "mock://local":
        return mock_embed(text)

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
