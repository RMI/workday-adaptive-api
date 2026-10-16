from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import requests

from workday_adaptive_api import (
    WorkdayAdaptiveApiError,
    export_levels,
    get_adaptive_access_token,
    get_raas_data,
    get_workday_access_token,
)


def _non_json_response(text: str, content_type: str) -> Mock:
    # Backstop: an HTTP 200 body that is not JSON, for example from a proxy or
    # a report that ignores format=json.
    response = Mock()
    response.ok = True
    response.status_code = 200
    response.text = text
    response.headers = {"Content-Type": content_type}
    response.json.side_effect = requests.exceptions.JSONDecodeError(
        "Expecting value", text, 0
    )
    return response


class NonJsonResponseTests(unittest.TestCase):
    @patch("workday_adaptive_api._http.requests.get")
    def test_raas_xml_response_raises(self, mock_get: Mock) -> None:
        mock_get.return_value = _non_json_response(
            "<?xml version='1.0' encoding='UTF-8'?><wd:Report_Data/>",
            "text/xml; charset=UTF-8",
        )
        with self.assertRaisesRegex(
            WorkdayAdaptiveApiError, r"not JSON \(Content-Type: text/xml"
        ):
            get_raas_data("token", "https://example.com/report")

    @patch("workday_adaptive_api._http.requests.get")
    def test_raas_csv_response_raises(self, mock_get: Mock) -> None:
        mock_get.return_value = _non_json_response(
            "Journal,Journal_Number\nOperational,1\n", "text/csv; charset=UTF-8"
        )
        with self.assertRaisesRegex(WorkdayAdaptiveApiError, "Journal,Journal_Number"):
            get_raas_data("token", "https://example.com/report")

    @patch("workday_adaptive_api._http.requests.post")
    def test_workday_token_non_json_raises(self, mock_post: Mock) -> None:
        mock_post.return_value = _non_json_response("<html>Error</html>", "text/html")
        with self.assertRaisesRegex(WorkdayAdaptiveApiError, "Workday access token"):
            get_workday_access_token("https://example.com/token", "id", "secret", "r")

    @patch("workday_adaptive_api._http.requests.get")
    def test_adaptive_token_non_json_raises(self, mock_get: Mock) -> None:
        mock_get.return_value = _non_json_response("<html>Error</html>", "text/html")
        with self.assertRaisesRegex(WorkdayAdaptiveApiError, "Adaptive access token"):
            get_adaptive_access_token("wd-token", "https://example.com/adaptive")


class NetworkErrorTests(unittest.TestCase):
    @patch("workday_adaptive_api._http.requests.get")
    def test_raas_timeout_raises(self, mock_get: Mock) -> None:
        # A report URL without its date prompt can run past the read timeout.
        mock_get.side_effect = requests.exceptions.ReadTimeout("Read timed out.")
        with self.assertRaisesRegex(
            WorkdayAdaptiveApiError, "Workday RaaS request failed: ReadTimeout"
        ) as caught:
            get_raas_data("token", "https://example.com/report")
        self.assertIsInstance(caught.exception.__cause__, requests.exceptions.ReadTimeout)

    @patch("workday_adaptive_api._http.requests.post")
    def test_adaptive_connection_error_raises(self, mock_post: Mock) -> None:
        mock_post.side_effect = requests.exceptions.ConnectionError("Name not resolved")
        with self.assertRaisesRegex(
            WorkdayAdaptiveApiError, "exportLevels request failed: ConnectionError"
        ):
            export_levels("token", "https://example.com/api", "instance")

    @patch("workday_adaptive_api._http.requests.post")
    def test_workday_token_timeout_raises(self, mock_post: Mock) -> None:
        mock_post.side_effect = requests.exceptions.ConnectTimeout("timed out")
        with self.assertRaisesRegex(WorkdayAdaptiveApiError, "ConnectTimeout"):
            get_workday_access_token("https://example.com/token", "id", "secret", "r")


if __name__ == "__main__":
    unittest.main()
