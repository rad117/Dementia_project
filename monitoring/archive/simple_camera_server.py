"""
CARE-VLM Simplified Browser Camera Server
Everything in one: HTML serving + frame reception + detection
"""

from flask import Flask, request, jsonify, send_file
import numpy as np
import cv2
from datetime import datetime
import sys
import os

sys.path.insert(0, 'server')

from temporal_memory import TemporalMemory, EventBuffer
from vlm_reasoner import VLMReasoner, AlertSystem
from ultralytics import YOLO
import mediapipe as mp

# Initialize Flask
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Global state
frame_count = 0
frames_received = 0
last_frame_time = None

# Load models
print("Loading YOLOv8-Nano...")
yolo = YOLO("yolov8n.pt")

print("Loading MediaPipe Pose...")
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=0,
    smooth_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Initialize memory and reasoning
print("Initializing temporal memory...")
memory = TemporalMemory(db_path="monitoring.db")
event_buffer = EventBuffer()

print("Loading VLM reasoner...")
reasoner = VLMReasoner(model_name="mistral")
alerts = AlertSystem(phone_number=None)

print("✅ All systems ready!\n")


def detect_objects(frame):
    """YOLOv8 detection"""
    results = yolo(frame, conf=0.4, device=0)
    objects = {"people": [], "appliances": [], "furniture": []}
    
    if results[0].boxes is not None:
        for box in results[0].boxes:
            cls_id = int(box.cls)
            conf = float(box.conf)
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            if cls_id == 0:  # Person
                objects["people"].append({
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2],
                    "center": [(x1+x2)//2, (y1+y2)//2]
                })
    
    return objects


def detect_pose(frame):
    """MediaPipe pose estimation"""
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(frame_rgb)
    
    pose_data = {"detected": results.pose_landmarks is not None, "activity": "idle"}
    
    if results.pose_landmarks:
        try:
            shoulder_y = (results.pose_landmarks.landmark[11].y + 
                         results.pose_landmarks.landmark[12].y) / 2
            hip_y = (results.pose_landmarks.landmark[23].y + 
                    results.pose_landmarks.landmark[24].y) / 2
            
            if abs(shoulder_y - hip_y) < 0.15:
                pose_data["activity"] = "lying_down"
            else:
                pose_data["activity"] = "standing" if shoulder_y < hip_y - 0.1 else "sitting"
        except:
            pose_data["activity"] = "unknown"
    
    return pose_data


