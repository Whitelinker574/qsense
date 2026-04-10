# QSense 设计理念与开发记录

## 定位：原子技能

QSense 是**多模态感知的原子技能（atomic skill）**。

"原子"的含义：**不可再分的最小有用单元**。它只做一件事——把图像/音频/视频送给模型，拿回文字。没有多余的封装，没有流水线，没有 workflow 引擎。

```
原子技能（qsense）            → "让模型看一眼这个东西"
组合技能（上层 skill）          → "审核这个视频的每一分钟"
应用（agent / 产品）           → "自动监控直播内容合规性"
```

这个分层是刻意的。QSense 保持最朴素的状态，是为了让上层 skill 能灵活组合：

| 你想做的 | QSense 负责的部分 | 上层 skill 负责的部分 |
|---------|-----------------|---------------------|
| 长视频分析 | 理解单个片段 | 下载、切片、汇总 |
| 会议纪要 | 转录单段音频 | 音频切片、结果拼接 |
| 批量 OCR | 识别单张图片 | 截图、遍历、结果收集 |
| 内容审核 | 判断单帧/单段 | 抽样策略、阈值逻辑 |
| 多模态问答 | 单次理解 | 对话管理、上下文维护 |

**qsense 永远只做表格左列的事。** 右列的逻辑不会进入 qsense 代码。

### 为什么不做更多

做更多 = 假设使用场景。一旦在 qsense 里内置"视频自动切片"，就假设了所有人都想按时间切。但有人想按场景切，有人想按语音停顿切，有人根本不想切——他们想整段直传。

保持原子，让上层自由选择策略。qsense 提供的是能力，不是方案。

## 为什么做这个

多模态理解能力正在从"实验性功能"变成"基础设施"。但现实是：

1. **每个模型的 API 格式不同** — 图片用 `image_url`，音频用 `input_audio`，视频有的支持有的不支持
2. **每个代理/中转的行为不同** — 有的强制 streaming，有的不支持音频转发，有的视频 URL 透传 500
3. **Agent 需要一个统一接口** — 不想在每个 skill 里重复写图片编码、音频下载、视频抽帧

QSense 把这些差异封装成一个 CLI，对外只暴露 `--image`、`--audio`、`--video`。

## 开发历程

### Phase 1: 图像理解

最初只做图片。设计文档明确限定了 V1 scope：

- 图像 only，1-5 张/请求
- OpenAI 兼容 API
- 全局配置 `~/.qsense/.env`
- 首次运行交互引导

实现时选择了 Python + Click + openai SDK。图像处理用 Pillow：
- 本地文件 → 校验格式 → Pillow 打开 → 等比缩放（长边 ≤ 2048） → base64 data URL
- 远程 URL → 直接透传给 API

关键决策：**图像要做尺寸处理**。大图浪费 token 和带宽，2048px 是多数模型的最佳平衡点。

### Phase 2: 音频理解

先做了格式探测（`scripts/probe_audio_format.py`），测试了三种 payload 格式：
- `input_audio`（OpenAI 标准）— 成功
- `image_url` + audio data URL — 成功（但非标准）
- `audio_url` — 失败

关键发现：**OpenAI API 没有 `audio_url` 类型**。图片有 `image_url`，但音频必须 base64 内联。这意味着远程音频必须先下载后编码，不能像图片那样透传 URL。

音频下载用 httpx 流式读取，超过 20MB 立即中断（防 OOM）。

### Phase 3: 视频理解

视频最复杂，因为策略选择多：

1. **直传模式**（默认）— 整个视频 base64 编码为 `data:video/mp4;base64,...`，通过 `image_url` 字段发送。Gemini 和 Kimi 支持。
2. **抽帧模式**（`--video-extract`）— ffmpeg 抽帧为图片 + 提取音轨，走 image + audio 通道。适合不支持原生视频的模型。

关键决策：**默认直传，抽帧可选**。直传保留了视频的时序信息和原始音轨，质量更好。抽帧是降级方案。

远程视频 URL 一开始是直接透传，但测试发现代理不稳定（经常 500）。改为默认下载后编码，同时保留 `--video-passthrough` 手动覆盖和注册表 `video_url_passthrough` 自动选择。

### Phase 4: 多模型支持

不同模型的差异很大：

| 差异点 | 处理方式 |
|--------|---------|
| 有的要求 stream=true | 注册表 `stream_only` + 自动降级 |
| 有的不支持音频 | 注册表 `audio: false`，`qsense models` 展示 |
| 有的支持原生视频 | 注册表 `native_video` |
| 有的推理模型输出 `<think>` | client 自动 strip |

用 **YAML 注册表**管理模型能力，而不是硬编码在代码里。加新模型只改 YAML，不碰 Python。

### Phase 5: 安全加固

Code review 发现的关键问题和修复：

- 配置文件默认 644 → chmod 600 + 目录 700
- `curl | sh` → 移除，要求用户自装 uv
- 异常可能泄漏 API key → 脱敏只打印 status_code + message
- .env 换行注入 → sanitize
- `<think>` strip 误删用户内容 → 限定响应开头
- 音频一次性加载到内存 → 流式下载
- fps=0 / max-frames=-1 → 参数校验

## 核心设计决策

### 为什么只用 OpenAI SDK

不引入 google-generativeai、anthropic 等 SDK。所有模型都通过 `openai.OpenAI(base_url=...)` 访问。原因：

