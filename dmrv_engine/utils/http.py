"""
Shared HTTP client with exponential backoff retry logic.
Used by all external API services to ensure consistent error handling.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError as ReqConnErr

logger = logging.getLogger(__name__)


class HttpError(Exception):
    """Raised when an HTTP request fails after all retries."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def retry_get(
    url: str,
    *,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: int = 30,
    retries: int = 3,
    backoff: float = 1.5,
    expected_json: bool = True,
) -> Any:
    """
    GET with exponential backoff.

    Args:
        url:            Target URL.
        params:         Query params.
        headers:        HTTP headers.
        timeout:        Per-request timeout in seconds.
        retries:        Number of retry attempts (total = retries + 1 requests).
        backoff:        Base backoff in seconds; delay = backoff * (2 ** attempt).
        expected_json:  If True, parse and return JSON; else return raw bytes.

    Raises:
        HttpError if all attempts fail.
    """
    last_err: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json() if expected_json else resp.content

        except (Timeout, ReqConnErr) as e:
            last_err = e
            wait = backoff * (2 ** attempt)
            logger.warning(
                "HTTP transient error (attempt %d/%d) for %s: %s — retry in %.1fs",
                attempt + 1, retries + 1, _redact_url(url), e, wait,
            )
            if attempt < retries:
                time.sleep(wait)

        except RequestException as e:
            # Non-transient error — no retry
            status = getattr(e.response, "status_code", None)
            raise HttpError(f"HTTP failed: {e}", status_code=status) from e

    raise HttpError(
        f"HTTP exhausted {retries + 1} attempts: {last_err}"
    ) from last_err


def retry_post(
    url: str,
    *,
    json_body: Optional[dict] = None,
    data: Optional[Any] = None,
    headers: Optional[dict] = None,
    timeout: int = 30,
    retries: int = 3,
    backoff: float = 1.5,
    expected_json: bool = True,
) -> Any:
    """POST with same retry semantics as `retry_get`."""
    last_err: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            resp = requests.post(
                url, json=json_body, data=data, headers=headers, timeout=timeout,
            )
            resp.raise_for_status()
            return resp.json() if expected_json else resp.content

        except (Timeout, ReqConnErr) as e:
            last_err = e
            wait = backoff * (2 ** attempt)
            logger.warning(
                "HTTP POST transient error (attempt %d/%d) for %s: %s — retry in %.1fs",
                attempt + 1, retries + 1, _redact_url(url), e, wait,
            )
            if attempt < retries:
                time.sleep(wait)

        except RequestException as e:
            status = getattr(e.response, "status_code", None)
            raise HttpError(f"HTTP POST failed: {e}", status_code=status) from e

    raise HttpError(
        f"HTTP POST exhausted {retries + 1} attempts: {last_err}"
    ) from last_err


def _redact_url(url: str) -> str:
    """Strip query params from URL for logging (may contain tokens)."""
    return url.split("?")[0]
