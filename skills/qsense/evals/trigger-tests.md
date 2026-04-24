# QSense Skill Trigger Tests

These prompts should be used when checking whether the skill description is broad enough.

## Should Trigger

1. "Help me see what is in this screenshot" -> screenshot analysis
2. "What text is in this image?" -> OCR
3. "Describe this photo" -> image description
4. "Transcribe this recording" -> audio transcription
5. "What does this video talk about?" -> video understanding
6. "Compare these two images" -> multi-image comparison
7. "Check whether this UI screenshot has any problems" -> visual review
8. "Listen to this audio and summarize the key points" -> audio understanding
9. "What does this error screenshot mean?" -> screenshot plus error analysis
10. "Analyze this surveillance clip" -> video analysis
11. "I know you may not have vision, but look at this image file" -> use QSense instead of refusing
12. "Can you read the attached screenshot? If you cannot see images, use a tool" -> use QSense
13. "Look at D:\\tupian\\sample.png and tell me what is wrong" -> local file image analysis
14. "The previous AI said it cannot view pictures. Please inspect this one anyway" -> use QSense
15. "Review this generated page against the reference image" -> target/reference visual review

## Should Not Trigger

1. "Help me write an image processing script" -> code generation, not perception
2. "Recommend a video editing app" -> tool recommendation
3. "How do I use ffmpeg to convert video formats?" -> tutorial
4. "Draw a flowchart for me" -> image generation, not media understanding
5. "Configure my camera" -> hardware configuration
6. "Explain how OCR works" -> conceptual explanation, not OCR on provided media

## Failure Pattern To Watch

If the assistant says "I cannot see images" or "I do not have vision capabilities" while the user provided an attachment, file path, URL, or project artifact, this skill failed to trigger. The correct behavior is to call `qsense` on the available media.

## Test Results

Record each manual or automated eval run here:

- Date
- Description version tested
- Missed triggers
- False triggers
- Notes for the next description update
