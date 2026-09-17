import clinicalStyles from "../../components/clinical/clinical.module.css";

export default function ClinicalPrivacy() {
  return (
    <div>
      <h1 style={{ fontSize: 26, marginBottom: 20 }}>Privacy</h1>
      <div className={clinicalStyles.panel}>
        <p style={{ color: "var(--slate)", lineHeight: 1.6 }}>
          All patient data shown in this application is fictional demo data generated for illustration. Recordings
          and derived indicators are treated as sensitive clinical data; access control, consent management and
          retention policy are implemented by the backend service, not this frontend.
        </p>
      </div>
    </div>
  );
}
