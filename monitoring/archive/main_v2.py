"""
CARE-VLM Main Integration Script - V2
Supports: Phone Camera, USB Camera, WiFi Camera, CCTV (RTSP), HTTP streams
"""

import sys
import argparse
import json
from datetime import datetime
from pathlib import Path

# Update paths if needed
sys.path.insert(0, 'server')
sys.path.insert(0, 'evaluation')

from core_pipeline_v2 import DetectionPipelineV2
from temporal_memory import TemporalMemory, EventBuffer
from vlm_reasoner import VLMReasoner, AlertSystem
from benchmark import BenchmarkSuite, Evaluator


class CAREVLMSystemV2:
    """Complete Alzheimer's monitoring system with flexible camera support"""
    
    def __init__(self, 
                 camera_type: str = "usb_camera",
                 camera_address: str = "0",
                 model: str = "mistral",
                 db_path: str = "monitoring.db",
                 alert_phone: str = None,
                 alert_email: str = None):
        """
        Initialize CARE-VLM system with flexible camera input
        
        Args:
            camera_type: "usb_camera", "phone_usb", "phone_wifi", "rtsp", "http"
            camera_address: Camera ID (0,1,2...) or URL
            model: LLM model ("mistral", "llama2", "phi")
            db_path: SQLite database path
            alert_phone: Phone number for SMS alerts
            alert_email: Email for alerts
        """
        
        print("🚀 Initializing CARE-VLM System (V2 - Flexible Camera)\n")
        
        # Components
        self.pipeline = DetectionPipelineV2(
            camera_source=camera_type,
            camera_address=camera_address
        )
        self.memory = TemporalMemory(db_path=db_path)
        self.reasoner = VLMReasoner(model_name=model)
        self.alerts = AlertSystem(phone_number=alert_phone, email=alert_email)
        self.event_buffer = EventBuffer()
        
        # Configuration
        self.hazard_check_interval = 10
        self.frame_count = 0
        
        print("✓ Detection pipeline ready")
        print("✓ Temporal memory initialized")
        print("✓ VLM reasoner loaded")
        print("✓ Alert system configured\n")
    
    def process_continuous(self, max_frames: int = None):
        """
        Run continuous monitoring loop
        
        Args:
            max_frames: Stop after N frames (for testing)
        """
        
        print("="*60)
        print("CARE-VLM CONTINUOUS MONITORING (V2)")
        print("="*60)
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                frame = self.pipeline.camera_source.read_frame()
                if frame is None:
                    break
                
                # Process frame
                event = self.pipeline.process_frame(frame)
                
                if event:
                    # Log event
                    self.memory.log_event(event)
                    self.event_buffer.add(event)
                    
                    # Check for hazards periodically
                    if self.frame_count % self.hazard_check_interval == 0:
                        self._check_hazards()
                    
                    # Display status
                    self._display_status(event)
                    
                    self.frame_count += 1
                
                if max_frames and self.frame_count >= max_frames:
                    break
        
        except KeyboardInterrupt:
            print("\n\nShutdown requested...")
        
        finally:
            self.pipeline.camera_source.release()
            self._print_session_summary()
    
    def _check_hazards(self):
        """Periodically check for hazards"""
        recent_events = self.memory.get_recent_events(minutes=10)
        
        if not recent_events:
            return
        
        # Get text summary
        summary = self.event_buffer.to_text()
        
        # Perform risk assessment
        context = {
            "location": recent_events[0].get("location", "unknown"),
            "activity": recent_events[0].get("activity", "unknown")
        }
        
        assessment = self.reasoner.assess_hazard(summary, recent_events, context)
        
        # Log hazard
        if assessment["risk_score"] >= 50:
            self.memory.log_hazard(
                hazard_type=assessment["risk_level"],
                risk_score=assessment["risk_score"],
                description=assessment["reasoning"]
            )
        
        # Generate alert if needed
        if assessment["action"] in ["alert", "emergency"]:
            alert = self.alerts.generate_alert(assessment)
            print(f"\n⚠️  ALERT: {alert['message']}")
            print(f"   Risk Score: {assessment['risk_score']}/100")
            print(f"   Reasoning: {assessment['reasoning']}\n")
    
    def _display_status(self, event: dict):
        """Display current status"""
        person = "✓" if event.get("person_detected") else "✗"
        location = event.get("person_location", "?")
        activity = event.get("person_activity", "?")
        objects = [o.get("type") for o in event.get("objects", [])]
        
        obj_str = f"[{', '.join(objects)}]" if objects else "[]"
        
        print(f"Frame {event['frame_id']:6d} | Person: {person} | "
              f"{location:10s} | {activity:12s} | Objects: {obj_str}")
    
    def _print_session_summary(self):
        """Print session summary"""
        print("\n" + "="*60)
        print("SESSION SUMMARY")
        print("="*60)
        
        recent = self.memory.get_recent_events(minutes=30)
        
        print(f"Frames processed:   {self.frame_count}")
        print(f"Events logged:      {len(recent)}")
        print(f"Duration:           ~{self.frame_count / 30:.1f} seconds")
        
        # Anomalies
        anomalies = self.memory.detect_anomalies()
        if anomalies:
            print(f"\nAnomalies detected:")
            for anom in anomalies:
                print(f"  • {anom['type']}: {anom.get('duration_minutes', anom.get('count', 'unknown'))}")
        
        print("\n✓ Session ended safely")
        print("="*60)
    
    def run_benchmark(self):
        """Run benchmark evaluation"""
        print("Running benchmark evaluation...\n")
        
        evaluator = Evaluator(reasoner=self.reasoner)
        scenarios = BenchmarkSuite.create_scenarios()
        
        evaluator.evaluate_all(scenarios)
        evaluator.export_results("benchmark_results.json")
        
        return evaluator.results
    
    def simulate_scenario(self, scenario_name: str):
        """Simulate a specific scenario"""
        print(f"Simulating: {scenario_name}\n")
        
        scenarios = BenchmarkSuite.create_scenarios()
        scenario = next((s for s in scenarios if s.name == scenario_name), None)
        
        if not scenario:
            print(f"Scenario '{scenario_name}' not found")
            return
        
        # Process events through system
        for event in scenario.events:
            self.memory.log_event(event)
            self.event_buffer.add(event)
        
        # Get risk assessment
        summary = self.event_buffer.to_text()
        assessment = self.reasoner.assess_hazard(
            summary,
            scenario.events
        )
        
        print(f"Scenario: {scenario.name}")
        print(f"Expected hazard: {scenario.ground_truth_hazard}")
        print(f"Detected hazard: {assessment['risk_score'] >= 50}")
        print(f"Risk score: {assessment['risk_score']}/100")
        print(f"Risk level: {assessment['risk_level']}")
        print(f"Action: {assessment['action']}")
        print(f"\nReasoning:\n{assessment['reasoning']}")


