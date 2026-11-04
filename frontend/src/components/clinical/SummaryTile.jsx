import styles from "./SummaryTile.module.css";

export default function SummaryTile({ icon: Icon, label, value, style }) {
  return (
    <div className={styles.tile} style={style}>
      {Icon && <Icon size={18} aria-hidden="true" className={styles.icon} />}
      <p className={styles.value}>{value}</p>
      <p className={styles.label}>{label}</p>
    </div>
  );
}
