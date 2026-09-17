import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import clinicalStyles from "./clinical.module.css";
import styles from "./ChangeSummary.module.css";

const DIRECTION_ICON = { increased: TrendingUp, decreased: TrendingDown, steady: Minus };

export default function ChangeSummary({ whatChanged }) {
  return (
    <div className={clinicalStyles.panel}>
      <div className={clinicalStyles.panelHeader}>
        <h2 className={clinicalStyles.panelTitle}>What changed since the previous assessment?</h2>
      </div>
      {!whatChanged ? (
        <p className={styles.empty}>Not enough assessments for a reliable comparison. This patient needs at least two assessments.</p>
      ) : (
        <>
          <ul className={styles.list}>
            {whatChanged.map((item) => {
              const Icon = DIRECTION_ICON[item.direction];
              return (
                <li key={item.key} className={styles.item}>
                  <Icon size={16} aria-hidden="true" className={styles[`icon-${item.direction}`]} />
                  <span>
                    {item.label} {item.direction === "steady" ? "stayed steady" : `${item.direction} by ${item.percent}%`}
                    {" "}
                    <span className={styles.values}>
                      ({item.previousValue} → {item.currentValue}{item.unit ? ` ${item.unit}` : ""})
                    </span>
                  </span>
                </li>
              );
            })}
          </ul>
          <p className={styles.disclaimer}>Descriptive comparison only — changes should be interpreted in clinical context.</p>
        </>
      )}
    </div>
  );
}
