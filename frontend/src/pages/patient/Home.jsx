import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Mic, Grid3x3 } from "lucide-react";
import { useSession } from "../../app/SessionContext.jsx";
import { useAssessment } from "../../app/AssessmentContext.jsx";
import { getPatient, getPatientAssessments } from "../../services/index.js";
import { pictureDescriptionTask } from "../../data/mockTasks.js";
import Button from "../../components/common/Button.jsx";
import Skeleton from "../../components/common/Skeleton.jsx";
import styles from "./patientPages.module.css";

export default function PatientHome() {
  const { participant } = useSession();
  const { reset } = useAssessment();
  const navigate = useNavigate();
  const [patient, setPatient] = useState(null);
  const [assessmentCount, setAssessmentCount] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    reset();
    Promise.all([getPatient(participant.patientId), getPatientAssessments(participant.patientId)]).then(
      ([patientData, assessments]) => {
        if (cancelled) return;
        setPatient(patientData);
        setAssessmentCount(assessments.length);
        setLoading(false);
      }
    );
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [participant.patientId]);

  return (
    <div className={styles.screen}>
      <div>
        <p className={styles.eyebrow}>DEMO DATA</p>
        <h1 className={styles.greeting}>
          {loading ? <Skeleton width="240px" height="32px" /> : `Hello, ${patient?.name?.split(" ")[0] ?? participant.name}`}
        </h1>
      </div>

      <div className={styles.card}>
        <h2 className={styles.taskTitle}>Today's assessment</h2>
        <p className={styles.taskMeta}>{pictureDescriptionTask.name} · Estimated time: {pictureDescriptionTask.estimatedMinutes}</p>
        <Button variant="accent" size="lg" className={styles.primaryAction} onClick={() => navigate("/patient/language")}>
          <Mic size={20} aria-hidden="true" /> Begin
        </Button>
      </div>

      <div className={styles.card}>
        <h2 className={styles.taskTitle}>Your progress</h2>
        <p className={styles.taskMeta}>
          {loading ? <Skeleton width="180px" height="16px" /> : `${assessmentCount} assessment${assessmentCount === 1 ? "" : "s"} completed so far.`}
        </p>
      </div>

      <button type="button" className={styles.activityCard} onClick={() => navigate("/patient/activities")}>
        <span className={styles.activityIcon}>
          <Grid3x3 size={22} aria-hidden="true" />
        </span>
        <span>
          <p className={styles.activityTitle}>Optional activities</p>
          <p className={styles.activityDescription}>Short, relaxed exercises you can try any time.</p>
        </span>
      </button>
    </div>
  );
}
