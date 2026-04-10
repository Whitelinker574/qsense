# Skill 评估与测试

完整的 skill 评估体系：从测试用例到基准统计到 description 优化。

---

## 运行和评估测试

这是一个连续的流程——不要中途停下来。把结果放在 `<skill-name>-workspace/` 作为 skill 目录的兄弟目录。在 workspace 内按迭代组织（`iteration-1/`、`iteration-2/` 等），每个测试用例一个目录（`eval-0/`、`eval-1/` 等）。

### 第 1 步：同时启动所有运行（有 skill + 基线）

对每个测试用例，在**同一个回合**启动两个 subagent——一个带 skill，一个不带。不要先启动带 skill 的再回来做基线。一起启动这样它们差不多同时完成。

**带 skill 运行：**
```
执行这个任务：
- Skill 路径: <path-to-skill>
- 任务: <eval prompt>
- 输入文件: <eval files 如果有，否则 "none">
- 保存输出到: <workspace>/iteration-<N>/eval-<ID>/with_skill/outputs/
- 要保存的输出: <用户关心的东西>
```

**基线运行**（取决于场景）：
- **创建新 skill**: 不用任何 skill。同样的 prompt，没有 skill 路径，保存到 `without_skill/outputs/`
- **改进现有 skill**: 用旧版本。编辑前先快照 skill（`cp -r`），然后让基线 subagent 指向快照

为每个测试用例写一个 `eval_metadata.json`（断言可以先为空）。

### 第 2 步：运行进行中时，起草断言

不要干等运行完成。起草定量断言并向用户解释。好的断言是**客观可验证的**且有**描述性名称**。

主观的 skill（写作风格、设计质量）更适合定性评估——不要强行把断言加到需要人类判断的东西上。

更新 `eval_metadata.json` 和 `evals/evals.json`。

### 第 3 步：运行完成时，捕获计时数据

每个 subagent 任务完成时，通知中包含 `total_tokens` 和 `duration_ms`。**立即保存**到 `timing.json`——这是捕获这些数据的唯一机会。

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

### 第 4 步：评分、聚合、启动查看器

所有运行完成后：

1. **评分每个运行** — 启动评分 subagent，读取 `agents/grader.md`，评估每个断言。保存到 `grading.json`。expectations 数组**必须**使用字段 `text`、`passed`、`evidence`。对可以编程检查的断言，写脚本而非目测。

2. **聚合为基准** — 运行聚合脚本：
   ```bash
   python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>
   ```
   产出 `benchmark.json` 和 `benchmark.md`，包含 pass_rate、time、tokens 的 mean +/- stddev 和 delta。

3. **分析师审查** — 读取基准数据，发现聚合统计可能隐藏的模式。参见 `agents/analyzer.md`——比如两种配置都 100% 通过的断言（无区分力）、高方差 eval（可能不稳定）、时间/token 权衡。

4. **告诉用户** 结果已准备好，定量和定性都可以查看。

### 第 5 步：读取反馈

用户完成后读取反馈。空反馈意味着用户觉得没问题。把改进集中在用户有具体意见的测试用例上。

---

## 改进 Skill

### 如何思考改进

1. **从反馈中泛化**。你和用户只在几个例子上迭代是为了快速移动。但如果 skill 只对这些例子有效，它就没用。不要放入过拟合的修补或压迫性的 MUST，如果有顽固的问题，试试不同的隐喻或推荐不同的工作模式。

2. **保持精简**。删掉没有贡献的内容。阅读执行记录（不只是最终输出）——如果 skill 让模型浪费大量时间做无用的事，试着删掉导致这种情况的部分。

3. **解释 why**。尽力解释你要求模型做每件事背后的 **why**。如果你发现自己在写全大写的 ALWAYS 或 NEVER，这是黄旗——重新框定并解释推理。

4. **发现重复工作**。阅读测试运行的记录，注意 subagent 是否都独立写了类似的辅助脚本。如果 3 个测试用例都让 subagent 写了 `create_docx.py`，那就该把这个脚本放进 `scripts/`。

### 迭代循环

改进 skill 后：

