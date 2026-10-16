from __future__ import annotations

from typing import Any, Callable

import requests
from requests import Response


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


def _send(
    send: Callable[..., Response],
    url: str,
    *,
    context: str,
    **kwargs: Any,
) -> Response:
    """Send a request and raise WorkdayAdaptiveApiError on network or HTTP failure."""
    try:
        response = send(url, **kwargs)
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
        requests.get, url, context=context, headers=headers, params=params, timeout=timeout
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
        requests.post, url, context=context, headers=headers, data=data, timeout=timeout
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
        requests.post, url, context=context, headers=headers, data=data, timeout=timeout
    )
    return _json(response, context)
