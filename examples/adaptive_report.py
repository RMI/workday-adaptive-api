from __future__ import annotations

import os
from datetime import date, timedelta

from dotenv import load_dotenv

from workday_adaptive_api import (
    export_data,
    get_adaptive_access_token,
    get_workday_access_token,
)

# Net_Income is revenue minus expense.
ACCOUNT_CODE = "Net_Income"


def previous_month() -> str:
    today = date.today()
    end_of_last_month = date(today.year, today.month, 1) - timedelta(days=1)
    return end_of_last_month.strftime("%m/%Y")


if __name__ == "__main__":
    load_dotenv()

    month = previous_month()
    workday_token = get_workday_access_token(
        token_url=os.environ["WD_TOKEN_ENDPOINT_PROD"],
        client_id=os.environ["WD_CLIENT_ID"],
        client_secret=os.environ["WD_CLIENT_SECRET"],
        refresh_token=os.environ["WD_REFRESH_TOKEN"],
    )
    adaptive_token = get_adaptive_access_token(
        workday_token,
        os.environ["ADAPTIVE_ACCESS_TOKEN_ENDPOINT_PROD"],
    )
    report = export_data(
        adaptive_token,
        os.environ["ADAPTIVE_PUBLIC_API_ENDPOINT"],
        os.environ["ADAPTIVE_INSTANCE_CODE_PROD"],
        account_code=ACCOUNT_CODE,
        start_date=month,
        end_date=month,
    )
    print(report)
