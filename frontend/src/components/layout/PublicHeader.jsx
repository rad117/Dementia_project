import { Link } from "react-router-dom";
import Button from "../common/Button.jsx";
import styles from "./PublicHeader.module.css";

export default function PublicHeader() {
  return (
    <header className={styles.header}>
      <div className={`${styles.inner} container`}>
        <Link to="/" className={styles.logo}>
          CognitiveAssist
        </Link>
        <nav className={styles.nav} aria-label="Primary">
          <a href="#how-it-works">How it works</a>
          <a href="#multilingual">Approach</a>
          <a href="#privacy">Privacy</a>
        </nav>
        <div className={styles.actions}>
          <Button as={Link} to="/role" variant="secondary" size="sm">
            Login
          </Button>
          <Button as={Link} to="/role" variant="accent" size="sm">
            Get Started
          </Button>
        </div>
      </div>
    </header>
  );
}
