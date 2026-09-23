import { useNavigate } from "react-router-dom";
import Status from "../common/Status.jsx";
import styles from "./AssessmentsTable.module.css";

export default function PatientsTable({ patients }) {
  const navigate = useNavigate();

  return (
    <div className={`${styles.wrap} fade-in-up`}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Patient</th>
            <th scope="col">Patient ID</th>
            <th scope="col">Language</th>
            <th scope="col">Assessments</th>
            <th scope="col">Last assessment</th>
            <th scope="col">Review status</th>
            <th scope="col"><span className="visually-hidden">Open</span></th>
          </tr>
        </thead>
        <tbody>
          {patients.map((patient) => (
            <tr
              key={patient.id}
              className={styles.row}
              tabIndex={0}
              onClick={() => navigate(`/clinical/patients/${patient.id}`)}
              onKeyDown={(e) => {
                if (e.key === "Enter") navigate(`/clinical/patients/${patient.id}`);
              }}
            >
              <td className={styles.patientCell}>{patient.name}</td>
              <td>{patient.id}</td>
              <td>{patient.preferredLanguage}</td>
              <td>{patient.assessmentCount}</td>
              <td>{patient.latestAssessment?.date ?? "—"}</td>
              <td>
                {patient.latestAssessment ? (
                  <Status tone={patient.latestAssessment.screening.needsClinicianReview ? "attention" : "positive"}>
                    {patient.latestAssessment.screening.needsClinicianReview ? "Review recommended" : "Reviewed"}
                  </Status>
                ) : (
                  <Status tone="neutral">No assessments</Status>
                )}
              </td>
              <td className={styles.openCell}>Open →</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
