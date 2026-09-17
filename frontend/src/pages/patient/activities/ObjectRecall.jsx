import { useEffect, useState } from "react";
import Button from "../../../components/common/Button.jsx";
import styles from "./activities.module.css";

const TARGET_WORDS = ["Kettle", "Bicycle", "Garden", "Pencil", "Blanket", "Lantern"];
const DISTRACTORS = ["Window", "Bottle", "Ladder", "Basket", "Mirror", "Whistle"];

function shuffle(arr) {
  return [...arr].sort(() => Math.random() - 0.5);
}

export default function ObjectRecall({ onFinish }) {
  const [phase, setPhase] = useState("study"); // study -> recall -> done
  const [secondsLeft, setSecondsLeft] = useState(8);
  const [options] = useState(() => shuffle([...TARGET_WORDS, ...DISTRACTORS]));
  const [selected, setSelected] = useState([]);

  useEffect(() => {
    if (phase !== "study") return;
    if (secondsLeft <= 0) {
      setPhase("recall");
      return;
    }
    const t = setTimeout(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [phase, secondsLeft]);

  function toggle(word) {
    setSelected((prev) => (prev.includes(word) ? prev.filter((w) => w !== word) : [...prev, word]));
  }

  const correctCount = selected.filter((w) => TARGET_WORDS.includes(w)).length;

  if (phase === "study") {
    return (
      <div className={styles.wrap}>
        <p style={{ textAlign: "center", color: "var(--muted)" }}>Try to remember these words. ({secondsLeft}s)</p>
        <div className={styles.wordList}>
          {TARGET_WORDS.map((w) => (
            <span key={w} className={styles.wordChip}>{w}</span>
          ))}
        </div>
      </div>
    );
  }

  if (phase === "recall") {
    return (
      <div className={styles.wrap}>
        <p style={{ textAlign: "center", color: "var(--muted)" }}>Which words did you see?</p>
        <div className={styles.wordList}>
          {options.map((w) => (
            <button
              key={w}
              type="button"
              className={`${styles.optionButton} ${selected.includes(w) ? styles.optionSelected : ""}`}
              onClick={() => toggle(w)}
              aria-pressed={selected.includes(w)}
            >
              {w}
            </button>
          ))}
        </div>
        <Button variant="accent" size="lg" onClick={() => setPhase("done")}>
          Done
        </Button>
      </div>
    );
  }

  return (
    <div className={styles.resultCard}>
      <p style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Well done!</p>
      <p style={{ color: "var(--muted)", marginBottom: 20 }}>
        You recalled {correctCount} of {TARGET_WORDS.length} words. This reflects activity performance, not a
        clinical result.
      </p>
      <Button variant="accent" onClick={onFinish}>Back to activities</Button>
    </div>
  );
}
