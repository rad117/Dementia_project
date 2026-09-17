import { createContext, useContext, useMemo, useState, useCallback } from "react";

const AssessmentContext = createContext(null);

// Holds the in-progress participant assessment state: language, task,
// recording artifact, assessment id, and eventual results. Reset between
// runs so a stale recording can never leak into a new assessment.
export function AssessmentProvider({ children }) {
  const [language, setLanguage] = useState(null);
  const [assessmentId, setAssessmentId] = useState(null);
  const [audioBlob, setAudioBlob] = useState(null);
  const [results, setResults] = useState(null);

  const reset = useCallback(() => {
    setLanguage(null);
    setAssessmentId(null);
    setAudioBlob(null);
    setResults(null);
  }, []);

  const value = useMemo(
    () => ({
      language,
      setLanguage,
      assessmentId,
      setAssessmentId,
      audioBlob,
      setAudioBlob,
      results,
      setResults,
      reset,
    }),
    [language, assessmentId, audioBlob, results, reset]
  );

  return <AssessmentContext.Provider value={value}>{children}</AssessmentContext.Provider>;
}

export function useAssessment() {
  const ctx = useContext(AssessmentContext);
  if (!ctx) throw new Error("useAssessment must be used within AssessmentProvider");
  return ctx;
}
