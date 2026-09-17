import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import ClinicalSidebar from "./ClinicalSidebar.jsx";
import ClinicalTopbar from "./ClinicalTopbar.jsx";
import { getPatients } from "../../services/index.js";
import styles from "./ClinicalLayout.module.css";

export default function ClinicalLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [reviewCount, setReviewCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getPatients().then((patients) => {
      if (cancelled) return;
      const count = patients.filter((p) => p.latestAssessment?.screening.needsClinicianReview).length;
      setReviewCount(count);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className={styles.shell}>
      <ClinicalSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className={styles.main}>
        <ClinicalTopbar onMenuClick={() => setSidebarOpen(true)} reviewCount={reviewCount} />
        <main className={styles.content}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
