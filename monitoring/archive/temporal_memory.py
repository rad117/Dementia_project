"""
Temporal Memory Module
Manages event history and generates summaries for VLM reasoning
Lightweight, runs on-device (SQLite + RAM)
"""

import sqlite3
import json
from datetime import datetime, timedelta
from collections import deque
from typing import List, Dict, Optional
import threading

class TemporalMemory:
    """Event logging and temporal reasoning system"""
    
    def __init__(self, db_path="events.db", window_minutes=10):
        """
        Args:
            db_path: SQLite database file
            window_minutes: How many minutes of history to keep in memory
        """
        self.db_path = db_path
        self.window_minutes = window_minutes
        self.memory_lock = threading.Lock()
        
        # In-memory buffer (RAM, for phone speed)
        self.event_buffer = deque(maxlen=500)  # ~10 min of events
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Create SQLite schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            frame_id INTEGER,
            event_type TEXT,
            person_detected BOOLEAN,
            location TEXT,
            activity TEXT,
            object_type TEXT,
            object_state TEXT,
            confidence REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS hazards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            hazard_type TEXT,
            risk_score INTEGER,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)
        """)
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_location ON events(location)
        """)
        
        conn.commit()
        conn.close()
    
    def log_event(self, event: Dict):
        """Log detection event to memory and database"""
        with self.memory_lock:
            # Add to RAM buffer
            self.event_buffer.append(event)
            
            # Persist to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
            INSERT INTO events 
            (timestamp, frame_id, event_type, person_detected, location, 
             activity, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event.get("timestamp"),
                event.get("frame_id"),
                "detection",
                event.get("person_detected", False),
                event.get("person_location"),
                event.get("person_activity"),
                0.9  # Confidence from detector
            ))
            
            # Log objects separately for analysis
            for obj in event.get("objects", []):
                cursor.execute("""
                INSERT INTO events 
                (timestamp, event_type, object_type, confidence)
                VALUES (?, ?, ?, ?)
                """, (
                    event.get("timestamp"),
                    "object_detection",
                    obj.get("type"),
                    obj.get("confidence", 0.0)
                ))
            
            conn.commit()
            conn.close()
    
    def log_hazard(self, hazard_type: str, risk_score: int, description: str):
        """Log detected hazard"""
        timestamp = datetime.now().isoformat()
        
        with self.memory_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
            INSERT INTO hazards (timestamp, hazard_type, risk_score, description)
            VALUES (?, ?, ?, ?)
            """, (timestamp, hazard_type, risk_score, description))
            
            conn.commit()
            conn.close()
    
    def get_recent_events(self, minutes: int = None) -> List[Dict]:
        """Get events from last N minutes"""
        if minutes is None:
            minutes = self.window_minutes
        
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self.memory_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT timestamp, event_type, person_detected, location, 
                   activity, object_type, confidence
            FROM events
            WHERE timestamp > ?
            ORDER BY timestamp DESC
            LIMIT 200
            """, (cutoff_time.isoformat(),))
            
            rows = cursor.fetchall()
            conn.close()
            
            events = []
            for row in rows:
                events.append({
                    "timestamp": row[0],
                    "type": row[1],
                    "person": row[2],
                    "location": row[3],
                    "activity": row[4],
                    "object": row[5],
                    "confidence": row[6]
                })
            
            return events
    
    def generate_summary(self, minutes: int = None) -> str:
        """Generate text summary of recent events for VLM"""
        if minutes is None:
            minutes = self.window_minutes
        
        events = self.get_recent_events(minutes)
        
        if not events:
            return "No recent events detected."
        
        # Group by time windows
        summary_points = []
        current_activity = None
        activity_start = None
        
        for event in reversed(events):  # Chronological order
            timestamp = event["timestamp"]
            
            # Compress consecutive same activities
            if event["activity"] != current_activity:
                if current_activity:
                    summary_points.append(
                        f"{activity_start} - {current_activity}"
                    )
                current_activity = event["activity"]
                activity_start = timestamp
            
            # Log location changes
            if summary_points and "location" in event and event["location"]:
                summary_points.append(
                    f"{timestamp} - Moved to {event['location']}"
                )
            
            # Log object interactions
            if event["object"]:
                summary_points.append(
                    f"{timestamp} - {event['object']} detected"
                )
        
        # Format as readable text
        summary = "Recent activity summary:\n"
        for point in summary_points[-10:]:  # Last 10 points
            summary += f"  • {point}\n"
        
        return summary
    
    def get_object_timeline(self, object_type: str, minutes: int = 30) -> Dict:
        """Get timeline of specific object (e.g., stove) over time"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self.memory_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT timestamp, COUNT(*)
            FROM events
            WHERE object_type = ? AND timestamp > ?
            GROUP BY DATE(timestamp, 'minute')
            ORDER BY timestamp
            """, (object_type, cutoff_time.isoformat()))
            
            rows = cursor.fetchall()
            conn.close()
        
        timeline = {
            "object": object_type,
            "observations": rows,
            "total_detections": sum([row[1] for row in rows]),
            "duration_minutes": minutes
        }
        
        return timeline
    
    def get_person_absence_duration(self) -> Optional[int]:
        """Get how long person has been absent from camera"""
        with self.memory_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT timestamp FROM events
            WHERE person_detected = 1
            ORDER BY timestamp DESC
            LIMIT 1
            """)
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return None
            
            last_seen = datetime.fromisoformat(result[0])
            absence = (datetime.now() - last_seen).total_seconds() // 60
            
            return absence
    
    def detect_anomalies(self) -> List[Dict]:
        """Detect anomalous patterns"""
        events = self.get_recent_events(minutes=30)
        anomalies = []
        
        # Check for repeated activities (confusion indicator)
        activity_counts = {}
        for event in events:
            activity = event["activity"]
            activity_counts[activity] = activity_counts.get(activity, 0) + 1
        
        for activity, count in activity_counts.items():
            if count > 15:  # Repeated same activity
                anomalies.append({
                    "type": "repetition",
                    "activity": activity,
                    "count": count,
                    "risk": "medium"
                })
        
        # Check for long inactivity
        person_absent = self.get_person_absence_duration()
        if person_absent and person_absent > 15:
            anomalies.append({
                "type": "prolonged_absence",
                "duration_minutes": person_absent,
                "risk": "high"
            })
        
        return anomalies
    
    def export_session(self, output_file: str):
        """Export current session for analysis"""
        with self.memory_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM events")
            events = cursor.fetchall()
            
            cursor.execute("SELECT * FROM hazards")
            hazards = cursor.fetchall()
            
            conn.close()
        
        session_data = {
            "exported_at": datetime.now().isoformat(),
            "events": events,
            "hazards": hazards,
            "summary": self.generate_summary()
        }
        
        with open(output_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        print(f"Session exported to {output_file}")


class EventBuffer:
    """Minimal RAM buffer for phone deployment"""
    
    def __init__(self, max_size=500):
        """Keep last N events in RAM only (faster, lower memory)"""
        self.buffer = deque(maxlen=max_size)
    
    def add(self, event: Dict):
        """Add event to buffer"""
        self.buffer.append(event)
    
    def get_last(self, n: int = 50) -> List[Dict]:
        """Get last N events"""
        return list(self.buffer)[-n:]
    
    def to_text(self) -> str:
        """Convert buffer to text for VLM"""
        lines = []
        for event in list(self.buffer)[-50:]:  # Last 50
            ts = event.get("timestamp", "?")[-8:]  # HH:MM:SS
            location = event.get("person_location", "?")
            activity = event.get("person_activity", "?")
            objects = [o.get("type") for o in event.get("objects", [])]
            
            line = f"{ts} | Location: {location} | Activity: {activity}"
            if objects:
                line += f" | Objects: {', '.join(objects)}"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def clear(self):
        """Clear buffer"""
        self.buffer.clear()


if __name__ == "__main__":
    # Test example
    memory = TemporalMemory()
    
    # Simulate some events
    test_event = {
        "timestamp": datetime.now().isoformat(),
        "frame_id": 1,
        "person_detected": True,
        "person_location": "kitchen",
        "person_activity": "standing",
        "objects": [
            {"type": "stove", "confidence": 0.92}
        ]
    }
    
    memory.log_event(test_event)
    
    print("Summary:")
    print(memory.generate_summary())
    
    print("\nAnomaly detection:")
    print(memory.detect_anomalies())
