import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

/**
 * Where GSAP is allowed in this app (clinical-safety + operational-UX rules,
 * not just taste -- see the "premium visual pass" plan for the full rationale):
 *
 *   ALLOWED   - simple, non-pinned fade/translate/scale/stagger reveals on
 *               pages/public/Landing.jsx and clinical detail pages
 *               (PatientProfile, AssessmentDetail) for panel entrance.
 *   FORBIDDEN - ScrollTrigger `pin: true`, horizontal scroll-hijack, or any
 *               scrub-linked scene, anywhere in the app, no exceptions.
 *   FORBIDDEN ENTIRELY - any GSAP usage at all inside pages/patient/Recording.jsx,
 *               Processing.jsx, or Task.jsx. That's a timed cognitive-assessment
 *               flow for memory-impaired patients; use Framer Motion entrance/
 *               hover only there (src/components/motion/).
 *   FORBIDDEN - restructuring AssessmentsTable/PatientsTable/Dashboard's summary
 *               grid into bento/asymmetric layouts. Reveal motion only, never
 *               layout motion, on operational data tables.
 *
 * Every component using GSAP must scope its tweens with gsap.context() and
 * call ctx.revert() in its effect cleanup, and gate scroll-triggered tweens
 * behind gsap.matchMedia()'s "(prefers-reduced-motion: no-preference)" query --
 * this SPA's client-side route changes will leak ScrollTrigger instances
 * otherwise, and the existing CSS-level reduced-motion override does not
 * catch GSAP's JS-driven tweens.
 */

export { gsap, ScrollTrigger };
