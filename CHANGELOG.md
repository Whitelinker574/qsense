# Changelog

All notable changes to QSense are documented here.

## [0.2.1] - 2026-04-10

### Added

- **skill-craft meta-skill** ⚠️ *experimental* — a skill for building skills (`skills/skill-craft/`)
  - 6 design principles: greedy-but-dense description, explain why not MUST, no parroting, skill memory, give URLs not commands, atomic scripts
  - Complete evaluation system adapted from Anthropic's skill-creator:
    - Subagent agents: `grader.md` (assertion evaluation + test critique), `comparator.md` (blind A/B comparison), `analyzer.md` (post-hoc analysis + benchmark pattern detection)
    - Automation scripts: `run_eval.py` (trigger rate testing), `run_loop.py` (eval + improve loop with train/test split), `improve_description.py` (Claude + extended thinking), `aggregate_benchmark.py` (benchmark statistics)
    - JSON schemas for evals, grading, benchmark, comparison, analysis
  - CLI design guidance separated into `references/cli-design.md` (not every skill needs a CLI)
  - SKILL.md follows its own layering rules: 182 lines, all operational detail in references/
- **qsense trigger tests** — `evals/trigger-tests.md` with 10 should-trigger + 5 should-not-trigger prompts
- **qsense description optimized** — expanded to cover screenshot analysis, photo description, UI error checking, image comparison

### Changed

- skill-craft SKILL.md restructured: evaluation workflow, CLI design, JSON schemas moved to references/ (was 372 → 182 lines)

## [0.2.0] - 2026-04-10

### Added

- **Agent Skills support** — standard `SKILL.md` following the [Agent Skills](https://agentskills.io) specification
  - Three-file design: `SKILL.md` (stable facts) + `references/models.md` (model knowledge) + `references/user-notes.md` (continuous learning)
  - Agent reads and updates `user-notes.md` over time — the more you use it, the better it gets
- **Agent-friendly `qsense init`** — non-TTY environments get actionable guidance instead of crashing on `input()`
- **Bilingual README** — `README.md` (English) + `README_CN.md` (Chinese)
- **pipx install support** — `pipx install qsense-cli` for global usage without venv activation
- **Prerequisites check in SKILL.md** — guides agent to verify Python and pipx before installing

### Changed

- Default install method changed from venv to `pipx install qsense-cli`
- README redesigned with centered header, feature table with icons, model table with checkmarks
- Agent Integration section explains the Skill + CLI dual-layer design

## [0.1.0] - 2026-04-09

### Added

- **Image understanding** — local files auto-resize via Pillow (max 2048px long side), remote URLs passthrough
- **Audio understanding** — streaming download + base64 encode, OpenAI `input_audio` format
- **Video understanding** — direct base64 encode (default) or ffmpeg frame extraction + audio track separation
- **Multi-model support** — Gemini, Claude, GPT, Grok, Kimi, Gemma via YAML registry
- **Stream auto-fallback** — `stream_only` registry flag + automatic retry on stream errors
- **Per-modality model defaults** — `--image-model`, `--audio-model`, `--video-model` config
- **Three-tier config** — CLI flags > environment variables > `~/.qsense/.env` (chmod 600)
- **Interactive first-run setup** — guided API key, base URL, model configuration
- **Security hardening** — config file permissions, .env injection prevention, API error sanitization, `<think>` block stripping
- **ffmpeg/pyav detection** — runtime dependency check with install guidance
- **Model registry** — `registry.yaml` with capabilities, limits, format lists, behavior flags
- **CLI commands** — `qsense` (inference), `qsense init`, `qsense config`, `qsense models`
