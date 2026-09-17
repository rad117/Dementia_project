import { useState } from "react";
import Button from "../../../components/common/Button.jsx";
import styles from "./activities.module.css";

const ROUNDS = [
  { sequence: ["●", "▲", "●", "▲"], options: ["●", "■"], answer: "●" },
  { sequence: ["■", "■", "▲", "■", "■"], options: ["▲", "■"], answer: "▲" },
  { sequence: ["●", "●", "▲", "▲", "▲"], options: ["●", "▲", "■"], answer: "▲" },
];

export default function PatternRecognition({ onFinish }) {
  const [roundIndex, setRoundIndex] = useState(0);
  const [correctCount, setCorrectCount] = useState(0);
  const [feedback, setFeedback] = useState(null);
  const [done, setDone] = useState(false);

  const round = ROUNDS[roundIndex];

  function choose(option) {
    if (feedback) return;
    const isCorrect = option === round.answer;
    setFeedback({ option, isCorrect });
    setTimeout(() => {
      if (isCorrect) setCorrectCount((c) => c + 1);
      if (roundIndex + 1 < ROUNDS.length) {
        setRoundIndex((r) => r + 1);
        setFeedback(null);
      } else {
        setDone(true);
      }
    }, 700);
  }

  if (done) {
    return (
      <div className={styles.resultCard}>
        <p style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>All done!</p>
        <p style={{ color: "var(--muted)", marginBottom: 20 }}>
          You continued {correctCount} of {ROUNDS.length} patterns correctly. This reflects activity performance,
          not a clinical result.
        </p>
        <Button variant="accent" onClick={onFinish}>Back to activities</Button>
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <p style={{ textAlign: "center", color: "var(--muted)" }}>What comes next in the pattern?</p>
      <div className={styles.patternRow}>
        {round.sequence.map((symbol, i) => (
          <span key={i}>{symbol}</span>
        ))}
        <span style={{ color: "var(--line-strong)" }}>?</span>
      </div>
      <div className={styles.wordList}>
        {round.options.map((opt) => {
          let cls = styles.optionButton;
          if (feedback?.option === opt) {
            cls += ` ${feedback.isCorrect ? styles.optionCorrect : styles.optionIncorrect}`;
          }
          return (
            <button key={opt} type="button" className={cls} onClick={() => choose(opt)} style={{ fontSize: 28 }}>
              {opt}
            </button>
          );
        })}
      </div>
    </div>
  );
}
