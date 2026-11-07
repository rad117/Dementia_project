"""Try the pose tier on your own webcam: python scripts/camera_check.py

Stand, sit, then lie down / crouch low in front of the camera while it runs.
macOS asks for camera permission for your terminal the first time. Frames are
analysed in memory and never saved.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2  # noqa: E402

from monitoring.pose_observer import PoseObserver  # noqa: E402

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    sys.exit("Camera not available. Allow camera access for your terminal in System Settings > Privacy & Security > Camera.")
pose = PoseObserver()
print("Running for ~40 s (one reading every ~4 s). Ctrl+C to stop.")
end = time.time() + 40
try:
    while time.time() < end:
        frames = []
        for _ in range(8):
            ok, f = cap.read()
            if ok:
                frames.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
            time.sleep(0.5)
        o = pose.observe(frames)
        print(f"person={o['person_present']!s:5} posture={o['posture']:9} on_floor={o['on_floor']!s:5} "
              f"motion={o['motion']:6} fall={o['fall_in_progress']} descent={o['sudden_descent']}")
finally:
    cap.release()
