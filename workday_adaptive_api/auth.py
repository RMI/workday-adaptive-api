from __future__ import annotations

import base64

from ._http import WorkdayAdaptiveApiError, get_json, post_form


def get_workday_access_token(
    token_url: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    *,
    timeout: int = 300,
) -> str:
    """
    Exchange a Workday OAuth refresh token for a new access token.

    Parameters
    ----------
    token_url:
        Full Workday OAuth token endpoint URL.
    client_id:
        OAuth client identifier issued by Workday.
    client_secret:
        OAuth client secret paired with ``client_id``.
    refresh_token:
        Refresh token used to request a new access token.
    timeout:
        Request timeout in seconds for the token call.

    Returns
    -------
    str
        The ``access_token`` value returned by Workday.

    Raises
    ------
    WorkdayAdaptiveApiError
        Raised when the HTTP request fails or the response does not contain
        an ``access_token`` field.
    """
    auth_string = f"{client_id}:{client_secret}"
    auth_b64 = base64.b64encode(auth_string.encode("ascii")).decode("ascii")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth_b64}",
    }
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    response_payload = post_form(
        token_url,
        headers=headers,
        data=payload,
        timeout=timeout,
        context="Workday access token request",
    )
    access_token = response_payload.get("access_token")
    if not access_token:
        raise WorkdayAdaptiveApiError("Workday access token response missing access_token")
    return access_token


def get_adaptive_access_token(
    workday_access_token: str,
    adaptive_access_token_url: str,
    *,
    timeout: int = 300,
) -> str:
    """
    Exchange a Workday access token for an Adaptive public API token.

    Parameters
    ----------
    workday_access_token:
        Bearer token previously obtained from Workday OAuth.
    adaptive_access_token_url:
        Endpoint URL that returns the Adaptive public API token payload.
    timeout:
        Request timeout in seconds for the token call.

    Returns
    -------
    str
        The Adaptive ``publicAPIToken`` value.

    Raises
    ------
    WorkdayAdaptiveApiError
        Raised when the HTTP request fails or the expected token payload is
        missing from the response.
    """
    payload = get_json(
        adaptive_access_token_url,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {workday_access_token}",
        },
        timeout=timeout,
        context="Adaptive access token request",
    )
    data = payload.get("data") or []
    if not data or not isinstance(data, list):
        raise WorkdayAdaptiveApiError("Adaptive access token response missing data")
    public_api_token = data[0].get("publicAPIToken")
    if not public_api_token:
        raise WorkdayAdaptiveApiError(
            "Adaptive access token response missing publicAPIToken"
        )
    return public_api_token
