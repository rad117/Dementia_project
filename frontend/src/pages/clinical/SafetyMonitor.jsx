import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ShieldAlert, Camera, Play, Trash2, RefreshCw, FlaskConical } from "lucide-react";
import {
  getMonitoringStatus,
  getMonitoringAlerts,
  getMonitoringScenarios,
  getPatients,
  runMonitoringDemo,
  clearMonitoringDemo,
} from "../../services/index.js";
import Button from "../../components/common/Button.jsx";
import EmptyState from "../../components/common/EmptyState.jsx";
import ErrorState from "../../components/common/ErrorState.jsx";
import Skeleton from "../../components/common/Skeleton.jsx";
import Status from "../../components/common/Status.jsx";
import SafetyAlertList from "../../components/clinical/SafetyAlertList.jsx";
import LiveCamera from "../../components/clinical/LiveCamera.jsx";
import clinicalStyles from "../../components/clinical/clinical.module.css";
import styles from "./SafetyMonitor.module.css";

const POLL_MS = 5000;

function cameraSummary(live) {
  if (!live) return { tone: "unknown", label: "Unknown" };
  if (!live.available) return { tone: "neutral", label: "Camera analysis off on this server" };
  if (live.observer === "failed") return { tone: "attention", label: "Vision model failed to load" };
  if (live.observer === "ready") return { tone: "positive", label: live.vlm ? "Ready (pose + vision model)" : "Ready (pose detection)" };
  if (live.observer === "loading") return { tone: "neutral", label: "Loading vision model" };
  return { tone: "neutral", label: "Idle — waiting for camera frames" };
}