@app.route('/')
def index():
    """Serve HTML page"""
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CARE-VLM Phone Camera</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
               min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 10px; }
        .container { background: white; border-radius: 15px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); 
                     padding: 20px; max-width: 500px; width: 100%; }
        .header { text-align: center; margin-bottom: 20px; color: #333; }
        .header h1 { font-size: 24px; margin-bottom: 5px; }
        #video { width: 100%; border-radius: 10px; background: #000; margin-bottom: 15px; transform: scaleX(-1); }
        .controls { display: flex; gap: 10px; margin-bottom: 15px; }
        button { flex: 1; padding: 12px 20px; border: none; border-radius: 8px; font-size: 14px; 
                 font-weight: bold; cursor: pointer; transition: all 0.3s; }
        #startBtn { background: #4CAF50; color: white; }
        #startBtn:hover { background: #45a049; }
        #stopBtn { background: #f44336; color: white; }
        .settings { background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
        .setting-item { margin-bottom: 12px; }
        label { display: block; font-size: 13px; color: #666; margin-bottom: 5px; font-weight: bold; }
        input, select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 5px; font-size: 13px; }
        .status { padding: 12px; border-radius: 5px; margin-bottom: 15px; font-size: 13px; }
        .status.success { background: #e8f5e9; color: #2e7d32; border-left: 4px solid #4CAF50; }
        .status.error { background: #ffebee; color: #c62828; border-left: 4px solid #f44336; }
        .stats { background: #f5f5f5; padding: 12px; border-radius: 8px; font-size: 12px; color: #666; }
        .stats-row { display: flex; justify-content: space-between; margin-bottom: 8px; }
        .info { background: #e3f2fd; border-left: 4px solid #2196F3; padding: 12px; border-radius: 5px; 
                font-size: 12px; color: #1565c0; line-height: 1.5; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📱 CARE-VLM Camera</h1>
            <p>Browser-Based Monitoring</p>
        </div>
        
        <video id="video" playsinline autoplay></video>
        
        <div class="settings">
            <div class="setting-item">
                <label for="fpsSelect">FPS:</label>
                <select id="fpsSelect">
                    <option value="1">1 FPS</option>
                    <option value="2" selected>2 FPS (Recommended)</option>
                    <option value="3">3 FPS</option>
                </select>
            </div>
        </div>
        
        <div class="controls">
            <button id="startBtn" onclick="startCapture()">▶ START</button>
            <button id="stopBtn" onclick="stopCapture()" disabled>⏹ STOP</button>
        </div>
        
        <div id="status" class="status success" style="display:none;"></div>
        
        <div class="stats">
            <div class="stats-row"><span>Status:</span><span id="statusText">Ready</span></div>
            <div class="stats-row"><span>Frames Sent:</span><span id="frameCount">0</span></div>
            <div class="stats-row"><span>FPS:</span><span id="fpsDisplay">0</span></div>
            <div class="stats-row"><span>Data Sent:</span><span id="dataSent">0 MB</span></div>
        </div>
        
        <div class="info">
            ℹ️ Phone captures frames and sends to server for AI processing.
        </div>
    </div>

    <script>
        let video = document.getElementById('video');
        let canvas = document.createElement('canvas');
        let ctx = canvas.getContext('2d');
        let isStreaming = false;
        let framesSent = 0;
        let dataSentMB = 0;
        
        async function requestCamera() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: 'environment', width: { ideal: 640 }, height: { ideal: 480 } },
                    audio: false
                });
                video.srcObject = stream;
                return true;
            } catch (error) {
                alert('Camera access denied: ' + error.message);
                return false;
            }
        }
        
        function showStatus(message, type = 'success') {
            const statusDiv = document.getElementById('status');
            statusDiv.textContent = message;
            statusDiv.className = 'status ' + type;
            statusDiv.style.display = 'block';
        }
        
        async function startCapture() {
            if (!video.srcObject) {
                const hasCamera = await requestCamera();
                if (!hasCamera) return;
            }
            
            isStreaming = true;
            framesSent = 0;
            dataSentMB = 0;
            
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            document.getElementById('statusText').textContent = '🔴 Streaming...';
            showStatus('✅ Streaming started!', 'success');
            
            const fps = parseInt(document.getElementById('fpsSelect').value);
            const intervalTime = 1000 / fps;
            
            const captureInterval = setInterval(() => {
                if (!isStreaming) {
                    clearInterval(captureInterval);
                    return;
                }
                sendFrame();
            }, intervalTime);
        }
        
        function sendFrame() {
            try {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                
                if (canvas.width === 0) return;
                
                ctx.scale(-1, 1);
                ctx.drawImage(video, -canvas.width, 0);
                ctx.scale(-1, 1);
                
                canvas.toBlob((blob) => {
                    if (!blob) return;
                    
                    const formData = new FormData();
                    formData.append('frame', blob, 'frame.jpg');
                    formData.append('timestamp', new Date().toISOString());
                    
                    fetch('/frame', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => {
                        if (response.ok) {
                            framesSent++;
                            dataSentMB += blob.size / (1024 * 1024);
                            
                            if (framesSent % 5 === 0) {
                                document.getElementById('frameCount').textContent = framesSent;
                                document.getElementById('dataSent').textContent = dataSentMB.toFixed(2) + ' MB';
                            }
                        }
                    })
                    .catch(error => console.error('Send error:', error));
                }, 'image/jpeg', 0.7);
            } catch (error) {
                console.error('Capture error:', error);
            }
        }
        
        function stopCapture() {
            isStreaming = false;
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
            document.getElementById('statusText').textContent = '⏸ Stopped';
            showStatus(`✅ Stopped. Sent ${framesSent} frames.`, 'success');
        }
        
        window.addEventListener('load', () => {
            requestCamera();
        });
    </script>
</body>
</html>'''
    return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/frame', methods=['POST'])
def receive_frame():
    """Receive and process frames"""
    global frames_received, last_frame_time, frame_count
    
    try:
        if 'frame' not in request.files:
            return jsonify({'status': 'error', 'message': 'No frame'}), 400
        
        frame_file = request.files['frame']
        frame_data = frame_file.read()
        nparr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'status': 'error'}), 400
        
        frames_received += 1
        last_frame_time = datetime.now()
        
        # Process every 3rd frame
        if frames_received % 3 == 0:
            frame_count += 1
            
            # Detect
            objects = detect_objects(frame)
            pose = detect_pose(frame)
            
            # Create event
            event = {
                "timestamp": datetime.now().isoformat(),
                "frame_id": frame_count,
                "person_detected": len(objects["people"]) > 0,
                "person_activity": pose["activity"],
                "objects": objects["appliances"]
            }
            
            # Log
            memory.log_event(event)
            event_buffer.add(event)
            
            # Display
            person = "✓" if event.get("person_detected") else "✗"
            activity = event.get("person_activity", "?")
            risk = "HIGH" if len(objects["appliances"]) > 0 and not event.get("person_detected") else "LOW"
            
            print(f"Frame {frame_count:6d} | Person: {person} | Activity: {activity:12s} | Risk: {risk} | Recv: {frames_received}")
        
        return jsonify({'status': 'ok', 'frames': frames_received}), 200
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/status', methods=['GET'])
def status():
    """Get status"""
    return jsonify({
        'status': 'running',
        'frames_received': frames_received,
        'frames_processed': frame_count,
        'timestamp': datetime.now().isoformat()
    }), 200


if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 CARE-VLM SIMPLIFIED BROWSER CAMERA SERVER")
    print("="*70)
    print("Server: http://0.0.0.0:5000")
    print("Tunnel: https://clanking-hence-matching.ngrok-free.dev")
    print("\nOn iPhone Safari:")
    print("1. Open: https://clanking-hence-matching.ngrok-free.dev")
    print("2. Allow camera permission")
    print("3. Click START")
    print("="*70 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
