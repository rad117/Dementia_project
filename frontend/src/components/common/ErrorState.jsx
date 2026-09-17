import { AlertTriangle } from "lucide-react";
import Button from "./Button.jsx";
import styles from "./ErrorState.module.css";

export default function ErrorState({ title = "Something went wrong", description, onRetry, retryLabel = "Try again" }) {
  return (
    <div className={styles.wrap} role="alert">
      <AlertTriangle size={24} aria-hidden="true" className={styles.icon} />
      <p className={styles.title}>{title}</p>
      {description && <p className={styles.description}>{description}</p>}
      {onRetry && (
        <Button variant="secondary" onClick={onRetry} className={styles.retry}>
          {retryLabel}
        </Button>
      )}
    </div>
  );
}
