from __future__ import annotations

from typing import Any

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


def get_json(
    url: str,
    *,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
    timeout: int = 300,
    context: str,
) -> Any:
    response = requests.get(url, headers=headers, params=params, timeout=timeout)
    _raise_for_status(response, context)
    return response.json()


def post_xml(
    url: str,
    *,
    headers: dict[str, str],
    data: str,
    timeout: int = 300,
    context: str,
) -> str:
    response = requests.post(url, headers=headers, data=data, timeout=timeout)
    _raise_for_status(response, context)
    return response.text


def post_form(
    url: str,
    *,
    headers: dict[str, str],
    data: dict[str, Any],
    timeout: int = 300,
    context: str,
) -> Any:
    response = requests.post(url, headers=headers, data=data, timeout=timeout)
    _raise_for_status(response, context)
    return response.json()
