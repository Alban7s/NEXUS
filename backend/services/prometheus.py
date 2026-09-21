import httpx
from typing import Any, Optional


async def prometheus_query(base_url: str, query: str) -> Optional[dict[str, Any]]:
    if not base_url:
        return None

    url = base_url.rstrip("/") + "/api/v1/query"

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(url, params={"query": query})
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") != "success":
                return None
            return payload
    except (httpx.HTTPError, ValueError):
        return None


def first_value(payload: Optional[dict[str, Any]]) -> Optional[float]:
    if not payload:
        return None

    result = payload.get("data", {}).get("result", [])
    if not result:
        return None

    value = result[0].get("value")
    if not value or len(value) < 2:
        return None

    try:
        return float(value[1])
    except (TypeError, ValueError):
        return None
