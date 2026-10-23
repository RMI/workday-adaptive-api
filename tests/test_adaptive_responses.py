from __future__ import annotations

import unittest
import warnings
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch

import pandas as pd

from workday_adaptive_api import (
    AdaptiveApiWarning,
    WorkdayAdaptiveApiError,
    export_data,
    export_dimensions,
    export_levels,
    export_model_sheet,
    export_versions,
)
from workday_adaptive_api.adaptive import _post_adaptive_call
from workday_adaptive_api.parsers import dimensions_to_dataframe

ARGS = ("token", "https://example.com/api", "instance")

# Response bodies below copy the messages that the Adaptive API returned for
# each input in a sandbox instance. Adaptive sends all of them with HTTP 200.
INVALID_XML = """<?xml version='1.0' encoding='UTF-8'?>
<response success="false"><messages>
<message key="invalid-xml">Illegal Input. Input data must be an XML document.</message>
</messages></response>"""

UNKNOWN_METHOD = """<response success="false"><messages>
<message key="unknown-function-name">Unknown method name exportNothing</message>
</messages></response>"""

INVALID_VERSION = """<response success="false"><messages>
<message key="error-invalid-version">Version is not valid.</message>
</messages></response>"""

INVALID_TIMESPAN = """<response success="false"><messages>
<message key="error-invalid-timespan">Error, invalid timespan: 2025-08 or 2025-09 for one or more accounts being exported.</message>
</messages></response>"""

INVALID_DIMENSION_IDS = """<response success="false"><messages>
<message key="invalid-attribute">Invalid dimension id list.</message>
</messages></response>"""

DATA_WITH_WARNINGS = """<response success="true"><messages>
<message key="warning-invalid-account-in-filter">Invalid account specified in filter: NO_SUCH_ACCOUNT_XYZ, isAssumption: false</message>
<message key="warning-invalid-dimension">Skipping invalid dimension name: Project ID</message>
</messages><output><![CDATA[Account Name,Account Code,08/2025
Cash,1000,5
]]></output></response>"""

DATA_OK = """<response success="true"><output><![CDATA[Account Name,Account Code,08/2025
Cash,1000,5
]]></output></response>"""

LEVELS_OK = """<response success="true"><output><levels>
<level id="1" name="Company"/>
</levels></output></response>"""

DIMENSIONS_OK = """<response success="true"><output><dimensions>
<dimension id="10" name="Project">
<dimensionValue id="100" name="Parent" code="P">
<dimensionValue id="101" name="Child" code="C">
<dimensionValue id="102" name="Grandchild" code="G"/>
</dimensionValue>
</dimensionValue>
<dimensionValue id="200" name="Other" code="O"/>
</dimension>
</dimensions></output></response>"""


def _response(text: str) -> Mock:
    response = Mock()
    response.ok = True
    response.status_code = 200
    response.text = text
    return response


def _sent_payload(mock_post: Mock) -> ET.Element:
    """Parse the request body; this fails if the library sent malformed XML."""
    return ET.fromstring(mock_post.call_args.kwargs["data"])


