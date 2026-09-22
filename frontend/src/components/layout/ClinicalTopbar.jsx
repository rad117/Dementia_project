import { useNavigate } from "react-router-dom";
import { Menu, Search, Bell, LogOut, Moon, Sun } from "lucide-react";
import { useState } from "react";
import { useSession } from "../../app/SessionContext.jsx";
import { useTheme } from "../../app/ThemeContext.jsx";
import IconButton from "../common/IconButton.jsx";
import styles from "./ClinicalTopbar.module.css";

export default function ClinicalTopbar({ onMenuClick, reviewCount = 0 }) {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  const { clinicalUser, logoutClinical } = useSession();
  const { theme, toggleTheme } = useTheme();

  function onSearchSubmit(e) {
    e.preventDefault();
    if (query.trim()) {
      navigate(`/clinical/patients?query=${encodeURIComponent(query.trim())}`);
    }
  }

  return (
    <header className={styles.topbar}>
      <IconButton icon={Menu} label="Open navigation" onClick={onMenuClick} className={styles.menuBtn} variant="outline" />

      <form className={styles.search} onSubmit={onSearchSubmit} role="search">
        <Search size={16} aria-hidden="true" />
        <input
          type="search"
          placeholder="Search patients or patient ID"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search patients or patient ID"
        />
      </form>

      <div className={styles.actions}>
        <button
          type="button"
          className={styles.iconWithBadge}
          onClick={() => navigate("/clinical#recent-assessments")}
          aria-label={`Review queue, ${reviewCount} awaiting review`}
        >
          <Bell size={18} aria-hidden="true" />
          {reviewCount > 0 && <span className={styles.badge}>{reviewCount}</span>}
        </button>
        <div className={styles.profile}>
          <span className={styles.avatar} aria-hidden="true">
            {(clinicalUser?.name ?? "CP").slice(0, 2).toUpperCase()}
          </span>
          <span className={styles.profileName}>{clinicalUser?.name ?? "Clinical Professional"}</span>
        </div>
        <IconButton
          icon={theme === "dark" ? Sun : Moon}
          label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          variant="outline"
          onClick={toggleTheme}
          className={styles.themeToggle}
        />
        <IconButton
          icon={LogOut}
          label="Log out"
          variant="outline"
          onClick={() => {
            logoutClinical();
            navigate("/");
          }}
        />
      </div>
    </header>
  );
}
