---
name: grok-chat-consistent-stills
description: >-
  Use this when you need a sequence of AI stills (a short, sketch, or novela
  beat by beat) with the same characters in every image, generated through the
  Grok chat in the browser.
---
# Consistent stills in the Grok chat

Why the chat and not the Imagine page: inside a single conversation Grok carries the characters over from one image to the next. Separate prompts on the Imagine page drift more.

## Recipe
1. Open https://grok.com (already logged in) and start **one** new conversation for the whole episode.
2. The first message only locks the cast and style:
   - One line per character with a fixed look: age (adults always stated), hair, clothes, body type, typical expression. Fruit characters get fruit type, color, eyes, and accessories.
   - Fixed style: photorealistic or 3D, main setting, light, and "vertical 9:16".
   - Ask it to "keep these characters identical in every image of this conversation".
3. Then send one scene per message, in the same conversation: "Generate image for scene XX, vertical 9:16: <action + who + where>". Name the characters by the names you locked.
4. Download each result and save it as `beat-XXs.jpg` in its own folder per episode (e.g. `/home/box/workspace/<project>-stills-chat/`). Downloading needs a native click on the image's download button.
5. If it refuses, soften the wording once. If it still refuses, skip the scene and note it.

## Checks before delivering
- Timestamp and `md5sum` of every file, so nothing stale or duplicated is reused (it has happened).
- Look at a few images: clothing consistency and props that came out wrong (e.g. dollars instead of paper bills). Fix those in the prompt and regenerate just that scene in the same conversation.
- Delivery: every still in one gallery, in order, noting any flaws.

## Timing
About 1 to 2 minutes per image, so roughly 25 minutes for 13 scenes.
