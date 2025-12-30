import os
import glob
import asyncio
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright
import subprocess

TARGET_PHONE = "3177635849"
CAPTURE_DIR = "./captures"
VIDEO_PATH = f"{CAPTURE_DIR}/session_video.mp4"

app = FastAPI()
if not os.path.exists(CAPTURE_DIR):
    os.makedirs(CAPTURE_DIR)
app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

# --- LOGGING SYSTEM ---
logs = []
def log_msg(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    logs.insert(0, entry)
    if len(logs) > 50: logs.pop()

# --- DASHBOARD UI ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Huawei Automation Core</title>
        <style>
            body { background: #0a0a0a; color: #00ff41; font-family: 'Consolas', monospace; padding: 20px; text-align: center; }
            .box { border: 1px solid #333; padding: 15px; margin: 10px auto; max-width: 900px; background: #111; border-radius: 8px; }
            button { 
                padding: 15px 30px; font-size: 18px; font-weight: bold; cursor: pointer; 
                border: none; border-radius: 5px; margin: 5px; text-transform: uppercase;
            }
            .btn-start { background: #d63031; color: white; box-shadow: 0 0 10px #d63031; }
            .btn-refresh { background: #0984e3; color: white; }
            .logs { 
                height: 250px; overflow-y: auto; text-align: left; border: 1px solid #444; 
                padding: 10px; color: #ddd; font-size: 13px; background: black;
            }
            .log-entry { margin-bottom: 2px; border-bottom: 1px solid #222; }
            .gallery { 
                display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); 
                gap: 10px; padding: 10px; 
            }
            .gallery img { 
                width: 100%; border: 2px solid #555; border-radius: 5px; transition: 0.3s; 
            }
            .gallery img:hover { border-color: #fff; transform: scale(1.05); }
            video { width: 80%; border: 2px solid #00ff41; margin-top: 10px; }
        </style>
    </head>
    <body>
        <h1>⚡ HUAWEI AUTOMATION CORE (Direct Playwright)</h1>
        
        <div class="box">
            <button class="btn-refresh" onclick="refreshData()">🔄 Refresh View</button>
            <button class="btn-start" onclick="startBot()">🚀 Start Process</button>
            <div id="video-container" style="display:none;">
                <h3>🎬 Session Recording</h3>
                <video id="player" controls><source id="vsrc" src="" type="video/mp4"></video>
            </div>
        </div>

        <div class="box logs" id="terminal">Waiting for input...</div>
        <div class="box gallery" id="gallery"></div>

        <script>
            function startBot() {
                logToScreen(">>> COMMAND SENT: INITIALIZE SEQUENCE");
                fetch('/start', {method: 'POST'});
                setTimeout(refreshData, 1000);
            }
            function logToScreen(msg) {
                const term = document.getElementById('terminal');
                term.innerHTML = `<div class="log-entry" style="color:yellow">${msg}</div>` + term.innerHTML;
            }
            function refreshData() {
                fetch('/status').then(r => r.json()).then(d => {
                    const term = document.getElementById('terminal');
                    term.innerHTML = "";
                    d.logs.forEach(l => term.innerHTML += `<div class="log-entry">${l}</div>`);
                    
                    const gal = document.getElementById('gallery');
                    gal.innerHTML = "";
                    d.images.forEach(i => gal.innerHTML += `<a href="${i}" target="_blank"><img src="${i}"></a>`);
                    
                    if(d.video) {
                        document.getElementById('video-container').style.display = 'block';
                        document.getElementById('vsrc').src = d.video;
                        document.getElementById('player').load();
                    }
                });
            }
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status():
    files = glob.glob(f'{CAPTURE_DIR}/*.jpg')
    files.sort(key=os.path.getmtime, reverse=True)
    urls = [f"/captures/{os.path.basename(f)}" for f in files]
    
    video_url = ""
    if os.path.exists(VIDEO_PATH):
        video_url = f"/captures/session_video.mp4?t={datetime.now().timestamp()}"
        
    return JSONResponse({"logs": logs, "images": urls, "video": video_url})

@app.post("/start")
async def start_bot(bt: BackgroundTasks):
    log_msg(">>> Start Request Received")
    bt.add_task(run_automation)
    return {"status": "started"}

# --- THE REAL ENGINE (Playwright Logic) ---
async def run_automation():
    try:
        # Clear old data
        for f in glob.glob(f"{CAPTURE_DIR}/*"):
            os.remove(f)
            
        log_msg("🚀 Starting Playwright Engine (Chromium)...")
        
        async with async_playwright() as p:
            # Browser Launch
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            # Context for Video Recording
            context = await browser.new_context(
                record_video_dir=CAPTURE_DIR,
                record_video_size={"width": 1280, "height": 800},
                viewport={"width": 1280, "height": 800}
            )
            
            page = await context.new_page()
            
            # --- STEP 1: Go to URL ---
            log_msg("Navigating to Huawei Cloud...")
            await page.goto("https://id5.cloud.huawei.com/CAS/mobile/standard/register/wapRegister.html?reqClientType=7&loginChannel=7000000&regionCode=hk&loginUrl=https%3A%2F%2Fid5.cloud.huawei.com%2FCAS%2Fmobile%2Fstandard%2FwapLogin.html&lang=en-us&themeName=huawei#/wapRegister/regByPhone")
            await page.screenshot(path=f"{CAPTURE_DIR}/01_loaded.jpg")
            
            # --- STEP 2: Handle Cookie/Popups ---
            try:
                # Agar koi cookie banner aya to accept karo (Timeout 2s)
                cookie_btn = page.get_by_text("Accept", exact=False)
                if await cookie_btn.count() > 0:
                    await cookie_btn.first.click(timeout=2000)
                    log_msg("Cookie banner closed.")
            except: pass

            # --- STEP 3: Click Country ---
            log_msg("Locating 'Country/Region' dropdown...")
            # Hum generic Text selector use kar rahe hain jo AI ki tarah kaam karta hai
            # Ye dhoonde ga k kahan "Region" ya "Country" likha hai aur click karega
            await page.locator("div").filter(has_text="Country/Region").last.click()
            await asyncio.sleep(2)
            await page.screenshot(path=f"{CAPTURE_DIR}/02_dropdown_open.jpg")
            
            # --- STEP 4: Search Pakistan ---
            log_msg("Searching for 'Pakistan'...")
            # Search input box usually has type='search'
            await page.get_by_role("searchbox").fill("Pakistan")
            await asyncio.sleep(1)
            await page.screenshot(path=f"{CAPTURE_DIR}/03_typed_pak.jpg")
            
            # --- STEP 5: Select Pakistan ---
            log_msg("Selecting 'Pakistan +92'...")
            await page.get_by_text("Pakistan", exact=False).first.click()
            await asyncio.sleep(2)
            await page.screenshot(path=f"{CAPTURE_DIR}/04_pak_selected.jpg")
            
            # --- STEP 6: Type Number ---
            log_msg(f"Entering Phone Number: {TARGET_PHONE}")
            # Phone inputs usually have type='tel'
            await page.locator("input[type='tel']").fill(TARGET_PHONE)
            await asyncio.sleep(1)
            await page.screenshot(path=f"{CAPTURE_DIR}/05_number_filled.jpg")
            
            # --- STEP 7: Get Code ---
            log_msg("Clicking 'Get Code'...")
            await page.get_by_text("Get code").click()
            await page.screenshot(path=f"{CAPTURE_DIR}/06_clicked_getcode.jpg")
            
            # --- STEP 8: Monitor ---
            log_msg("Monitoring screen for 15 seconds...")
            for i in range(5):
                await asyncio.sleep(3)
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_{i}.jpg")
                log_msg(f"Status check {i+1}/5...")

            log_msg("✅ Process Finished. Saving Video...")
            
            # Close context to save video
            await context.close()
            await browser.close()
            
            # Rename video file to fixed name
            videos = glob.glob(f"{CAPTURE_DIR}/*.webm")
            if videos:
                # Convert WebM to MP4 using FFmpeg
                log_msg("Converting Video to MP4...")
                subprocess.run(f"ffmpeg -y -i {videos[0]} {VIDEO_PATH}", shell=True)
                log_msg("Video Ready!")

    except Exception as e:
        log_msg(f"❌ ERROR: {str(e)}")
        print(f"CRASH: {e}")