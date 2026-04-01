"""Rate-limited async HTTP client — stateless, creates fresh client per call."""

import asyncio
import time
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)
from .logging import get_logger

logger = get_logger("http_client")

# Module-level rate tracking
_last_request: dict[str, float] = {}


def _is_retryable(exc: BaseException) -> bool:
    """Only retry on server errors (5xx) and connection issues, NOT 4xx."""
    if isinstance(exc, httpx.ConnectError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


async def _rate_limit(source: str, delay: float):
    """Enforce minimum delay between requests for a given source."""
    now = time.monotonic()
    last = _last_request.get(source, 0)
    wait = delay - (now - last)
    if wait > 0:
        await asyncio.sleep(wait)
    _last_request[source] = time.monotonic()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception(_is_retryable),
)
async def http_get(
    url: str,
    source: str = "default",
    rate_limit: float = 1.0,
    params: dict | None = None,
    headers: dict | None = None,
) -> httpx.Response:
    """Stateless GET — fresh client each call, retries only on 5xx/connection errors."""
    await _rate_limit(source, rate_limit)
    logger.debug("http_get", url=url, source=source)
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={
            "User-Agent": "APEX-Screener/1.0 (contact@apex-screener.dev)",
            "Accept": "application/json",
            **(headers or {}),
        },
    ) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response
