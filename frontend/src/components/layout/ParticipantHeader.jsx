import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronLeft, CircleHelp } from "lucide-react";
import IconButton from "../common/IconButton.jsx";
import styles from "./ParticipantHeader.module.css";

export default function ParticipantHeader({ onBack, showHelp = true }) {
  const navigate = useNavigate();
  const [helpOpen, setHelpOpen] = useState(false);

  return (
    <header className={styles.header}>
      <div className={styles.side}>
        {onBack !== null ? (
          <IconButton icon={ChevronLeft} label="Go back" onClick={onBack ?? (() => navigate(-1))} variant="outline" />
        ) : (
          <span />
        )}
      </div>
      <Link to="/patient" className={styles.logo} aria-label="Memora Home">
        Memora
      </Link>
      <div className={styles.side} style={{ justifyContent: "flex-end" }}>
        {showHelp && (
          <button type="button" className={styles.help} onClick={() => setHelpOpen((v) => !v)} aria-expanded={helpOpen}>
            <CircleHelp size={18} aria-hidden="true" />
            <span>Need help?</span>
          </button>
        )}
      </div>
      {helpOpen && (
        <div role="status" className={styles.helpNote}>
          A staff member nearby can help you with this assessment at any time.
        </div>
      )}
    </header>
  );
}
