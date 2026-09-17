import { CheckCircle2, AlertCircle, Clock, HelpCircle } from "lucide-react";
import styles from "./Status.module.css";

// Status communicates meaning through icon + text + color together —
// never color alone (see requirements §4.2 / §48).
const TONE_ICON = {
  positive: CheckCircle2,
  attention: AlertCircle,
  neutral: Clock,
  unknown: HelpCircle,
};

export default function Status({ tone = "neutral", children }) {
  const Icon = TONE_ICON[tone] ?? TONE_ICON.neutral;
  return (
    <span className={`${styles.status} ${styles[tone]}`}>
      <Icon size={14} aria-hidden="true" />
      <span>{children}</span>
    </span>
  );
}
