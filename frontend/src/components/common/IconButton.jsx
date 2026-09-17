import { forwardRef } from "react";
import styles from "./IconButton.module.css";

const IconButton = forwardRef(function IconButton(
  { icon: Icon, label, size = "md", variant = "ghost", className = "", ...props },
  ref
) {
  const classes = [styles.iconButton, styles[variant], styles[size], className].filter(Boolean).join(" ");
  return (
    <button ref={ref} type="button" className={classes} aria-label={label} title={label} {...props}>
      <Icon size={size === "sm" ? 16 : 20} aria-hidden="true" />
    </button>
  );
});

export default IconButton;
