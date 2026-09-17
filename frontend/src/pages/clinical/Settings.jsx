import clinicalStyles from "../../components/clinical/clinical.module.css";

export default function ClinicalSettings() {
  return (
    <div>
      <h1 style={{ fontSize: 26, marginBottom: 20 }}>Settings</h1>
      <div className={clinicalStyles.panel}>
        <p style={{ color: "var(--muted)" }}>
          Account and workspace settings will appear here once connected to the backend identity and preferences
          service.
        </p>
      </div>
    </div>
  );
}
