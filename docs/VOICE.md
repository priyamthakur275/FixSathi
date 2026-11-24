# Spoken replies

## When FixSaathi speaks

| Technician action | Text reply | Spoken automatically |
|---|---|---|
| Types a message (or a follow-up) | yes | **never** |
| Presses Read aloud on a reply | yes | that reply only, on request |
| Speaks (mic → Done) with the speaker on | yes | yes |
| Speaks with the speaker off | yes | no |

Each message carries its channel (`text` or `voice`, sent by the composer and stored in `conversations.meta.channel` for the
technician's message and the reply). `ChatPage` reads a reply aloud by itself only when `channel == 'voice'` and the speaker is
on; history is never spoken. Answering a message never generates audio on the server: audio is made only when the app asks
for it. Turning the speaker off stops playback at once (`PrefsContext.setSpeaker`), and every new playback stops the previous one.

## Voices

0. **Personal voice (default when configured):** the technician's own ElevenLabs voice clone
   (`ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, model `ELEVENLABS_MODEL=eleven_multilingual_v2`, optional
   `ELEVENLABS_MODEL_KANNADA`). MP3 (`mp3_44100_128`). Same rules as below: only stored, safety-screened replies, cached per
   message. If ElevenLabs fails (key without the Text to Speech permission, out of credits, network), the server answers with
   the Gemini voice, and if that fails too the app reads the reply with the device voice. Account errors pause ElevenLabs for
   10 minutes so every reply does not fail again. The key is never logged or sent to the browser.
1. **Natural voice:** Gemini text-to-speech, `GEMINI_TTS_MODEL=gemini-2.5-flash-preview-tts`, prebuilt voice
   `GEMINI_TTS_VOICE=Charon` (technicians can choose Kore, Iapetus, Orus, Alnilam or Sadaltager in Settings). The model's
   `speech_config` exists only on the v1beta API, so `GeminiClient.raw_beta` is used for it; on v1 every request failed with
   `Unknown name "speechConfig"`, which is why spoken replies had fallen back to the browser voice. Delivery is steered by the
   natural-language direction `TTS_STYLE` (confident expert, clear and crisp, natural brisk pace, emphasis on key actions,
   short pauses between steps); the direction is not spoken.
   The server speaks only the stored, safety-screened reply (`services/voice.spoken_text`): withheld power steps stay withheld
   and the written lock note becomes the spoken one. Audio is cached per message and voice.
2. **Device voice (fallback):** the browser's speech synthesis, used when the natural voice is not configured, its quota is
   used up (the app then skips it for 10 minutes), the network fails, or the technician chooses "Device voice only".

## Measured samples (21 Nov, same 66-word repair instruction)

| Voice | Pitch variation (sd, semitones) | Pitch range (st) | Pace (wpm) | Avg pause |
|---|---|---|---|---|
| macOS Rishi (en-IN, device voice) | 1.91 | 6.3 | 173 | 228 ms |
| macOS Samantha (device voice) | 2.87 | 10.8 | 197 | 235 ms |
| Gemini Charon | 6.54 | 22.7 | 176 | 434 ms |
| Gemini Iapetus | 5.62 | 18.2 | 187 | 368 ms |
| Gemini Kore | 5.47 | 19.4 | 191 | 304 ms |
| Gemini Orus | 4.75 | 15.1 | 184 | 367 ms |

Generation takes about 12–14 s for a 20 s reply; the model returns the audio in one piece (streaming gave no earlier audio),
so the app shows "Preparing voice…" meanwhile.

## Limits

- Free-tier keys: **10 TTS requests per day** for this model (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`). After
  that the device voice is used until the quota resets. Attach billing to the key's project for regular use.
- Safari may block playback that starts long after the last tap; the app then reads the reply with the device voice.
