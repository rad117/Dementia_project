import { Navigate, Outlet } from "react-router-dom";
import { useSession } from "./SessionContext.jsx";

export function RequireParticipant() {
  const { participant } = useSession();
  if (!participant) return <Navigate to="/login/patient" replace />;
  return <Outlet />;
}

export function RequireClinical() {
  const { clinicalUser } = useSession();
  if (!clinicalUser) return <Navigate to="/login/clinical" replace />;
  return <Outlet />;
}
