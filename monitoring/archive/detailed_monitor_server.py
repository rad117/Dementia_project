"""
detailed_monitor_server.py
--------------------------
Fine-grained monitoring pipeline.

  phone browser  --POST jpeg-->  Flask
                                   |
                          rolling clip buffer (8 frames @ ~2 fps)
                                   |
                          YOLO gate: is anything worth describing?
                                   |
                          Qwen2.5-VL: free-text detailed description
                                   |
                          JSONL log + console

The VLM takes ~1.5-3 s per clip on an A5000, so it does NOT run on every
clip. The gate decides. Everything the VLM says is written to
descriptions.jsonl so you can inspect exactly what it saw.

Run:
    python detailed_monitor_server.py --port 5000
Then point the phone browser page at this server and press START.
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

from vlm_describer import VLMDescriber


# ----------------------------------------------------------------------
# COCO class IDs -- these are the REAL ones. Note there is no "stove"
# class in COCO; an oven/burner has to come from `oven`, or from the VLM
# description, which is one reason the VLM matters.
# ----------------------------------------------------------------------
COCO = {
    0: "person",
    39: "bottle",
    41: "cup",
    43: "knife",
    44: "spoon",
    45: "bowl",
    56: "chair",
    57: "couch",
    59: "bed",
    60: "dining table",
    62: "tv",
    68: "microwave",
    69: "oven",
    70: "toaster",
    71: "sink",
    72: "refrigerator",
    74: "clock",
}

# Objects whose presence makes a clip worth describing in detail
HAZARD_CONTEXT = {68, 69, 70, 71, 72, 43, 59}   # microwave, oven, toaster, sink, fridge, knife, bed


class DetailedMonitor:
    def __init__(self, clip_len=8, capture_fps=2.0, gate_conf=0.35,
                 min_seconds_between_vlm=6.0, log_path="descriptions.jsonl"):
        print("Loading YOLOv8 gate ...")
        self.yolo = YOLO("yolov8n.pt")

        self.describer = VLMDescriber()

        self.clip_len = clip_len
        self.capture_fps = capture_fps
        self.gate_conf = gate_conf
        self.min_gap = min_seconds_between_vlm
        self.log_path = log_path

        self.buffer = deque(maxlen=clip_len)
        self.lock = threading.Lock()

        self.frames_received = 0
        self.clips_described = 0
        self.last_vlm_time = 0.0
        self.last_description = ""
        self.busy = False

    # ------------------------------------------------------------------

    def add_frame(self, bgr_frame):
        """Store a frame; trigger a description if the buffer is full and gated."""
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)

        with self.lock:
            self.buffer.append(rgb)
            self.frames_received += 1
            ready = len(self.buffer) == self.clip_len
            clip = list(self.buffer) if ready else None

        if not ready or self.busy:
            return

        if time.time() - self.last_vlm_time < self.min_gap:
            return

        gate = self.gate(bgr_frame)
        if not gate["describe"]:
            return

        # Run the VLM off the request thread so frame intake never blocks
        threading.Thread(
            target=self._describe, args=(clip, gate), daemon=True
        ).start()

    # ------------------------------------------------------------------

    def gate(self, bgr_frame) -> dict:
        """
        Cheap YOLO pass deciding whether this clip deserves the VLM.
        Returns the detected labels so they can be logged alongside the
        description for cross-checking.
        """
        results = self.yolo(bgr_frame, conf=self.gate_conf, verbose=False)

        labels = []
        person = False
        hazard_ctx = False

        boxes = results[0].boxes
        if boxes is not None:
            for box in boxes:
                cid = int(box.cls)
                name = COCO.get(cid, f"class_{cid}")
                labels.append(name)
                if cid == 0:
                    person = True
                if cid in HAZARD_CONTEXT:
                    hazard_ctx = True

        # Describe if: a person is present, OR a hazard-relevant object is
        # visible without a person (the unattended case), OR nothing at all
        # is detected but we haven't described in a while (catches the
        # "person collapsed and YOLO missed them" failure mode).
        stale = time.time() - self.last_vlm_time > 45
        describe = person or hazard_ctx or stale

        return {
            "describe": describe,
            "labels": sorted(set(labels)),
            "person": person,
            "hazard_context": hazard_ctx,
        }

    # ------------------------------------------------------------------

    def _describe(self, clip, gate):
        self.busy = True
        try:
            if self.last_description:
                result = self.describer.compare_to_previous(
                    clip, self.last_description, fps=self.capture_fps
                )
            else:
                result = self.describer.describe_clip(clip, fps=self.capture_fps)

            self.last_vlm_time = time.time()
            self.last_description = result["description"]
            self.clips_described += 1

            record = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "clip_id": self.clips_described,
                "yolo_labels": gate["labels"],
                "person_detected": gate["person"],
                "description": result["description"],
                "vlm_latency_s": result["latency_s"],
                "n_frames": result["n_frames"],
            }

            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            print(f"\n[clip {self.clips_described}] "
                  f"{record['timestamp']}  ({result['latency_s']}s)")
            print(f"  yolo: {', '.join(gate['labels']) or 'nothing'}")
            print(f"  {result['description']}\n")

        except Exception as e:
            print(f"VLM error: {e}")
        finally:
            self.busy = False


# ----------------------------------------------------------------------

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
monitor: DetailedMonitor = None


CAPTURE_PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CARE-VLM Capture</title>
<style>
body{font-family:system-ui,sans-serif;background:#111;color:#eee;margin:0;padding:16px}
video{width:100%;border-radius:8px;background:#000}
button{width:100%;padding:14px;margin-top:10px;border:0;border-radius:8px;
       font-size:16px;font-weight:600}
#start{background:#2e7d32;color:#fff}#stop{background:#c62828;color:#fff}
.row{display:flex;justify-content:space-between;padding:6px 0;
     border-bottom:1px solid #333;font-size:14px}
#desc{margin-top:14px;padding:12px;background:#1c1c1c;border-radius:8px;
      font-size:14px;line-height:1.5;min-height:60px}
</style></head><body>
<video id="v" playsinline autoplay muted></video>
<button id="start" onclick="go()">START</button>
<button id="stop" onclick="halt()" disabled>STOP</button>
<div class="row"><span>Frames sent</span><span id="n">0</span></div>
<div class="row"><span>Clips described</span><span id="c">0</span></div>
<div id="desc">Press START.</div>
<script>
const v=document.getElementById('v');
const cv=document.createElement('canvas');const cx=cv.getContext('2d');
let on=false,n=0,timer=null;

async function cam(){
  try{
    v.srcObject=await navigator.mediaDevices.getUserMedia({
      video:{facingMode:'environment',width:{ideal:640},height:{ideal:480}},
      audio:false});
    return true;
  }catch(e){document.getElementById('desc').textContent='Camera blocked: '+e.message;
    return false;}
}

async function go(){
  if(!v.srcObject && !(await cam()))return;
  on=true;n=0;
  start.disabled=true;stop.disabled=false;
  timer=setInterval(send,500);          // 2 fps, matches --fps default
  setInterval(poll,4000);
}

function send(){
  if(!on||!v.videoWidth)return;
  cv.width=v.videoWidth;cv.height=v.videoHeight;
  cx.drawImage(v,0,0);
  cv.toBlob(b=>{
    if(!b)return;
    const fd=new FormData();fd.append('frame',b,'f.jpg');
    fetch('/frame',{method:'POST',body:fd})
      .then(r=>r.json())
      .then(d=>{n=d.frames;document.getElementById('n').textContent=n;
                document.getElementById('c').textContent=d.clips_described;})
      .catch(()=>{});
  },'image/jpeg',0.7);
}

function poll(){
  fetch('/latest').then(r=>r.json()).then(d=>{
    if(d.last_description)document.getElementById('desc').textContent=d.last_description;
  }).catch(()=>{});
}

function halt(){on=false;clearInterval(timer);
  start.disabled=false;stop.disabled=true;}

cam();
</script></body></html>"""


