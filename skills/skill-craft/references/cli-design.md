# 为 Skill 设计配套 CLI

不是每个 skill 都需要 CLI。纯知识型 skill（写作规范、代码风格、设计模式）不需要。当 skill 需要调用外部能力（感知、转换、部署）时，CLI 是执行层。

**什么时候读这个文件：** skill 有配套 CLI 或 API 工具时。

---

## 核心原则：让 CLI 自己说话

不要在 skill 里替 CLI 解释配置流程。CLI 的 stderr 和 --help 就是文档。

```bash
# 不好 — skill 里写了 5 行解释
"设置 API key：QSENSE_API_KEY=xxx，base URL：QSENSE_BASE_URL=xxx，
优先级是 CLI 参数 > 环境变量 > ~/.qsense/.env..."

# 好 — skill 里 1 行，CLI 自己输出引导
qsense init    # stderr 会告诉你需要什么
```

5 行 → 1 行。解释的事交给 CLI。

## CLI 设计要点

### 输出规范

- **结构化错误到 stderr** — agent 解析后决定下一步
- **纯结果到 stdout** — 可管道，不混入元数据
- **Exit code** — 0 成功，1 失败

### 非 TTY 检测

CLI 在 agent 环境下运行时，stdin 不是终端。如果 CLI 调用 `input()`，会 EOFError 崩溃。

```python
# 不好 — 非 TTY 下崩溃
api_key = input("Enter API key: ")

# 好 — 检测环境，输出引导
if sys.stdin.isatty():
    run_interactive_setup()
else:
    click.echo(
        "[tool] Non-interactive environment detected.\n"
        "  tool init --api-key <KEY> --base-url <URL>\n"
        "Ask the user for these values.",
        err=True,
    )
    sys.exit(1)
```

### 前置检查不啰嗦

```bash
python3 --version               # 需要 Python >= 3.10；没有就让用户装
pipx --version                  # 没有就: brew install pipx (macOS) / apt install pipx (Linux)
pipx install my-tool            # 全局安装，不用激活环境
my-tool init                    # CLI 引导后续配置
```

agent 逐行执行，哪行失败注释就告诉它怎么办。不需要写说明段落。

### 安装方式

优先 pipx / npx 等全局安装方式，让用户不用每次激活虚拟环境。

### 安全

- 配置文件 chmod 600
- .env 注入防护
- API 错误响应清洗（不泄露 key）

---

## SKILL.md 中的 CLI 章节模板

如果 skill 有配套 CLI，在 SKILL.md 中应该包含这些章节：

```markdown
## 安装
前置检查 + CLI 安装命令。让 CLI 引导后续配置。

## 快速参考
覆盖所有主要场景的命令示例。

## 输出约定
stdout / stderr / exit code 的规范。

## 错误速查
表格：错误 → 原因 → 修复。
```

### 什么放哪里（CLI 相关内容）

| 内容 | 文件 | 原因 |
|------|------|------|
| 命令语法、参数 | SKILL.md | 稳定，每次都需要 |
| 输出格式、exit code | SKILL.md | 约定，很少变 |
| 错误表 | SKILL.md | agent 出错时需要立即查 |
| 安全规则 | SKILL.md | 不可妥协，必须常驻 |

---

## 验证清单（CLI 部分）

- [ ] CLI 错误到 stderr，结果到 stdout
- [ ] 非 TTY 下 init 有引导而不是崩溃
- [ ] 全局安装可用（pipx / npx），不需要激活环境
- [ ] 配置文件权限正确（chmod 600）
- [ ] API 错误响应不泄露密钥

---

## 实战案例

### 让 CLI 自己说话

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

### 前置检查

CLI 在非 TTY 环境下的输出：
```
[qsense] Non-interactive environment detected. Please provide API key and base URL:
  qsense init --api-key <YOUR_API_KEY> --base-url <YOUR_BASE_URL>
Ask the user for these values.
```

agent 看到这个输出就知道下一步该做什么：问用户要 API key 和 base URL。
