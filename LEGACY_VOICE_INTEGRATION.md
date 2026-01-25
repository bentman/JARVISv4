# JARVISv4: Legacy Voice Integration & Porting Strategy

## 1. Executive Summary
JARVISv4 will carry forward the proven “local voice stack” from legacy JARVISv2 and JARVISv3: offline STT (whisper.cpp), offline TTS (Piper), and local wake word detection (openWakeWord). This port is executed in a way that preserves JARVISv4’s Explicit Cognition Framework (ECF): deterministic controller + artifact-driven state, with Redis used only as a cache (never as authoritative task state).

Key objective: restore end-to-end voice I/O as a reliable “ingress/egress channel” for the v4 backend (and, later, the frontend), without introducing new abstractions or refactors.

Primary reference implementations:
- JARVISv3: container-native voice runtime service logic and multi-stage binary builds (S6).
- JARVISv2: API-level voice endpoints + compose patterns for dev/prod posture and Redis caching (S5).

Custom wake word training is explicitly deferred as a stretch goal and should not block baseline voice enablement (S3).

---

## 2. Why Voice Fits Now (Holistic Placement in JARVISv4)
Voice work is correctly sequenced at this point because it unlocks the next “real user loop” while respecting what’s already proven in v4:

- The deterministic controller + artifact-driven lifecycle are already validated; voice becomes a disciplined input/output surface that feeds that controller, not a competing state machine.
- Docker + compose porting is a prerequisite for voice because STT/TTS rely on native binaries and runtime libraries; the container boundary is how we make this reproducible across dev and prod.
- Redis is already part of the environment shape in legacy, and in v4 it should remain a performance-oriented cache layer (e.g., short-lived session metadata, model download metadata, throttling), while tasks and outcomes remain artifacts on disk.

Voice is therefore a “platform capability bridge”:
frontend audio capture → backend voice endpoints/tools → deterministic controller tasks → artifact outputs → backend TTS playback payloads → frontend playback.

---

## 3. Reference Policy (Hard Boundary)
All legacy code lives under `./reference/` and is read-only. Porting means: identify the canonical legacy behavior, then implement it in v4 using v4 architecture and nomenclature.

- JARVISv2 source: `./reference/JARVISv2_ref`
- JARVISv3 source: `./reference/JARVISv3_ref`

---

## 4. Legacy Surface Map (What to Pull From Where)

### 4.1 Core service logic (backend)
Prefer v3 as the “service spine”:
- `./reference/JARVISv3_ref/backend/core/voice.py` (service orchestration; model provisioning; executable discovery; wake word integration) (S6)

Pull v2 as the “API semantics guide”:
- `./reference/JARVISv2_ref/backend/app/services/voice_service.py` (STT/TTS/wake fallbacks; executable discovery patterns) (S5)
- `./reference/JARVISv2_ref/backend/app/api/v1/endpoints/voice.py` (endpoint layout and request/response expectations)

### 4.2 Container build patterns (binaries + posture)
Prefer v3 as the “container-native build model”:
- `./reference/JARVISv3_ref/backend/Dockerfile.dev` (multi-stage builds for whisper.cpp + llama.cpp + piper; dev runtime deps and LD paths) (S6)
- `./reference/JARVISv3_ref/backend/Dockerfile` (prod runtime posture: non-root user, ownership, etc.) (S6)

Use v2 compose as the “posture split” exemplar (dev vs prod):
- `./reference/JARVISv2_ref/docker-compose.dev.yml` (relaxed dev; Redis no persistence; model volume RW) (S5)
- `./reference/JARVISv2_ref/docker-compose.yml` (hardened prod; read_only + tmpfs; Redis persistence; healthcheck) (S5)

---

## 4.3 Compatibility Targets (Legacy API Shape)
Because JARVISv2 and JARVISv3 expose different voice endpoints and payload formats, v4 must declare a compatibility target **per phase**.

