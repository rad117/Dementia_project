import { Outlet, useLocation, useNavigate } from "react-router-dom";
import ParticipantHeader from "./ParticipantHeader.jsx";
import styles from "./ParticipantLayout.module.css";

const NO_BACK_ROUTES = new Set(["/patient"]);

export default function ParticipantLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const hideBack = NO_BACK_ROUTES.has(location.pathname);

  return (
    <div className={styles.shell}>
      <ParticipantHeader onBack={hideBack ? null : () => navigate(-1)} />
      <main className={styles.content}>
        <div className={styles.inner}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}
