import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAssessment } from "../../app/AssessmentContext.jsx";
import { supportedLanguages } from "../../data/mockTasks.js";
import Button from "../../components/common/Button.jsx";
import pageStyles from "./patientPages.module.css";
import styles from "./Language.module.css";

export default function PatientLanguage() {
  const { language, setLanguage } = useAssessment();
  const [selected, setSelected] = useState(language);
  const navigate = useNavigate();

  function handleContinue() {
    setLanguage(selected);
    navigate("/patient/instructions");
  }

  return (
    <div className={pageStyles.screen}>
      <h1 className={pageStyles.greeting}>Choose your language</h1>
      <div className={styles.grid} role="radiogroup" aria-label="Choose your language">
        {supportedLanguages.map((lang) => (
          <button
            key={lang.code}
            type="button"
            role="radio"
            aria-checked={selected?.code === lang.code}
            className={`${styles.option} ${selected?.code === lang.code ? styles.selected : ""}`}
            onClick={() => setSelected(lang)}
          >
            {lang.label}
          </button>
        ))}
      </div>
      <Button variant="accent" size="lg" className={pageStyles.primaryAction} disabled={!selected} onClick={handleContinue}>
        Continue
      </Button>
    </div>
  );
}
