# QSense User Notes

This file is maintained by the agent. Read it before using qsense, update it when you learn something worth remembering.

## Update Triggers

Common signals -- not exhaustive, use your judgment:

- User corrects your choice (model, parameters, prompt style)
- A command fails and you figure out why
- User expresses a preference (language, detail level, speed vs quality)
- You notice a recurring pattern or workflow
- Something surprising happens (unexpected model behavior, edge case)

User can add custom triggers below:

<!-- Custom triggers: -->

## User Preferences

## Learned Patterns

- Large images waste tokens. `--max-size 1024` is a good starting point for OCR / layout checks.
- Video is expensive. `--video-extract --fps 0.5 --max-frames 10` is cheaper than direct passthrough for quick summaries.
- Multiple `--image` in one call is cheaper than looping single-image calls.

## Lessons

## Custom Workflows

Starter patterns -- replace with the user's actual workflows over time:

```bash
# Batch images
for img in screenshots/*.png; do
  qsense --prompt "any errors?" --image "$img"
done

# Long video: split then analyze
ffmpeg -i long.mp4 -segment_time 60 -f segment seg_%03d.mp4
for seg in seg_*.mp4; do
  qsense --prompt "summarize" --video "$seg"
done

# Capture result for downstream use
result=$(qsense --prompt "extract text" --image doc.png)
```