@app.route("/", methods=["GET"])
def index():
    return CAPTURE_PAGE, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/frame", methods=["POST"])
def frame():
    if "frame" not in request.files:
        return jsonify({"status": "error", "message": "no frame"}), 400

    data = request.files["frame"].read()
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return jsonify({"status": "error", "message": "decode failed"}), 400

    monitor.add_frame(img)
    return jsonify({
        "status": "ok",
        "frames": monitor.frames_received,
        "clips_described": monitor.clips_described,
    }), 200


@app.route("/latest", methods=["GET"])
def latest():
    return jsonify({
        "frames_received": monitor.frames_received,
        "clips_described": monitor.clips_described,
        "last_description": monitor.last_description,
    }), 200


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--clip-len", type=int, default=8,
                    help="frames per clip sent to the VLM")
    ap.add_argument("--fps", type=float, default=2.0,
                    help="rate the phone is sending frames at")
    ap.add_argument("--gap", type=float, default=6.0,
                    help="minimum seconds between VLM calls")
    args = ap.parse_args()

    monitor = DetailedMonitor(
        clip_len=args.clip_len,
        capture_fps=args.fps,
        min_seconds_between_vlm=args.gap,
    )

    print(f"\nListening on 0.0.0.0:{args.port}")
    print(f"Descriptions -> descriptions.jsonl\n")
    app.run(host="0.0.0.0", port=args.port, threaded=True)