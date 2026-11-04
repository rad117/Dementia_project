import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { HelpCircle } from "lucide-react";
import { useSession } from "../../app/SessionContext.jsx";
import { verifyParticipantCode, verifyParticipantAssisted, getPatients } from "../../services/index.js";
import Button from "../../components/common/Button.jsx";
import styles from "./PatientLogin.module.css";

export default function PatientLogin() {
    const [code, setCode] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [assistedOpen, setAssistedOpen] = useState(false);
    const [patients, setPatients] = useState([]);
    const [assistLoading, setAssistLoading] = useState(false);
    const { loginParticipant } = useSession();
    const navigate = useNavigate();

    async function login(c) {
        setError(null);
        setLoading(true);

        try {
            const result = await verifyParticipantCode(c.trim());
            loginParticipant(result);
            navigate("/patient");
        } catch (e) {
            setError(e.message || "That participant code was not found.");
        } finally {
            setLoading(false);
        }
    }

    async function assist() {
        setError(null);
        setAssistedOpen(true);

        if (patients.length) return;

        setAssistLoading(true);

        try {
            setPatients(await getPatients());
        } catch (e) {
            setError(
                e.message || "We couldn't load the participant list. Please try again."
            );
        } finally {
            setAssistLoading(false);
        }
    }

    return (
        <div className={styles.wrap}>
            <p className={styles.eyebrow}>Participant</p>

            <h1 className={styles.heading}>Enter your participant code</h1>

            <p className={styles.subtext}>
                Your clinical team provided this code.
            </p>

            <form
                onSubmit={(e) => {
                    e.preventDefault();
                    login(code);
                }}
            >
                <label htmlFor="participant-code" className={styles.label}>
                    Participant code
                </label>

                <input
                    id="participant-code"
                    className={styles.input}
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    placeholder="PT-1001"
                    autoComplete="off"
                    required
                    aria-invalid={!!error}
                />

                {error && (
                    <p className={styles.errorText} role="alert">
                        {error}
                    </p>
                )}

                <Button
                    type="submit"
                    variant="accent"
                    size="lg"
                    className={styles.submit}
                    disabled={!code.trim() || loading}
                >
                    {loading ? "Checking…" : "Continue"}
                </Button>
            </form>

            <div className={styles.help}>
                <HelpCircle size={18} />

                <div>
                    <strong>Need help?</strong>
                    <p>A staff member can start the assessment for you.</p>
                </div>
            </div>

            {!assistedOpen ? (
                <Button
                    variant="secondary"
                    size="lg"
                    className={styles.submit}
                    onClick={assist}
                >
                    Assisted start
                </Button>
            ) : (
                <div className={styles.assisted}>
                    {assistLoading ? (
                        <p>Loading participants…</p>
                    ) : (
                        patients.map((patient) => (
                            <button
                                key={patient.id}
                                onClick={async () => {
                                    try {
                                        const result = await verifyParticipantAssisted(patient.id);
                                        loginParticipant(result);
                                        navigate("/patient");
                                    } catch (e) {
                                        setError(e.message || "We couldn't start the assessment for this participant.");
                                    }
                                }}
                            >
                                {patient.name}
                                <span>{patient.id}</span>
                            </button>
                        ))
                    )}
                </div>
            )}
        </div>
    );
}