import os
import glob
import asyncio
import random
import imageio
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
TARGET_PHONE = "3177635849"
CAPTURE_DIR = "./captures"
MAGIC_URL = "https://id5.cloud.huawei.com/CAS/portal/userRegister/regbyphone.html?regionCode=pk&countryCode=pk&lang=en-us"
VIDEO_PATH = f"{CAPTURE_DIR}/proof.mp4"

# Proxy abhi nahi hai, to None kar dia
PROXY_CONFIG = None 

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
        <title>Huawei Proof Bot</title>
        <style>
            body { background: #111; color: #ff3d00; font-family: monospace; padding: 20px; text-align: center; }
            .box { border: 2px solid #ff3d00; padding: 20px; margin: 15px auto; max-width: 800px; background: #222; border-radius: 8px; }
            button { padding: 15px 30px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #d84315; color: white; font-size: 16px; border-radius: 5px; }
            .logs { height: 300px; overflow-y: auto; text-align: left; border: 1px solid #444; padding: 10px; color: #ccc; font-size: 13px; }
            .video-link { display: block; margin: 20px; font-size: 20px; color: #00e676; text-decoration: none; border: 2px solid #00e676; padding: 10px; }
            .video-link:hover { background: #00e676; color: black; }
        </style>
    </head>
    <body>
        <h1>🎥 PROJECT PROOF GENERATOR</h1>
        <div class="box">
            <button onclick="startBot()">🚀 GENERATE PROOF VIDEO</button>
            <button onclick="refreshData()" style="background: #2196f3;">🔄 REFRESH STATUS</button>
        </div>
        <div id="video-container"></div>
        <div class="box logs" id="logs">Waiting to start...</div>
        <script>
            function startBot() {
                fetch('/start', {method: 'POST'});
                document.getElementById('logs').innerHTML = "<div>>>> STARTING SEQUENCE...</div>" + document.getElementById('logs').innerHTML;
                document.getElementById('video-container').innerHTML = "";
                setTimeout(refreshData, 2000);
            }
            function refreshData() {
                fetch('/status').then(r=>r.json()).then(d=>{
                    document.getElementById('logs').innerHTML = d.logs.map(l=>`<div>${l}</div>`).join('');
                    if (d.video_ready) {
                        document.getElementById('video-container').innerHTML = `<a href="/captures/proof.mp4" target="_blank" class="video-link">🎬 CLICK HERE TO DOWNLOAD/VIEW VIDEO</a>`;
                    }
                });
            }
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status():
    video_ready = os.path.exists(VIDEO_PATH)
    return JSONResponse({"logs": logs, "video_ready": video_ready})

@app.post("/start")
async def start_bot(bt: BackgroundTasks):
    log_msg(">>> COMMAND: Start Proof Generation")
    bt.add_task(run_proof_agent)
    return {"status": "started"}

# --- HELPER: VIDEO GENERATOR ---
def generate_video():
    log_msg("🎬 Generating Video from captured frames...")
    # Sirf monitor wali images uthao
    files = sorted(glob.glob(f'{CAPTURE_DIR}/monitor_*.jpg'))
    if not files:
        log_msg("❌ No frames found for video!")
        return

    try:
        # 2 FPS (Frames Per Second) - Slow video taake sab clear nazar aye
        with imageio.get_writer(VIDEO_PATH, fps=2, format='FFMPEG') as writer:
            for filename in files:
                image = imageio.imread(filename)
                writer.append_data(image)
        log_msg(f"✅ VIDEO READY: {VIDEO_PATH}")
    except Exception as e:
        log_msg(f"❌ Video generation failed: {str(e)}")

# --- HUMAN MOVEMENT HELPER ---
async def human_move_to(page, x, y):
    await page.mouse.move(x, y, steps=25)

async def human_click_element(page, element, desc):
    box = await element.bounding_box()
    if box:
        target_x = box['x'] + (box['width'] / 2) + random.uniform(-10, 10)
        target_y = box['y'] + (box['height'] / 2) + random.uniform(-5, 5)
        log_msg(f"🖱️ Moving to {desc}...")
        await human_move_to(page, target_x, target_y)
        await asyncio.sleep(random.uniform(0.3, 0.6))
        log_msg(f"🖱️ Clicking {desc}...")
        await page.mouse.down()
        await asyncio.sleep(random.uniform(0.05, 0.15))
        await page.mouse.up()
        return True
    return False

# --- MAIN LOGIC ---
async def run_proof_agent():
    try:
        # Cleanup old files
        for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)

        async with async_playwright() as p:
            # Launch Browser (Server IP)
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--start-maximized"]
            )
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

            log_msg("🚀 Navigating to Clean URL...")
            await page.goto(MAGIC_URL)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            
            # Initial Snapshot
            await page.screenshot(path=f"{CAPTURE_DIR}/monitor_00.jpg")

            # --- INPUT NUMBER ---
            log_msg("🔍 Finding Input...")
            phone_input = page.locator("input.huawei-input").first
            if await phone_input.count() == 0: phone_input = page.locator("input[type='text']").first
            
            if await phone_input.count() > 0:
                await human_click_element(page, phone_input.first, "Phone Input")
                log_msg(f"⌨️ Typing {TARGET_PHONE}...")
                await page.keyboard.type(TARGET_PHONE, delay=random.randint(80, 150))
                await asyncio.sleep(1)
                # Blur and capture
                await page.mouse.click(500, 500)
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_01_filled.jpg")
            else:
                log_msg("❌ Input not found!")
                return

            # --- GET CODE CLICK ---
            log_msg("🔍 Finding 'Get Code'...")
            get_code_btn = page.locator(".get-code-btn").first
            if await get_code_btn.count() == 0: get_code_btn = page.get_by_text("Get code").first
            
            if await get_code_btn.count() > 0:
                # Capture before click
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_02_pre_click.jpg")
                
                await human_click_element(page, get_code_btn, "Get Code Button")
                log_msg("✅ Click Sent!")
                
                # Capture right after click
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_03_post_click.jpg")
            else:
                log_msg("❌ Button not found!")

            # --- MONITORING (Recording for Video) ---
            log_msg("🎥 Recording results (30s)...")
            for i in range(4, 20): # More frames for video
                await asyncio.sleep(2)
                # Use leading zeros for correct sorting (04, 05, etc)
                path = f"{CAPTURE_DIR}/monitor_{i:02d}.jpg"
                await page.screenshot(path=path)
                if len(page.frames) > 1: log_msg(f"⚠️ CAPTCHA/ERROR DETECTED (Frame {i})")
            
            log_msg("✅ Recording Finished. Processing Video...")
            await browser.close()
            
            # Generate Video
            generate_video()

    except Exception as e:
        log_msg(f"❌ CRASH: {str(e)}")