# Skill Craft Examples

Real patterns from building the qsense skill.

## Example: Three-File Evolution

Started with everything in SKILL.md (137 lines). Ended with:

```
SKILL.md           97 lines   →  command syntax, contracts, errors
references/
  models.md        73 lines   →  model capabilities, strategies
  user-notes.md    47 lines   →  triggers, patterns, workflows
```

Why: model tables change when models update. User preferences change every session. Command syntax almost never changes. Different rates of change = different files.

## Example: CLI Speaks for Itself

Before (in SKILL.md):
```
## Configuration
Set your API key and base URL. The API key is required.
Run: qsense init --api-key <KEY> --base-url <URL>
Or set environment variables: QSENSE_API_KEY, QSENSE_BASE_URL
Priority: CLI flags > env vars > ~/.qsense/.env
```

After (in SKILL.md):
```
qsense init    # stderr will tell you what's needed -- ask the user accordingly
```

The CLI's non-TTY output:
```
[qsense] Non-interactive environment detected. Please provide API key and base URL:
  qsense init --api-key <YOUR_API_KEY> --base-url <YOUR_BASE_URL>
Ask the user for these values.
```

5 lines in the skill → 1 line. The CLI does the explaining.

## Example: Prerequisites Without Bloat

```bash
python3 --version               # need Python >= 3.10; if missing, ask user to install
pipx --version                  # if missing: brew install pipx (macOS) / apt install pipx (Linux)
pipx install qsense-cli         # global install, no activation needed
qsense init                     # CLI guides the rest
```

Agent runs each line. If one fails, the comment tells it what to do. No paragraphs of explanation needed.

## Example: User-Notes Triggers

Over-specified (bad):
```
Update when user says "用这个模型", "switch to", "prefer", "别用",
"太慢了", "too slow", "faster", "太贵了", "cost"...
```

Right-sized (good):
```
Common signals -- not exhaustive, use your judgment:
- User corrects your choice
- A command fails and you figure out why
- User expresses a preference
- You notice a recurring pattern
```

## Example: Install Guidance

```
Install the qsense multimodal perception skill from https://github.com/hezi-ywt/qsense
The skill follows the Agent Skills standard (https://agentskills.io).
Install it using your platform's skill installation method.
For example: npx skills add hezi-ywt/qsense
```

One block. Works for any platform. Agent figures out the rest.
