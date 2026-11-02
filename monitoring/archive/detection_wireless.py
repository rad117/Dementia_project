"""
CARE-VLM Detection Pipeline V3 - Wireless Streaming
Supports: RTMP, HTTP, HLS, WebSocket, Cloud storage
Phone and server can be on completely different networks
"""

import sys
sys.path.insert(0, 'server')

from wireless_camera_streaming import WirelessCameraCapture
from ultralytics import YOLO
import mediapipe as mp
from datetime import datetime
import json
from collections import defaultdict
import cv2


class DetectionPipelineWireless:
    """Detection pipeline with wireless camera streaming"""
    
    def __init__(self, 
                 camera_method: str = "http",
                 camera_source: str = None,
                 skip_frames: int = 15):
        """
        Args:
            camera_method: "rtmp", "http", "hls", "http_post", "websocket", "cloud"
            camera_source: Stream URL or configuration
            skip_frames: Process every Nth frame
        
        Examples:
            # HTTP stream from phone
            pipeline = DetectionPipelineWireless(
                camera_method="http",
                camera_source="http://phone-ip:8080/video"
            )
            
            # RTMP stream from phone
            pipeline = DetectionPipelineWireless(
                camera_method="rtmp",
                camera_source="rtmp://server-ip:1935/live/camera"
            )
            
            # Server receives frames from phone (HTTP POST)
            pipeline = DetectionPipelineWireless(
                camera_method="http_post",
                camera_source="0.0.0.0:5000"
            )
        """
        
        self.camera = WirelessCameraCapture(
            method=camera_method,
            source=camera_source
        )
        self.skip_frames = skip_frames
        self.frame_count = 0
        
        # Load models
        print("\nLoading detection models...")
        self.yolo = YOLO("yolov8n.pt")
        
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,
            smooth_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        self.object_timings = defaultdict(lambda: None)
        self.person_location = None
        self.falling = False
        
        print("✅ Detection pipeline ready!")
        print(f"   Camera method: {camera_method}")
        print(f"   Source: {camera_source}")
    
    def detect_objects(self, frame):
        """YOLOv8 object detection"""
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
                        "bbox": [x1, y1, x2, y2]
                    })
                    self.person_location = self._classify_location([x1, y1, x2, y2], frame.shape)
                
                for appliance, yolo_id in appliance_classes.items():
                    if cls_id == yolo_id:
                        objects["appliances"].append({
                            "type": appliance,
                            "confidence": conf
                        })
                        self.object_timings[appliance] = datetime.now()
        
        return objects
    
    def detect_pose(self, frame):
        """MediaPipe pose estimation"""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)
        
        pose_data = {
            "detected": results.pose_landmarks is not None,
            "activity": "idle"
        }
        
        if results.pose_landmarks:
            pose_data["activity"] = self._classify_pose(results.pose_landmarks)
        
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
        """Classify pose"""
        try:
            shoulder_y = (landmarks[11].y + landmarks[12].y) / 2
            hip_y = (landmarks[23].y + landmarks[24].y) / 2
            
            if abs(shoulder_y - hip_y) < 0.15:
                self.falling = True
                return "lying_down"
            else:
                self.falling = False
                return "standing" if shoulder_y < hip_y - 0.1 else "sitting"
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
                      max_frames: int = None):
        """
        Run continuous detection from wireless camera
        
        Args:
            output_file: Where to save events
            max_frames: Stop after N frames
        """
        
        print("\n" + "="*70)
        print("🚀 WIRELESS CAMERA DETECTION - CONTINUOUS MODE")
        print("="*70)
        print(f"Output: {output_file}")
        print(f"Server and Phone can be on DIFFERENT networks ✅")
        print("Press Ctrl+C to stop\n")
        
        frame_count = 0
        
        try:
            with open(output_file, 'w') as f:
                while True:
                    # Get frame from wireless camera
                    frame = self.camera.read_frame()
                    
                    if frame is None:
                        print("⚠️  No frame received, retrying...")
                        continue
                    
                    # Process frame
                    event = self.process_frame(frame)
                    
                    if event:
                        f.write(json.dumps(event) + '\n')
                        f.flush()
                        
                        # Display status
                        person = "✓" if event["person_detected"] else "✗"
                        objects = [o.get("type") for o in event.get("objects", [])]
                        obj_str = f"[{', '.join(objects)}]" if objects else "[]"
                        
                        print(f"Frame {event['frame_id']:6d} | Person: {person} | "
                              f"Activity: {event['person_activity']:12s} | "
                              f"Objects: {obj_str}")
                    
                    frame_count += 1
                    if max_frames and frame_count >= max_frames:
                        break
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Stopped by user")
        finally:
            print(f"\n✅ Captured {frame_count} frames")
            print(f"📁 Events saved to {output_file}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="CARE-VLM Wireless Camera Detection"
    )
    
    parser.add_argument(
        "--method",
        choices=["http", "rtmp", "hls", "http_post", "websocket", "cloud"],
        default="http",
        help="Camera streaming method"
    )
    
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Camera stream URL or configuration"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="events.jsonl",
        help="Output file for events"
    )
    
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Max frames to process"
    )
    
    args = parser.parse_args()
    
    # Examples:
    # python detection_wireless.py --method http --source "http://phone-ip:8080/video"
    # python detection_wireless.py --method rtmp --source "rtmp://server:1935/live/cam"
    # python detection_wireless.py --method http_post --source "0.0.0.0:5000"
    
    pipeline = DetectionPipelineWireless(
        camera_method=args.method,
        camera_source=args.source
    )
    
    pipeline.run_continuous(
        output_file=args.output,
        max_frames=args.max_frames
    )
