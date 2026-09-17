import { useState } from "react";
import clinicalStyles from "./clinical.module.css";
import styles from "./TranscriptViewer.module.css";

const TYPE_LABEL = { filler: "Filler", repetition: "Repetition", revision: "Revision", concept: "Concept" };

function formatTimestamp(sec) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function TranscriptViewer({ transcript }) {
  const [showAnnotations, setShowAnnotations] = useState(false);

  if (!transcript || transcript.segments.length === 0) {
    return (
      <div className={clinicalStyles.panel}>
        <h2 className={clinicalStyles.panelTitle}>Transcript</h2>
        <p style={{ color: "var(--muted)", marginTop: 12 }}>Transcript unavailable for this assessment.</p>
      </div>
    );
  }

  return (
    <div className={clinicalStyles.panel}>
      <div className={clinicalStyles.panelHeader}>
        <div>
          <h2 className={clinicalStyles.panelTitle}>Transcript</h2>
          <p className={clinicalStyles.panelSubtitle}>{transcript.generatedNote}</p>
        </div>
        <label className={styles.toggle}>
          <input type="checkbox" checked={showAnnotations} onChange={(e) => setShowAnnotations(e.target.checked)} />
          Show annotations
        </label>
      </div>
      <div className={styles.segments}>
        {transcript.segments.map((seg) => (
          <p key={seg.id} className={styles.segment}>
            <span className={styles.timestamp}>{formatTimestamp(seg.startSec)}</span>
            <span className={showAnnotations && seg.type !== "normal" ? styles[`tag-${seg.type}`] : undefined}>
              {seg.text}
            </span>
            {showAnnotations && seg.type !== "normal" && (
              <span className={styles.annotationLabel}>{TYPE_LABEL[seg.type]}</span>
            )}
          </p>
        ))}
      </div>
    </div>
  );
}
