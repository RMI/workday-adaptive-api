from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlsplit, urlunsplit

import pandas as pd
import requests

from ._http import WorkdayAdaptiveApiError, get_json


def _json_request_url(
    request_url: str, params: dict[str, Any] | None
) -> tuple[str, dict[str, Any] | None]:
    """
    Return the RaaS URL and params to send, with the request asking for JSON.

    Workday ignores the ``Accept`` header and uses the ``format`` query
    parameter. With no ``format``, it returns XML.

    ``params`` are encoded once, by requests, into the returned URL. The check
    reads that URL, so it sees the query that Workday receives. Encoding again
    would consume iterator values a second time and drop them.
    """
    try:
        sent_url = requests.Request("GET", request_url, params=params).prepare().url
    except requests.RequestException:
        # An invalid URL fails in the request itself, with WorkdayAdaptiveApiError.
        return request_url, params
    parts = urlsplit(sent_url)
    formats = parse_qs(parts.query, keep_blank_values=True).get("format", [])
    other = [value for value in formats if value.lower() != "json"]
    if other:
        raise ValueError(
            f"get_raas_data returns JSON, but the request asks for format={other[0]}. "
            "Use format=json."
        )
    if not formats:
        query = f"{parts.query}&format=json" if parts.query else "format=json"
        sent_url = urlunsplit(parts._replace(query=query))
    return sent_url, None


def get_raas_data(
    workday_access_token: str,
    request_url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: int = 300,
) -> Any:
    """
    Fetch JSON data from a Workday RaaS endpoint.

    Adds ``format=json`` when the URL and ``params`` have no ``format``.

    Raises
    ------
    ValueError
        Raised when the URL or ``params`` ask for a format other than JSON.
    WorkdayAdaptiveApiError
        Raised when the request fails or the response is not JSON.
    """
    request_url, params = _json_request_url(request_url, params)
    return get_json(
        request_url,
        headers={
            "Authorization": f"Bearer {workday_access_token}",
            "Accept": "application/json",
        },
        params=params,
        timeout=timeout,
        context="Workday RaaS request",
    )


def get_raas_dataframe(
    workday_access_token: str,
    request_url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: int = 300,
) -> pd.DataFrame:
    """
    Fetch a Workday RaaS report as a DataFrame with one row per report entry.

    Workday sends each value as a string and leaves out a field that has no
    value, so the DataFrame holds strings and NaN for the missing fields.
    A report with no entries returns an empty DataFrame.

    Raises
    ------
    ValueError
        Raised when the URL or ``params`` ask for a format other than JSON.
    WorkdayAdaptiveApiError
        Raised when the request fails, the response is not JSON, or the
        response has no ``Report_Entry`` list.
    """
    payload = get_raas_data(
        workday_access_token, request_url, params=params, timeout=timeout
    )
    entries = payload.get("Report_Entry") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        if isinstance(payload, dict) and "Report_Entry" in payload:
            found = f"Report_Entry of type {type(entries).__name__}"
        elif isinstance(payload, dict):
            found = f"keys {list(payload)}"
        else:
            found = type(payload).__name__
        raise WorkdayAdaptiveApiError(
            f"Workday RaaS response has no Report_Entry list. Found: {found}"
        )
    return pd.DataFrame(entries)
