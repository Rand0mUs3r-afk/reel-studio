# Reel Studio

Actions > Generate Reels > Run workflow. Quick test: demo, basic, variants=1, voice=off, presenter=none, 720p. Download the artifact after success. No automatic Instagram posting or Google Drive connection.

Use a public product_url, direct photo_urls, or upload images into inbox and choose repository_folder. Pick 1/2/3/5/10 variants per story or per photo. Maximum 12 accepted images and 30 videos. Blocked/login/JavaScript-only pages may fail; no access bypass.

main_words turns offer fragments into text: 2 for $30 -> Get 2 for $30. Explicit offer text appears in ending scenes even with general captions off. Numerics/currency/common added claims are checked, not every semantic error. Original words, resulting sentence and storyboard are saved.

reel_idea is your creative brief. follow_my_idea requires engine=cloud_ai and OPENAI_API_KEY in Actions Secrets. It directs available scene text, photo order, style and audio; unsupported footage/lip-sync/3D requests are reported. Local/basic modes record ideas but do not claim full natural-language interpretation.

local_ai runs BLIP image descriptions on the GitHub runner without an inference key; local/basic direction uses templates/rules. Cloud planning and generated fictional portraits require your OpenAI key, send selected thumbnails/text to that provider and may incur charges. Never put keys in code or chat.

Audio is original procedural backing or silence plus optional English espeak-ng narration, not premium neural TTS or scraped/trending songs. Scene captions are not word-aligned subtitles. Presenters are portrait overlays, not talking avatars. Motion is pan/zoom/cuts, not generative product video or unseen angles.

This repository, uploaded photos, logs and artifacts are not private. Artifacts expire after 30 days. Outputs include MP4, cover, optional caption/scene text, scripts, storyboard, settings and audio provenance; temporary working audio/frames are removed. GitHub resource limits/billing apply. Core had 10 local tests and an actual FFmpeg vertical MP4/audio smoke render; the director had 11 isolated tests. Hosted workflow, live model downloads, product scraping and cloud APIs have not been run by the assistant.
