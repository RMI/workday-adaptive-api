from __future__ import annotations

import warnings
import xml.etree.ElementTree as ET

import pandas as pd

from ._http import AdaptiveApiWarning, WorkdayAdaptiveApiError, post_xml
from .parsers import (
    adaptive_export_to_dataframe,
    dimensions_to_dataframe,
    export_accounts_to_dataframe,
    generic_elements_to_dataframe,
)


def _adaptive_headers() -> dict[str, str]:
    return {"Content-Type": "application/xml"}


def _adaptive_credentials_xml(access_token: str, instance_code: str) -> str:
    return f'<credentials token="{access_token}" instanceCode="{instance_code}"/>'


def _format_messages(root: ET.Element) -> list[str]:
    formatted = []
    for message in root.iter("message"):
        text = (message.text or "").strip()
        label = message.get("key") or message.get("type")
        formatted.append(f"{label}: {text}" if label else text)
    return formatted


def _check_adaptive_response(response_text: str, context: str) -> None:
    """
    Raise when Adaptive reports a failed call, and warn on skipped input.

    Adaptive answers with HTTP 200 for most errors. The outcome is in the
    ``success`` attribute of the ``<response>`` root and in its ``<message>``
    elements.
    """
    try:
        root = ET.fromstring(response_text.strip())
    except ET.ParseError as exc:
        raise WorkdayAdaptiveApiError(
            f"{context} returned a response that is not XML: {exc}"
        ) from exc

    messages = _format_messages(root)
    if root.get("success") != "true":
        details = "; ".join(messages) or "no message returned"
        raise WorkdayAdaptiveApiError(f"{context} failed: {details}")

    for message in messages:
        warnings.warn(f"{context}: {message}", AdaptiveApiWarning, stacklevel=4)


def _post_adaptive_call(
    method: str,
    adaptive_access_token: str,
    adaptive_public_api_endpoint: str,
    adaptive_instance_code: str,
    *,
    body: str = "",
    timeout: int = 300,
) -> str:
    payload = (
        "<?xml version='1.0' encoding='UTF-8'?>"
        f'<call method="{method}" callerName="PYTHON">'
        f"{_adaptive_credentials_xml(adaptive_access_token, adaptive_instance_code)}"
        f"{body}"
        "</call>"
    )
    context = f"Adaptive {method} request"
    response_text = post_xml(
        adaptive_public_api_endpoint,
        headers=_adaptive_headers(),
        data=payload,
        timeout=timeout,
        context=context,
    )
    _check_adaptive_response(response_text, context)
    return response_text


def smoke_test_connection(
    adaptive_access_token: str,
    adaptive_public_api_endpoint: str,
    adaptive_instance_code: str,
    *,
    timeout: int = 300,
) -> pd.DataFrame:
    """Verify Adaptive connectivity by issuing an exportLevels request."""
    return export_levels(
        adaptive_access_token,
        adaptive_public_api_endpoint,
        adaptive_instance_code,
        timeout=timeout,
    )


def export_versions(
    adaptive_access_token: str,
    adaptive_public_api_endpoint: str,
    adaptive_instance_code: str,
    *,
    timeout: int = 300,
) -> str:
    """Return the raw XML from Adaptive exportVersions."""
    return _post_adaptive_call(
        "exportVersions",
        adaptive_access_token,
        adaptive_public_api_endpoint,
        adaptive_instance_code,
        timeout=timeout,
    )


def export_sheets(
    adaptive_access_token: str,
    adaptive_public_api_endpoint: str,
    adaptive_instance_code: str,
    *,
    timeout: int = 300,
) -> str:
    """Return the raw XML from Adaptive exportSheets."""
    return _post_adaptive_call(
        "exportSheets",
        adaptive_access_token,
        adaptive_public_api_endpoint,
        adaptive_instance_code,
        timeout=timeout,
    )


