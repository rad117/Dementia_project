import { Link, Outlet } from "react-router-dom";
import styles from "./AuthLayout.module.css";

export default function AuthLayout() {
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <Link to="/" className={styles.logo}>
          CognitiveAssist
        </Link>
      </header>
      <main className={styles.content}>
        <Outlet />
      </main>
    </div>
  );
}
