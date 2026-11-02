"""
nurse_server.py
---------------
Nurse-mode monitoring.

  phone browser --POST jpeg--> clip buffer --> NurseObserver (structured obs)
                                                     |
                                               CareState (temporal rules)
                                                     |
                                          risk events -> console, JSONL, phone

Only risk events are surfaced. Raw observations still go to observations.jsonl
so you can audit why a decision was made, but they are not shown by default.

Run:
    python nurse_server.py --port 5000
"""

import argparse
import json
import threading
import time
from collections import deque
from datetime import datetime

import cv2
import numpy as np
from flask import Flask, request, jsonify
from ultralytics import YOLO

from nurse_observer import NurseObserver
from care_state import CareState


LEVEL_ICON = {"CRITICAL": "!!!", "HIGH": "!!", "MEDIUM": "!", "LOW": " "}


class NurseMonitor:
    def __init__(self, clip_len=8, fps=2.0, gap_s=6.0, demo=False):
        print("Loading YOLO gate ...")
        self.yolo = YOLO("yolov8n.pt")
        self.observer = NurseObserver()
        self.state = CareState.demo() if demo else CareState()
        if demo:
            print("DEMO MODE -- short thresholds, not for real use")

        self.clip_len = clip_len
        self.fps = fps
        self.gap_s = gap_s

        self.buffer = deque(maxlen=clip_len)
        self.lock = threading.Lock()
        self.busy = False

        self.frames_received = 0
        self.clips_analysed = 0
        self.last_run = 0.0
        self.alerts = deque(maxlen=100)
        self.last_obs = {}

    # ------------------------------------------------------------------

    def add_frame(self, bgr):
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        with self.lock:
            self.buffer.append(rgb)
            self.frames_received += 1
            ready = len(self.buffer) == self.clip_len
            clip = list(self.buffer) if ready else None

        if not ready or self.busy:
            return
        if time.time() - self.last_run < self.gap_s:
            return

        threading.Thread(target=self._analyse, args=(clip,), daemon=True).start()

    def _analyse(self, clip):
        self.busy = True
        try:
            obs = self.observer.observe(clip, fps=self.fps)
            events = self.state.update(obs)

            self.last_run = time.time()
            self.clips_analysed += 1
            self.last_obs = obs

            with open("observations.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "at": datetime.now().isoformat(timespec="seconds"),
                    "clip": self.clips_analysed,
                    **{k: v for k, v in obs.items() if not k.startswith("_")},
                    "latency_s": obs.get("_latency_s"),
                }, ensure_ascii=False) + "\n")

            if events:
                with open("alerts.jsonl", "a", encoding="utf-8") as f:
                    for e in events:
                        f.write(json.dumps(e.to_dict(), ensure_ascii=False) + "\n")

                for e in events:
                    self.alerts.appendleft(e.to_dict())
                    print(f"\n{LEVEL_ICON[e.level]} [{e.level}] {e.summary}")
                    print(f"    why:  {e.evidence}")
                    print(f"    do:   {e.action}\n")
            else:
                print(f"clip {self.clips_analysed:4d}  ok  "
                      f"({obs.get('posture')}, {obs.get('activity')})  "
                      f"{obs.get('_latency_s')}s")

        except Exception as ex:
            print(f"analysis error: {ex}")
        finally:
            self.busy = False


# ----------------------------------------------------------------------

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
monitor: NurseMonitor = None


PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CARE-VLM</title><style>
body{font-family:system-ui,sans-serif;background:#0d0d0f;color:#eaeaea;margin:0;padding:14px}
video{width:100%;border-radius:10px;background:#000}
button{width:100%;padding:14px;margin-top:8px;border:0;border-radius:10px;font-size:16px;font-weight:600}
#start{background:#2e7d32;color:#fff}#stop{background:#b71c1c;color:#fff}
.row{display:flex;justify-content:space-between;padding:6px 2px;font-size:13px;color:#9a9a9a}
.alert{margin-top:8px;padding:11px;border-radius:9px;font-size:14px;line-height:1.45}
.CRITICAL{background:#4a0d0d;border-left:5px solid #ff3b30}
.HIGH{background:#4a2c0d;border-left:5px solid #ff9500}
.MEDIUM{background:#3d3a12;border-left:5px solid #ffd60a}
.lvl{font-weight:700;font-size:11px;letter-spacing:.06em}
.act{color:#b9b9b9;font-size:13px;margin-top:4px}
#ok{padding:11px;background:#14361b;border-left:5px solid #34c759;border-radius:9px;font-size:14px}
</style></head><body>
<video id="v" playsinline autoplay muted></video>
<button id="start" onclick="go()">START MONITORING</button>
<button id="stop" onclick="halt()" disabled>STOP</button>
<div class="row"><span id="n">0 frames</span><span id="c">0 checks</span></div>
<div id="feed"><div id="ok">Not started.</div></div>
<script>
const v=document.getElementById('v'),cv=document.createElement('canvas'),cx=cv.getContext('2d');
let on=false,t1=null,t2=null;
async function cam(){try{v.srcObject=await navigator.mediaDevices.getUserMedia(
{video:{facingMode:'environment',width:{ideal:640},height:{ideal:480}},audio:false});return 1}
catch(e){document.getElementById('feed').innerHTML='<div id="ok">Camera blocked: '+e.message+'</div>';return 0}}
async function go(){if(!v.srcObject&&!(await cam()))return;on=true;
start.disabled=true;stop.disabled=false;t1=setInterval(send,500);t2=setInterval(poll,4000);poll();}
function send(){if(!on||!v.videoWidth)return;cv.width=v.videoWidth;cv.height=v.videoHeight;
cx.drawImage(v,0,0);cv.toBlob(b=>{if(!b)return;const f=new FormData();f.append('frame',b,'f.jpg');
fetch('/frame',{method:'POST',body:f}).then(r=>r.json()).then(d=>{
document.getElementById('n').textContent=d.frames+' frames';
document.getElementById('c').textContent=d.clips+' checks';}).catch(()=>{});},'image/jpeg',0.7);}
function poll(){fetch('/alerts').then(r=>r.json()).then(d=>{
const f=document.getElementById('feed');
if(!d.alerts.length){f.innerHTML='<div id="ok">Nothing needing attention.</div>';return;}
f.innerHTML=d.alerts.slice(0,6).map(a=>
'<div class="alert '+a.level+'"><div class="lvl">'+a.level+' &middot; '+a.at.slice(11)+
'</div><div>'+a.summary+'</div><div class="act">'+a.action+'</div></div>').join('');
}).catch(()=>{});}
function halt(){on=false;clearInterval(t1);clearInterval(t2);start.disabled=false;stop.disabled=true;}
cam();
</script></body></html>"""


@app.route("/")
def index():
    return PAGE, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/frame", methods=["POST"])
def frame():
    if "frame" not in request.files:
        return jsonify({"status": "error"}), 400
    img = cv2.imdecode(
        np.frombuffer(request.files["frame"].read(), np.uint8), cv2.IMREAD_COLOR
    )
    if img is None:
        return jsonify({"status": "error"}), 400
    monitor.add_frame(img)
    return jsonify({
        "status": "ok",
        "frames": monitor.frames_received,
        "clips": monitor.clips_analysed,
    }), 200


@app.route("/alerts")
def alerts():
    return jsonify({
        "alerts": list(monitor.alerts),
        "state": monitor.state.status(),
    }), 200


@app.route("/observation")
def observation():
    """Raw last observation -- for debugging why an alert did or didn't fire."""
    return jsonify(monitor.last_obs), 200


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--clip-len", type=int, default=8)
    ap.add_argument("--fps", type=float, default=2.0)
    ap.add_argument("--gap", type=float, default=6.0)
    ap.add_argument("--demo", action="store_true",
                    help="short thresholds for live demonstration")
    args = ap.parse_args()

    monitor = NurseMonitor(clip_len=args.clip_len, fps=args.fps,
                           gap_s=args.gap, demo=args.demo)
    print(f"\nNurse mode on 0.0.0.0:{args.port}")
    print("alerts.jsonl / observations.jsonl\n")
    app.run(host="0.0.0.0", port=args.port, threaded=True)