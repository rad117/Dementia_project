import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Mic, Grid3x3 } from "lucide-react";
import { useSession } from "../../app/SessionContext.jsx";
import { useAssessment } from "../../app/AssessmentContext.jsx";
import { getPatient, getPatientAssessments } from "../../services/index.js";
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
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    reset();

    Promise.all([
      getPatient(participant.patientId),
      getPatientAssessments(participant.patientId),
    ])
      .then(([patientData, assessments]) => {
        if (!cancelled) {
          setPatient(patientData);
          setAssessmentCount(assessments.length);
          setError(null);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(
            e.message || "We couldn't load your assessment history."
          );
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [participant.patientId, reset]);

  const firstName =
    patient?.name?.split(" ")[0] ??
    participant.name?.split(" ")[0] ??
    "Participant";

  return (
    <div className={styles.screen}>
      <div>
        <p className={styles.welcomeEyebrow}>Memora</p>

        <h1 className={styles.greeting}>
          {loading ? (
            <Skeleton width="260px" height="50px" />
          ) : (
            `Hello, ${firstName}`
          )}
        </h1>

        <p className={styles.subGreeting}>
          Complete today's assessment when you're ready.
        </p>
      </div>

      <section
        className={styles.primaryTaskCard}
        aria-labelledby="today-title"
      >
        <div className={styles.taskCardHeader}>
          <h2 id="today-title" className={styles.taskTitle}>
            Today's assessment
          </h2>

          <span className={styles.taskDurationBadge}>
            About 2 minutes
          </span>
        </div>

        <p className={styles.taskPromptSummary}>
          You will look at a picture and describe what you see.
        </p>

        <Button
          variant="accent"
          size="lg"
          className={styles.primaryAction}
          onClick={() => navigate("/patient/language")}
        >
          <Mic size={21} aria-hidden="true" />
          Start assessment
        </Button>
      </section>

      <div className={styles.progressCard}>
        <p className={styles.progressTitle}>Assessment history</p>

        {error ? (
          <p className={styles.progressMeta} role="alert">
            {error}
          </p>
        ) : (
          <p className={styles.progressMeta}>
            {loading ? (
              <Skeleton width="210px" height="18px" />
            ) : (
              `${assessmentCount} completed assessment${assessmentCount === 1 ? "" : "s"
              }`
            )}
          </p>
        )}
      </div>

      <section className={styles.secondarySection}>
        <p className={styles.secondaryLabel}>Optional</p>

        <button
          className={styles.activityCard}
          onClick={() => navigate("/patient/activities")}
          type="button"
        >
          <span className={styles.activityIcon}>
            <Grid3x3 size={21} />
          </span>

          <span>
            <span className={styles.activityTitle}>Activities</span>
            <span className={styles.activityDescription}>
              Memory and attention activities.
            </span>
          </span>
        </button>
      </section>
    </div>
  );
}