Target A (v2 semantics):
- Base path: `/api/v1/voice/*` (router prefix in `reference/JARVISv2_ref/backend/app/api/v1/__init__.py`).
- STT: `POST /stt` with JSON `{ audio_data: base64 }`, returns `{ text, confidence }` (`speech_to_text` in `reference/JARVISv2_ref/backend/app/api/v1/endpoints/voice.py`).
- TTS: `POST /tts` with `text: str` parameter, returns `{ audio_data: base64 }` (`text_to_speech` in `reference/JARVISv2_ref/backend/app/api/v1/endpoints/voice.py`).
- Wake: `POST /wake-word` with JSON `{ audio_data: base64 }`.
- Session: `POST /session` with `{ audio_data, conversation_id?, mode, include_web, escalate_llm }`.

Target B (v3 semantics):
- Base path: `/api/v1/voice/*` (routes defined directly in `reference/JARVISv3_ref/backend/main.py`).
- STT: `POST /transcribe` with multipart upload (`UploadFile`).
- TTS: `POST /speak` with JSON `{ text }`, returns `audio/wav` bytes.
- Session: `POST /session` with JSON `{ audio_data: base64, ... }`, returns `VoiceSessionResponse` with base64 audio.

**Decision requirement:** v4 Phase C must explicitly choose Target A or Target B for its baseline. Dual-compatibility can be added later but must be called out explicitly in acceptance criteria.

## 5. v4 Target Architecture (Boundaries and Ownership)

### 5.1 Placement in v4
Create a dedicated core service module (mirrors v3 intent, aligns with v4’s “core services” concept):
- v4 target: `backend/core/voice/` (service logic and adapters)
  - `service.py` (or `voice_service.py`): orchestration entrypoint
  - `stt_whispercpp.py`: whisper.cpp subprocess adapter
  - `tts_piper.py`: piper subprocess adapter
  - `wake_openwakeword.py`: openWakeWord adapter
  - `schemas.py`: typed request/response models (only if v4 standardizes this elsewhere)

Expose voice to the system through the minimal surfaces needed (choose one, then add the other later if required):
- API-first surface: `backend/api/routers/voice.py` (FastAPI routes; request/response stable for frontend integration)
- Tool-first surface: v4 Tool Registry exposes `speech_to_text`, `text_to_speech`, `detect_wake_word` tools for agent/controller use

Recommendation: start API-first for frontend bridging, then register tool wrappers that call the same service functions (single implementation).

### 5.2 What voice must NOT own
- No task lifecycle state. Voice produces/consumes artifacts or messages, but never becomes authoritative.
- No “controller bypass.” Transcriptions that become actionable should enter the normal controller flow (create a task, plan, execute, archive).
- No long-lived state in Redis. Redis is cache only.

---

## 5.3 Legacy Fallback Behavior Matrix (Baseline Expectations)
| Capability | Legacy Behavior | Source | v4 Baseline Requirement |
| --- | --- | --- | --- |
| Wake word | Prefer openWakeWord; if unavailable, fallback to STT keyword spotting (`hello assistant`, `hey assistant`, `assistant`, `qwen`, `wake up`). Threshold is `>= 0.5` in legacy for model scores. | `reference/JARVISv2_ref/backend/app/services/voice_service.py` → `detect_wake_word()`; `reference/JARVISv3_ref/backend/core/voice.py` → `detect_wake_word()` | **Required**: openWakeWord baseline + threshold 0.5. **Optional**: STT keyword fallback (if dropped, document divergence). |
| TTS | Piper preferred; fallback to `espeak-ng`/`espeak` if Piper unavailable or fails. | `reference/JARVISv3_ref/backend/core/voice.py` → `_tts_fallback()` | **Required**: Piper. **Required**: espeak fallback to match legacy resiliency. |

Note: v3 installs `espeak-ng` in Dockerfiles (dev/prod), enabling this fallback path.

## 6. Infrastructure & Configuration Strategy (Dev vs Prod)

### 6.1 Dockerfiles (binaries, runtime deps, posture)
Adopt v3’s multi-stage builder pattern for reproducibility:
- whisper.cpp built in a dedicated stage and copied into runtime image (S6, S1)
- llama.cpp built similarly (S6, S2) (even if not strictly required for the first voice milestone; keep it aligned with the stack)
- piper built similarly (S6, S4)

Legacy binary mapping (explicit):
- `whisper.cpp` build artifact `whisper-cli` is copied to `/usr/local/bin/whisper` (v2/v3 Dockerfiles).
- `piper` build artifact is copied to `/usr/local/bin/piper` (v2/v3 Dockerfiles).
- LD paths are required because shared libraries are copied out of the build trees (see `LD_LIBRARY_PATH` in `reference/JARVISv3_ref/backend/Dockerfile(.dev)` and v2 Dockerfiles).

