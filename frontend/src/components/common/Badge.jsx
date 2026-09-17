import styles from "./Badge.module.css";

export default function Badge({ tone = "default", children }) {
  return <span className={`${styles.badge} ${styles[tone]}`}>{children}</span>;
}
