import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { TrendingUp } from "lucide-react";
import { getPatient, getPatientAssessments, getAssessmentResults } from "../../services/index.js";
import PatientHeader from "../../components/clinical/PatientHeader.jsx";
import AssessmentAnalysisSections from "../../components/clinical/AssessmentAnalysisSections.jsx";
import ExportPanel from "../../components/clinical/ExportPanel.jsx";
import Status from "../../components/common/Status.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import Skeleton from "../../components/common/Skeleton.jsx";
import Button from "../../components/common/Button.jsx";
import clinicalStyles from "../../components/clinical/clinical.module.css";
import styles from "./PatientProfile.module.css";

export default function ClinicalPatientProfile() {
  const { patientId } = useParams();
  const navigate = useNavigate();
  const [patient, setPatient] = useState(null);
  const [history, setHistory] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId]);

  function load() {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([getPatient(patientId), getPatientAssessments(patientId)])
      .then(async ([patientData, assessments]) => {
        if (!patientData) throw new Error("NOT_FOUND");
        const bundles = await Promise.all(assessments.map((a) => getAssessmentResults(a.id)));
        if (cancelled) return;
        setPatient(patientData);
        setHistory(bundles);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message === "NOT_FOUND" ? "NOT_FOUND" : "Something went wrong loading this patient.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }

  if (loading) {
    return (
      <div>
        <Skeleton height="80px" radius="md" />
        <div style={{ marginTop: 24 }}>
          <Skeleton height="320px" radius="lg" />
        </div>
      </div>
    );
  }

  if (error === "NOT_FOUND") {
    return (
      <EmptyState
        title="Patient not found"
        description={`No patient exists with ID "${patientId}".`}
        action={<Button variant="secondary" onClick={() => navigate("/clinical/patients")}>Back to patients</Button>}
      />
    );
  }

  if (error) {
    return <ErrorState description={error} onRetry={load} />;
  }

  const latest = history[history.length - 1];
  const previous = history.slice(0, -1).reverse();

  return (
    <div>
      <PatientHeader patient={patient} onExport={() => window.print()} />

      {!latest ? (
        <EmptyState title="No assessments yet" description="This patient has not completed an assessment." />
      ) : (
        <>
          <AssessmentAnalysisSections results={latest} history={history} />
          <div className={clinicalStyles.sectionSpacer}>
            <Link
              to={`/clinical/assessments/${latest.assessment.id}/compare`}
              style={{ color: "var(--cobalt-deep)", fontWeight: 600, fontSize: 14, display: "inline-flex", alignItems: "center" }}
            >
              <TrendingUp size={14} style={{ marginRight: 4 }} aria-hidden="true" />
              View longitudinal trends
            </Link>
          </div>
        </>
      )}

      {previous.length > 0 && (
        <section id="previous-assessments" className={`${clinicalStyles.panel} ${clinicalStyles.sectionSpacer}`}>
          <div className={clinicalStyles.panelHeader}>
            <h2 className={clinicalStyles.panelTitle}>Previous assessments</h2>
          </div>
          <div className={styles.previousList}>
            {previous.map(({ assessment }) => (
              <div
                key={assessment.id}
                className={styles.previousRow}
                role="button"
                tabIndex={0}
                onClick={() => navigate(`/clinical/assessments/${assessment.id}`)}
                onKeyDown={(e) => e.key === "Enter" && navigate(`/clinical/assessments/${assessment.id}`)}
              >
                <div className={styles.previousMeta}>
                  <strong>{assessment.date}</strong>
                  <span>{assessment.language}</span>
                  <span>{assessment.task.name}</span>
                </div>
                <Status tone={assessment.screening.needsClinicianReview ? "attention" : "positive"}>
                  {assessment.screening.needsClinicianReview ? "Review recommended" : "Reviewed"}
                </Status>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className={clinicalStyles.sectionSpacer}>
        <ExportPanel />
      </div>
    </div>
  );
}
