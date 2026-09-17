import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";

import PublicLayout from "../components/layout/PublicLayout.jsx";
import AuthLayout from "../components/layout/AuthLayout.jsx";
import ParticipantLayout from "../components/layout/ParticipantLayout.jsx";
import ClinicalLayout from "../components/layout/ClinicalLayout.jsx";
import { RequireParticipant, RequireClinical } from "./guards.jsx";
import Skeleton from "../components/common/Skeleton.jsx";

import Landing from "../pages/public/Landing.jsx";
import RoleSelect from "../pages/public/RoleSelect.jsx";
import PatientLogin from "../pages/public/PatientLogin.jsx";
import ClinicalLogin from "../pages/public/ClinicalLogin.jsx";
import NotFound from "../pages/public/NotFound.jsx";

import PatientHome from "../pages/patient/Home.jsx";
import PatientLanguage from "../pages/patient/Language.jsx";
import PatientInstructions from "../pages/patient/Instructions.jsx";
import PatientTask from "../pages/patient/Task.jsx";
import PatientRecording from "../pages/patient/Recording.jsx";
import PatientProcessing from "../pages/patient/Processing.jsx";
import PatientComplete from "../pages/patient/Complete.jsx";
import PatientActivities from "../pages/patient/Activities.jsx";

// Clinical routes are dense/analytics-heavy (Recharts, transcript viewers,
// etc.) and are not needed for the participant path — split them out of
// the main bundle.
const ClinicalDashboard = lazy(() => import("../pages/clinical/Dashboard.jsx"));
const ClinicalPatients = lazy(() => import("../pages/clinical/Patients.jsx"));
const ClinicalPatientProfile = lazy(() => import("../pages/clinical/PatientProfile.jsx"));
const ClinicalAssessmentDetail = lazy(() => import("../pages/clinical/AssessmentDetail.jsx"));
const ClinicalAssessmentCompare = lazy(() => import("../pages/clinical/AssessmentCompare.jsx"));
const ClinicalSettings = lazy(() => import("../pages/clinical/Settings.jsx"));
const ClinicalModelInfo = lazy(() => import("../pages/clinical/ModelInfo.jsx"));
const ClinicalPrivacy = lazy(() => import("../pages/clinical/Privacy.jsx"));

function ClinicalRouteFallback() {
  return (
    <div style={{ padding: "var(--space-6)" }}>
      <Skeleton height="320px" radius="lg" />
    </div>
  );
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<Landing />} />
      </Route>

      <Route element={<AuthLayout />}>
        <Route path="/role" element={<RoleSelect />} />
        <Route path="/login/patient" element={<PatientLogin />} />
        <Route path="/login/clinical" element={<ClinicalLogin />} />
      </Route>

      <Route element={<RequireParticipant />}>
        <Route element={<ParticipantLayout />}>
          <Route path="/patient" element={<PatientHome />} />
          <Route path="/patient/language" element={<PatientLanguage />} />
          <Route path="/patient/instructions" element={<PatientInstructions />} />
          <Route path="/patient/task" element={<PatientTask />} />
          <Route path="/patient/recording" element={<PatientRecording />} />
          <Route path="/patient/processing" element={<PatientProcessing />} />
          <Route path="/patient/complete" element={<PatientComplete />} />
          <Route path="/patient/activities" element={<PatientActivities />} />
        </Route>
      </Route>

      <Route element={<RequireClinical />}>
        <Route element={<ClinicalLayout />}>
          <Route
            path="/clinical"
            element={
              <Suspense fallback={<ClinicalRouteFallback />}>
                <ClinicalDashboard />
              </Suspense>
            }
          />
          <Route
            path="/clinical/patients"
            element={
              <Suspense fallback={<ClinicalRouteFallback />}>
                <ClinicalPatients />
              </Suspense>
            }
          />
          <Route
            path="/clinical/patients/:patientId"
            element={
              <Suspense fallback={<ClinicalRouteFallback />}>
                <ClinicalPatientProfile />
              </Suspense>
            }
          />
          <Route
            path="/clinical/assessments/:assessmentId"
            element={
              <Suspense fallback={<ClinicalRouteFallback />}>
                <ClinicalAssessmentDetail />
              </Suspense>
            }
          />
          <Route
            path="/clinical/assessments/:assessmentId/compare"
            element={
              <Suspense fallback={<ClinicalRouteFallback />}>
                <ClinicalAssessmentCompare />
              </Suspense>
            }
          />
          <Route
            path="/clinical/settings"
            element={
              <Suspense fallback={<ClinicalRouteFallback />}>
                <ClinicalSettings />
              </Suspense>
            }
          />
          <Route
            path="/clinical/model"
            element={
              <Suspense fallback={<ClinicalRouteFallback />}>
                <ClinicalModelInfo />
              </Suspense>
            }
          />
          <Route
            path="/clinical/privacy"
            element={
              <Suspense fallback={<ClinicalRouteFallback />}>
                <ClinicalPrivacy />
              </Suspense>
            }
          />
        </Route>
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
