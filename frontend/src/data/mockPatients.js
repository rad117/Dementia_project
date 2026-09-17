// Fictional demo patients only. Never real patient data.
// `trend` drives deterministic mock assessment generation in mockAssessments.js
// (declining / improving / stable / mixed) — it is a data-generation knob,
// not a clinical label shown anywhere in the UI.

export const mockPatients = [
  {
    id: "CA-1001",
    name: "Rajesh Kumar",
    age: 71,
    preferredLanguage: "Hindi",
    loginCode: "PT-1001",
    trend: "declining",
    assessmentCount: 4,
  },
  {
    id: "CA-1002",
    name: "Anita Shah",
    age: 68,
    preferredLanguage: "Marathi",
    loginCode: "PT-1002",
    trend: "stable",
    assessmentCount: 3,
  },
  {
    id: "CA-1003",
    name: "Meena Iyer",
    age: 74,
    preferredLanguage: "Tamil",
    loginCode: "PT-1003",
    trend: "improving",
    assessmentCount: 3,
  },
  {
    id: "CA-1004",
    name: "Abdul Rahman",
    age: 69,
    preferredLanguage: "Urdu",
    loginCode: "PT-1004",
    trend: "mixed",
    assessmentCount: 2,
  },
  {
    id: "CA-1005",
    name: "Sunita Das",
    age: 77,
    preferredLanguage: "Bengali",
    loginCode: "PT-1005",
    trend: "declining",
    assessmentCount: 4,
  },
  {
    id: "CA-1006",
    name: "Joseph Thomas",
    age: 66,
    preferredLanguage: "English",
    loginCode: "PT-1006",
    trend: "stable",
    assessmentCount: 3,
  },
  {
    id: "CA-1007",
    name: "Lakshmi Venkataraman Subramaniam",
    age: 72,
    preferredLanguage: "Telugu",
    loginCode: "PT-1007",
    trend: "mixed",
    assessmentCount: 2,
  },
  {
    id: "CA-1008",
    name: "Ravi Shankar Nair",
    age: 70,
    preferredLanguage: "Kannada",
    loginCode: "PT-1008",
    trend: "declining",
    assessmentCount: 3,
  },
  {
    id: "CA-1009",
    name: "Fatima Sheikh",
    age: 65,
    preferredLanguage: "Urdu",
    loginCode: "PT-1009",
    trend: "stable",
    assessmentCount: 1,
  },
  {
    id: "CA-1010",
    name: "David Fernandes",
    age: 73,
    preferredLanguage: "English",
    loginCode: "PT-1010",
    trend: "stable",
    assessmentCount: 4,
  },
];

export function getPatientById(id) {
  return mockPatients.find((p) => p.id === id) ?? null;
}
