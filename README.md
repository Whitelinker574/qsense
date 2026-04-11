<p align="center">
  <h1 align="center">QSense</h1>
  <p align="center">
    <strong>Multimodal Perception Atomic Skill</strong>
  </p>
  <p align="center">
    <a href="#quick-start">Quick Start</a> ·
    <a href="#usage-examples">Examples</a> ·
    <a href="#available-models">Models</a> ·
    <a href="#ai-agent-integration">Agent Integration</a> ·
    <a href="README_CN.md">中文文档</a>
  </p>
</p>

---

One command. Files in, text out.

QSense is not an app — it's the lowest-level perception primitive for skills, agents, and scripts. It does one thing: **send multimodal input to an LLM, get text back.** Video splitting, audio segmentation, batch processing, result parsing — all belong to the caller.

```
┌──────────────────────────────────────────────────────┐
│  Skills / Agents / Scripts                           │
│  video review, meeting notes, OCR pipeline, ...      │
├──────────────────────────────────────────────────────┤
│  QSense  ← you are here                             │
│  image / audio / video  →  LLM  →  text             │
├──────────────────────────────────────────────────────┤
│  OpenAI-compatible API (Gemini, Claude, GPT, Grok…)  │
└──────────────────────────────────────────────────────┘
```

## Features

| | Feature | Detail |
|---|---------|--------|
| 🖼 | **Image** | Auto-resize & encode local files; passthrough remote URLs |
| 🎙 | **Audio** | Streaming download & base64 encode (OpenAI `input_audio` format) |
| 🎬 | **Video** | Direct encode (default) or ffmpeg frame extraction + audio track |
| 🤖 | **Multi-model** | Gemini / Claude / GPT / Grok / Kimi / Gemma — YAML registry |
| ⚡ | **Auto-adapt** | Stream/non-stream fallback, model capability matching |
| 🔌 | **Agent-ready** | Plain text stdout, `[qsense]` stderr errors, exit 0/1, zero side effects |

## Quick Start

**Recommended (global, no activation needed):**

```bash
pipx install qsense-cli
qsense --prompt "Describe this image" --image photo.png
# First run will interactively guide API key setup
```

**For development:**

```bash
bash setup.sh && source .venv/bin/activate
# or: uv venv --python 3.12 && source .venv/bin/activate && uv pip install -e .
```

**For agents / CI:**

```bash
pipx install qsense-cli
QSENSE_API_KEY=sk-xxx qsense init --api-key $QSENSE_API_KEY
```

## Usage Examples

```bash
# ── Image ──────────────────────────────────────────
qsense --prompt "What's in this image?" --image screenshot.png
qsense --prompt "Compare these" --image a.png --image b.png
qsense --prompt "Describe" --image https://example.com/photo.jpg

# ── Audio ──────────────────────────────────────────
qsense --prompt "Transcribe this" --audio recording.wav
qsense --prompt "What genre?" --audio https://example.com/song.mp3

# ── Video (direct passthrough) ─────────────────────
qsense --prompt "Summarize this video" --video clip.mp4

# ── Video (frame extraction) ──────────────────────
qsense --prompt "Describe" --video clip.mp4 --video-extract --fps 2

# ── Mixed modalities ──────────────────────────────
qsense --prompt "Analyze" --image frame.png --audio narration.wav

# ── Model override ────────────────────────────────
qsense --model anthropic/claude-opus-4-6 --prompt "Analyze" --image photo.png
```

## Available Models

```bash
qsense models           # List all models
qsense models --detail  # Show detailed limits
```

| Model | Vision | Audio | Video | Context |
|:------|:------:|:-----:|:-----:|--------:|
| `google/gemini-3-flash-preview` | ✅ | ✅ | native | 1M |
| `google/gemini-3.1-pro-preview` | ✅ | ✅ | native | 1M |
| `gemma-4-31B-it` | ✅ | — | extract | 256K |
| `anthropic/claude-opus-4-6` | ✅ | — | — | 1M |
| `anthropic/claude-sonnet-4-6` | ✅ | — | — | 1M |
| `gpt-5.4` | ✅ | — | — | — |
| `grok-4.20-beta` | ✅ | — | — | 256K |
| `Kimi-K2.5` | ✅ | — | native* | 256K |

<sup>* experimental</sup>

## CLI Reference

