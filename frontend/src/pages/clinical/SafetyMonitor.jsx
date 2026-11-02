import { useCallback, useEffect, useState } from "react";
import { ShieldAlert, Camera, Play, Trash2, RefreshCw } from "lucide-react";
import {
  getMonitoringStatus,
  getMonitoringAlerts,
  runMonitoringDemo,
  clearMonitoringDemo,
} from "../../services/index.js";
import Button from "../../components/common/Button.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import Skeleton from "../../components/common/Skeleton.jsx";
import Status from "../../components/common/Status.jsx";
import clinicalStyles from "../../components/clinical/clinical.module.css";
import styles from "./SafetyMonitor.module.css";

const POLL_MS = 5000;

function formatTime(iso) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString([], { dateStyle: "medium", timeStyle: "medium" });
}

function cameraSummary(live) {
  if (!live) return { tone: "unknown", label: "Unknown" };
  if (!live.available) return { tone: "neutral", label: "Not installed on this server" };
  if (live.observer === "failed") return { tone: "attention", label: "Vision model failed to load" };
  if (live.observer === "ready") return { tone: "positive", label: "Ready" };
  if (live.observer === "loading") return { tone: "neutral", label: "Loading vision model" };
  return { tone: "neutral", label: "Idle — waiting for camera frames" };
}

export default function ClinicalSafetyMonitor() {
  const [status, setStatus] = useState(null);
  const [alerts, setAlerts] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [s, a] = await Promise.all([getMonitoringStatus(), getMonitoringAlerts({ limit: 50 })]);
      setStatus(s);
      setAlerts(a);
      setError(null);
    } catch (err) {
      setError(err.message ?? "Something went wrong.");
    }
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, POLL_MS);
    return () => clearInterval(timer);
  }, [load]);

  async function act(fn) {
    setBusy(true);
    try {
      await fn();
      await load();
    } catch (err) {
      setError(err.message ?? "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  const live = status?.live_camera;
  const camera = cameraSummary(live);
  const state = status?.state;

  return (
    <div>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Safety monitor</h1>
          <p className={styles.subtitle}>
            Fall, unattended-appliance and wandering alerts from the room camera. Alerts support a caregiver&apos;s
            attention; they are not a diagnosis.
          </p>
        </div>
        <div className={styles.actions}>
          <Button variant="secondary" size="sm" onClick={() => act(load)} disabled={busy}>
            <RefreshCw size={15} aria-hidden="true" /> Refresh
          </Button>
          <Button variant="secondary" size="sm" onClick={() => act(clearMonitoringDemo)} disabled={busy}>
            <Trash2 size={15} aria-hidden="true" /> Clear demo
          </Button>
          <Button variant="accent" size="sm" onClick={() => act(runMonitoringDemo)} disabled={busy}>
            <Play size={15} aria-hidden="true" /> Run demo scenario
          </Button>
        </div>
      </div>

      {error && <ErrorState title="Couldn't load safety data" description={error} onRetry={load} />}

      {!error && (
        <>
          <section className={clinicalStyles.panel} aria-labelledby="camera-heading">
            <div className={clinicalStyles.panelHeader}>
              <div>
                <h2 id="camera-heading" className={clinicalStyles.panelTitle}>
                  <Camera size={17} aria-hidden="true" style={{ verticalAlign: "-3px", marginRight: 8 }} />
                  Live camera
                </h2>
                <p className={clinicalStyles.panelSubtitle}>
                  {live && !live.available
                    ? `The camera analysis packages (${live.missing.join(", ")}) are not installed here, so live monitoring is off. The rest of the platform is unaffected, and you can still try the demo scenario.`
                    : "Frames from the room camera are analysed in short clips and checked against the care rules."}
                </p>
              </div>
              {status ? <Status tone={camera.tone}>{camera.label}</Status> : <Skeleton width="140px" height="22px" />}
            </div>
            {live?.observer_error && <p className={styles.errorLine}>Vision model error: {live.observer_error}</p>}
            {live?.last_error && <p className={styles.errorLine}>Last analysis error: {live.last_error}</p>}
            {state && (
              <dl className={styles.stats}>
                <div>
                  <dt>Frames received</dt>
                  <dd>{status.counters.frames}</dd>
                </div>
                <div>
                  <dt>Clips analysed</dt>
                  <dd>{status.counters.clips}</dd>
                </div>
                <div>
                  <dt>Appliances on</dt>
                  <dd>{Object.keys(state.heat_on).length ? Object.keys(state.heat_on).join(", ") : "None"}</dd>
                </div>
                <div>
                  <dt>Last seen</dt>
                  <dd>{state.seconds_since_seen == null ? "—" : `${state.seconds_since_seen}s ago`}</dd>
                </div>
              </dl>
            )}
          </section>

          <section className={`${clinicalStyles.panel} ${clinicalStyles.sectionSpacer}`} aria-labelledby="alerts-heading">
            <div className={clinicalStyles.panelHeader}>
              <div>
                <h2 id="alerts-heading" className={clinicalStyles.panelTitle}>
                  Alerts
                </h2>
                <p className={clinicalStyles.panelSubtitle}>Most recent first. Updates every few seconds.</p>
              </div>
            </div>

            {alerts === null && <Skeleton height="96px" radius="md" />}
            {alerts && alerts.length === 0 && (
              <EmptyState
                icon={ShieldAlert}
                title="Nothing needing attention"
                description="No safety alerts have been raised. Use “Run demo scenario” to see what an incident looks like."
              />
            )}
            {alerts && alerts.length > 0 && (
              <ul className={styles.alertList}>
                {alerts.map((a, i) => (
                  <li key={`${a.at}-${a.kind}-${i}`} className={`${styles.alert} ${styles[a.level] ?? ""}`}>
                    <div className={styles.alertTop}>
                      <span className={styles.level}>{a.level}</span>
                      {a.source === "demo" && <span className={styles.demoTag}>Demo</span>}
                      <time className={styles.time} dateTime={a.at}>
                        {formatTime(a.at)}
                      </time>
                    </div>
                    <p className={styles.summary}>{a.summary}</p>
                    <p className={styles.meta}>
                      <strong>Why:</strong> {a.evidence}
                    </p>
                    <p className={styles.meta}>
                      <strong>Suggested action:</strong> {a.action}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
