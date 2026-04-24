---
name: qsense
description: "Multimodal perception CLI: send images, audio, or video to an LLM and get text back. Use for image recognition, screenshot analysis, OCR, photo description, audio transcription, video summarization, and any task where a model needs to see or hear something. Also use when comparing images, analyzing UI screenshots for errors, or extracting information from visual or audio content."
compatibility: "Requires qsense-cli (pipx install qsense-cli). Optional: ffmpeg for video frame extraction."
---

# QSense -- Multimodal Perception

One command: files in, text or JSON out. QSense is the atomic unit for "let a model see/hear something."

This skill is split into three files:
- **SKILL.md** (this file) -- command syntax, output contract, error reference. Stable facts.
- **references/models.md** -- model capabilities, limits, video/audio strategy. Syncs with `qsense models --detail`.
- **references/user-notes.md** -- user preferences, learned patterns, workflows. You maintain this over time.

## Setup

Check prerequisites, then install:

```bash
python3 --version               # need Python >= 3.10; if missing, ask user to install
pipx --version                  # if missing: brew install pipx (macOS) / apt install pipx (Linux)
pipx install qsense-cli         # global install, no activation needed
qsense init                     # stderr will tell you what's needed -- ask the user accordingly
```

## Quick Reference

```bash
# Image
qsense --prompt "describe this" --image photo.png
qsense --prompt "OCR" --image https://example.com/doc.jpg
qsense --prompt "review target against reference" --target page.png --reference ref.png --spec review.md

# Audio
qsense --prompt "transcribe" --audio recording.wav

# Video -- direct (models with native video support)
qsense --prompt "summarize" --video clip.mp4

# Video -- frame extraction (models without native video)
qsense --prompt "describe" --video clip.mp4 --video-extract --fps 1

# Multi-input
qsense --prompt "compare" --image a.png --image b.png
qsense --prompt "match?" --image frame.png --audio narration.wav
qsense --prompt "extract findings" --target screenshot.png --schema review.schema.json --output json
qsense --prompt "read small chart labels" --target chart.png --vision-fidelity max

# Specify model
qsense --model google/gemini-3-flash-preview --prompt "analyze" --image x.png

# List available models
qsense models --detail
```

## Usage Principles

### Model, Video, Audio

See `references/models.md` for capabilities, limits, video/audio strategy, and user preferences.

Before naming any model:
- run `qsense models`
- only use exact model IDs listed there
- never infer, shorten, or substitute model names
- if a model is not listed, treat it as unavailable

### Cost, Composability, Patterns

See `references/user-notes.md` for cost tips, learned patterns, and workflow templates.
QSense does ONE request per invocation -- batch/pipeline logic belongs to the caller.

### Security

- Never read or log `~/.qsense/.env` -- it contains the API key.
- Don't pass API keys via `--prompt` or stdout.

## Output Contract

- **stdout**: text by default, or JSON envelope with `model`, `output_format`, `text`, `warnings`, `meta`, and optional `data`
- **stderr**: `[qsense] ...` errors and warnings
- **exit 0**: success | **exit 1**: failure

Role-aware review options:
- `--target`: main artifact under review, at most one
- `--reference`: comparison inputs, previous versions, style refs
- `--context`: supporting context only
- `--spec`: requirements / rubric text or media

Structured-output options:
- `--output json`: print the response envelope instead of raw text
- `--schema path.json`: validate model text as JSON and populate `data`
- `--system`: optional system prompt override

Vision controls:
- `--vision-fidelity low|standard|max`
- use `max` for OCR, dense charts, or subtle diffs

## Error Quick Reference

| stderr contains | Cause | Fix |
|----------------|-------|-----|
| `Missing API key` | Not configured | `qsense init` or set `QSENSE_API_KEY` |
| `model not found` | Wrong model id | `qsense models` to list available |
| `too large` | File exceeds limit | `--max-size` for images, split video |
| `ffmpeg is required` | Extract mode needs ffmpeg | `brew install ffmpeg` / `apt install ffmpeg` |
| `HTTP 401` | Invalid API key | `qsense config --api-key <new-key>` |

## Model Capabilities

See `references/models.md` for the full table, per-model limits, and selection guide.
Or run `qsense models --detail` for live data from registry.

Do not guess model names from memory. Use the exact registry ID or do not mention the model.

## Continuous Improvement

Read `references/user-notes.md` before using qsense.
It records this user's preferences, lessons learned, and effective patterns.
Update it when you notice something worth remembering -- common triggers are listed inside that file, but use your own judgment too.
Keep entries short and useful.

## Boundaries

QSense does not do batching, rerun loops, workflow orchestration, or domain-specific review logic. Keep those in the caller.
