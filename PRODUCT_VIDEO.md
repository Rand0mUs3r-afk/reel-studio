# Product image → rotating product ad

Use **Actions → Product Ad Video - Rotation and Presenter Controls → Run workflow**. This replaces the comparison workflow entry point; it renders a real mesh, not photo slideshow variants. The original standalone Free 3D workflow and the existing URL/photo-ad workflows are left unchanged.

## Controls

The form restores source type and source, product gallery image index, variants, duration, video quality, mesh quality, motion, offer, creative keywords, captions, music and voice. It adds product name, explicit rotation, presenter and exact narration script.

- `rotation`: 90, **180 (default)** or 360 degrees. `turntable` turns the model; `orbit` moves the camera. The setting overrides slow/fast angle keywords. The existing reveal motion is compensated so its net angular sweep matches the selection.
- `presenter=voiceover_only`: synthetic narration without a visible character.
- `presenter=visible_humanoid_illustrated`: a visible, original illustrated robot-like humanoid with audio-energy-driven mouth movement and blinking, plus synthetic narration. This is NOT a photorealistic AI person, trained talking-head generation or phoneme-accurate lip sync. It is fully local and does not use paid APIs.
- `voice=off` supports music-only/silent output when presenter is voiceover_only. A visible speaking humanoid requires voice=on; incompatible settings fail before reconstruction.
- `music`: existing procedural original backing, auto/off/on, mixed under narration. It is not a trending/commercial song.
- `narration_text`: exact English script. If blank, product name plus formatted offer are spoken. Speech is basic espeak-ng. A script that exceeds the selected duration is rejected before reconstruction rather than truncated or silently speeding up the rotation.

Start with one variant, ten seconds, preview_360p, mesh 64, turntable, rotation 180, music on, voice on, and the presenter option you want. A procedural bottle demo can exercise the pipeline without reconstructing a real product; it is explicitly NOT derived from your photo.

## What is in the output

Each variant contains `reel.mp4` (final output), original 3D settings and `presentation.json` recording requested rotation, audio/presenter choice, validation and free-only metadata. Narrated variants retain `product-render.mp4` before the voice/presenter pass and `narration.txt`. The visible-character layout contains the full product render in the left portion and a character at the right, rather than placing the character over the product. Base cover images are generated before that presentation pass.

This workflow never silently substitutes a photo zoom video for a failed 3D reconstruction. Failures are run failures; available artifacts are retained for inspection. Existing photo/URL workflows still provide non-3D ads but are not this workflow. Multiple photo URLs are not fused into one mesh here; use a single source image or an existing accurate GLB. Single-photo 3D estimates unknown sides; logos, labels and shape can be wrong. A 180-degree turn is half a revolution, not a view of every surface.

## Cost and validation limits

No paid AI API, provider key, cloud avatar or premium voice is used. GitHub compute/storage limits and any account billing still apply; artifacts expire after seven days and public artifacts are not private. CPU 3D can be slow, especially at 1080p or high mesh resolution.

Ten local tests passed for exact rotation configuration, visible mouth changes, audio envelope extraction, and real FFmpeg muxes for BOTH presentation modes, with and without existing backing audio, using synthetic test audio. Actual espeak-ng speech, Blender geometry rendering, product reconstruction, runner setup and subjective visual quality were not tested in that local environment. The workflow includes a native Blender preflight and runs the presenter tests on its runner. Inspect the real outputs before use.

```bash
python -m pytest -q tests/test_product_video.py
```
