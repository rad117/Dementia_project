# Safety monitoring (CARE-VLM)

Camera-based safety monitoring for people living with dementia: falls, a stove
left on, taps left running, prolonged absence, night-time wandering, repeated
unfinished tasks. Built by the internship team's senior as **CARE-VLM**, and
merged into this platform as a built-in feature.

It is hazard and behaviour monitoring only. It does not diagnose, and it does
not classify faces or expressions.

## How it works

```
camera frames -> clip buffer -> NurseObserver (vision model, fixed JSON schema)
                                      |
                                CareState (temporal rules)
                                      |
                       risk alerts -> SQLite -> Safety monitor page
```

| File | Role |
|---|---|
| `care_state.py` | Rules engine. Remembers how long a heat source has been on, how long someone has been on the floor, repeated activities, etc. Pure Python, no heavy dependencies. Unchanged from the original. |
| `nurse_observer.py` | Vision model wrapper (Qwen2.5-VL). Turns a short clip into a structured observation. Heavy imports are lazy. |
| `service.py` | Glue: observations in, alerts out. Replaces the original Flask `nurse_server.py`. |
| `store.py` | SQLite tables `monitoring_alerts` / `monitoring_observations` in the same database as assessments. |
| `archive/` | The senior's original scripts, kept for reference and credit. Not used at runtime. |

## Two ways to feed it

1. **Structured observation** (no camera, no GPU): `POST /monitoring/observations`
   with the JSON schema from `nurse_observer.py`. This is what the tests use.
2. **Camera frames**: `POST /monitoring/frame` (multipart field `frame`, a JPEG).
   Needs `pip install -r monitoring/requirements.txt` and a GPU.
   If the packages are missing the endpoint answers `{"status":"unavailable"}`.

## Demo without hardware

Open **Safety monitor** in the clinician dashboard, pick a patient and run one
of the incident scenarios (stove left on then a fall, bathroom fall, night-time
wandering, tap left running, repeating an unfinished task). Each scenario is a
sequence of structured observations -- the same output the vision model
produces -- replayed through the real `CareState` rules with short demo
thresholds. Alerts are tagged "Simulated", linked to the patient, and appear on
the clinical overview and the patient's profile.

API: `GET /monitoring/scenarios`, then
`POST /monitoring/demo?scenario=bathroom_fall&patient_id=<id>` (clinician token
required). Re-running a scenario for the same patient replaces its earlier
alerts; `DELETE /monitoring/demo` clears all simulated alerts.

## Configuration

| Variable | Effect |
|---|---|
| `MONITORING_DEMO=1` | Use short demo thresholds for live monitoring (never in a real home). |
| `MONITORING_VLM_MODEL` | Vision model id (default `Qwen/Qwen2.5-VL-7B-Instruct`). |
| `MONITORING_DEVICE` | `cuda`, `mps` or `cpu` (default: auto). |

## What changed from the original

- Flask servers replaced by FastAPI routes (`backend/routes/monitoring.py`); one process serves everything.
- Alerts and observations go to SQLite instead of loose `.jsonl` files in the working directory.
- The unused YOLO "gate" and OpenCV dependency were dropped; frames are decoded with Pillow.
- Model device is chosen automatically instead of being hard-coded to CUDA.
- A failing model load is reported on the status endpoint instead of crashing the worker.
- Recorded `observations.jsonl`, `alerts.jsonl`, `descriptions.jsonl` and `monitoring.db` were not imported (they contain observations of a real person).
- The ~30 duplicate guides were not carried over; this README replaces them.

## Tiered camera pipeline (how it stays affordable)

Calling a large vision model every few seconds is ~14,400 calls per camera per
day. Instead the live path is tiered, cheapest first:

```
frame -> motion gate -> pose model (CPU) -> vision model (GPU, only when needed)
```

| Tier | File | Runs | Job |
|---|---|---|---|
| Motion gate | `motion_gate.py` | every frame | Skip clips while the scene is unchanged. Stays open while someone is on the floor or a stove/tap/door is flagged (a person lying still makes no motion), plus a 5-minute heartbeat. |
| Pose | `pose_observer.py` | every passing clip, CPU | Person present, standing/sitting/lying, fall and sudden-descent. MediaPipe; no per-call cost. |
| Vision model | `nurse_observer.py` via `tiered_observer.py` | on odd pose, else every `MONITORING_VLM_INTERVAL_S` (600 s) | Confirms a fall, reads stove/tap/door. Optional: without it, pose-only monitoring still detects falls. |

Between vision looks, pose-only observations carry the last stove/tap/door
reading forward so `CareState` timers keep counting.

Install: `pip install -r monitoring/requirements.txt` then
`scripts/download_pose_model.sh`. The light stack (mediapipe) is enough for
fall detection; torch/transformers are only for the vision model.

**Not yet validated:** pose thresholds are tested on synthetic poses and assume
a roughly side-on, wall-mounted camera. Real footage and the real vision model
have not been run end to end. Sway/unsteadiness is only set by the vision model.

## Family alerts by SMS / WhatsApp (Twilio)

Add family contacts per patient (patient profile, "Family alerts", or
`POST /monitoring/contacts`). When a **live** alert at or above
`MONITORING_NOTIFY_MIN_LEVEL` (default `HIGH`) is raised, each contact is texted.

- Simulated/demo alerts never send anything.
- Without Twilio credentials nothing is sent; attempts are logged as `dry_run`.
- Every attempt is logged (`GET /monitoring/notifications`): sent / failed / dry_run.
- Same alert kind for the same patient is not re-sent within `MONITORING_NOTIFY_COOLDOWN_S` (600).
- Messages carry the patient's first name, the summary and the action only. No evidence or location text, since SMS is not private.

| Variable | Meaning |
|---|---|
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | Twilio credentials (environment only, never in the repo) |
| `TWILIO_SMS_FROM` | Sending number, e.g. `+15551234567` |
| `TWILIO_WHATSAPP_FROM` | e.g. `whatsapp:+14155238886` (sandbox) or an approved sender |
| `MONITORING_NOTIFY_MIN_LEVEL` | `CRITICAL`, `HIGH` (default), `MEDIUM`, `LOW` |

Before real use: Twilio trial accounts only reach verified numbers; WhatsApp
needs the sandbox join or an approved sender; SMS to Indian numbers has its own
sender/template registration rules. Check Twilio's current requirements.
Families must consent to receiving alerts and to the camera.

## Limitations

Thresholds in `CareState` are conservative defaults and must be tuned to the person's routine. No detection accuracy has been measured in this repository; treat any figure quoted in the original materials as unverified.
