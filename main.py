import os
import glob
import asyncio
import random
import time
import imageio
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
CAPTURE_DIR = "./captures"
VIDEO_PATH = f"{CAPTURE_DIR}/proof.mp4"
NUMBERS_FILE = "numbers.txt"
BASE_URL = "https://id5.cloud.huawei.com"
TARGET_COUNTRY = "Russia"

PROXY_CONFIG = {
    "server": "http://p.webshare.io:80", 
    "username": "wwwsyxzg-rotate", 
    "password": "582ygxexguhx"
}

app = FastAPI()
if not os.path.exists(CAPTURE_DIR): os.makedirs(CAPTURE_DIR)
app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

logs = []
def log_msg(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    logs.insert(0, entry)
    if len(logs) > 300: logs.pop()

def generate_russia_number():
    prefix = "9"
    rest = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    return f"{prefix}{rest}"

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei 0.1s Burst</title>
        <style>
            body { background: #000; color: #00e676; font-family: monospace; padding: 20px; text-align: center; }
            button { padding: 10px 20px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #6200ea; color: white; border-radius: 4px; }
            .logs { height: 300px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; background: #111; margin-bottom: 20px; font-size: 13px; color: #ccc; }
            .gallery { display: flex; flex-wrap: wrap; justify-content: center; gap: 2px; }
            .gallery img { height: 80px; border: 1px solid #333; }
            #video-section { display:none; margin-top:20px; border: 2px solid #00e676; padding:10px; }
        </style>
    </head>
    <body>
        <h1>📸 0.1s ULTRA BURST MODE</h1>
        <p>Capturing every 100ms | 10 FPS Video Generation</p>
        <button onclick="startBot()">🚀 START HIGH-SPEED TEST</button>
        <button onclick="makeVideo()" style="background: #e91e63;">🎬 GENERATE VIDEO</button>
        <button onclick="refreshData()" style="background: #2962ff;">🔄 REFRESH</button>
        
        <div class="logs" id="logs">Waiting...</div>
        <div id="video-section">
            <h3>🎬 REPLAY (10 FPS)</h3>
            <video id="v-player" controls width="400" autoplay loop></video>
        </div>
        <h3>🎞️ FRAME-BY-FRAME FEED</h3>
        <div class="gallery" id="gallery"></div>

        <script>
            function startBot() { fetch('/start', {method: 'POST'}); logUpdate(">>> STARTING..."); }
            function refreshData() {
                fetch('/status').then(r=>r.json()).then(d=>{
                    document.getElementById('logs').innerHTML = d.logs.map(l=>`<div>${l}</div>`).join('');
                    document.getElementById('gallery').innerHTML = d.images.map(i=>`<img src="${i}">`).join('');
                });
            }
            function makeVideo() {
                logUpdate(">>> GENERATING VIDEO (Please Wait)...");
                fetch('/generate_video', {method: 'POST'}).then(r=>r.json()).then(d=>{
                    if(d.status === "done") {
                        document.getElementById('video-section').style.display = 'block';
                        document.getElementById('v-player').src = "/captures/proof.mp4?t=" + Date.now();
                        logUpdate("✅ VIDEO READY!");
                    } else {
                        logUpdate("❌ Video Generation Failed");
                    }
                });
            }
            function logUpdate(msg) { document.getElementById('logs').innerHTML = "<div>" + msg + "</div>" + document.getElementById('logs').innerHTML; }
            setInterval(refreshData, 3000);
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status():
    # Show only last 50 images to avoid browser lag
    files = sorted(glob.glob(f'{CAPTURE_DIR}/*.jpg'), key=os.path.getmtime, reverse=True)[:50]
    urls = [f"/captures/{os.path.basename(f)}" for f in files]
    return JSONResponse({"logs": logs, "images": urls})

@app.post("/start")
async def start_bot(bt: BackgroundTasks):
    bt.add_task(run_russia_flow)
    return {"status": "started"}

@app.post("/generate_video")
async def trigger_video():
    # Sort by filename (timestamp ensures correct order)
    files = sorted(glob.glob(f'{CAPTURE_DIR}/*.jpg'))
    if not files: return {"status": "error"}
    try:
        # FPS = 10 because we are capturing every 0.1s
        with imageio.get_writer(VIDEO_PATH, fps=10, format='FFMPEG') as writer:
            for filename in files: writer.append_data(imageio.imread(filename))
        return {"status": "done"}
    except Exception as e:
        print(e)
        return {"status": "error"}

# --- VISUAL TAP ---
async def visual_tap(page, element, desc):
    try:
        await element.scroll_into_view_if_needed()
        box = await element.bounding_box()
        if box:
            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2
            
            # Red Dot
            await page.evaluate(f"""
                var dot = document.createElement('div');
                dot.style.position = 'absolute'; left = '{x}px'; top = '{y}px';
                dot.style.width = '20px'; height = '20px'; background = 'red';
                dot.style.borderRadius = '50%'; zIndex = '999999'; 
                dot.style.border = '2px solid yellow';
                document.body.appendChild(dot);
            """)
            log_msg(f"👆 Tapping {desc}...")
            await page.touchscreen.tap(x, y)
            return True
    except: pass
    return False

# --- 🔥 ULTRA BURST CAPTURE (0.1s) ---
async def burst_wait(page, seconds, step_name):
    log_msg(f"📸 Recording {step_name} ({seconds}s)...")
    frames = int(seconds / 0.1) # 10 frames per second
    for i in range(frames):
        # High precision timestamp for sorting
        ts = datetime.now().strftime("%H%M%S%f")
        filename = f"{ts}_{step_name}.jpg"
        await page.screenshot(path=f"{CAPTURE_DIR}/{filename}")
        await asyncio.sleep(0.1)

# --- MAIN FLOW ---
async def run_russia_flow():
    # Cleanup
    for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)
    
    current_number = generate_russia_number()
    log_msg(f"🎬 Starting 0.1s Capture Test | Number: {current_number}")

    async with async_playwright() as p:
        pixel_5 = p.devices['Pixel 5'].copy()
        pixel_5['user_agent'] = "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.101 Mobile Safari/537.36"
        pixel_5['viewport'] = {'width': 412, 'height': 950} 

        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            proxy=PROXY_CONFIG
        )

        context = await browser.new_context(**pixel_5, locale="en-US")
        page = await context.new_page()

        try:
            log_msg("🚀 Navigating...")
            await page.goto(BASE_URL, timeout=90000)
            await burst_wait(page, 3, "01_loaded")
            
            # Cookie
            cookie_close = page.locator(".cookie-close-btn").first
            if await cookie_close.count() == 0: cookie_close = page.get_by_text("Accept", exact=True).first
            if await cookie_close.count() > 0: await visual_tap(page, cookie_close, "Cookie")
            
            # Register
            reg_btn = page.get_by_text("Register", exact=True).first
            if await reg_btn.count() == 0: reg_btn = page.get_by_role("button", name="Register").first
            if await reg_btn.count() > 0:
                await visual_tap(page, reg_btn, "Register")
                await burst_wait(page, 3, "02_reg_click")
            
            # Terms
            agree_text = page.get_by_text("Huawei ID User Agreement").first
            if await agree_text.count() > 0: await visual_tap(page, agree_text, "Terms")
            
            agree_btn = page.get_by_text("Agree", exact=True).first
            if await agree_btn.count() == 0: agree_btn = page.get_by_text("Next", exact=True).first
            if await agree_btn.count() > 0:
                await visual_tap(page, agree_btn, "Agree_Next")
                await burst_wait(page, 3, "03_terms_done")

            # DOB
            await page.mouse.move(200, 500)
            await page.mouse.down()
            await page.mouse.move(200, 800, steps=20)
            await page.mouse.up()
            
            dob_next = page.get_by_text("Next", exact=True).first
            if await dob_next.count() > 0: await visual_tap(page, dob_next, "DOB_Next")
            await burst_wait(page, 2, "04_dob_done")

            # Phone Option
            use_phone = page.get_by_text("Use phone number", exact=False).first
            if await use_phone.count() > 0: await visual_tap(page, use_phone, "Use_Phone")
            await burst_wait(page, 2, "05_phone_screen")

            # --- 🔥 CRITICAL: COUNTRY SWITCH LOGIC ---
            log_msg("🌍 Attempting to Click HONG KONG...")
            
            # Identify Selector
            hk_selector = page.get_by_text("Hong Kong").first
            if await hk_selector.count() == 0: hk_selector = page.get_by_text("Country/Region").first
            
            if await hk_selector.count() > 0:
                # FORCE CLICK LOOP
                list_opened = False
                for attempt in range(3):
                    await visual_tap(page, hk_selector, f"Country_Click_Try_{attempt+1}")
                    await burst_wait(page, 2, f"06_check_click_{attempt}")
                    
                    # Check if Search Box appeared (Meaning list opened)
                    if await page.locator("input[type='search']").count() > 0 or \
                       await page.locator("input[placeholder='Search']").count() > 0:
                        log_msg("✅ Country List OPENED!")
                        list_opened = True
                        break
                    else:
                        log_msg("⚠️ List did not open, retrying click...")
                
                if list_opened:
                    # SEARCH RUSSIA
                    search_box = page.locator("input").first
                    await visual_tap(page, search_box, "Search_Box")
                    
                    log_msg("⌨️ Typing Russia...")
                    await page.keyboard.type("Russia", delay=100)
                    await burst_wait(page, 2, "07_typing")

                    target = page.get_by_text("Russia", exact=True).first
                    if await target.count() > 0:
                        await visual_tap(page, target, "Select_Russia")
                        await burst_wait(page, 3, "08_russia_set")
                    else:
                        log_msg("❌ Russia option not found")
            else:
                log_msg("❌ Country Selector Element Not Found")

            # INPUT & GET CODE
            inp = page.locator("input[type='tel']").first
            if await inp.count() == 0: inp = page.locator("input").first
            
            if await inp.count() > 0:
                await visual_tap(page, inp, "Input")
                for char in current_number:
                    await page.keyboard.type(char)
                    await asyncio.sleep(0.1)
                
                await page.touchscreen.tap(350, 100) # Close KB
                await burst_wait(page, 1, "09_ready")
                
                get_code = page.locator(".get-code-btn").first
                if await get_code.count() == 0: get_code = page.get_by_text("Get code", exact=False).first
                
                if await get_code.count() > 0:
                    await visual_tap(page, get_code, "GET CODE")
                    log_msg("⏳ Waiting 10s (Burst Mode)...")
                    await burst_wait(page, 10, "10_final_loading")

            await browser.close()
            log_msg("✅ Test Finished. Click 'GENERATE VIDEO' to watch replay.")

        except Exception as e:
            log_msg(f"❌ Error: {str(e)}")
            await browser.close()