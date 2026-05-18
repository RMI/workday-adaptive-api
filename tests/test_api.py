from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from workday_adaptive_api import (
    WorkdayAdaptiveApiError,
    export_accounts,
    get_adaptive_access_token,
    get_raas_data,
    get_workday_access_token,
)


class ApiTests(unittest.TestCase):
    @patch("workday_adaptive_api._http.requests.post")
    def test_get_workday_access_token_success(self, mock_post: Mock) -> None:
        response = Mock()
        response.ok = True
        response.json.return_value = {"access_token": "abc123"}
        mock_post.return_value = response

        token = get_workday_access_token("https://example.com/token", "id", "secret", "refresh")

        self.assertEqual(token, "abc123")

    @patch("workday_adaptive_api._http.requests.post")
    def test_get_workday_access_token_failure_raises(self, mock_post: Mock) -> None:
        response = Mock()
        response.ok = False
        response.status_code = 401
        response.text = "unauthorized"
        mock_post.return_value = response

        with self.assertRaises(WorkdayAdaptiveApiError):
            get_workday_access_token("https://example.com/token", "id", "secret", "refresh")

    @patch("workday_adaptive_api._http.requests.get")
    def test_get_adaptive_access_token_success(self, mock_get: Mock) -> None:
        response = Mock()
        response.ok = True
        response.json.return_value = {"data": [{"publicAPIToken": "adaptive-token"}]}
        mock_get.return_value = response

        token = get_adaptive_access_token("wd-token", "https://example.com/adaptive")

        self.assertEqual(token, "adaptive-token")

    @patch("workday_adaptive_api._http.requests.get")
    def test_get_raas_data_failure_raises(self, mock_get: Mock) -> None:
        response = Mock()
        response.ok = False
        response.status_code = 500
        response.text = "server error"
        mock_get.return_value = response

        with self.assertRaises(WorkdayAdaptiveApiError):
            get_raas_data("token", "https://example.com/report")

    @patch("workday_adaptive_api._http.requests.post")
    def test_export_accounts_returns_dataframe_without_writing_files(
        self,
        mock_post: Mock,
    ) -> None:
        response = Mock()
        response.ok = True
        response.text = """
        <response>
            <output>
                <accounts>
                    <account id="1" code="1000" name="Cash"/>
                </accounts>
            </output>
        </response>
        """
        mock_post.return_value = response

        frame = export_accounts("token", "https://example.com/api", "instance")

        self.assertEqual(frame.shape, (1, 3))
        self.assertEqual(frame.iloc[0]["name"], "Cash")


if __name__ == "__main__":
    unittest.main()
