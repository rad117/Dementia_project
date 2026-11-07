"""Alert notifications to a patient's family by SMS / WhatsApp, through Twilio.

Design rules (this texts real people about a person's safety):

* Only LIVE alerts at or above ``MONITORING_NOTIFY_MIN_LEVEL`` (default HIGH).
  Simulated/demo alerts never message anyone.
* Contacts are stored per patient (``guardian_contacts``). No contacts, no message.
* Without Twilio credentials nothing is sent: the attempt is logged as
  ``dry_run`` so the flow can be tested end to end.
* Messages go through a queue saved in the database, so a restart does not lose
  them. Pending messages resume at startup (``resume_pending``). A crash in the
  middle of a send can repeat that one message, which is better than losing it.
* Temporary failures (network, HTTP 408/429/5xx) are retried with a growing delay.
  Permanent ones (bad number, bad credentials) are logged and not retried.
  Every attempt is logged in ``notification_log``, never silently dropped.
* A message older than ``MONITORING_NOTIFY_MAX_AGE_S`` is dropped and logged as
  ``expired``, because a fall text that arrives hours late only misleads.
* A contact removed while a message is queued gets nothing: the contact is
  re-read immediately before each send.
* The cooldown is per contact and starts only after a delivery, so one person's
  failed send does not silence their next alert.
* Sending can never raise into monitoring.
* Messages are short and carry the patient's first name only, no evidence text
  or location detail (SMS is not a private channel).

Environment:
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
    TWILIO_SMS_FROM        e.g. +15551234567
    TWILIO_WHATSAPP_FROM   e.g. whatsapp:+14155238886 (sandbox) or an approved sender
    MONITORING_NOTIFY_MIN_LEVEL   CRITICAL | HIGH | MEDIUM | LOW   (default HIGH)
    MONITORING_NOTIFY_COOLDOWN_S  default 600
    MONITORING_NOTIFY_MAX_AGE_S   default 1800
"""

import os
import re
import threading
import time

import httpx

from monitoring import store
from monitoring.settings import env_float

LEVEL_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
E164 = re.compile(r"^\+[1-9]\d{7,14}$")
TWILIO_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
RETRY_DELAYS_S = (30.0, 120.0, 300.0)
MAX_ATTEMPTS = len(RETRY_DELAYS_S) + 1
RETRYABLE_HTTP = {408, 429}


def valid_phone(phone: str) -> bool:
    return bool(E164.match(phone or ""))


def default_transport(url: str, auth: tuple[str, str], data: dict) -> tuple[int, str]:
    r = httpx.post(url, auth=auth, data=data, timeout=10.0)
    return r.status_code, r.text


