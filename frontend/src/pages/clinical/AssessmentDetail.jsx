import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { ChevronLeft, TrendingUp } from "lucide-react";
import { getAssessment, getPatient, getPatientAssessments, getAssessmentResults } from "../../services/index.js";
import AssessmentAnalysisSections from "../../components/clinical/AssessmentAnalysisSections.jsx";
import ExportPanel from "../../components/clinical/ExportPanel.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import Skeleton from "../../components/common/Skeleton.jsx";
import Button from "../../components/common/Button.jsx";
import IconButton from "../../components/common/IconButton.jsx";
import FadeInUp from "../../components/motion/FadeInUp.jsx";
import clinicalStyles from "../../components/clinical/clinical.module.css";

export default function ClinicalAssessmentDetail() {
  const { assessmentId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessmentId]);

  function load() {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getAssessment(assessmentId)
      .then(async (assessment) => {
        if (!assessment) throw new Error("NOT_FOUND");
        const [patient, siblings, results] = await Promise.all([
          getPatient(assessment.patientId),
          getPatientAssessments(assessment.patientId),
          getAssessmentResults(assessmentId),
        ]);
        const history = await Promise.all(siblings.map((a) => (a.id === assessmentId ? results : getAssessmentResults(a.id))));
        if (cancelled) return;
        setData({ patient, results, history });
      })
      .catch((err) => {
        if (!cancelled) setError(err.message === "NOT_FOUND" ? "NOT_FOUND" : "Something went wrong loading this assessment.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }

  if (loading) return <Skeleton height="420px" radius="lg" />;

  if (error === "NOT_FOUND") {
    return (
      <EmptyState
        title="Assessment not found"
        description={`No assessment exists with ID "${assessmentId}".`}
        action={<Button variant="secondary" onClick={() => navigate("/clinical/patients")}>Back to patients</Button>}
      />
    );
  }

  if (error) return <ErrorState description={error} onRetry={load} />;

  const { patient, results, history } = data;
  const hasMultipleAssessments = history.length >= 2;

  return (
    <div>
      <FadeInUp style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <IconButton icon={ChevronLeft} label="Back to patient" variant="outline" onClick={() => navigate(`/clinical/patients/${patient.id}`)} />
          <div>
            <p style={{ fontSize: 12, color: "var(--muted)", fontWeight: 700, textTransform: "uppercase" }}>{patient.name} · {patient.id}</p>
            <h1 style={{ fontSize: 22 }}>{results.assessment.date} · {results.assessment.task.name}</h1>
          </div>
        </div>
        {hasMultipleAssessments && (
          <Link to={`/clinical/assessments/${assessmentId}/compare`}>
            <Button variant="secondary">
              <TrendingUp size={16} aria-hidden="true" /> Compare over time
            </Button>
          </Link>
        )}
      </FadeInUp>

      <AssessmentAnalysisSections results={results} history={history} />

      <div className={clinicalStyles.sectionSpacer}>
        <ExportPanel fileName={`memora-assessment-${patient.id}-${results.assessment.date}.pdf`} />
      </div>
    </div>
  );
}
