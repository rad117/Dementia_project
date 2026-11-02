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

Open **Safety monitor** in the clinician dashboard and press *Run demo scenario*,
or `curl -X POST localhost:8000/monitoring/demo`. It replays an unattended stove
followed by a fall using short demo thresholds.

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

## Limitations

Thresholds in `CareState` are conservative defaults and must be tuned to the person's routine. No detection accuracy has been measured in this repository; treat any figure quoted in the original materials as unverified.
