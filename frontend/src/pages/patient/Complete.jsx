import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { useAssessment } from "../../app/AssessmentContext.jsx";
import Button from "../../components/common/Button.jsx";
import styles from "./patientPages.module.css";

export default function PatientComplete() {
  const { assessmentId, reset } = useAssessment();
  const navigate = useNavigate();

  useEffect(() => {
    if (!assessmentId) navigate("/patient", { replace: true });
  }, [assessmentId, navigate]);

  function handleDone() {
    reset();
    navigate("/patient");
  }

  if (!assessmentId) return null;

  return (
    <div className={styles.screen} style={{ alignItems: "center", textAlign: "center", paddingTop: "var(--space-7)" }}>
      <CheckCircle2 size={56} strokeWidth={1.5} style={{ color: "var(--green)" }} aria-hidden="true" />
      <h1 className={styles.greeting}>Assessment complete</h1>
      <p style={{ fontSize: 17, color: "var(--slate)", maxWidth: 380 }}>
        Your response has been recorded successfully. Your results will be reviewed by the clinical team.
      </p>
      <Button variant="accent" size="lg" onClick={handleDone} style={{ marginTop: "var(--space-4)" }}>
        Return home
      </Button>
    </div>
  );
}
