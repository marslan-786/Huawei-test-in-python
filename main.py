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
app.mount("/captures", StaticFiles(directory=CAPTURE_DIR), name="captures")

# --- MONGODB ---
client = AsyncIOMotorClient(MONGO_URL)
db = client.huawei_bot
collection = db.captcha_dataset

# --- GLOBAL VARS ---
TOTAL_ATTEMPTS = 0
CAPTCHAS_FOUND = 0
MINING_ACTIVE = False
LIVE_VIEW_ACTIVE = False 

logs = []
def log_msg(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    logs.insert(0, entry)
    if len(logs) > 300: logs.pop()

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
        <title>Huawei Turtle Miner</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background: #000; color: #00e676; font-family: monospace; padding: 20px; text-align: center; }
            .stats-container { display: flex; justify-content: center; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }
            .card { background: #111; padding: 15px; border-radius: 8px; width: 140px; border: 1px solid #333; }
            .card h3 { margin: 0; font-size: 11px; color: #aaa; text-transform: uppercase; }
            .card h1 { margin: 5px 0 0 0; font-size: 28px; color: #fff; }
            .c-blue { color: #2979ff !important; } .c-gold { color: #ffd740 !important; }
            .btn { padding: 12px 20px; font-weight: bold; cursor: pointer; border:none; border-radius: 4px; font-size: 14px; margin: 5px; transition: 0.2s; width: 200px; }
            .btn-start { background: #00c853; color: black; }
            .btn-stop { background: #d50000; color: white; }
            .btn-live-on { background: #ff3d00; color: white; animation: pulse 2s infinite; }
            .btn-live-off { background: #37474f; color: #90a4ae; }
            @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(255, 61, 0, 0.7); } 70% { box-shadow: 0 0 0 10px rgba(255, 61, 0, 0); } 100% { box-shadow: 0 0 0 0 rgba(255, 61, 0, 0); } }
            .logs { height: 250px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; background: #0a0a0a; margin: 15px auto; width: 95%; font-size: 12px; color: #cfd8dc; font-family: 'Courier New', monospace; }
            .log-entry { padding: 2px 0; border-bottom: 1px solid #1a1a1a; }
            .live-container { margin-top: 20px; border: 2px solid #333; padding: 10px; display: none; background: #111; }
            .live-img { width: 100%; max-width: 350px; border: 2px solid #ff3d00; border-radius: 5px; }
            .live-badge { color: #ff3d00; font-weight: bold; margin-bottom: 5px; display: block; }
        </style>
    </head>
    <body>
        <h2>🐢 SUPER TURTLE MINER</h2>
        <div class="stats-container">
            <div class="card"><h3>Attempts</h3><h1 id="s-attempts" class="c-blue">0</h1></div>
            <div class="card"><h3>Captchas</h3><h1 id="s-found" class="c-gold">0</h1></div>
            <div class="card"><h3>DB Saved</h3><h1 id="s-saved">0</h1></div>
        </div>
        <div>
            <button class="btn btn-start" onclick="fetch('/start', {method: 'POST'})">🚀 START BOT</button>
            <button class="btn btn-stop" onclick="fetch('/stop', {method: 'POST'})">🛑 STOP BOT</button>
        </div>
        <div style="margin-top: 10px;">
            <button id="btn-live" class="btn btn-live-off" onclick="toggleLive()">🔴 START LIVE ACTIVITY</button>
        </div>
        <div id="live-box" class="live-container">
            <span class="live-badge">● LIVE FEED (1s Update)</span>
            <img id="live-feed" src="" class="live-img" />
        </div>
        <div class="logs" id="logs">Waiting for logs...</div>
        <script>
            let liveActive = false;
            function refreshStats() {
                fetch('/status').then(r=>r.json()).then(d=>{
                    document.getElementById('logs').innerHTML = d.logs.map(l=>`<div class="log-entry">${l}</div>`).join('');
                    document.getElementById('s-attempts').innerText = d.stats.attempts;
                    document.getElementById('s-found').innerText = d.stats.found;
                    document.getElementById('s-saved').innerText = d.stats.saved_db;
                    if(d.live_active && liveActive) document.getElementById('live-feed').src = "/captures/live_monitor.jpg?t=" + new Date().getTime();
                });
            }
            function toggleLive() {
                liveActive = !liveActive;
                const btn = document.getElementById('btn-live');
                const box = document.getElementById('live-box');
                if (liveActive) {
                    fetch('/live/start', {method: 'POST'});
                    btn.className = "btn btn-live-on"; btn.innerText = "⚫ STOP LIVE ACTIVITY"; box.style.display = "block";
                } else {
                    fetch('/live/stop', {method: 'POST'});
                    btn.className = "btn btn-live-off"; btn.innerText = "🔴 START LIVE ACTIVITY"; box.style.display = "none";
                }
            }
            setInterval(refreshStats, 2000);
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status():
    try: saved_count = await collection.count_documents({})
    except: saved_count = "Err"
    return JSONResponse({
        "logs": logs,
        "stats": {"attempts": TOTAL_ATTEMPTS, "found": CAPTCHAS_FOUND, "saved_db": saved_count},
        "live_active": LIVE_VIEW_ACTIVE
    })

@app.post("/start")
async def start_mining(bt: BackgroundTasks):
    global MINING_ACTIVE
    if not MINING_ACTIVE:
        MINING_ACTIVE = True
        bt.add_task(run_turtle_loop)
    return {"status": "started"}

@app.post("/stop")
async def stop_mining():
    global MINING_ACTIVE
    MINING_ACTIVE = False
    log_msg("🛑 STOP COMMAND RECEIVED. Finishing cycle...")
    return {"status": "stopping"}

@app.post("/live/start")
async def start_live():
    global LIVE_VIEW_ACTIVE
    LIVE_VIEW_ACTIVE = True
    return {"status": "live_on"}

@app.post("/live/stop")
async def stop_live():
    global LIVE_VIEW_ACTIVE
    LIVE_VIEW_ACTIVE = False
    return {"status": "live_off"}

async def do_live_update(page):
    if LIVE_VIEW_ACTIVE:
        try: await page.screenshot(path=f"{CAPTURE_DIR}/live_monitor.jpg")
        except: pass

# --- SMART CLICK FUNCTION ---
async def smart_click(page, selector, desc, wait_time=5):
    """Waits for element to appear, scrolls to it, and clicks."""
    log_msg(f"🔍 Finding: {desc}...")
    try:
        # Wait up to 10 seconds for the element to appear in DOM
        element = page.locator(selector).first
        await element.wait_for(state="visible", timeout=10000)
        
        # Scroll & Click
        await element.scroll_into_view_if_needed()
        box = await element.bounding_box()
        if box:
            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2
            await page.touchscreen.tap(x, y)
            log_msg(f"✅ CLICKED: {desc}")
            await do_live_update(page)
            
            # TURTLE DELAY (Wait after every success)
            log_msg(f"⏳ Waiting {wait_time}s (Turtle Mode)...")
            await asyncio.sleep(wait_time) 
            return True
            
    except Exception as e:
        log_msg(f"❌ NOT FOUND / CLICK FAILED: {desc}")
        await do_live_update(page)
    return False

# --- 🐢 TURTLE MINING LOOP ---
async def run_turtle_loop():
    global MINING_ACTIVE, TOTAL_ATTEMPTS, CAPTCHAS_FOUND
    log_msg("🐢 TURTLE MINING STARTED (Slow & Steady)...")

    while MINING_ACTIVE:
        browser = None
        try:
            async with async_playwright() as p:
                target_number = get_random_number()
                TOTAL_ATTEMPTS += 1
                
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                    proxy=PROXY_CONFIG
                )
                
                context = await browser.new_context(
                    viewport={'width': 412, 'height': 950},
                    user_agent="Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.101 Mobile Safari/537.36",
                    locale="en-US"
                )
                page = await context.new_page()
                
                log_msg(f"🎬 CYCLE #{TOTAL_ATTEMPTS} START")
                
                # 1. LOAD PAGE (Super Wait)
                log_msg(f"🌍 Loading Page...")
                try:
                    await page.goto(BASE_URL, timeout=90000, wait_until='domcontentloaded')
                except:
                    log_msg("❌ Network Timeout. Restarting...")
                    await browser.close()
                    continue
                
                log_msg("⏳ Letting page settle (8s)...")
                await asyncio.sleep(8) 
                await do_live_update(page)

                # 2. COOKIE (Ignore errors if not found)
                await smart_click(page, "text=Accept", "Cookie", wait_time=2)

                # 3. REGISTER (Critical Step)
                # We try two selectors for Register
                if not await smart_click(page, "button:has-text('Register')", "Register Button", wait_time=8):
                    if not await smart_click(page, "text=Register", "Register Text", wait_time=8):
                        log_msg("⚠️ Register button missing. Aborting cycle.")
                        await browser.close()
                        continue # Restart loop

                # 4. TERMS
                if not await smart_click(page, "text=Agree", "Agree Button", wait_time=6):
                     await smart_click(page, "text=Next", "Next Button", wait_time=6)

                # 5. DOB (Scroll and Next)
                if await page.get_by_text("Date of birth").count() > 0:
                    log_msg("🖱️ Scrolling DOB...")
                    await page.mouse.move(200, 600)
                    await page.mouse.down()
                    await page.mouse.move(200, 800, steps=50) # Very slow scroll
                    await page.mouse.up()
                    await asyncio.sleep(2)
                    await do_live_update(page)
                    
                    await smart_click(page, "text=Next", "DOB Next", wait_time=5)

                # 6. PHONE OPTION
                await smart_click(page, "text=Use phone number", "Use Phone Option", wait_time=5)

                # 7. COUNTRY SWITCH
                log_msg("🌍 Switching Country...")
                # Try to click country selector
                if await smart_click(page, "text=Hong Kong", "HK Selector", wait_time=5) or \
                   await smart_click(page, "text=Country/Region", "Region Selector", wait_time=5):
                    
                    # Search
                    await smart_click(page, "input", "Search Box", wait_time=2)
                    log_msg("⌨️ Typing 'Russia'...")
                    await page.keyboard.type("Russia", delay=150) # Slow typing
                    await asyncio.sleep(3)
                    await do_live_update(page)
                    
                    await smart_click(page, "text=Russia", "Russia Option", wait_time=5)

                # 8. INPUT NUMBER
                log_msg(f"⌨️ Inputting Number...")
                if await smart_click(page, "input[type='tel']", "Number Field", wait_time=2):
                    await page.keyboard.type(target_number, delay=100)
                    await asyncio.sleep(1)
                    await page.touchscreen.tap(350, 100) # Hide keyboard
                    await asyncio.sleep(2)
                    await do_live_update(page)

                    # 9. GET CODE
                    if await smart_click(page, ".get-code-btn", "GET CODE", wait_time=2) or \
                       await smart_click(page, "text=Get code", "GET CODE Text", wait_time=2):
                        
                        log_msg("⏳ Waiting 20s for Captcha...")
                        
                        # Wait Loop for Captcha
                        captcha_frame = None
                        for i in range(20):
                            for frame in page.frames:
                                if await frame.get_by_text("swap 2 tiles", exact=False).count() > 0:
                                    captcha_frame = frame
                                    break
                            if captcha_frame: break
                            if i % 3 == 0: await do_live_update(page)
                            await asyncio.sleep(1)
                        
                        if captcha_frame:
                            CAPTCHAS_FOUND += 1
                            log_msg("🎉 CAPTCHA FOUND!")
                            
                            # Clean Crop & Save
                            try:
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
                                    log_msg(f"💾 DATA SAVED: {filename}")
                                    
                                    await collection.insert_one({
                                        "filename": filename, "timestamp": datetime.now(),
                                        "number": target_number, "status": "raw_dataset"
                                    })
                            except Exception as save_err:
                                log_msg(f"⚠️ Save Error: {save_err}")
                        else:
                            log_msg("❌ No Captcha appeared.")

        except Exception as e:
            log_msg(f"⚠️ CRASH: {str(e)[:50]}")
        
        finally:
            if browser:
                log_msg("💤 Cooling down (10s)...")
                await browser.close()
                await asyncio.sleep(10)