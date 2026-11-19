// Central configuration, all overridable with environment variables.
export const config = {
  port: Number(process.env.PORT || 8080),
  apiKey: process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY || '',
  // Vertex AI mode (production on Google Cloud): set GOOGLE_GENAI_USE_VERTEXAI=true + GOOGLE_CLOUD_PROJECT.
  useVertex: process.env.GOOGLE_GENAI_USE_VERTEXAI === 'true',
  project: process.env.GOOGLE_CLOUD_PROJECT || '',
  location: process.env.GOOGLE_CLOUD_LOCATION || 'us-central1',
  // Live models are tried in order until one connects.
  liveModels: (process.env.GEMINI_LIVE_MODEL || 'gemini-3.8-live,gemini-3.1-flash-live-preview,gemini-2.5-flash-native-audio-preview-12-2025')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean),
  agentModel: process.env.GEMINI_AGENT_MODEL || 'gemini-3.6-flash',
  imageModel: process.env.NANO_BANANA_MODEL || 'gemini-3.1-flash-image', // Nano Banana 2
  voice: process.env.GEMINI_VOICE || 'Puck',
  // Storage: "firestore" on Google Cloud, otherwise a local JSON file.
  store: process.env.STORE || (process.env.GOOGLE_CLOUD_PROJECT ? 'firestore' : 'file'),
  dataFile: process.env.DATA_FILE || './data/jobs.json',
  // Optional shared access code so a public URL does not burn your API key.
  accessCode: process.env.ACCESS_CODE || '',
};
