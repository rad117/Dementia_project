import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Play, Pause, RotateCcw, AlertTriangle } from "lucide-react";
import { useRecorder } from "../../hooks/useRecorder.js";
import { useAssessment } from "../../app/AssessmentContext.jsx";
import MicButton from "../../components/assessment/MicButton.jsx";
import Waveform from "../../components/assessment/Waveform.jsx";
import Button from "../../components/common/Button.jsx";
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
      <h1 className={pageStyles.greeting}>Recording</h1>

      {state === "unsupported" && (
        <div className={styles.errorBox} role="alert">
          <p className={styles.errorTitle}>Recording isn't supported in this browser</p>
          <p className={styles.errorText}>
            This device or browser doesn't support audio recording. Please try a recent version of Chrome, Edge,
            Firefox or Safari, or ask a staff member for an alternative device.
          </p>
        </div>
      )}

      {state === "error" && error?.type === "permission_denied" && (
        <div className={styles.errorBox} role="alert">
          <AlertTriangle size={20} aria-hidden="true" style={{ color: "var(--red)", marginBottom: 8 }} />
          <p className={styles.errorTitle}>Microphone access needed</p>
          <p className={styles.errorText}>{error.message}</p>
          <Button variant="secondary" style={{ marginTop: 16 }} onClick={start}>
            Try again
          </Button>
        </div>
      )}

      {state === "error" && error?.type !== "permission_denied" && (
        <div className={styles.errorBox} role="alert">
          <AlertTriangle size={20} aria-hidden="true" style={{ color: "var(--red)", marginBottom: 8 }} />
          <p className={styles.errorTitle}>Something went wrong</p>
          <p className={styles.errorText}>{error?.message ?? "Please try again."}</p>
          <Button variant="secondary" style={{ marginTop: 16 }} onClick={reset}>
            Try again
          </Button>
        </div>
      )}

      {(state === "idle" || state === "requesting_permission") && (
        <div className={styles.stage}>
          <p className={styles.statusText}>
            {state === "requesting_permission" ? "Requesting microphone access…" : "Tap the microphone when you're ready."}
          </p>
          <MicButton
            recording={false}
            disabled={state === "requesting_permission"}
            onClick={start}
            label="Start recording"
          />
        </div>
      )}

      {state === "recording" && (
        <div className={styles.stage}>
          <p className={styles.statusText}>Listening…</p>
          <p className={styles.timer} aria-live="polite">{formatTime(elapsedSec)}</p>
          <Waveform level={level} active />
          <MicButton recording onClick={stop} label="Stop recording" />
        </div>
      )}

      {state === "stopped" && (
        <div className={styles.stage}>
          <p className={styles.statusText}>Recording complete</p>
          <p className={styles.timer}>{formatTime(elapsedSec)}</p>
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
              Playback isn't available right now, but your recording was captured and you can continue.
            </p>
          )}
          <div className={styles.buttonRow}>
            <Button variant="secondary" size="lg" onClick={togglePlayback}>
              {isPlaying ? <Pause size={18} aria-hidden="true" /> : <Play size={18} aria-hidden="true" />}
              {isPlaying ? "Pause" : "Play recording"}
            </Button>
            <Button variant="secondary" size="lg" onClick={reset}>
              <RotateCcw size={18} aria-hidden="true" /> Record again
            </Button>
            <Button variant="accent" size="lg" onClick={handleContinue}>
              Continue
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
