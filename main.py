import os
import glob
import asyncio
import random
import time
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright
from motor.motor_asyncio import AsyncIOMotorClient

# --- CONFIGURATION ---
CAPTURE_DIR = "./captures"
DATASET_DIR = "./dataset_training"
NUMBERS_FILE = "numbers.txt"
BASE_URL = "https://id5.cloud.huawei.com"
MONGO_URL = "mongodb://mongo:AEvrikOWlrmJCQrDTQgfGtqLlwhwLuAA@crossover.proxy.rlwy.net:29609"

PROXY_CONFIG = {
    "server": "http://p.webshare.io:80", 
    "username": "wwwsyxzg-rotate", 
    "password": "582ygxexguhx"
}

app = FastAPI()

if not os.path.exists(CAPTURE_DIR): os.makedirs(CAPTURE_DIR)
if not os.path.exists(DATASET_DIR): os.makedirs(DATASET_DIR)

app.mount("/dataset", StaticFiles(directory=DATASET_DIR), name="dataset")

# --- MONGODB ---
client = AsyncIOMotorClient(MONGO_URL)
db = client.huawei_bot
collection = db.captcha_dataset

# --- GLOBAL STATS ---
TOTAL_ATTEMPTS = 0
CAPTCHAS_FOUND = 0
MINING_ACTIVE = False

