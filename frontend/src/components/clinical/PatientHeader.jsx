import { useNavigate } from "react-router-dom";
import { FileText, History, Plus } from "lucide-react";
import Button from "../common/Button.jsx";
import Status from "../common/Status.jsx";
import Bezel from "../common/Bezel.jsx";
import styles from "./PatientHeader.module.css";

export default function PatientHeader({ patient, onExport }) {
  const navigate = useNavigate();
  const needsReview = patient.latestAssessment?.screening.needsClinicianReview;

  return (
    <Bezel className="mb-5" innerClassName={`${styles.header} p-5`}>
      <div className={styles.identity}>
        <h1 className={styles.name}>{patient.name}</h1>
        <div className={styles.metaRow}>
          <span>{patient.id}</span>
          <span>·</span>
          <span>{patient.age} years</span>
          <span>·</span>
          <span>{patient.preferredLanguage}</span>
          <span>·</span>
          <span>Last assessment: {patient.latestAssessment?.date ?? "—"}</span>
          {patient.latestAssessment && (
            <Status tone={needsReview ? "attention" : "positive"}>
              {needsReview ? "Review recommended" : "Reviewed"}
            </Status>
          )}
        </div>
      </div>
      <div className={styles.actions}>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => navigate("/login/patient")}
          title="Starts a new assessment session on the participant device"
        >
          <Plus size={16} aria-hidden="true" /> New assessment
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => document.getElementById("previous-assessments")?.scrollIntoView({ behavior: "smooth" })}
        >
          <History size={16} aria-hidden="true" /> View history
        </Button>
        <Button variant="secondary" size="sm" onClick={onExport}>
          <FileText size={16} aria-hidden="true" /> Export report
        </Button>
      </div>
    </Bezel>
  );
}
