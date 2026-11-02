"""
Core Detection Pipeline - V2 (Phone Camera & CCTV Ready)
Supports multiple camera sources:
  1. Built-in webcam (camera_id=0)
  2. USB camera connected to phone/laptop
  3. Phone as USB camera (via USB cable)
  4. Phone WiFi camera (IP camera mode)
  5. CCTV stream (RTSP/HTTP - for later)
"""

import cv2
import numpy as np
from ultralytics import YOLO
import mediapipe as mp
from collections import defaultdict
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Optional, Dict, List
import threading

class CameraSource:
    """Flexible camera input handler"""
    
    def __init__(self, source_type: str, source_address: str = "0"):
        """
        Args:
            source_type: "usb_camera", "phone_usb", "phone_wifi", "rtsp", "http"
            source_address: Camera ID (0, 1...) or IP address
        """
        self.source_type = source_type
        self.source_address = source_address
        self.cap = None
        self.setup_camera()
    
    def setup_camera(self):
        """Setup camera based on source type"""
        
        if self.source_type == "usb_camera":
            # Local USB camera (camera_id = 0, 1, 2, etc.)
            camera_id = int(self.source_address)
            print(f"📷 Connecting to USB Camera {camera_id}...")
            self.cap = cv2.VideoCapture(camera_id)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
        elif self.source_type == "phone_usb":
            # Phone connected via USB cable
            # Phone appears as camera_id (usually 1 if laptop has built-in camera at 0)
            camera_id = int(self.source_address)
            print(f"📱 Connecting to Phone (USB) at Camera ID {camera_id}...")
            print("   Make sure phone is in USB camera mode (not MTP)")
            self.cap = cv2.VideoCapture(camera_id)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
        elif self.source_type == "phone_wifi":
            # Phone WiFi camera (requires IP camera app on phone)
            # Example: "http://192.168.1.100:8080/video"
            print(f"📱 Connecting to Phone WiFi Camera at {self.source_address}...")
            print("   Make sure IP Camera app is running on phone")
            self.cap = cv2.VideoCapture(self.source_address)
            
        elif self.source_type == "rtsp":
            # CCTV or IP camera via RTSP
            # Example: "rtsp://admin:password@192.168.1.100:554/stream1"
            print(f"📹 Connecting to CCTV (RTSP) at {self.source_address}...")
            self.cap = cv2.VideoCapture(self.source_address)
            
        elif self.source_type == "http":
            # HTTP MJPEG stream
            # Example: "http://192.168.1.100:8080/video"
            print(f"📹 Connecting to IP Camera (HTTP) at {self.source_address}...")
            self.cap = cv2.VideoCapture(self.source_address)
        
        # Verify connection
        if not self.cap or not self.cap.isOpened():
            raise Exception(f"Failed to connect to camera: {self.source_type} {self.source_address}")
        
        print(f"✅ Camera connected successfully!")
    
    def read_frame(self):
        """Get next frame from camera"""
        ret, frame = self.cap.read()
        if not ret:
            print("⚠️  Failed to read frame from camera")
            return None
        return frame
    
    def release(self):
        """Close camera connection"""
        if self.cap:
            self.cap.release()


