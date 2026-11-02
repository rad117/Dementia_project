import pytest

import backend.db as db_module
from backend import seed
from backend.services.auth import issue_token
from monitoring import service as service_module
from monitoring import store


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Throwaway DB and a fresh service singleton for every test."""
    path = tmp_path / "test_monitoring.db"
    monkeypatch.setattr(db_module, "DB_PATH", path)
    db_module.init_db(path)
    seed.run()
    store.init_db(path)
    service_module.reset_service()
    yield
    service_module.reset_service()


@pytest.fixture
def clinician_headers():
    return {"Authorization": f"Bearer {issue_token('clinician', 'dr-sharma')}"}


@pytest.fixture
def participant_headers():
    return {"Authorization": f"Bearer {issue_token('participant', 'CA-1001')}"}
