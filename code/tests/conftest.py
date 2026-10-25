"""Pytest configuration for Shomei test suite.

Handles graceful test skipping when confidential competition datasets
are not present in public/open-source repository checkouts.
"""

from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_DIR = REPO_ROOT / "dataset"

DATASET_DEPENDENT_MODULES = {
    "test_classifier",
    "test_correlation",
    "test_data_loader",
    "test_decision",
    "test_discovery",
    "test_evidence",
    "test_identity",
    "test_multimodal",
    "test_output",
    "test_policy",
    "test_precision_regression",
    "test_sql_engine",
    "test_steps",
}


def pytest_runtest_setup(item):
    if not DATASET_DIR.exists():
        module_name = item.module.__name__ if hasattr(item, "module") else ""
        short_mod = module_name.split(".")[-1]
        if short_mod in DATASET_DEPENDENT_MODULES:
            pytest.skip("Competition dataset not present in open-source checkout")
