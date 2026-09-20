import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Play, Pause, RotateCcw, AlertTriangle, ArrowRight, Square } from "lucide-react";
import { useRecorder } from "../../hooks/useRecorder.js";
import { useAssessment } from "../../app/AssessmentContext.jsx";
import MicButton from "../../components/assessment/MicButton.jsx";
import Waveform from "../../components/assessment/Waveform.jsx";
import Button from "../../components/common/Button.jsx";
import Badge from "../../components/common/Badge.jsx";
import pageStyles from "./patientPages.module.css";
import styles from "./Recording.module.css";

function formatTime(totalSeconds) {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function PatientRecording() {
  const { state, elapsedSec, level, audioBlob, audioUrl, error, start, stop, reset } = useRecorder();
  const { language, assessmentId, setAudioBlob } = useAssessment();
  const navigate = useNavigate();
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackError, setPlaybackError] = useState(false);

  useEffect(() => {
    if (!language || !assessmentId) navigate("/patient/task", { replace: true });
  }, [language, assessmentId, navigate]);

  function handleContinue() {
    setAudioBlob(audioBlob);
    navigate("/patient/processing");
  }

  function togglePlayback() {
    if (!audioRef.current) return;
    setPlaybackError(false);
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play().catch(() => setPlaybackError(true));
    }
  }

  if (!language || !assessmentId) return null;

  return (
    <div className={pageStyles.screen}>
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <Badge tone="accent">{language.label}</Badge>
          <span style={{ fontSize: 13, color: "var(--muted)", fontWeight: 600 }}>Step 4 of 4</span>
        </div>
        <div className={pageStyles.progressTrack}>
          <div className={pageStyles.progressFill} style={{ width: "100%" }} />
        </div>
        <h1 className={pageStyles.greeting}>Record your response</h1>
        <p className={pageStyles.subGreeting}>Describe the picture in your own words.</p>
      </div>

      {state === "unsupported" && (
        <div className={styles.errorBox} role="alert">
          <p className={styles.errorTitle}>Recording isn't supported in this browser</p>
          <p className={styles.errorText}>
            This device or browser doesn't support audio capture. Please try Chrome, Edge, Safari, or Firefox,
            or ask a team member for assistance.
          </p>
        </div>
      )}

      {state === "error" && error?.type === "permission_denied" && (
        <div className={styles.errorBox} role="alert">
          <AlertTriangle size={24} aria-hidden="true" style={{ color: "var(--red)", marginBottom: 8 }} />
          <p className={styles.errorTitle}>Microphone access needed</p>
          <p className={styles.errorText}>
            We couldn't access your microphone. Please check your browser permissions to allow microphone access,
            then select Record again.
          </p>
          <Button variant="secondary" size="lg" style={{ marginTop: 16 }} onClick={start}>
            Record again
          </Button>
        </div>
      )}

      {state === "error" && error?.type !== "permission_denied" && (
        <div className={styles.errorBox} role="alert">
          <AlertTriangle size={24} aria-hidden="true" style={{ color: "var(--red)", marginBottom: 8 }} />
          <p className={styles.errorTitle}>Microphone issue</p>
          <p className={styles.errorText}>{error?.message ?? "An unexpected recording error occurred. Please try again."}</p>
          <Button variant="secondary" size="lg" style={{ marginTop: 16 }} onClick={reset}>
            Record again
          </Button>
        </div>
      )}

      {(state === "idle" || state === "requesting_permission") && (
        <div className={styles.stage}>
          <div className={styles.promptTextWrap}>
            <p className={styles.stageMainPrompt}>Tell us what you see.</p>
            <p className={styles.stageSubPrompt}>Speak at your normal pace.</p>
          </div>

          <div className={styles.micWrap}>
            <MicButton
              recording={false}
              disabled={state === "requesting_permission"}
              onClick={start}
              label="Start recording"
            />
          </div>
          <p className={styles.actionHint}>
            {state === "requesting_permission" ? "Asking for microphone permission…" : "Tap to start"}
          </p>
        </div>
      )}

      {state === "recording" && (
        <div className={styles.stage}>
          <p className={styles.stageMainPrompt}>Recording</p>
          <p className={styles.timer} aria-live="polite">{formatTime(elapsedSec)}</p>
          
          <div className={styles.waveformWrap}>
            <Waveform level={level} active />
          </div>

          <Button
            variant="danger"
            size="lg"
            onClick={stop}
            style={{ minHeight: 56, fontSize: 18, paddingInline: 36, display: "flex", alignItems: "center", gap: 10 }}
          >
            <Square size={20} fill="currentColor" aria-hidden="true" />
            Stop recording
          </Button>
          <p className={styles.actionHint}>Tap when you have finished describing the picture</p>
        </div>
      )}

      {state === "stopped" && (
        <div className={styles.stage}>
          <p className={styles.stageMainPrompt}>Recording complete.</p>
          <p className={styles.timer}>{formatTime(elapsedSec)} recorded</p>
          {audioUrl && (
            <audio
              ref={audioRef}
              src={audioUrl}
              onEnded={() => setIsPlaying(false)}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              onError={() => setPlaybackError(true)}
            />
          )}
          {playbackError && (
            <p className={styles.statusText} style={{ color: "var(--red)", fontSize: 14 }} role="alert">
              Playback preview is unavailable, but your speech was recorded and is ready to submit.
            </p>
          )}
          <div className={styles.buttonRow}>
            <Button
              variant="secondary"
              size="lg"
              onClick={togglePlayback}
              style={{ minHeight: 52, fontSize: 16 }}
            >
              {isPlaying ? <Pause size={20} aria-hidden="true" /> : <Play size={20} aria-hidden="true" />}
              {isPlaying ? "Pause" : "Listen to recording"}
            </Button>
            <Button
              variant="secondary"
              size="lg"
              onClick={reset}
              style={{ minHeight: 52, fontSize: 16 }}
            >
              <RotateCcw size={20} aria-hidden="true" /> Record again
            </Button>
            <Button
              variant="accent"
              size="lg"
              onClick={handleContinue}
              style={{ minHeight: 54, fontSize: 18, marginTop: 4 }}
            >
              Continue <ArrowRight size={20} aria-hidden="true" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
