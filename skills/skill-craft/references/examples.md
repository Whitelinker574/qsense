# Skill Craft 实战案例

从构建 qsense skill 中提炼的真实模式。

## 案例：三文件演化

一开始所有内容都在 SKILL.md（137 行）。最终拆成：

```
SKILL.md           97 行   →  命令语法、约定、错误表
references/
  models.md        73 行   →  模型能力、策略
  user-notes.md    47 行   →  触发规则、经验、工作流
```

为什么拆：模型表随模型更新而变，用户偏好每次使用都可能变，命令语法几乎不变。变化频率不同 = 分开放。

## 案例：让 CLI 自己说话

改之前（SKILL.md 里写了 5 行）：
```
## 配置
设置 API key（必需）和 base URL。
运行: qsense init --api-key <KEY> --base-url <URL>
或设置环境变量: QSENSE_API_KEY, QSENSE_BASE_URL
优先级: CLI 参数 > 环境变量 > ~/.qsense/.env
```

改之后（SKILL.md 里 1 行）：
```
qsense init    # stderr 会告诉你需要什么——问用户要对应信息
```

CLI 在非 TTY 环境下的输出：
```
[qsense] Non-interactive environment detected. Please provide API key and base URL:
  qsense init --api-key <YOUR_API_KEY> --base-url <YOUR_BASE_URL>
Ask the user for these values.
```

5 行 → 1 行。解释的事交给 CLI。

## 案例：前置检查不啰嗦

```bash
python3 --version               # 需要 Python >= 3.10；没有就让用户装
pipx --version                  # 没有就: brew install pipx (macOS) / apt install pipx (Linux)
pipx install qsense-cli         # 全局安装，不用激活环境
qsense init                     # CLI 引导后续配置
```

agent 逐行执行，哪行失败注释就告诉它怎么办。不需要写说明段落。

## 案例：Description 的贪心写法

保守写法（容易漏触发）：
```yaml
description: "多模态感知 CLI 工具"
```

贪心写法（覆盖边缘场景）：
```yaml
description: "Multimodal perception CLI: send images, audio, or video to an LLM 
and get text back. Use for image recognition, audio transcription, video understanding, 
OCR, and any task where a model needs to see or hear something."
```

关键区别：后者列出了具体用途（OCR、转录、视频理解），还加了兜底语句（"any task where a model needs to see or hear something"）。

## 案例：解释 why 而不是写 MUST

不好：
```markdown
MUST: 永远不要在 SKILL.md 中放模型能力表。
NEVER: 不要在 skill 中写平台特定的安装命令。
```

好：
```markdown
模型能力表会随模型更新而变，但 SKILL.md 每次都加载。
把会变的内容放在 references/ 里，只在需要时加载，节省上下文。

每个 agent 框架有自己的安装方式。给项目地址和规范链接就够了，
agent 知道自己平台怎么装。
```

区别：前者是规则，agent 只能死记硬背。后者是原因，agent 理解后能举一反三应用到类似场景。

## 案例：User-Notes 触发规则

过度指定（不好）：
```
当用户说"用这个模型"、"switch to"、"prefer"、"别用"、
"太慢了"、"too slow"、"faster"、"太贵了"、"cost"时更新...
```

合适的粒度（好）：
```
Common signals -- not exhaustive, use your judgment:
- User corrects your choice
- A command fails and you figure out why
- User expresses a preference
- You notice a recurring pattern
```

前者是关键词匹配，后者是理解意图。agent 不是正则引擎。

## 案例：触发测试设计

为 qsense skill 写的测试 prompt：

应该触发：
- "帮我看看这张截图里有什么错误" → 图片识别
- "把这段会议录音转成文字" → 音频转录
- "这个视频讲了什么" → 视频理解

不应该触发：
- "帮我写一个图片处理脚本" → 写代码，不是感知
- "推荐一个视频编辑软件" → 推荐工具，不是分析内容

如果"帮我看看这张截图"没触发，说明 description 少了 "screenshot" 或 "image recognition" 这类词。
