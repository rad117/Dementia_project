import { useState } from "react";
import { Grid3x3, ListChecks, Shapes } from "lucide-react";
import { cognitiveActivities } from "../../data/mockTasks.js";
import IconButton from "../../components/common/IconButton.jsx";
import { ChevronLeft } from "lucide-react";
import MemoryMatch from "./activities/MemoryMatch.jsx";
import ObjectRecall from "./activities/ObjectRecall.jsx";
import PatternRecognition from "./activities/PatternRecognition.jsx";
import styles from "./patientPages.module.css";

const ICONS = { Grid3x3, ListChecks, Shapes };
const ACTIVITY_COMPONENTS = {
  "activity-memory-match": MemoryMatch,
  "activity-object-recall": ObjectRecall,
  "activity-pattern-recognition": PatternRecognition,
};

export default function PatientActivities() {
  const [activeId, setActiveId] = useState(null);

  if (activeId) {
    const activity = cognitiveActivities.find((a) => a.id === activeId);
    const ActivityComponent = ACTIVITY_COMPONENTS[activeId];
    return (
      <div className={styles.screen}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <IconButton icon={ChevronLeft} label="Back to activities" variant="outline" onClick={() => setActiveId(null)} />
          <h1 className={styles.greeting} style={{ fontSize: 22 }}>{activity.name}</h1>
        </div>
        <ActivityComponent onFinish={() => setActiveId(null)} />
      </div>
    );
  }

  return (
    <div className={styles.screen}>
      <h1 className={styles.greeting}>Optional activities</h1>
      <p style={{ color: "var(--muted)", fontSize: 15 }}>
        These short exercises are relaxed and optional — there's no time pressure or comparison with others.
      </p>
      <div className={styles.activityGrid}>
        {cognitiveActivities.map((activity) => {
          const Icon = ICONS[activity.icon];
          return (
            <button key={activity.id} type="button" className={styles.activityCard} onClick={() => setActiveId(activity.id)}>
              <span className={styles.activityIcon}>
                <Icon size={22} aria-hidden="true" />
              </span>
              <span>
                <p className={styles.activityTitle}>{activity.name}</p>
                <p className={styles.activityDescription}>{activity.description} · {activity.estimatedMinutes}</p>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