@patch("workday_adaptive_api._http.requests.post")
class FailedCallTests(unittest.TestCase):
    """Adaptive reports success="false" with HTTP 200; each must raise."""

    def test_invalid_xml_raises(self, mock_post: Mock) -> None:
        mock_post.return_value = _response(INVALID_XML)
        with self.assertRaisesRegex(WorkdayAdaptiveApiError, "invalid-xml"):
            export_levels(*ARGS)

    def test_unknown_method_raises(self, mock_post: Mock) -> None:
        mock_post.return_value = _response(UNKNOWN_METHOD)
        with self.assertRaisesRegex(WorkdayAdaptiveApiError, "unknown-function-name"):
            _post_adaptive_call("exportNothing", *ARGS)

    def test_unknown_version_raises(self, mock_post: Mock) -> None:
        mock_post.return_value = _response(INVALID_VERSION)
        with self.assertRaisesRegex(WorkdayAdaptiveApiError, "error-invalid-version"):
            export_data(*ARGS, version_name="No Such Version", account_code="1000")

    def test_invalid_timespan_raises(self, mock_post: Mock) -> None:
        mock_post.return_value = _response(INVALID_TIMESPAN)
        with self.assertRaisesRegex(WorkdayAdaptiveApiError, "error-invalid-timespan"):
            export_data(*ARGS, account_code="1000", start_date="2025-08", end_date="2025-09")

    def test_invalid_dimension_ids_raises(self, mock_post: Mock) -> None:
        mock_post.return_value = _response(INVALID_DIMENSION_IDS)
        with self.assertRaisesRegex(WorkdayAdaptiveApiError, "Invalid dimension id list"):
            export_dimensions(*ARGS, dimension_ids="not-a-list")

    def test_failed_raw_export_raises(self, mock_post: Mock) -> None:
        mock_post.return_value = _response(INVALID_XML)
        with self.assertRaises(WorkdayAdaptiveApiError):
            export_versions(*ARGS)

    def test_missing_success_attribute_raises(self, mock_post: Mock) -> None:
        mock_post.return_value = _response("<response><output/></response>")
        with self.assertRaisesRegex(WorkdayAdaptiveApiError, "no message returned"):
            export_levels(*ARGS)

    def test_non_xml_response_raises(self, mock_post: Mock) -> None:
        mock_post.return_value = _response("<html>Service Unavailable")
        with self.assertRaisesRegex(WorkdayAdaptiveApiError, "not XML"):
            export_levels(*ARGS)


@patch("workday_adaptive_api._http.requests.post")
class PartialResultTests(unittest.TestCase):
    """Adaptive skips invalid accounts or dimensions and returns the rest."""

    def test_skipped_input_warns_and_returns_data(self, mock_post: Mock) -> None:
        mock_post.return_value = _response(DATA_WITH_WARNINGS)
        with self.assertWarns(AdaptiveApiWarning) as caught:
            frame = export_data(*ARGS, account_code="1000")
        self.assertEqual(frame.shape, (1, 3))
        self.assertIn("warning-invalid-account-in-filter", str(caught.warning))

    def test_warnings_can_be_made_errors(self, mock_post: Mock) -> None:
        mock_post.return_value = _response(DATA_WITH_WARNINGS)
        with warnings.catch_warnings():
            warnings.simplefilter("error", AdaptiveApiWarning)
            with self.assertRaises(AdaptiveApiWarning):
                export_data(*ARGS, account_code="1000")

    def test_clean_response_does_not_warn(self, mock_post: Mock) -> None:
        mock_post.return_value = _response(DATA_OK)
        with warnings.catch_warnings():
            warnings.simplefilter("error", AdaptiveApiWarning)
            frame = export_data(*ARGS, account_code="1000")
        self.assertEqual(frame.shape, (1, 3))

    def test_unknown_dimension_ids_warn(self, mock_post: Mock) -> None:
        # Adaptive returns only dimension 10 for "10,999" and sends no message.
        mock_post.return_value = _response(DIMENSIONS_OK)
        with self.assertWarnsRegex(AdaptiveApiWarning, "dimension_ids 999$"):
            frame = export_dimensions(*ARGS, dimension_ids="10, 999")
        self.assertEqual(len(frame), 4)

    def test_known_dimension_ids_do_not_warn(self, mock_post: Mock) -> None:
        mock_post.return_value = _response(DIMENSIONS_OK)
        with warnings.catch_warnings():
            warnings.simplefilter("error", AdaptiveApiWarning)
            export_dimensions(*ARGS, dimension_ids="10")

    def test_message_without_key_keeps_text(self, mock_post: Mock) -> None:
        mock_post.return_value = _response(
            '<response success="false"><messages>'
            "<message>Invalid 'modeled-sheet name' attribute: No Such Sheet</message>"
            "</messages></response>"
        )
        with self.assertRaisesRegex(
            WorkdayAdaptiveApiError, "failed: Invalid 'modeled-sheet name'"
        ):
            export_model_sheet(*ARGS, sheet_name="No Such Sheet")

    def test_export_data_requests_only_dimension_name(self, mock_post: Mock) -> None:
        # The instances have no "Project ID" dimension, so it is not requested.
        mock_post.return_value = _response(DATA_OK)
        export_data(*ARGS, account_code="1000")
        names = [d.get("name") for d in _sent_payload(mock_post).iter("dimension")]
        self.assertEqual(names, ["WD Project"])


