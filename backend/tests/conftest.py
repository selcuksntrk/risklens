import pytest
from app import config


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Mock model tests must never mutate the real budget or private reports."""
    monkeypatch.setattr(config, 'SCANS_DIR', tmp_path)
    monkeypatch.setattr(config, 'EXAMPLES_DIR', tmp_path / '_examples')