Decision point (must be explicit in implementation phase):
- Legacy v3 clones `rhasspy/piper`, but that upstream repo is now archived and points to a new development location (S4). Decide whether to:
  - pin to the archived source for continuity, or
  - switch to the new upstream (license and long-term maintenance implications).

### 6.2 docker-compose split (dev vs prod)
Maintain both:
- `docker-compose.dev.yml` + `backend/Dockerfile.dev` (relaxed)
- `docker-compose.yml` + `backend/Dockerfile` (hardened)

Minimum compose expectations carried forward:
- Backend service + Redis service as baseline (S5)
- Model persistence volume mounted at `/models` (S5, S6)
- Prod hardening:
  - backend `read_only: true`, `tmpfs: /tmp`, `security_opt: no-new-privileges:true` (S5)
  - backend healthcheck endpoint (S5)
- Dev relaxed:
  - bind-mount backend source for iteration and make `/models` writable (S5)
  - Redis dev mode can disable persistence for speed (S5)

Legacy compose alignment notes:
- v2 dev/prod compose mount `./models:/models` and set `REDIS_URL=redis://redis:6379/0` with backend → redis linkage (`reference/JARVISv2_ref/docker-compose(.dev).yml`).
- v3 dev/prod compose mount `./models:/models` and set `REDIS_URL=redis://redis:6379/0` with backend depending on redis (`reference/JARVISv3_ref/docker-compose(.dev).yml`).

### 6.3 Environment variables (baseline contract)
Standardize the minimal voice-related env contract:
- `MODEL_PATH=/models` (common root for weights, voices, wake models) (S5, S6)
- `REDIS_URL=redis://redis:6379/0` (cache) (S5)
- `LD_LIBRARY_PATH` includes copied whisper/llama/piper libs as needed (S6)

Legacy env deltas to resolve:
- v2 config defaults `MODEL_PATH=/models` and `REDIS_URL=redis://redis:6379/0` (`reference/JARVISv2_ref/backend/app/core/config.py`).
- v3 config defaults `MODEL_PATH=./models` and `REDIS_URL=redis://localhost:6379/0` (`reference/JARVISv3_ref/backend/core/config.py`), but compose injects `/models` + `redis://redis:6379/0`.

**Decision requirement:** v4 should follow container truth (compose-provided values) and document any host-only defaults if needed.

Container-truth recommendation:
- v4 should align with compose-injected values (`MODEL_PATH=/models`, `REDIS_URL=redis://redis:6379/0`) and treat config-file defaults as host-only fallbacks.

### 6.4 openWakeWord provisioning details (legacy behavior)
Provisioning in v3 ensures these base models under `MODEL_PATH/openwakeword/`:
- Expected directory: `/models/openwakeword/` (i.e., `${MODEL_PATH}/openwakeword/`).
- Expected ONNX files (preferred):
  - `alexa*.onnx`
  - `melspectrogram*.onnx`
  - `embedding_model*.onnx`
- Fallback: if no ONNX present, load `*.tflite` models.

Source: `reference/JARVISv3_ref/backend/core/voice.py` → `_provision_oww_models()` + `_init_wake_word()`.

---

## 7. Porting Roadmap (Objective-Scoped, System-Level)

### Phase A: Container + runtime prerequisites (no API yet)
Objective: backend image can build with required native binaries present; runtime can locate executables.
- Port v3 multi-stage build pattern into v4 `backend/Dockerfile.dev` and `backend/Dockerfile` (S6).
- Ensure runtime paths match what service code expects (e.g., `/usr/local/bin/whisper`, `/usr/local/bin/piper`) (S6).
- Create a `/models` persistence story for both dev and prod compose (S5).

Done when:
- A reproducible build succeeds in both dev and prod variants.
- A minimal “binary presence check” in v4 can run inside the container (no functional STT/TTS yet):
  - `whisper --help` and `piper --help` succeed (binary presence + executable permissions).
  - Required runtime deps installed (`libsndfile1`, `espeak-ng`, `espeak-ng-data`, `libgomp1`) as seen in v3 Dockerfiles (`reference/JARVISv3_ref/backend/Dockerfile(.dev)`) and v2 prod Dockerfile (`reference/JARVISv2_ref/backend/Dockerfile`).

