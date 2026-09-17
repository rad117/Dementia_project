import { pictureDescriptionTask } from "../../data/mockTasks.js";
import styles from "./PictureStimulus.module.css";

// Original, non-photographic composed illustration for the standardized
// picture-description task. Deliberately schematic/editorial rather than
// cartoonish, per the participant "not childish" visual requirement.
export default function PictureStimulus() {
  return (
    <div className={styles.frame}>
      <svg viewBox="0 0 480 320" role="img" aria-label={pictureDescriptionTask.imageAlt} className={styles.svg}>
        <rect x="0" y="0" width="480" height="320" fill="#F6F5F1" />
        {/* Room outline */}
        <rect x="16" y="16" width="448" height="288" fill="none" stroke="#30343B" strokeWidth="2" />
        {/* Window */}
        <rect x="340" y="40" width="90" height="70" fill="#E9EDFF" stroke="#30343B" strokeWidth="2" />
        <line x1="385" y1="40" x2="385" y2="110" stroke="#30343B" strokeWidth="2" />
        <line x1="340" y1="75" x2="430" y2="75" stroke="#30343B" strokeWidth="2" />

        {/* Shelf with jar */}
        <rect x="150" y="70" width="120" height="10" fill="#30343B" />
        <rect x="195" y="40" width="30" height="30" rx="4" fill="#D99A21" stroke="#111318" strokeWidth="2" />
        <ellipse cx="210" cy="40" rx="15" ry="4" fill="#111318" opacity="0.15" />

        {/* Child on stool reaching */}
        <g>
          <rect x="185" y="205" width="50" height="14" rx="3" fill="#7159B8" />
          <line x1="192" y1="219" x2="188" y2="245" stroke="#7159B8" strokeWidth="6" strokeLinecap="round" />
          <line x1="228" y1="219" x2="232" y2="245" stroke="#7159B8" strokeWidth="6" strokeLinecap="round" />
          <circle cx="210" cy="150" r="14" fill="#3157D5" />
          <rect x="198" y="163" width="24" height="42" rx="8" fill="#3157D5" />
          <line x1="222" y1="175" x2="205" y2="95" stroke="#3157D5" strokeWidth="7" strokeLinecap="round" />
        </g>

        {/* Woman drying a dish, not noticing */}
        <g>
          <circle cx="330" cy="170" r="15" fill="#2443A8" />
          <rect x="315" y="184" width="30" height="55" rx="8" fill="#2443A8" />
          <line x1="315" y1="200" x2="295" y2="215" stroke="#2443A8" strokeWidth="7" strokeLinecap="round" />
          <rect x="285" y="208" width="18" height="14" rx="2" fill="#FFFFFF" stroke="#111318" strokeWidth="2" />
        </g>

        {/* Sink with overflowing water */}
        <rect x="80" y="220" width="90" height="40" rx="4" fill="#FFFFFF" stroke="#30343B" strokeWidth="2" />
        <path
          d="M85 258 C 95 275, 60 280, 55 300 M100 258 C 105 280, 130 285, 120 305"
          stroke="#3157D5"
          strokeWidth="4"
          fill="none"
          strokeLinecap="round"
        />
        <rect x="60" y="300" width="70" height="8" fill="#3157D5" opacity="0.35" />

        {/* Falling object cue near shelf */}
        <circle cx="245" cy="110" r="5" fill="#C94B4B" />
      </svg>
    </div>
  );
}
