import clinicalStyles from "./clinical.module.css";
import styles from "./AISummary.module.css";
import Badge from "../common/Badge.jsx";

const SECTIONS = [
  { key: "overview", label: "Overview", isText: true },
  { key: "observedChanges", label: "Observed changes" },
  { key: "speechPatterns", label: "Speech patterns" },
  { key: "languagePatterns", label: "Language patterns" },
  { key: "assessmentQuality", label: "Assessment quality" },
  { key: "reviewPoints", label: "Review points" },
];

export default function AISummary({ summary }) {
  return (
    <div className={clinicalStyles.panel}>
      <div className={clinicalStyles.panelHeader}>
        <h2 className={clinicalStyles.panelTitle}>AI-assisted summary</h2>
        <Badge tone="demo">Deterministic, structured-data summary</Badge>
      </div>
      {SECTIONS.map((section) => (
        <div key={section.key} className={styles.section}>
          <h3 className={styles.sectionTitle}>{section.label}</h3>
          {section.isText ? (
            <p className={styles.text}>{summary[section.key]}</p>
          ) : (
            <ul className={styles.list}>
              {summary[section.key].map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
      <p className={styles.disclaimer}>{summary.disclaimer}</p>
    </div>
  );
}
