import os
import glob
import asyncio
import random
import imageio
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
CAPTURE_DIR = "./captures"
VIDEO_PATH = f"{CAPTURE_DIR}/proof.mp4"

# 🇺🇸 USA LINK
MAGIC_URL = "https://id5.cloud.huawei.com/CAS/portal/userRegister/regbyphone.html?regionCode=us&countryCode=us&lang=en-us"

# 🇺🇸 Hardcoded California Number (Matches Timezone)
FIXED_US_PHONE = "3102661985"

# 👇 YOUR USA PROXY 👇
PROXY_CONFIG = {
    "server": "http://142.111.48.253:7030", 
    "username": "wwwsyxzg", 
    "password": "582ygxexguhx"
}

app = FastAPI()
if not os.path.exists(CAPTURE_DIR): os.makedirs(CAPTURE_DIR)
app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

# --- LOGGING ---
logs = []
def log_msg(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    logs.insert(0, entry)
    if len(logs) > 100: logs.pop()

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei Ultimate Stealth</title>
        <style>
            body { background: #000; color: #00bcd4; font-family: monospace; padding: 20px; text-align: center; }
            .control-panel { 
                background: #111; padding: 20px; border: 1px solid #333; 
                margin: 0 auto 20px auto; max-width: 900px; border-radius: 10px;
                display: flex; justify-content: space-around;
            }
            button { 
                padding: 12px 24px; font-weight: bold; cursor: pointer; border:none; 
                margin: 5px; color: white; font-size: 14px; border-radius: 6px; text-transform: uppercase;
            }
            .btn-start { background: #e91e63; }
            .btn-refresh { background: #2196f3; }
            .btn-video { background: #4caf50; }
            .logs { height: 200px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; color: #ddd; margin-bottom: 20px; background: #0a0a0a; }
            .gallery { display: flex; flex-wrap: wrap; justify-content: center; gap: 5px; margin-bottom: 20px; }
            .gallery img { height: 120px; border: 1px solid #333; border-radius: 4px; }
            #video-section { display: none; margin-top: 30px; padding: 20px; border-top: 1px dashed #333; }
            video { width: 80%; max-width: 800px; border: 2px solid #00bcd4; border-radius: 8px; }
        </style>
    </head>
    <body>
        <h1>🥷 ULTIMATE FINGERPRINT SPOOFING</h1>
        <div class="control-panel">
            <button onclick="startBot()" class="btn-start">🚀 START STEALTH MODE</button>
            <button onclick="refreshData()" class="btn-refresh">🔄 REFRESH</button>
            <button onclick="makeVideo()" class="btn-video">🎬 MAKE VIDEO</button>
        </div>
        <div class="logs" id="logs">Ready...</div>
        <h3>📸 LIVE FEED</h3>
        <div class="gallery" id="gallery"></div>
        <div id="video-section">
            <h3>✨ PROOF VIDEO</h3>
            <video id="proof-player" controls><source src="" type="video/mp4"></video>
        </div>
        <script>
            function startBot() { fetch('/start', {method: 'POST'}); logUpdate(">>> STARTING STEALTH ENGINE..."); }
            function refreshData() {
                fetch('/status').then(r=>r.json()).then(d=>{
                    document.getElementById('logs').innerHTML = d.logs.map(l=>`<div>${l}</div>`).join('');
                    document.getElementById('gallery').innerHTML = d.images.map(i=>`<a href="${i}" target="_blank"><img src="${i}"></a>`).join('');
                });
            }
            function makeVideo() {
                logUpdate(">>> GENERATING VIDEO...");
                fetch('/generate_video', {method: 'POST'}).then(r=>r.json()).then(d=>{
                    if(d.status === "done") {
                        const vSec = document.getElementById('video-section');
                        const player = document.getElementById('proof-player');
                        const url = "/captures/proof.mp4?t=" + new Date().getTime();
                        vSec.style.display = "block"; player.src = url; player.load();
                    }
                });
            }
            function logUpdate(msg) { document.getElementById('logs').innerHTML = "<div>" + msg + "</div>" + document.getElementById('logs').innerHTML; }
            setInterval(refreshData, 5000);
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status():
    files = sorted(glob.glob(f'{CAPTURE_DIR}/*.jpg'), key=os.path.getmtime, reverse=True)
    urls = [f"/captures/{os.path.basename(f)}" for f in files]
    return JSONResponse({"logs": logs, "images": urls})

@app.post("/start")
async def start_bot(bt: BackgroundTasks):
    log_msg(">>> COMMAND: Start Ultimate Stealth Test")
    bt.add_task(run_stealth_agent)
    return {"status": "started"}

@app.post("/generate_video")
async def trigger_video():
    files = sorted(glob.glob(f'{CAPTURE_DIR}/monitor_*.jpg'))
    if not files: return {"status": "error"}
    try:
        with imageio.get_writer(VIDEO_PATH, fps=2, format='FFMPEG') as writer:
            for filename in files: writer.append_data(imageio.imread(filename))
        return {"status": "done"}
    except: return {"status": "error"}

# --- HUMAN HELPERS ---
async def human_click(page, elem, desc):
    box = await elem.bounding_box()
    if box:
        tx = box['x'] + (box['width']/2) + random.uniform(-10,10)
        ty = box['y'] + (box['height']/2) + random.uniform(-5,5)
        log_msg(f"🖱️ Moving to {desc}...")
        await page.mouse.move(tx, ty, steps=30) # Slower movement
        await asyncio.sleep(random.uniform(0.4, 0.8)) # Thinking time
        log_msg(f"🖱️ Clicking {desc}...")
        await page.mouse.down()
        await asyncio.sleep(random.uniform(0.08, 0.15))
        await page.mouse.up()
        return True
    return False

# --- STEALTH INJECTION SCRIPT ---
# Ye script Huawei ko jhoot bolegi k ye asli computer hai
STEALTH_JS = """
// 1. Fake GPU (Intel HD Graphics)
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Open Source Technology Center';
    if (parameter === 37446) return 'Mesa DRI Intel(R) HD Graphics 620';
    return getParameter(parameter);
};

// 2. Fake Plugins (Real browsers have plugins)
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// 3. Fake Languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
});

// 4. Hide WebDriver completely
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});
"""

# --- MAIN AGENT ---
async def run_stealth_agent():
    try:
        for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)

        async with async_playwright() as p:
            log_msg("🌍 Launching Browser with Timezone: America/Los_Angeles")
            
            # Browser Launch ARGS (Hardening)
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--window-size=1920,1080",
                    "--lang=en-US"
                ],
                proxy=PROXY_CONFIG
            )
            
            # Context with Timezone & Locale Matching USA
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                timezone_id="America/Los_Angeles", # Matches 310 Area Code
                locale="en-US",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            
            # Inject Stealth Script
            await page.add_init_script(STEALTH_JS)

            log_msg("🚀 Navigating to Huawei USA...")
            try:
                await page.goto(MAGIC_URL, timeout=60000)
            except:
                log_msg("❌ Proxy Timeout")
                await browser.close()
                return

            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            await page.screenshot(path=f"{CAPTURE_DIR}/monitor_00_loaded.jpg")

            # INPUT
            log_msg("🔍 Finding Input...")
            inp = page.locator("input.huawei-input").first
            if await inp.count() == 0: inp = page.locator("input[type='text']").first
            
            if await inp.count() > 0:
                await human_click(page, inp.first, "Input")
                await page.keyboard.type(FIXED_US_PHONE, delay=random.randint(90, 160))
                await asyncio.sleep(0.5)
                # Realistic Blur: Move mouse away then click
                await page.mouse.move(200, 200, steps=10)
                await page.mouse.click(200, 200)
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_01_filled.jpg")
            else:
                log_msg("❌ Input not found")
                return

            # CLICK
            log_msg("🔍 Finding Button...")
            btn = page.locator(".get-code-btn").first
            if await btn.count() == 0: btn = page.get_by_text("Get code").first
            
            if await btn.count() > 0:
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_02_pre_click.jpg")
                await human_click(page, btn, "Get Code")
                log_msg("✅ Click Sent!")
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_03_post_click.jpg")
            
            # MONITOR
            log_msg("👀 Analyzing Response (20s)...")
            for i in range(4, 20):
                await asyncio.sleep(1.5)
                path = f"{CAPTURE_DIR}/monitor_{i:02d}.jpg"
                await page.screenshot(path=path)
                
                # Check for Success (Captcha)
                if len(page.frames) > 1:
                    log_msg(f"🎉 BINGO! CAPTCHA DETECTED at Frame {i}! (Bypass Successful)")
                
                # Check for Failure
                err = await page.get_by_text("An unexpected problem").count()
                if err > 0:
                    log_msg(f"🛑 Still blocked at Frame {i}")

            log_msg("✅ Test Complete")
            await browser.close()

    except Exception as e:
        log_msg(f"❌ CRASH: {str(e)}")