export default function ClinicalSafetyMonitor() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [status, setStatus] = useState(null);
  const [alerts, setAlerts] = useState(null);
  const [patients, setPatients] = useState([]);
  const [scenarios, setScenarios] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(null); // scenario id | "clear" | "refresh"
  const [lastRun, setLastRun] = useState(null);

  // ?patient=<id> preselects a patient (linked from the patient profile).
  const simPatient = searchParams.get("patient") ?? "";
  const [filterPatient, setFilterPatient] = useState(simPatient);

  const patientNameById = useMemo(() => Object.fromEntries(patients.map((p) => [p.id, p.name])), [patients]);

  const load = useCallback(async () => {
    try {
      const [s, a] = await Promise.all([
        getMonitoringStatus(),
        getMonitoringAlerts({ limit: 100, patient_id: filterPatient || undefined }),
      ]);
      setStatus(s);
      setAlerts(a);
      setError(null);
    } catch (err) {
      setError(err.message ?? "Something went wrong.");
    }
  }, [filterPatient]);

  useEffect(() => {
    load();
    const timer = setInterval(load, POLL_MS);
    return () => clearInterval(timer);
  }, [load]);

  useEffect(() => {
    getPatients().then(setPatients).catch(() => setPatients([]));
    getMonitoringScenarios().then(setScenarios).catch(() => setScenarios([]));
  }, []);

  function setSimPatient(id) {
    const next = new URLSearchParams(searchParams);
    if (id) next.set("patient", id);
    else next.delete("patient");
    setSearchParams(next, { replace: true });
  }

  async function act(key, fn) {
    setBusy(key);
    try {
      const result = await fn();
      await load();
      return result;
    } catch (err) {
      setError(err.message ?? "Something went wrong.");
      return null;
    } finally {
      setBusy(null);
    }
  }

  async function runScenario(scenario) {
    const raised = await act(scenario.id, () => runMonitoringDemo({ scenario: scenario.id, patientId: simPatient || undefined }));
    if (raised) {
      setLastRun({ title: scenario.title, count: raised.length, patient: patientNameById[simPatient] });
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
          <Button variant="secondary" size="sm" onClick={() => act("refresh", load)} disabled={busy !== null}>
            <RefreshCw size={15} aria-hidden="true" /> Refresh
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => act("clear", clearMonitoringDemo).then(() => setLastRun(null))}
            disabled={busy !== null}
          >
            <Trash2 size={15} aria-hidden="true" /> Clear simulated alerts
          </Button>
        </div>
      </div>

      {error && <ErrorState title="Couldn't load safety data" description={error} onRetry={load} />}

      {!error && (
        <>
          <section className={clinicalStyles.panel} aria-labelledby="simulate-heading">
            <div className={clinicalStyles.panelHeader}>
              <div>
                <h2 id="simulate-heading" className={clinicalStyles.panelTitle}>
                  <FlaskConical size={17} aria-hidden="true" style={{ verticalAlign: "-3px", marginRight: 8 }} />
                  Simulate an incident
                </h2>
                <p className={clinicalStyles.panelSubtitle}>
                  Replays a sequence of room observations — the same structured output the camera&apos;s vision model
                  produces — through the live care rules, using short demo timings. Alerts are tagged “Simulated”.
                </p>
              </div>
              <label className={styles.field}>
                <span>Patient</span>
                <select className={styles.select} value={simPatient} onChange={(e) => setSimPatient(e.target.value)}>
                  <option value="">No patient (unassigned)</option>
                  {patients.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {scenarios === null && <Skeleton height="120px" radius="md" />}
            {scenarios && (
              <div className={styles.scenarioGrid}>
                {scenarios.map((s) => (
                  <div key={s.id} className={styles.scenario}>
                    <h3 className={styles.scenarioTitle}>{s.title}</h3>
                    <p className={styles.scenarioText}>{s.description}</p>
                    <Button variant="accent" size="sm" onClick={() => runScenario(s)} disabled={busy !== null}>
                      <Play size={14} aria-hidden="true" /> {busy === s.id ? "Running…" : "Run"}
                    </Button>
                  </div>
                ))}
              </div>
            )}
            {lastRun && (
              <p className={styles.runNote} role="status">
                “{lastRun.title}” raised {lastRun.count} alert{lastRun.count === 1 ? "" : "s"}
                {lastRun.patient ? ` for ${lastRun.patient}` : ""}.
              </p>
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
              <label className={styles.field}>
                <span>Show</span>
                <select className={styles.select} value={filterPatient} onChange={(e) => setFilterPatient(e.target.value)}>
                  <option value="">All patients</option>
                  {patients.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {alerts === null && <Skeleton height="96px" radius="md" />}
            {alerts && alerts.length === 0 && (
              <EmptyState
                icon={ShieldAlert}
                title="Nothing needing attention"
                description="No safety alerts have been raised. Run a scenario above to see what an incident looks like."
              />
            )}
            {alerts && alerts.length > 0 && <SafetyAlertList alerts={alerts} patientNameById={patientNameById} />}
          </section>

          <section className={`${clinicalStyles.panel} ${clinicalStyles.sectionSpacer}`} aria-labelledby="camera-heading">
            <div className={clinicalStyles.panelHeader}>
              <div>
                <h2 id="camera-heading" className={clinicalStyles.panelTitle}>
                  <Camera size={17} aria-hidden="true" style={{ verticalAlign: "-3px", marginRight: 8 }} />
                  Live camera
                </h2>
                <p className={clinicalStyles.panelSubtitle}>
                  {live && !live.available
                    ? `Live camera analysis needs extra packages on the server (${live.missing.join(", ")}). This deployment runs the care rules and alerting; the simulator above feeds them the same observations a camera would.`
                    : "Uses this device's camera. Frames are analysed in short clips (pose first, vision model only when needed) and checked against the care rules for the patient selected above."}
                </p>
              </div>
              {status ? <Status tone={camera.tone}>{camera.label}</Status> : <Skeleton width="140px" height="22px" />}
            </div>
            <LiveCamera patientId={simPatient || undefined} available={live ? live.available : undefined} />
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
        </>
      )}
    </div>
  );
}
