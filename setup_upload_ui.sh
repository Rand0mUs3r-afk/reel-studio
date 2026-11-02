#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3.11}"
command -v "$PYTHON" >/dev/null || { echo 'Install Python 3.11 or set PYTHON to its executable.'; exit 1; }
sudo apt-get update -qq
sudo apt-get install -y blender ffmpeg espeak-ng fonts-dejavu-core python3-venv
"$PYTHON" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --no-cache-dir -r requirements.txt
REEL_STUDIO_HOST_PYTHON="$PWD/.venv/bin/python" blender --background --disable-autoexec --python-exit-code 1 --python render_free3d.py -- --check-deps
.venv/bin/python -m pip install --no-cache-dir torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install --no-cache-dir -r requirements-free3d.txt -r requirements-ui.txt
if [ ! -d .triposr/.git ]; then
  git init .triposr
  git -C .triposr remote add origin https://github.com/VAST-AI-Research/TripoSR.git
fi
git -C .triposr fetch --depth 1 origin 107cefdc244c39106fa830359024f6a2f1c78871
git -C .triposr checkout --detach FETCH_HEAD
printf '\nStart the UI with: .venv/bin/streamlit run upload_app.py\n'
