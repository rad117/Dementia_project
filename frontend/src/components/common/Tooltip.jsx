import { useId, useState } from "react";
import styles from "./Tooltip.module.css";

export default function Tooltip({ label, children }) {
  const [open, setOpen] = useState(false);
  const id = useId();

  return (
    <span
      className={styles.wrapper}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <span tabIndex={0} aria-describedby={id} className={styles.trigger}>
        {children}
      </span>
      <span role="tooltip" id={id} className={styles.tooltip} data-open={open}>
        {label}
      </span>
    </span>
  );
}
