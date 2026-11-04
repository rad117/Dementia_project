"""
Benchmark and Evaluation Framework
Tests hazard detection accuracy on synthetic scenarios
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import sys
sys.path.insert(0, '../server')

from core_pipeline import DetectionPipeline
from temporal_memory import TemporalMemory
from vlm_reasoner import VLMReasoner

class SyntheticScenario:
    """Synthetic test scenario for Alzheimer's monitoring"""
    
    def __init__(self, name: str, ground_truth_hazard: bool, 
                 events: List[Dict], expected_risk_score: int):
        self.name = name
        self.ground_truth_hazard = ground_truth_hazard
        self.events = events
        self.expected_risk_score = expected_risk_score
    
    def generate_event_summary(self) -> str:
        """Generate text summary of events"""
        summary = []
        for event in self.events:
            ts = event.get("timestamp", "00:00:00")
            location = event.get("person_location", "?")
            activity = event.get("person_activity", "?")
            objects = [o.get("type") for o in event.get("objects", [])]
            
            line = f"{ts} - {location}: {activity}"
            if objects:
                line += f" (near {', '.join(objects)})"
            summary.append(line)
        
        return "\n".join(summary)


class BenchmarkSuite:
    """Collection of test scenarios"""
    
    @staticmethod
    def create_scenarios() -> List[SyntheticScenario]:
        """Create benchmark scenarios"""
        
        scenarios = []
        
        # Scenario 1: Unattended stove (HIGH HAZARD)
        scenario1 = SyntheticScenario(
            name="Unattended stove (5 min)",
            ground_truth_hazard=True,
            events=[
                {
                    "timestamp": "14:00:00",
                    "person_detected": True,
                    "person_location": "kitchen",
                    "person_activity": "standing",
                    "objects": [{"type": "stove", "confidence": 0.95}]
                },
                {
                    "timestamp": "14:01:00",
                    "person_detected": True,
                    "person_location": "kitchen",
                    "person_activity": "cooking",
                    "objects": [{"type": "stove", "confidence": 0.92}]
                },
                {
                    "timestamp": "14:02:00",
                    "person_detected": False,
                    "person_location": None,
                    "person_activity": None,
                    "objects": []
                },
                {
                    "timestamp": "14:03:00",
                    "person_detected": False,
                    "person_location": None,
                    "person_activity": None,
                    "objects": []
                },
                {
                    "timestamp": "14:05:00",
                    "person_detected": False,
                    "person_location": None,
                    "person_activity": None,
                    "objects": []
                }
            ],
            expected_risk_score=85
        )
        scenarios.append(scenario1)
        
        # Scenario 2: Fall detected (CRITICAL HAZARD)
        scenario2 = SyntheticScenario(
            name="Fall detection",
            ground_truth_hazard=True,
            events=[
                {
                    "timestamp": "15:30:00",
                    "person_detected": True,
                    "person_location": "bedroom",
                    "person_activity": "standing",
                    "objects": []
                },
                {
                    "timestamp": "15:30:05",
                    "person_detected": True,
                    "person_location": "bedroom",
                    "person_activity": "lying_down",
                    "falling": True,
                    "objects": []
                }
            ],
            expected_risk_score=95
        )
        scenarios.append(scenario2)
        
        # Scenario 3: Normal cooking (LOW HAZARD)
        scenario3 = SyntheticScenario(
            name="Normal supervised cooking",
            ground_truth_hazard=False,
            events=[
                {
                    "timestamp": "12:00:00",
                    "person_detected": True,
                    "person_location": "kitchen",
                    "person_activity": "standing",
                    "objects": [{"type": "stove", "confidence": 0.90}]
                },
                {
                    "timestamp": "12:01:00",
                    "person_detected": True,
                    "person_location": "kitchen",
                    "person_activity": "cooking",
                    "objects": [{"type": "stove", "confidence": 0.92}]
                },
                {
                    "timestamp": "12:02:00",
                    "person_detected": True,
                    "person_location": "kitchen",
                    "person_activity": "cooking",
                    "objects": [{"type": "stove", "confidence": 0.91}]
                }
            ],
            expected_risk_score=15
        )
        scenarios.append(scenario3)
        
        # Scenario 4: Wandering away (MEDIUM HAZARD)
        scenario4 = SyntheticScenario(
            name="Person wandering, away from home",
            ground_truth_hazard=True,
            events=[
                {
                    "timestamp": "11:00:00",
                    "person_detected": True,
                    "person_location": "living_room",
                    "person_activity": "sitting",
                    "objects": []
                },
                {
                    "timestamp": "11:05:00",
                    "person_detected": False,
                    "person_location": None,
                    "person_activity": None,
                    "objects": []
                },
                {
                    "timestamp": "11:10:00",
                    "person_detected": False,
                    "person_location": None,
                    "person_activity": None,
                    "objects": []
                }
            ],
            expected_risk_score=70
        )
        scenarios.append(scenario4)
        
        # Scenario 5: Medication time check (MEDIUM HAZARD)
        scenario5 = SyntheticScenario(
            name="Medication time - no activity",
            ground_truth_hazard=True,
            events=[
                {
                    "timestamp": "09:00:00",
                    "person_detected": True,
                    "person_location": "bedroom",
                    "person_activity": "sitting",
                    "objects": []
                },
                {
                    "timestamp": "09:15:00",
                    "person_detected": False,
                    "person_location": None,
                    "person_activity": None,
                    "objects": []
                }
            ],
            expected_risk_score=55
        )
        scenarios.append(scenario5)
        
        # Scenario 6: Normal sitting/watching TV (LOW HAZARD)
        scenario6 = SyntheticScenario(
            name="Normal sitting activity",
            ground_truth_hazard=False,
            events=[
                {
                    "timestamp": "19:00:00",
                    "person_detected": True,
                    "person_location": "living_room",
                    "person_activity": "sitting",
                    "objects": []
                },
                {
                    "timestamp": "19:05:00",
                    "person_detected": True,
                    "person_location": "living_room",
                    "person_activity": "sitting",
                    "objects": []
                }
            ],
            expected_risk_score=5
        )
        scenarios.append(scenario6)
        
        # Scenario 7: Fridge open repeatedly (MEDIUM HAZARD - confusion)
        scenario7 = SyntheticScenario(
            name="Repeated fridge opening",
            ground_truth_hazard=True,
            events=[
                {
                    "timestamp": "10:00:00",
                    "person_detected": True,
                    "person_location": "kitchen",
                    "person_activity": "standing",
                    "objects": [{"type": "fridge", "confidence": 0.85}]
                },
                {
                    "timestamp": "10:01:00",
                    "person_detected": True,
                    "person_location": "kitchen",
                    "person_activity": "standing",
                    "objects": [{"type": "fridge", "confidence": 0.87}]
                },
                {
                    "timestamp": "10:02:00",
                    "person_detected": True,
                    "person_location": "kitchen",
                    "person_activity": "standing",
                    "objects": [{"type": "fridge", "confidence": 0.89}]
                },
                {
                    "timestamp": "10:03:00",
                    "person_detected": True,
                    "person_location": "kitchen",
                    "person_activity": "standing",
                    "objects": [{"type": "fridge", "confidence": 0.86}]
                }
            ],
            expected_risk_score=45
        )
        scenarios.append(scenario7)
        
        return scenarios


