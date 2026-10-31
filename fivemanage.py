import httpx
import config


async def upload_png(png_bytes: bytes, filename: str) -> str | None:
    """Uploads a rendered PNG to Fivemanage API v3 and returns the hosted URL, or None if not configured."""
    api_key = (config.FIVEMANAGE_API_KEY or "").strip()
    if not api_key or api_key.startswith("your_"):
        return None
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.fivemanage.com/api/v3/file",
            headers={"Authorization": api_key},
            files={"file": (filename, png_bytes, "image/png")},
            data={"filename": filename},
        )
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("url") or (payload.get("data") or {}).get("url")
