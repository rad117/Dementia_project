import { useState } from "react";
import { ChevronDown } from "lucide-react";
import styles from "./Accordion.module.css";

export default function Accordion({ title, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={styles.wrap}>
      <button type="button" className={styles.trigger} onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <span>{title}</span>
        <ChevronDown size={16} className={styles.chevron} data-open={open} aria-hidden="true" />
      </button>
      {open && <div className={styles.content}>{children}</div>}
    </div>
  );
}
