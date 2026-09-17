import { Link } from "react-router-dom";
import { Languages, Mic, FileText, TrendingUp, ShieldCheck, ArrowRight } from "lucide-react";
import { LineChart, Line, ResponsiveContainer, YAxis } from "recharts";
import Button from "../../components/common/Button.jsx";
import styles from "./Landing.module.css";

const STEPS = [
  { n: "01", title: "Choose language", description: "The participant selects their preferred language for the session." },
  { n: "02", title: "Describe a standardized image", description: "A consistent picture-description task keeps sessions comparable." },
  { n: "03", title: "Record speech", description: "A short spoken response is captured directly in the browser." },
  { n: "04", title: "Review structured analysis", description: "Clinicians review speech, language and task indicators." },
];

const TRAJECTORY_DATA = [
  { visit: 1, value: 82 },
  { visit: 2, value: 78 },
  { visit: 3, value: 74 },
  { visit: 4, value: 69 },
  { visit: 5, value: 71 },
  { visit: 6, value: 65 },
];

export default function Landing() {
  return (
    <>
      <section className={styles.hero}>
        <div className={`container ${styles.heroInner}`}>
          <div className={styles.heroCopy}>
            <p className={styles.eyebrow}>Cognitive screening platform</p>
            <h1 className={styles.headline}>Cognitive assessment, built around real speech.</h1>
            <p className={styles.subtext}>
              CognitiveAssist combines structured speech tasks, multilingual analysis and longitudinal clinical
              insight to support cognitive screening and follow-up.
            </p>
            <div className={styles.ctaRow}>
              <Button as={Link} to="/role" variant="accent" size="lg">
                Get Started <ArrowRight size={18} aria-hidden="true" />
              </Button>
              <Button as="a" href="#how-it-works" variant="secondary" size="lg">
                How it works
              </Button>
            </div>
          </div>

          <div className={styles.heroVisual} aria-hidden="true">
            <svg viewBox="0 0 400 320" className={styles.heroSvg} role="img" aria-label="">
              <rect x="0" y="0" width="400" height="320" rx="12" fill="#1B1E24" />
              <g stroke="#3157D5" strokeWidth="2" strokeLinecap="round">
                {Array.from({ length: 28 }).map((_, i) => {
                  const h = 20 + Math.abs(Math.sin(i * 0.6)) * 90 + (i % 5) * 6;
                  const x = 24 + i * 13;
                  return <line key={i} x1={x} y1={200 - h / 2} x2={x} y2={200 + h / 2} />;
                })}
              </g>
              <circle cx="340" cy="70" r="26" fill="none" stroke="#E9EDFF" strokeWidth="2" opacity="0.5" />
              <rect x="24" y="250" width="180" height="10" rx="5" fill="#30343B" />
              <rect x="24" y="270" width="120" height="10" rx="5" fill="#30343B" />
            </svg>
            <div className={styles.floatingCard}>
              <p className={styles.floatingLabel}>Assessment quality</p>
              <p className={styles.floatingValue}>Good</p>
              <p className={styles.floatingMeta}>ASR confidence 91% · Hindi</p>
            </div>
          </div>
        </div>
      </section>

      <section id="how-it-works" className={styles.section}>
        <div className="container">
          <h2 className={styles.sectionTitle}>How it works</h2>
          <div className={styles.stepsGrid}>
            {STEPS.map((step) => (
              <div key={step.n} className={styles.stepBlock}>
                <span className={styles.stepNumber}>{step.n}</span>
                <h3 className={styles.stepTitle}>{step.title}</h3>
                <p className={styles.stepDescription}>{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="multilingual" className={styles.sectionAlt}>
        <div className={`container ${styles.splitSection}`}>
          <div>
            <h2 className={styles.sectionTitle}>Built for multilingual assessment</h2>
            <p className={styles.sectionLead}>
              Language is treated as first-class metadata throughout the platform, not an afterthought.
            </p>
            <ul className={styles.checkList}>
              <li><Languages size={18} aria-hidden="true" /> Language selection at the start of every session</li>
              <li><Mic size={18} aria-hidden="true" /> Native voice interaction via browser recording</li>
              <li><FileText size={18} aria-hidden="true" /> Language-aware transcript and analysis</li>
              <li><TrendingUp size={18} aria-hidden="true" /> Task-specific semantic analysis per language</li>
            </ul>
          </div>
          <div className={styles.languageGrid} aria-hidden="true">
            {["English", "Hindi", "Marathi", "Tamil", "Bengali", "Telugu", "Urdu", "Kannada"].map((l) => (
              <span key={l} className={styles.languageChip}>{l}</span>
            ))}
          </div>
        </div>
      </section>

      <section id="insights" className={styles.section}>
        <div className="container">
          <div className={styles.trajectoryLayout}>
            <div>
              <h2 className={styles.sectionTitle}>The useful signal is often in the change.</h2>
              <p className={styles.sectionLead}>
                Repeated assessments allow clinicians to review changes in speech, language and task performance
                over time. No single metric on its own proves disease progression — the trend is reviewed in
                clinical context.
              </p>
            </div>
            <div className={styles.chartCard}>
              <p className={styles.chartLabel}>Illustrative concept-coverage trend</p>
              <ResponsiveContainer width="100%" height={140}>
                <LineChart data={TRAJECTORY_DATA} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
                  <YAxis hide domain={["dataMin - 5", "dataMax + 5"]} />
                  <Line type="monotone" dataKey="value" stroke="#3157D5" strokeWidth={2.5} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
              <p className={styles.chartCaption}>Demo data across six visits</p>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.sectionAlt}>
        <div className="container">
          <h2 className={styles.sectionTitle}>Clinical review</h2>
          <p className={styles.sectionLead}>
            A dense, structured review workspace built for clinical professionals reading speech, language and task
            data across a caseload.
          </p>
          <div className={styles.dashboardMock} aria-hidden="true">
            <div className={styles.dashboardMockSidebar} />
            <div className={styles.dashboardMockMain}>
              <div className={styles.dashboardMockRow}>
                <span /><span /><span /><span />
              </div>
              <div className={styles.dashboardMockTable}>
                <span /><span /><span /><span /><span />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="privacy" className={styles.section}>
        <div className={`container ${styles.privacySection}`}>
          <ShieldCheck size={28} aria-hidden="true" />
          <h2 className={styles.sectionTitle}>Privacy</h2>
          <p className={styles.sectionLead}>
            Recordings and derived indicators are handled as sensitive clinical data. This frontend is a demo shell
            around a service boundary designed for a backend team to implement proper storage, consent and access
            controls.
          </p>
        </div>
      </section>
      <p id="accessibility-note" className="visually-hidden">CognitiveAssist supports keyboard navigation and screen readers throughout.</p>
    </>
  );
}
