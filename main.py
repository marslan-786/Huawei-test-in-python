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
TARGET_PHONE = "3177635849"
CAPTURE_DIR = "./captures"
MAGIC_URL = "https://id5.cloud.huawei.com/CAS/portal/userRegister/regbyphone.html?regionCode=pk&countryCode=pk&lang=en-us"
VIDEO_PATH = f"{CAPTURE_DIR}/proof.mp4"

# Proxy (None for now)
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
        <title>Huawei Proof Generator</title>
        <style>
            body { background: #0f0f0f; color: #00e676; font-family: monospace; padding: 20px; text-align: center; }
            .control-panel { 
                background: #1a1a1a; padding: 20px; border: 2px solid #333; 
                margin: 0 auto 20px auto; max-width: 900px; border-radius: 10px;
                display: flex; justify-content: space-around; flex-wrap: wrap;
            }
            button { 
                padding: 12px 24px; font-weight: bold; cursor: pointer; border:none; 
                margin: 5px; color: white; font-size: 14px; border-radius: 6px; text-transform: uppercase;
            }
            .btn-start { background: #d32f2f; }
            .btn-refresh { background: #1976d2; }
            .btn-video { background: #388e3c; }
            
            .logs { height: 200px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; color: #aaa; margin-bottom: 20px; background: #000; }
            
            .gallery { display: flex; flex-wrap: wrap; justify-content: center; gap: 5px; margin-bottom: 20px; }
            .gallery img { height: 120px; border: 1px solid #444; border-radius: 4px; }
            
            #video-section { 
                display: none; margin-top: 30px; padding: 20px; 
                border-top: 2px dashed #444; text-align: center; 
            }
            video { width: 80%; max-width: 800px; border: 3px solid #00e676; border-radius: 8px; }
        </style>
    </head>
    <body>
        <h1>🎥 PROJECT PROOF DASHBOARD</h1>
        
        <div class="control-panel">
            <button onclick="startBot()" class="btn-start">🚀 1. START BOT</button>
            <button onclick="refreshData()" class="btn-refresh">🔄 2. REFRESH IMAGES</button>
            <button onclick="makeVideo()" class="btn-video">🎬 3. GENERATE VIDEO</button>
        </div>

        <div class="logs" id="logs">System Ready...</div>
        
        <h3>📸 LIVE CAPTURES</h3>
        <div class="gallery" id="gallery"></div>

        <div id="video-section">
            <h3>✨ FINAL PROOF VIDEO</h3>
            <video id="proof-player" controls>
                <source src="" type="video/mp4">
                Your browser does not support the video tag.
            </video>
            <br>
            <a id="download-link" href="#" target="_blank" style="color: #00e676; margin-top: 10px; display: block;">⬇️ Download Video</a>
        </div>

        <script>
            function startBot() {
                fetch('/start', {method: 'POST'});
                logUpdate(">>> COMMAND: STARTING BOT...");
            }

            function refreshData() {
                fetch('/status').then(r=>r.json()).then(d=>{
                    document.getElementById('logs').innerHTML = d.logs.map(l=>`<div>${l}</div>`).join('');
                    document.getElementById('gallery').innerHTML = d.images.map(i=>`<a href="${i}" target="_blank"><img src="${i}"></a>`).join('');
                });
            }

            function makeVideo() {
                logUpdate(">>> COMMAND: GENERATING VIDEO...");
                fetch('/generate_video', {method: 'POST'}).then(r=>r.json()).then(d=>{
                    if(d.status === "done") {
                        const vSection = document.getElementById('video-section');
                        const player = document.getElementById('proof-player');
                        const dlLink = document.getElementById('download-link');
                        
                        // Add timestamp to bypass cache
                        const vidUrl = "/captures/proof.mp4?t=" + new Date().getTime();
                        
                        vSection.style.display = "block";
                        player.src = vidUrl;
                        dlLink.href = vidUrl;
                        player.load();
                        alert("Video Generated Successfully! Check bottom of page.");
                    } else {
                        alert("Error: " + d.message);
                    }
                });
            }

            function logUpdate(msg) {
                const logDiv = document.getElementById('logs');
                logDiv.innerHTML = "<div>" + msg + "</div>" + logDiv.innerHTML;
            }
            
            // Auto refresh every 5 seconds
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
    log_msg(">>> BOT STARTED")
    bt.add_task(run_proof_agent)
    return {"status": "started"}

@app.post("/generate_video")
async def trigger_video_generation():
    # Check if we have images
    files = sorted(glob.glob(f'{CAPTURE_DIR}/monitor_*.jpg'))
    if not files:
        return {"status": "error", "message": "No images found. Run the bot first!"}
    
    try:
        log_msg("🎬 Stitched images into video...")
        # 2 FPS = Slow & Clear
        with imageio.get_writer(VIDEO_PATH, fps=2, format='FFMPEG') as writer:
            for filename in files:
                image = imageio.imread(filename)
                writer.append_data(image)
        log_msg(f"✅ VIDEO SAVED to {VIDEO_PATH}")
        return {"status": "done"}
    except Exception as e:
        log_msg(f"❌ Video Error: {str(e)}")
        return {"status": "error", "message": str(e)}

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

            log_msg("🚀 Navigating...")
            await page.goto(MAGIC_URL)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            await page.screenshot(path=f"{CAPTURE_DIR}/monitor_00.jpg")

            # --- INPUT ---
            log_msg("🔍 Finding Input...")
            phone_input = page.locator("input.huawei-input").first
            if await phone_input.count() == 0: phone_input = page.locator("input[type='text']").first
            
            if await phone_input.count() > 0:
                await human_click_element(page, phone_input.first, "Phone Input")
                log_msg(f"⌨️ Typing {TARGET_PHONE}...")
                await page.keyboard.type(TARGET_PHONE, delay=random.randint(80, 150))
                await asyncio.sleep(1)
                await page.mouse.click(500, 500)
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_01_filled.jpg")
            else:
                log_msg("❌ Input not found!")
                return

            # --- CLICK ---
            log_msg("🔍 Finding 'Get Code'...")
            get_code_btn = page.locator(".get-code-btn").first
            if await get_code_btn.count() == 0: get_code_btn = page.get_by_text("Get code").first
            
            if await get_code_btn.count() > 0:
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_02_pre_click.jpg")
                await human_click_element(page, get_code_btn, "Get Code Button")
                log_msg("✅ Click Sent!")
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_03_post_click.jpg")
            else:
                log_msg("❌ Button not found!")

            # --- MONITORING ---
            log_msg("🎥 Recording (Capture Mode)...")
            # 20 frames for video proof
            for i in range(4, 25):
                await asyncio.sleep(1.5)
                # Important: 04, 05 format for correct video sorting
                path = f"{CAPTURE_DIR}/monitor_{i:02d}.jpg"
                await page.screenshot(path=path)
                if len(page.frames) > 1: log_msg(f"⚠️ CAPTCHA DETECTED (Frame {i})")
            
            log_msg("✅ Finished! Now click 'GENERATE VIDEO'.")
            await browser.close()

    except Exception as e:
        log_msg(f"❌ CRASH: {str(e)}")