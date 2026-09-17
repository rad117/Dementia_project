import { useCallback, useEffect, useRef, useState } from "react";

// States: idle | requesting_permission | recording | stopped | error | unsupported
export function useRecorder() {
  const [state, setState] = useState("idle");
  const [elapsedSec, setElapsedSec] = useState(0);
  const [level, setLevel] = useState(0); // 0..1 live audio level for the waveform
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [error, setError] = useState(null);

  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const rafRef = useRef(null);

  const isSupported = useCallback(() => {
    return (
      typeof navigator !== "undefined" &&
      !!navigator.mediaDevices &&
      typeof navigator.mediaDevices.getUserMedia === "function" &&
      typeof window !== "undefined" &&
      typeof window.MediaRecorder === "function"
    );
  }, []);

  useEffect(() => {
    if (!isSupported()) {
      setState("unsupported");
    }
    return () => cleanup();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function cleanup() {
    if (timerRef.current) clearInterval(timerRef.current);
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
  }

  function trackLevel() {
    const analyser = analyserRef.current;
    if (!analyser) return;
    const data = new Uint8Array(analyser.frequencyBinCount);
    const tick = () => {
      analyser.getByteTimeDomainData(data);
      let sum = 0;
      for (let i = 0; i < data.length; i++) {
        const v = (data[i] - 128) / 128;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / data.length);
      setLevel(Math.min(1, rms * 4));
      rafRef.current = requestAnimationFrame(tick);
    };
    tick();
  }

  const start = useCallback(async () => {
    if (!isSupported()) {
      setState("unsupported");
      return;
    }

    setError(null);
    setAudioBlob(null);
    setAudioUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });
    setState("requesting_permission");

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      setState("error");
      if (err && (err.name === "NotAllowedError" || err.name === "PermissionDeniedError")) {
        setError({
          type: "permission_denied",
          message:
            "Microphone access is required for this assessment. Please allow microphone access in your browser and try again.",
        });
      } else if (err && err.name === "NotFoundError") {
        setError({ type: "no_microphone", message: "No microphone was found on this device." });
      } else {
        setError({ type: "unknown", message: "We couldn't start the microphone. Please try again." });
      }
      return;
    }

    streamRef.current = stream;

    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      const audioContext = new AudioContextClass();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);
      audioContextRef.current = audioContext;
      analyserRef.current = analyser;
      trackLevel();
    } catch {
      // Waveform is a progressive enhancement — recording still works without it.
    }

    chunksRef.current = [];
    let recorder;
    try {
      recorder = new MediaRecorder(stream);
    } catch {
      setState("error");
      setError({ type: "unknown", message: "Recording could not be started on this device." });
      cleanup();
      return;
    }

    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) chunksRef.current.push(event.data);
    };

    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
      setAudioBlob(blob);
      setAudioUrl(URL.createObjectURL(blob));
      setState("stopped");
      if (timerRef.current) clearInterval(timerRef.current);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      setLevel(0);
    };

    recorder.onerror = () => {
      setState("error");
      setError({ type: "recording_error", message: "Recording stopped unexpectedly. Please try again." });
    };

    mediaRecorderRef.current = recorder;
    recorder.start();
    setState("recording");
    setElapsedSec(0);
    timerRef.current = setInterval(() => {
      setElapsedSec((prev) => prev + 1);
    }, 1000);
  }, [isSupported]);

  const stop = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    cleanup();
    setState(isSupported() ? "idle" : "unsupported");
    setElapsedSec(0);
    setLevel(0);
    setError(null);
    setAudioBlob(null);
    setAudioUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isSupported]);

  return { state, elapsedSec, level, audioBlob, audioUrl, error, start, stop, reset };
}
