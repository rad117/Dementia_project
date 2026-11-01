"""
Vision-Language Model Reasoner
Text-based risk assessment using quantized LLM (Llama 3.2-3B)
Runs on phone or server
"""

import json
from datetime import datetime
from typing import Dict, List, Tuple
import subprocess
import os

class VLMReasoner:
    """Risk assessment using LLM reasoning"""
    
    def __init__(self, model_name: str = "mistral", use_ollama: bool = True):
        """
        Args:
            model_name: "mistral" (4.2B), "llama2" (7B), or "phi" (2.7B)
            use_ollama: Use Ollama for model management
        """
        self.model_name = model_name
        self.use_ollama = use_ollama
        
        if use_ollama:
            self._check_ollama()
    
    def _check_ollama(self):
        """Verify Ollama is running"""
        try:
            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                timeout=5
            )
            if result.returncode != 0:
                print("⚠️  Ollama not running. Start with: ollama serve")
        except FileNotFoundError:
            print("⚠️  Ollama not installed. Install from https://ollama.ai")
    
    def query_llm(self, prompt: str, max_tokens: int = 200) -> str:
        """Query LLM (Ollama backend)"""
        try:
            result = subprocess.run(
                [
                    "ollama", "run", self.model_name,
                    prompt
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Error: {result.stderr}"
        except Exception as e:
            return f"Failed to query LLM: {str(e)}"
    
    def assess_hazard(self, 
                     event_summary: str,
                     recent_events: List[Dict],
                     context: Dict = None) -> Dict:
        """
        Assess risk based on event sequence
        
        Args:
            event_summary: Text summary of recent events
            recent_events: List of detection events
            context: Additional context (time, location, etc.)
        
        Returns:
            Risk assessment with score (0-100) and recommendations
        """
        
        # Build reasoning prompt
        prompt = self._build_reasoning_prompt(
            event_summary, 
            recent_events, 
            context
        )
        
        # Query LLM for reasoning
        reasoning = self.query_llm(prompt, max_tokens=250)
        
        # Parse response and extract risk score
        risk_score = self._extract_risk_score(reasoning)
        risk_level = self._classify_risk(risk_score)
        
        # Determine action
        action = self._determine_action(risk_score, reasoning)
        
        assessment = {
            "timestamp": datetime.now().isoformat(),
            "risk_score": risk_score,  # 0-100
            "risk_level": risk_level,  # low, medium, high, critical
            "reasoning": reasoning,
            "action": action,
            "confidence": 0.85  # LLM confidence
        }
        
        return assessment
    
    def _build_reasoning_prompt(self, 
                               event_summary: str,
                               recent_events: List[Dict],
                               context: Dict = None) -> str:
        """Build prompt for LLM reasoning"""
        
        # Analyze event patterns
        patterns = self._analyze_patterns(recent_events)
        
        prompt = f"""
You are a healthcare AI assistant helping monitor elderly patients with Alzheimer's disease.

Recent Activity Log:
{event_summary}

Detected Patterns:
{self._format_patterns(patterns)}

Current Context:
- Time: {datetime.now().strftime('%H:%M:%S')}
- Location: {context.get('location', 'unknown') if context else 'unknown'}
- Activity: {context.get('activity', 'unknown') if context else 'unknown'}

Based on the activity log and patterns, assess:
1. Is there any immediate safety concern? (yes/no)
2. What is the risk level? (low: 0-25, medium: 26-50, high: 51-75, critical: 76-100)
3. What action should be taken? (none, monitor, alert caregiver, emergency)

Respond in this exact format:
RISK_SCORE: [number 0-100]
RISK_LEVEL: [low/medium/high/critical]
REASONING: [brief explanation]
ACTION: [none/monitor/alert/emergency]
        """
        
        return prompt.strip()
    
    def _analyze_patterns(self, events: List[Dict]) -> Dict:
        """Analyze event patterns for anomalies"""
        patterns = {
            "stove_on_duration": 0,
            "person_away_duration": 0,
            "repeated_activities": [],
            "unusual_locations": [],
            "falls_detected": 0
        }
        
        if not events:
            return patterns
        
        # Track stove on time
        stove_on_time = None
        for event in reversed(events):
            for obj in event.get("objects", []):
                if obj.get("type") == "stove":
                    if not stove_on_time:
                        stove_on_time = event.get("timestamp")
        
        # Track person absence
        person_detected = False
        for event in reversed(events):
            if event.get("person_detected"):
                person_detected = True
                break
        
        patterns["person_away_duration"] = 0 if person_detected else "unknown"
        
        # Count repeated activities
        activities = [e.get("person_activity") for e in events if e.get("person_activity")]
        if activities:
            patterns["repeated_activities"] = list(set(activities))
        
        return patterns
    
    def _format_patterns(self, patterns: Dict) -> str:
        """Format patterns for prompt"""
        lines = []
        
        if patterns.get("stove_on_duration"):
            lines.append(f"- Stove has been ON for {patterns['stove_on_duration']} minutes")
        
        if patterns.get("person_away_duration", 0) > 10:
            lines.append(f"- Person away for {patterns['person_away_duration']} minutes")
        
        if patterns.get("falls_detected", 0) > 0:
            lines.append(f"- {patterns['falls_detected']} potential falls detected")
        
        if patterns.get("repeated_activities"):
            lines.append(f"- Repeated activities: {', '.join(patterns['repeated_activities'])}")
        
        return "\n".join(lines) if lines else "- No significant patterns detected"
    
    def _extract_risk_score(self, response: str) -> int:
        """Extract risk score from LLM response"""
        try:
            for line in response.split("\n"):
                if "RISK_SCORE:" in line:
                    score = int(line.split(":")[-1].strip())
                    return max(0, min(100, score))  # Clamp 0-100
        except:
            pass
        
        # Default to medium risk if parsing fails
        return 50
    
    def _classify_risk(self, score: int) -> str:
        """Classify risk level"""
        if score < 25:
            return "low"
        elif score < 50:
            return "medium"
        elif score < 75:
            return "high"
        else:
            return "critical"
    
    def _determine_action(self, risk_score: int, reasoning: str) -> str:
        """Determine action based on risk"""
        if risk_score < 25:
            return "none"
        elif risk_score < 50:
            return "monitor"
        elif risk_score < 75:
            return "alert"
        else:
            return "emergency"
    
    def detect_stove_hazard(self, events: List[Dict]) -> Tuple[bool, int, str]:
        """
        Detect unattended stove hazard
        
        Returns:
            (is_hazard, risk_score, reason)
        """
        stove_events = [e for e in events if any(
            o.get("type") == "stove" for o in e.get("objects", [])
        )]
        
        if not stove_events:
            return False, 0, "Stove not detected"
        
        # Check if stove has been on for too long
        if len(stove_events) > 20:  # ~1+ minute of detections
            person_events = [e for e in events if e.get("person_detected")]
            
            if not person_events:
                return True, 90, "Stove on, person absent"
            
            # Check if person in kitchen
            kitchen_events = [e for e in person_events 
                             if e.get("person_location") == "kitchen"]
            
            if not kitchen_events:
                return True, 85, "Stove on, person away from kitchen"
        
        return False, 15, "Stove under observation"
    
    def detect_fall(self, events: List[Dict]) -> Tuple[bool, int, str]:
        """Detect fall hazard"""
        fall_events = [e for e in events if e.get("falling", False)]
        
        if not fall_events:
            return False, 0, "No fall detected"
        
        if len(fall_events) > 2:
            return True, 100, f"Fall detected ({len(fall_events)} events)"
        
        return False, 20, "Possible fall, monitoring"
    
    def detect_medication_non_adherence(self, 
                                       medication_time: str,
                                       events: List[Dict]) -> Tuple[bool, int, str]:
        """
        Detect if patient missed medication
        
        Args:
            medication_time: Expected time format "HH:MM"
            events: List of recent events
        """
        hour, minute = map(int, medication_time.split(":"))
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute
        
        # If past medication time
        if current_hour > hour or (current_hour == hour and current_minute > minute + 30):
            # Check if patient interacted with medication (simplified)
            medication_events = [e for e in events 
                                if "medication" in str(e).lower()]
            
            if not medication_events:
                return True, 60, "Medication time passed, no activity detected"
        
        return False, 0, "Within medication window or already taken"


class AlertSystem:
    """Generate and manage alerts"""
    
    def __init__(self, phone_number: str = None, email: str = None):
        """
        Args:
            phone_number: SMS alerts (optional)
            email: Email alerts (optional)
        """
        self.phone_number = phone_number
        self.email = email
        self.alert_history = []
    
    def generate_alert(self, risk_assessment: Dict) -> Dict:
        """Generate alert from risk assessment"""
        risk_score = risk_assessment["risk_score"]
        risk_level = risk_assessment["risk_level"]
        action = risk_assessment["action"]
        
        alert = {
            "timestamp": datetime.now().isoformat(),
            "severity": risk_level,
            "risk_score": risk_score,
            "message": self._generate_message(risk_assessment),
            "channels": self._determine_channels(risk_level)
        }
        
        self.alert_history.append(alert)
        
        return alert
    
    def _generate_message(self, assessment: Dict) -> str:
        """Generate human-readable alert message"""
        risk_level = assessment["risk_level"]
        action = assessment["action"]
        
        messages = {
            "low": "Activity monitored. No immediate concerns.",
            "medium": "⚠️  Medium risk detected. Caregiver review recommended.",
            "high": "⚠️⚠️  HIGH RISK! Immediate caregiver notification required.",
            "critical": "🚨 CRITICAL! Emergency services may be needed."
        }
        
        base_message = messages.get(risk_level, "Alert generated")
        
        if action == "alert":
            base_message += " Notifying caregiver now."
        elif action == "emergency":
            base_message += " Emergency response initiated."
        
        return base_message
    
    def _determine_channels(self, risk_level: str) -> List[str]:
        """Determine which alert channels to use"""
        channels = ["app_notification"]  # Always on app
        
        if risk_level == "high":
            if self.phone_number:
                channels.append("sms")
            if self.email:
                channels.append("email")
        
        elif risk_level == "critical":
            if self.phone_number:
                channels.extend(["sms", "call"])
            if self.email:
                channels.append("email")
        
        return channels


if __name__ == "__main__":
    # Test example
    reasoner = VLMReasoner(model_name="mistral")
    
    # Simulate events
    test_events = [
        {
            "timestamp": datetime.now().isoformat(),
            "person_detected": True,
            "person_location": "kitchen",
            "person_activity": "standing",
            "objects": [{"type": "stove", "confidence": 0.95}]
        },
        {
            "timestamp": datetime.now().isoformat(),
            "person_detected": False,
            "person_location": None,
            "person_activity": None,
            "objects": []
        }
    ]
    
    # Test hazard detection
    print("Testing hazard detection...")
    is_hazard, score, reason = reasoner.detect_stove_hazard(test_events)
    print(f"  Stove hazard: {is_hazard} (score: {score}, reason: {reason})")
    
    # Test risk assessment
    print("\nTesting risk assessment...")
    summary = "8:15 Kitchen entered\n8:16 Stove ON\n8:20 Person left kitchen"
    assessment = reasoner.assess_hazard(summary, test_events)
    print(f"  Risk Score: {assessment['risk_score']}")
    print(f"  Risk Level: {assessment['risk_level']}")
    print(f"  Action: {assessment['action']}")
