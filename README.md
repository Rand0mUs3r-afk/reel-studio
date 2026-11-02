# Reel Studio — product photo ads

## Recommended: photo-preserving ad mode

Turn 1–8 photos of the same product into one vertical ad: hook → up to three verified benefits → optional exact offer → call to action. Original product images are fitted into the design without cropping or generative reconstruction; mild pan/zoom animates the finished scene cards. This is a designed 2D photo ad, not photorealistic image-to-video, background removal, or new product camera angles. No invented claims, automatic posting, paid API calls, or provider keys.

### Browser upload interface

Install FFmpeg (including ffprobe), DejaVu Sans fonts, and optionally espeak-ng for basic English narration. On Ubuntu:

```bash
sudo apt-get update && sudo apt-get install -y ffmpeg fonts-dejavu-core espeak-ng
python -m pip install -r requirements.txt -r requirements-ui.txt
streamlit run product_ad_app.py
```

Upload photos, fill in product name, brand, hook, verified benefits, exact offer, CTA, brand colors, and optional logo. Preview the scene images/storyboard before generating. Optional music must be your own licensed audio. Narration is basic espeak-ng, not a premium AI voice; text that exceeds the chosen duration is rejected rather than cut off. Outputs include MP4, cover, scene previews, exact timeline, scene-level SRT subtitles, caption text and ffprobe validation. Scene text is burned into the video; the SRT is scene-timed, not word-aligned.

Uploads are processed in temporary local folders and removed after the job; downloadable bytes remain in the browser app session until cleared. The UI has no authentication or job queue: do not expose it publicly without adding access controls and resource limits. Images: 15 MB each, minimum 200×200, maximum 30 million pixels. Logos use the same image limits. Music uploads: 30 MB. Browser output archive: 200 MB maximum.

### GitHub-only generation

Add 1–8 photos to a repository folder such as `inbox`, then open **Actions → Product Photo Ad → Run workflow**. Supply the product details; separate benefits using `|`. Download the artifact after completion. This path does not need Blender, TripoSR, GPU or AI credentials. Standard GitHub compute/storage limits apply. Artifacts expire after seven days. On public repositories, committed inputs and artifacts must not be treated as private. Existing 3D workflows remain separate.

### Command line

```bash
python product_ad.py --photos inbox/front.png inbox/side.png \
  --product 'Your product' --brand 'Your brand' \
  --hook 'Meet your next everyday essential' \
  --benefit 'A verified feature you supplied' \
  --offer 'Your exact promotion and conditions' --cta 'Visit our store' \
  --duration 15 --resolution 720p --output output_ads
```

Add `--preview-only` to create storyboards without FFmpeg. Use a different empty output directory for the full render; existing files are never overwritten. `--logo`, `--background`, `--accent`, `--music` (licensed local audio) and `--voice` are optional. All advertising text comes from the supplied brief and is not independently fact-checked. Photos cycle in upload order across scenes; front/back photos are not fused into a 3D model. Music and voice default off. No brand URL fetching, general natural-language director, auto-posting, avatars, lip sync, or generated footage is added in this mode.

### Tests

```bash
python -m pytest -q tests/test_product_ad.py
PHOTO_AD_SMOKE=1 python -m pytest -q tests/test_product_ad.py
```

The opt-in smoke test encodes a real 15-second 720p H.264 MP4 and probes its duration and dimensions. It does not verify subjective visual quality, the Streamlit deployment or GitHub runner operation. Inspect the preview before using an ad.

## Optional: experimental 3D showcase

The original **Free 3D Product Video - Experimental CPU** workflow remains unchanged. It reconstructs one image into a vertex-colored GLB using CPU TripoSR, then animates real geometry in Blender. Inputs include public image/product URLs, repository images, an existing GLB or procedural demo. Motion options: turntable, orbit, float, reveal. Use `upload_app.py` for its separate batch UI.

This mode is approximate: hidden sides, labels, logos and geometry may be wrong. Vertex colors are not high-resolution texture baking or verified CAD. Start with one five-second preview_360p variant and voice/music off. CPU reconstruction/rendering can be slow; public model downloads and GitHub resource limits apply. Offers use local templates and the idea field understands only documented keywords. No paid-service fallback, premium voice, lip-synced presenter or social posting.

Upstream TripoSR remains pinned by its workflow to `107cefdc244c39106fa830359024f6a2f1c78871`. Preserve its MIT notices and comply with model/dependency licenses: https://github.com/VAST-AI-Research/TripoSR . Artifacts expire after seven days. The legacy slideshow workflow is still disabled; cloud helpers in legacy modules are not used by either free active workflow.
