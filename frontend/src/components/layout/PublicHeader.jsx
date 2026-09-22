import { Link } from "react-router-dom";
import { Moon, Sun } from "lucide-react";
import Button from "../common/Button.jsx";
import IconButton from "../common/IconButton.jsx";
import { useTheme } from "../../app/ThemeContext.jsx";
import styles from "./PublicHeader.module.css";

export default function PublicHeader() {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className={styles.header}>
      <div className={`${styles.inner} container`}>
        <Link to="/" className={styles.logo} aria-label="Memora Home">
          <span className={styles.brandMark}>Memora</span>
        </Link>
        <nav className={styles.nav} aria-label="Primary navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#assessment-approach">Assessment</a>
          <a href="#clinical-review">Clinical Review</a>
          <a href="#privacy">Privacy</a>
        </nav>
        <div className={styles.actions}>
          <IconButton
            icon={theme === "dark" ? Sun : Moon}
            label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            variant="outline"
            onClick={toggleTheme}
          />
          <Button as={Link} to="/role" variant="secondary" size="sm">
            Sign In
          </Button>
          <Button as={Link} to="/role" variant="accent" size="sm">
            Get Started
          </Button>
        </div>
      </div>
    </header>
  );
}
