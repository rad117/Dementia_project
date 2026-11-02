"""
CARE-VLM Browser Camera Server
Receives frames from phone browser camera via HTTP POST
Processes with YOLOv8 + VLM reasoning
"""

from flask import Flask, request, jsonify
import numpy as np
import cv2
import json
import threading
from datetime import datetime
from io import BytesIO
from PIL import Image
import sys

sys.path.insert(0, 'server')

from temporal_memory import TemporalMemory, EventBuffer
from vlm_reasoner import VLMReasoner, AlertSystem
from ultralytics import YOLO
import mediapipe as mp

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Global state
detection_enabled = True
frame_count = 0
frames_received = 0
last_frame_time = None
hazard_check_interval = 10

# Initialize YOLO
print("Loading YOLOv8-Nano...")
yolo = YOLO("yolov8n.pt")

# Initialize MediaPipe
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
alerts = AlertSystem(phone_number=None)  # Set phone number via config

# Tracking variables
person_location = None
falling = False
object_timings = {}

print("✅ Server ready!")
print("="*70)
print("Waiting for frames from phone browser camera...")
print("="*70)


def detect_objects(frame):
    """YOLOv8 detection"""
    results = yolo(frame, conf=0.4, device=0)
    
    objects = {
        "people": [],
        "appliances": [],
        "furniture": []
    }
    
    appliance_classes = {
        "stove": 79, "oven": 80, "microwave": 81,
        "fridge": 82, "refrigerator": 82
    }
    
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
            
            for appliance, yolo_id in appliance_classes.items():
                if cls_id == yolo_id:
                    objects["appliances"].append({
                        "type": appliance,
                        "confidence": conf,
                        "bbox": [x1, y1, x2, y2]
                    })
                    object_timings[appliance] = datetime.now()
    
    return objects


def detect_pose(frame):
    """MediaPipe pose estimation"""
    global falling
    
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(frame_rgb)
    
    pose_data = {
        "detected": results.pose_landmarks is not None,
        "activity": "idle"
    }
    
    if results.pose_landmarks:
        try:
            shoulder_y = (results.pose_landmarks.landmark[11].y + 
                         results.pose_landmarks.landmark[12].y) / 2
            hip_y = (results.pose_landmarks.landmark[23].y + 
                    results.pose_landmarks.landmark[24].y) / 2
            
            if abs(shoulder_y - hip_y) < 0.15:
                falling = True
                pose_data["activity"] = "lying_down"
            else:
                falling = False
                pose_data["activity"] = "standing" if shoulder_y < hip_y - 0.1 else "sitting"
        except:
            pose_data["activity"] = "unknown"
    
    return pose_data


def process_frame(frame):
    """Process single frame"""
    global frame_count, person_location
    
    frame_count += 1
    
    # Detect objects
    objects = detect_objects(frame)
    
    # Detect pose
    pose = detect_pose(frame)
    
    # Classify location
    h, w = frame.shape[:2]
    if objects["people"]:
        person = objects["people"][0]
        x1, y1, x2, y2 = person["bbox"]
        center_x = (x1 + x2) // 2
        
        if center_x < w // 3:
            person_location = "left"
        elif center_x < 2 * w // 3:
            person_location = "center"
        else:
            person_location = "right"
    
    # Create event
    event = {
        "timestamp": datetime.now().isoformat(),
        "frame_id": frame_count,
        "person_detected": len(objects["people"]) > 0,
        "person_location": person_location,
        "person_activity": pose["activity"],
        "falling": falling,
        "objects": objects["appliances"]
    }
    
    return event


def check_hazards():
    """Check for hazards using VLM"""
    recent_events = memory.get_recent_events(minutes=10)
    
    if not recent_events:
        return None
    
    # Get text summary
    summary = event_buffer.to_text()
    
    # Perform risk assessment
    context = {
        "location": recent_events[0].get("person_location", "unknown"),
        "activity": recent_events[0].get("person_activity", "unknown")
    }
    
    assessment = reasoner.assess_hazard(summary, recent_events, context)
    
    # Log hazard if risky
    if assessment["risk_score"] >= 50:
        memory.log_hazard(
            hazard_type=assessment["risk_level"],
            risk_score=assessment["risk_score"],
            description=assessment["reasoning"]
        )
    
    return assessment