def main():
    parser = argparse.ArgumentParser(
        description="CARE-VLM V2: Flexible Camera Input Support"
    )
    
    parser.add_argument(
        "--mode",
        choices=["monitor", "benchmark", "simulate"],
        default="monitor",
        help="Operating mode"
    )
    
    parser.add_argument(
        "--camera-type",
        choices=["usb_camera", "phone_usb", "phone_wifi", "rtsp", "http"],
        default="usb_camera",
        help="Type of camera input"
    )
    
    parser.add_argument(
        "--camera-address",
        type=str,
        default="0",
        help="Camera ID (0,1,2...) or URL (http://...)"
    )
    
    parser.add_argument(
        "--model",
        choices=["mistral", "llama2", "phi"],
        default="mistral",
        help="LLM model to use"
    )
    
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Max frames to process (for testing)"
    )
    
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Scenario to simulate"
    )
    
    parser.add_argument(
        "--phone",
        type=str,
        default=None,
        help="Phone number for SMS alerts"
    )
    
    parser.add_argument(
        "--email",
        type=str,
        default=None,
        help="Email for alerts"
    )
    
    args = parser.parse_args()
    
    # Initialize system
    system = CAREVLMSystemV2(
        camera_type=args.camera_type,
        camera_address=args.camera_address,
        model=args.model,
        alert_phone=args.phone,
        alert_email=args.email
    )
    
    # Run mode
    if args.mode == "monitor":
        system.process_continuous(max_frames=args.max_frames)
    
    elif args.mode == "benchmark":
        system.run_benchmark()
    
    elif args.mode == "simulate":
        if not args.scenario:
            print("Error: --scenario required for simulate mode")
            parser.print_help()
            return
        system.simulate_scenario(args.scenario)


if __name__ == "__main__":
    main()
