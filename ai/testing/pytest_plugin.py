"""Pytest plugin that records test results to the stability database."""

import logging
import os

try:
    from ai.testing import get_test_intel
except ImportError:
    get_test_intel = None

logger = logging.getLogger("ai.testing.pytest_plugin")


def pytest_runtest_makereport(item, call):
    """Record test results after each test execution."""
    if get_test_intel is None:
        return

    if call.when != "call":
        return

    try:
        test_id = f"{item.module.__name__}::{item.name}"
        intel = get_test_intel()
        intel.record_result(
            test_id=test_id,
            passed=call.excinfo is None,
            duration=call.stop - call.start,
            worker=os.environ.get("PYTEST_XDIST_WORKER", "main"),
        )
    except Exception as e:
        logger.debug(f"Test result recording skipped: {e}")
