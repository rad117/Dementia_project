import { useMemo, useState } from "react";
import { Apple, Umbrella, Sun, Star, Heart, Music, Flower2, Cloud } from "lucide-react";
import Button from "../../../components/common/Button.jsx";
import styles from "./activities.module.css";

const ICONS = [Apple, Umbrella, Sun, Star, Heart, Music, Flower2, Cloud];

function shuffledDeck() {
  const chosen = ICONS.slice(0, 6);
  const deck = [...chosen, ...chosen]
    .map((Icon, i) => ({ id: i, Icon, key: Icon.displayName ?? Icon.name }))
    .sort(() => Math.random() - 0.5);
  return deck;
}

export default function MemoryMatch({ onFinish }) {
  const [deck] = useState(shuffledDeck);
  const [flipped, setFlipped] = useState([]);
  const [matched, setMatched] = useState([]);

  const isComplete = matched.length === deck.length;

  function handleFlip(index) {
    if (flipped.includes(index) || matched.includes(index) || flipped.length === 2) return;
    const next = [...flipped, index];
    setFlipped(next);
    if (next.length === 2) {
      const [a, b] = next;
      if (deck[a].key === deck[b].key) {
        setTimeout(() => {
          setMatched((prev) => [...prev, a, b]);
          setFlipped([]);
        }, 400);
      } else {
        setTimeout(() => setFlipped([]), 700);
      }
    }
  }

  const cards = useMemo(() => deck, [deck]);

  if (isComplete) {
    return (
      <div className={styles.resultCard}>
        <p style={{ fontSize: 20, fontWeight: 700, marginBottom: 8, color: "var(--ink)" }}>All pairs matched</p>
        <p style={{ color: "var(--slate)", marginBottom: 20, fontSize: 16 }}>
          You've completed this exercise. This relaxed activity is for engagement and is not a clinical assessment.
        </p>
        <Button variant="accent" size="lg" onClick={onFinish}>Back to activities</Button>
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <p style={{ textAlign: "center", color: "var(--muted)" }}>Find the matching pairs.</p>
      <div className={styles.grid}>
        {cards.map((card, i) => {
          const isFlipped = flipped.includes(i) || matched.includes(i);
          return (
            <button
              key={card.id}
              type="button"
              className={`${styles.tile} ${matched.includes(i) ? styles.tileMatched : ""} ${isFlipped && !matched.includes(i) ? styles.tileFlipped : ""}`}
              onClick={() => handleFlip(i)}
              aria-label={isFlipped ? card.key : "Hidden card"}
            >
              {isFlipped && <card.Icon size={26} aria-hidden="true" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}
