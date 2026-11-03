# One product input, one comparison batch

Open **Actions → Compare Product Ad Approaches → Run workflow**. Supply one direct HTTPS product image URL (or up to six different angles), product name, and optional verified brief. Run once, then download the comparison artifact. Extract the whole archive and open `comparison.html`; videos reference neighboring files. Machine-readable per-mode status is in `comparison.json`.

## What runs

1. **Intact photo ad:** original photos contained in a designed layout with the supplied hook, benefits, offer and CTA.
2. **Automatic cutout → dark ad:** the same photographed views with their backgrounds removed and a dark design.
3. **Automatic cutout → lighter ad:** the same cutouts in a lighter design. No product relighting or generative background synthesis is claimed.
4. **Optional approximate 3D orbit:** existing CPU TripoSR and Blender pipeline, isolated in a temporary workspace, using ONLY the first photo. Fixed five-second 360p silent preview to limit initial cost. It is not multi-view reconstruction and not a full offer ad. Unknown sides, labels and geometry may be wrong.

The photo ads use the selected 15/30-second duration and 720p/1080p resolution. This comparison is silent so we can judge visuals first; the existing product-ad UI still provides music/voice options. Source angles retain their order. Every supplied angle is used in the photo ads. Cutout failures skip only cutout ads; 3D failures do not erase completed photo ads. Error reports use exception types rather than raw external responses. Inspect the runner for dependency failures; optional installs may fail and produce skipped/failed modes.

## Important boundaries

- No paid inference API, provider key, auto-posting, real-person avatar or lip sync is added.
- This does NOT add photographic AI-generated side/back views or a cloud image-to-video provider. That remains a separate, explicitly approved backend and budget decision; the report states it is not implemented.
- Background removal can damage fine edges, transparency or parts of the product. Inspect previews, logos and labels. Completion does not establish visual fidelity or advertising accuracy.
- The 3D step downloads public pretrained weights and can take hours on CPU. Its subprocess has a three-hour timeout; the manual workflow has a 330-minute limit. GitHub resource/storage charges and limits can still apply even without paid inference APIs.
- Inputs must be direct public HTTPS images, not product webpages. All inputs must load; duplicates/failures are not silently skipped. Network requests reach the image hosts. Do not use private credentials or treat workflow inputs as secret.
- Generated artifacts contain product images and videos; public repositories/artifacts are not private. Retention: seven days. The downloaded 3D outputs include existing upstream license notices where applicable.
- Other workflows and the current upload UI remain unchanged. This is a separate comparison action, not a public web deployment.

## Local CLI

```bash
python comparison_suite.py --photos inbox/front.png --product 'Your product' \
  --offer 'Your exact offer' --output output_comparison
```

Use `--urls-file angles.txt` instead of `--photos` for labelled URL lines. Add `--preview-only` for scene images without 2D encoding or 3D, or `--include-3d` to attempt the approximate model showcase. Install base repository requirements and FFmpeg/DejaVu fonts. Cutouts require rembg/ONNX Runtime; 3D requires the existing pinned TripoSR checkout and CPU dependencies plus Blender. Use an empty output directory; previous comparisons are not overwritten.

## Validation

```bash
python -m pytest -q tests/test_comparison_suite.py
PHOTO_AD_SMOKE=1 python -m pytest -q tests/test_product_ad.py tests/test_ad_sources.py tests/test_comparison_suite.py
```

New report tests cover failure isolation, safe status reporting, HTML escaping and explicit unimplemented-paid-generation metadata. They do not run pretrained segmentation, reconstruction, Blender, live URLs, or GitHub Actions. The pre-existing opt-in photo-ad smoke test encodes a real video. A real product input and runner test are still required before assessing results.
