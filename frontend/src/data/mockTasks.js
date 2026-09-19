// Task definitions. Frontend-only demo content — the actual clinical
// stimulus set is owned by the research team and would be swapped in via
// the backend contract.

export const pictureDescriptionTask = {
  id: "picture-01",
  name: "Picture Description",
  instructions: [
    "You will see a picture.",
    "Please describe what you see in your own words.",
    "Take your time. There is no need to rush.",
  ],
  prompt: "Describe what you see in this picture.",
  // Original, non-photographic composed scene — deliberately neutral and
  // culturally generic, avoiding any specific copyrighted clinical stimulus.
  // Structural complexity (multiple characters, two independent mishaps,
  // foreground/background depth) is deliberately matched to standardized
  // picture-description stimuli used in speech-based cognitive research, so
  // elicited speech length/complexity stays comparable to the training data
  // without reusing any copyrighted content.
  imageAlt:
    "An illustrated kitchen scene: a boy on a tilting three-legged stool reaches into a cookie jar on a high shelf while a girl below reaches up toward him, a woman dries a dish nearby without noticing water overflowing from a sink, a cat reacts to the spreading puddle, and a tree is visible through a window in the background.",
  expectedConcepts: [
    "kitchen",
    "boy",
    "girl",
    "stool",
    "tilting",
    "reaching",
    "cookie jar",
    "shelf",
    "woman",
    "drying dish",
    "sink",
    "overflowing water",
    "cat",
    "window",
    "tree",
    "falling",
  ],
  estimatedMinutes: "5–8 minutes",
};

export const supportedLanguages = [
  { code: "en", label: "English" },
  { code: "hi", label: "Hindi" },
  { code: "mr", label: "Marathi" },
  { code: "ta", label: "Tamil" },
  { code: "bn", label: "Bengali" },
  { code: "te", label: "Telugu" },
  { code: "ur", label: "Urdu" },
  { code: "kn", label: "Kannada" },
];

// Optional cognitive activities — extensions, not the core screening model.
// No leaderboards, no competitive scoring, no diagnostic framing.
export const cognitiveActivities = [
  {
    id: "activity-memory-match",
    name: "Memory Matching",
    description: "Find matching pairs of everyday objects.",
    estimatedMinutes: "3–5 minutes",
    icon: "Grid3x3",
  },
  {
    id: "activity-object-recall",
    name: "Object Recall",
    description: "Look at a short list of objects, then recall as many as you can.",
    estimatedMinutes: "2–4 minutes",
    icon: "ListChecks",
  },
  {
    id: "activity-pattern-recognition",
    name: "Pattern Recognition",
    description: "Continue a simple visual pattern.",
    estimatedMinutes: "2–3 minutes",
    icon: "Shapes",
  },
];
