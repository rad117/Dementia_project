import { pictureDescriptionTask } from "./mockTasks.js";
import { seededFromString, clamp } from "../utils/random.js";

// One demo sentence per expected concept, in the same order as
// pictureDescriptionTask.expectedConcepts.
const CONCEPT_SENTENCES = [
  "I can see a kitchen with everyday things around.",
  "There is a child in the picture.",
  "The child is standing on a stool.",
  "The child is reaching up toward something.",
  "It looks like the child wants the jar.",
  "The jar is sitting on a high shelf.",
  "A woman is standing nearby.",
  "She is close to the sink.",
  "Water is overflowing from the sink onto the floor.",
  "It looks like something is about to fall.",
];

const FILLER_WORDS = ["um", "uh", "hmm"];

// Deterministic demo transcript built from the structured feature counts —
// this is placeholder text for UI/UX purposes, not a real ASR transcript.
export function generateTranscript(assessment, features) {
  const rng = seededFromString(assessment.id + "-transcript");
  const conceptsIdentified = clamp(features.semantic.conceptsIdentified, 0, CONCEPT_SENTENCES.length);
  const fillerCount = clamp(features.linguistic.fillers, 0, 10);
  const repetitionCount = clamp(features.linguistic.repetitions, 0, 5);
  const revisionCount = clamp(features.linguistic.revisions, 0, 3);

  const segments = [];
  let cursor = 0;
  const wordsPerSecond = features.speech.speechRateWpm / 60;

  const pushSegment = (text, type, meta = {}) => {
    const words = text.split(" ").length;
    const durationSec = Math.max(0.6, words / wordsPerSecond);
    const startSec = cursor;
    const endSec = cursor + durationSec;
    cursor = endSec + (type === "filler" ? 0.2 : 0.35);
    segments.push({
      id: `${assessment.id}-seg-${segments.length}`,
      startSec: Number(startSec.toFixed(1)),
      endSec: Number(endSec.toFixed(1)),
      text,
      type,
      ...meta,
    });
  };

  for (let i = 0; i < conceptsIdentified; i++) {
    if (fillerCount > 0 && i % 2 === 0 && segments.filter((s) => s.type === "filler").length < fillerCount) {
      pushSegment(FILLER_WORDS[Math.floor(rng() * FILLER_WORDS.length)], "filler");
    }
    pushSegment(CONCEPT_SENTENCES[i], "concept", {
      concept: pictureDescriptionTask.expectedConcepts[i],
    });

    if (repetitionCount > 0 && segments.filter((s) => s.type === "repetition").length < repetitionCount) {
      const firstWords = CONCEPT_SENTENCES[i].split(" ").slice(0, 3).join(" ");
      pushSegment(`${firstWords}... ${firstWords}`, "repetition");
    }
    if (revisionCount > 0 && i % 3 === 1 && segments.filter((s) => s.type === "revision").length < revisionCount) {
      pushSegment("the jar — I mean, the cookie jar on the shelf", "revision");
    }
  }

  if (segments.length === 0) {
    pushSegment("The recording did not contain enough identifiable speech for a transcript.", "normal");
  }

  return {
    assessmentId: assessment.id,
    language: assessment.language,
    generatedNote: "Demo transcript text generated for illustration — not real ASR output.",
    segments,
  };
}
