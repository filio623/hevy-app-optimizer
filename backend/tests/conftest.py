import pytest

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "serial: mark test to run sequentially"
    ) 