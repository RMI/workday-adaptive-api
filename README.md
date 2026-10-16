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
    get_raas_data,
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

report_data = get_raas_data(
    workday_access_token=workday_token,
    request_url="https://example.com/raas/report",
    params={"Start_Date": "2026-01-01", "End_Date": "2026-01-31"},
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

## Example Script

See [examples/raas_report.py](examples/raas_report.py) for a local script that
loads environment variables and fetches a Workday report.
