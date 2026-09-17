import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useSession } from "../../app/SessionContext.jsx";
import { useAssessment } from "../../app/AssessmentContext.jsx";
import { pictureDescriptionTask } from "../../data/mockTasks.js";
import { createAssessment } from "../../services/index.js";
import PictureStimulus from "../../components/assessment/PictureStimulus.jsx";
import Button from "../../components/common/Button.jsx";
import Badge from "../../components/common/Badge.jsx";
import styles from "./patientPages.module.css";

export default function PatientTask() {
  const { participant } = useSession();
  const { language, assessmentId, setAssessmentId } = useAssessment();
  const navigate = useNavigate();

  useEffect(() => {
    if (!language) {
      navigate("/patient/language", { replace: true });
      return;
    }
    if (!assessmentId) {
      createAssessment({ patientId: participant.patientId, language: language.label, taskId: pictureDescriptionTask.id }).then(
        (assessment) => setAssessmentId(assessment.id)
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language]);

  if (!language) return null;

  // Recording requires assessmentId to exist first (Recording redirects back
  // here otherwise) — keep Continue disabled until the in-flight
  // createAssessment call above has resolved, rather than racing it.
  const isPreparing = !assessmentId;

  return (
    <div className={styles.screen}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Badge tone="accent">{language.label}</Badge>
        <span style={{ fontSize: 13, color: "var(--muted)", fontWeight: 600 }}>Step 3 of 5</span>
      </div>
      <div className={styles.progressTrack}>
        <div className={styles.progressFill} style={{ width: "60%" }} />
      </div>

      <h1 className={styles.greeting}>{pictureDescriptionTask.prompt}</h1>
      <PictureStimulus />

      <Button
        variant="accent"
        size="lg"
        className={styles.primaryAction}
        disabled={isPreparing}
        onClick={() => navigate("/patient/recording")}
      >
        {isPreparing ? "Preparing…" : "Continue"}
      </Button>
    </div>
  );
}
