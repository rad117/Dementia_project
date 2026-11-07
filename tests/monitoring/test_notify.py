import time

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from monitoring import notify, store
from monitoring.notify import Notifier, valid_phone

@pytest.fixture
def client():
    return TestClient(app)


ENV = {"TWILIO_ACCOUNT_SID": "ACtest", "TWILIO_AUTH_TOKEN": "tok",
       "TWILIO_SMS_FROM": "+15550001111", "TWILIO_WHATSAPP_FROM": "whatsapp:+14155238886"}

FALL = {"level": "CRITICAL", "kind": "fall_event", "summary": "A fall was observed.",
        "evidence": "posture=lying, location=kitchen", "action": "Attend immediately.", "at": "x"}
MEDIUM = {**FALL, "level": "MEDIUM", "kind": "unsteady"}


class Recorder:
    def __init__(self, code=201):
        self.calls, self.code = [], code

    def __call__(self, url, auth, data):
        self.calls.append((url, auth, data))
        return self.code, "{}"


def make(env=ENV, transport=None, **kw):
    t = transport or Recorder()
    return Notifier(transport=t, env=env, patient_name=lambda pid: "Asha", background=False, **kw), t


def test_phone_validation():
    assert valid_phone("+919876543210")
    assert not valid_phone("9876543210") and not valid_phone("+12") and not valid_phone("")


def test_live_critical_alert_texts_each_contact_on_their_channel():
    store.add_contact("CA-1001", "Ravi", "+919876543210", "sms")
    store.add_contact("CA-1001", "Meena", "+919811111111", "whatsapp")
    n, t = make()
    n.dispatch([FALL], patient_id="CA-1001")
    sent = {c[2]["To"]: c[2] for c in t.calls}
    assert set(sent) == {"+919876543210", "whatsapp:+919811111111"}
    assert sent["+919876543210"]["From"] == "+15550001111"
    assert sent["whatsapp:+919811111111"]["From"] == "whatsapp:+14155238886"
    body = sent["+919876543210"]["Body"]
    assert "Asha" in body and "A fall was observed." in body
    assert "kitchen" not in body                         # no evidence/location over SMS
    assert t.calls[0][1] == ("ACtest", "tok")
    assert {r["status"] for r in store.list_notifications()} == {"sent"}


def test_demo_alerts_never_message_anyone():
    store.add_contact("CA-1001", "Ravi", "+919876543210")
    n, t = make()
    n.dispatch([FALL], patient_id="CA-1001", source="demo")
    assert t.calls == [] and store.list_notifications() == []


def test_below_threshold_is_not_sent():
    store.add_contact("CA-1001", "Ravi", "+919876543210")
    n, t = make()
    n.dispatch([MEDIUM], patient_id="CA-1001")
    assert t.calls == []


def test_threshold_is_configurable():
    store.add_contact("CA-1001", "Ravi", "+919876543210")
    n, t = make(env={**ENV, "MONITORING_NOTIFY_MIN_LEVEL": "MEDIUM"})
    n.dispatch([MEDIUM], patient_id="CA-1001")
    assert len(t.calls) == 1


def test_no_credentials_is_a_logged_dry_run():
    store.add_contact("CA-1001", "Ravi", "+919876543210")
    n, t = make(env={})
    n.dispatch([FALL], patient_id="CA-1001")
    assert t.calls == []
    assert [r["status"] for r in store.list_notifications()] == ["dry_run"]


def test_failure_is_logged_not_raised():
    store.add_contact("CA-1001", "Ravi", "+919876543210")
    n, _ = make(transport=Recorder(code=401))
    n.dispatch([FALL], patient_id="CA-1001")
    row = store.list_notifications()[0]
    assert row["status"] == "failed" and "401" in row["detail"]

    def boom(*a):
        raise ConnectionError("offline")
    n2, _ = make(transport=boom)
    n2._last_sent.clear()
    n2.dispatch([FALL], patient_id="CA-1001")
    assert "offline" in store.list_notifications()[0]["detail"]


def test_cooldown_stops_repeat_texts():
    store.add_contact("CA-1001", "Ravi", "+919876543210")
    now = [0.0]
    n, t = make(clock=lambda: now[0])
    n.dispatch([FALL], patient_id="CA-1001")
    now[0] = 100
    n.dispatch([FALL], patient_id="CA-1001")
    assert len(t.calls) == 1
    now[0] = 700
    n.dispatch([FALL], patient_id="CA-1001")
    assert len(t.calls) == 2


def test_no_contacts_no_messages():
    n, t = make()
    n.dispatch([FALL], patient_id="CA-1001")
    assert t.calls == []


