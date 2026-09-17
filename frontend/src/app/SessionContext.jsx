import { createContext, useContext, useMemo, useState } from "react";

const SessionContext = createContext(null);

// Deliberately in-memory only (no localStorage/sessionStorage) — this is a
// demo identity placeholder, not a real auth session, and nothing here
// should persist across a hard refresh per the privacy requirements.
export function SessionProvider({ children }) {
  const [participant, setParticipant] = useState(null); // { patientId, name }
  const [clinicalUser, setClinicalUser] = useState(null); // { name, role }

  const value = useMemo(
    () => ({
      participant,
      clinicalUser,
      loginParticipant: (patient) => setParticipant(patient),
      logoutParticipant: () => setParticipant(null),
      loginClinical: (user) => setClinicalUser(user),
      logoutClinical: () => setClinicalUser(null),
    }),
    [participant, clinicalUser]
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}
