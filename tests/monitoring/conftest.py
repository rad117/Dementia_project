import pytest

import backend.db as db_module
from monitoring import service as service_module
from monitoring import store


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Throwaway DB and a fresh service singleton for every test."""
    path = tmp_path / "test_monitoring.db"
    monkeypatch.setattr(db_module, "DB_PATH", path)
    db_module.init_db(path)
    store.init_db(path)
    service_module.reset_service()
    yield
    service_module.reset_service()
