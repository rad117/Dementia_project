import { NavLink } from "react-router-dom";
import { LayoutDashboard, Users, ClipboardList, TrendingUp, Settings, Info, ShieldCheck, X } from "lucide-react";
import styles from "./ClinicalSidebar.module.css";

const SECTIONS = [
  {
    label: "Overview",
    items: [{ to: "/clinical", label: "Dashboard", icon: LayoutDashboard, end: true }],
  },
  {
    label: "Patients",
    items: [{ to: "/clinical/patients", label: "Patient list", icon: Users }],
  },
  {
    label: "Assessments",
    items: [{ to: "/clinical#recent-assessments", label: "Recent assessments", icon: ClipboardList, isAnchor: true }],
  },
  {
    label: "Insights",
    items: [{ to: "/clinical#insights", label: "Longitudinal analysis", icon: TrendingUp, isAnchor: true }],
  },
  {
    label: "System",
    items: [
      { to: "/clinical/settings", label: "Settings", icon: Settings },
      { to: "/clinical/model", label: "Model information", icon: Info },
      { to: "/clinical/privacy", label: "Privacy", icon: ShieldCheck },
    ],
  },
];

export default function ClinicalSidebar({ open, onClose }) {
  return (
    <>
      {open && <button className={styles.scrim} aria-label="Close navigation" onClick={onClose} />}
      <aside className={`${styles.sidebar} ${open ? styles.open : ""}`} aria-label="Clinical navigation">
        <div className={styles.header}>
          <span className={styles.brand}>
            Memora <span className={styles.subBrand}>Clinical</span>
          </span>
          <button className={styles.closeBtn} onClick={onClose} aria-label="Close navigation">
            <X size={18} />
          </button>
        </div>
        <nav>
          {SECTIONS.map((section) => (
            <div key={section.label} className={styles.section}>
              <p className={styles.sectionLabel}>{section.label}</p>
              <ul>
                {section.items.map((item) =>
                  item.isAnchor ? (
                    <li key={item.to}>
                      <a href={item.to} className={styles.link} onClick={onClose}>
                        <item.icon size={17} aria-hidden="true" />
                        <span>{item.label}</span>
                      </a>
                    </li>
                  ) : (
                    <li key={item.to}>
                      <NavLink
                        to={item.to}
                        end={item.end}
                        className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}
                        onClick={onClose}
                      >
                        <item.icon size={17} aria-hidden="true" />
                        <span>{item.label}</span>
                      </NavLink>
                    </li>
                  )
                )}
              </ul>
            </div>
          ))}
        </nav>
      </aside>
    </>
  );
}
