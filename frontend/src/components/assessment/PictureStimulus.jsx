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
        {/* Wall/floor guideline for background depth */}
        <line x1="16" y1="110" x2="464" y2="110" stroke="#E3E0D6" strokeWidth="1.5" />

        {/* Window with tree and cloud visible outside */}
        <rect x="345" y="30" width="95" height="70" fill="#E9EDFF" stroke="#30343B" strokeWidth="2" />
        <line x1="392" y1="30" x2="392" y2="100" stroke="#30343B" strokeWidth="2" />
        <line x1="345" y1="65" x2="440" y2="65" stroke="#30343B" strokeWidth="2" />
        <rect x="358" y="75" width="6" height="20" fill="#7A5230" />
        <circle cx="361" cy="63" r="13" fill="#3E8E5B" />
        <ellipse cx="418" cy="45" rx="14" ry="8" fill="#FFFFFF" stroke="#C7CBD6" strokeWidth="1" />
        <ellipse cx="428" cy="48" rx="10" ry="6" fill="#FFFFFF" stroke="#C7CBD6" strokeWidth="1" />

        {/* Shelf with cookie jar */}
        <rect x="225" y="95" width="110" height="8" fill="#30343B" />
        <rect x="265" y="63" width="32" height="32" rx="4" fill="#D99A21" stroke="#111318" strokeWidth="2" />
        <ellipse cx="281" cy="63" rx="16" ry="4" fill="#111318" opacity="0.15" />

        {/* Boy on a tilting stool reaching into the jar */}
        <g>
          <rect
            x="245"
            y="225"
            width="55"
            height="12"
            rx="3"
            fill="#7159B8"
            transform="rotate(-6 272 231)"
          />
          <line x1="253" y1="237" x2="248" y2="272" stroke="#7159B8" strokeWidth="6" strokeLinecap="round" />
          <line x1="290" y1="234" x2="296" y2="258" stroke="#7159B8" strokeWidth="6" strokeLinecap="round" />
          <circle cx="272" cy="170" r="14" fill="#3157D5" />
          <rect x="260" y="183" width="24" height="32" rx="8" fill="#3157D5" />
          <line x1="265" y1="215" x2="263" y2="225" stroke="#3157D5" strokeWidth="6" strokeLinecap="round" />
          <line x1="283" y1="215" x2="287" y2="225" stroke="#3157D5" strokeWidth="6" strokeLinecap="round" />
          <line x1="284" y1="190" x2="278" y2="97" stroke="#3157D5" strokeWidth="7" strokeLinecap="round" />
        </g>

        {/* Falling cookie cue, arcing toward the girl below */}
        <circle cx="250" cy="112" r="5" fill="#C94B4B" />

        {/* Girl reaching up toward her brother */}
        <g>
          <circle cx="185" cy="205" r="12" fill="#C65D8A" />
          <rect x="174" y="217" width="22" height="36" rx="7" fill="#C65D8A" />
          <line x1="196" y1="222" x2="228" y2="175" stroke="#C65D8A" strokeWidth="6" strokeLinecap="round" />
          <line x1="174" y1="222" x2="155" y2="200" stroke="#C65D8A" strokeWidth="6" strokeLinecap="round" />
          <line x1="179" y1="253" x2="175" y2="278" stroke="#C65D8A" strokeWidth="6" strokeLinecap="round" />
          <line x1="191" y1="253" x2="195" y2="278" stroke="#C65D8A" strokeWidth="6" strokeLinecap="round" />
        </g>

        {/* Woman drying a dish, not noticing the sink */}
        <g>
          <circle cx="390" cy="175" r="15" fill="#2443A8" />
          <rect x="375" y="190" width="30" height="55" rx="8" fill="#2443A8" />
          <line x1="382" y1="245" x2="380" y2="270" stroke="#2443A8" strokeWidth="6" strokeLinecap="round" />
          <line x1="398" y1="245" x2="400" y2="270" stroke="#2443A8" strokeWidth="6" strokeLinecap="round" />
          <line x1="375" y1="205" x2="350" y2="222" stroke="#2443A8" strokeWidth="7" strokeLinecap="round" />
          <rect x="338" y="214" width="20" height="15" rx="2" fill="#FFFFFF" stroke="#111318" strokeWidth="2" />
        </g>

        {/* Sink with overflowing water */}
        <rect x="40" y="230" width="90" height="38" rx="4" fill="#FFFFFF" stroke="#30343B" strokeWidth="2" />
        <path
          d="M50 230 C 60 260, 30 285, 28 305 M70 230 C 75 260, 100 285, 92 306"
          stroke="#3157D5"
          strokeWidth="4"
          fill="none"
          strokeLinecap="round"
        />
        <rect x="25" y="302" width="80" height="8" fill="#3157D5" opacity="0.35" />

        {/* Cat reacting to the spreading puddle */}
        <g>
          <ellipse cx="115" cy="290" rx="18" ry="10" fill="#4A4A4A" />
          <circle cx="132" cy="282" r="8" fill="#4A4A4A" />
          <polygon points="126,276 130,268 134,277" fill="#4A4A4A" />
          <polygon points="134,277 138,269 141,278" fill="#4A4A4A" />
          <path d="M97 292 Q 85 280, 90 268" stroke="#4A4A4A" strokeWidth="4" fill="none" strokeLinecap="round" />
        </g>
      </svg>
    </div>
  );
}