1. 用户通常通过中转站/代理聚合多个模型，统一暴露 OpenAI 兼容接口
2. 一个 SDK 意味着一套 content format 处理逻辑
3. 减少依赖，降低维护成本

### 为什么图片 URL 透传但音频不透传

- 图片：OpenAI 标准 `image_url` 类型支持远程 URL，所有代理都实现了
- 音频：没有 `audio_url` 类型，只有 `input_audio`（base64），必须本地编码
- 视频：`image_url` 能传但代理行为不一致，默认下载编码更稳定

### 为什么默认下载视频而非透传

测试发现代理透传远程视频 URL 经常 500。下载后编码虽然多了一次网络请求，但：
- 确保数据格式一致
- 不依赖代理的 URL fetch 能力
- 可以做大小限制（20MB）

注册表 `video_url_passthrough` 留了口子，代理稳定后改成 true 就能自动走透传。

### 为什么 stream 要自动降级

有的代理（如某些 GPT 中转）强制要求 `stream=true`，返回 `"Stream must be set to true"` 错误。而大多数模型用 non-stream 更简单。

策略：注册表有 `stream_only` 标记的直接走 stream。没标记的先试 non-stream，如果错误消息含 "stream" 就自动重试 stream。兼顾已知模型和未知模型。

## 作为 Agent Skill 的设计

QSense 的 CLI 接口天然适合 agent 调用：

### 输入输出契约

- **输入**: CLI 参数（`--prompt`、`--image`、`--audio`、`--video`）
- **输出**: 纯文本到 stdout，错误到 stderr，exit code 0/1
- **无副作用**: 不写文件（除首次 init），不修改系统状态

### Agent 使用模式

```bash
# 基础调用
result=$(qsense --prompt "描述图片内容" --image screenshot.png)

# 带模型选择
result=$(qsense --model anthropic/claude-opus-4-6 --prompt "分析" --image photo.png)

# 多模态
result=$(qsense --prompt "视频中说了什么" --video meeting.mp4 --video-extract)

# 管道组合
qsense --prompt "提取文字" --image doc.png | other-tool --input -
```

### 配置方式

```bash
# 方式 1: 环境变量（推荐 agent 使用）
QSENSE_API_KEY=sk-xxx QSENSE_BASE_URL=https://... qsense --prompt ...

# 方式 2: 一次性 init
qsense init --api-key sk-xxx --base-url https://...

# 方式 3: 交互式（人工）
qsense init
```

### Skill 集成示例

```yaml
# skill 定义（示例）
name: visual-understand
description: 使用多模态模型理解图像/音频/视频内容
tool: qsense
setup: |
  pipx install qsense-cli
  qsense init --api-key $API_KEY
usage: |
  qsense --prompt "{prompt}" --image "{file}"
  qsense --prompt "{prompt}" --video "{file}" --video-extract
```

### 模型选择策略

Agent 可以根据任务类型自动选择模型：

```bash
# 需要音频理解 → 选 Gemini
qsense --model google/gemini-3-flash-preview --prompt "转录" --audio recording.wav

# 需要深度推理 → 选 Claude
qsense --model anthropic/claude-opus-4-6 --prompt "分析逻辑" --image diagram.png

# 需要快速响应 → 选默认 Gemini Flash
qsense --prompt "简要描述" --image photo.png

# 查询模型能力
qsense models --detail  # 输出可解析
```

## 原子能力 vs 上层 Skill

QSense 刻意保持"原子"状态。以下是 qsense 做和不做的边界：

| qsense 做 | qsense 不做（留给上层 skill） |
|-----------|---------------------------|
| 读取本地文件 | 从网盘/云存储下载素材 |
| 图片缩放编码 | 批量图片处理流水线 |
| 音频下载编码 | 长音频切片、VAD 静音检测 |
| 视频编码/抽帧 | 视频下载、切片、场景分割 |
| 单次 API 调用 | 多轮对话、上下文管理 |
| 返回纯文本 | 结构化解析、JSON schema 校验 |
| 模型注册表查询 | 自动模型路由、成本优化 |

上层 skill 可以这样组合 qsense：

```bash
# Skill: 长视频分析
# 1. 下载视频（其他工具）
yt-dlp -o video.mp4 "https://..."

# 2. 切片（ffmpeg，不是 qsense 的事）
ffmpeg -i video.mp4 -segment_time 60 -f segment chunk_%03d.mp4

# 3. 逐片理解（qsense 的事）
for chunk in chunk_*.mp4; do
  qsense --prompt "总结这一分钟的内容" --video "$chunk" >> summaries.txt
done

# 4. 汇总（其他 skill）
qsense --prompt "根据以下逐段总结，写一份完整摘要：$(cat summaries.txt)" --image placeholder.png
```

```bash
# Skill: 会议纪要
# 1. 提取音频（ffmpeg）
ffmpeg -i meeting.mp4 -vn -ar 16000 meeting.wav

# 2. 切片（sox/ffmpeg）
sox meeting.wav chunk_ trim 0 300 : newfile : restart

# 3. 逐段转录（qsense）
for chunk in chunk_*.wav; do
  qsense --model google/gemini-3-flash-preview --prompt "转录" --audio "$chunk"
done
```

## 后续方向

保持原子能力不变，可能扩展的方向：

- **`--output json`**: 可选返回 JSON（方便 agent 解析）
- **Python API**: `from qsense import chat` 供 skill 直接 import
- **PDF 模态**: 文档理解作为新的原子能力
- **注册表动态同步**: 从 API `/models` 自动发现模型（可选）
