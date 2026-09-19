# CognitiveAssist Frontend

React 19 + Vite app implementing the patient screening flow (language select → task → mic recording → processing → results) and a clinician dashboard. See `CONTEXT.md` (repo root) for the full product spec.

## Setup

```
cd frontend
npm install
npm run dev
```

## Talking to the backend

By default the app runs entirely against a built-in mock API (`src/services/mockApi.js`) — no backend required. To point it at the real backend instead:

```
cp .env.example .env.local
# then edit .env.local if the backend isn't on http://127.0.0.1:8000
```

This only makes the **patient screening flow** real (Language → Task → Recording → Processing → Complete) — the backend implements `POST /assessments`, `POST /assessments/{id}/audio`, `GET /assessments/{id}/results`. The clinician dashboard/login pages (`Dashboard`, `Patients`, `PatientProfile`, `AssessmentDetail`, `AssessmentCompare`, `PatientLogin`) call endpoints (`/patients`, `/auth/*`, etc.) the backend doesn't implement yet — those still need `VITE_USE_MOCK_API` unset/mock, or will fail once flipped to the real backend, until that separate ticket lands.

## Other scripts

- `npm run build` — production build
- `npm run lint` — oxlint
- `npm run preview` — preview a production build locally