@patch("workday_adaptive_api._http.requests.post")
class RequestXmlTests(unittest.TestCase):
    """User input must not make the request XML malformed."""

    SPECIAL = 'R&D "Plan" <v2>'

    def test_export_dimensions_escapes_version_name(self, mock_post: Mock) -> None:
        mock_post.return_value = _response(DIMENSIONS_OK)
        export_dimensions(*ARGS, version_name=self.SPECIAL, dimension_ids="1,2")
        include = _sent_payload(mock_post).find("include")
        self.assertEqual(include.get("versionName"), self.SPECIAL)
        self.assertEqual(include.get("dimensionIDs"), "1,2")

    def test_export_data_escapes_all_inputs(self, mock_post: Mock) -> None:
        mock_post.return_value = _response(DATA_OK)
        export_data(
            *ARGS,
            version_name=self.SPECIAL,
            account_code="A&B",
            dimension_name='Dim "X"',
        )
        payload = _sent_payload(mock_post)
        self.assertEqual(payload.find("version").get("name"), self.SPECIAL)
        self.assertEqual(payload.find(".//account").get("code"), "A&B")
        self.assertEqual(payload.find(".//dimension").get("name"), 'Dim "X"')

    def test_export_model_sheet_escapes_sheet_name(self, mock_post: Mock) -> None:
        mock_post.return_value = _response(DATA_OK)
        export_model_sheet(*ARGS, sheet_name=self.SPECIAL)
        sheet = _sent_payload(mock_post).find("modeled-sheet")
        self.assertEqual(sheet.get("name"), self.SPECIAL)

    def test_credentials_are_escaped(self, mock_post: Mock) -> None:
        mock_post.return_value = _response(LEVELS_OK)
        export_levels('tok&"<', "https://example.com/api", "inst&1")
        credentials = _sent_payload(mock_post).find("credentials")
        self.assertEqual(credentials.get("token"), 'tok&"<')
        self.assertEqual(credentials.get("instanceCode"), "inst&1")

    def test_empty_dimension_ids_is_omitted(self, mock_post: Mock) -> None:
        mock_post.return_value = _response(DIMENSIONS_OK)
        export_dimensions(*ARGS)
        include = _sent_payload(mock_post).find("include")
        self.assertNotIn("dimensionIDs", include.attrib)

    def test_reversed_time_span_raises_before_request(self, mock_post: Mock) -> None:
        for call in (
            lambda: export_data(*ARGS, start_date="09/2025", end_date="08/2025"),
            lambda: export_model_sheet(
                *ARGS, sheet_name="Sheet", start_date="09/2025", end_date="08/2025"
            ),
        ):
            with self.assertRaisesRegex(ValueError, "after end_date"):
                call()
        mock_post.assert_not_called()


class NestedDimensionValueTests(unittest.TestCase):
    def test_nested_values_are_included_with_parent_id(self) -> None:
        frame = dimensions_to_dataframe(DIMENSIONS_OK)
        self.assertEqual(sorted(frame["value_id"]), ["100", "101", "102", "200"])
        parents = dict(zip(frame["value_id"], frame["value_parent_id"]))
        self.assertTrue(pd.isna(parents["100"]))
        self.assertEqual(parents["101"], "100")
        self.assertEqual(parents["102"], "101")
        self.assertTrue(pd.isna(parents["200"]))


if __name__ == "__main__":
    unittest.main()
