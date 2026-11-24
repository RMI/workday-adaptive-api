# Workday Adaptive API

Reusable Python helpers for Workday and Adaptive integrations, packaged so other
projects can install directly from this repository.

## Install

From a public GitHub repository:

```powershell
pip install git+https://github.com/<owner>/<repo>.git
```

From a local clone while developing:

```powershell
pip install -e .
```

## Package Layout

- `workday_adaptive_api/auth.py`: Workday and Adaptive token helpers
- `workday_adaptive_api/adaptive.py`: Adaptive export functions
- `workday_adaptive_api/workday.py`: Workday RaaS helpers
- `workday_adaptive_api/parsers.py`: XML and CSV parsing helpers

## Usage

```python
from workday_adaptive_api import (
    get_adaptive_access_token,
    get_raas_dataframe,
    get_workday_access_token,
)

workday_token = get_workday_access_token(
    token_url="https://example.com/token",
    client_id="client-id",
    client_secret="client-secret",
    refresh_token="refresh-token",
)

adaptive_token = get_adaptive_access_token(
    workday_access_token=workday_token,
    adaptive_access_token_url="https://example.com/adaptive-token",
)

report = get_raas_dataframe(
    workday_access_token=workday_token,
    request_url="https://example.com/raas/report",
    params={"Start_Date": "2026-01-01", "End_Date": "2026-01-31"},
)
```

`get_raas_dataframe` returns one row for each report entry.
The values are strings, as Workday sends them.
To get the JSON response, use `get_raas_data`.

`export_data` returns Adaptive data for an account and its descendants.
It adds one column for each name in `dimension_names`:

```python
from workday_adaptive_api import export_data

revenue = export_data(
    adaptive_token,
    "https://example.com/adaptive-api",
    "instance-code",
    account_code="LAS_REVENUES",
    start_date="11/2026",
    end_date="12/2026",
    dimension_names=["WD Project", "WD Customer Contract"],
)
```

## Errors and Warnings

- A failed Workday or Adaptive call raises `WorkdayAdaptiveApiError`.
- A partial Adaptive result, for example a skipped account, issues `AdaptiveApiWarning`.

Library code does not load environment variables for you. If you want `.env`
support in a consuming app or script, load it there with `python-dotenv`.

## Environment Variables

See [.env.example](.env.example) for a sample local setup.

## Tests

Run the test suite with:

```powershell
python -m unittest discover -s tests
```

## Example Scripts

These local scripts load environment variables and get data for the previous month:

- [examples/raas_report.py](examples/raas_report.py) fetches a Workday report.
- [examples/adaptive_report.py](examples/adaptive_report.py) exports Adaptive net income.