class DetectionPipelineV2:
    """Updated detection pipeline with flexible camera support"""
    
    def __init__(self, 
                 camera_source: str = "usb_camera",
                 camera_address: str = "0",
                 skip_frames: int = 15):
        """
        Args:
            camera_source: Type of camera ("usb_camera", "phone_usb", "phone_wifi", "rtsp", "http")
            camera_address: Camera ID or URL
            skip_frames: Process every Nth frame (for efficiency)
        """
        self.camera_source = CameraSource(camera_source, camera_address)
        self.skip_frames = skip_frames
        self.frame_count = 0
        
        # Load models
        print("Loading YOLOv8-Nano...")
        self.yolo = YOLO("yolov8n.pt")
        
        print("Loading MediaPipe Pose...")
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,  # Lite
            smooth_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Activity tracking
        self.object_timings = defaultdict(lambda: None)
        self.person_location = None
        self.person_pose = None
        self.falling = False
        
        print("✅ Detection pipeline ready!")
    
    def detect_objects(self, frame):
        """YOLOv8 detection"""
        results = self.yolo(frame, conf=0.4, device=0)
        
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
                    self.person_location = self._classify_location([x1, y1, x2, y2], frame.shape)
                
                for appliance, yolo_id in appliance_classes.items():
                    if cls_id == yolo_id:
                        objects["appliances"].append({
                            "type": appliance,
                            "confidence": conf,
                            "bbox": [x1, y1, x2, y2]
                        })
                        self.object_timings[appliance] = datetime.now()
        
        return objects
    
    def detect_pose(self, frame):
        """MediaPipe pose estimation"""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)
        
        pose_data = {
            "detected": results.pose_landmarks is not None,
            "keypoints": [],
            "activity": "idle"
        }
        
        if results.pose_landmarks:
            h, w, _ = frame.shape
            for idx, lm in enumerate(results.pose_landmarks.landmark):
                if idx in [11, 12, 13, 14, 15, 16]:
                    pose_data["keypoints"].append({
                        "id": idx,
                        "x": lm.x * w,
                        "y": lm.y * h,
                        "confidence": lm.visibility
                    })
            
            pose_data["activity"] = self._classify_pose(results.pose_landmarks)
            self.person_pose = pose_data
        
        return pose_data
    
    def _classify_location(self, bbox, frame_shape):
        """Classify person location"""
        h, w = frame_shape[:2]
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) // 2
        
        if center_x < w // 3:
            return "left"
        elif center_x < 2 * w // 3:
            return "center"
        else:
            return "right"
    
    def _classify_pose(self, landmarks):
        """Classify pose (standing/sitting/lying)"""
        try:
            left_shoulder = landmarks[11]
            right_shoulder = landmarks[12]
            left_hip = landmarks[23]
            right_hip = landmarks[24]
            
            shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
            hip_y = (left_hip.y + right_hip.y) / 2
            
            if abs(shoulder_y - hip_y) < 0.15:
                self.falling = True
                return "lying_down"
            else:
                self.falling = False
            
            if shoulder_y < hip_y - 0.1:
                return "standing"
            else:
                return "sitting"
        except:
            return "unknown"
    
    def process_frame(self, frame):
        """Process single frame"""
        self.frame_count += 1
        
        if self.frame_count % self.skip_frames != 0:
            return None
        
        objects = self.detect_objects(frame)
        pose = self.detect_pose(frame)
        
        event = {
            "timestamp": datetime.now().isoformat(),
            "frame_id": self.frame_count,
            "person_detected": len(objects["people"]) > 0,
            "person_location": self.person_location,
            "person_activity": pose["activity"],
            "falling": self.falling,
            "objects": objects["appliances"]
        }
        
        return event
    
    def run_continuous(self, 
                      output_file: str = "events.jsonl",
                      max_frames: int = None,
                      display: bool = True):
        """
        Run continuous detection
        
        Args:
            output_file: Where to save events
            max_frames: Stop after N frames
            display: Show live video feed
        """
        print(f"\n{'='*60}")
        print(f"📱 CONTINUOUS DETECTION - {self.camera_source.source_type.upper()}")
        print(f"{'='*60}")
        print(f"Saving to: {output_file}")
        print(f"Press 'q' to stop\n")
        
        frame_count = 0
        with open(output_file, 'w') as f:
            try:
                while True:
                    frame = self.camera_source.read_frame()
                    if frame is None:
                        break
                    
                    event = self.process_frame(frame)
                    if event:
                        f.write(json.dumps(event) + '\n')
                        f.flush()
                        
                        # Display status
                        print(f"Frame {event['frame_id']:5d} | "
                              f"Person: {str(event['person_detected']):5s} | "
                              f"Activity: {event['person_activity']:12s} | "
                              f"Location: {str(event['person_location']):8s} | "
                              f"Objects: {len(event['objects'])}")
                    
                    # Show frame
                    if display:
                        cv2.imshow("CARE-VLM Detection", frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                    
                    frame_count += 1
                    if max_frames and frame_count >= max_frames:
                        break
                        
            except KeyboardInterrupt:
                print("\n⚠️  Interrupted by user")
            finally:
                self.camera_source.release()
                cv2.destroyAllWindows()
                print(f"\n✅ Captured {frame_count} frames")
                print(f"Events saved to {output_file}")


# Example usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera-type", 
                       choices=["usb_camera", "phone_usb", "phone_wifi", "rtsp", "http"],
                       default="usb_camera",
                       help="Type of camera input")
    parser.add_argument("--camera-address", 
                       type=str, 
                       default="0",
                       help="Camera ID (0,1,2...) or URL")
    parser.add_argument("--skip-frames", 
                       type=int, 
                       default=15,
                       help="Skip N frames for speed")
    parser.add_argument("--output", 
                       type=str, 
                       default="events.jsonl",
                       help="Output file for events")
    parser.add_argument("--max-frames", 
                       type=int, 
                       default=None,
                       help="Max frames to process")
    
    args = parser.parse_args()
    
    # Examples:
    # python core_pipeline_v2.py --camera-type usb_camera --camera-address 0
    # python core_pipeline_v2.py --camera-type phone_usb --camera-address 1
    # python core_pipeline_v2.py --camera-type phone_wifi --camera-address "http://192.168.1.100:8080/video"
    # python core_pipeline_v2.py --camera-type rtsp --camera-address "rtsp://192.168.1.100:554/stream1"
    
    pipeline = DetectionPipelineV2(
        camera_source=args.camera_type,
        camera_address=args.camera_address,
        skip_frames=args.skip_frames
    )
    
    pipeline.run_continuous(
        output_file=args.output,
        max_frames=args.max_frames
    )
