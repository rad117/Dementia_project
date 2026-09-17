import styles from "./EmptyState.module.css";

export default function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className={styles.wrap}>
      {Icon && <Icon size={28} strokeWidth={1.5} aria-hidden="true" className={styles.icon} />}
      <p className={styles.title}>{title}</p>
      {description && <p className={styles.description}>{description}</p>}
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
}
