import { mockApi } from "./mockApi.js";
import { api as realApi } from "./api.js";

const useMock = import.meta.env.VITE_USE_MOCK_API !== "false";

export const isMockApi = useMock;
export const api = useMock ? mockApi : realApi;

export const {
  getPatients,
  getPatient,
  getPatientAssessments,
  getAssessment,
  createAssessment,
  uploadAssessmentAudio,
  getAssessmentResults,
  getAllAssessments,
  verifyParticipantCode,
  loginClinicalUser,
} = api;
