from __future__ import annotations

import os
from datetime import date, timedelta

from dotenv import load_dotenv

from workday_adaptive_api import get_raas_dataframe, get_workday_access_token


def previous_month_range() -> tuple[str, str]:
    today = date.today()
    first_of_this_month = date(today.year, today.month, 1)
    end_date = first_of_this_month - timedelta(days=1)
    start_date = date(end_date.year, end_date.month, 1)
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


if __name__ == "__main__":
    load_dotenv()

    start_date, end_date = previous_month_range()
    token = get_workday_access_token(
        token_url=os.environ["WD_TOKEN_ENDPOINT_PROD"],
        client_id=os.environ["WD_CLIENT_ID"],
        client_secret=os.environ["WD_CLIENT_SECRET"],
        refresh_token=os.environ["WD_REFRESH_TOKEN"],
    )
    report = get_raas_dataframe(
        token,
        os.environ["TIMESHEET_REPORT_URL_PROD"],
        params={"Start_Date": start_date, "End_Date": end_date},
    )
    print(report)
