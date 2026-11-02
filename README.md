# Reel Studio — free experimental 3D

Use Actions > Free 3D Product Video - Experimental CPU > Run workflow. No paid inference API, account key or paid GPU is used. The old slideshow workflow is disabled. Standard public-repository runner rules and GitHub resource/storage limits still apply; this is not an unlimited compute service.

First real-image test: input_mode=image_url, source=your public HTTPS product image, variants=1, duration=5, quality=preview_360p, mesh_resolution=64, voice/music=off. Or upload a photo into inbox and choose repository_image with its file path. product_url selects a page image using image_index. This experiment reconstructs one source image per run, then reuses the mesh across variants.

Pipeline: local TripoSR CPU inference -> vertex-colored GLB mesh -> Blender geometry animation -> MP4. No slideshow or paid-service fallback. Downloads of public model weights and a background-removal model are required, but source-photo inference runs on the runner. Higher mesh resolutions and video sizes need more compute.

No-reconstruction smoke test: demo_3d, source empty, one variant, 5 seconds, preview_360p, voice/music off. This renders a procedural 3D bottle, NOT a model inferred from your photo. existing_glb can reuse an exported model after a rendering failure.

Motion: turntable/orbit/float/reveal. main_words uses conservative local offer-sentence templates. reel_idea is a KEYWORD director, not a general language model: orbit/float/reveal/turntable, slow/fast, light background, no music/no voice. Unrecognized details are recorded but not interpreted; an explicit motion dropdown overrides keyword motion. Audio uses synthesized original backing and optional English espeak-ng narration. No lip-synced avatar or premium voice.

Download the free-3d artifact: GLB, MP4 variants, covers, caption/settings/provenance and upstream license where applicable. Available outputs are preserved on failure. Artifact retention: 7 days. Public source photos, logs and artifacts are not private. No automatic social posting.

Experimental: upstream TripoSR code is pinned to 107cefdc244c39106fa830359024f6a2f1c78871; CPU marching cubes uses scikit-image instead of a CUDA extension. Vertex colors are not high-resolution texture baking. Hidden sides, labels and geometry can be wrong; this is not verified CAD. CPU runtime/memory, downloaded checkpoints and Blender integration have NOT been end-to-end verified by the assistant. Start small, inspect results, then refine.

Source: https://github.com/VAST-AI-Research/TripoSR . Preserve its MIT notices and comply with upstream model/dependency licenses. Legacy modules remain for reference but the active free workflow does not call their cloud API helpers or pass provider secrets.
