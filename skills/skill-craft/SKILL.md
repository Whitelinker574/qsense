---
name: skill-craft
description: "创建和优化 Agent Skills。当需要构建新 skill、为 skill 设计配套 CLI、改进现有 skill 结构、或优化 skill 的触发率和使用体验时使用。即使用户只是提到想让 agent 学会某个能力，也应该考虑用这个 skill 来设计方案。"
compatibility: "遵循 Agent Skills 标准 (https://agentskills.io)"
---

# Skill Craft — 创建 Agent Skills

一个关于如何造 skill 的 skill。

## 核心理念

Skill 是**知识层**，教 agent 怎么用一个工具。工具（CLI/API/脚本）是**执行层**，负责干活。

```
Skill = 什么时候做、为什么这么做、注意什么
CLI   = 怎么做（skill 的手）
```

CLI 是脚手架，Skill 才是产品。

## Skill 的结构

### 三文件分层

按内容的变化频率分开存放：

```
skills/<name>/
├── SKILL.md              # 很少变。命令语法、输出约定、错误表。
├── scripts/              # 可选。确定性任务的脚本，agent 调用但不需要读源码。
└── references/
    ├── <领域>.md          # 偶尔变。领域知识、能力表、策略。
    └── user-notes.md     # 持续变。agent 自动维护：偏好、经验、教训。
```

**原则：两个信息如果变化频率不同，就不要放在同一个文件里。**

### 三层渐进式加载

1. **元数据**（name + description，~100 词）— 始终在上下文中，用于判断是否触发
2. **SKILL.md 正文**（< 500 行）— 触发后加载
3. **references/ 和 scripts/**  — 按需加载，不占常驻上下文

SKILL.md 每次触发都加载，每个 token 都是成本。能挪走的就挪走。

### SKILL.md 模板

```markdown
---
name: my-skill
description: "做什么。什么时候用。保持 1024 字符以内。"
compatibility: "运行依赖：哪些二进制、可选依赖。"
---

# 标题
一句话说明这个 skill 给 agent 带来什么能力。

## 安装
怎么装。让 CLI 引导 agent 完成配置。

## 快速参考
覆盖所有主要场景的命令示例。

## 使用原则
指向 references/ 文件。只有安全规则留在本文件。

## 输出约定
stdout / stderr / exit code 的规范。

## 错误速查
表格：错误 → 原因 → 修复。

## 持续改进
指向 user-notes.md。告诉 agent 用之前读、用之后更新。
```

### 什么放哪里

| 内容 | 文件 | 原因 |
|------|------|------|
| 命令语法、参数 | SKILL.md | 稳定，每次都需要 |
| 输出格式、exit code | SKILL.md | 约定，很少变 |
| 错误表 | SKILL.md | agent 出错时需要立即查 |
| 安全规则 | SKILL.md | 不可妥协，必须常驻 |
| 模型/能力表 | references/ | 随模型更新而变 |
| 策略决策树 | references/ | 领域知识，不是语法 |
| 重复性操作 | scripts/ | 脚本执行，不占上下文 |
| 成本技巧、最佳实践 | user-notes.md | 随使用经验积累 |
| 用户偏好 | user-notes.md | 每人不同，agent 维护 |
| 工作流模板 | user-notes.md | 起初通用，逐渐个性化 |

## 设计原则

### 1. Description 要"贪心"

Agent 倾向于**欠触发** skill。description 要写得激进，宁可多触发也别漏掉。

```yaml
# 不好 — 太保守，很多相关场景不会触发
description: "创建 Agent Skills 的工具"

# 好 — 主动覆盖相关场景
description: "创建和优化 Agent Skills。当需要构建新 skill、为 skill 设计配套 CLI、
改进现有 skill 结构、或优化 skill 的触发率和使用体验时使用。即使用户只是提到
想让 agent 学会某个能力，也应该考虑用这个 skill 来设计方案。"
```

### 2. 解释 why，不要写 MUST

如果你发现自己在写 ALWAYS 或 NEVER 大写字母，这是一个警告信号。改成解释原因，让 agent 理解意图后自己泛化。

```markdown
# 不好 — 命令式，agent 不知道为什么
MUST: 永远不要在 SKILL.md 中放模型能力表。

# 好 — 解释原因，agent 能举一反三
模型能力表会随模型更新而变，但 SKILL.md 每次都加载。
把会变的内容放在 references/ 里，只在需要时加载，节省上下文。
```

### 3. 让 CLI 自己说话

不要在 skill 里替 CLI 解释配置流程。CLI 的 stderr 和 --help 就是文档。

```bash
# 不好 — skill 里写了 5 行解释
"设置 API key：QSENSE_API_KEY=xxx，base URL：QSENSE_BASE_URL=xxx，
优先级是 CLI 参数 > 环境变量 > ~/.qsense/.env..."

# 好 — skill 里 1 行，CLI 自己输出引导
qsense init    # stderr 会告诉你需要什么
```

CLI 设计要点：
- **结构化错误到 stderr** — agent 解析后决定下一步
- **纯结果到 stdout** — 可管道，不混入元数据
- **Exit code** — 0 成功，1 失败
- **非 TTY 检测** — stdin 不是终端时，打印引导而不是调用 input()

### 4. User-notes：学习而非记录

user-notes.md 是 agent 的记忆文件。设计要点：

- 给触发信号的**框架**，不要给穷举的关键词列表
- 写 "use your judgment"，不要写 if-else
- 给空的分区结构（Preferences / Patterns / Lessons / Workflows），让 agent 自己填
- 用户也可以加自定义触发规则

### 5. 安装引导：给地址，不给平台命令

每个 agent 框架有自己的安装方式。给项目地址和规范链接就够了：

```
安装 xxx 技能，项目地址 https://github.com/user/repo
该 skill 遵循 Agent Skills 标准（https://agentskills.io）。
请使用你所在平台的 skill 安装方式进行安装。
```

### 6. 重复工作抽成脚本

如果 agent 每次使用 skill 时都要写类似的辅助代码，那这段代码应该放进 `scripts/`。
脚本可以直接执行（`python scripts/xxx.py`），不需要加载到上下文中。

## 验证 Skill

### 基础检查清单

- [ ] frontmatter 有 `name` 和 `description`（必需）
- [ ] `name` 全小写，匹配目录名，无连续连字符
- [ ] `description` < 1024 字符，说了"做什么"和"什么时候用"
- [ ] `description` 足够"贪心"，覆盖了边缘场景
- [ ] SKILL.md < 500 行
- [ ] 领域知识在 references/，不在 SKILL.md
- [ ] user-notes.md 存在，有触发框架和空分区
- [ ] CLI 错误到 stderr，结果到 stdout
- [ ] 非 TTY 下 init 有引导而不是崩溃
- [ ] 没有写死平台特定的安装命令
- [ ] 没有不必要的 MUST/NEVER/ALWAYS

### 触发测试

写 3-5 个测试 prompt 验证 skill 能否正确触发：
- 2-3 个应该触发的（包括不太明显的边缘场景）
- 1-2 个不应该触发的（相关但不相关的场景）

如果漏触发多，说明 description 不够"贪心"。如果误触发多，说明 description 边界不清。

## 持续改进

参考 `references/examples.md` 获取实际案例。
每次创建或改进 skill 后，回顾这份清单，看看哪些原则被遗忘了。
