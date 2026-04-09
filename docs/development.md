# QSense 开发文档

## 开发环境

```bash
# 克隆项目后
cd qsense
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e .

# 验证
qsense --help
qsense init  # 配置 API key + 检测 ffmpeg
```

## 项目结构

```
qsense/
├── pyproject.toml              包配置、依赖、入口点
├── CLAUDE.md                   Agent 上下文（Claude Code 自动加载）
├── README.md                   项目介绍
├── setup.sh                    一键安装脚本
├── .gitignore
├── docs/
│   ├── usage.md                使用指南
│   ├── development.md          本文件
│   ├── design-rationale.md     设计理念与决策记录
│   └── 2026-04-09-qsense-cli-design.md  原始 V1 设计规格
├── scripts/
│   └── probe_audio_format.py   音频格式探测脚本
└── src/qsense/
    ├── __init__.py              版本号
    ├── _util.py                 公共工具（abort, NoReturn）
    ├── cli.py                   CLI 入口（Click group + 子命令）
    ├── client.py                API 客户端（stream 自动降级）
    ├── config.py                配置加载 + 首次设置（chmod 600）
    ├── image.py                 图像处理（Pillow resize + base64）
    ├── audio.py                 音频处理（流式下载 + base64）
    ├── video.py                 视频处理（直传/下载/抽帧）
    ├── models.py                模型注册表加载器
    └── registry.yaml            模型注册表数据
```

## 模块职责

### `_util.py`
唯一导出 `abort(message) -> NoReturn`。统一错误退出：`[qsense] message` 到 stderr，exit 1。

### `config.py`
- `Config` dataclass: api_key, base_url, model, timeout
- `load_config()`: 三层合并（CLI > env > file）
- `run_first_time_setup()`: 交互式引导
- `show_config()` / `update_config()`: 配置管理
- `_write_config()`: 写入 `~/.qsense/.env`，chmod 600
- `_sanitize()`: 防止换行符注入

### `image.py`
- `prepare_image(source)` / `prepare_images(sources)`
- 远程 URL: 直接透传（`image_url` 字段）
- 本地文件: Pillow 打开 → 校验尺寸 → 等比缩小 → base64 data URL
- 类型: `ImageContentPart` (TypedDict)

### `audio.py`
- `prepare_audio(source)` / `prepare_audios(sources)`
- 远程 URL: httpx **流式下载**（超限即中断）→ 格式检测 → base64
- 本地文件: 读取 → 校验 → base64
- 输出: `input_audio` 格式（OpenAI 标准，无 `audio_url` 类型）

### `video.py`
- `encode_video_direct(source, url_passthrough=)`:
  - 远程 + passthrough → URL 直接透传
  - 远程 + 默认 → 流式下载 → base64 data URL
  - 本地 → 读取 → base64 data URL
- `extract_frames_and_audio(source)`: ffmpeg 抽帧 + 音轨
  - 支持远程 URL（先下载到临时文件）
  - 复用 `image.prepare_images()` + `audio.prepare_audio()`

### `client.py`
- `chat()`: 构建 message content → OpenAI SDK 调用
- 流式策略: registry `stream_only` → 直接 stream；否则先 non-stream，失败降级
- `_format_api_error()`: 异常脱敏，不泄漏 API key
- `_strip_thinking()`: 去除响应开头的 `<think>` 块

### `models.py`
- `ModelInfo` frozen dataclass
- 从 `registry.yaml` 加载，YAML 损坏时优雅降级（空列表 + 警告）
- `get_model()` / `list_models()` / `is_registered()`

### `cli.py`
- `main`: Click group，无子命令时执行推理
- `init`: 初始化配置 + ffmpeg 检测/安装
- `config`: 查看/修改配置
- `models`: 列出注册表模型（`--detail` 显示限制）

## 注册表配置参考

### 字段说明

