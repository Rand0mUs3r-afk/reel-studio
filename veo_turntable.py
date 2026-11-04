"""Automated Veo video generation for vape product commercials with 5 distinct non-repeating variants."""
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
STATE_FILE = ROOT / '.vape_variant_history.json'

VAPE_VARIANTS = [
    {
        "id": "minimalist_dark_studio",
        "name": "Minimalist Dark Luxury Studio",
        "prompt": (
            "Commercial vape product video. The sleek modern vape device rotates smoothly and continuously "
            "360 degrees on a circular brushed-metal turntable disk pedestal. Subtle radial rim lights, soft reflections "
            "gliding over the glossy and metallic chassis, elegant dark studio backdrop with gentle slow-rising vapor wisps, "
            "photorealistic 3D render, cinematic lighting."
        ),
        "chord_root": 110.0,
    },
    {
        "id": "subzero_glacier_ice",
        "name": "Sub-Zero Glacial Ice & Frost Mist",
        "prompt": (
            "Commercial vape product video. The sleek vape rotates smoothly 360 degrees on an illuminated ice-crystal "
            "turntable pedestal surrounded by crystal clear glacial water, floating ice cubes, and frosty cold vapor smoke. "
            "Crisp cyan and deep blue reflections, photorealistic 3D product commercial."
        ),
        "chord_root": 87.31,
    },
    {
        "id": "neon_nightclub_party",
        "name": "Neon Cyberclub & Laser Glow",
        "prompt": (
            "Commercial vape product video. The vibrant vape device rotates smoothly on a sleek circular glass turntable "
            "with ambient neon magenta and electric blue rim lights. Dark futuristic club atmosphere with soft hazy vapor trails "
            "and dynamic colorful reflections sweeping across the vape surface."
        ),
        "chord_root": 130.81,
    },
    {
        "id": "candy_clouds_dream",
        "name": "Pastel Candy Clouds & Sweet Mist",
        "prompt": (
            "Commercial vape product video. The stylish colorful vape device slowly turns and rotates on a smooth pastel pedestal "
            "suspended in dreamy pink and lavender cotton candy clouds with gentle crystalline sparkle particles and soft swirling vapor. "
            "Bright, playful luxury commercial aesthetic, photorealistic 3D quality."
        ),
        "chord_root": 146.83,
    },
    {
        "id": "deep_water_splash",
        "name": "Deep Aqua Splash & Floating Citrus",
        "prompt": (
            "Commercial vape product video. The modern waterproof vape device smoothly rotates 360 degrees surrounded by suspended "
            "crystal water droplets, fresh fruit slices, effervescent bubbles, and cool swirling vapor. Volumetric caustics and "
            "vibrant turquoise studio lighting."
        ),
        "chord_root": 98.00,
    },
]


def load_next_variant(requested_index=None):
    if requested_index is not None and 0 <= requested_index < len(VAPE_VARIANTS):
        return requested_index, VAPE_VARIANTS[requested_index]

    history = {"last_index": -1}
    if STATE_FILE.is_file():
        try:
            history = json.loads(STATE_FILE.read_text())
        except Exception:
            pass

    next_index = (history.get("last_index", -1) + 1) % len(VAPE_VARIANTS)
    try:
        STATE_FILE.write_text(json.dumps({"last_index": next_index, "variant_id": VAPE_VARIANTS[next_index]["id"]}))
    except Exception:
        pass
    return next_index, VAPE_VARIANTS[next_index]


def discover_images(folder_path):
    folder = Path(folder_path).resolve()
    if not folder.is_dir():
        return []
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS],
        key=lambda p: (p.name.casefold(), p.name)
    )


def generate_ambient_music(output_path, root_freq, duration_seconds=8.0):
    rate = 22050
    t = np.arange(int(rate * duration_seconds)) / rate
    multipliers = [1.0, 1.25, 1.5, 1.875, 2.25]
    audio = np.zeros_like(t, dtype=float)
    for i, m in enumerate(multipliers):
        freq = root_freq * m
        lfo = 0.6 + 0.4 * np.sin(2 * np.pi * (0.10 + 0.03 * i) * t)
        audio += (0.14 / (i + 1)**0.5) * np.sin(2 * np.pi * freq * t) * lfo
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

    print(f"Veo task started: {op_name}. Polling status...")
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
    parser.add_argument('--variant', type=int, default=None, help='Force a specific variant index (0 to 4)')
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

    var_idx, variant = load_next_variant(args.variant)
    print(f"Selected Vape Variant [{var_idx + 1}/5]: {variant['name']}")

    out_path = Path(args.output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    product_img = images[0]
    print(f"Generating video from {product_img.name}...")

    raw_video_bytes = call_veo_api(product_img, variant["prompt"], api_key)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        raw_video_path = tmp_dir / "raw.mp4"
        raw_video_path.write_bytes(raw_video_bytes)

        final_video_path = out_path / f"vape_{variant['id']}.mp4"
        if args.music == 'on':
            audio_path = tmp_dir / "ambient.wav"
            generate_ambient_music(audio_path, root_freq=variant["chord_root"], duration_seconds=8.0)
            subprocess.run([
                "ffmpeg", "-y", "-i", str(raw_video_path), "-i", str(audio_path),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                "-movflags", "+faststart", str(final_video_path)
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        else:
            final_video_path.write_bytes(raw_video_bytes)

    (out_path / "manifest.json").write_text(json.dumps({
        "variant_index": var_idx,
        "variant_id": variant["id"],
        "variant_name": variant["name"],
        "prompt": variant["prompt"],
        "image": product_img.name,
        "output_file": str(final_video_path.name)
    }, indent=2))
    print(f"Successfully generated: {final_video_path}")


if __name__ == "__main__":
    main()
