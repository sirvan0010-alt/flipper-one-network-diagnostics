# Local data model

Status: initial implementation, schema version 1.

## Storage goals

- All measurements remain on the device by default.
- The database is an implementation detail behind the core API.
- A diagnostic result is stored as a complete JSON envelope for forward-compatible export.
- Common fields and findings are also normalized into SQLite tables for efficient history and filtering.
- No account, cloud, telemetry or external database is required.

## SQLite schema v1

### diagnostic_runs

| Column | Meaning |
|---|---|
| run_id | Locally generated UUID |
| collector | Stable identifier of the producing collector |
| status | Collector status such as pass, warning, fail or error |
| interface | Interface name, if applicable |
| schema_version | Diagnostic result envelope version |
| started_at | ISO-8601 UTC timestamp |
| result_json | Complete JSON-serialized DiagnosticResult |

### findings

| Column | Meaning |
|---|---|
| finding_id | Local integer primary key |
| run_id | Parent diagnostic run |
| code | Stable machine-readable finding code |
| severity | info, warning, critical or other defined severity |
| title | Short user-facing title |
| detail | Evidence and explanation |
| recommendation | Suggested next diagnostic or remediation step |

Findings are deleted only when their parent run is deleted (foreign-key cascade). No deletion UI is implemented yet.

## Migration policy

SQLite `PRAGMA user_version` tracks the schema version. New migrations must be sequential and tested against:
1. an empty database;
2. a database at the immediately previous schema version;
3. a database with a newer version (must fail closed, never downgrade or rewrite).

Schema changes must preserve old results. The full result JSON remains the archival source for each run.

## Current API

- `initialize_database(path)`
- `save_result(path, result)`
- `list_results(path, limit=50)`
- `default_database_path()`

The `flipper-diag history` command reads recent results. It initializes an empty database if needed but does not run any network tests.

## Resource and durability notes

The initial implementation uses SQLite from the Python standard library. WAL mode, retention/rotation, flash write amplification, backup/restore, and power-loss behavior have not yet been tuned or validated on Flipper One. Do not claim target-device durability until measured on the actual storage stack.