### Phase B: Core voice service (service logic only)
Objective: v4 has a single voice service implementation callable from tests.
- Implement v4 `backend/core/voice/` by adapting:
  - v3’s service orchestration and openWakeWord provisioning logic (S6)
  - v2’s fallback patterns for STT/TTS executable discovery and voice selection (S5)
- Keep wake word as “optional dependency”: if openWakeWord isn’t installed, degrade gracefully.

Model provisioning stance (explicit baseline):
- **v4 baseline = v3-style model-manager downloads into `/models`.**
- v3 uses `model_manager.download_recommended_model("stt"|"tts")` to fetch weights (`reference/JARVISv3_ref/backend/core/voice.py`).
- v2 expects weights pre-provisioned under `MODEL_PATH` and raises if not found (`_find_whisper_weights()` in `reference/JARVISv2_ref/backend/app/services/voice_service.py`).

Implication: Phase B acceptance should require successful model-manager resolution for STT/TTS tiers (even if binaries are present).

Done when:
- Unit/integration tests can call v4 voice service methods without requiring the frontend.

### Phase C: API surface for frontend bridging
Objective: stable HTTP API for the frontend to call.
- Implement `backend/api/routers/voice.py` (or equivalent v4 API routing location).
- Minimum endpoints:
  - STT endpoint: accept audio payload → return transcript + confidence/metadata
  - TTS endpoint: accept text → return audio payload (or a file reference in artifacts/media)
  - (Optional) wake endpoint: accept audio chunk → return detected/not detected

Session endpoint policy (not baseline):
- `/api/v1/voice/session` is **not** part of Phase C baseline. It is bound to Phase D (voice → task lifecycle wiring).
- Legacy anchors: v2 `voice_session()` in `reference/JARVISv2_ref/backend/app/api/v1/endpoints/voice.py`; v3 `voice_session()` in `reference/JARVISv3_ref/backend/main.py`.

Done when:
- Target A (v2 semantics) acceptance (baseline primitives):
  - `POST /api/v1/voice/stt`
    - Request: `application/json` `{ "audio_data": "<base64 wav>" }`
    - Response: `application/json` `{ "text": "...", "confidence": 0.0 }`
    - Legacy: `reference/JARVISv2_ref/backend/app/api/v1/endpoints/voice.py` → `speech_to_text()`.
  - `POST /api/v1/voice/tts`
    - Request: `application/json` `{ "text": "..." }` (v4 normalization of v2 `text: str` signature).
    - Response: `application/json` `{ "audio_data": "<base64 wav>" }`
    - Legacy: `reference/JARVISv2_ref/backend/app/api/v1/endpoints/voice.py` → `text_to_speech()`.
  - `POST /api/v1/voice/wake-word`
    - Request: `application/json` `{ "audio_data": "<base64 wav>" }`
    - Response: `application/json` `{ "detected": true|false }`
    - Legacy: `reference/JARVISv2_ref/backend/app/api/v1/endpoints/voice.py` → `detect_wake_word()`.
  - Non-baseline (v2-only): `POST /api/v1/voice/upload-audio` multipart upload (`UploadFile`).

- Target B (v3 semantics) acceptance (baseline primitives):
  - `POST /api/v1/voice/transcribe`
    - Request: `multipart/form-data` file upload (`UploadFile = File(...)`).
    - Response: `application/json` `{ "text": "...", "confidence": 0.0 }`.
    - Legacy: `reference/JARVISv3_ref/backend/main.py` → `transcribe_audio()`.
  - `POST /api/v1/voice/speak`
    - Request: `application/json` `{ "text": "..." }`.
    - Response: `audio/wav` raw bytes.
    - Legacy: `reference/JARVISv3_ref/backend/main.py` → `text_to_speech()`.

In all cases: a lightweight request-based integration test can exercise STT/TTS paths (can be skipped/marked if binaries absent in local non-container test runs, but must be runnable in container harness).

### Phase D: Controller/Agent wiring (voice → task lifecycle)
Objective: transcribed text can become a normal v4 task without bypassing lifecycle.
- Create an explicit “voice ingress” path:
  - transcript → create task artifact → normal plan/execute/archive
