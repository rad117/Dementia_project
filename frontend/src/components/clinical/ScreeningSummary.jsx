import clinicalStyles from "./clinical.module.css";
import styles from "./ScreeningSummary.module.css";
import Badge from "../common/Badge.jsx";
import Bezel from "../common/Bezel.jsx";

export default function ScreeningSummary({ screening }) {
  const scoreOutOf100 = Math.round(screening.estimate * 100);

  return (
    <Bezel innerClassName="p-5">
      <div className={clinicalStyles.panelHeader}>
        <h2 className={clinicalStyles.panelTitle}>Screening estimate</h2>
        <Badge tone="demo">Illustrative screening output</Badge>
      </div>
      <p className={styles.score}>{scoreOutOf100} / 100</p>
      <p className={styles.caption}>
        This estimate is intended to support clinical review and is not a standalone diagnosis.
      </p>
      <p className={styles.modelVersion}>Model version: {screening.modelVersion}</p>
    </Bezel>
  );
}
