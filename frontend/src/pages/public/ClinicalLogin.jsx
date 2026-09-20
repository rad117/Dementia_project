import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSession } from "../../app/SessionContext.jsx";
import { loginClinicalUser } from "../../services/index.js";
import Button from "../../components/common/Button.jsx";
import styles from "./PatientLogin.module.css";

export default function ClinicalLogin() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { loginClinical } = useSession();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = await loginClinicalUser({ email, password });
      loginClinical(user);
      navigate("/clinical");
    } catch (err) {
      setError(err.message ?? "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.wrap}>
      <h1 className={styles.heading}>Clinical sign in</h1>
      <p className={styles.subtext}>Sign in with your clinical account to review assessments.</p>

      <form onSubmit={handleSubmit}>
        <div className={styles.field}>
          <label htmlFor="clinical-email" className={styles.label}>
            Email
          </label>
          <input
            id="clinical-email"
            type="email"
            className={styles.input}
            style={{ fontSize: 16, letterSpacing: "normal" }}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@clinic.example"
            autoComplete="email"
            required
          />
        </div>
        <div className={styles.field}>
          <label htmlFor="clinical-password" className={styles.label}>
            Password
          </label>
          <input
            id="clinical-password"
            type="password"
            className={styles.input}
            style={{ fontSize: 16, letterSpacing: "normal" }}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            aria-describedby={error ? "clinical-error" : undefined}
            required
          />
          {error && (
            <p id="clinical-error" className={styles.errorText} role="alert">
              {error}
            </p>
          )}
        </div>
        <Button type="submit" variant="accent" size="lg" className={styles.submit} disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </Button>
      </form>
      <div className={styles.demoSection} style={{ marginTop: "var(--space-4)" }}>
        <p className={styles.demoLabel}>Demo quick access:</p>
        <button
          type="button"
          className={styles.chip}
          style={{ width: "100%", textAlign: "center" }}
          onClick={() => {
            setEmail("dr.sharma@memora.org");
            setPassword("demo1234");
          }}
        >
          Fill Demo Clinician (Dr. Sharma)
        </button>
      </div>
      <p className={styles.hint} style={{ marginTop: "var(--space-4)", textAlign: "center" }}>
        Demo mode — any credentials will grant access.
      </p>
    </div>
  );
}
