# Local data model

Status: initial implementation, schema version 2.

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

### inventory_baselines (schema v2)

| Column | Meaning |
|---|---|
| baseline_id | Locally generated UUID |
| name | Unique operator-defined baseline name |
| created_at | ISO-8601 UTC timestamp |
| inventory_json | Complete observed device inventory |

The current API and CLI can save, load, list and compare named baselines. Comparison logic is pure and offline: it identifies new/missing devices, address changes and duplicate IP observations. MAC addresses are used as the current identity key; devices without a usable MAC are rejected rather than silently matched by a potentially unstable IP. MAC randomization, spoofing, virtual interfaces and multi-homing can still cause false new/missing-device findings. A duplicate IP in a snapshot is therefore a warning requiring confirmation, not proof of an address conflict.

CLI input is a JSON array of observed devices, each with a `mac_address` and an `addresses` array. Example:

```json
[
  {"mac_address": "02:00:00:00:00:01", "addresses": ["192.0.2.10"]}
]
```

Example workflow:

```bash
flipper-diag baseline save --name office --input inventory.json
flipper-diag baseline compare --name office --input current-inventory.json
flipper-diag baseline list
```


## Migration policy

SQLite `PRAGMA user_version` tracks the schema version. Version 2 adds `inventory_baselines` without rewriting existing diagnostic runs. New migrations must be sequential and tested against:
1. an empty database;
2. a database at the immediately previous schema version;
3. a database with a newer version (must fail closed, never downgrade or rewrite).

Schema changes must preserve old results. The full result JSON remains the archival source for each run.

## Current API

- `initialize_database(path)`
- `save_result(path, result)`
- `list_results(path, limit=50)`
- `save_baseline(path, name, devices)`
- `load_baseline(path, name)`
- `list_baselines(path)`
- `default_database_path()`

The `flipper-diag history` command reads recent results. It initializes an empty database if needed but does not run any network tests.

## Resource and durability notes

The initial implementation uses SQLite from the Python standard library. On POSIX systems the database file is restricted to owner read/write permissions (0600); failure to change permissions is tolerated and must be checked on the target image. WAL mode, retention/rotation, flash write amplification, backup/restore, and power-loss behavior have not yet been tuned or validated on Flipper One. Do not claim target-device durability until measured on the actual storage stack.
