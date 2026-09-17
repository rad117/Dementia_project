import { useNavigate } from "react-router-dom";
import Status from "../common/Status.jsx";
import styles from "./AssessmentsTable.module.css";

export default function AssessmentsTable({ rows }) {
  const navigate = useNavigate();

  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Patient</th>
            <th scope="col">Date</th>
            <th scope="col">Language</th>
            <th scope="col">Task</th>
            <th scope="col">Duration</th>
            <th scope="col">Quality</th>
            <th scope="col">Screening status</th>
            <th scope="col"><span className="visually-hidden">Open</span></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.assessment.id}
              className={styles.row}
              tabIndex={0}
              onClick={() => navigate(`/clinical/assessments/${row.assessment.id}`)}
              onKeyDown={(e) => {
                if (e.key === "Enter") navigate(`/clinical/assessments/${row.assessment.id}`);
              }}
            >
              <td className={styles.patientCell}>{row.patientName}</td>
              <td>{row.assessment.date}</td>
              <td>{row.assessment.language}</td>
              <td>{row.assessment.task.name}</td>
              <td>{row.assessment.quality.durationSeconds}s</td>
              <td style={{ textTransform: "capitalize" }}>{row.assessment.quality.audioQuality}</td>
              <td>
                <Status tone={row.assessment.screening.needsClinicianReview ? "attention" : "positive"}>
                  {row.assessment.screening.needsClinicianReview ? "Review recommended" : "Reviewed"}
                </Status>
              </td>
              <td className={styles.openCell}>Open →</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