logs = []
def log_msg(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    logs.insert(0, entry)
    if len(logs) > 200: logs.pop()

def get_random_number():
    prefix = "9"
    rest = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    return f"{prefix}{rest}"

# --- DASHBOARD UI ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei Data Miner v2</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background: #0f0f0f; color: #e0e0e0; font-family: 'Segoe UI', monospace; padding: 20px; text-align: center; }
            .stats-container { display: flex; justify-content: center; gap: 20px; margin-bottom: 20px; flex-wrap: wrap; }
            .card { background: #1e1e1e; padding: 15px; border-radius: 8px; width: 150px; border: 1px solid #333; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
            .card h3 { margin: 0; font-size: 14px; color: #aaa; }
            .card h1 { margin: 10px 0 0 0; font-size: 32px; color: #fff; }
            .c-blue { color: #2979ff !important; }
            .c-green { color: #00e676 !important; }
            .c-yellow { color: #ffea00 !important; }
            .btn { padding: 12px 25px; font-weight: bold; cursor: pointer; border:none; border-radius: 6px; font-size: 14px; margin: 5px; transition: 0.2s; }
            .btn:hover { transform: scale(1.05); }
            .btn-start { background: #6200ea; color: white; }
            .btn-stop { background: #d50000; color: white; }
            .btn-refresh { background: #00bfa5; color: white; }
            .btn-gallery { background: #ff6d00; color: white; }
            .logs { height: 200px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; background: #000; margin: 20px auto; width: 90%; color: #ccc; font-size: 12px; border-radius: 5px; }
            .hidden { display: none; }
            .gallery-container { margin-top: 20px; border-top: 1px solid #333; padding-top: 20px; }
            .gallery { display: flex; flex-wrap: wrap; justify-content: center; gap: 5px; }
            .gallery img { height: 100px; border: 1px solid #444; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h2 style="color: #2979ff;">⛏️ SAFE MINING DASHBOARD (Auto-Restart)</h2>

        <div class="stats-container">
            <div class="card">
                <h3>ATTEMPTS</h3>
                <h1 id="s-attempts" class="c-blue">0</h1>
            </div>
            <div class="card">
                <h3>CAPTCHAS</h3>
                <h1 id="s-found" class="c-yellow">0</h1>
            </div>
            <div class="card">
                <h3>SAVED (DB)</h3>
                <h1 id="s-saved" class="c-green">0</h1>
            </div>
        </div>

        <div>
            <button class="btn btn-start" onclick="startBot()">🚀 START SAFE MINING</button>
            <button class="btn btn-stop" onclick="stopBot()">🛑 STOP</button>
            <button class="btn btn-refresh" onclick="refreshStats()">🔄 CHECK RESULT</button>
        </div>

        <div class="logs" id="logs">Waiting...</div>
        
        <div class="gallery-container">
            <button id="btn-gal" class="btn btn-gallery" onclick="toggleGallery()">👁️ VIEW CAPTCHAS</button>
            <div id="gallery-wrapper" class="hidden">
                <p style="font-size: 12px; color: #888;">(Latest 50 Captures)</p>
                <div class="gallery" id="gallery"></div>
            </div>
        </div>

        <script>
            let showGallery = false;
            function startBot() { fetch('/start', {method: 'POST'}); logUpdate(">>> COMMAND: START"); }
            function stopBot() { fetch('/stop', {method: 'POST'}); logUpdate(">>> COMMAND: STOP"); }
            
            function refreshStats() {
                fetch('/status?gallery=' + showGallery).then(r=>r.json()).then(d=>{
                    document.getElementById('logs').innerHTML = d.logs.map(l=>`<div>${l}</div>`).join('');
                    document.getElementById('s-attempts').innerText = d.stats.attempts;
                    document.getElementById('s-found').innerText = d.stats.found;
                    document.getElementById('s-saved').innerText = d.stats.saved_db;
                    if (showGallery) {
                        document.getElementById('gallery').innerHTML = d.images.map(i=>`<a href="${i}" target="_blank"><img src="${i}"></a>`).join('');
                    }
                });
            }

            function toggleGallery() {
                showGallery = !showGallery;
                const wrapper = document.getElementById('gallery-wrapper');
                const btn = document.getElementById('btn-gal');
                if (showGallery) {
                    wrapper.classList.remove('hidden'); btn.innerText = "❌ CLOSE CAPTCHAS"; btn.style.background = "#d50000"; refreshStats();
                } else {
                    wrapper.classList.add('hidden'); btn.innerText = "👁️ VIEW CAPTCHAS"; btn.style.background = "#ff6d00"; document.getElementById('gallery').innerHTML = "";
                }
            }
            function logUpdate(msg) { var logs = document.getElementById('logs'); logs.innerHTML = "<div>[" + new Date().toLocaleTimeString() + "] " + msg + "</div>" + logs.innerHTML; }
            setInterval(refreshStats, 3000);
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status(gallery: str = "false"):
    try: saved_count = await collection.count_documents({})
    except: saved_count = "Err"

    response = {
        "logs": logs,
        "stats": {"attempts": TOTAL_ATTEMPTS, "found": CAPTCHAS_FOUND, "saved_db": saved_count},
        "images": []
    }
    if gallery == "true":
        files = sorted(glob.glob(f'{DATASET_DIR}/*.jpg'), key=os.path.getmtime, reverse=True)[:50]
        response["images"] = [f"/dataset/{os.path.basename(f)}" for f in files]
    return JSONResponse(response)

@app.post("/start")
async def start_mining(bt: BackgroundTasks):
    global MINING_ACTIVE
    if not MINING_ACTIVE:
        MINING_ACTIVE = True
        bt.add_task(run_mining_loop)
    return {"status": "started"}

@app.post("/stop")
async def stop_mining():
    global MINING_ACTIVE
    MINING_ACTIVE = False
    log_msg("🛑 Stopping after current cycle...")
    return {"status": "stopping"}

async def visual_tap(page, element, desc):
    try:
        await element.scroll_into_view_if_needed()
        box = await element.bounding_box()
        if box:
            x = box['x'] + box['width'] / 2; y = box['y'] + box['height'] / 2
            await page.touchscreen.tap(x, y)
            return True
    except: pass
    return False

# --- 🔥 ROBUST MINING LOOP (RESTART BROWSER EVERY TIME) ---
async def run_mining_loop():
    global MINING_ACTIVE, TOTAL_ATTEMPTS, CAPTCHAS_FOUND
    log_msg("🔥 Safe Mining Started (Browser will restart every cycle)...")

    # We instantiate playwright only once, but launch browser repeatedly
    async with async_playwright() as p:
        pixel_5 = p.devices['Pixel 5'].copy()
        pixel_5['user_agent'] = "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.101 Mobile Safari/537.36"
        pixel_5['viewport'] = {'width': 412, 'height': 950} 

        while MINING_ACTIVE:
            browser = None
            try:
                target_number = get_random_number()
                TOTAL_ATTEMPTS += 1
                
                # 1. LAUNCH NEW BROWSER INSTANCE (Clean Slate)
                # log_msg(f"🔄 Launching Fresh Browser for #{target_number}")
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                    proxy=PROXY_CONFIG
                )
                
                context = await browser.new_context(**pixel_5, locale="en-US")
                page = await context.new_page()

                # 2. EXECUTE FLOW
                log_msg(f"🚀 Navigating (Attempt #{TOTAL_ATTEMPTS})")
                await page.goto(BASE_URL, timeout=40000)
                await asyncio.sleep(1.5)
                
                # --- FAST STEPS ---
                if await page.get_by_text("Accept", exact=True).count() > 0:
                    await visual_tap(page, page.get_by_text("Accept", exact=True).first, "Cookie")
                
                reg = page.get_by_role("button", name="Register").first
                if await reg.count() > 0: await visual_tap(page, reg, "Register")
                await asyncio.sleep(1.5)

                agree = page.get_by_text("Agree", exact=True).first
                if await agree.count() > 0: await visual_tap(page, agree, "Agree")
                await asyncio.sleep(1.5)

                await page.mouse.move(200, 600); await page.mouse.down(); await page.mouse.move(200, 700, steps=5); await page.mouse.up()
                nxt = page.get_by_text("Next", exact=True).first
                if await nxt.count() > 0: await visual_tap(page, nxt, "DOB Next")
                await asyncio.sleep(1)

                ph = page.get_by_text("Use phone number", exact=False).first
                if await ph.count() > 0: await visual_tap(page, ph, "Phone Option")
                await asyncio.sleep(1)

                # Country Switch
                hk = page.get_by_text("Hong Kong").first
                if await hk.count() == 0: hk = page.get_by_text("Country/Region").first
                if await hk.count() > 0:
                    await visual_tap(page, hk, "Country List")
                    await asyncio.sleep(1)
                    if await page.locator("input").count() > 0:
                        await page.locator("input").first.click()
                        await page.keyboard.type("Russia", delay=30)
                        await asyncio.sleep(1)
                        rus = page.get_by_text("Russia", exact=False).first
                        if await rus.count() > 0: await visual_tap(page, rus, "Russia")
                
                # Input Number
                inp = page.locator("input[type='tel']").first
                if await inp.count() == 0: inp = page.locator("input").first
                
                if await inp.count() > 0:
                    await inp.click()
                    await page.keyboard.type(target_number)
                    await page.touchscreen.tap(350, 100)
                    
                    get_code = page.locator(".get-code-btn").first
                    if await get_code.count() > 0:
                        await visual_tap(page, get_code, "Get Code")
                        
                        # Wait for Captcha (Max 8s)
                        captcha_frame = None
                        for _ in range(8):
                            for frame in page.frames:
                                if await frame.get_by_text("swap 2 tiles", exact=False).count() > 0:
                                    captcha_frame = frame
                                    break
                            if captcha_frame: break
                            await asyncio.sleep(1)
                        
                        if captcha_frame:
                            CAPTCHAS_FOUND += 1
                            log_msg("🧩 CAPTCHA CAPTURED!")
                            
                            header = captcha_frame.get_by_text("Please complete verification", exact=False).first
                            footer = captcha_frame.get_by_text("swap 2 tiles", exact=False).first
                            
                            if await header.count() > 0 and await footer.count() > 0:
                                hb = await header.bounding_box()
                                fb = await footer.bounding_box()
                                
                                top_pad = 25
                                grid_y = hb['y'] + hb['height'] + top_pad
                                grid_h = fb['y'] - grid_y - 10
                                center_x = fb['x'] + (fb['width'] / 2)
                                grid_w = 340
                                grid_x = center_x - (grid_w / 2)
                                
                                ts = int(time.time())
                                filename = f"captcha_{ts}_{target_number}.jpg"
                                filepath = f"{DATASET_DIR}/{filename}"
                                
                                await page.screenshot(path=filepath, clip={
                                    "x": grid_x, "y": grid_y, "width": grid_w, "height": grid_h
                                })
                                log_msg(f"✅ SAVED to Dataset")
                                
                                try:
                                    await collection.insert_one({
                                        "filename": filename, "timestamp": datetime.now(),
                                        "number": target_number, "status": "unsolved"
                                    })
                                except: pass
                        else:
                            log_msg("❌ No Captcha")

            except Exception as e:
                log_msg(f"⚠️ Error: {str(e)[:50]}...")
            
            finally:
                # 3. CLOSE BROWSER COMPLETELY (Anti-Fingerprinting)
                if browser:
                    await browser.close()
                    # log_msg("🔒 Browser Session Closed. Cooldown...")
                
                # Optional: Add small random delay to look human
                await asyncio.sleep(random.uniform(1, 3))