"""Alert notifications to a patient's family by SMS / WhatsApp, through Twilio.

Design rules (this texts real people about a person's safety):

* Only LIVE alerts at or above ``MONITORING_NOTIFY_MIN_LEVEL`` (default HIGH).
  Simulated/demo alerts never message anyone.
* Contacts are stored per patient (``guardian_contacts``). No contacts, no message.
* Without Twilio credentials nothing is sent: the attempt is logged as
  ``dry_run`` so the flow can be tested end to end.
* Sending happens on a background thread and can never raise into monitoring.
  A failed send is logged (``notification_log``), never silently dropped.
* The same alert kind for the same patient is not re-sent within a cooldown, on
  top of CareState's own muting.
* Messages are short and carry the patient's first name only, no evidence text
  or location detail (SMS is not a private channel).

Environment:
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
    TWILIO_SMS_FROM        e.g. +15551234567
    TWILIO_WHATSAPP_FROM   e.g. whatsapp:+14155238886 (sandbox) or an approved sender
    MONITORING_NOTIFY_MIN_LEVEL   CRITICAL | HIGH | MEDIUM | LOW   (default HIGH)
    MONITORING_NOTIFY_COOLDOWN_S  default 600
"""

import os
import re
import threading
import time

import httpx

from monitoring import store

LEVEL_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
E164 = re.compile(r"^\+[1-9]\d{7,14}$")
TWILIO_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


def valid_phone(phone: str) -> bool:
    return bool(E164.match(phone or ""))


def default_transport(url: str, auth: tuple[str, str], data: dict) -> tuple[int, str]:
    r = httpx.post(url, auth=auth, data=data, timeout=10.0)
    return r.status_code, r.text


class Notifier:
    def __init__(self, transport=default_transport, env=None, clock=time.monotonic,
                 patient_name=None, background: bool = True):
        self._transport = transport
        self._env = env if env is not None else os.environ
        self._clock = clock
        self._patient_name = patient_name or _patient_first_name
        self._background = background
        self._last_sent: dict[tuple, float] = {}
        self._lock = threading.Lock()

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

    def _cooldown(self) -> float:
        try:
            return float(self._env.get("MONITORING_NOTIFY_COOLDOWN_S", "600"))
        except ValueError:
            return 600.0

    # -- public ----------------------------------------------------------
    def dispatch(self, alerts: list[dict], *, patient_id: str | None, source: str = "live") -> None:
        """Called after new alerts are saved. Returns immediately."""
        if source != "live" or not patient_id or not alerts:
            return
        floor = LEVEL_RANK[self._min_level()]
        due = [a for a in alerts if LEVEL_RANK.get(a["level"], 0) >= floor]
        if not due:
            return
        if self._background:
            threading.Thread(target=self._safe_send, args=(due, patient_id), daemon=True).start()
        else:
            self._safe_send(due, patient_id)

    def send_test(self, contact: dict) -> dict:
        text = "Memora test message: alerts for this person will be sent to this number."
        return self._send_one(contact, text, patient_id=contact["patient_id"], kind="test")

    # -- internals -------------------------------------------------------
    def _safe_send(self, alerts, patient_id):
        try:
            contacts = store.list_contacts(patient_id)
            for alert in alerts:
                if not self._cooldown_ok(patient_id, alert["kind"]):
                    continue
                text = self._compose(alert, patient_id)
                for c in contacts:
                    self._send_one(c, text, patient_id=patient_id, kind=alert["kind"])
        except Exception as exc:  # never take monitoring down
            try:
                store.log_notification(patient_id=patient_id, contact_id=None, channel="-",
                                       alert_kind=None, status="error", detail=repr(exc))
            except Exception:
                pass

    def _cooldown_ok(self, patient_id, kind) -> bool:
        key, now = (patient_id, kind), self._clock()
        with self._lock:
            last = self._last_sent.get(key)
            if last is not None and now - last < self._cooldown():
                return False
            self._last_sent[key] = now
            return True

    def _compose(self, alert: dict, patient_id: str) -> str:
        name = self._patient_name(patient_id) or "your family member"
        return (f"Memora {alert['level']} alert for {name}: {alert['summary']} "
                f"{alert['action']}")[:600]

    def _send_one(self, contact: dict, text: str, *, patient_id, kind) -> dict:
        channel = contact["channel"]
        base = dict(patient_id=patient_id, contact_id=contact["id"], channel=channel, alert_kind=kind)
        if not self.configured:
            store.log_notification(**base, status="dry_run", detail="Twilio not configured; nothing sent")
            return {"status": "dry_run"}
        e = self._env
        sender = e.get("TWILIO_WHATSAPP_FROM") if channel == "whatsapp" else e.get("TWILIO_SMS_FROM")
        if not sender:
            store.log_notification(**base, status="failed", detail=f"no sender configured for {channel}")
            return {"status": "failed", "detail": f"no sender configured for {channel}"}
        to = f"whatsapp:{contact['phone']}" if channel == "whatsapp" else contact["phone"]
        try:
            code, body = self._transport(TWILIO_URL.format(sid=e["TWILIO_ACCOUNT_SID"]),
                                         (e["TWILIO_ACCOUNT_SID"], e["TWILIO_AUTH_TOKEN"]),
                                         {"From": sender, "To": to, "Body": text})
        except Exception as exc:
            store.log_notification(**base, status="failed", detail=f"{type(exc).__name__}: {exc}")
            return {"status": "failed", "detail": str(exc)}
        ok = 200 <= code < 300
        store.log_notification(**base, status="sent" if ok else "failed",
                               detail=None if ok else f"HTTP {code}: {body}")
        return {"status": "sent" if ok else "failed", "http": code}


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
