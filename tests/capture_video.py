"""
Capture Product Demo Video

Playwright script that walks through the MacroHero platform,
capturing frames for an animated GIF and MP4 video.

Usage:
    python main.py &
    python tests/capture_video.py

Output:
    docs/demo_video.gif
    docs/frames/*.png
"""

import asyncio
from pathlib import Path

ROOT = Path(__file__).parent.parent
FRAMES_DIR = ROOT / "docs" / "frames"
BASE_URL = "http://localhost:5030"

frame_num = 0


async def capture(page, label, pause=1.0):
    global frame_num
    await asyncio.sleep(pause)
    path = FRAMES_DIR / f"{frame_num:03d}_{label}.png"
    await page.screenshot(path=str(path), type="png")
    print(f"  [{frame_num:03d}] {label}")
    frame_num += 1


async def send_chat(page, msg, wait=3.0):
    await page.evaluate(f"""
        () => {{
            var ta=document.getElementById('chat-input');
            var fm=ta ? ta.form : null;
            if(ta&&fm){{ ta.value={repr(msg)}; ta.disabled=false; fm.requestSubmit(); }}
        }}
    """)
    await asyncio.sleep(wait)
    await page.evaluate("() => { var m=document.getElementById('chat-messages'); if(m) m.scrollTop=m.scrollHeight; }")


async def run():
    from playwright.async_api import async_playwright

    FRAMES_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        # ===== LANDING PAGE =====
        await page.goto(BASE_URL)
        await asyncio.sleep(2)
        await capture(page, "landing_hero", 1.5)

        # Scroll to features
        await page.evaluate("() => { document.getElementById('features')?.scrollIntoView({behavior:'smooth'}); }")
        await capture(page, "landing_features", 1.5)

        # Scroll to how it works
        await page.evaluate("() => { document.getElementById('how')?.scrollIntoView({behavior:'smooth'}); }")
        await capture(page, "landing_how", 1.5)

        # ===== HOMEPAGE (app) =====
        await page.goto(BASE_URL, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        await capture(page, "welcome_screen", 1.5)
        await capture(page, "welcome_hold", 1.0)

        # ===== CHAT: market movers =====
        await send_chat(page, "What's moving markets today?", 4)
        await capture(page, "chat_movers", 1.0)

        # ===== CHAT: FX strategies =====
        await send_chat(page, "Give me FX strategies for a Hormuz deal scenario", 8)
        await capture(page, "chat_strategies", 1.0)

        # Scroll to see full response
        await page.evaluate("() => { var m=document.getElementById('chat-messages'); if(m) m.scrollTop=m.scrollHeight; }")
        await capture(page, "chat_strategies_scroll", 0.5)

        # ===== CHAT: backtest =====
        await send_chat(page, "Backtest momentum on EUR/USD over last year", 10)
        await capture(page, "chat_backtest", 1.0)

        # Scroll to see results
        await page.evaluate("() => { var m=document.getElementById('chat-messages'); if(m) m.scrollTop=m.scrollHeight; }")
        await capture(page, "chat_backtest_scroll", 0.5)

        # ===== VIEW: Currency Pairs =====
        await page.evaluate("""
            () => { htmx.ajax('GET', '/view/pairs', {target:'#center-content', swap:'innerHTML'}); }
        """)
        await asyncio.sleep(2)
        await capture(page, "view_pairs", 1.0)

        # ===== VIEW: News History =====
        await page.evaluate("""
            () => { htmx.ajax('GET', '/view/history', {target:'#center-content', swap:'innerHTML'}); }
        """)
        await asyncio.sleep(2)
        await capture(page, "view_history", 1.0)

        # ===== BACK TO WELCOME =====
        await page.goto(BASE_URL, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        await capture(page, "final_welcome", 1.5)

        await browser.close()

    print(f"\n  Captured {frame_num} frames to docs/frames/")


def build_gif():
    """Assemble frames into animated GIF."""
    from PIL import Image

    frames = sorted(FRAMES_DIR.glob("*.png"))
    if not frames:
        print("No frames found!")
        return

    images = [Image.open(f) for f in frames]
    print(f"  Building GIF from {len(images)} frames...")

    gif_path = ROOT / "docs" / "demo_video.gif"
    w, h = images[0].size
    resized = [img.resize((w // 2, h // 2), Image.LANCZOS) for img in images]

    resized[0].save(
        str(gif_path), save_all=True, append_images=resized[1:],
        duration=1500, loop=0, optimize=True,
    )
    print(f"  Saved GIF: {gif_path}")

    # Copy to static for serving
    static_path = ROOT / "static" / "demo_video.gif"
    import shutil
    shutil.copy2(str(gif_path), str(static_path))
    print(f"  Copied to: {static_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MacroHero Product Demo — Video Capture")
    parser.add_argument("--gif-only", action="store_true",
                        help="Skip Playwright capture, build GIF from existing frames")
    parser.add_argument("--capture-only", action="store_true",
                        help="Capture frames only, skip GIF generation")
    args = parser.parse_args()

    if not args.gif_only:
        print(f"\n{'='*60}")
        print(f"  MacroHero Product Demo — Capturing frames")
        print(f"{'='*60}\n")
        asyncio.run(run())

    if not args.capture_only:
        print(f"\n{'='*60}")
        print(f"  Building GIF...")
        print(f"{'='*60}\n")
        build_gif()
        print(f"\n  Done!")
        print(f"  GIF: docs/demo_video.gif")
        print(f"  Static: static/demo_video.gif")
        print(f"  Frames: docs/frames/\n")


if __name__ == "__main__":
    main()