def test_service_live_ingest_triggers_notification(monkeypatch):
    from monitoring.service import get_service
    store.add_contact("CA-1001", "Ravi", "+919876543210")
    rec = Recorder()
    monkeypatch.setattr(notify, "_notifier", Notifier(transport=rec, env=ENV,
                                                      patient_name=lambda p: "Asha"))
    get_service().ingest_observation({"person_present": True, "fall_in_progress": True},
                                     patient_id="CA-1001")
    for _ in range(50):
        if rec.calls:
            break
        time.sleep(0.05)
    assert len(rec.calls) == 1


# --------------------------------------------------------------- HTTP API

def test_contacts_api_roundtrip(client, clinician_headers):
    r = client.post("/monitoring/contacts", headers=clinician_headers, json={
        "patient_id": "CA-1001", "name": "Ravi", "phone": "+919876543210", "channel": "whatsapp"})
    assert r.status_code == 201
    cid = r.json()["id"]
    assert client.get("/monitoring/contacts?patient_id=CA-1001",
                      headers=clinician_headers).json()[0]["name"] == "Ravi"
    assert client.delete(f"/monitoring/contacts/{cid}", headers=clinician_headers).status_code == 200
    assert client.get("/monitoring/contacts", headers=clinician_headers).json() == []


def test_contacts_api_rejects_bad_input(client, clinician_headers, participant_headers):
    base = {"patient_id": "CA-1001", "name": "Ravi", "phone": "+919876543210"}
    assert client.post("/monitoring/contacts", headers=clinician_headers,
                       json={**base, "phone": "98765"}).status_code == 422
    assert client.post("/monitoring/contacts", headers=clinician_headers,
                       json={**base, "patient_id": "NOPE"}).status_code == 404
    assert client.post("/monitoring/contacts", json=base).status_code in (401, 403)
    assert client.post("/monitoring/contacts", headers=participant_headers,
                       json=base).status_code in (401, 403)


def test_test_message_endpoint_is_a_dry_run_without_credentials(client, clinician_headers, monkeypatch):
    for k in ENV:
        monkeypatch.delenv(k, raising=False)
    notify.reset_notifier()
    cid = client.post("/monitoring/contacts", headers=clinician_headers, json={
        "patient_id": "CA-1001", "name": "Ravi", "phone": "+919876543210"}).json()["id"]
    r = client.post(f"/monitoring/contacts/{cid}/test", headers=clinician_headers)
    assert r.json()["status"] == "dry_run"
    assert client.get("/monitoring/notifications/status", headers=clinician_headers).json()["configured"] is False


# ------------------------------------------------- queue, retries, cooldown

class Scripted:
    """Replies with each code in turn; the last one repeats."""

    def __init__(self, *codes):
        self.codes, self.calls = list(codes), []

    def __call__(self, url, auth, data):
        self.calls.append(data)
        code = self.codes.pop(0) if len(self.codes) > 1 else self.codes[0]
        if isinstance(code, Exception):
            raise code
        return code, "{}"


def test_temporary_failure_is_retried_until_it_is_sent():
    store.add_contact("CA-1001", "Ravi", "+919876543210")
    now = [0.0]
    t = Scripted(500, ConnectionError("offline"), 201)
    n, _ = make(transport=t, clock=lambda: now[0])
    n.dispatch([FALL], patient_id="CA-1001")
    assert len(t.calls) == 1 and store.next_queued_time() == 30.0
    now[0] = 10; n._drain_once(); assert len(t.calls) == 1   # not due yet
    now[0] = 31; n._drain_once(); assert len(t.calls) == 2
    now[0] = 160; n._drain_once(); assert len(t.calls) == 3
    assert store.next_queued_time() is None
    assert [r["status"] for r in store.list_notifications()] == ["sent", "failed", "failed"]


def test_permanent_failure_is_not_retried():
    store.add_contact("CA-1001", "Ravi", "+919876543210")
    t = Scripted(400)
    n, _ = make(transport=t)
    n.dispatch([FALL], patient_id="CA-1001")
    assert len(t.calls) == 1 and store.next_queued_time() is None


def test_gives_up_after_the_last_retry():
    store.add_contact("CA-1001", "Ravi", "+919876543210")
    now = [0.0]
    t = Scripted(500)
    n, _ = make(transport=t, clock=lambda: now[0], env={**ENV, "MONITORING_NOTIFY_MAX_AGE_S": "99999"})
    n.dispatch([FALL], patient_id="CA-1001")
    for step in (31, 152, 453, 999):
        now[0] = step
        n._drain_once()
    assert len(t.calls) == 4 and store.next_queued_time() is None


