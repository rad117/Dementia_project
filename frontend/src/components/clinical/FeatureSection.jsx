import clinicalStyles from "./clinical.module.css";
import styles from "./FeatureSection.module.css";
import Tooltip from "../common/Tooltip.jsx";

export default function FeatureSection({ title, items, footnote, children, bare = false }) {
  const content = (
    <>
      {title && (
        <div className={clinicalStyles.panelHeader}>
          <h2 className={clinicalStyles.panelTitle}>{title}</h2>
        </div>
      )}
      <dl className={styles.grid}>
        {items.map((item) => (
          <div key={item.label} className={styles.item}>
            <dt className={styles.label}>
              {item.tooltip ? <Tooltip label={item.tooltip}>{item.label}</Tooltip> : item.label}
            </dt>
            <dd className={styles.value}>
              {item.value}
              {item.unit ? <span className={styles.unit}> {item.unit}</span> : null}
            </dd>
          </div>
        ))}
      </dl>
      {footnote && <p className={styles.footnote}>{footnote}</p>}
      {children}
    </>
  );

  if (bare) return content;
  return <div className={clinicalStyles.panel}>{content}</div>;
}