1. 应用改进
2. 重新运行所有测试用例到新的 `iteration-<N+1>/` 目录，包含基线运行
3. 启动查看器（如果有），指向上一次迭代
4. 等待用户审查
5. 读取新反馈，再次改进，重复

持续直到：
- 用户满意
- 反馈全为空（一切看起来不错）
- 不再有实质性进展

---

## 高级：盲比较

需要更严格的比较时（例如"新版本真的更好吗？"），使用盲比较系统。读取 `agents/comparator.md` 和 `agents/analyzer.md`。基本思路：把两个输出给独立 agent，不告诉它哪个是哪个，让它判断质量。然后分析为什么获胜者赢了。

这是可选的，需要 subagent，大多数用户不需要。人工审查循环通常就够了。

---

## Description 优化

description 是决定 Claude 是否调用 skill 的主要机制。创建或改进 skill 后，提议优化 description 以提高触发准确率。

### 第 1 步：生成触发测试查询

创建 20 个 eval 查询——should-trigger 和 should-not-trigger 的混合。保存为 JSON：

```json
[
  {"query": "用户 prompt", "should_trigger": true},
  {"query": "另一个 prompt", "should_trigger": false}
]
```

查询必须**真实具体**——像真正的用户会输入的那样。包含文件路径、个人上下文、列名、公司名。有些可能是小写的、有缩写或错别字。混合不同长度，**聚焦边缘情况**而非清晰的例子。

**不好**：`"格式化数据"`、`"从 PDF 提取文本"`
**好**：`"我老板刚发了个 xlsx 文件（在我下载目录里，叫什么 'Q4 销售 final 最终版 v2.xlsx'），她要我加一列算利润率百分比。收入在 C 列成本在 D 列"`

**should-trigger (8-10 个)**：不同措辞的相同意图、用户没有显式命名 skill 的情况、不常见的用例。
**should-not-trigger (8-10 个)**：**近似场景**——共享关键词但需要不同处理。避免明显不相关的（太容易了，没有区分力）。

### 第 2 步：与用户确认

把 eval 集展示给用户审查。用户可以编辑查询、切换 should_trigger、添加/删除条目。这一步很重要——坏的查询会产出坏的 description。

### 第 3 步：运行优化循环

告诉用户这需要一些时间，然后在后台运行：

```bash
python -m scripts.run_loop \
  --eval-set <path-to-trigger-eval.json> \
  --skill-path <path-to-skill> \
  --model <当前会话的模型 ID> \
  --max-iterations 5 \
  --verbose
```

脚本自动处理完整优化循环：把 eval 集分成 60% 训练和 40% 留出测试，评估当前 description（每个查询运行 3 次获得可靠触发率），然后调用 Claude（带扩展思考）提出改进。按测试分数（而非训练分数）选择最佳，防止过拟合。

### 触发机制原理

理解触发机制有助于设计更好的查询。Skill 出现在 Claude 的 `available_skills` 列表中，Claude 根据 description 决定是否查阅。重要的是：Claude 只为**它不能轻易独自处理**的任务查阅 skill——简单的一步查询（如"读这个 PDF"）即使 description 完美匹配也可能不触发。复杂的、多步骤的、专业的查询在 description 匹配时可靠触发。

### 第 4 步：应用结果

取 JSON 输出中的 `best_description` 更新 skill 的 SKILL.md frontmatter。向用户展示前后对比和分数。

---

## Subagent 和脚本索引

`agents/` 目录包含专门 subagent 的指令。需要启动相关 subagent 时阅读它们：

- `agents/grader.md` — 如何评估断言是否满足
- `agents/comparator.md` — 如何做盲 A/B 比较
- `agents/analyzer.md` — 如何分析为什么一个版本胜出

`scripts/` 目录有评估自动化脚本：

- `scripts/run_eval.py` — 测试 description 触发率
- `scripts/run_loop.py` — 运行 eval + 改进循环
- `scripts/improve_description.py` — 基于 eval 结果改进 description
- `scripts/aggregate_benchmark.py` — 聚合运行结果为基准统计

`references/` 目录有额外文档：

- `references/schemas.md` — evals.json、grading.json 等的 JSON 结构
- `references/examples.md` — 实战案例