class Evaluator:
    """Evaluate system performance"""
    
    def __init__(self, reasoner: VLMReasoner = None):
        self.reasoner = reasoner or VLMReasoner(model_name="mistral")
        self.results = []
    
    def evaluate_scenario(self, scenario: SyntheticScenario) -> Dict:
        """Evaluate single scenario"""
        
        # Generate summary
        summary = scenario.generate_event_summary()
        
        # Get risk assessment
        assessment = self.reasoner.assess_hazard(
            summary,
            scenario.events
        )
        
        # Calculate metrics
        predicted_hazard = assessment["risk_score"] >= 50
        actual_hazard = scenario.ground_truth_hazard
        
        correct = predicted_hazard == actual_hazard
        score_error = abs(assessment["risk_score"] - scenario.expected_risk_score)
        
        result = {
            "scenario": scenario.name,
            "ground_truth_hazard": actual_hazard,
            "predicted_hazard": predicted_hazard,
            "correct": correct,
            "predicted_risk_score": assessment["risk_score"],
            "expected_risk_score": scenario.expected_risk_score,
            "score_error": score_error,
            "risk_level": assessment["risk_level"],
            "action": assessment["action"],
            "reasoning": assessment["reasoning"]
        }
        
        self.results.append(result)
        return result
    
    def evaluate_all(self, scenarios: List[SyntheticScenario]):
        """Evaluate all scenarios"""
        print("\n" + "="*80)
        print("BENCHMARK EVALUATION - CARE-VLM")
        print("="*80 + "\n")
        
        for scenario in scenarios:
            result = self.evaluate_scenario(scenario)
            
            # Print result
            status = "✅ PASS" if result["correct"] else "❌ FAIL"
            print(f"{status} | {result['scenario']}")
            print(f"     Predicted: {result['predicted_risk_score']}/100 ({result['risk_level']})")
            print(f"     Expected:  {result['expected_risk_score']}/100")
            print(f"     Error:     {result['score_error']:.0f} points")
            print()
        
        # Summary statistics
        self._print_summary()
    
    def _print_summary(self):
        """Print evaluation summary"""
        total = len(self.results)
        correct = sum(1 for r in self.results if r["correct"])
        accuracy = (correct / total * 100) if total > 0 else 0
        
        avg_error = sum(r["score_error"] for r in self.results) / total if total > 0 else 0
        
        # Hazard detection metrics
        true_positives = sum(1 for r in self.results 
                           if r["correct"] and r["ground_truth_hazard"])
        false_positives = sum(1 for r in self.results 
                            if not r["correct"] and r["predicted_hazard"])
        false_negatives = sum(1 for r in self.results 
                            if not r["correct"] and not r["predicted_hazard"])
        
        precision = true_positives / (true_positives + false_positives + 1e-6)
        recall = true_positives / (true_positives + false_negatives + 1e-6)
        f1 = 2 * (precision * recall) / (precision + recall + 1e-6)
        
        print("="*80)
        print("SUMMARY STATISTICS")
        print("="*80)
        print(f"Overall Accuracy:       {accuracy:.1f}% ({correct}/{total})")
        print(f"Avg Risk Score Error:   {avg_error:.1f} points")
        print()
        print("Hazard Detection Metrics:")
        print(f"  Precision:  {precision:.2f} (correct hazards / all predicted hazards)")
        print(f"  Recall:     {recall:.2f} (caught hazards / actual hazards)")
        print(f"  F1-Score:   {f1:.2f}")
        print()
        print(f"False Positives: {false_positives} (unnecessary alerts)")
        print(f"False Negatives: {false_negatives} (missed hazards)")
        print("="*80 + "\n")
        
        return {
            "accuracy": accuracy,
            "avg_error": avg_error,
            "precision": precision,
            "recall": recall,
            "f1_score": f1
        }
    
    def export_results(self, output_file: str = "benchmark_results.json"):
        """Export detailed results"""
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"Results exported to {output_file}")


if __name__ == "__main__":
    # Create evaluator
    evaluator = Evaluator()
    
    # Get scenarios
    scenarios = BenchmarkSuite.create_scenarios()
    
    # Run evaluation
    evaluator.evaluate_all(scenarios)
    
    # Export results
    evaluator.export_results("benchmark_results.json")
