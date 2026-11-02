"""
Core Detection Pipeline
Runs YOLOv8-Nano + MediaPipe Pose continuously
Generates structured events for VLM reasoning
"""

import cv2
import numpy as np
from ultralytics import YOLO
import mediapipe as mp
from collections import defaultdict
from datetime import datetime, timedelta
import json
from pathlib import Path

class DetectionPipeline:
    """Lightweight detection pipeline for phone deployment"""
    
    def __init__(self, camera_id=0, skip_frames=15):
        """
        Args:
            camera_id: Webcam index (0 = default)
            skip_frames: Process every Nth frame (1-3 FPS target)
        """
        self.camera_id = camera_id
        self.skip_frames = skip_frames
        self.frame_count = 0
        
        # Load models
        print("Loading YOLOv8-Nano...")
        self.yolo = YOLO("yolov8n.pt")
        
        print("Loading MediaPipe Pose...")
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,  # Lite model
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
        
    def detect_objects(self, frame):
        """YOLOv8 detection"""
        results = self.yolo(frame, conf=0.4, device=0)
        
        objects = {
            "people": [],
            "appliances": [],
            "furniture": []
        }
        
        # Map YOLO classes to categories
        appliance_classes = {
            "stove": 79, "oven": 80, "microwave": 81, 
            "fridge": 82, "refrigerator": 82
        }
        furniture_classes = {
            "chair": 56, "bed": 59, "table": 60,
            "door": 76  # Simplified, may need custom training
        }
        
        if results[0].boxes is not None:
            for box in results[0].boxes:
                cls_id = int(box.cls)
                conf = float(box.conf)
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                # Person detection (class 0)
                if cls_id == 0:
                    objects["people"].append({
                        "confidence": conf,
                        "bbox": [x1, y1, x2, y2],
                        "center": [(x1+x2)//2, (y1+y2)//2]
                    })
                    self.person_location = self._classify_location([x1, y1, x2, y2], frame.shape)
                
                # Check appliances
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
            
            # Extract key joints
            for idx, lm in enumerate(results.pose_landmarks.landmark):
                if idx in [11, 12, 13, 14, 15, 16]:  # Shoulders, elbows, wrists
                    pose_data["keypoints"].append({
                        "id": idx,
                        "x": lm.x * w,
                        "y": lm.y * h,
                        "confidence": lm.visibility
                    })
            
            # Classify activity from pose
            pose_data["activity"] = self._classify_pose(results.pose_landmarks)
            
            self.person_pose = pose_data
        
        return pose_data
    
    def _classify_location(self, bbox, frame_shape):
        """Classify person location in home"""
        h, w = frame_shape[:2]
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        
        # Simple grid-based location (customize for your layout)
        if center_x < w // 3:
            location = "kitchen"
        elif center_x < 2 * w // 3:
            location = "living_room"
        else:
            location = "bedroom"
        
        return location
    
    def _classify_pose(self, landmarks):
        """Classify pose into activities"""
        # Simplified pose classification
        try:
            # Get key coordinates
            left_shoulder = landmarks[11]
            right_shoulder = landmarks[12]
            left_hip = landmarks[23]
            right_hip = landmarks[24]
            
            # Calculate angles (simplified)
            shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
            hip_y = (left_hip.y + right_hip.y) / 2
            
            # Lying down (fall detection)
            if abs(shoulder_y - hip_y) < 0.15:
                self.falling = True
                return "lying_down"
            else:
                self.falling = False
            
            # Standing vs sitting
            if shoulder_y < hip_y - 0.1:
                return "standing"
            else:
                return "sitting"
        except:
            return "unknown"
    
    def process_frame(self, frame):
        """Process single frame"""
        self.frame_count += 1
        
        # Skip frames for efficiency
        if self.frame_count % self.skip_frames != 0:
            return None
        
        # Detection
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
    
    def run_continuous(self, output_file="events.jsonl", max_frames=None):
        """Run continuous detection from camera"""
        cap = cv2.VideoCapture(self.camera_id)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        print(f"Starting continuous detection (saving to {output_file})...")
        print("Press 'q' to stop\n")
        
        frame_count = 0
        with open(output_file, 'w') as f:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                event = self.process_frame(frame)
                if event:
                    f.write(json.dumps(event) + '\n')
                    f.flush()
                    
                    # Display
                    print(f"Frame {event['frame_id']:5d} | "
                          f"Person: {event['person_detected']} | "
                          f"Activity: {event['person_activity']:12s} | "
                          f"Location: {event['person_location']:12s} | "
                          f"Objects: {len(event['objects'])}")
                
                # Show frame
                cv2.imshow("CARE-VLM Detection", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
                frame_count += 1
                if max_frames and frame_count >= max_frames:
                    break
        
        cap.release()
        cv2.destroyAllWindows()
        print(f"\nCaptured {frame_count} frames")
        print(f"Events saved to {output_file}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", type=int, default=0, help="Camera device ID")
    parser.add_argument("--skip-frames", type=int, default=15, help="Skip N frames (1-3 FPS)")
    parser.add_argument("--output", type=str, default="events.jsonl", help="Output file")
    parser.add_argument("--max-frames", type=int, default=None, help="Max frames to capture")
    args = parser.parse_args()
    
    pipeline = DetectionPipeline(camera_id=args.camera, skip_frames=args.skip_frames)
    pipeline.run_continuous(output_file=args.output, max_frames=args.max_frames)
