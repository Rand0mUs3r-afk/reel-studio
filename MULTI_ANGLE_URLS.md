# Multiple product-angle URLs → one ad

Use `streamlit run product_ad_app.py` and paste direct HTTPS image URLs, one per line. For example:

```text
Front | https://your-image-host.example/front.jpg
Left side | https://your-image-host.example/left.jpg
Back | https://your-image-host.example/back.jpg
Right side | https://your-image-host.example/right.jpg
```

These example hosts are placeholders; replace them with accessible photos. Links must return images, not product web pages or login screens. Keep signed query strings intact. A URL without a label receives `Angle 1`, `Angle 2`, etc. Do not paste passwords or private credentials. The downloader accepts public HTTPS port 443 targets only, checks DNS targets and redirects using the existing `studio.fetch` protections, and limits each download to 15 MB. Actual host availability still needs to be tested with your links.

## Order and limits

- One ad uses all supplied angles of the same product, in input order.
- In URL mode, use 1–6 combined uploads and URLs. Uploads come first, followed by URL lines. This cap matches the existing six-scene ad renderer.
- Neutral product-detail scenes are added when necessary so every input is used at least once. Offer and CTA stay at the end. Later scenes may reuse earlier photos.
- A failed URL, non-image response, oversized image or byte-identical duplicate stops generation with an indexed error; inputs are not silently skipped.
- URL mode does not infer unseen sides or combine images into a reconstructed 3D model. It preserves the supplied photos in a designed 2D sequence.
- The pre-existing upload-only path remains available with its original limits; this addition does not alter the experimental 3D renderer or the folder-based workflow.

## GitHub-only operation

Open **Actions → Product Ad From Image URLs → Run workflow**. Paste the URL list into `image_urls`, then fill in the product brief. This is separate from the existing folder-based **Product Photo Ad** workflow. Downloads contain one MP4, scene previews, storyboard, subtitles, caption and `input-angles.json`. The latter records labels and source types, not raw URLs. Scene `photo_index` values map into that manifest.

The workflow uses read-only repository permissions, no provider secrets, and no auto-posting. Download requests reach the image hosts. GitHub workflow inputs may be visible to people with repository/run access; do not treat signed URLs as secret or anonymous. Artifacts contain your product images and videos and expire after seven days. Public repositories/artifacts must not be used for private material. The browser UI does not persist raw URLs in output files, but holds form inputs in its session.

## Tests

```bash
python -m pytest -q tests/test_ad_sources.py
PHOTO_AD_SMOKE=1 python -m pytest -q tests/test_product_ad.py tests/test_ad_sources.py
```

URL tests cover parsing, order, labels, intact query strings, limits, invalid URL shapes and scene coverage without network access. They do not prove live image-host compatibility, Streamlit deployment, or GitHub runner operation. Preview your real angles before rendering.
