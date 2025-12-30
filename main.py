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

# 👇👇👇 YOUR WEBSHARE PROXY CREDENTIALS 👇👇👇
PROXY_CONFIG = {
    "server": "http://p.webshare.io:80", 
    "username": "wwwsyxzg-rotate", 
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

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei Smart Bot</title>
        <style>
            body { background: #121212; color: #00e676; font-family: monospace; padding: 20px; text-align: center; }
            .control-panel { 
                background: #1e1e1e; padding: 20px; border: 2px solid #333; 
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
            
            #video-section { display: none; margin-top: 30px; padding: 20px; border-top: 2px dashed #444; }
            video { width: 80%; max-width: 800px; border: 3px solid #00e676; border-radius: 8px; }
        </style>
    </head>
    <body>
        <h1>🛡️ HUAWEI SMART ROTATION BOT</h1>
        
        <div class="control-panel">
            <button onclick="startBot()" class="btn-start">🚀 1. START SMART BOT</button>
            <button onclick="refreshData()" class="btn-refresh">🔄 2. REFRESH STATUS</button>
            <button onclick="makeVideo()" class="btn-video">🎬 3. GENERATE VIDEO</button>
        </div>

        <div class="logs" id="logs">System Ready...</div>
        
        <h3>📸 LIVE FEED</h3>
        <div class="gallery" id="gallery"></div>

        <div id="video-section">
            <h3>✨ SESSION RECORDING</h3>
            <video id="proof-player" controls><source src="" type="video/mp4"></video>
            <br><a id="download-link" href="#" target="_blank" style="color: #00e676;">⬇️ Download Video</a>
        </div>

        <script>
            function startBot() { fetch('/start', {method: 'POST'}); logUpdate(">>> COMMAND: STARTING..."); }
            
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
                        const vSection = document.getElementById('video-section');
                        const player = document.getElementById('proof-player');
                        const dlLink = document.getElementById('download-link');
                        const vidUrl = "/captures/proof.mp4?t=" + new Date().getTime();
                        vSection.style.display = "block";
                        player.src = vidUrl; dlLink.href = vidUrl; player.load();
                        alert("Video Ready!");
                    } else { alert("Error: " + d.message); }
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
    log_msg(">>> INITIALIZING SMART AGENT")
    bt.add_task(run_smart_agent)
    return {"status": "started"}

@app.post("/generate_video")
async def trigger_video():
    files = sorted(glob.glob(f'{CAPTURE_DIR}/monitor_*.jpg'))
    if not files: return {"status": "error", "message": "No frames"}
    try:
        with imageio.get_writer(VIDEO_PATH, fps=2, format='FFMPEG') as writer:
            for filename in files: writer.append_data(imageio.imread(filename))
        return {"status": "done"}
    except Exception as e: return {"status": "error", "message": str(e)}

# --- HUMAN HELPERS ---
async def human_click_element(page, element, desc):
    box = await element.bounding_box()
    if box:
        # Human jitter
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

# --- MAIN LOGIC ---
async def run_smart_agent():
    max_retries = 10
    attempt = 0
    
    # Clean previous captures
    for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)

    while attempt < max_retries:
        attempt += 1
        log_msg(f"🔄 ATTEMPT #{attempt} (Using Rotating IP)")
        
        browser = None
        try:
            async with async_playwright() as p:
                # Launch with Proxy
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

                log_msg("🚀 Navigating...")
                try:
                    await page.goto(MAGIC_URL, timeout=45000)
                except:
                    log_msg("⚠️ Network Timeout - Rotating IP...")
                    await browser.close()
                    continue

                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_00_loaded.jpg")

                # INPUT NUMBER
                log_msg("🔍 Finding Input...")
                inp = page.locator("input.huawei-input").first
                if await inp.count() == 0: inp = page.locator("input[type='text']").first
                
                if await inp.count() > 0:
                    await human_click_element(page, inp.first, "Input")
                    await page.keyboard.type(TARGET_PHONE, delay=100)
                    await page.mouse.click(500, 500) # Blur
                    await page.screenshot(path=f"{CAPTURE_DIR}/monitor_01_filled.jpg")
                else:
                    log_msg("❌ Layout Mismatch - Retrying...")
                    await browser.close()
                    continue

                # GET CODE CLICK
                log_msg("🔍 Finding Button...")
                btn = page.locator(".get-code-btn").first
                if await btn.count() == 0: btn = page.get_by_text("Get code").first
                
                if await btn.count() > 0:
                    await page.screenshot(path=f"{CAPTURE_DIR}/monitor_02_pre_click.jpg")
                    await human_click_element(page, btn, "Get Code")
                    log_msg("✅ Click Sent! Checking response...")
                    await asyncio.sleep(1)
                    await page.screenshot(path=f"{CAPTURE_DIR}/monitor_03_post_click.jpg")
                else:
                    log_msg("❌ Button not found - Retrying...")
                    await browser.close()
                    continue

                # --- INTELLIGENT MONITORING ---
                success = False
                captcha_found = False
                
                for i in range(4, 15):
                    await asyncio.sleep(2)
                    path = f"{CAPTURE_DIR}/monitor_{i:02d}.jpg"
                    await page.screenshot(path=path)
                    
                    # 1. CHECK FOR ERROR TEXT (The one you showed)
                    # "An unexpected problem was encountered"
                    error_check = await page.get_by_text("An unexpected problem was encountered").count()
                    if error_check > 0:
                        log_msg(f"🛑 BLOCKED (Frame {i}): 'Unexpected problem' detected.")
                        log_msg("♻️ Switching Proxy & Retrying...")
                        break # Break inner loop to trigger retry
                    
                    # 2. CHECK FOR CAPTCHA (Iframes or Slider)
                    if len(page.frames) > 1:
                        log_msg(f"⚠️ CAPTCHA DETECTED (Frame {i})! Pausing for analysis.")
                        captcha_found = True
                        break # Stop everything, we found a captcha!
                        
                if captcha_found:
                    log_msg("✅ MISSION SUCCESS: Captcha appeared! (Check images)")
                    return # Stop logic here
                    
                # Agar loop khatam hua aur error detected tha, to browser close hoga aur while loop dobara chalega
                await browser.close()
                
        except Exception as e:
            log_msg(f"❌ Error: {str(e)}")
            if browser: await browser.close()
            
    log_msg("❌ All Retries Failed or Blocked.")