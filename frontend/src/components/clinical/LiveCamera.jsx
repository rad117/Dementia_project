import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, Square } from "lucide-react";
import { getLastObservation, getMonitoringStatus, submitMonitoringFrame } from "../../services/index.js";
import Button from "../common/Button.jsx";
import styles from "./LiveCamera.module.css";

const FRAME_INTERVAL_MS = 500; // 2 frames per second, matching the server's clip timing
const POLL_MS = 2000;
const FRAME_WIDTH = 640;

function yesNo(value) {
  return value ? "Yes" : "No";
}

// Streams this browser's webcam to the backend pose/vision pipeline.
// The video is only shown locally; the server analyses frames in memory and
// stores the structured result (posture, flags, alerts), never the images.
export default function LiveCamera({ patientId, available }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const sendTimer = useRef(null);
  const inFlight = useRef(false);
  const patientRef = useRef(patientId);
  // Bumped by every stop. Camera startup and frame encoding finish later, so each
  // checks it is still in the same session before doing anything with the result.
  const sessionRef = useRef(0);
  const [phase, setPhase] = useState("idle"); // idle | starting | running
  const [error, setError] = useState(null);
  const [observation, setObservation] = useState(null);
  const [counters, setCounters] = useState(null);

  const stop = useCallback(() => {
    sessionRef.current += 1;
    clearInterval(sendTimer.current);
    sendTimer.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    inFlight.current = false;
    setPhase("idle");
  }, []);

  useEffect(() => stop, [stop]);

  // Monitoring belongs to one patient: changing patient stops the camera, so one
  // person's readings and alerts can never be filed under another.
  useEffect(() => {
    patientRef.current = patientId;
    stop();
    setObservation(null);
    setCounters(null);
  }, [patientId, stop]);

  const sendFrame = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || inFlight.current || video.videoWidth === 0) return;
    const scale = Math.min(1, FRAME_WIDTH / video.videoWidth);
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    inFlight.current = true;
    // Fixed now, at capture: this frame belongs to this patient whatever happens next.
    const session = sessionRef.current;
    const framePatient = patientRef.current;
    const stale = () => session !== sessionRef.current;
    canvas.toBlob(
      (blob) => {
        if (stale()) return;
        if (!blob) {
          inFlight.current = false;
          return;
        }
        submitMonitoringFrame(blob, framePatient || undefined)
          .then((result) => {
            if (!stale() && result?.status === "unavailable") {
              setError(`Camera analysis isn't available on this server (missing: ${(result.missing ?? []).join(", ") || "unknown"}).`);
              stop();
            }
          })
          .catch((err) => {
            if (stale()) return;
            setError(err.message ?? "Couldn't send a frame to the server.");
            stop();
          })
          .finally(() => {
            if (!stale()) inFlight.current = false;
          });
      },
      "image/jpeg",
      0.7
    );
  }, [stop]);

  async function start() {
    setError(null);
    setObservation(null);
    if (!patientId) return;
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("This browser can't access a camera here. Use Chrome or Safari on https or localhost.");
      return;
    }
    setPhase("starting");
    const session = sessionRef.current;
    const stale = () => session !== sessionRef.current;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
        audio: false,
      });
      if (stale()) {
        // The patient changed while the permission prompt was open: release the camera.
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      streamRef.current = stream;
      const video = videoRef.current;
      video.srcObject = stream;
      await video.play();
      if (stale()) return;
      sendTimer.current = setInterval(sendFrame, FRAME_INTERVAL_MS);
      setPhase("running");
    } catch (err) {
      if (stale()) return;
      stop();
      setError(
        err?.name === "NotAllowedError"
          ? "Camera permission was denied. Allow camera access for this site in the browser, then try again."
          : err?.name === "NotFoundError"
            ? "No camera was found on this device."
            : (err?.message ?? "Couldn't start the camera.")
      );
    }
  }

  useEffect(() => {
    if (phase !== "running") return undefined;
    let cancelled = false;
    async function poll() {
      try {
        const [obs, status] = await Promise.all([getLastObservation(patientId), getMonitoringStatus()]);
        if (cancelled) return;
        setObservation(obs?.observation ? obs : null);
        setCounters(status.counters);
      } catch {
        /* a failed poll only means one stale readout */
      }
    }
    poll();
    const timer = setInterval(poll, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [phase, patientId]);

  const o = observation?.observation;
  const tiers = counters?.tiers;
  const running = phase === "running";

  return (
    <div className={styles.wrap}>
      <div className={styles.videoBox}>
        <video ref={videoRef} className={styles.video} muted playsInline aria-label="Camera preview" />
        {running && <span className={styles.live}>LIVE</span>}
        {!running && (
          <div className={styles.placeholder}>
            {phase === "starting" ? "Starting camera…" : "Camera is off. Nothing is being recorded or analysed."}
          </div>
        )}
        <canvas ref={canvasRef} hidden />
      </div>

      <div className={styles.side}>
        <div className={styles.controls}>
          {!running ? (
            <Button variant="accent" size="sm" onClick={start} disabled={phase === "starting" || available === false || !patientId}>
              <Camera size={15} aria-hidden="true" /> Start camera
            </Button>
          ) : (
            <Button variant="secondary" size="sm" onClick={stop}>
              <Square size={14} aria-hidden="true" /> Stop camera
            </Button>
          )}
        </div>

        {available === false && (
          <p className={styles.note}>Camera analysis isn&apos;t installed on this server, so the camera can&apos;t be used here.</p>
        )}
        {available !== false && !patientId && (
          <p className={styles.note}>Select a patient above first. Alerts and family texts are sent for that patient.</p>
        )}
        {error && <p className={styles.err} role="alert">{error}</p>}

        {running && !o && <p className={styles.note}>Watching… the first reading appears after about 5 seconds.</p>}
        {running && o && (
          <dl className={styles.readout}>
            <div><dt>Person in view</dt><dd>{yesNo(o.person_present)}</dd></div>
            <div><dt>Posture</dt><dd>{o.posture}</dd></div>
            <div><dt>Motion</dt><dd>{o.motion}</dd></div>
            <div><dt>On the floor</dt><dd className={o.on_floor ? styles.warn : styles.ok}>{yesNo(o.on_floor)}</dd></div>
            <div><dt>Fall in progress</dt><dd className={o.fall_in_progress ? styles.warn : styles.ok}>{yesNo(o.fall_in_progress)}</dd></div>
            <div><dt>Sudden drop</dt><dd className={o.sudden_descent ? styles.warn : styles.ok}>{yesNo(o.sudden_descent)}</dd></div>
          </dl>
        )}
        {running && counters && (
          <p className={styles.note}>
            {counters.frames} frames received · {counters.clips} clips analysed
            {tiers ? ` · pose ${tiers.pose_clips}, vision model ${tiers.vlm_clips} (${tiers.vlm})` : ""}
          </p>
        )}

        <p className={styles.note}>
          The video stays in this browser tab. The server analyses frames in memory and keeps only the result
          (posture, flags and any alerts), never the images. Alerts appear in the list above.
        </p>
      </div>
    </div>
  );
}
