from __future__ import annotations

from typing import Any

from ._http import get_json


def get_raas_data(
    workday_access_token: str,
    request_url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: int = 300,
) -> Any:
    """Fetch JSON data from a Workday RaaS endpoint."""
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
