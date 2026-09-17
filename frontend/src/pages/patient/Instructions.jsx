import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Volume2 } from "lucide-react";
import { useAssessment } from "../../app/AssessmentContext.jsx";
import { pictureDescriptionTask } from "../../data/mockTasks.js";
import Button from "../../components/common/Button.jsx";
import styles from "./patientPages.module.css";

export default function PatientInstructions() {
  const navigate = useNavigate();
  const { language } = useAssessment();
  const canSpeak = typeof window !== "undefined" && "speechSynthesis" in window;

  useEffect(() => {
    if (!language) navigate("/patient/language", { replace: true });
  }, [language, navigate]);

  if (!language) return null;

  function playInstructions() {
    if (!canSpeak) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(pictureDescriptionTask.instructions.join(". "));
    window.speechSynthesis.speak(utterance);
  }

  return (
    <div className={styles.screen}>
      <h1 className={styles.greeting}>Instructions</h1>
      <ul className={styles.instructionsList}>
        {pictureDescriptionTask.instructions.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>

      {canSpeak && (
        <Button variant="secondary" size="lg" onClick={playInstructions}>
          <Volume2 size={20} aria-hidden="true" /> Listen to instructions
        </Button>
      )}

      <Button variant="accent" size="lg" className={styles.primaryAction} onClick={() => navigate("/patient/task")}>
        Continue
      </Button>
    </div>
  );
}
