import { Link } from "react-router-dom";
import { User, Stethoscope } from "lucide-react";
import styles from "./RoleSelect.module.css";

export default function RoleSelect() {
  return (
    <div className={styles.wrap}>
      <h1 className={styles.heading}>How will you use CognitiveAssist?</h1>
      <div className={styles.grid}>
        <Link to="/login/patient" className={styles.card}>
          <User size={28} strokeWidth={1.6} className={styles.icon} aria-hidden="true" />
          <h2 className={styles.cardTitle}>Participant</h2>
          <p className={styles.cardDescription}>Complete an assessment or activity.</p>
        </Link>
        <Link to="/login/clinical" className={styles.card}>
          <Stethoscope size={28} strokeWidth={1.6} className={styles.icon} aria-hidden="true" />
          <h2 className={styles.cardTitle}>Clinical Professional</h2>
          <p className={styles.cardDescription}>Review assessments, speech analysis and longitudinal change.</p>
        </Link>
      </div>
    </div>
  );
}
