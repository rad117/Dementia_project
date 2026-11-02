"""
CARE-VLM Main V3 - Complete Integration
Wireless Camera → Detection → Temporal Memory → VLM → Alerts
"""

import sys
sys.path.insert(0, 'server')

from detection_wireless import DetectionPipelineWireless
from temporal_memory import TemporalMemory, EventBuffer
from vlm_reasoner import VLMReasoner, AlertSystem
from benchmark import BenchmarkSuite, Evaluator
import argparse
from datetime import datetime


class CAREVLMSystemV3:
    """Complete wireless monitoring system with VLM reasoning and alerts"""
    
    def __init__(self, 
                 camera_method: str = "http",
                 camera_source: str = None,
                 model: str = "mistral",
                 db_path: str = "monitoring.db",
                 alert_phone: str = None,
                 alert_email: str = None):
        """
        Initialize CARE-VLM V3 system
        
        Args:
            camera_method: "http", "rtmp", "hls", "http_post", "websocket", "cloud"
            camera_source: Stream URL or configuration
            model: LLM model ("mistral", "llama2", "phi")
            db_path: SQLite database path
            alert_phone: Phone number for SMS alerts
            alert_email: Email for alerts
        """
        
        print("\n🚀 Initializing CARE-VLM V3 System (Wireless)")
        print("="*70)
        
        # Camera
        print("📡 Setting up wireless camera...")
        self.pipeline = DetectionPipelineWireless(
            camera_method=camera_method,
            camera_source=camera_source
        )
        
        # Memory
        print("💾 Setting up temporal memory...")
        self.memory = TemporalMemory(db_path=db_path)
        
        # VLM Reasoning
        print("🧠 Loading VLM model...")
        self.reasoner = VLMReasoner(model_name=model)
        
        # Alerts
        print("📞 Configuring alert system...")
        self.alerts = AlertSystem(phone_number=alert_phone, email=alert_email)
        
        # Event buffer
        self.event_buffer = EventBuffer()
        
        # Configuration
        self.hazard_check_interval = 10
        self.frame_count = 0
        
        print("\n✅ CARE-VLM V3 System Ready!")
        print("="*70)
        print(f"Camera: {camera_method}")
        print(f"LLM Model: {model}")
        print(f"Alerts: SMS={bool(alert_phone)}, Email={bool(alert_email)}")
        print("="*70 + "\n")
    
    def process_continuous(self, max_frames: int = None):
        """
        Run continuous monitoring
        
        Args:
            max_frames: Stop after N frames (for testing)
        """
        
        print("🚀 CARE-VLM MONITORING - WIRELESS")
        print("="*70)
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Continuous monitoring (Ctrl+C to stop)\n")
        
        try:
            while True:
                # Get frame from wireless camera
                frame = self.pipeline.camera.read_frame()
                
                if frame is None:
                    print("⚠️  No frame received, retrying...")
                    continue
                
                # Process frame
                event = self.pipeline.process_frame(frame)
                
                if event:
                    # Log event to memory
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
            print("\n\n⚠️  Monitoring stopped by user")
        finally:
            self.pipeline.camera.camera.release()
            self._print_session_summary()
    
    def _check_hazards(self):
        """Check for hazards using VLM reasoning"""
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
        
        # Log hazard if risky
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
        """Display current frame status"""
        person = "✓" if event.get("person_detected") else "✗"
        location = event.get("person_location", "?")
        activity = event.get("person_activity", "?")
        objects = [o.get("type") for o in event.get("objects", [])]
        
        obj_str = f"[{', '.join(objects)}]" if objects else "[]"
        
        # Estimate risk (simple heuristic)
        risk = "LOW"
        if len(objects) > 0 and not person:
            risk = "HIGH"
        elif len(objects) > 0:
            risk = "MEDIUM"
        
        print(f"Frame {event['frame_id']:6d} | Person: {person} | "
              f"{activity:12s} | Risk: {risk}")
    
    def _print_session_summary(self):
        """Print session summary"""
        print("\n" + "="*70)
        print("SESSION SUMMARY")
        print("="*70)
        
        recent = self.memory.get_recent_events(minutes=30)
        
        print(f"Frames processed:   {self.frame_count}")
        print(f"Events logged:      {len(recent)}")
        print(f"Duration:           ~{self.frame_count / 2.5:.1f} seconds @ 2.5 FPS")
        
        # Anomalies
        anomalies = self.memory.detect_anomalies()
        if anomalies:
            print(f"\nAnomalies detected:")
            for anom in anomalies:
                print(f"  • {anom['type']}: {anom.get('duration_minutes', anom.get('count', 'unknown'))}")
        
        print("\n✅ Monitoring session ended")
        print("="*70)
    
    def run_benchmark(self):
        """Run accuracy benchmark"""
        print("\n🧪 Running benchmark evaluation...\n")
        
        evaluator = Evaluator(reasoner=self.reasoner)
        scenarios = BenchmarkSuite.create_scenarios()
        
        evaluator.evaluate_all(scenarios)
        evaluator.export_results("benchmark_results.json")
        
        print("\n✅ Benchmark complete")
        return evaluator.results
    
    def simulate_scenario(self, scenario_name: str):
        """Simulate a specific scenario"""
        print(f"\n🎬 Simulating: {scenario_name}\n")
        
        scenarios = BenchmarkSuite.create_scenarios()
        scenario = next((s for s in scenarios if s.name == scenario_name), None)
        
        if not scenario:
            print(f"❌ Scenario '{scenario_name}' not found")
            print("Available scenarios:")
            for s in scenarios:
                print(f"  • {s.name}")
            return
        
        # Process events
        for event in scenario.events:
            self.memory.log_event(event)
            self.event_buffer.add(event)
        
        # Get assessment
        summary = self.event_buffer.to_text()
        assessment = self.reasoner.assess_hazard(
            summary,
            scenario.events
        )
        
        # Display results
        print(f"Scenario: {scenario.name}")
        print(f"Expected hazard: {scenario.ground_truth_hazard}")
        print(f"Detected hazard: {assessment['risk_score'] >= 50}")
        print(f"Risk score: {assessment['risk_score']}/100")
        print(f"Risk level: {assessment['risk_level']}")
        print(f"Action: {assessment['action']}")
        print(f"\nReasoning:\n{assessment['reasoning']}")


def main():
    parser = argparse.ArgumentParser(
        description="CARE-VLM V3: Complete Wireless Alzheimer's Monitoring"
    )
    
    parser.add_argument(
        "--mode",
        choices=["monitor", "benchmark", "simulate"],
        default="monitor",
        help="Operating mode"
    )
    
    parser.add_argument(
        "--camera-method",
        choices=["http", "rtmp", "hls", "http_post", "websocket", "cloud"],
        default="http",
        help="Wireless camera method"
    )
    
    parser.add_argument(
        "--camera-source",
        type=str,
        required=True,
        help="Camera stream URL or configuration"
    )
    
    parser.add_argument(
        "--model",
        choices=["mistral", "llama2", "phi"],
        default="mistral",
        help="LLM model"
    )
    
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Max frames (for testing)"
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
    system = CAREVLMSystemV3(
        camera_method=args.camera_method,
        camera_source=args.camera_source,
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
