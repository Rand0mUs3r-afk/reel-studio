"""Automated video generation for vape product commercials using official Google GenAI SDK."""
import argparse
import http.client
import ipaddress
import json
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path
from urllib.parse import urlsplit, urljoin
from bs4 import BeautifulSoup
from PIL import Image, ImageOps
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


def target(url):
    p = urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443):
        raise ValueError('Only public HTTPS URLs on port 443 are supported')
    addresses = {a[4][0] for a in socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM)}
    if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
        raise ValueError('Private/local network targets are blocked')
    return p, sorted(addresses)[0]


def fetch(url, limit=15000000):
    for _ in range(5):
        p, ip = target(url)
        sock = ssl.create_default_context().wrap_socket(socket.create_connection((ip, 443), timeout=30), server_hostname=p.hostname)
        try:
            path = (p.path or '/') + ('?' + p.query if p.query else '')
            sock.sendall(('GET ' + path + ' HTTP/1.1\r\nHost: ' + p.hostname + '\r\nUser-Agent: ReelStudio/1.0\r\nConnection: close\r\n\r\n').encode('ascii'))
            resp = http.client.HTTPResponse(sock)
            resp.begin()
            if resp.status in (301, 302, 303, 307, 308):
                location = resp.getheader('Location')
                if not location:
                    raise ValueError('Redirect without location')
                url = urljoin(url, location)
                continue
            if resp.status != 200:
                raise ValueError('Source HTTP ' + str(resp.status))
            data = resp.read(limit + 1)
            if len(data) > limit:
                raise ValueError('Source exceeds download limit')
            return data
        finally:
            sock.close()
    raise ValueError('Too many redirects')


def extract_product_images(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    images = []
    def walk(val):
        if isinstance(val, list):
            for item in val:
                walk(item)
        elif isinstance(val, dict):
            kind = val.get('@type', [])
            if 'Product' in ([kind] if isinstance(kind, str) else kind):
                img = val.get('image', [])
                for item in img if isinstance(img, list) else [img]:
                    c = item.get('url') or item.get('contentUrl') if isinstance(item, dict) else item
                    if isinstance(c, str):
                        images.append(urljoin(url, c))
            for item in val.values():
                if isinstance(item, (dict, list)):
                    walk(item)
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            walk(json.loads(tag.string or tag.get_text()))
        except Exception:
            pass
    for tag in soup.select('meta[property="og:image"], meta[name="twitter:image"]'):
        if tag.get('content'):
            images.append(urljoin(url, tag['content']))
    if not images:
        for tag in soup.select('img'):
            src = tag.get('data-src') or tag.get('src')
            if src:
                images.append(urljoin(url, src))
    return list(dict.fromkeys(images))[:10]


def get_input_image(args, temp_dir):
    if args.photo_url:
        data = fetch(args.photo_url)
        path = temp_dir / 'downloaded.png'
        path.write_bytes(data)
        return path

    if args.product_url:
        print(f"Scraping product page: {args.product_url}")
        html = fetch(args.product_url, limit=2000000).decode('utf-8', errors='ignore')
        urls = extract_product_images(html, args.product_url)
        if not urls:
            raise ValueError(f"No product image found on webpage: {args.product_url}")
        print(f"Found product image: {urls[0]}")
        data = fetch(urls[0])
        path = temp_dir / 'scraped_product.png'
        path.write_bytes(data)
        return path

    folder = Path(args.input_folder).resolve()
    if folder.is_dir():
        local_imgs = sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS])
        if local_imgs:
            return local_imgs[0]

    print("Notice: Generating product canvas seed...")
    gen_path = temp_dir / 'synth_vape.png'
    img = Image.new('RGB', (1080, 1920), '#080C14')
    ImageOps.fit(img, (1080, 1920)).save(gen_path)
    return gen_path


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


def call_google_genai_video(image_path, prompt, api_key):
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    with Image.open(image_path) as im:
        pil_image = im.convert("RGB")

    print("Submitting video generation to Google GenAI SDK (client.models.generate_videos)...")
    candidate_models = ["gemini-omni-1.1-flash", "veo-3.1-fast-generate-preview", "veo-3.1-generate-preview"]
    last_err = None

    for model_name in candidate_models:
        try:
            print(f"Requesting video generation with model: {model_name}...")
            operation = client.models.generate_videos(
                model=model_name,
                prompt=prompt,
                image=pil_image,
                config=types.GenerateVideosConfig(
                    aspect_ratio="9:16",
                    duration_seconds=8
                )
            )
            print(f"Generation task started. Operation: {getattr(operation, 'name', operation)}. Polling...")
            while not operation.done:
                time.sleep(10)
                operation = client.operations.get(operation)

            if hasattr(operation, "error") and operation.error:
                raise RuntimeError(operation.error)

            generated_videos = operation.response.generated_videos
            if not generated_videos:
                raise RuntimeError("No video returned from generation operation.")

            vid = generated_videos[0]
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                tmp_out = f.name
            
            client.files.download(file=vid.video, download_path=tmp_out)
            data = Path(tmp_out).read_bytes()
            Path(tmp_out).unlink(missing_ok=True)
            return data
        except Exception as exc:
            last_err = exc
            print(f"Model {model_name} error: {exc}. Trying next model...")
            continue

    raise RuntimeError(f"All GenAI video generation models failed: {last_err}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-folder', default='inbox', help='Local folder with product photos')
    parser.add_argument('--product-url', default='', help='Public e-commerce product webpage to scrape photo from')
    parser.add_argument('--photo-url', default='', help='Direct HTTPS URL to a product photo')
    parser.add_argument('--output-dir', default='output/veo_turntable')
    parser.add_argument('--variant', type=int, default=None, help='Force a specific variant index (0 to 4)')
    parser.add_argument('--music', default='on', choices=['on', 'off'])
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable required.", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        product_img = get_input_image(args, tmp_dir)
        var_idx, variant = load_next_variant(args.variant)
        print(f"Selected Vape Variant [{var_idx + 1}/5]: {variant['name']}")
        print(f"Generating commercial from image: {product_img.name}...")

        raw_video_bytes = call_google_genai_video(product_img, variant["prompt"], api_key)
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
        "output_file": str(final_video_path.name)
    }, indent=2))
    print(f"Successfully generated: {final_video_path}")


if __name__ == "__main__":
    main()
