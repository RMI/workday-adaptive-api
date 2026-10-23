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


@patch("workday_adaptive_api._http.requests.get")
class RaasFormatGuardTests(unittest.TestCase):
    """Workday ignores the Accept header; only the format parameter selects JSON."""

    def _ok(self, mock_get: Mock) -> None:
        response = Mock()
        response.ok = True
        response.json.return_value = {"Report_Entry": []}
        mock_get.return_value = response

    def _sent_url(self, mock_get: Mock) -> str:
        """Return the URL that requests.get would send for the last call."""
        return requests.Request(
            "GET", mock_get.call_args.args[0], params=mock_get.call_args.kwargs["params"]
        ).prepare().url

    def test_non_json_format_in_url_raises_before_request(self, mock_get: Mock) -> None:
        for value in ("csv", "simplexml", "CSV"):
            with self.assertRaisesRegex(ValueError, f"format={value}"):
                get_raas_data("token", f"https://example.com/report?a=1&format={value}")
        mock_get.assert_not_called()

    def test_non_json_format_in_params_raises_before_request(self, mock_get: Mock) -> None:
        with self.assertRaisesRegex(ValueError, "format=simplexml"):
            get_raas_data("token", "https://example.com/report", params={"format": "simplexml"})
        mock_get.assert_not_called()

    def test_conflicting_formats_raise(self, mock_get: Mock) -> None:
        with self.assertRaisesRegex(ValueError, "format=csv"):
            get_raas_data(
                "token", "https://example.com/report?format=csv", params={"format": "json"}
            )
        mock_get.assert_not_called()

    def test_missing_format_adds_json(self, mock_get: Mock) -> None:
        self._ok(mock_get)
        get_raas_data("token", "https://example.com/report", params={"Start_Date": "2026-01-01"})
        self.assertEqual(
            self._sent_url(mock_get),
            "https://example.com/report?Start_Date=2026-01-01&format=json",
        )

    def test_iterator_params_are_sent_once_encoded(self, mock_get: Mock) -> None:
        # The format check must not consume iterator values before the request.
        self._ok(mock_get)
        get_raas_data(
            "token",
            "https://example.com/report",
            params={"Company!WID": (wid for wid in ["a", "b"]), "format": "json"},
        )
        self.assertIsNone(mock_get.call_args.kwargs["params"])
        self.assertEqual(
            self._sent_url(mock_get),
            "https://example.com/report?Company%21WID=a&Company%21WID=b&format=json",
        )

    def test_encoded_url_is_not_changed(self, mock_get: Mock) -> None:
        # Report URLs carry encoded prompt names such as Ledger%21WID.
        self._ok(mock_get)
        url = "https://example.com/report?Ledger%21WID=abc&Date=2026-01-05&format=json"
        get_raas_data("token", url)
        self.assertEqual(self._sent_url(mock_get), url)

    def test_params_that_requests_sends_as_json_are_accepted(self, mock_get: Mock) -> None:
        # requests sends each of these as format=json, or drops a None value.
        self._ok(mock_get)
        for url, params in (
            ("https://example.com/report", {"format": ["json"]}),
            ("https://example.com/report", {"format": b"json"}),
            ("https://example.com/report?format=json", {"format": None}),
        ):
            get_raas_data("token", url, params=params)
        self.assertEqual(mock_get.call_count, 3)

    def test_none_format_param_adds_json(self, mock_get: Mock) -> None:
        self._ok(mock_get)
        get_raas_data("token", "https://example.com/report", params={"format": None})
        self.assertEqual(self._sent_url(mock_get), "https://example.com/report?format=json")

    def test_blank_format_raises(self, mock_get: Mock) -> None:
        with self.assertRaisesRegex(ValueError, "format=\\."):
            get_raas_data("token", "https://example.com/report?format=")
        mock_get.assert_not_called()

    def test_json_format_in_url_is_kept(self, mock_get: Mock) -> None:
        self._ok(mock_get)
        get_raas_data("token", "https://example.com/report?format=JSON")
        self.assertEqual(self._sent_url(mock_get), "https://example.com/report?format=JSON")


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
