import styles from "./Skeleton.module.css";

export default function Skeleton({ width = "100%", height = "16px", radius = "sm", className = "" }) {
  return (
    <span
      className={`${styles.skeleton} ${className}`}
      style={{ width, height, borderRadius: `var(--radius-${radius})` }}
      aria-hidden="true"
    />
  );
}
