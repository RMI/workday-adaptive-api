# Changelog

## 0.2.0 - 2026-10-16

### Fixed

- Adaptive calls now raise `WorkdayAdaptiveApiError` when the response has `success="false"`.
  Before, they returned an empty DataFrame.
- Adaptive calls now raise `WorkdayAdaptiveApiError` when the response is not XML.
- Adaptive calls now issue `AdaptiveApiWarning` for each message in a successful response.
  Adaptive uses these messages to report skipped accounts and dimensions.
- `export_dimensions` now warns when a requested dimension ID is not in the response.
- The library now escapes the values that it puts in the request XML.
  Before, a value with `&`, `"`, or `<` made the request malformed.
- `export_dimensions` with no `dimension_ids` now exports all dimensions.
  Before, it sent `dimensionIDs=""`, which Adaptive rejects.
- `dimensions_to_dataframe` now includes nested dimension values.
  A new `value_parent_id` column holds the ID of the parent value.
- `export_data` no longer requests a `Project ID` dimension.
  The sandbox and production instances have no dimension with that name,
  so Adaptive skipped it and warned on every call.
  Project data comes from `dimension_name`, which defaults to `WD Project`.
- `export_data` and `export_model_sheet` now raise `ValueError` when `start_date` is after `end_date`.
- All requests now raise `WorkdayAdaptiveApiError` for network errors and timeouts.
  Before, they raised `requests` exceptions.
- Workday calls now raise `WorkdayAdaptiveApiError` when a response is not JSON.
  Before, they raised `JSONDecodeError`.
- `get_raas_data` now adds `format=json` when the URL and `params` have no `format`.
  Before, Workday returned XML for these requests.
- `get_raas_data` now raises `ValueError` when the URL or `params` ask for a format other than JSON.

### Added

- `AdaptiveApiWarning` warning category.
- `examples/adaptive_report.py`, which exports Adaptive net income for the previous month.
