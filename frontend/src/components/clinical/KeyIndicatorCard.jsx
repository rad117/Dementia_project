import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import Sparkline from "../charts/Sparkline.jsx";
import styles from "./KeyIndicatorCard.module.css";

const DIRECTION_ICON = { increased: TrendingUp, decreased: TrendingDown, steady: Minus };

export default function KeyIndicatorCard({ label, value, unit, percent, direction, sparklineData }) {
  const Icon = DIRECTION_ICON[direction] ?? Minus;
  return (
    <div className={styles.card}>
      <p className={styles.label}>{label}</p>
      <p className={styles.value}>
        {value}
        {unit && <span className={styles.unit}>{unit}</span>}
      </p>
      {direction && (
        <p className={styles.change}>
          <Icon size={14} aria-hidden="true" />
          {direction === "steady" ? "Steady vs previous" : `${percent}% vs previous`}
        </p>
      )}
      {sparklineData && sparklineData.length >= 2 && (
        <div className={styles.sparkline}>
          <Sparkline data={sparklineData} />
        </div>
      )}
    </div>
  );
}