class Notifier:
    def __init__(self, transport=default_transport, env=None, clock=time.time,
                 patient_name=None, background: bool = True):
        self._transport = transport
        self._env = env if env is not None else os.environ
        self._clock = clock
        self._patient_name = patient_name or _patient_first_name
        self._background = background
        self._last_sent: dict[tuple, float] = {}
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._worker_alive = False

    # -- config ----------------------------------------------------------
    @property
    def configured(self) -> bool:
        e = self._env
        return bool(e.get("TWILIO_ACCOUNT_SID") and e.get("TWILIO_AUTH_TOKEN")
                    and (e.get("TWILIO_SMS_FROM") or e.get("TWILIO_WHATSAPP_FROM")))

    def status(self) -> dict:
        return {"configured": self.configured,
                "min_level": self._min_level(),
                "sms": bool(self._env.get("TWILIO_SMS_FROM")),
                "whatsapp": bool(self._env.get("TWILIO_WHATSAPP_FROM"))}

    def _min_level(self) -> str:
        lvl = (self._env.get("MONITORING_NOTIFY_MIN_LEVEL") or "HIGH").upper()
        return lvl if lvl in LEVEL_RANK else "HIGH"

    # -- public ----------------------------------------------------------
    def dispatch(self, alerts: list[dict], *, patient_id: str | None, source: str = "live") -> None:
        """Called after new alerts are saved. Queues the messages and returns."""
        if source != "live" or not patient_id or not alerts:
            return
        floor = LEVEL_RANK[self._min_level()]
        due = [a for a in alerts if LEVEL_RANK.get(a["level"], 0) >= floor]
        if not due:
            return
        try:
            self._enqueue(due, patient_id)
        except Exception as exc:  # never take monitoring down
            self._log_error(patient_id, exc)
        self._kick()

    def resume(self) -> None:
        """Start sending anything still queued from before a restart."""
        if store.next_queued_time() is not None:
            self._kick()

    def send_test(self, contact: dict) -> dict:
        text = "Memora test message: alerts for this person will be sent to this number."
        result, _ = self._deliver(contact, text, patient_id=contact["patient_id"], kind="test")
        return result

    # -- queue -----------------------------------------------------------
    def _enqueue(self, alerts, patient_id):
        contacts = store.list_contacts(patient_id)
        now = self._clock()
        for alert in alerts:
            text = self._compose(alert, patient_id)
            for c in contacts:
                if self._cooling_down(patient_id, alert["kind"], c["id"], now):
                    continue
                if store.is_notification_queued(c["id"], alert["kind"]):
                    continue
                store.enqueue_notification(patient_id=patient_id, contact_id=c["id"],
                                           alert_kind=alert["kind"], body=text, created=now)

    def _cooling_down(self, patient_id, kind, contact_id, now) -> bool:
        with self._lock:
            last = self._last_sent.get((patient_id, kind, contact_id))
        cooldown = env_float("MONITORING_NOTIFY_COOLDOWN_S", 600.0, env=self._env)
        return last is not None and now - last < cooldown

    def _drain_once(self) -> None:
        now = self._clock()
        max_age = env_float("MONITORING_NOTIFY_MAX_AGE_S", 1800.0, env=self._env)
        for row in store.due_notifications(now):
            base = dict(patient_id=row["patient_id"], contact_id=row["contact_id"],
                        alert_kind=row["alert_kind"])
            contact = store.get_contact(row["contact_id"])
            if contact is None:
                store.log_notification(**base, channel="-", status="skipped",
                                       detail="contact was removed before sending")
                store.remove_queued_notification(row["id"])
                continue
            if now - row["created"] > max_age:
                store.log_notification(**base, channel=contact["channel"], status="expired",
                                       detail="too old to send")
                store.remove_queued_notification(row["id"])
                continue
            result, retryable = self._deliver(contact, row["body"],
                                              patient_id=row["patient_id"], kind=row["alert_kind"])
            attempts = row["attempts"] + 1
            if result["status"] in ("sent", "dry_run"):
                with self._lock:
                    self._last_sent[(row["patient_id"], row["alert_kind"], row["contact_id"])] = now
                store.remove_queued_notification(row["id"])
            elif retryable and attempts < MAX_ATTEMPTS:
                store.reschedule_notification(row["id"], attempts=attempts,
                                              next_try=now + RETRY_DELAYS_S[attempts - 1])
            else:
                store.remove_queued_notification(row["id"])

    def _safe_drain(self) -> None:
        try:
            self._drain_once()
        except Exception as exc:
            self._log_error(None, exc)

    def _kick(self) -> None:
        if not self._background:
            self._safe_drain()
            return
        with self._lock:
            self._wake.set()
            if self._worker_alive:
                return
            self._worker_alive = True
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        while True:
            self._wake.clear()
            self._safe_drain()
            with self._lock:
                try:
                    next_at = store.next_queued_time()
                except Exception:
                    next_at = None
                if next_at is None and not self._wake.is_set():
                    self._worker_alive = False
                    return
            if next_at is not None:
                self._wake.wait(timeout=max(0.5, min(next_at - self._clock(), 60.0)))

    # -- sending ---------------------------------------------------------
    def _compose(self, alert: dict, patient_id: str) -> str:
        name = self._patient_name(patient_id) or "your family member"
        return (f"Memora {alert['level']} alert for {name}: {alert['summary']} "
                f"{alert['action']}")[:600]

    def _deliver(self, contact: dict, text: str, *, patient_id, kind) -> tuple[dict, bool]:
        """Try one send and log it. Returns (result, is it worth retrying)."""
        channel = contact["channel"]
        base = dict(patient_id=patient_id, contact_id=contact["id"], channel=channel, alert_kind=kind)
        if not self.configured:
            store.log_notification(**base, status="dry_run", detail="Twilio not configured; nothing sent")
            return {"status": "dry_run"}, False
        e = self._env
        sender = e.get("TWILIO_WHATSAPP_FROM") if channel == "whatsapp" else e.get("TWILIO_SMS_FROM")
        if not sender:
            store.log_notification(**base, status="failed", detail=f"no sender configured for {channel}")
            return {"status": "failed", "detail": f"no sender configured for {channel}"}, False
        to = f"whatsapp:{contact['phone']}" if channel == "whatsapp" else contact["phone"]
        try:
            code, body = self._transport(TWILIO_URL.format(sid=e["TWILIO_ACCOUNT_SID"]),
                                         (e["TWILIO_ACCOUNT_SID"], e["TWILIO_AUTH_TOKEN"]),
                                         {"From": sender, "To": to, "Body": text})
        except Exception as exc:
            store.log_notification(**base, status="failed", detail=f"{type(exc).__name__}: {exc}")
            return {"status": "failed", "detail": str(exc)}, True
        ok = 200 <= code < 300
        store.log_notification(**base, status="sent" if ok else "failed",
                               detail=None if ok else f"HTTP {code}: {body}")
        return {"status": "sent" if ok else "failed", "http": code}, (code >= 500 or code in RETRYABLE_HTTP)

    @staticmethod
    def _log_error(patient_id, exc) -> None:
        try:
            store.log_notification(patient_id=patient_id, contact_id=None, channel="-",
                                   alert_kind=None, status="error", detail=repr(exc))
        except Exception:
            pass


def _patient_first_name(patient_id: str) -> str | None:
    try:
        from backend import db
        row = db.get_patient_row(patient_id)
        return (row or {}).get("name", "").split(" ")[0] or None
    except Exception:
        return None


_notifier: Notifier | None = None
_lock = threading.Lock()


def get_notifier() -> Notifier:
    global _notifier
    with _lock:
        if _notifier is None:
            _notifier = Notifier()
        return _notifier


def reset_notifier() -> None:
    global _notifier
    with _lock:
        _notifier = None


def resume_pending() -> None:
    """Called at startup. Must never stop the application from booting."""
    try:
        get_notifier().resume()
    except Exception:
        pass
