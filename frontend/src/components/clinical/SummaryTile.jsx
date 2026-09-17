import styles from "./SummaryTile.module.css";

export default function SummaryTile({ icon: Icon, label, value }) {
  return (
    <div className={styles.tile}>
      {Icon && <Icon size={18} aria-hidden="true" className={styles.icon} />}
      <p className={styles.value}>{value}</p>
      <p className={styles.label}>{label}</p>
    </div>
  );
}
