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
  imageAlt:
    "An illustrated kitchen scene: a child reaches for a jar on a high shelf while standing on a wobbling stool, a woman dries a dish nearby without noticing, and water overflows from a sink onto the floor.",
  expectedConcepts: [
    "kitchen",
    "child",
    "stool",
    "reaching",
    "jar",
    "shelf",
    "woman",
    "sink",
    "overflowing water",
    "falling",
  ],
  estimatedMinutes: "5–8 minutes",
};

export const supportedLanguages = [
  { code: "en", label: "English", native: "English" },
  { code: "hi", label: "Hindi", native: "हिन्दी" },
  { code: "mr", label: "Marathi", native: "मराठी" },
  { code: "ta", label: "Tamil", native: "தமிழ்" },
  { code: "bn", label: "Bengali", native: "বাংলা" },
  { code: "te", label: "Telugu", native: "తెలుగు" },
  { code: "ur", label: "Urdu", native: "اُردُو" },
  { code: "kn", label: "Kannada", native: "ಕನ್ನಡ" },
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
