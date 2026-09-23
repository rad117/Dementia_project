import { createContext, useContext, useMemo, useState } from "react";
import { setAuthToken, clearAuthToken } from "../services/api.js";
import { logout as apiLogout } from "../services/index.js";

const SessionContext = createContext(null);

// Deliberately in-memory only (no localStorage/sessionStorage) — this is a
// demo identity placeholder, not a real auth session, and nothing here
// should persist across a hard refresh per the privacy requirements. The
// real backend's session token follows the same rule: it lives in api.js's
// module-scoped variable (set/cleared here), never in persisted storage.
export function SessionProvider({ children }) {
  const [participant, setParticipant] = useState(null); // { patientId, name }
  const [clinicalUser, setClinicalUser] = useState(null); // { name, role }

  const value = useMemo(
    () => ({
      participant,
      clinicalUser,
      loginParticipant: (patient) => {
        setAuthToken(patient.token);
        setParticipant(patient);
      },
      logoutParticipant: () => {
        apiLogout().catch(() => {});
        clearAuthToken();
        setParticipant(null);
      },
      loginClinical: (user) => {
        setAuthToken(user.token);
        setClinicalUser(user);
      },
      logoutClinical: () => {
        apiLogout().catch(() => {});
        clearAuthToken();
        setClinicalUser(null);
      },
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
