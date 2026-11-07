#!/usr/bin/env bash
# Downloads MediaPipe's small pose model (~6 MB) used by the camera safety monitor.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p monitoring/models
curl -fSL -o monitoring/models/pose_landmarker_lite.task \
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task
echo "saved monitoring/models/pose_landmarker_lite.task"
