# Workday and Adaptive API Functions

This repository provides Python functions for interacting with Adaptive Insights and Workday APIs, exporting data, and processing it into CSV format for analysis.

## Contents

- `functions.py`: Contains utility functions for authentication, environment configuration, and API requests to Adaptive Insights and Workday.
- `requirements.txt`: Lists required Python packages for the project.

## Setup

1. Clone the repository.
2. Create and activate a Python virtual environment:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

## Usage

### Exporting Account Balances
Run `grantBalance.py` to export account balances from Adaptive Insights. The script authenticates, makes API requests, parses XML, and saves results as CSV.

### Exporting Workday Journal Lines
Run `wdJournals.py` to retrieve journal lines from Workday. The script authenticates, fetches data for a specified date range, normalizes JSON, and saves results as CSV.


## Example `.env` File

Create a `.env` file in the project root to store environment variables. Do not include actual credentials or sensitive information.

```env
WD_CLIENT_ID=
WD_CLIENT_SECRET=
WD_REFRESH_TOKEN=
WD_TOKEN_ENDPOINT=
WD_TOKEN_ENDPOINT_PROD=
ADAPTIVE_ACCESS_TOKEN_ENDPOINT=
ADAPTIVE_ACCESS_TOKEN_ENDPOINT_PROD=
ADAPTIVE_PUBLIC_API_ENDPOINT=
ADAPTIVE_INSTANCE_CODE=
ADAPTIVE_INSTANCE_CODE_PROD=
JOURNAL_REPORT_URL=
JOURNAL_REPORT_URL_PROD=
```

## Testing
Run `test_adaptive.py` to execute tests for Adaptive Insights API integration and data export functions.

## Notes
- Ensure you have valid API credentials and endpoint URLs for Adaptive Insights and Workday.
- The scripts are designed for modularity and can be adapted for other reporting or data export needs.

