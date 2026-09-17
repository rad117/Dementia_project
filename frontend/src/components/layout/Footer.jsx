import { Link } from "react-router-dom";
import styles from "./Footer.module.css";

export default function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={`container ${styles.inner}`}>
        <div className={styles.brandCol}>
          <p className={styles.logo}>CognitiveAssist</p>
          <p className={styles.tagline}>Multilingual cognitive screening and longitudinal speech analysis.</p>
        </div>
        <nav className={styles.links} aria-label="Footer">
          <a href="#how-it-works">Product</a>
          <a href="#multilingual">Approach</a>
          <a href="#privacy">Privacy</a>
          <a href="#accessibility-note">Accessibility</a>
          <a href="mailto:hello@cognitiveassist.example">Contact</a>
          <Link to="/role">Login</Link>
        </nav>
      </div>
      <div className={`container ${styles.bottom}`}>
        <span>© 2026 CognitiveAssist. Demo product — not a certified medical device.</span>
      </div>
    </footer>
  );
}
