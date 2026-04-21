# QSense 使用指南

## 安装

### 推荐安装（全局可用，无需激活环境）

```bash
pipx install qsense-cli
```

### Agent / CI

```bash
pipx install qsense-cli
QSENSE_API_KEY=sk-xxx qsense init --api-key $QSENSE_API_KEY
```

环境变量：
- `QSENSE_API_KEY` -- API 密钥（必需）
- `QSENSE_BASE_URL` -- API 地址（默认 `https://api.openai.com/v1`）
- `QSENSE_MODEL` -- 默认模型（默认 `google/gemini-3-flash-preview`）

### 开发安装

```bash
bash setup.sh && source .venv/bin/activate
# 或: uv venv --python 3.12 && source .venv/bin/activate && uv pip install -e .
```

### 验证

```bash
qsense --help
qsense models
```

## 首次配置

第一次运行时，如果缺少 API key，qsense 会交互式引导你完成配置：

```
$ qsense --prompt "test" --image photo.png
[qsense] First-run setup — your answers will be saved to ~/.qsense/.env
API key: sk-xxxxxxx
Base URL [https://api.openai.com/v1]:
Default model [google/gemini-3-flash-preview]:
[qsense] Configuration saved to ~/.qsense/.env
```

配置存储在 `~/.qsense/.env`，后续运行自动读取。

非交互环境（CI/agent）中需提前配置，否则会报错退出。

## 图像理解

### 本地图片

```bash
qsense --prompt "描述这张图片" --image photo.png
qsense --prompt "这张截图里有什么文字" --image screenshot.jpg
```

支持格式：`jpg` `jpeg` `png` `webp` `gif`

### 远程图片

```bash
qsense --prompt "描述" --image https://example.com/photo.jpg
```

远程 URL 直接透传给 API，不下载。

### 多图对比

```bash
qsense --prompt "对比这两张图的差异" --image before.png --image after.png
```

`--image` 可重复使用，图片按顺序传给模型。

### 角色化输入

```bash
qsense --prompt "根据参考和规范审核目标图。" --target page.png --reference ref.png --spec review.md
qsense --prompt "对比当前页面和上一版。" --target current.png --reference previous.png --context notes.md
```

- `--target` 表示当前要看的主对象，单次请求最多一个
- `--reference` 表示对照素材、风格参考、上一版
- `--context` 表示只提供背景信息，不直接作为判定依据
- `--spec` 表示规则、要求、审核标准；可传文本文件或媒体文件

### 控制图片尺寸

```bash
qsense --prompt "描述" --image photo.png --max-size 1024
```

`--max-size` 设置长边最大像素（默认 2048）。大图会等比缩小，小图不放大。

### 视觉精度控制

```bash
qsense --prompt "读取图表中的全部小字" --target chart.png --vision-fidelity max
qsense --prompt "快速扫一眼页面布局" --target layout.png --vision-fidelity low
```

- `low`: 降低视觉细节预算，适合快速粗看
- `standard`: 当前默认行为，兼顾成本和细节
- `max`: 尽量保留更多细节，适合 OCR、小字、密集图表、局部差异

## 音频理解

### 本地音频

```bash
qsense --prompt "转录这段录音" --audio recording.wav
qsense --prompt "这是什么音乐风格" --audio song.mp3
```

支持格式：`mp3` `wav` `flac` `ogg` `m4a` `aac` `webm`

### 远程音频

```bash
qsense --prompt "描述这段音频" --audio https://example.com/clip.mp3
```

远程音频会自动下载到内存后编码（上限 20MB）。格式从 Content-Type 或 URL 扩展名推断。

### 注意事项

- 音频使用 OpenAI `input_audio` 格式（base64 内联），不是所有模型都支持
- Gemini 系列支持最好（最长 ~8.4 小时）
- Claude、GPT、Grok 不支持音频输入

## 视频理解

### 直传模式（默认）

```bash
qsense --prompt "总结这个视频" --video clip.mp4
```

整个视频 base64 编码发送。适用于支持原生视频的模型（Gemini、Kimi）。上限 20MB。

支持格式：`mp4` `webm` `mov` `avi` `mkv`

### 抽帧模式

```bash
qsense --prompt "描述视频内容" --video clip.mp4 --video-extract
```

使用 ffmpeg 抽取视频帧为图片 + 提取音轨，分别通过图像和音频通道发送。适用于不支持原生视频的模型。

**需要安装 ffmpeg**：
```bash
# macOS
brew install ffmpeg

# Ubuntu
apt install ffmpeg
```

### 抽帧参数

