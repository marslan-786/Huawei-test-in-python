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

# --- IMPORT SOLVER (Make sure captcha_solver.py is in the same folder) ---
try:
    from captcha_solver import solve_captcha
except ImportError:
    print("❌ ERROR: captcha_solver.py not found! Make sure it's uploaded.")
    def solve_captcha(*args, **kwargs): return False # Fallback dummy

# --- CONFIGURATION ---
CAPTURE_DIR = "./captures"
VIDEO_PATH = f"{CAPTURE_DIR}/proof.mp4"
NUMBERS_FILE = "numbers.txt"
BASE_URL = "https://id5.cloud.huawei.com"
TARGET_COUNTRY = "Russia"

PROXY_CONFIG = {
    "server": "http://p.webshare.io:80", 
    "username": "arldpbwk-rotate", 
    "password": "iak7d1keh2ix"
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
    if len(logs) > 500: logs.pop()

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
        <title>Huawei AI Solver Bot</title>
        <style>
            body { background: #000; color: #00e676; font-family: monospace; padding: 20px; text-align: center; }
            button { padding: 12px 24px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #6200ea; color: white; border-radius: 4px; }
            .status-bar { background: #333; color: yellow; padding: 10px; margin: 10px auto; width: 80%; border-radius: 5px; font-weight: bold; display: none; }
            .logs { height: 250px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; background: #111; margin-bottom: 20px; font-size: 12px; color: #ccc; }
            #video-section { display:none; margin: 20px auto; border: 3px solid #00e676; padding:15px; background: #111; width: fit-content; border-radius: 10px; }
            .gallery { display: flex; flex-wrap: wrap; justify-content: center; gap: 2px; margin-top: 20px; }
            .gallery img { height: 60px; border: 1px solid #333; opacity: 0.9; }
            .gallery img:hover { height: 150px; border-color: white; z-index:999; transition: 0.1s; }
        </style>
    </head>
    <body>
        <h1>🇷🇺 HUAWEI AI SOLVER BOT</h1>
        <p>Auto-Solve Captcha using Trained AI Logic</p>
        
        <div>
            <button onclick="startBot()">🚀 START SOLVER LOOP</button>
            <button onclick="makeVideo()" style="background: #e91e63;">🎬 MAKE VIDEO</button>
            <button onclick="refreshData()" style="background: #2962ff;">🔄 REFRESH</button>
        </div>

        <div id="status-bar" class="status-bar"></div>
        <div class="logs" id="logs">Waiting...</div>
        <div id="video-section">
            <h3 style="margin-top:0; color: #00e676;">🎬 REPLAY</h3>
            <video id="v-player" controls width="500" autoplay loop></video>
        </div>
        <h3>🎞️ ACTIVITY FEED</h3>
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
                var status = document.getElementById('status-bar');
                status.style.display = 'block';
                status.innerText = "⏳ PROCESSING VIDEO...";
                fetch('/generate_video', {method: 'POST'}).then(r=>r.json()).then(d=>{
                    if(d.status === "done") {
                        status.innerText = "✅ VIDEO READY!";
                        var vSection = document.getElementById('video-section');
                        vSection.style.display = 'block';
                        var player = document.getElementById('v-player');
                        player.src = "/captures/proof.mp4?t=" + Date.now();
                        player.load(); player.play();
                    } else {
                        status.innerText = "❌ ERROR: " + d.error;
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
    files = sorted(glob.glob(f'{CAPTURE_DIR}/*.jpg'), key=os.path.getmtime, reverse=True)
    urls = [f"/captures/{os.path.basename(f)}" for f in files]
    return JSONResponse({"logs": logs, "images": urls})

@app.post("/start")
async def start_bot(bt: BackgroundTasks):
    bt.add_task(run_russia_flow)
    return {"status": "started"}

@app.post("/generate_video")
async def trigger_video():
    files = sorted(glob.glob(f'{CAPTURE_DIR}/*.jpg'))
    if not files: return {"status": "error", "error": "No images"}
    try:
        with imageio.get_writer(VIDEO_PATH, fps=15, format='FFMPEG', quality=8) as writer:
            for filename in files:
                try: writer.append_data(imageio.imread(filename))
                except: continue
        return {"status": "done"}
    except Exception as e: return {"status": "error", "error": str(e)}

async def visual_tap(page, element, desc):
    try:
        await element.scroll_into_view_if_needed()
        box = await element.bounding_box()
        if box:
            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2
            # Visual Dot
            await page.evaluate(f"""
                var dot = document.createElement('div');
                dot.style.position = 'absolute'; dot.style.left = '{x}px'; dot.style.top = '{y}px';
                dot.style.width = '15px'; dot.style.height = '15px'; dot.style.background = 'rgba(255,0,0,0.7)';
                dot.style.borderRadius = '50%'; dot.style.zIndex = '999999'; 
                document.body.appendChild(dot);
            """)
            log_msg(f"👆 Tapping {desc}...")
            await page.touchscreen.tap(x, y)
            return True
    except: pass
    return False

async def burst_wait(page, seconds, step_name):
    log_msg(f"📸 Recording {step_name} ({seconds}s)...")
    frames = int(seconds / 0.2) # Optimized capture rate
    for i in range(frames):
        ts = datetime.now().strftime("%H%M%S%f")
        try: await page.screenshot(path=f"{CAPTURE_DIR}/{ts}_{step_name}.jpg")
        except: pass
        await asyncio.sleep(0.2)

# --- MAIN FLOW ---
async def run_russia_flow():
    current_number = generate_russia_number()
    log_msg(f"🎬 Starting New Session | Number: {current_number}")

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
            
            # --- STANDARD FLOW (Cookie -> Register -> Terms -> DOB -> Phone) ---
            # (Keeping it short for brevity, assuming standard selectors work)
            
            cookie = page.locator(".cookie-close-btn").first
            if await cookie.count() == 0: cookie = page.get_by_text("Accept", exact=True).first
            if await cookie.count() > 0: await visual_tap(page, cookie, "Cookie")

            reg_btn = page.get_by_text("Register", exact=True).first
            if await reg_btn.count() == 0: reg_btn = page.get_by_role("button", name="Register").first
            if await reg_btn.count() > 0:
                await visual_tap(page, reg_btn, "Register")
                await burst_wait(page, 3, "02_reg")

            agree = page.get_by_text("Agree", exact=True).first
            if await agree.count() == 0: agree = page.get_by_text("Next", exact=True).first
            if await agree.count() > 0:
                await visual_tap(page, agree, "Terms")
                await burst_wait(page, 3, "03_terms")

            # DOB Scroll
            await page.mouse.move(200, 500); await page.mouse.down()
            await page.mouse.move(200, 800, steps=20); await page.mouse.up()
            dob_next = page.get_by_text("Next", exact=True).first
            if await dob_next.count() > 0: await visual_tap(page, dob_next, "DOB")
            await burst_wait(page, 2, "04_dob")

            use_phone = page.get_by_text("Use phone number", exact=False).first
            if await use_phone.count() > 0: await visual_tap(page, use_phone, "PhoneOpt")
            await burst_wait(page, 2, "05_phone")

            # --- RUSSIA SWITCH ---
            log_msg("🌍 Switching Country...")
            hk = page.get_by_text("Hong Kong").first
            if await hk.count() == 0: hk = page.get_by_text("Country/Region").first
            
            if await hk.count() > 0:
                await visual_tap(page, hk, "Country")
                await burst_wait(page, 2, "06_list")
                
                search = page.locator("input").first
                if await search.count() > 0:
                    await visual_tap(page, search, "Search")
                    await page.keyboard.type("Russia", delay=100)
                    await burst_wait(page, 2, "07_typed")
                    
                    rus = page.get_by_text("Russia", exact=False).first
                    if await rus.count() > 0:
                        await visual_tap(page, rus, "Russia")
                        await burst_wait(page, 3, "08_set")

            # --- INPUT & CAPTCHA ---
            inp = page.locator("input[type='tel']").first
            if await inp.count() == 0: inp = page.locator("input").first
            
            if await inp.count() > 0:
                await visual_tap(page, inp, "Input")
                for c in current_number:
                    await page.keyboard.type(c); await asyncio.sleep(0.05)
                await page.touchscreen.tap(350, 100) # Close KB
                await burst_wait(page, 1, "09_ready")
                
                get_code = page.locator(".get-code-btn").first
                if await get_code.count() == 0: get_code = page.get_by_text("Get code").first
                
                if await get_code.count() > 0:
                    await visual_tap(page, get_code, "GET CODE")
                    log_msg("⏳ Waiting for Captcha Popup...")
                    
                    # Wait explicitly for the captcha frame
                    # We check every 1s for 15s
                    captcha_found = False
                    for _ in range(15):
                        if len(page.frames) > 1:
                            for frame in page.frames:
                                if await frame.get_by_text("swap 2 tiles", exact=False).count() > 0:
                                    captcha_found = True
                                    log_msg("🧩 CAPTCHA POPUP DETECTED!")
                                    
                                    # 🔥 CALL THE SOLVER HERE 🔥
                                    session_id = f"sess_{int(time.time())}"
                                    success = await solve_captcha(page, session_id, logger=log_msg)
                                    
                                    if success:
                                        log_msg("✅ AI Solver Finished Successfully!")
                                        await burst_wait(page, 5, "12_success")
                                    else:
                                        log_msg("❌ AI Solver Failed.")
                                        await burst_wait(page, 3, "12_fail")
                                    
                                    break
                        if captcha_found: break
                        await asyncio.sleep(1)
                    
                    if not captcha_found:
                        log_msg("❓ Captcha did not appear in time.")

        except Exception as e:
            log_msg(f"❌ Crash: {str(e)}")
        
        await browser.close()
        log_msg("🏁 Session Ended.")