import { Link } from "react-router-dom";
import styles from "./Footer.module.css";

export default function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={`container ${styles.inner}`}>
        <div className={styles.brandCol}>
          <p className={styles.logo}>Memora</p>
          <p className={styles.tagline}>Understanding memory through speech.</p>
        </div>
        <nav className={styles.links} aria-label="Footer">
          <a href="#how-it-works">How it works</a>
          <a href="#assessment-approach">Assessment</a>
          <a href="#clinical-review">Clinical review</a>
          <a href="#privacy">Privacy</a>
          <Link to="/role">Sign in</Link>
        </nav>
      </div>
      <div className={`container ${styles.bottom}`}>
        <span>© 2026 Memora. Cognitive screening & clinical review support platform — not a standalone diagnostic device.</span>
      </div>
    </footer>
  );
}
