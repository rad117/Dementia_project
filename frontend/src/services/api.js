// Real backend implementation of the API service interface. Structurally
// mirrors mockApi.js so swapping VITE_USE_MOCK_API=false requires no
// component changes — only this file talks to the network.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

class ApiError extends Error {
  constructor(message, code = "API_ERROR", status) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request(path, options = {}) {
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers: isFormData ? options.headers : { "Content-Type": "application/json", ...options.headers },
    });
  } catch {
    throw new ApiError(
      "We couldn't reach the analysis service. Your assessment has not been lost. Please try again.",
      "NETWORK_ERROR"
    );
  }

  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const body = await response.json();
      if (body?.message) message = body.message;
    } catch {
      // ignore body parse failures
    }
    throw new ApiError(message, "HTTP_ERROR", response.status);
  }

  if (response.status === 204) return null;
  return response.json();
}

export async function getPatients(params = {}) {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
  ).toString();
  return request(`/patients${query ? `?${query}` : ""}`);
}

export async function getPatient(id) {
  return request(`/patients/${id}`);
}

export async function getPatientAssessments(id) {
  return request(`/patients/${id}/assessments`);
}

export async function getAssessment(id) {
  return request(`/assessments/${id}`);
}

export async function createAssessment(payload) {
  return request("/assessments", { method: "POST", body: JSON.stringify(payload) });
}

export async function uploadAssessmentAudio(id, audioBlob) {
  const formData = new FormData();
  formData.append("audio", audioBlob, `${id}.webm`);
  return request(`/assessments/${id}/audio`, {
    method: "POST",
    headers: {}, // let the browser set multipart boundary
    body: formData,
  });
}

export async function getAssessmentResults(id) {
  return request(`/assessments/${id}/results`);
}

export async function getAllAssessments() {
  return request("/assessments");
}

export async function verifyParticipantCode(code) {
  return request("/auth/participant", { method: "POST", body: JSON.stringify({ code }) });
}

export async function loginClinicalUser(credentials) {
  return request("/auth/clinical", { method: "POST", body: JSON.stringify(credentials) });
}

export const api = {
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
};

export { ApiError };
