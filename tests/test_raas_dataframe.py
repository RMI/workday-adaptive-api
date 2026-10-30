from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import pandas as pd

from workday_adaptive_api import WorkdayAdaptiveApiError, get_raas_dataframe


def _ok(payload: object) -> Mock:
    response = Mock()
    response.ok = True
    response.json.return_value = payload
    return response


@patch("workday_adaptive_api._http.requests.get")
class GetRaasDataframeTests(unittest.TestCase):
    # Field names and value types match a production timesheet report. A field
    # that has no value for a row is absent from that row.
    def test_returns_one_row_per_report_entry(self, mock_get: Mock) -> None:
        mock_get.return_value = _ok(
            {
                "Report_Entry": [
                    {
                        "EmployeeID": "100001",
                        "Reported_Date": "2026-09-01",
                        "Reported_Quantity": "8",
                        "Reported_Quantity__Time_Entry_": "8",
                    },
                    {
                        "EmployeeID": "100002",
                        "Reported_Date": "2026-09-01",
                        "Reported_Quantity": "4",
                        "Reported_Quantity__Time_Off_": "4",
                    },
                ]
            }
        )

        frame = get_raas_dataframe("token", "https://example.com/report")

        self.assertIsInstance(frame, pd.DataFrame)
        self.assertEqual(len(frame), 2)
        self.assertEqual(
            list(frame.columns),
            [
                "EmployeeID",
                "Reported_Date",
                "Reported_Quantity",
                "Reported_Quantity__Time_Entry_",
                "Reported_Quantity__Time_Off_",
            ],
        )
        self.assertEqual(frame.loc[0, "EmployeeID"], "100001")
        self.assertTrue(pd.isna(frame.loc[0, "Reported_Quantity__Time_Off_"]))
        self.assertEqual(frame.loc[1, "Reported_Quantity__Time_Off_"], "4")

    def test_empty_report_returns_empty_dataframe(self, mock_get: Mock) -> None:
        mock_get.return_value = _ok({"Report_Entry": []})

        frame = get_raas_dataframe("token", "https://example.com/report")

        self.assertIsInstance(frame, pd.DataFrame)
        self.assertTrue(frame.empty)

    def test_payload_without_report_entry_raises(self, mock_get: Mock) -> None:
        mock_get.return_value = _ok({"error": "Invalid request"})

        with self.assertRaisesRegex(WorkdayAdaptiveApiError, "Report_Entry"):
            get_raas_dataframe("token", "https://example.com/report")

    def test_report_entry_that_is_not_a_list_raises(self, mock_get: Mock) -> None:
        mock_get.return_value = _ok({"Report_Entry": {"EmployeeID": "100001"}})

        with self.assertRaisesRegex(WorkdayAdaptiveApiError, "Report_Entry"):
            get_raas_dataframe("token", "https://example.com/report")

    def test_sends_params_and_requests_json(self, mock_get: Mock) -> None:
        mock_get.return_value = _ok({"Report_Entry": []})

        get_raas_dataframe(
            "token",
            "https://example.com/report",
            params={"Start_Date": "2026-09-01", "End_Date": "2026-09-30"},
            timeout=60,
        )

        sent_url = mock_get.call_args.args[0]
        self.assertIn("Start_Date=2026-09-01", sent_url)
        self.assertIn("End_Date=2026-09-30", sent_url)
        self.assertIn("format=json", sent_url)
        self.assertEqual(mock_get.call_args.kwargs["timeout"], 60)


if __name__ == "__main__":
    unittest.main()
