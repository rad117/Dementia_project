import styles from "./Waveform.module.css";

const BAR_COUNT = 24;
const PHASES = Array.from({ length: BAR_COUNT }, (_, i) => Math.sin(i * 0.9));

export default function Waveform({ level = 0, active = false }) {
  return (
    <div className={styles.wrap} aria-hidden="true">
      {PHASES.map((phase, i) => {
        const base = active ? 0.15 + Math.max(0, level) * (0.5 + 0.5 * Math.abs(phase)) : 0.08;
        const height = Math.min(1, base) * 100;
        return <span key={i} className={styles.bar} style={{ height: `${height}%` }} />;
      })}
    </div>
  );
}