```bash
# 每秒 2 帧，最多 60 帧
qsense --prompt "分析" --video long_video.mp4 --video-extract --fps 2 --max-frames 60
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--fps` | 1.0 | 每秒抽帧数 |
| `--max-frames` | 30 | 最大帧数，超出则均匀采样 |

### 远程视频 URL

直传模式支持远程 URL（透传给 API）：
```bash
qsense --prompt "描述" --video https://example.com/clip.mp4
```

抽帧模式不支持远程 URL，需先下载到本地。

## 混合输入

可以同时传入多种模态：

```bash
# 图片 + 音频
qsense --prompt "图片和音频匹配吗" --image frame.png --audio narration.wav

# 视频 + 图片
qsense --prompt "对比视频和截图" --video clip.mp4 --image reference.png
```

角色化参数和传统参数可以混用，但推荐在审核/对比任务里优先使用 `--target` / `--reference` / `--context` / `--spec`，这样提示组装更稳定。

## 结构化输出

### JSON 响应封装

```bash
qsense --prompt "提取结论" --target screenshot.png --output json
```

`--output json` 会返回统一响应封装，包含：
- `model`
- `output_format`
- `text`
- `warnings`
- `meta`
- `data`（当 schema 校验成功时写入解析后的 JSON）

### 使用 Schema 校验模型输出

```bash
qsense --prompt "提取审核结果" --target screenshot.png --schema review.schema.json --output json
```

推荐让模型输出纯 JSON 字符串，再用 `--schema` 校验。如果校验通过，`data` 字段会包含解析后的结构化对象；如果不通过，qsense 会直接报错退出。

## 模型选择

### 查看可用模型

```bash
qsense models              # 简要列表
qsense models --detail     # 详细限制信息
```

输出示例：
```
  google/gemini-3-flash-preview *
    Gemini 3 Flash | vision, audio, video(native) | ctx 1M
    快速多模态模型，适合日常图像/音频/视频理解
```

`*` 标记当前默认模型。

### 指定模型

```bash
qsense --model anthropic/claude-opus-4-6 --prompt "分析" --image photo.png
qsense --model gpt-5.4 --prompt "描述" --image screenshot.png
```

### 切换默认模型

```bash
qsense config --model google/gemini-3.1-pro-preview
```

## 配置管理

### 查看当前配置

```bash
$ qsense config
  api_key:  sk-lkb...EiX9
  base_url: https://api.openai.com/v1
  model:    google/gemini-3-flash-preview
```

### 修改配置

```bash
qsense config --model google/gemini-3.1-pro-preview
qsense config --api-key sk-newkey
qsense config --base-url https://other-api.com/v1
qsense config --model gpt-5.4 --base-url https://new.api/v1  # 一次改多个
```

### 环境变量

环境变量优先级高于配置文件：

```bash
export QSENSE_API_KEY=sk-xxx
export QSENSE_BASE_URL=https://api.openai.com/v1
export QSENSE_MODEL=google/gemini-3-flash-preview
```

### 优先级

1. CLI 参数（`--model xxx`）
2. 环境变量（`QSENSE_MODEL`）
3. 配置文件（`~/.qsense/.env`）

## 错误排查

| 错误信息 | 原因 | 解决 |
|----------|------|------|
| `Missing API key` | 未配置 API key | 在交互终端运行一次 qsense 完成配置 |
| `Image file not found` | 本地文件路径错误 | 检查路径 |
| `Unsupported image type` | 不支持的格式 | 使用 jpg/png/webp/gif |
| `Image too small` | 图片宽或高 < 64px | 使用更大的图片 |
| `Video too large for direct mode` | 视频 > 20MB | 改用 `--video-extract` |
| `ffmpeg is required` | 抽帧模式缺少 ffmpeg | 安装 ffmpeg |
| `Failed to download audio` | 远程音频下载失败 | 检查 URL 是否可访问 |
| `Cannot determine audio format` | 无法推断音频格式 | 使用明确扩展名的 URL |
| `model '<id>' is not in the registry` | 指定了未注册的模型，qsense 会直接退出 | 运行 `qsense models` 选择精确模型 ID |
| `HTTP 401` | API key 无效 | `qsense config --api-key` 更新 |
| `Stream must be set to true` | 模型要求流式（会自动重试） | 注册表标记 `stream_only: true` |

## 边界说明

QSense 仍然保持原子能力边界，只负责单次多模态观察请求。它现在支持角色化输入、视觉精度控制、JSON 输出和可选 schema 校验，但依然不负责：

- 批处理
- 自动重跑 / prompt 修复
- 工作流编排
- 领域专属审核规则库
