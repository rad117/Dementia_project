import Bezel from "../../components/common/Bezel.jsx";
import FadeInUp from "../../components/motion/FadeInUp.jsx";

export default function ClinicalPrivacy() {
  return (
    <div>
      <h1 style={{ fontSize: 26, marginBottom: 20 }}>Privacy</h1>
      <FadeInUp>
        <Bezel innerClassName="p-5">
          <p style={{ color: "var(--slate)", lineHeight: 1.6, margin: 0 }}>
            All patient data shown in this application is fictional demo data generated for illustration. Session
            tokens live only in memory on this device and are cleared on logout or a hard refresh — nothing persists
            client-side. Recordings and derived indicators are treated as sensitive clinical data on the backend:
            passwords are PBKDF2-hashed, every request is authenticated with a bearer token scoped to either a
            participant or a clinician, and access to another patient's records is rejected server-side. Consent
            management and data-retention policy are owned by the deploying clinic, not this application.
          </p>
        </Bezel>
      </FadeInUp>
    </div>
  );
}
