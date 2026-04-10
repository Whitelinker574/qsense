# QSense -- Agent Context

## What This Is

QSense is a **multimodal perception atomic skill** -- the smallest useful unit for "let a model see/hear something." It takes image/audio/video input, sends it to an LLM via OpenAI-compatible API, returns text.

It is NOT an application or framework. It is a primitive that higher-level skills compose. Video splitting, audio segmentation, batch processing, result parsing -- all belong to the caller, not qsense.

Package: `qsense-cli`. Binary: `qsense`. Docs: `docs/`.

## Quick Use (for agents)

```bash
# Setup (once)
pipx install qsense-cli
qsense init --api-key sk-xxx

# Image
qsense --prompt "describe" --image photo.png

# Audio (Gemini only)
qsense --prompt "transcribe" --audio recording.wav

# Video
qsense --prompt "summarize" --video clip.mp4

# Video (no native support) → frame extraction
qsense --prompt "describe" --video clip.mp4 --video-extract

# Choose model
qsense --model anthropic/claude-opus-4-6 --prompt "analyze" --image photo.png
```

Output: plain text to stdout. Errors: `[qsense] ...` to stderr, exit 1.

## Code Layout

```
src/qsense/
  _util.py          abort() -> NoReturn
  config.py         Three-tier config: CLI > env > ~/.qsense/.env (chmod 600)
  image.py          prepare_image(s)() -- Pillow resize + base64. Remote URLs pass through.
  audio.py          prepare_audio(s)() -- streaming download + base64 input_audio.
  video.py          encode_video_direct() -- download + base64 (or URL passthrough).
                    extract_frames_and_audio() -- ffmpeg frames + audio.
  client.py         chat() -- OpenAI SDK, auto stream fallback, error sanitization.
  models.py         Registry loader from registry.yaml. Graceful fallback on errors.
  registry.yaml     Model capabilities, limits, and behavior flags.
  cli.py            Click group: inference + init + config + models subcommands.
```

## Key Design Decisions

- **OpenAI SDK only**: No provider-specific SDKs. All models via `base_url`.
- **Image URLs pass through**: API fetches them. Local files → Pillow resize → base64 data URL.
- **Audio always base64**: No `audio_url` type in OpenAI API. Remote audio downloaded via streaming httpx.
- **Video default downloads**: Remote URLs downloaded + base64 encoded (proxy passthrough unreliable). `--video-passthrough` or registry `video_url_passthrough: true` for passthrough.
- **Stream auto-detection**: Registry `stream_only` → stream. Otherwise non-stream first, fallback to stream on error.
- **Security**: Config chmod 600, .env injection prevention, API error sanitization.

## Registry (registry.yaml)

```yaml
- id: google/gemini-3-flash-preview
  name: Gemini 3 Flash
  vision: true
  audio: true
  video: true
  native_video: true
  stream_only: false              # forces stream=True in API call
  video_url_passthrough: false    # true = pass remote URL directly to API
  context_tokens: 1048576
  max_image_size_mb: 7
  max_audio_duration_min: 504
  max_video_duration_min: 45
  image_formats: [jpeg, png, webp]
  audio_formats: [mp3, wav, flac]
  video_formats: [mp4, mov, webm]
  description: ...
```

**Behavior flags that affect code logic:**
- `stream_only` → `client.py` uses `stream=True` directly
- `video_url_passthrough` → `video.py` skips download, passes URL to API

Add new models: edit `registry.yaml` only. No code changes.

## Config

`~/.qsense/.env` (chmod 600):
```
QSENSE_API_KEY=sk-xxx
QSENSE_BASE_URL=https://api.openai.com/v1
QSENSE_MODEL=google/gemini-3-flash-preview
```

Env vars override file. CLI flags override both.

## Model Selection Guide

| Need | Model |
|------|-------|
| Audio understanding | `google/gemini-3-flash-preview` (only Gemini supports audio) |
| Native video | `google/gemini-3-flash-preview` or `Kimi-K2.5` |
| Deep reasoning + image | `anthropic/claude-opus-4-6` |
| Fast image | `google/gemini-3-flash-preview` (default) |
| Stream-only proxy | `gpt-5.4` |

## Full Documentation

- `docs/usage.md` -- Complete usage guide (Chinese)
- `docs/development.md` -- Developer guide, registry reference, adding models/modalities
- `docs/design-rationale.md` -- Design decisions, development history, agent skill integration