```yaml
- id: provider/model-name        # API 使用的确切模型 ID（必填）
  name: Display Name              # 显示名称
  # ── 能力标记 ──
  vision: true                    # 支持图像输入
  audio: false                    # 支持音频输入（input_audio 格式）
  video: false                    # 支持视频输入（任何方式）
  native_video: false             # 服务端原生处理视频（vs 仅抽帧）
  # ── 行为控制 ──
  stream_only: false              # 模型要求 stream=true（如 gpt-5.4）
  video_url_passthrough: false    # 远程视频 URL 直接透传给 API（节约流量）
  # ── 容量限制 ──
  context_tokens: 128000          # 上下文窗口 token 数（null=未知）
  max_image_size_mb: 10           # 单张图片大小上限 MB（null=未知）
  max_image_resolution: 8000x8000 # 最大分辨率（null=无固定限制）
  max_images_per_request: null    # 单次请求最大图片数
  max_audio_duration_min: 0       # 最大音频时长分钟（0=不支持）
  max_video_duration_min: 0       # 最大视频时长分钟（0=不支持）
  # ── 格式 ──
  image_formats: [jpeg, png, webp]
  audio_formats: []               # 空=不支持音频
  video_formats: []               # 空=不支持视频
  # ── 描述 ──
  description: 一句话描述
```

### 关键字段注意事项

| 字段 | 影响 | 何时设 true |
|------|------|------------|
| `stream_only` | client.py 直接用 `stream=True` 调用 | 模型返回 "Stream must be set to true" 错误时 |
| `video_url_passthrough` | 远程视频 URL 不下载，直接传给 API | 确认代理能稳定处理远程视频 URL 时 |
| `native_video` | `qsense models` 显示 "video(native)" vs "video(extract)" | 模型/代理支持视频直传（非抽帧） |

### 添加新模型

1. 编辑 `src/qsense/registry.yaml`，追加一条
2. 至少填 `id`、`name`、`vision`，其他可选
3. 重新 `pip install -e .` 后生效
4. 不需要改任何 Python 代码

### 验证新模型

```bash
# 确认注册表加载正常
qsense models

# 测试图像
qsense --model new-model-id --prompt "描述" --image test.png

# 如果需要 stream，加 stream_only: true 再试
# 如果远程视频想透传，加 video_url_passthrough: true 再试
```

## 添加新模态

以添加 "PDF 理解" 为例：

1. 创建 `src/qsense/pdf.py`
   - 定义 `prepare_pdf(source)` → 返回 content part dict
   - 参考 `image.py` 的模式
2. 修改 `cli.py`
   - 添加 `--pdf` option
   - 调用 `prepare_pdf()` 处理
3. 修改 `client.py`
   - `chat()` 参数增加 `pdfs` 或放入 `extras`
4. 修改 `registry.yaml`
   - 给支持 PDF 的模型添加 `pdf: true`
5. 修改 `models.py`
   - `ModelInfo` 增加 `pdf` 字段

## 设计原则

### OpenAI 兼容
所有 API 调用统一走 `openai` Python SDK 的 `chat.completions.create()`。不引入任何 provider 特定 SDK。通过 `base_url` 参数适配不同代理/中转站。

### 三层配置
CLI flags > 环境变量 > `~/.qsense/.env`。确保交互式使用和 agent 自动化场景都能工作。

### 流式降级
默认 `stream=False`。注册表 `stream_only: true` 的模型直接走流式。未注册模型 non-stream 失败且错误含 "stream" 时，自动重试 stream。

### 安全优先
- 配置文件 chmod 600，目录 chmod 700
- .env 写入时过滤换行符（防注入）
- API 异常信息脱敏（不打印完整 exception 避免泄漏 key）
- setup.sh 不 `curl | sh`

### 最小依赖
运行时 6 个包（click, openai, httpx, python-dotenv, Pillow, PyYAML）。ffmpeg 可选。

### 错误优先
所有用户可触发的错误路径都有 `[qsense] ...` 格式消息和 exit 1。不吞异常，不静默失败。

## 已知限制

- 音频 `input_audio` 格式并非所有代理都支持转发
- 视频 URL 透传依赖代理实现，当前默认走下载编码
- 注册表是静态的，不会自动从 API `/models` 端点同步
- 没有 JSON 结构化输出模式
- 不支持对话上下文/多轮
- 不支持音频/视频生成，仅理解
