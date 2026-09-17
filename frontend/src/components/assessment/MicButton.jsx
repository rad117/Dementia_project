import { Mic, Square } from "lucide-react";
import styles from "./MicButton.module.css";

export default function MicButton({ recording, onClick, disabled, label }) {
  return (
    <button
      type="button"
      className={`${styles.mic} ${recording ? styles.recording : ""}`}
      onClick={onClick}
      disabled={disabled}
      aria-pressed={recording}
      aria-label={label}
    >
      {recording ? <Square size={30} fill="currentColor" aria-hidden="true" /> : <Mic size={40} aria-hidden="true" />}
    </button>
  );
}
