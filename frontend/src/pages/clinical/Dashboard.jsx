import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ClipboardList, AlertCircle, Users, Activity, ArrowRight } from "lucide-react";
import { getAllAssessments, getPatients } from "../../services/index.js";
import SummaryTile from "../../components/clinical/SummaryTile.jsx";
import AssessmentsTable from "../../components/clinical/AssessmentsTable.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import Skeleton from "../../components/common/Skeleton.jsx";
import Button from "../../components/common/Button.jsx";
import FadeInUp from "../../components/motion/FadeInUp.jsx";
import clinicalStyles from "../../components/clinical/clinical.module.css";
import styles from "./Dashboard.module.css";

export default function ClinicalDashboard() {
  const [assessments, setAssessments] = useState(null);
  const [patients, setPatients] = useState(null);
  const [error, setError] = useState(null);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    Promise.all([getAllAssessments(), getPatients()])
      .then(([a, p]) => {
        if (cancelled) return;
        setAssessments(a);
        setPatients(p);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "We couldn't load the caseload overview.");
      });
    return () => {
      cancelled = true;
    };
  }, [retryKey]);

  const patientNameById = useMemo(() => {
    const map = {};
    (patients ?? []).forEach((p) => (map[p.id] = p.name));
    return map;
  }, [patients]);

  const stats = useMemo(() => {
    if (!assessments || !patients) return null;
    const anchor = assessments.reduce((max, a) => (a.date > max ? a.date : max), "0000-00-00");
    const anchorDate = new Date(anchor);
    const recentCutoff = new Date(anchorDate);
    recentCutoff.setDate(recentCutoff.getDate() - 30);

    const needsReview = assessments.filter((a) => a.screening?.needsClinicianReview);
    const recent = assessments.filter((a) => new Date(a.date) >= recentCutoff);

    return {
      total: assessments.length,
      awaitingReview: needsReview.length,
      activePatients: patients.length,
      recentCount: recent.length,
      needsReview,
      recentRows: [...assessments].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 8),
    };
  }, [assessments, patients]);

  function toRows(list) {
    return list.map((assessment) => ({
      assessment,
      patientName: patientNameById[assessment.patientId] ?? assessment.patientId,
    }));
  }

  return (
    <div>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Clinical overview</h1>
          <p className={styles.subtitle}>Caseload triage, speech indicators, and longitudinal assessments.</p>
        </div>
        <Button as={Link} to="/clinical/patients" variant="secondary" size="md">
          View all patients <ArrowRight size={16} aria-hidden="true" />
        </Button>
      </div>

      {error && (
        <ErrorState description={error} onRetry={() => setRetryKey((k) => k + 1)} />
      )}

      {!error && (
        <>
          {/* Priority 1: Needs review queue */}
          <FadeInUp as="section" id="needs-review" className={`${clinicalStyles.panel} ${clinicalStyles.sectionSpacer}`}>
            <div className={clinicalStyles.panelHeader}>
              <div>
                <div className={styles.headerRow}>
                  <h2 className={clinicalStyles.panelTitle}>Needs review</h2>
                  {stats && stats.awaitingReview > 0 && (
                    <span className={styles.pendingBadge}>{stats.awaitingReview} pending</span>
                  )}
                </div>
                <p className={clinicalStyles.panelSubtitle}>
                  Assessments flagged with speech or language indicator shifts requiring clinical attention.
                </p>
              </div>
            </div>
            {!stats && <Skeleton height="180px" radius="md" />}
            {stats && stats.needsReview.length === 0 && (
              <EmptyState title="Nothing needs review right now" description="All assessments have been reviewed or are within stable limits." />
            )}
            {stats && stats.needsReview.length > 0 && <AssessmentsTable rows={toRows(stats.needsReview)} />}
          </FadeInUp>

          {/* Priority 2: Operational Caseload Summary */}
          <FadeInUp id="insights" className={styles.summaryGrid} delay={0.08}>
            {stats ? (
              summaryTiles(stats).map((tile, i) => (
                <SummaryTile key={tile.label} icon={tile.icon} label={tile.label} value={tile.value} style={{ animationDelay: `${i * 40}ms` }} />
              ))
            ) : (
              Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height="96px" radius="md" />)
            )}
          </FadeInUp>

          {/* Priority 3: Recent Assessments */}
          <FadeInUp as="section" id="recent-assessments" className={`${clinicalStyles.panel} ${clinicalStyles.sectionSpacer}`} delay={0.16}>
            <div className={clinicalStyles.panelHeader}>
              <div>
                <h2 className={clinicalStyles.panelTitle}>Recent assessments</h2>
                <p className={clinicalStyles.panelSubtitle}>Recently completed picture description tasks across caseload.</p>
              </div>
            </div>
            {!stats && <Skeleton height="240px" radius="md" />}
            {stats && stats.recentRows.length === 0 && (
              <EmptyState title="No assessments yet" description="Completed assessments will appear here." />
            )}
            {stats && stats.recentRows.length > 0 && <AssessmentsTable rows={toRows(stats.recentRows)} />}
          </FadeInUp>
        </>
      )}
    </div>
  );
}

function summaryTiles(stats) {
  return [
    { icon: AlertCircle, label: "Awaiting review", value: stats.awaitingReview },
    { icon: ClipboardList, label: "Total assessments", value: stats.total },
    { icon: Users, label: "Active patients", value: stats.activePatients },
    { icon: Activity, label: "Last 30 days", value: stats.recentCount },
  ];
}
