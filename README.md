# QSense

**多模态感知原子技能。** 一条命令让模型"看"图像、"听"音频、"看"视频，返回文字。

QSense 不是应用，是给上层 skill、agent、脚本调用的最底层感知能力。它只做一件事：**把多模态输入送给模型，拿回文字结果。** 视频切片、音频分段、批量处理、结果解析——这些都不是 qsense 的事，留给上层组合。

```
┌──────────────────────────────────────────────────────┐
│  上层 Skill / Agent / 脚本                             │
│  (视频审核、会议纪要、OCR 流水线、内容分析...)            │
├──────────────────────────────────────────────────────┤
│  QSense  ← 你在这里                                   │
│  原子能力：图像/音频/视频 → 模型 → 文字                  │
├──────────────────────────────────────────────────────┤
│  OpenAI-compatible API (Gemini, Claude, GPT, Grok...) │
└──────────────────────────────────────────────────────┘
```

## Features

- **Image** -- 本地文件自动缩放编码，远程 URL 直接透传
- **Audio** -- 本地/远程文件流式下载编码（OpenAI `input_audio` 格式）
- **Video** -- 直传编码（默认）或 ffmpeg 抽帧+音轨分离
- **Multi-model** -- Gemini / Claude / GPT / Grok / Kimi / Gemma，YAML 注册表管理
- **Auto-adapt** -- 流式/非流式自动降级，模型能力自动匹配
- **Agent-ready** -- 纯文本 stdout 输出，`[qsense]` stderr 错误，exit 0/1，零副作用

## Quick Start

### 一键安装（人工）

```bash
bash setup.sh
source .venv/bin/activate
qsense --prompt "Describe this image" --image photo.png
# 首次运行会交互式引导配置 API key
```

### 一键安装（Agent / CI）

```bash
QSENSE_API_KEY=sk-xxx bash setup.sh
source .venv/bin/activate
```

### 手动安装

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e .
# 或: pip install -e .
```

## Usage Examples

```bash
# Image
qsense --prompt "What's in this image?" --image screenshot.png
qsense --prompt "Compare these" --image a.png --image b.png
qsense --prompt "Describe" --image https://example.com/photo.jpg

# Audio
qsense --prompt "Transcribe this" --audio recording.wav
qsense --prompt "What genre?" --audio https://example.com/song.mp3

# Video (direct passthrough, default)
qsense --prompt "Summarize this video" --video clip.mp4

# Video (frame extraction, for models without native video)
qsense --prompt "Describe" --video clip.mp4 --video-extract --fps 2

# Mixed
qsense --prompt "Analyze" --image frame.png --audio narration.wav

# Specify model
qsense --model anthropic/claude-opus-4-6 --prompt "Analyze" --image photo.png
```

## Available Models

```bash
qsense models           # List all models
qsense models --detail  # Show limits (formats, max size, etc.)
```

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

*experimental

## CLI Reference

```
qsense [OPTIONS] [COMMAND]

Options:
  --prompt TEXT         Text prompt (required for inference)
  --image TEXT          Image path or URL (repeatable)
  --audio TEXT          Audio file path or URL (repeatable)
  --video TEXT          Video file path or URL (repeatable)
  --video-extract       Use ffmpeg frame extraction instead of direct passthrough
  --fps FLOAT           Extraction frame rate (default: 1)
  --max-frames INT      Max extracted frames (default: 30)
  --model TEXT          Override default model
  --timeout INT         Request timeout in seconds
  --max-size INT        Max image longest side in pixels (default: 2048)

Commands:
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

## Project Structure

```
src/qsense/
  __init__.py       Package metadata
  _util.py          Shared utilities (abort)
  cli.py            Click CLI entry point
  client.py         OpenAI-compatible API client
  config.py         Configuration loading and first-run setup
  image.py          Image validation, resize, encoding
  audio.py          Audio validation, download, encoding
  video.py          Video direct passthrough and frame extraction
  models.py         Model registry loader
  registry.yaml     Curated model list with capabilities
```

## Design Philosophy

QSense 是**原子技能（atomic skill）**——不可再分的最小感知单元。

**QSense 做什么：** 把一个/多个文件送给模型，返回文字。就这样。

**QSense 不做什么：** 视频下载、音频切片、批量遍历、结果解析、对话管理、workflow 编排——全部留给上层 skill 组合。

```bash
# 上层 skill 组合示例：长视频逐段分析
ffmpeg -i long.mp4 -segment_time 60 -f segment chunk_%03d.mp4
for f in chunk_*.mp4; do
  qsense --prompt "总结这一分钟" --video "$f" >> result.txt
done
```

保持原子，才能让上层自由选择策略。详见 [docs/design-rationale.md](docs/design-rationale.md)。

## Requirements

- Python >= 3.10
- ffmpeg (only for `--video-extract` mode)
