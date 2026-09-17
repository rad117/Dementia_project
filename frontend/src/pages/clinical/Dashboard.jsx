import { useEffect, useMemo, useState } from "react";
import { ClipboardList, AlertCircle, Users, Activity } from "lucide-react";
import { getAllAssessments, getPatients } from "../../services/index.js";
import SummaryTile from "../../components/clinical/SummaryTile.jsx";
import AssessmentsTable from "../../components/clinical/AssessmentsTable.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import Skeleton from "../../components/common/Skeleton.jsx";
import clinicalStyles from "../../components/clinical/clinical.module.css";
import styles from "./Dashboard.module.css";

export default function ClinicalDashboard() {
  const [assessments, setAssessments] = useState(null);
  const [patients, setPatients] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getAllAssessments(), getPatients()]).then(([a, p]) => {
      if (cancelled) return;
      setAssessments(a);
      setPatients(p);
    });
    return () => {
      cancelled = true;
    };
  }, []);

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
      recentRows: [...assessments].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 10),
    };
  }, [assessments, patients]);

  function toRows(list) {
    return list.map((assessment) => ({ assessment, patientName: patientNameById[assessment.patientId] ?? assessment.patientId }));
  }

  return (
    <div>
      <div className={styles.header}>
        <h1 className={styles.title}>Clinical overview</h1>
        <p className={styles.subtitle}>Speech and language assessment activity across your caseload.</p>
      </div>

      <div className={styles.summaryGrid}>
        {stats ? (
          <>
            <SummaryTile icon={ClipboardList} label="Assessments" value={stats.total} />
            <SummaryTile icon={AlertCircle} label="Awaiting review" value={stats.awaitingReview} />
            <SummaryTile icon={Users} label="Active patients" value={stats.activePatients} />
            <SummaryTile icon={Activity} label="Recent assessments" value={stats.recentCount} />
          </>
        ) : (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height="96px" radius="md" />)
        )}
      </div>

      <section id="recent-assessments" className={`${clinicalStyles.panel} ${clinicalStyles.sectionSpacer}`}>
        <div className={clinicalStyles.panelHeader}>
          <div>
            <h2 className={clinicalStyles.panelTitle}>Needs review</h2>
            <p className={clinicalStyles.panelSubtitle}>Assessments flagged for clinician review.</p>
          </div>
        </div>
        {!stats && <Skeleton height="180px" radius="md" />}
        {stats && stats.needsReview.length === 0 && (
          <EmptyState title="Nothing needs review right now" description="Flagged assessments will appear here." />
        )}
        {stats && stats.needsReview.length > 0 && <AssessmentsTable rows={toRows(stats.needsReview)} />}
      </section>

      <section id="insights" className={`${clinicalStyles.panel} ${clinicalStyles.sectionSpacer}`}>
        <div className={clinicalStyles.panelHeader}>
          <div>
            <h2 className={clinicalStyles.panelTitle}>Recent assessments</h2>
            <p className={clinicalStyles.panelSubtitle}>Most recently completed assessments across all patients.</p>
          </div>
        </div>
        {!stats && <Skeleton height="240px" radius="md" />}
        {stats && stats.recentRows.length === 0 && (
          <EmptyState title="No assessments yet" description="Completed assessments will appear here." />
        )}
        {stats && stats.recentRows.length > 0 && <AssessmentsTable rows={toRows(stats.recentRows)} />}
      </section>
    </div>
  );
}
