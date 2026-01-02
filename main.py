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

# --- IMPORT SOLVER ---
try:
    from captcha_solver import solve_captcha
except ImportError:
    print("❌ ERROR: captcha_solver.py not found!")
    async def solve_captcha(page, session_id, logger=print): return False

# --- CONFIGURATION ---
CAPTURE_DIR = "./captures"
VIDEO_PATH = f"{CAPTURE_DIR}/proof.mp4"
NUMBERS_FILE = "numbers.txt"
BASE_URL = "https://id5.cloud.huawei.com"
TARGET_COUNTRY = "Russia"

PROXY_CONFIG = {
    "server": "http://p.webshare.io:80", 
    "username": "klxgqgei-rotate", 
    "password": "upjk9roh3rhi"
}

app = FastAPI()
if not os.path.exists(CAPTURE_DIR): os.makedirs(CAPTURE_DIR)
app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

# --- GLOBAL STATE ---
BOT_RUNNING = False
logs = []

def log_msg(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    logs.insert(0, entry)
    if len(logs) > 500: logs.pop()

def get_next_number():
    """Reads from numbers.txt or generates random"""
    if os.path.exists(NUMBERS_FILE):
        with open(NUMBERS_FILE, "r") as f:
            lines = f.read().splitlines()
        for num in lines:
            # Simple logic: Just pick random from file for now, 
            # or implement a cursor system if needed.
            # Here we pick a random one from file to simulate 'next'
            if num.strip(): return num.strip()
    
    # Fallback to generator
    prefix = "9"
    rest = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    return f"{prefix}{rest}"

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei Smart Bot</title>
        <style>
            body { background: #0a0a0a; color: #00e676; font-family: 'Courier New', monospace; padding: 20px; text-align: center; }
            button { padding: 15px 30px; font-weight: bold; cursor: pointer; border:none; margin:5px; border-radius: 5px; font-size: 16px; transition: 0.3s; }
            
            .btn-start { background: #6200ea; color: white; }
            .btn-start:hover { background: #7c4dff; }
            
            .btn-stop { background: #d50000; color: white; }
            .btn-stop:hover { background: #ff1744; }

            .status-bar { background: #333; color: yellow; padding: 10px; margin: 10px auto; width: 80%; border-radius: 5px; display: none; }
            .logs { height: 300px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; background: #111; margin-bottom: 20px; font-size: 12px; color: #ccc; }
            #video-section { display:none; margin: 20px auto; border: 2px solid #00e676; padding:10px; background: #111; width: fit-content; border-radius: 10px; }
            .gallery { display: flex; flex-wrap: wrap; justify-content: center; gap: 2px; margin-top: 20px; }
            .gallery img { height: 60px; border: 1px solid #333; opacity: 0.8; }
            .gallery img:hover { height: 150px; border-color: white; opacity: 1; z-index:999; }
        </style>
    </head>
    <body>
        <h1>🇷🇺 HUAWEI SMART LOOP BOT</h1>
        <p>Persistent Session | Auto-Retry Logic | Number List</p>
        
        <div>
            <button id="btn-toggle" onclick="toggleBot()" class="btn-start">🚀 START BOT</button>
            <button onclick="makeVideo()" style="background: #0091ea; color: white;">🎬 MAKE VIDEO</button>
            <button onclick="clearLogs()" style="background: #424242; color: white;">🗑️ CLEAR</button>
        </div>

        <div id="status-bar" class="status-bar"></div>
        <div class="logs" id="logs">Waiting...</div>
        
        <div id="video-section">
            <h3 style="margin:0 0 10px 0;">🎬 REPLAY</h3>
            <video id="v-player" controls width="500" autoplay loop></video>
        </div>

        <h3>🎞️ LIVE FEED</h3>
        <div class="gallery" id="gallery"></div>

        <script>
            function toggleBot() {
                const btn = document.getElementById('btn-toggle');
                // We check current state from text (simplified) or fetch
                if (btn.innerText.includes("START")) {
                    fetch('/start', {method: 'POST'});
                    logUpdate(">>> SENDING START COMMAND...");
                } else {
                    fetch('/stop', {method: 'POST'});
                    logUpdate(">>> SENDING STOP COMMAND...");
                }
                // UI update happens in refreshData
            }
            
            function clearLogs() { fetch('/clear_logs', {method:'POST'}); }

            function refreshData() {
                fetch('/status').then(r=>r.json()).then(d=>{
                    // 1. Update Logs
                    document.getElementById('logs').innerHTML = d.logs.map(l=>`<div>${l}</div>`).join('');
                    
                    // 2. Update Gallery
                    document.getElementById('gallery').innerHTML = d.images.map(i=>`<img src="${i}">`).join('');
                    
                    // 3. Update Button State (Persistence)
                    const btn = document.getElementById('btn-toggle');
                    if (d.running) {
                        btn.innerText = "🛑 STOP BOT";
                        btn.className = "btn-stop";
                    } else {
                        btn.innerText = "🚀 START BOT";
                        btn.className = "btn-start";
                    }
                });
            }

            function makeVideo() {
                var status = document.getElementById('status-bar');
                status.style.display = 'block';
                status.innerText = "⏳ GENERATING VIDEO...";
                fetch('/generate_video', {method: 'POST'}).then(r=>r.json()).then(d=>{
                    if(d.status === "done") {
                        status.innerText = "✅ VIDEO READY!";
                        document.getElementById('video-section').style.display = 'block';
                        var player = document.getElementById('v-player');
                        player.src = "/captures/proof.mp4?t=" + Date.now();
                        player.load(); player.play();
                    } else {
                        status.innerText = "❌ ERROR: " + d.error;
                    }
                });
            }

            function logUpdate(msg) { 
                var l = document.getElementById('logs');
                l.innerHTML = "<div>" + msg + "</div>" + l.innerHTML; 
            }
            
            setInterval(refreshData, 2000); // Poll every 2s
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status():
    files = sorted(glob.glob(f'{CAPTURE_DIR}/*.jpg'), key=os.path.getmtime, reverse=True)
    urls = [f"/captures/{os.path.basename(f)}" for f in files]
    return JSONResponse({"logs": logs, "images": urls, "running": BOT_RUNNING})

@app.post("/start")
async def start_bot(bt: BackgroundTasks):
    global BOT_RUNNING
    if not BOT_RUNNING:
        BOT_RUNNING = True
        bt.add_task(master_loop) # Run the Master Loop
    return {"status": "started"}

@app.post("/stop")
async def stop_bot():
    global BOT_RUNNING
    BOT_RUNNING = False
    log_msg("🛑 STOP COMMAND RECEIVED. Finishing current step...")
    return {"status": "stopping"}

@app.post("/clear_logs")
async def clear_logs_endpoint():
    global logs
    logs = []
    # Optional: Clear images too? 
    # for f in glob.glob(f'{CAPTURE_DIR}/*.jpg'): os.remove(f)
    return {"status": "cleared"}

@app.post("/generate_video")
async def trigger_video():
    files = sorted(glob.glob(f'{CAPTURE_DIR}/*.jpg'))
    if not files: return {"status": "error", "error": "No images"}
    try:
        with imageio.get_writer(VIDEO_PATH, fps=10, format='FFMPEG', quality=8) as writer:
            for filename in files:
                try: writer.append_data(imageio.imread(filename))
                except: continue
        return {"status": "done"}
    except Exception as e: return {"status": "error", "error": str(e)}

# --- HELPER FUNCTIONS ---
async def visual_tap(page, element, desc):
    try:
        await element.scroll_into_view_if_needed()
        box = await element.bounding_box()
        if box:
            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2
            await page.evaluate(f"""
                var dot = document.createElement('div');
                dot.style.position = 'absolute'; left = '{x}px'; top = '{y}px';
                dot.style.width = '15px'; dot.style.height = '15px'; dot.style.background = 'rgba(255,0,0,0.6)';
                dot.style.borderRadius = '50%'; dot.style.zIndex = '999999'; dot.style.pointerEvents='none';
                document.body.appendChild(dot);
            """)
            log_msg(f"👆 Tapping {desc}...")
            await page.touchscreen.tap(x, y)
            return True
    except: pass
    return False

async def burst_wait(page, seconds, step_name):
    log_msg(f"📸 Wait {step_name} ({seconds}s)...")
    frames = int(seconds / 0.2)
    for i in range(frames):
        if not BOT_RUNNING: break # Immediate stop check
        ts = datetime.now().strftime("%H%M%S%f")
        try: await page.screenshot(path=f"{CAPTURE_DIR}/{ts}_{step_name}.jpg")
        except: pass
        await asyncio.sleep(0.2)

# --- CORE LOGIC LOOP ---
async def master_loop():
    """Keeps running continuously until STOP is pressed"""
    
    current_number = get_next_number()
    retry_same_number = False

    while BOT_RUNNING:
        # If we need to retry same number, don't fetch new one
        if not retry_same_number:
            current_number = get_next_number()
        
        log_msg(f"🎬 SESSION START | Number: {current_number}")
        
        # Result flag: 
        # 'success' -> Next Number
        # 'fail' -> Retry Same Number
        result = await run_single_session(current_number)
        
        if result == "success":
            log_msg("🎉 Number Verified! Moving to next...")
            retry_same_number = False
        elif result == "ai_fail":
            log_msg("⚠️ AI Failed or Error. Retrying SAME Number...")
            retry_same_number = True
        else:
            # Stopped manually or crash
            break
        
        await asyncio.sleep(2)

async def run_single_session(phone_number):
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
            if not BOT_RUNNING: return "stopped"
            log_msg("🚀 Navigating...")
            await page.goto(BASE_URL, timeout=60000)
            await burst_wait(page, 2, "01_load")

            # --- STANDARD FLOW ---
            cookie = page.locator(".cookie-close-btn").first
            if await cookie.count() == 0: cookie = page.get_by_text("Accept", exact=True).first
            if await cookie.count() > 0: await visual_tap(page, cookie, "Cookie")

            reg_btn = page.get_by_text("Register", exact=True).first
            if await reg_btn.count() == 0: reg_btn = page.get_by_role("button", name="Register").first
            if await reg_btn.count() > 0:
                await visual_tap(page, reg_btn, "Register")
                await burst_wait(page, 2, "02_reg")

            agree = page.get_by_text("Agree", exact=True).first
            if await agree.count() == 0: agree = page.get_by_text("Next", exact=True).first
            if await agree.count() > 0:
                await visual_tap(page, agree, "Terms")
                await burst_wait(page, 2, "03_terms")

            # DOB
            await page.mouse.move(200, 500); await page.mouse.down()
            await page.mouse.move(200, 800, steps=10); await page.mouse.up()
            dob_next = page.get_by_text("Next", exact=True).first
            if await dob_next.count() > 0: await visual_tap(page, dob_next, "DOB")
            await burst_wait(page, 2, "04_dob")

            use_phone = page.get_by_text("Use phone number", exact=False).first
            if await use_phone.count() > 0: await visual_tap(page, use_phone, "PhoneOpt")
            
            # RUSSIA
            log_msg("🌍 Switching Country...")
            hk = page.get_by_text("Hong Kong").first
            if await hk.count() == 0: hk = page.get_by_text("Country/Region").first
            if await hk.count() > 0:
                await visual_tap(page, hk, "Country")
                await burst_wait(page, 2, "06_list")
                search = page.locator("input").first
                if await search.count() > 0:
                    await visual_tap(page, search, "Search")
                    await page.keyboard.type("Russia", delay=50)
                    await burst_wait(page, 2, "07_typed")
                    rus = page.get_by_text("Russia", exact=False).first
                    if await rus.count() > 0: await visual_tap(page, rus, "Russia")

            # INPUT
            inp = page.locator("input[type='tel']").first
            if await inp.count() == 0: inp = page.locator("input").first
            if await inp.count() > 0:
                await visual_tap(page, inp, "Input")
                for c in phone_number:
                    if not BOT_RUNNING: return "stopped"
                    await page.keyboard.type(c); await asyncio.sleep(0.05)
                await page.touchscreen.tap(350, 100) # Close KB
                
                get_code = page.locator(".get-code-btn").first
                if await get_code.count() == 0: get_code = page.get_by_text("Get code").first
                
                if await get_code.count() > 0:
                    await visual_tap(page, get_code, "GET CODE")
                    log_msg("⏳ Monitoring for Captcha...")
                    
                    # --- 🔥 SMART CAPTCHA LOOP 🔥 ---
                    captcha_start_time = time.time()
                    
                    while BOT_RUNNING:
                        # Safety break after 60s of struggle
                        if time.time() - captcha_start_time > 60:
                            log_msg("⏰ Timeout waiting/solving. Restarting.")
                            return "ai_fail"

                        # 1. Check if Captcha Frame Exists
                        captcha_frame = None
                        for frame in page.frames:
                            try:
                                if await frame.get_by_text("swap 2 tiles", exact=False).count() > 0:
                                    captcha_frame = frame
                                    break
                            except: pass
                        
                        if captcha_frame:
                            log_msg("🧩 CAPTCHA DETECTED! Calling AI...")
                            
                            # Solve
                            session_id = f"sess_{int(time.time())}"
                            ai_success = await solve_captcha(page, session_id, logger=log_msg)
                            
                            if not ai_success:
                                log_msg("⚠️ AI returned Error/No Match. Restarting Session.")
                                return "ai_fail" # Restart Same Number
                            
                            # If AI said "Drag Done", Verify Result
                            log_msg("⏳ Checking result (10s wait)...")
                            await burst_wait(page, 10, "11_verify")
                            
                            # Check if frame is GONE
                            is_still_there = False
                            for frame in page.frames:
                                try:
                                    if await frame.get_by_text("swap 2 tiles", exact=False).count() > 0:
                                        is_still_there = True
                                        break
                                except: pass
                            
                            if not is_still_there:
                                log_msg("✅ CAPTCHA GONE! SUCCESS!")
                                await burst_wait(page, 3, "12_success")
                                return "success" # Next Number
                            else:
                                log_msg("🔁 Captcha still there (Failed). Retrying loop...")
                                await asyncio.sleep(2) # Breath before loop restarts
                                continue
                        
                        else:
                            # Frame not found yet, keep waiting
                            await asyncio.sleep(1)

            await browser.close()
            return "success" # Assumed success if no captcha triggered? Or fail?

        except Exception as e:
            log_msg(f"❌ Crash: {str(e)}")
            await browser.close()
            return "ai_fail" # Retry on crash