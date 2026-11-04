"""Automated Veo video generation for product turntable commercials with ambient audio."""
import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path
from urllib.request import Request, urlopen
import numpy as np

ROOT = Path(__file__).resolve().parent
EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}


def discover_images(folder_path):
    folder = Path(folder_path).resolve()
    if not folder.is_dir():
        return []
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS],
        key=lambda p: (p.name.casefold(), p.name)
    )


def generate_ambient_music(output_path, duration_seconds=8.0):
    rate = 22050
    t = np.arange(int(rate * duration_seconds)) / rate
    chord_freqs = [87.31, 103.83, 130.81, 155.56, 196.00]
    audio = np.zeros_like(t, dtype=float)
    for i, freq in enumerate(chord_freqs):
        lfo = 0.6 + 0.4 * np.sin(2 * np.pi * (0.10 + 0.04 * i) * t)
        audio += (0.15 / (i + 1)**0.5) * np.sin(2 * np.pi * freq * t) * lfo
    fade = np.minimum(1.0, t / 1.5) * np.minimum(1.0, (duration_seconds - t) / 1.5)
    audio *= fade
    with wave.open(str(output_path), 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes((np.clip(audio, -1, 1) * 32767).astype('<i2').tobytes())


def call_veo_api(image_path, prompt, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/veo-2.0-generate-video:predictLongRunning?key={api_key}"
    with open(image_path, "rb") as f:
        b64_image = base64.b64encode(f.read()).decode("utf-8")
    mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"

    payload = {
        "instances": [{
            "prompt": prompt,
            "image": {"bytesBase64Encoded": b64_image, "mimeType": mime}
        }],
        "parameters": {
            "aspectRatio": "9:16",
            "sampleCount": 1,
            "durationSeconds": 8
        }
    }

    req = Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urlopen(req) as resp:
        op = json.loads(resp.read().decode("utf-8"))
    
    op_name = op.get("name")
    if not op_name:
        raise RuntimeError(f"Failed to start video generation: {op}")

    print(f"Generation started: {op_name}. Waiting for completion...")
    check_url = f"https://generativelanguage.googleapis.com/v1beta/{op_name}?key={api_key}"
    for _ in range(60):
        time.sleep(10)
        with urlopen(check_url) as poll_resp:
            status = json.loads(poll_resp.read().decode("utf-8"))
        if status.get("done"):
            if "error" in status:
                raise RuntimeError(status["error"])
            res = status.get("response", {})
            videos = res.get("generatedVideos", []) or res.get("videos", [])
            if not videos:
                raise RuntimeError("No video returned from model.")
            video_uri = videos[0].get("video", {}).get("uri") or videos[0].get("uri")
            with urlopen(f"{video_uri}&key={api_key}" if "?" in video_uri else f"{video_uri}?key={api_key}") as v_resp:
                return v_resp.read()
    raise TimeoutError("Veo video generation timed out.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-folder', default='inbox')
    parser.add_argument('--output-dir', default='output/veo_turntable')
    parser.add_argument('--prompt', default=(
        "Commercial product video. The sleek product rotates smoothly and continuously 360 degrees on a "
        "circular dark studio turntable disk pedestal. Subtle radial lights and reflections glide across the surface. "
        "Dark luxury studio environment with gentle vapor wisps and volumetric lighting. Photorealistic 3D render quality."
    ))
    parser.add_argument('--music', default='on', choices=['on', 'off'])
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable required.", file=sys.stderr)
        sys.exit(1)

    images = discover_images(args.input_folder)
    if not images:
        print(f"No product images found in {args.input_folder}", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    product_img = images[0]
    print(f"Generating turntable video from {product_img.name} using Veo...")

    raw_video_bytes = call_veo_api(product_img, args.prompt, api_key)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        raw_video_path = tmp_dir / "raw.mp4"
        raw_video_path.write_bytes(raw_video_bytes)

        final_video_path = out_path / "product_turntable_commercial.mp4"
        if args.music == 'on':
            audio_path = tmp_dir / "ambient.wav"
            generate_ambient_music(audio_path, duration_seconds=8.0)
            subprocess.run([
                "ffmpeg", "-y", "-i", str(raw_video_path), "-i", str(audio_path),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                "-movflags", "+faststart", str(final_video_path)
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        else:
            final_video_path.write_bytes(raw_video_bytes)

    print(f"Successfully generated product commercial: {final_video_path}")


if __name__ == "__main__":
    main()
