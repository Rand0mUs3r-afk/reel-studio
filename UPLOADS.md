# Multi-upload + URL browser interface

The upload form is a local Streamlit app, not a file picker inside GitHub Actions. Committing these files does not host a website. GitHub's workflow form has no file-upload input type. The existing single-source GitHub workflow remains unchanged.

Run on Linux/WSL with Python 3.11 and git installed, from your checkout:

```bash
bash setup_upload_ui.sh
.venv/bin/streamlit run upload_app.py
```

The setup installs packages through apt/pip, downloads pinned upstream TripoSR source and creates a local virtual environment. First reconstruction also downloads public model/background-removal weights. No paid API keys or hosted GPU are used. Rendering consumes your own machine's CPU, memory, disk and electricity. Full inference/Blender performance remains experimental.

The UI has two independent sections: multi-file upload (JPG/JPEG/PNG/WebP) and URL lines. Fill either or BOTH. URLs can be direct photos, or enable the product-page checkbox to select one gallery image from each page. Preview the combined queue, then submit all inputs. Duplicate normalized images are removed; invalid inputs are listed rather than silently hidden.

Limits: 8 combined input entries, 15 MB per image, 20 output videos. Example: 3 uploads + 2 URLs, 2 variants each = up to 10 videos. Each unique image is reconstructed separately; this is not multi-view fusion or one merged 3D model. Shared offer, keyword idea, motion, audio and quality settings apply to the batch. Rendering is sequential with one local batch lock.

The UI provides video previews, individual MP4 downloads and an outputs ZIP. Uploaded originals, source URLs, runtime code and render logs are not included in that ZIP. Available model/video outputs from failed items are retained; inspect local render.log to diagnose failures. Batches persist under ignored .upload-jobs; delete the current batch using its button, and remove older batches manually when no longer needed. Ignoring files prevents ordinary git add, not intentional force-add.

The server binds to localhost by default. Do not expose it publicly without authentication/resource limits. Uploads are processed by the local app and are NOT automatically committed to the public GitHub repository or sent to an external inference API. URL images are downloaded from their source sites. Keyword-only idea direction and conservative offer templates remain unchanged.