def export_accounts(
    adaptive_access_token: str,
    adaptive_public_api_endpoint: str,
    adaptive_instance_code: str,
    *,
    timeout: int = 300,
) -> pd.DataFrame:
    """
    Export Adaptive accounts and return them as a flattened DataFrame.

    Parameters
    ----------
    adaptive_access_token:
        Adaptive public API token used for authentication.
    adaptive_public_api_endpoint:
        Full Adaptive public API endpoint URL.
    adaptive_instance_code:
        Adaptive instance code sent with the credentials block.
    timeout:
        Request timeout in seconds for the API call.

    Returns
    -------
    pandas.DataFrame
        One row per ``<account>`` element with account attributes such as
        identifiers, codes, names, and types.

    Raises
    ------
    WorkdayAdaptiveApiError
        Raised when the HTTP request fails or Adaptive reports a failed call.
    """
    response_text = _post_adaptive_call(
        "exportAccounts",
        adaptive_access_token,
        adaptive_public_api_endpoint,
        adaptive_instance_code,
        timeout=timeout,
    )
    return export_accounts_to_dataframe(response_text)


def export_dimensions(
    adaptive_access_token: str,
    adaptive_public_api_endpoint: str,
    adaptive_instance_code: str,
    *,
    version_name: str = "Live Forecast",
    dimension_ids: str = "",
    timeout: int = 300,
) -> pd.DataFrame:
    """
    Export Adaptive dimensions and flatten dimension values into a DataFrame.

    Parameters
    ----------
    adaptive_access_token:
        Adaptive public API token used for authentication.
    adaptive_public_api_endpoint:
        Full Adaptive public API endpoint URL.
    adaptive_instance_code:
        Adaptive instance code sent with the credentials block.
    version_name:
        Version name used by the ``include`` block for the export request.
    dimension_ids:
        Optional comma-separated Adaptive dimension IDs. Leave empty to export
        all available dimensions.
    timeout:
        Request timeout in seconds for the API call.

    Returns
    -------
    pandas.DataFrame
        One row per ``dimensionValue`` element, with parent dimension metadata
        repeated on each row.

    Raises
    ------
    WorkdayAdaptiveApiError
        Raised when the HTTP request fails or Adaptive reports a failed call.
    """
    body = (
        f'<include versionName="{version_name}" '
        f'attributes="true" dimensionIDs="{dimension_ids}" '
        'dimensionValues="true" displayNameEnabled="true"/>'
    )
    response_text = _post_adaptive_call(
        "exportDimensions",
        adaptive_access_token,
        adaptive_public_api_endpoint,
        adaptive_instance_code,
        body=body,
        timeout=timeout,
    )
    return dimensions_to_dataframe(response_text)


def export_project_dimension_values(
    adaptive_access_token: str,
    adaptive_public_api_endpoint: str,
    adaptive_instance_code: str,
    *,
    version_name: str = "Live Forecast",
    dimension_ids: str = "",
    timeout: int = 300,
) -> pd.DataFrame:
    """Convenience wrapper for project-related dimension exports."""
    return export_dimensions(
        adaptive_access_token,
        adaptive_public_api_endpoint,
        adaptive_instance_code,
        version_name=version_name,
        dimension_ids=dimension_ids,
        timeout=timeout,
    )


def export_data(
    adaptive_access_token: str,
    adaptive_public_api_endpoint: str,
    adaptive_instance_code: str,
    *,
    version_name: str = "Live Forecast",
    account_code: str = "",
    start_date: str = "08/2025",
    end_date: str = "09/2025",
    dimension_name: str = "WD Project",
    timeout: int = 300,
) -> pd.DataFrame:
    """
    Export Adaptive cube data for an account and time range.

    This helper sends an ``exportData`` request, parses the CSV payload embedded
    in the XML response, and returns the result as a DataFrame.

    Parameters
    ----------
    adaptive_access_token:
        Adaptive public API token used for authentication.
    adaptive_public_api_endpoint:
        Full Adaptive public API endpoint URL.
    adaptive_instance_code:
        Adaptive instance code sent with the credentials block.
    version_name:
        Adaptive version name to query, such as ``"Live Forecast"``.
    account_code:
        Account code to export. The request includes descendants for this
        account automatically.
    start_date:
        Start of the export time span, typically in ``MM/YYYY`` format expected
        by the Adaptive API.
    end_date:
        End of the export time span, typically in ``MM/YYYY`` format expected
        by the Adaptive API.
    dimension_name:
        Primary dimension to include alongside the built-in ``Project ID``
        dimension already added by this helper.
    timeout:
        Request timeout in seconds for the API call.

    Returns
    -------
    pandas.DataFrame
        Parsed export rows from the Adaptive CSV payload.

    Raises
    ------
    WorkdayAdaptiveApiError
        Raised when the HTTP request fails or Adaptive reports a failed call.
    """
    body = f"""
        <version name="{version_name}" isDefault="false"/>
        <format useInternalCodes="true" includeUnmappedItems="false" displayNameEnabled="true" includeDisplayNames="true"/>
        <filters>
            <accounts>
                <account code="{account_code}" includeDescendants="true" isAssumption="false"/>
            </accounts>
            <timeSpan start="{start_date}" end="{end_date}"/>
        </filters>
        <dimensions>
            <dimension name="{dimension_name}"/>
            <dimension name="Project ID"/>
        </dimensions>
        <rules></rules>
    """
    response_text = _post_adaptive_call(
        "exportData",
        adaptive_access_token,
        adaptive_public_api_endpoint,
        adaptive_instance_code,
        body=body,
        timeout=timeout,
    )
    return adaptive_export_to_dataframe(response_text)


