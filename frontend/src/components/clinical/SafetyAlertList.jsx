import { Link } from "react-router-dom";
import styles from "./SafetyAlertList.module.css";

function formatTime(iso) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

/**
 * Safety-monitoring alerts, most recent first. Shared by the Safety monitor
 * page, the clinical overview and the patient profile.
 *
 * - patientNameById: when given, each alert links to its patient's profile.
 * - compact: hides the evidence / suggested-action lines (dashboard summary).
 */
export default function SafetyAlertList({ alerts, patientNameById, compact = false }) {
  return (
    <ul className={styles.alertList}>
      {alerts.map((a, i) => (
        <li key={`${a.at}-${a.kind}-${a.patient_id ?? ""}-${i}`} className={`${styles.alert} ${styles[a.level] ?? ""}`}>
          <div className={styles.alertTop}>
            <span className={styles.level}>{a.level}</span>
            {a.source === "demo" && <span className={styles.demoTag}>Simulated</span>}
            {patientNameById && a.patient_id && (
              <Link className={styles.patient} to={`/clinical/patients/${a.patient_id}`}>
                {patientNameById[a.patient_id] ?? a.patient_id}
              </Link>
            )}
            <time className={styles.time} dateTime={a.at}>
              {formatTime(a.at)}
            </time>
          </div>
          <p className={styles.summary}>{a.summary}</p>
          {!compact && (
            <>
              <p className={styles.meta}>
                <strong>Why:</strong> {a.evidence}
              </p>
              <p className={styles.meta}>
                <strong>Suggested action:</strong> {a.action}
              </p>
            </>
          )}
          {compact && <p className={styles.meta}>{a.action}</p>}
        </li>
      ))}
    </ul>
  );
}
