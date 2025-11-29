# Intelligence Module Roadmap (Student 2)

- [x] **Environment:**
    - [x] Install libraries: `google-generativeai`, `elevenlabs`, `pygame`, `python-dotenv`, `pytest`.

## Phase 2: The Philosopher's Brain
- [x] **Gemini Configuration:**
    - [x] Get API key from Google AI Studio (Gemini API).
    - [x] Set up the model (e.g., `gemini-2.0-flash` or `1.5-flash`).
    - [x] Implement "System Instruction" (Marcus Aurelius Prompt).
- [x] **Text Tests:**
    - [x] Verify in the console that the duck responds stoically and briefly.

## Phase 3: The Philosopher's Voice
- [ ] **ElevenLabs Integration:**
    - [ ] Get API key from ElevenLabs (Free Tier).
    - [ ] Select a voice (e.g., "Marcus" or another Deep Narrative voice).
    - [ ] Write a function to convert text from Gemini into an `.mp3` file.
- [ ] **Audio Player:**
    - [ ] Implement `.mp3` playback using `pygame` (without blocking the program).

## Phase 4: Optimization & Integration
- [ ] **Optimize API request**
- [ ] **Threading:**
    - [ ] Move the generation and speech process to a separate thread (so the UI doesn't freeze) - check that.
- [ ] **Cooldown:**
    - [ ] Add a timer (e.g., 3 minutes) to prevent the duck from speaking too often.
- [ ] **Refactoring:**
    - [ ] Expose a single clean function `trigger_intervention()` for Student 1 and 3 to use.