def export_model_sheet(
    adaptive_access_token: str,
    adaptive_public_api_endpoint: str,
    adaptive_instance_code: str,
    *,
    sheet_name: str,
    version_name: str = "Live Forecast",
    start_date: str = "08/2025",
    end_date: str = "09/2025",
    include_all_columns: bool = False,
    timeout: int = 300,
) -> pd.DataFrame:
    """
    Export data from an Adaptive modeled sheet as a DataFrame.

    This helper sends an ``exportConfigurableModelData`` request and parses the
    returned CSV payload into a pandas DataFrame.

    Parameters
    ----------
    adaptive_access_token:
        Adaptive public API token used for authentication.
    adaptive_public_api_endpoint:
        Full Adaptive public API endpoint URL.
    adaptive_instance_code:
        Adaptive instance code sent with the credentials block.
    sheet_name:
        Name of the modeled sheet to export.
    version_name:
        Adaptive version name to query.
    start_date:
        Start of the export time span, typically in ``MM/YYYY`` format expected
        by the Adaptive API.
    end_date:
        End of the export time span, typically in ``MM/YYYY`` format expected
        by the Adaptive API.
    include_all_columns:
        When ``True``, request all available modeled-sheet columns instead of
        the reduced default set.
    timeout:
        Request timeout in seconds for the API call.

    Returns
    -------
    pandas.DataFrame
        Parsed modeled-sheet rows from the Adaptive CSV payload.

    Raises
    ------
    WorkdayAdaptiveApiError
        Raised when the HTTP request fails or Adaptive reports a failed call.
    """
    body = f"""
        <version name="{version_name}"/>
        <modeled-sheet
            name="{sheet_name}"
            isGlobal="false"
            displayNameEnabled="true"
            includeDisplayNames="true"
            includeAllColumns="{str(include_all_columns).lower()}"
            isGetAllRows="true"
            useNumericIDs="false"
        />
        <filters>
            <timeSpan start="{start_date}" end="{end_date}"/>
        </filters>
    """
    response_text = _post_adaptive_call(
        "exportConfigurableModelData",
        adaptive_access_token,
        adaptive_public_api_endpoint,
        adaptive_instance_code,
        body=body,
        timeout=timeout,
    )
    return adaptive_export_to_dataframe(response_text)


def export_levels(
    adaptive_access_token: str,
    adaptive_public_api_endpoint: str,
    adaptive_instance_code: str,
    *,
    timeout: int = 300,
) -> pd.DataFrame:
    """
    Export Adaptive levels and return them as a DataFrame.

    Parameters
    ----------
    adaptive_access_token:
        Adaptive public API token used for authentication.
    adaptive_public_api_endpoint:
        Full Adaptive public API endpoint URL.
    adaptive_instance_code:
        Adaptive instance code sent with the credentials block.
    timeout:
        Request timeout in seconds for the API call.

    Returns
    -------
    pandas.DataFrame
        One row per ``<level>`` element with its XML attributes flattened into
        columns.

    Raises
    ------
    WorkdayAdaptiveApiError
        Raised when the HTTP request fails or Adaptive reports a failed call.
    """
    response_text = _post_adaptive_call(
        "exportLevels",
        adaptive_access_token,
        adaptive_public_api_endpoint,
        adaptive_instance_code,
        timeout=timeout,
    )
    return generic_elements_to_dataframe(response_text, ".//output//levels//level")
