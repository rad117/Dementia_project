import clinicalStyles from "./clinical.module.css";
import styles from "./ModelExplanation.module.css";
import Badge from "../common/Badge.jsx";

export default function ModelExplanation({ explanation }) {
  return (
    <div className={clinicalStyles.panel}>
      <div className={clinicalStyles.panelHeader}>
        <h2 className={clinicalStyles.panelTitle}>Why was this assessment flagged?</h2>
        {explanation.isDemoExplanation && <Badge tone="demo">Demo explanation</Badge>}
      </div>
      <ul className={styles.list}>
        {explanation.indicators.map((indicator) => (
          <li key={indicator}>{indicator}</li>
        ))}
      </ul>
      <p className={styles.note}>These indicators contributed to the model's screening output.</p>
      <p className={styles.modelVersion}>Model version: {explanation.modelVersion}</p>
    </div>
  );
}
