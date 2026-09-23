import pytest

import backend.db as db_module
from backend import seed
from backend.services.auth import issue_token


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    # Route handlers call db.* without an explicit db_path, so they always
    # hit the module-level default -- point that at a throwaway file per
    # test instead of the real dev DB. Was previously duplicated across
    # test_assessments_v2.py/test_demo_auth.py; centralized here.
    test_db_path = tmp_path / "test.db"
    monkeypatch.setattr(db_module, "DB_PATH", test_db_path)
    db_module.init_db(test_db_path)
    # main.py's lifespan (which calls seed.run() after db.init_db()) does
    # not reliably fire under a plain TestClient(app) instantiation in this
    # test style -- seed explicitly so every test starts with the same
    # known patients/clinician seed.run() would otherwise provide.
    seed.run()


@pytest.fixture
def clinician_token():
    return issue_token("clinician", "dr-sharma")


@pytest.fixture
def participant_token():
    return issue_token("participant", "CA-1001")


@pytest.fixture
def clinician_headers(clinician_token):
    return {"Authorization": f"Bearer {clinician_token}"}


@pytest.fixture
def participant_headers(participant_token):
    return {"Authorization": f"Bearer {participant_token}"}
