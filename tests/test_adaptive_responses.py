from __future__ import annotations

import unittest
import warnings
from unittest.mock import Mock, patch

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

if __name__ == "__main__":
    unittest.main()
