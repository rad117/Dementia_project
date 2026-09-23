import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getPatients } from "../../services/index.js";
import { supportedLanguages } from "../../data/mockTasks.js";
import PatientsTable from "../../components/clinical/PatientsTable.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import Skeleton from "../../components/common/Skeleton.jsx";
import Button from "../../components/common/Button.jsx";
import FadeInUp from "../../components/motion/FadeInUp.jsx";
import clinicalStyles from "../../components/clinical/clinical.module.css";
import styles from "./Patients.module.css";

const DEFAULT_FILTERS = { query: "", language: "all", reviewStatus: "all", sort: "recent" };

export default function ClinicalPatients() {
  const [searchParams] = useSearchParams();
  const [filters, setFilters] = useState(() => ({ ...DEFAULT_FILTERS, query: searchParams.get("query") ?? "" }));
  const [patients, setPatients] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getPatients(filters)
      .then((result) => {
        if (!cancelled) setPatients(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message ?? "Something went wrong.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filters]);

  const languages = useMemo(() => supportedLanguages.map((l) => l.label), []);
  const hasActiveFilters =
    filters.query || filters.language !== "all" || filters.reviewStatus !== "all" || filters.sort !== "recent";

  return (
    <div>
      <div className={styles.header}>
        <h1 className={styles.title}>Patients</h1>
      </div>

      <FadeInUp className={styles.filterBar}>
        <input
          type="search"
          className={styles.searchInput}
          placeholder="Search by name or patient ID"
          value={filters.query}
          onChange={(e) => setFilters((f) => ({ ...f, query: e.target.value }))}
          aria-label="Search by name or patient ID"
        />
        <select
          className={styles.select}
          value={filters.language}
          onChange={(e) => setFilters((f) => ({ ...f, language: e.target.value }))}
          aria-label="Filter by language"
        >
          <option value="all">All languages</option>
          {languages.map((l) => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
        <select
          className={styles.select}
          value={filters.reviewStatus}
          onChange={(e) => setFilters((f) => ({ ...f, reviewStatus: e.target.value }))}
          aria-label="Filter by review status"
        >
          <option value="all">All review statuses</option>
          <option value="needs-review">Review recommended</option>
          <option value="reviewed">Reviewed</option>
        </select>
        <select
          className={styles.select}
          value={filters.sort}
          onChange={(e) => setFilters((f) => ({ ...f, sort: e.target.value }))}
          aria-label="Sort patients"
        >
          <option value="recent">Sort: most recent</option>
          <option value="name">Sort: name (A–Z)</option>
          <option value="review">Sort: needs review first</option>
        </select>
      </FadeInUp>

      <FadeInUp className={clinicalStyles.panel} delay={0.08}>
        {loading && <Skeleton height="280px" radius="md" />}
        {!loading && error && <ErrorState description={error} onRetry={() => setFilters({ ...filters })} />}
        {!loading && !error && patients?.length === 0 && (
          <EmptyState
            title="No patients match your filters."
            action={
              hasActiveFilters && (
                <Button variant="secondary" onClick={() => setFilters(DEFAULT_FILTERS)}>
                  Clear filters
                </Button>
              )
            }
          />
        )}
        {!loading && !error && patients?.length > 0 && <PatientsTable patients={patients} />}
      </FadeInUp>
    </div>
  );
}
