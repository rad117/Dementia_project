import styles from "./QualityCard.module.css";
import clinicalStyles from "./clinical.module.css";
import Status from "../common/Status.jsx";

export default function QualityCard({ quality }) {
  const isPoor = quality.audioQuality === "poor" || quality.asrConfidence < 0.75;

  return (
    <div className={clinicalStyles.panel}>
      <div className={clinicalStyles.panelHeader}>
        <h2 className={clinicalStyles.panelTitle}>Assessment quality</h2>
      </div>
      <div className={styles.grid}>
        <div>
          <p className={styles.label}>Audio quality</p>
          <Status tone={quality.audioQuality === "good" ? "positive" : "attention"}>
            {quality.audioQuality === "good" ? "Good" : "Fair"}
          </Status>
        </div>
        <div>
          <p className={styles.label}>Background noise</p>
          <p className={styles.value} style={{ textTransform: "capitalize" }}>{quality.backgroundNoise}</p>
        </div>
        <div>
          <p className={styles.label}>ASR confidence</p>
          <p className={styles.value}>{(quality.asrConfidence * 100).toFixed(0)}%</p>
        </div>
        <div>
          <p className={styles.label}>Language match</p>
          <p className={styles.value}>{quality.languageMatch ? "Yes" : "No"}</p>
        </div>
        <div>
          <p className={styles.label}>Recording duration</p>
          <p className={styles.value}>{quality.durationSeconds}s</p>
        </div>
        <div>
          <p className={styles.label}>Task completion</p>
          <p className={styles.value}>{quality.taskComplete ? "Complete" : "Incomplete"}</p>
        </div>
      </div>
      {isPoor && (
        <p className={styles.caution}>Interpret results cautiously. A cleaner recording may improve reliability.</p>
      )}
    </div>
  );
}
