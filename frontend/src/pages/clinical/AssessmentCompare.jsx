import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RTooltip, ResponsiveContainer, Dot } from "recharts";
import { ChevronLeft } from "lucide-react";
import { getAssessment, getPatient, getPatientAssessments, getAssessmentResults } from "../../services/index.js";
import { useTheme } from "../../app/ThemeContext.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import Skeleton from "../../components/common/Skeleton.jsx";
import Button from "../../components/common/Button.jsx";
import IconButton from "../../components/common/IconButton.jsx";
import clinicalStyles from "../../components/clinical/clinical.module.css";
import styles from "./AssessmentCompare.module.css";

const CHART_COLORS = {
  light: { grid: "#D9D9D4", tick: "#686B72", line: "#2f55c8" },
  dark: { grid: "#4c4a50", tick: "#9c9a95", line: "#7091ff" },
};

const METRICS = [
  { key: "speechRate", label: "Speech rate", unit: "WPM", get: (f) => f.speech.speechRateWpm },
  { key: "pauseFrequency", label: "Pause frequency", unit: "/min", get: (f) => f.speech.pauseFrequencyPerMin },
  { key: "responseLatency", label: "Response latency", unit: "sec", get: (f) => f.speech.responseLatencySec },
  { key: "vocabularyDiversity", label: "Vocabulary diversity", unit: "", get: (f) => f.linguistic.vocabularyDiversity },
  { key: "conceptCoverage", label: "Concept coverage", unit: "", get: (f) => f.semantic.conceptCoverage },
  { key: "semanticRelevance", label: "Semantic relevance", unit: "", get: (f) => f.semantic.semanticRelevance },
];

function CustomTooltip({ active, payload, label, unit }) {
  if (!active || !payload?.length) return null;
  return (
    <div className={styles.tooltip}>
      <div>{label}</div>
      <div>{payload[0].value} {unit}</div>
    </div>
  );
}

export default function ClinicalAssessmentCompare() {
  const { assessmentId } = useParams();
  const navigate = useNavigate();
  const { theme } = useTheme();
  const chartColors = CHART_COLORS[theme];
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [metricKey, setMetricKey] = useState(METRICS[0].key);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getAssessment(assessmentId)
      .then(async (assessment) => {
        if (!assessment) throw new Error("NOT_FOUND");
        const [patient, siblings] = await Promise.all([
          getPatient(assessment.patientId),
          getPatientAssessments(assessment.patientId),
        ]);
        const history = await Promise.all(siblings.map((a) => getAssessmentResults(a.id)));
        if (cancelled) return;
        setData({ patient, history });
      })
      .catch((err) => {
        if (!cancelled) setError(err.message === "NOT_FOUND" ? "NOT_FOUND" : "Something went wrong loading trends.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [assessmentId]);

  const metric = METRICS.find((m) => m.key === metricKey);

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.history.map((bundle) => ({
      date: bundle.assessment.date,
      value: metric.get(bundle.features),
    }));
  }, [data, metric]);

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

  if (error) return <ErrorState description={error} />;

  const { patient, history } = data;

  return (
    <div>
      <div className={styles.header} style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <IconButton icon={ChevronLeft} label="Back to patient" variant="outline" onClick={() => navigate(`/clinical/patients/${patient.id}`)} />
        <div>
          <p style={{ fontSize: 12, color: "var(--muted)", fontWeight: 700, textTransform: "uppercase" }}>{patient.name} · {patient.id}</p>
          <h1 style={{ fontSize: 24 }}>Longitudinal analysis</h1>
        </div>
      </div>

      {history.length < 2 ? (
        <EmptyState
          title="Not enough assessments for a reliable trend."
          description="This patient needs at least two completed assessments to show a trend."
        />
      ) : (
        <>
          <div className={styles.metricTabs} role="tablist" aria-label="Select metric">
            {METRICS.map((m) => (
              <button
                key={m.key}
                type="button"
                role="tab"
                aria-selected={m.key === metricKey}
                className={`${styles.metricTab} ${m.key === metricKey ? styles.metricTabActive : ""}`}
                onClick={() => setMetricKey(m.key)}
              >
                {m.label}
              </button>
            ))}
          </div>

          <div className={`${clinicalStyles.panel} ${styles.chartPanel}`}>
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 12, fill: chartColors.tick, fontVariantNumeric: "tabular-nums" }} />
                <YAxis tick={{ fontSize: 12, fill: chartColors.tick, fontVariantNumeric: "tabular-nums" }} width={40} />
                <RTooltip content={<CustomTooltip unit={metric.unit} />} />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={chartColors.line}
                  strokeWidth={2.5}
                  dot={(props) => <Dot {...props} r={4} fill={chartColors.line} />}
                  activeDot={{ r: 6 }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>

            <div className={styles.pointsRow}>
              <div className={styles.pointStat}>
                <p className={styles.pointLabel}>Previous</p>
                <p className={styles.pointValue}>{chartData[chartData.length - 2]?.value} {metric.unit}</p>
              </div>
              <div className={styles.pointStat}>
                <p className={styles.pointLabel}>Current</p>
                <p className={styles.pointValue}>{chartData[chartData.length - 1]?.value} {metric.unit}</p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