```
qsense [OPTIONS] [COMMAND]

Options:
  --prompt TEXT         Text prompt (required for inference)
  --image TEXT          Image path or URL (repeatable)
  --audio TEXT          Audio file path or URL (repeatable)
  --video TEXT          Video file path or URL (repeatable)
  --video-extract       Use ffmpeg frame extraction
  --fps FLOAT           Extraction frame rate (default: 1)
  --max-frames INT      Max extracted frames (default: 30)
  --model TEXT          Override default model
  --timeout INT         Request timeout in seconds
  --max-size INT        Max image longest side in px (default: 2048)

Commands:
  init                  Initialize configuration
  config                Show or update configuration
  models                List available models
```

## Configuration

Priority: CLI flags > environment variables > `~/.qsense/.env`

```bash
# Show current config
qsense config

# Update
qsense config --model google/gemini-3.1-pro-preview
qsense config --api-key sk-xxx
qsense config --base-url https://api.openai.com/v1

# Environment variables
export QSENSE_API_KEY=sk-xxx
export QSENSE_BASE_URL=https://api.openai.com/v1
export QSENSE_MODEL=google/gemini-3-flash-preview
```

## Design Philosophy

> QSense is an **atomic skill** — the smallest indivisible unit of perception.

**What QSense does** — send files to a model, return text. That's it.

**What QSense does NOT do** — video download, audio slicing, batch iteration, result parsing, conversation management, workflow orchestration. All left to the caller.

```bash
# Compose with higher-level skills
ffmpeg -i long.mp4 -segment_time 60 -f segment chunk_%03d.mp4
for f in chunk_*.mp4; do
  qsense --prompt "Summarize this minute" --video "$f" >> result.txt
done
```

Stay atomic, stay composable. See [docs/design-rationale.md](docs/design-rationale.md) for the full story.

## AI Agent Integration

QSense is a **Skill + CLI** project: the CLI is the execution layer, the Skill is the knowledge layer that teaches AI agents how to use it effectively.

### Install

**GitHub:** https://github.com/hezi-ywt/qsense

Copy the following to your agent — it knows how to install skills for its own platform:

```
Install the qsense multimodal perception skill from https://github.com/hezi-ywt/qsense
The skill follows the Agent Skills standard (https://agentskills.io).
Install it using your platform's skill installation method.
For example: npx skills add hezi-ywt/qsense
```

### Three-File Skill Design

```
skills/qsense/
├── SKILL.md                    # Stable facts
│                               # Command syntax, output contract, error guide
│
└── references/
    ├── models.md               # Model knowledge
    │                           # Capabilities, limits, video/audio strategy
    │                           # Syncs with `qsense models --detail`
    │
    └── user-notes.md           # Living memory
                                # Agent-maintained: preferences, patterns, lessons
```

| File | Changes | Maintained by |
|------|---------|---------------|
| `SKILL.md` | Rarely — only when CLI changes | Developer |
| `models.md` | When models are added/updated | Developer + Agent sync |
| `user-notes.md` | Continuously during use | Agent automatically |

The agent reads `user-notes.md` before each use and updates it when it learns something — a model preference, a failed command's fix, a recurring workflow. **The more you use it, the better it gets.**

### Skill-Craft: A Skill for Building Skills

> ⚠️ **Experimental** — This meta-skill is in early stages and has not been validated across multiple real-world skill creation cycles. Design principles are distilled from building qsense, but may evolve significantly.

This repo also includes `skills/skill-craft/`, a meta-skill that teaches agents how to design and evaluate Agent Skills. It covers:

- **Structure** — Three-file layering by change frequency, progressive context loading
- **6 Design Principles** — Greedy-but-dense descriptions, explain why not MUST, no parroting, skill memory, give URLs not commands, atomic scripts
- **Evaluation System** — Subagent-based parallel testing, grading, blind A/B comparison, automated description optimization with train/test split
- **CLI Design** — Separated into `references/cli-design.md` (not every skill needs a CLI)

```
skills/skill-craft/
├── SKILL.md                  # Design principles & structure guide
├── agents/                   # Subagent instructions (grader, comparator, analyzer)
├── references/               # Evaluation workflow, CLI design, JSON schemas, examples
└── scripts/                  # Automated eval: trigger testing, description optimization
```

## Project Structure

```
src/qsense/
  cli.py            Click CLI entry point
  client.py         OpenAI-compatible API client
  config.py         Three-tier config: CLI > env > file
  image.py          Image validation, resize, encoding
  audio.py          Audio validation, download, encoding
  video.py          Video passthrough and frame extraction
  models.py         Model registry loader
  registry.yaml     Curated model capabilities database
```

## Requirements

- Python >= 3.10
- ffmpeg (only for `--video-extract` mode)

## License

MIT
