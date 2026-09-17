import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check } from "lucide-react";
import { useAssessment } from "../../app/AssessmentContext.jsx";
import { uploadAssessmentAudio, getAssessmentResults } from "../../services/index.js";
import ErrorState from "../../components/common/ErrorState.jsx";
import pageStyles from "./patientPages.module.css";
import styles from "./Processing.module.css";

const STEPS = ["Uploading recording", "Preparing speech", "Analyzing language", "Preparing results"];

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export default function PatientProcessing() {
  const { assessmentId, audioBlob, setResults } = useAssessment();
  const navigate = useNavigate();
  const [stepIndex, setStepIndex] = useState(0);
  const [failed, setFailed] = useState(false);
  const attemptRef = useRef(0);

  useEffect(() => {
    if (!assessmentId || !audioBlob) {
      navigate("/patient/recording", { replace: true });
      return;
    }
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessmentId, audioBlob]);

  async function run() {
    const myAttempt = ++attemptRef.current;
    setFailed(false);
    setStepIndex(0);
    try {
      await Promise.all([uploadAssessmentAudio(assessmentId, audioBlob), wait(1100)]);
      if (attemptRef.current !== myAttempt) return;
      setStepIndex(1);
      await wait(800);
      if (attemptRef.current !== myAttempt) return;
      setStepIndex(2);
      await wait(800);
      if (attemptRef.current !== myAttempt) return;
      setStepIndex(3);
      const results = await getAssessmentResults(assessmentId);
      if (attemptRef.current !== myAttempt) return;
      setResults(results);
      await wait(500);
      if (attemptRef.current !== myAttempt) return;
      navigate("/patient/complete");
    } catch {
      if (attemptRef.current === myAttempt) setFailed(true);
    }
  }

  if (!assessmentId || !audioBlob) return null;

  if (failed) {
    return (
      <div className={pageStyles.screen}>
        <h1 className={pageStyles.greeting}>Processing</h1>
        <ErrorState
          title="We couldn't reach the analysis service"
          description="Your assessment has not been lost. Please try again."
          onRetry={run}
        />
      </div>
    );
  }

  return (
    <div className={pageStyles.screen}>
      <h1 className={pageStyles.greeting}>Processing your assessment</h1>
      <div className={styles.stage}>
        <div className={styles.spinner} role="status" aria-label="Processing" />
        <ol className={styles.steps}>
          {STEPS.map((step, i) => {
            const done = i < stepIndex;
            const active = i === stepIndex;
            return (
              <li
                key={step}
                className={`${styles.step} ${done ? styles.stepDone : ""} ${active ? styles.stepActive : ""}`}
              >
                <span
                  className={`${styles.stepMarker} ${done ? styles.stepMarkerDone : ""} ${active ? styles.stepMarkerActive : ""}`}
                  aria-hidden="true"
                >
                  {done && <Check size={12} />}
                </span>
                {step}
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}
