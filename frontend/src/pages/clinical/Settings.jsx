import { SlidersHorizontal } from "lucide-react";
import clinicalStyles from "../../components/clinical/clinical.module.css";
import EmptyState from "../../components/common/EmptyState.jsx";
import Bezel from "../../components/common/Bezel.jsx";
import FadeInUp from "../../components/motion/FadeInUp.jsx";
import { useSession } from "../../app/SessionContext.jsx";

export default function ClinicalSettings() {
  const { clinicalUser } = useSession();

  return (
    <div>
      <h1 style={{ fontSize: 26, marginBottom: 20 }}>Settings</h1>
      <FadeInUp className={clinicalStyles.panel}>
        <div className={clinicalStyles.panelHeader}>
          <h2 className={clinicalStyles.panelTitle}>Signed in as</h2>
        </div>
        <dl style={{ display: "flex", gap: 24, margin: 0 }}>
          <div>
            <dt style={{ fontSize: 13, color: "var(--muted)", fontWeight: 600 }}>Name</dt>
            <dd style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "var(--ink)" }}>
              {clinicalUser?.name ?? "—"}
            </dd>
          </div>
          <div>
            <dt style={{ fontSize: 13, color: "var(--muted)", fontWeight: 600 }}>Role</dt>
            <dd style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "var(--ink)" }}>
              {clinicalUser?.role ?? "—"}
            </dd>
          </div>
        </dl>
      </FadeInUp>
      <FadeInUp delay={0.08} style={{ marginTop: 20 }}>
        <Bezel innerClassName="p-5">
          <EmptyState
            icon={SlidersHorizontal}
            title="Workspace preferences — coming soon"
            description="Notification defaults, review-queue thresholds, and account management are on the roadmap and will land here once the identity and preferences service ships."
          />
        </Bezel>
      </FadeInUp>
    </div>
  );
}
