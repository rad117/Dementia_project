import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check } from "lucide-react";
import { useAssessment } from "../../app/AssessmentContext.jsx";
import {
    getAssessmentResults,
    uploadAssessmentAudio,
} from "../../services/index.js";
import styles from "./Processing.module.css";

const STEPS = [
    "Uploading recording",
    "Preparing speech",
    "Analyzing language",
    "Preparing assessment",
];

const MAX_RESULT_ATTEMPTS = 12;
const RESULT_POLL_DELAY_MS = 1000;

function wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

export default function Processing() {
    const navigate = useNavigate();
    const { assessmentId, audioBlob, setResults } = useAssessment();
    const [step, setStep] = useState(0);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!assessmentId || !audioBlob) {
            navigate("/patient/task", { replace: true });
            return;
        }

        let cancelled = false;

        async function waitForResults() {
            for (let attempt = 0; attempt < MAX_RESULT_ATTEMPTS; attempt += 1) {
                const results = await getAssessmentResults(assessmentId);

                if (cancelled) return;

                if (results?.features) {
                    setResults(results);
                    return;
                }

                await wait(RESULT_POLL_DELAY_MS);
            }

            throw new Error(
                "Your recording was uploaded, but the assessment results are taking longer than expected. Please try again."
            );
        }

        async function run() {
            try {
                setStep(0);

                await uploadAssessmentAudio(assessmentId, audioBlob);

                if (cancelled) return;

                setStep(1);
                await wait(350);

                if (cancelled) return;

                setStep(2);
                await wait(350);

                if (cancelled) return;

                setStep(3);
                await waitForResults();

                if (!cancelled) {
                    navigate("/patient/complete");
                }
            } catch (e) {
                if (!cancelled) {
                    setError(
                        e.message || "We couldn't process this recording."
                    );
                }
            }
        }

        run();

        return () => {
            cancelled = true;
        };
    }, [
        assessmentId,
        audioBlob,
        navigate,
        setResults,
    ]);

    if (error) {
        return (
            <div className="memora-flow">
                <div className="memora-flow-head">
                    <p className="memora-kicker">Assessment</p>
                    <h1>Recording could not be processed</h1>
                    <p>{error}</p>
                </div>

                <button
                    className="memora-retry"
                    onClick={() => window.location.reload()}
                >
                    Try again
                </button>
            </div>
        );
    }

    return (
        <div className="memora-flow">
            <div className="memora-flow-head">
                <p className="memora-kicker">Assessment</p>
                <h1>Processing your recording</h1>
                <p>This may take a moment.</p>
            </div>

            <div className={styles.panel}>
                {STEPS.map((label, i) => (
                    <div
                        className={`${styles.row} ${i === step ? styles.current : ""
                            }`}
                        key={label}
                    >
                        <span className={styles.icon}>
                            {i < step ? (
                                <Check size={17} />
                            ) : i === step ? (
                                <span className={styles.dot} />
                            ) : null}
                        </span>

                        <span>{label}</span>

                        {i === step && <small>In progress</small>}
                    </div>
                ))}
            </div>
        </div>
    );
}