def test_failed_send_does_not_start_the_cooldown():
    store.add_contact("CA-1001", "Ravi", "+919876543210")
    now = [0.0]
    t = Scripted(400, 201)
    n, _ = make(transport=t, clock=lambda: now[0])
    n.dispatch([FALL], patient_id="CA-1001")
    now[0] = 60
    n.dispatch([FALL], patient_id="CA-1001")
    assert len(t.calls) == 2 and store.list_notifications()[0]["status"] == "sent"


def test_cooldown_is_per_contact():
    """One person's failure must not stop the other, or re-text the one who got it."""
    store.add_contact("CA-1001", "Ravi", "+919876543210")
    store.add_contact("CA-1001", "Meena", "+919811111111")
    now = [0.0]

    def transport(url, auth, data):
        calls.append(data["To"])
        return (400 if data["To"] == "+919811111111" and len(calls) <= 2 else 201), "{}"

    calls = []
    n, _ = make(transport=transport, clock=lambda: now[0])
    n.dispatch([FALL], patient_id="CA-1001")
    now[0] = 60
    n.dispatch([FALL], patient_id="CA-1001")
    assert calls == ["+919876543210", "+919811111111", "+919811111111"]


def test_no_contacts_at_the_time_does_not_block_a_later_contact():
    n, t = make()
    n.dispatch([FALL], patient_id="CA-1001")
    store.add_contact("CA-1001", "Ravi", "+919876543210")
    n.dispatch([FALL], patient_id="CA-1001")
    assert len(t.calls) == 1


def test_repeat_alert_while_one_is_queued_is_not_doubled():
    store.add_contact("CA-1001", "Ravi", "+919876543210")
    now = [0.0]
    t = Scripted(500, 201)
    n, _ = make(transport=t, clock=lambda: now[0])
    n.dispatch([FALL], patient_id="CA-1001")
    now[0] = 5
    n.dispatch([FALL], patient_id="CA-1001")
    now[0] = 40
    n._drain_once()
    assert len(t.calls) == 2


def test_queued_message_survives_a_restart():
    store.add_contact("CA-1001", "Ravi", "+919876543210")
    now = [0.0]
    first, _ = make(transport=Scripted(500), clock=lambda: now[0])
    first.dispatch([FALL], patient_id="CA-1001")

    now[0] = 40
    t = Recorder()
    restarted, _ = make(transport=t, clock=lambda: now[0])      # empty memory, same database
    restarted.resume()
    assert len(t.calls) == 1 and store.next_queued_time() is None


def test_message_too_old_to_be_useful_is_dropped_and_logged():
    cid = store.add_contact("CA-1001", "Ravi", "+919876543210")["id"]
    store.enqueue_notification(patient_id="CA-1001", contact_id=cid, alert_kind="fall_event",
                               body="old", created=0.0)
    t = Recorder()
    n, _ = make(transport=t, clock=lambda: 5000.0)
    n.resume()
    assert t.calls == [] and store.next_queued_time() is None
    assert store.list_notifications()[0]["status"] == "expired"


def test_removing_a_contact_cancels_their_queued_messages():
    cid = store.add_contact("CA-1001", "Ravi", "+919876543210")["id"]
    now = [0.0]
    t = Scripted(500, 201)
    n, _ = make(transport=t, clock=lambda: now[0])
    n.dispatch([FALL], patient_id="CA-1001")
    store.delete_contact(cid)
    now[0] = 40
    n._drain_once()
    assert len(t.calls) == 1 and store.next_queued_time() is None


def test_contact_is_reread_immediately_before_sending():
    store.enqueue_notification(patient_id="CA-1001", contact_id=999, alert_kind="fall_event",
                               body="x", created=0.0)
    t = Recorder()
    n, _ = make(transport=t, clock=lambda: 1.0)
    n.resume()
    assert t.calls == [] and store.list_notifications()[0]["status"] == "skipped"


def test_background_worker_delivers_and_stops():
    store.add_contact("CA-1001", "Ravi", "+919876543210")
    rec = Recorder()
    n = Notifier(transport=rec, env=ENV, patient_name=lambda p: "Asha")
    n.dispatch([FALL], patient_id="CA-1001")
    for _ in range(100):
        if rec.calls and not n._worker_alive:
            break
        time.sleep(0.02)
    assert len(rec.calls) == 1 and n._worker_alive is False


def test_observation_can_be_read_for_one_patient(client, clinician_headers):
    from monitoring.service import get_service
    svc = get_service()
    svc.ingest_observation({"person_present": True, "posture": "sitting"}, patient_id="CA-1001")
    svc.ingest_observation({"person_present": True, "posture": "standing"}, patient_id="CA-1002")
    get = lambda q: client.get(f"/monitoring/observation{q}", headers=clinician_headers).json()
    assert get("?patient_id=CA-1001")["observation"]["posture"] == "sitting"
    assert get("")["observation"]["posture"] == "standing"
    assert get("?patient_id=NOPE") == {}
