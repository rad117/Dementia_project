import { forwardRef } from "react";
import styles from "./Button.module.css";

const Button = forwardRef(function Button(
  { variant = "primary", size = "md", as: Component = "button", className = "", ...props },
  ref
) {
  const classes = [styles.button, styles[variant], styles[size], className].filter(Boolean).join(" ");
  return <Component ref={ref} className={classes} {...props} />;
});

export default Button;
