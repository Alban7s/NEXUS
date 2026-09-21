import httpx


async def applications(base_url: str, token: str | None):
    if not base_url:
        return None

    url = base_url.rstrip("/") + "/api/v1/applications"
    headers = {"Accept": "application/json"}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
