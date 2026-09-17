import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSession } from "../../app/SessionContext.jsx";
import { verifyParticipantCode, getPatients } from "../../services/index.js";
import Button from "../../components/common/Button.jsx";
import styles from "./PatientLogin.module.css";

export default function PatientLogin() {
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [assistedOpen, setAssistedOpen] = useState(false);
  const [assistedPatients, setAssistedPatients] = useState([]);
  const { loginParticipant } = useSession();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const result = await verifyParticipantCode(code);
      loginParticipant(result);
      navigate("/patient");
    } catch (err) {
      setError(err.message ?? "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function openAssistedStart() {
    setAssistedOpen(true);
    if (assistedPatients.length === 0) {
      const patients = await getPatients();
      setAssistedPatients(patients);
    }
  }

  function selectAssisted(patient) {
    loginParticipant({ patientId: patient.id, name: patient.name });
    navigate("/patient");
  }

  return (
    <div className={styles.wrap}>
      <h1 className={styles.heading}>Welcome</h1>
      <p className={styles.subtext}>Enter your participant code to begin. A staff member can help at any time.</p>

      <form onSubmit={handleSubmit}>
        <div className={styles.field}>
          <label htmlFor="participant-code" className={styles.label}>
            Participant code
          </label>
          <input
            id="participant-code"
            className={styles.input}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="e.g. PT-1001"
            autoComplete="off"
            aria-describedby={error ? "code-error" : "code-hint"}
            required
          />
          {error ? (
            <p id="code-error" className={styles.errorText} role="alert">
              {error}
            </p>
          ) : (
            <p id="code-hint" className={styles.hint}>
              Your code was provided by your clinical team.
            </p>
          )}
        </div>
        <Button type="submit" variant="accent" size="lg" className={styles.submit} disabled={loading || !code.trim()}>
          {loading ? "Checking…" : "Continue"}
        </Button>
      </form>

      <div className={styles.divider}>or</div>

      {!assistedOpen ? (
        <Button variant="secondary" size="lg" className={styles.submit} onClick={openAssistedStart}>
          I need help — assisted start
        </Button>
      ) : (
        <div className={styles.assistedList} role="list" aria-label="Select participant">
          {assistedPatients.length === 0 && <p className={styles.hint} style={{ padding: "var(--space-4)" }}>Loading…</p>}
          {assistedPatients.map((p) => (
            <button key={p.id} type="button" className={styles.assistedItem} onClick={() => selectAssisted(p)}>
              {p.name} · {p.id}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
