"""
Capture the Vigie product launch video using Playwright.

Opens the HTML animation, records video at 1920x1080, waits for the
full 180-second animation to complete, then saves as WebM.

Audio is generated separately and merged with FFmpeg.
"""
import asyncio
import time
from pathlib import Path
from playwright.async_api import async_playwright

HTML_PATH = Path("/home/z/my-project/scripts/vigie_video.html")
OUTPUT_DIR = Path("/home/z/my-project/scripts/video_output")
OUTPUT_DIR.mkdir(exist_ok=True)

VIDEO_DURATION = 185  # 180s animation + 5s buffer

async def capture_video():
    async with async_playwright() as p:
        # Launch Chromium with audio enabled
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--autoplay-policy=no-user-gesture-required',
                '--mute-audio',  # We'll generate audio separately
                '--disable-gpu',
                '--no-sandbox',
            ]
        )

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_video_dir=str(OUTPUT_DIR),
            record_video_size={'width': 1920, 'height': 1080},
        )

        page = await context.new_page()

        print(f"Opening {HTML_PATH}...")
        await page.goto(f"file://{HTML_PATH}")

        # Wait for fonts to load
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)

        # Trigger autoplay
        await page.evaluate("() => { window.location.search = '?autoplay=1'; }")
        await asyncio.sleep(1)

        # Actually, just click to start
        print("Starting animation...")
        await page.click('body')

        # Wait for the full animation
        print(f"Recording {VIDEO_DURATION}s of video...")
        for i in range(VIDEO_DURATION):
            await asyncio.sleep(1)
            if i % 10 == 0:
                print(f"  {i}s / {VIDEO_DURATION}s")

        # Close context to save video
        print("Saving video...")
        await context.close()
        await browser.close()

        # Find the saved video file
        videos = list(OUTPUT_DIR.glob("*.webm"))
        if videos:
            latest = max(videos, key=lambda p: p.stat().st_mtime)
            print(f"Video saved: {latest}")
            return latest
        else:
            print("ERROR: No video file found!")
            return None

if __name__ == "__main__":
    video_path = asyncio.run(capture_video())
    if video_path:
        print(f"\n✓ Video captured: {video_path}")
        print(f"  Size: {video_path.stat().st_size / 1024 / 1024:.1f} MB")
    else:
        print("\n✗ Video capture failed")