@app.route('/', methods=['GET'])
def index():
    """Serve the phone camera HTML file"""
    try:
        with open('phone_camera.html', 'r') as f:
            return f.read(), 200, {'Content-Type': 'text/html'}
    except FileNotFoundError:
        return jsonify({'status': 'error', 'message': 'phone_camera.html not found'}), 404


@app.route('/phone_camera.html', methods=['GET'])
def phone_camera():
    """Serve the phone camera HTML file (direct route)"""
    try:
        with open('phone_camera.html', 'r') as f:
            return f.read(), 200, {'Content-Type': 'text/html'}
    except FileNotFoundError:
        return jsonify({'status': 'error', 'message': 'phone_camera.html not found'}), 404


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'frames_received': frames_received,
        'frames_processed': frame_count,
        'last_frame_time': str(last_frame_time)
    }), 200


@app.route('/frame', methods=['POST'])
def receive_frame():
    """Receive frame from phone browser camera"""
    global frames_received, last_frame_time, frame_count
    
    try:
        # Get frame from request
        if 'frame' not in request.files:
            return jsonify({'status': 'error', 'message': 'No frame in request'}), 400
        
        frame_file = request.files['frame']
        timestamp = request.form.get('timestamp', datetime.now().isoformat())
        fps = request.form.get('fps', '2')
        resolution = request.form.get('resolution', 'unknown')
        
        # Read frame
        frame_data = frame_file.read()
        nparr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'status': 'error', 'message': 'Invalid frame'}), 400
        
        frames_received += 1
        last_frame_time = datetime.now()
        
        # Process frame (skip some for speed)
        if frames_received % 3 == 0:  # Process every 3rd frame
            event = process_frame(frame)
            
            # Log event
            memory.log_event(event)
            event_buffer.add(event)
            
            # Check for hazards periodically
            if frame_count % hazard_check_interval == 0:
                assessment = check_hazards()
                
                # Display and send alert if hazard detected
                if assessment and assessment["action"] in ["alert", "emergency"]:
                    print(f"\n⚠️  ALERT: {assessment['action'].upper()}")
                    print(f"   Risk Score: {assessment['risk_score']}/100")
                    print(f"   Reason: {assessment['reasoning']}\n")
                    
                    # Generate alert
                    alert = alerts.generate_alert(assessment)
                    print(f"   Alert Message: {alert['message']}")
            
            # Display status every frame
            person = "✓" if event.get("person_detected") else "✗"
            activity = event.get("person_activity", "?")
            risk = "HIGH" if event.get("objects") and not event.get("person_detected") else "LOW"
            
            print(f"Frame {frame_count:6d} | Person: {person} | Activity: {activity:12s} | Risk: {risk} | Recv: {frames_received}")
        
        return jsonify({
            'status': 'success',
            'frames_received': frames_received,
            'frames_processed': frame_count,
            'message': 'Frame received and queued for processing'
        }), 200
    
    except Exception as e:
        print(f"Error processing frame: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/config', methods=['POST'])
def configure():
    """Configure alerts and settings"""
    try:
        data = request.get_json()
        
        if 'phone' in data:
            alerts.phone_number = data['phone']
            print(f"✅ SMS alerts configured: {data['phone']}")
        
        if 'email' in data:
            alerts.email = data['email']
            print(f"✅ Email alerts configured: {data['email']}")
        
        return jsonify({'status': 'success', 'message': 'Configuration updated'}), 200
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/status', methods=['GET'])
def status():
    """Get current system status"""
    try:
        recent_events = memory.get_recent_events(minutes=1)
        
        return jsonify({
            'status': 'running',
            'frames_received': frames_received,
            'frames_processed': frame_count,
            'recent_events': len(recent_events),
            'detection_enabled': detection_enabled,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 CARE-VLM Browser Camera Server")
    print("="*70)
    print("Server running on: http://0.0.0.0:5000")
    print("\nPhone browser camera server ready!")
    print("\nHow to use:")
    print("1. Open phone_camera.html on phone browser")
    print("2. Enter Server IP: (this PC's IP):5000")
    print("3. Click START to begin streaming")
    print("\nServer will display detection status in real-time")
    print("="*70 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
