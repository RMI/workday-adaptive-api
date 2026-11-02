from __future__ import annotations

from typing import Any

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CONNECT_TIMEOUT = 10
"""Seconds to wait for a connection. The ``timeout`` arguments set the read timeout."""

CONNECT_RETRIES = 4
"""Retries after a failed connect, so a request has up to 5 tries."""

BACKOFF_FACTOR = 1
"""urllib3 waits 0, 2, 4, then 8 seconds before the retries."""


class WorkdayAdaptiveApiError(Exception):
    """Raised when a Workday or Adaptive API request fails."""


class AdaptiveApiWarning(UserWarning):
    """Issued when Adaptive accepts a request but reports skipped or invalid input."""


def _raise_for_status(response: Response, context: str) -> None:
    if response.ok:
        return
    raise WorkdayAdaptiveApiError(
        f"{context} failed: {response.status_code} {response.text}"
    )


def _session() -> requests.Session:
    """
    Return a session that retries only failed connects.

    A failed connect means that the server did not get the request, so a retry
    is safe for POST too. Read errors and HTTP status codes do not retry, so an
    export or a token exchange never runs twice.
    """
    retry = Retry(
        total=None,
        connect=CONNECT_RETRIES,
        read=0,
        status=0,
        other=0,
        redirect=None,
        backoff_factor=BACKOFF_FACTOR,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _send(
    method: str,
    url: str,
    *,
    context: str,
    timeout: float,
    **kwargs: Any,
) -> Response:
    """Send a request and raise WorkdayAdaptiveApiError on network or HTTP failure."""
    try:
        with _session() as session:
            response = session.request(
                method=method,
                url=url,
                timeout=(CONNECT_TIMEOUT, timeout),
                **kwargs,
            )
    except requests.RequestException as exc:
        raise WorkdayAdaptiveApiError(
            f"{context} failed: {type(exc).__name__}: {exc}"
        ) from exc
    _raise_for_status(response, context)
    return response


def _json(response: Response, context: str) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        content_type = response.headers.get("Content-Type", "unknown")
        raise WorkdayAdaptiveApiError(
            f"{context} returned a response that is not JSON "
            f"(Content-Type: {content_type}): {response.text[:200]}"
        ) from exc


def get_json(
    url: str,
    *,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
    timeout: int = 300,
    context: str,
) -> Any:
    response = _send(
        "GET", url, context=context, headers=headers, params=params, timeout=timeout
    )
    return _json(response, context)


def post_xml(
    url: str,
    *,
    headers: dict[str, str],
    data: str,
    timeout: int = 300,
    context: str,
) -> str:
    response = _send(
        "POST", url, context=context, headers=headers, data=data, timeout=timeout
    )
    return response.text


def post_form(
    url: str,
    *,
    headers: dict[str, str],
    data: dict[str, Any],
    timeout: int = 300,
    context: str,
) -> Any:
    response = _send(
        "POST", url, context=context, headers=headers, data=data, timeout=timeout
    )
    return _json(response, context)
