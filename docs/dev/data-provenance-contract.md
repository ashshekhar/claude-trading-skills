# Common Trading Data Contract — `data_provenance`

> Schema version: **1.0**
> Source: GitHub issue #297 (2026-08 external review, score 86/100).
> Validator: [`scripts/validate_provenance.py`](../../scripts/validate_provenance.py)

## Purpose

Eighteen skills require the FMP API, and endpoint-drift checks already exist for
API *clients*. But there is no shared standard for the **meaning and
time-consistency of the data the consumers actually read**. This contract is the
shared, versioned answer. It forces every data-fetching, screening, and
backtesting skill to state the semantics of the data it returns so that a
downstream consumer can reason about restated financials, non-point-in-time
values, missing delisted tickers, earnings-timestamp error, split/dividend
adjustment, and free-vs-paid tier differences.

## Contract

Every data-fetching, screening, and backtesting skill **must** include a
`data_provenance` object in its JSON/YAML output. The block is required, not
optional, and its shape is versioned.

```yaml
data_provenance:
  # Contract version. Must match the current schema (1.0).
  schema_version: "1.0"

  # Where the data was fetched from. For FMP this is commonly "fmp".
  provider: fmp

  # The specific endpoint or dataset that produced the rows.
  endpoint: historical-price-eod

  # When the fetch actually occurred (ISO-8601 UTC timestamp).
  retrieved_at: 2026-08-01T14:30:00Z

  # The date the data points describe (the "as of" business date). A date
  # (YYYY-MM-DD) or a timestamp.
  as_of: 2026-07-31

  # IANA timezone the data is reported in.
  timezone: America/New_York

  # Whether the data has been adjusted for splits and dividends.
  adjusted: true

  # Whether the data is point-in-time (no look-ahead into future revisions).
  point_in_time: true

  # Whether the universe includes securities that were subsequently delisted.
  # Unknown must be stated honestly as false, not omitted.
  survivorship_free: false

  # Whether corporate actions have been handled for the returned rows.
  corporate_actions_handled: true
```

### Required fields

| Field | Type | Meaning |
|-------|------|---------|
| `schema_version` | string | Contract version this block follows. Must match the current version. |
| `provider` | non-empty string | Data provider (e.g. `fmp`, `finviz`, `trader-monty`). |
| `endpoint` | non-empty string | Endpoint or dataset that produced the rows. |
| `retrieved_at` | ISO-8601 timestamp | When the fetch occurred. |
| `as_of` | ISO-8601 date (or timestamp) | The business date the data describes. |
| `timezone` | valid IANA string | Reporting timezone. |
| `adjusted` | boolean | Adjusted for splits and dividends. |
| `point_in_time` | boolean | No look-ahead into future revisions. |
| `survivorship_free` | boolean | Includes delisted securities. |
| `corporate_actions_handled` | boolean | Corporate actions handled. |

### Rules

1. **Required.** Every applicable skill must emit the block. It is not optional.
2. **State unknown honestly.** If a value is unknown, write `false` (or the
   conservative value) rather than omitting the field. Omitting a required field
   is a validation error.
3. **Versioned.** `schema_version` identifies the schema. The validator rejects a
   mismatched version so a consumer can detect a contract change.
4. **Extensible.** Unknown extra fields are permitted so the contract can evolve
   without breaking older outputs; only the required set is enforced.

## Validation

Use the shared validator in skill tests and workflow E2E replay harnesses:

```bash
# On a JSON report
python3 scripts/validate_provenance.py --file reports/some_report.json

# On a YAML report
python3 scripts/validate_provenance.py --file reports/some_report.yaml

# From stdin
cat report.json | python3 scripts/validate_provenance.py --stdin
```

- Exit code `0` — valid block.
- Exit code `1` — invalid block (each error printed to stdout).
- Exit code `2` — I/O or parse error.

Python API:

```python
import sys
sys.path.insert(0, "scripts")
from validate_provenance import validate_provenance, SCHEMA_VERSION

errors = validate_provenance(report["data_provenance"])
assert errors == [], errors  # empty => valid
```

## Scope and rollout

Implementation is incremental (see issue #297 acceptance criteria):

- **Done here:** provenance schema documented and versioned (this file).
- **Done here:** the shared validator + its tests.
- **Not here (follow-up slices):** every FMP-required skill emitting the block
  in its JSON output, and the workflow E2E replay harness validating provenance
  on artifact handoffs.
