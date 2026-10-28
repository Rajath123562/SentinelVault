# HOTFIX — Data and Resource Inventory

**Project Name**: HOTFIX Privacy-by-Design Analytics Gateway  
**Team ID**: UG 59  
**Track**: Privacy by Design — Unlock Data Without Exposing It  
**Current Phase**: Phase 1 Foundation  
**Version**: 1.0.0

---

## 1. Official Dataset Inspection Results

In accordance with **Rule 1 (Inspect before editing)** and **Rule 3 (Do not invent official resources)**, the workspace was audited for the synthetic health-record and financial-transaction datasets referenced in the Track 4 challenge.

### 1.1 Finding
* **Official Datasets Present in Workspace**: **None**.
* **Searched Locations**: Repository root, parent directories, and subdirectories for `.csv`, `.parquet`, `.json`, `.sqlite`, and `.tsv` files.
* **Status**: `UNAVAILABLE / NOT PRESENT IN WORKSPACE`.

### 1.2 Anti-Invention Commitment
To preserve absolute integrity:
* No column names, schema definitions, categorical distributions, or sample values have been fabricated and claimed to represent the official hackathon datasets.
* Privacy-unit definitions (e.g., patient-level vs. visit-level, customer-level vs. transaction-level) remain formally **unspecified** until official challenge documentation is provided.
* No clipping ranges, global sensitivity parameters, or contribution bounds have been arbitrarily selected for production logic.

---

## 2. Test Fixture Inventory (Unit Testing Only)

To enable automated unit testing of data-loading interfaces without inventing mock domain data, a single, isolated test fixture is maintained:

* **File Location**: `backend/tests/fixtures/sample_dataset_stub.json`
* **Purpose**: Verifies that JSON parsing, dictionary unpacking, and serialization routines function deterministically.
* **Is Official Dataset**: **NO** (`"is_official_dataset": false`).
* **Content Schema**:
  ```json
  {
    "__comment": "TEST FIXTURE ONLY: Fabricated dummy records for unit testing structure. NOT official hackathon data.",
    "is_official_dataset": false,
    "fixture_purpose": "unit-test-data-pipeline-contracts",
    "records": [
      {
        "mock_id": "TEST-001",
        "mock_category": "A",
        "mock_metric": 10.5
      },
      {
        "mock_id": "TEST-002",
        "mock_category": "B",
        "mock_metric": 22.0
      }
    ]
  }
  ```

---

## 3. Planned Dataset Adapter Architecture (Phase 2 Interface)

When official datasets are provided, they will be registered through a validated dataset adapter interface:

```python
# Planned Interface for Phase 2 (backend/app/adapters/dataset_adapter.py)
class DatasetAdapterInterface:
    def load_schema(self, dataset_path: str) -> dict:
        """Inspects metadata, column types, and null counts without dumping microdata."""
        raise NotImplementedError

    def compute_contribution_bounds(self, user_id_col: str) -> dict:
        """Calculates empirical user contribution frequencies once privacy unit is known."""
        raise NotImplementedError

    def get_clipping_bounds(self, column_name: str) -> tuple[float, float]:
        """Retrieves verified clipping bounds per official specification."""
        raise NotImplementedError
```

No analytical query will be executed against raw datasets until this adapter is implemented and linked with the Phase 3 differential privacy accountant.
