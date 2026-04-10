# JSON Schema 定义

skill-craft 评估系统使用的 JSON 结构定义。

---

## evals.json

定义 skill 的测试用例。位于 `evals/evals.json`。

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "用户的示例 prompt",
      "expected_output": "预期结果的描述",
      "files": ["evals/files/sample1.pdf"],
      "expectations": [
        "输出包含 X",
        "skill 使用了脚本 Y"
      ]
    }
  ]
}
```

**字段说明：**
- `skill_name`: 与 skill frontmatter 的 name 匹配
- `evals[].id`: 唯一整数标识符
- `evals[].prompt`: 要执行的任务
- `evals[].expected_output`: 人类可读的成功描述
- `evals[].files`: 可选，输入文件路径列表（相对于 skill 根目录）
- `evals[].expectations`: 可验证断言列表

---

## trigger-eval.json

Description 触发测试的查询集。用于 `scripts/run_eval.py`。

```json
[
  {"query": "帮我看看这张截图里有什么错误", "should_trigger": true},
  {"query": "帮我写一个图片处理脚本", "should_trigger": false}
]
```

**查询设计原则：**
- 查询要**真实具体**，包含细节（文件路径、上下文背景）
- 不要太简短笼统（"处理数据"、"从 PDF 提取"太泛）
- should-trigger (8-10 个)：覆盖不同措辞、不同意图、边缘场景
- should-not-trigger (8-10 个)：**近似场景**，共享关键词但需要不同处理
- 避免明显不相关的负例（"写斐波那契函数"对 PDF skill 没有区分力）

---

## eval_metadata.json

每个测试用例的元数据。位于 `<workspace>/iteration-N/eval-ID/eval_metadata.json`。

```json
{
  "eval_id": 0,
  "eval_name": "descriptive-name-here",
  "prompt": "用户的任务 prompt",
  "assertions": [
    "输出包含正确的名称",
    "使用了指定的模型"
  ]
}
```

---

## grading.json

评分 agent 的输出。位于 `<run-dir>/grading.json`。

```json
{
  "expectations": [
    {
      "text": "输出包含名称 'John Smith'",
      "passed": true,
      "evidence": "在执行记录第 3 步找到：'提取的名称：John Smith'"
    }
  ],
  "summary": {
    "passed": 2,
    "failed": 1,
    "total": 3,
    "pass_rate": 0.67
  },
  "execution_metrics": {
    "tool_calls": { "Read": 5, "Write": 2, "Bash": 8 },
    "total_tool_calls": 15,
    "total_steps": 6,
    "errors_encountered": 0,
    "output_chars": 12450,
    "transcript_chars": 3200
  },
  "timing": {
    "executor_duration_seconds": 165.0,
    "grader_duration_seconds": 26.0,
    "total_duration_seconds": 191.0
  },
  "claims": [
    {
      "claim": "表单有 12 个可填字段",
      "type": "factual",
      "verified": true,
      "evidence": "在 field_info.json 中计数了 12 个字段"
    }
  ],
  "user_notes_summary": {
    "uncertainties": [],
    "needs_review": [],
    "workarounds": []
  },
  "eval_feedback": {
    "suggestions": [],
    "overall": "断言覆盖充分，无额外建议。"
  }
}
```

**重要**：expectations 数组必须使用字段 `text`、`passed`、`evidence`（不是 `name`/`met`/`details`）——查看器依赖这些确切的字段名。

---

## timing.json

运行的时钟计时。位于 `<run-dir>/timing.json`。

**如何捕获**：当 subagent 任务完成时，任务通知包含 `total_tokens` 和 `duration_ms`。立即保存——它们不会持久化到其他地方。

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

---

## metrics.json

执行 agent 的输出。位于 `<run-dir>/outputs/metrics.json`。

```json
{
  "tool_calls": { "Read": 5, "Write": 2, "Bash": 8 },
  "total_tool_calls": 18,
  "total_steps": 6,
  "files_created": ["filled_form.pdf", "field_values.json"],
  "errors_encountered": 0,
  "output_chars": 12450,
  "transcript_chars": 3200
}
```

---

## benchmark.json

基准测试的聚合结果。

```json
{
  "metadata": {
    "skill_name": "my-skill",
    "skill_path": "/path/to/skill",
    "executor_model": "claude-sonnet-4-20250514",
    "timestamp": "2026-01-15T10:30:00Z",
    "evals_run": [1, 2, 3],
    "runs_per_configuration": 3
  },
  "runs": [
    {
      "eval_id": 1,
      "eval_name": "test-name",
      "configuration": "with_skill",
      "run_number": 1,
      "result": {
        "pass_rate": 0.85,
        "passed": 6,
        "failed": 1,
        "total": 7,
        "time_seconds": 42.5,
        "tokens": 3800,
        "tool_calls": 18,
        "errors": 0
      },
      "expectations": [
        {"text": "...", "passed": true, "evidence": "..."}
      ],
      "notes": []
    }
  ],
  "run_summary": {
    "with_skill": {
      "pass_rate": {"mean": 0.85, "stddev": 0.05, "min": 0.80, "max": 0.90},
      "time_seconds": {"mean": 45.0, "stddev": 12.0, "min": 32.0, "max": 58.0},
      "tokens": {"mean": 3800, "stddev": 400, "min": 3200, "max": 4100}
    },
    "without_skill": {
      "pass_rate": {"mean": 0.35, "stddev": 0.08, "min": 0.28, "max": 0.45},
      "time_seconds": {"mean": 32.0, "stddev": 8.0, "min": 24.0, "max": 42.0},
      "tokens": {"mean": 2100, "stddev": 300, "min": 1800, "max": 2500}
    },
    "delta": {
      "pass_rate": "+0.50",
      "time_seconds": "+13.0",
      "tokens": "+1700"
    }
  },
  "notes": [
    "断言 '输出是 PDF 文件' 在两种配置中都 100% 通过——可能无法区分 skill 价值"
  ]
}
```

**重要**：查看器直接读取这些字段名。使用 `config` 而非 `configuration`，或把 `pass_rate` 放在 run 的顶层而非嵌套在 `result` 下，会导致查看器显示空/零值。

---

## comparison.json

盲比较器的输出。位于 `<grading-dir>/comparison-N.json`。

```json
{
  "winner": "A",
  "reasoning": "输出 A 提供了完整解决方案...",
  "rubric": {
    "A": {
      "content": { "correctness": 5, "completeness": 5, "accuracy": 4 },
      "structure": { "organization": 4, "formatting": 5, "usability": 4 },
      "content_score": 4.7,
      "structure_score": 4.3,
      "overall_score": 9.0
    },
    "B": { "...": "..." }
  },
  "output_quality": {
    "A": { "score": 9, "strengths": ["..."], "weaknesses": ["..."] },
    "B": { "score": 5, "strengths": ["..."], "weaknesses": ["..."] }
  },
  "expectation_results": {
    "A": { "passed": 4, "total": 5, "pass_rate": 0.80, "details": [] },
    "B": { "passed": 3, "total": 5, "pass_rate": 0.60, "details": [] }
  }
}
```

---

## analysis.json

事后分析器的输出。位于 `<grading-dir>/analysis.json`。

```json
{
  "comparison_summary": {
    "winner": "A",
    "winner_skill": "path/to/winner/skill",
    "loser_skill": "path/to/loser/skill",
    "comparator_reasoning": "比较器选择获胜者的原因简述"
  },
  "winner_strengths": ["..."],
  "loser_weaknesses": ["..."],
  "instruction_following": {
    "winner": { "score": 9, "issues": [] },
    "loser": { "score": 6, "issues": ["..."] }
  },
  "improvement_suggestions": [
    {
      "priority": "high",
      "category": "instructions",
      "suggestion": "...",
      "expected_impact": "..."
    }
  ],
  "transcript_insights": {
    "winner_execution_pattern": "...",
    "loser_execution_pattern": "..."
  }
}
```

---

## history.json

改进模式中的版本追踪。位于 workspace 根目录。

```json
{
  "started_at": "2026-01-15T10:30:00Z",
  "skill_name": "my-skill",
  "current_best": "v2",
  "iterations": [
    {
      "version": "v0",
      "parent": null,
      "expectation_pass_rate": 0.65,
      "grading_result": "baseline",
      "is_current_best": false
    },
    {
      "version": "v2",
      "parent": "v1",
      "expectation_pass_rate": 0.85,
      "grading_result": "won",
      "is_current_best": true
    }
  ]
}
```
