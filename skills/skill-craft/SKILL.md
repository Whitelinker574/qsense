---
name: skill-craft
description: "创建和优化 Agent Skills。当需要构建新 skill、为 skill 设计配套 CLI、改进现有 skill 结构、或优化 skill 的触发率和使用体验时使用。即使用户只是提到想让 agent 学会某个能力，也应该考虑用这个 skill 来设计方案。"
compatibility: "遵循 Agent Skills 标准 (https://agentskills.io)"
---

# Skill Craft — 创建 Agent Skills

一个关于如何造 skill 的 skill。

## 核心理念

Skill 是**知识层**——教 agent 怎么做一件事、为什么这么做、注意什么。

有些 skill 是纯知识（写作规范、代码风格），有些有配套工具（CLI/API/脚本）作为执行层。工具是可选的脚手架，Skill 才是产品。

## 结构

### 分层原则

**两个信息如果变化频率不同，就不要放在同一个文件里。**

```
skills/<name>/
├── SKILL.md              # 很少变。核心知识、规则、约定。
├── scripts/              # 可选。原子脚本，agent 调用但不读源码。
└── references/
    ├── <领域>.md          # 偶尔变。领域知识、能力表、策略。
    └── user-notes.md     # 持续变。agent 维护：偏好、经验、教训。
```

### 三层渐进式加载

| 层 | 内容 | 加载时机 | 预算 |
|----|------|---------|------|
| 元数据 | name + description | 始终在上下文，和所有 skill 竞争注意力 | ~100 词 |
| 正文 | SKILL.md | 触发后加载 | < 500 行 |
| 引用 | references/ + scripts/ | 按需加载 | 不限 |

SKILL.md 每次触发都全量加载，每个 token 都是成本。能挪走的就挪走。

### 什么放哪里

| 内容 | 位置 | 原因 |
|------|------|------|
| 核心知识、安全规则 | SKILL.md | 稳定，不可妥协 |
| 领域知识、策略 | references/ | 随领域演进而变 |
| 确定性操作 | scripts/ | 执行不占上下文 |
| 偏好、经验、教训 | user-notes.md | 持续积累，因人而异 |
| CLI 设计规范 | references/cli-design.md | 有 CLI 时才需要 |

## 设计原则

### 1. Description：贪心且密

Agent 倾向于**欠触发** skill。description 要主动覆盖边缘场景。但有硬约束：

- **< 1024 字符**，超了被截断
- **始终在上下文中**，和所有 skill 竞争注意力
- **是唯一的触发依据**

所以"贪心"不是"长"，是**用最少字符覆盖最大触发面积**。每个词要能拉进一个本来会漏掉的场景。

```yaml
# 太保守 → 漏触发
description: "创建 Agent Skills 的工具"

# 太啰嗦 → 字符浪费在连接词上
description: "这是一个用于创建和优化 Agent Skills 的 skill。
它可以帮助你构建新的 skill，也可以帮助你..."

# 贪心且密 → 每个短语都是独立触发锚点
description: "创建和优化 Agent Skills。当需要构建新 skill、
设计配套 CLI、改进 skill 结构、优化触发率时使用。
即使用户只是提到想让 agent 学会某个能力，也应考虑。"
```

技巧：顿号并列触发词，不用句子展开。末尾加兜底语句覆盖未列出的场景。

### 2. 解释 why，不写 MUST

全大写的 ALWAYS/NEVER 是警告信号。解释原因，agent 理解意图后能自己泛化到类似场景。

```markdown
# 不好 — 死规则，agent 不知道为什么
MUST: 永远不要在 SKILL.md 中放模型能力表。

# 好 — 原因清楚，agent 能举一反三
模型能力表随更新而变，但 SKILL.md 每次触发都加载。
会变的内容放 references/，按需加载，节省上下文。
```

### 3. 不做传声筒

Skill 只写 agent 自己推断不出来的信息。

```markdown
# 不好 — 复述工具自己会输出的内容
"--format 支持 json、csv、text 三种格式，默认 json"

# 好 — 只写 agent 推断不出的决策依据
"批量处理用 csv（下游脚本解析快），单次查看用 text"
```

判断标准：**删掉这段话，agent 跑一次工具后能自己搞清楚吗？** 能 → 删。不能 → 留。

### 4. 让 skill 拥有记忆

user-notes.md 让 skill **越用越好用**——逐渐适应用户的真实场景和习惯。

**写入框架，不写穷举规则：**
- "use your judgment"，不要 if-else 关键词列表
- 给空分区（Preferences / Patterns / Lessons / Workflows），agent 自己填

**记录什么：**
- 用户偏好、执行记录、踩过的坑、用户的修正信号

**渐进式磨合：**
- 定期把反复出现的模式**总结为原则**（具体经验 → 抽象规则）
- 一次不改太多——边际优化不能动摇 skill 核心逻辑
- 不确定的先标记观察，多次验证后再固化
- 模式稳定后可从 user-notes 提升到 references/

Skill 不是静态文档，是持续学习系统。种子内容给方向，agent 使用中填充，用户纠正来校准。

### 5. 安装引导：给地址，不给命令

每个 agent 框架安装方式不同，写死命令只会过时。给项目地址和规范链接，agent 知道自己平台怎么装。

### 6. 确定性操作抽成原子脚本

什么时候该写脚本：
- **重复**：agent 每次都写类似代码（3 次 = 该抽了）
- **确定性**：步骤固定、输入输出明确，不需要判断

设计成**原子操作**——一个脚本做一件事，输入输出清晰：

```bash
# 好 — 原子，agent 自由编排
scripts/extract_frames.py  --video x.mp4 --out frames/
scripts/describe_image.py  --image frame_01.png
scripts/merge_results.py   --dir frames/ --format markdown

# 不好 — 大而全，agent 无法拆分或跳过
scripts/process_video.py   --video x.mp4 --do-everything
```

原子脚本的好处：agent 保留编排权、跨 skill 可复用、独立可测试。

## 验证

### 检查清单

- [ ] `name` + `description` 存在，description < 1024 字符
- [ ] description 足够"贪心"且信息密度高
- [ ] SKILL.md < 500 行，领域知识在 references/
- [ ] user-notes.md 存在，有框架和空分区
- [ ] 没有复述工具自己能传达的信息
- [ ] 没有不必要的 MUST/NEVER/ALWAYS
- [ ] 没有写死平台特定的安装命令
- [ ] 如果有配套 CLI → `references/cli-design.md`

### 触发测试

写 3-5 个 prompt 验证触发：
- 2-3 个应该触发的（含边缘场景）
- 1-2 个不应该触发的（相关但不相关）

漏触发多 → description 不够贪心。误触发多 → 边界不清。

完整评估体系（subagent 并行测试、评分、基准统计、description 自动优化）→ `references/evaluation.md`

## 参考文件

| 类别 | 文件 | 什么时候读 |
|------|------|-----------|
| 评估 | `references/evaluation.md` | 测试或改进 skill 时 |
| CLI | `references/cli-design.md` | skill 有配套 CLI 时 |
| Schema | `references/schemas.md` | 写评估代码时 |
| 案例 | `references/examples.md` | 需要参考模式时 |
| Subagents | `agents/grader.md` `comparator.md` `analyzer.md` | 启动对应 subagent 时 |
| 脚本 | `scripts/run_eval.py` `run_loop.py` 等 | 运行自动化评估时 |
