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

Every flow the frontend uses is implemented on the real backend: the patient
screening flow (`POST /assessments`, `POST /assessments/{id}/audio`,
`GET /assessments/{id}/results`), the clinician dashboard/login pages
(`GET /patients`, `GET /assessments`, `/auth/*`), and logout. Setting
`VITE_USE_MOCK_API=false` with a valid `VITE_API_BASE_URL` runs the whole app
— patient and clinician sides — against the real backend. See
`backend/README.md` for how to run or deploy it.

**Careful with `VITE_USE_MOCK_API`**: `src/services/index.js` treats any
value other than the literal string `"false"` as "use mock" — including an
unset variable. A deployed build (e.g. on Vercel) with this env var missing
or misspelled will silently serve mock data instead of erroring.

## Other scripts

- `npm run build` — production build
- `npm run lint` — oxlint
- `npm run test` — Vitest + React Testing Library (clinician login, assessment-submission processing)
- `npm run preview` — preview a production build locally