- TTS egress path:
  - completed task text output → TTS → deliver audio back to caller (frontend) or store as artifact.

Done when:
- A system-level test proves “audio transcript → archived task + output → optional TTS artifact” with no dangling ACTIVE tasks.

### Phase E (Stretch): Custom wake word model
Objective: enable “Hey Jarvis” (or equivalent) without blocking baseline voice.
- Use openWakeWord’s documented training path (utility/Colab) to generate a model file (S3).
- Persist the custom model under `/models/openwakeword/` and load it via v4 configuration.
- Keep “alexa/hey alexa” as the baseline supported model until custom model quality is proven.

Done when:
- Custom model is demonstrably reliable in a controlled test, and remains optional.

---

## 8. Validation Strategy (Evidence-Gated)
Validation must compound (system-level) and respect v4’s evidence discipline.

Recommended validation ladder:
1) Build validation: container builds for dev/prod Dockerfiles.
2) Service validation: minimal tests for voice service functions (non-API).
3) API validation: request-level tests for STT/TTS endpoints in container harness.
4) End-to-end validation: transcript → task lifecycle → archived outcome → optional TTS artifact.

Key constraints:
- Tests should not mirror implementation details (avoid micro-proofs).
- Skip conditions must be explicit (e.g., if binaries absent outside container).
- Redis is validated as cache only (no task authority stored there).

---

## 9. Notes on Legacy Differences (What to Keep / What to Drop)

Keep:
- v3 approach of provisioning openWakeWord base models into persisted storage and loading from `/models` (S6).
- v3 builder-based compilation for native binaries (S6).
- v2 dev/prod compose posture split, especially read-only + tmpfs in prod (S5).

Drop/defer:
- Any runtime “auto-install” behaviors (v2 attempts to clone/build whisper at runtime via `_install_whisper()` in `voice_service.py`) should not be carried into v4; v4 should rely on container build and explicit provisioning (S5, S6).
- Emotion detection (present in v3 voice service) is out-of-scope until baseline STT/TTS/wake are stable (S6).

---

## 9.1 Redis Cache Clarification (Voice Scope)
Redis is cache-only. Voice features **MUST ONLY** use Redis for ephemeral or derived data that can be safely recomputed:
- Allowed: short-lived session metadata, throttling counters, model download metadata.
- MUST NOT store: authoritative transcript history, task lifecycle state, or persisted conversation state.

Source posture: v2/v3 compose files configure Redis as a cache-like service (`reference/JARVISv2_ref/docker-compose.yml`, `reference/JARVISv3_ref/docker-compose.yml`).

## 10. Appendix: Porting Matrix (Legacy → v4)

| Capability | Legacy Source (Ref) | v4 Target | Notes |
| --- | --- | --- | --- |
| STT (offline) | `reference/JARVISv3_ref/backend/core/voice.py` (S6) + `reference/JARVISv2_ref/backend/app/services/voice_service.py` (S5) | `backend/core/voice/stt_whispercpp.py` | Use whisper.cpp binary; keep discovery paths aligned with Docker copy locations. |
| TTS (offline) | `reference/JARVISv2_ref/backend/app/services/voice_service.py` (S5) | `backend/core/voice/tts_piper.py` | Piper voice selection logic can start simple; add quality/voice catalog later. |
| Wake word | `reference/JARVISv3_ref/backend/core/voice.py` (S6) | `backend/core/voice/wake_openwakeword.py` | Keep baseline models and thresholds; custom model is stretch. |
| Container build | `reference/JARVISv3_ref/backend/Dockerfile.dev` + `Dockerfile` (S6) | v4 `backend/Dockerfile.dev` + `backend/Dockerfile` | Multi-stage builds, copy binaries, keep prod non-root posture. |
| Compose posture | `reference/JARVISv2_ref/docker-compose.dev.yml` + `docker-compose.yml` (S5) | v4 `docker-compose.dev.yml` + `docker-compose.yml` | Redis + backend baseline; dev relaxed vs prod hardened. |
| Redis caching | `reference/JARVISv2_ref/docker-compose.yml` (S5) | v4 Redis service + cache client | Cache-only: never authoritative task state. |

---
