# QSense Model Reference

Source of truth: `qsense models --detail` (reads from registry.yaml at runtime).
If this file is outdated, run the command and update accordingly.

## Capabilities

| Model | Vision | Audio | Video | Context |
|-------|--------|-------|-------|---------|
| google/gemini-3-flash-preview | yes | yes | native | 1M |
| google/gemini-3.1-pro-preview | yes | yes | native | 1M |
| gemma-4-31B-it | yes | - | extract | 256K |
| anthropic/claude-opus-4-6 | yes | - | - | 1M |
| anthropic/claude-sonnet-4-6 | yes | - | - | 1M |
| gpt-5.4 | yes | - | - | - |
| grok-4.20-beta | yes | - | - | 256K |
| Kimi-K2.5 | yes | - | native* | 256K |

## Selection Guide

| Need | Choose | Why |
|------|--------|-----|
| Audio input | `google/gemini-3-flash-preview` | This exact registry model supports audio |
| Native video | `google/gemini-3-flash-preview` or `Kimi-K2.5` | These exact registry models support native video |
| Deep reasoning on images | `google/gemini-3.1-pro-preview` | Strongest reasoning, 1M context |
| Fast image tasks | `google/gemini-3-flash-preview` | Fastest general-purpose registry default |

## Request Shaping

- Before naming any model, run `qsense models` and copy the exact ID from output.
- Never shorten model IDs, never replace them with memory-based aliases, and never guess a nearby family/version.
- If an ID is not listed by `qsense models`, treat it as unavailable.
- Prefer `--target` for the main artifact and `--reference` for comparison assets instead of stacking everything under `--image`.
- Use `--spec` for review criteria and `--context` for supporting material.
- Use `--vision-fidelity max` for OCR, dense UI screenshots, charts, or subtle visual regressions.
- Use `--output json --schema ...` when the caller needs machine-readable findings.

## Limits Quick Reference

### Gemini 3 Flash / 3.1 Pro
- Image: max 7MB, up to 3000/request, formats: jpeg png webp heic heif
- Audio: max ~8.4h, formats: mp3 wav flac ogg aac m4a webm
- Video: max 45min (with audio), formats: mp4 mpeg mov avi webm wmv 3gpp

### Claude Opus 4.6 / Sonnet 4.6
- Image: max 5MB, max 8000x8000 (>20 images: 2000x2000), up to 600/request, formats: jpeg png gif webp
- No audio, no video

### Grok 4.20 Beta
- Image: max 20MB, up to 10/request, formats: jpeg png
- No audio, no video

### GPT-5.4
- Image: formats: jpeg png webp gif. Stream-only mode.
- No audio, no video

### Kimi K2.5
- Image: max 100MB (request body limit), max 4K resolution, formats: jpeg png webp gif
- Video: experimental native support, formats: mp4 mpeg mov avi webm wmv 3gpp
- No audio

## Video Strategy

```
Model supports native video? (check capabilities table above)
  YES  --> direct: qsense --prompt "..." --video clip.mp4
  NO   --> extract: qsense --prompt "..." --video clip.mp4 --video-extract
```

- Direct mode preserves temporal info + audio track -- always prefer when available.
- Video > 20MB: split with `ffmpeg -segment_time 60 -f segment` first, then process segments.
- `--fps` and `--max-frames` control extraction density. Low fps (0.5) for slow-paced, higher (2-3) for action.

## Audio Notes

- Only Gemini models accept audio. Don't send `--audio` to Claude/GPT/Grok.
- Remote audio is downloaded to memory (limit 20MB). For large files, download and trim first.
- To analyze audio from a video separately: `ffmpeg -i video.mp4 -vn audio.mp3`, then `--audio audio.mp3`.

## User Model Preferences

<!-- Which models this user prefers and why, models their proxy doesn't support, etc. -->
