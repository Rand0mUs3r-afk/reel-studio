# Inbox dropdown: no image filenames to type

In **Actions → Product Ad Video - Rotation and Presenter Controls → Run workflow**, choose `input_mode=inbox` (the new default). Leave `source` blank. All direct files in the repository's `inbox` folder ending in `.jpg`, `.jpeg` or `.png` are discovered automatically, case-insensitively. `.gitkeep`, other file types and nested folders are ignored. Files are processed in case-insensitive filename order; use prefixes such as `01-front.jpg`, `02-side.png` if order matters.

All existing rotation, music, voice, presenter, quality, duration, motion, captions, variants and narration controls remain. They apply to each image. Other input modes remain selectable; they still use the `source` field.

## Inbox output dropdown

- `separate_videos` (default): independently reconstruct and render EVERY matching image. With four images and one variant, expect four final videos if all four succeed.
- `combined_video`: perform the same per-image renders and additionally concatenate corresponding variants into one sequence, in filename order. Four ten-second renders yield approximately forty seconds per combined variant. Narration/music/presenter occur in each segment and can repeat at segment boundaries.

This is NOT multi-view fusion or a guaranteed accurate model inferred jointly from four angles. Each image independently produces an estimated mesh; individual products or different views can therefore look different. Combined mode does not silently exclude failed sources: if any source fails, the combined output is blocked and the run reports failure, while available per-source files remain downloadable.

## Outputs and validation

`output_free3d/inbox-manifest.json` lists every selected source and its status. `source-001`, `source-002`, etc. hold each source's variants, model and `render.log`. Combined outputs are named `combined-variant-01.mp4`, etc. Each source is rendered in an isolated temporary workspace so one source cannot overwrite another source's GLB or videos. Input images are not edited, moved, deleted or committed by this workflow. The output folder must be empty before a local run.

All selected images are validated before reconstruction: valid image content, at least 200 pixels per side, at most 15 MB per file and the existing image pixel safety limit. Symlinks are rejected. Per-source failures are recorded and later images are still attempted. Three-hour per-source and 330-minute overall workflow limits can stop large batches; CPU work grows with number of images × variants. Start with one variant, mesh 64 and preview_360p. No paid API is enabled; GitHub compute/storage limits still apply.

Five local tests passed: supported extension discovery/order, ignored files, invalid/symlink inputs, all-source processing and failure isolation with a stub renderer, refusal to omit failures from combined mode, and a real two-clip FFmpeg concatenation/duration check. Actual Inbox product reconstruction and the full GitHub batch have not been run in the assistant environment.

```bash
python -m pytest -q tests/test_inbox_video.py
python inbox_video.py --input-mode inbox --inbox-output separate_videos --rotation 180 --variants 1 --duration 10 --quality preview_360p --mesh-resolution 64 --voice off
```
