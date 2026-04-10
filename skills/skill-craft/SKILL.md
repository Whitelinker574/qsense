---
name: skill-craft
description: "Create well-designed Agent Skills. Use when building a new skill, designing a CLI that supports a skill, or improving an existing skill's structure."
compatibility: "Follows the Agent Skills standard (https://agentskills.io)."
---

# Skill Craft -- Build Agent Skills

A skill about making skills. This encodes the design philosophy and patterns for building skills that get better over time.

## Core Idea

A skill is a **knowledge layer** that teaches an agent how to use a tool. The tool (CLI, API, script) is the execution layer -- it does things. The skill decides *when*, *why*, and *how* to use it.

```
Skill  = what to do, when to do it, what to watch out for
CLI    = how to do it (the skill's hands)
```

The CLI is scaffolding. The skill is the product.

## Skill Anatomy

### Three-File Split

Split by how often content changes:

```
skills/<name>/
├── SKILL.md              # Rarely changes. Command syntax, output contract, errors.
└── references/
    ├── <domain>.md       # Sometimes changes. Domain knowledge, capability tables, strategies.
    └── user-notes.md     # Always changing. Agent-maintained: preferences, patterns, lessons.
```

**Rule: if two pieces of information change at different rates, they belong in different files.**

SKILL.md is loaded every time -- keep it small. References are loaded on demand.

### SKILL.md Structure

```markdown
---
name: my-skill
description: "What it does. When to use it. Keep under 1024 chars."
compatibility: "Runtime requirements: binaries, optional dependencies."
---

# Title

One-line explanation of what this skill gives the agent.

## Setup
How to install. Let the CLI guide the agent through config.

## Quick Reference
Command examples covering all major use cases.

## Usage Principles
Pointers to references/ files. Only keep security rules inline.

## Output Contract
stdout/stderr/exit code conventions.

## Error Quick Reference
Table: error → cause → fix.

## Continuous Improvement
Point to user-notes.md. Tell agent to read before use, update after.
```

### What Goes Where

| Content | File | Why |
|---------|------|-----|
| Command syntax, flags | SKILL.md | Stable, needed every time |
| Output format, exit codes | SKILL.md | Contract, rarely changes |
| Error table | SKILL.md | Agent needs this on failure |
| Security rules | SKILL.md | Non-negotiable, always loaded |
| Model/capability tables | references/ | Changes when models update |
| Strategy decision trees | references/ | Domain knowledge, not syntax |
| Cost tips, best practices | user-notes.md | Evolves with use |
| User preferences | user-notes.md | Per-user, agent-maintained |
| Workflow templates | user-notes.md | Starts generic, becomes specific |

## Design Principles

### Let the CLI speak for itself

Don't explain in the skill what the CLI already tells the agent:

```bash
# BAD: skill explains every config field
"Set QSENSE_API_KEY to your API key, QSENSE_BASE_URL to..."

# GOOD: skill says run init, CLI explains the rest
qsense init    # stderr will tell you what's needed
```

The CLI's --help, error messages, and stderr output ARE documentation. A well-designed CLI reduces what the skill needs to say.

### CLI design for skills

When building the CLI that supports your skill:

- **Structured errors to stderr** -- agent parses these to decide next steps
- **Plain result to stdout** -- pipe-safe, no metadata mixed in
- **Exit codes** -- 0 success, 1 failure, agent checks this
- **Non-TTY detection** -- when stdin isn't a terminal, print guidance instead of prompting `input()`
- **`--help` is a fallback** -- if the skill doesn't cover it, agent runs `--help`

### User-notes.md: learning, not logging

The agent maintains user-notes.md. Design it for learning, not logging:

```markdown
## Update Triggers

Common signals -- not exhaustive, use your judgment:

- User corrects your choice
- A command fails and you figure out why
- User expresses a preference
- You notice a recurring pattern

User can add custom triggers below:
<!-- Custom triggers: -->

## User Preferences
## Learned Patterns
## Lessons
## Custom Workflows
```

**Key: "use your judgment" -- don't over-specify triggers.** The agent should develop its own sense of what matters for this user.

### Keep SKILL.md under budget

The agentskills.io spec recommends < 5000 tokens for instructions. Every token in SKILL.md is loaded every time. Ask yourself:

- Does the agent need this *every* time? → SKILL.md
- Does the agent need this *sometimes*? → references/
- Will this change as the user uses it? → user-notes.md
- Does the CLI already say this? → nowhere

### Installation: give the URL, not the command

Different agent platforms install skills differently. Don't write platform-specific commands:

```
# GOOD
Install from https://github.com/user/repo
This skill follows the Agent Skills standard (https://agentskills.io).

# BAD
For Claude Code: npx skills add ...
For OpenCode: npx skills add ...
For Cursor: copy .cursor/rules/...
```

The agent knows its own platform.

## Checklist

When reviewing a skill:

- [ ] SKILL.md frontmatter has `name`, `description` (required), `compatibility` (if dependencies exist)
- [ ] `name` matches parent directory, lowercase, no consecutive hyphens
- [ ] `description` < 1024 chars, says what AND when
- [ ] SKILL.md < 5000 tokens
- [ ] Domain knowledge is in references/, not SKILL.md
- [ ] user-notes.md exists with triggers and empty sections
- [ ] CLI errors go to stderr with actionable messages
- [ ] CLI output goes to stdout, pipe-safe
- [ ] Non-TTY init provides guidance instead of crashing
- [ ] No platform-specific install commands hardcoded
