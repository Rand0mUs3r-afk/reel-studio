"""Browser-based UI for generating Veo 3D turntable vape commercials with ambient music."""
import os
import tempfile
from pathlib import Path
import streamlit as st
import veo_turntable as veo

st.set_page_config(page_title="Vape Turntable Studio", layout="centered", page_icon="💨")

st.title("💨 Vape Commercial Turntable Studio")
st.caption("Generate high-end 360° rotating vape product commercials with ambient chill soundscapes right in your browser.")

api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
user_key = st.text_input("Gemini API Key (Veo access)", value=api_key, type="password", help="Your Google AI Studio API key")

tab_upload, tab_url = st.tabs(["📁 Upload Product Photo", "🌐 Product Webpage URL"])

with tab_upload:
    uploaded_file = st.file_uploader("Upload Vape Photo", type=["jpg", "jpeg", "png", "webp"])

with tab_url:
    product_url = st.text_input("E-commerce Product Webpage URL", placeholder="https://store.com/products/ice-bar-vape")

st.subheader("Commercial Settings")
col1, col2 = st.columns(2)

with col1:
    variant_options = [
        "Auto (Round-Robin non-repeating)",
        "1. Minimalist Dark Studio",
        "2. Sub-Zero Glacier Ice",
        "3. Neon Cyberclub Glow",
        "4. Pastel Candy Clouds",
        "5. Deep Aqua Splash"
    ]
    selected_variant_label = st.selectbox("Commercial Style", variant_options)
    variant_choice = None if "Auto" in selected_variant_label else int(selected_variant_label.split(".")[0]) - 1

with col2:
    music_option = st.selectbox("Ambient Background Music", ["Calming Synth Drone (On)", "Muted / No Music (Off)"])
    enable_music = "On" in music_option

if st.button("🚀 Generate 360° Rotating Commercial", type="primary"):
    active_key = user_key.strip()
    if not active_key:
        st.error("Please provide your Gemini API Key above.")
    elif not uploaded_file and not product_url.strip():
        st.error("Please either upload a product photo or provide an e-commerce product webpage URL.")
    else:
        with st.spinner("Extracting product & generating 360° commercial with Veo... (approx 60-90s)"):
            try:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_path = Path(tmp_dir)
                    
                    class Args:
                        photo_url = ""
                        product_url = product_url.strip() if not uploaded_file else ""
                        input_folder = ""
                        variant = variant_choice

                    args = Args()
                    if uploaded_file:
                        input_img = tmp_path / f"input_{uploaded_file.name}"
                        input_img.write_bytes(uploaded_file.getvalue())
                        args.input_folder = str(tmp_path)
                    else:
                        input_img = veo.get_input_image(args, tmp_path)

                    var_idx, variant = veo.load_next_variant(variant_choice)
                    st.info(f"Rendering Style: **{variant['name']}**")

                    raw_video = veo.call_veo_api(input_img, variant["prompt"], active_key)
                    raw_path = tmp_path / "raw.mp4"
                    raw_path.write_bytes(raw_video)

                    final_path = tmp_path / f"vape_{variant['id']}.mp4"
                    if enable_music:
                        audio_path = tmp_path / "ambient.wav"
                        veo.generate_ambient_music(audio_path, root_freq=variant["chord_root"], duration_seconds=8.0)
                        import subprocess
                        subprocess.run([
                            "ffmpeg", "-y", "-i", str(raw_path), "-i", str(audio_path),
                            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                            "-movflags", "+faststart", str(final_path)
                        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                    else:
                        final_path.write_bytes(raw_video)

                    st.success("Commercial generated successfully!")
                    video_bytes = final_path.read_bytes()
                    st.video(video_bytes)
                    st.download_button(
                        label="📥 Download Commercial (MP4)",
                        data=video_bytes,
                        file_name=f"vape_{variant['id']}_commercial.mp4",
                        mime="video/mp4"
                    )
            except Exception as exc:
                st.error(f"Generation error: {exc}")
