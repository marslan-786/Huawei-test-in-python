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

# 🇺🇸 USA LINK (Updated)
MAGIC_URL = "https://id5.cloud.huawei.com/CAS/portal/userRegister/regbyphone.html?regionCode=us&countryCode=us&lang=en-us"

# 👇👇👇 YOUR USA PROXY (Fixed) 👇👇👇
PROXY_CONFIG = {
    "server": "http://142.111.48.253:7030", 
    "username": "wwwsyxzg", 
    "password": "582ygxexguhx"
}
# 👆👆👆

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

# --- HELPER: GENERATE RANDOM USA NUMBER ---
def get_usa_number():
    # US Area codes (e.g., 202, 212, 310)
    area_codes = ["202", "212", "310", "323", "415", "646"]
    code = random.choice(area_codes)
    # Remaining 7 digits
    number = f"{random.randint(100, 999)}{random.randint(1000, 9999)}"
    return f"{code}{number}"

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei USA Test</title>
        <style>
            body { background: #0d1117; color: #58a6ff; font-family: monospace; padding: 20px; text-align: center; }
            .control-panel { 
                background: #161b22; padding: 20px; border: 1px solid #30363d; 
                margin: 0 auto 20px auto; max-width: 900px; border-radius: 10px;
                display: flex; justify-content: space-around;
            }
            button { 
                padding: 12px 24px; font-weight: bold; cursor: pointer; border:none; 
                margin: 5px; color: white; font-size: 14px; border-radius: 6px; text-transform: uppercase;
            }
            .btn-start { background: #238636; }
            .btn-refresh { background: #1f6feb; }
            .btn-video { background: #8957e5; }
            
            .logs { height: 200px; overflow-y: auto; text-align: left; border: 1px solid #30363d; padding: 10px; color: #8b949e; margin-bottom: 20px; background: #0d1117; }
            .gallery { display: flex; flex-wrap: wrap; justify-content: center; gap: 5px; margin-bottom: 20px; }
            .gallery img { height: 120px; border: 1px solid #30363d; border-radius: 4px; }
            #video-section { display: none; margin-top: 30px; padding: 20px; border-top: 1px dashed #30363d; }
            video { width: 80%; max-width: 800px; border: 2px solid #238636; border-radius: 8px; }
        </style>
    </head>
    <body>
        <h1>🇺🇸 HUAWEI USA PROXY TEST</h1>
        <div class="control-panel">
            <button onclick="startBot()" class="btn-start">🚀 START USA TEST</button>
            <button onclick="refreshData()" class="btn-refresh">🔄 REFRESH</button>
            <button onclick="makeVideo()" class="btn-video">🎬 VIDEO PROOF</button>
        </div>
        <div class="logs" id="logs">Ready for US Proxy Test...</div>
        <h3>📸 LIVE FEED</h3>
        <div class="gallery" id="gallery"></div>
        <div id="video-section">
            <h3>✨ SESSION RECORDING</h3>
            <video id="proof-player" controls><source src="" type="video/mp4"></video>
        </div>
        <script>
            function startBot() { fetch('/start', {method: 'POST'}); logUpdate(">>> INITIALIZING USA TEST..."); }
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
    log_msg(">>> COMMAND: Start USA Proxy Test")
    bt.add_task(run_usa_agent)
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

# --- HELPERS ---
async def human_click(page, elem, desc):
    box = await elem.bounding_box()
    if box:
        tx = box['x'] + (box['width']/2) + random.uniform(-5,5)
        ty = box['y'] + (box['height']/2) + random.uniform(-5,5)
        log_msg(f"🖱️ Moving to {desc}...")
        await page.mouse.move(tx, ty, steps=25)
        await asyncio.sleep(0.5)
        log_msg(f"🖱️ Clicking {desc}...")
        await page.mouse.down()
        await asyncio.sleep(0.1)
        await page.mouse.up()
        return True
    return False

# --- MAIN AGENT ---
async def run_usa_agent():
    try:
        for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)
        
        target_phone_us = get_usa_number()
        log_msg(f"🇺🇸 Generated Random US Phone: {target_phone_us}")

        async with async_playwright() as p:
            log_msg(f"🌍 Connecting to Proxy: {PROXY_CONFIG['server']}...")
            
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
                proxy=PROXY_CONFIG
            )
            
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

            log_msg("🚀 Navigating to USA Page...")
            try:
                await page.goto(MAGIC_URL, timeout=60000)
            except:
                log_msg("❌ Proxy Connection Failed / Timeout")
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
                await page.keyboard.type(target_phone_us, delay=100)
                await page.mouse.click(500, 500) # Blur
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_01_filled.jpg")
            else:
                log_msg("❌ Input not found")
                return

            # CLICK
            log_msg("🔍 Finding 'Get Code'...")
            btn = page.locator(".get-code-btn").first
            if await btn.count() == 0: btn = page.get_by_text("Get code").first
            
            if await btn.count() > 0:
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_02_pre_click.jpg")
                await human_click(page, btn, "Get Code")
                log_msg("✅ Click Sent!")
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_03_post_click.jpg")
            else:
                log_msg("❌ Button not found")

            # MONITOR
            log_msg("👀 Watching for CAPTCHA (20s)...")
            for i in range(4, 20):
                await asyncio.sleep(1.5)
                path = f"{CAPTURE_DIR}/monitor_{i:02d}.jpg"
                await page.screenshot(path=path)
                
                # Check Logic
                if len(page.frames) > 1:
                    log_msg(f"🎉 SUCCESS! CAPTCHA DETECTED at Frame {i}!")
                
                err = await page.get_by_text("An unexpected problem").count()
                if err > 0:
                    log_msg(f"🛑 Still Blocked (Proxy might be detected) at Frame {i}")

            log_msg("✅ Test Complete")
            await browser.close()

    except Exception as e:
        log_msg(f"❌ CRASH: {str(e)}")