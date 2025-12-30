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

# --- MONGODB ---
client = AsyncIOMotorClient(MONGO_URL)
db = client.huawei_bot
collection = db.captcha_dataset

# --- GLOBAL VARS ---
TOTAL_ATTEMPTS = 0
CAPTCHAS_FOUND = 0
MINING_ACTIVE = False

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
        <title>Huawei 12H Miner</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background: #050505; color: #b0bec5; font-family: monospace; padding: 20px; text-align: center; }
            .stats-container { display: flex; justify-content: center; gap: 20px; margin-bottom: 20px; }
            .card { background: #151515; padding: 20px; border-radius: 8px; width: 160px; border: 1px solid #333; }
            .card h3 { margin: 0; font-size: 12px; color: #78909c; }
            .card h1 { margin: 10px 0 0 0; font-size: 36px; color: #fff; }
            .c-blue { color: #4fc3f7 !important; } .c-green { color: #00e676 !important; } .c-gold { color: #ffd740 !important; }
            .btn { padding: 15px 30px; font-weight: bold; cursor: pointer; border:none; border-radius: 5px; font-size: 16px; margin: 10px; transition: 0.3s; }
            .btn-start { background: #2e7d32; color: white; }
            .btn-stop { background: #c62828; color: white; }
            .btn-check { background: #0277bd; color: white; }
            .logs { height: 300px; overflow-y: auto; text-align: left; border: 1px solid #222; padding: 10px; background: #000; margin: 20px auto; width: 95%; font-size: 11px; color: #90a4ae; }
            .hidden { display: none; }
            .gallery img { height: 80px; border: 1px solid #333; margin: 2px; }
        </style>
    </head>
    <body>
        <h2 style="color: #4fc3f7;">🌙 OVERNIGHT MINER (STABLE MODE)</h2>

        <div class="stats-container">
            <div class="card"><h3>TOTAL CYCLES</h3><h1 id="s-attempts" class="c-blue">0</h1></div>
            <div class="card"><h3>CAPTCHAS</h3><h1 id="s-found" class="c-gold">0</h1></div>
            <div class="card"><h3>DB SAVED</h3><h1 id="s-saved" class="c-green">0</h1></div>
        </div>

        <div>
            <button class="btn btn-start" onclick="fetch('/start', {method: 'POST'})">🚀 START (SLEEP MODE)</button>
            <button class="btn btn-stop" onclick="fetch('/stop', {method: 'POST'})">🛑 STOP</button>
            <button class="btn btn-check" onclick="refreshStats()">🔄 CHECK STATUS</button>
        </div>

        <div class="logs" id="logs">Waiting for command...</div>
        
        <button onclick="toggleGallery()" style="background: #333; color: white; border: none; padding: 10px;">👁️ SHOW/HIDE CAPTCHAS</button>
        <div id="gallery-wrapper" class="hidden">
            <div id="gallery" style="margin-top:10px;"></div>
        </div>

        <script>
            let showGal = false;
            function refreshStats() {
                fetch('/status?gallery=' + showGal).then(r=>r.json()).then(d=>{
                    document.getElementById('logs').innerHTML = d.logs.map(l=>`<div>${l}</div>`).join('');
                    document.getElementById('s-attempts').innerText = d.stats.attempts;
                    document.getElementById('s-found').innerText = d.stats.found;
                    document.getElementById('s-saved').innerText = d.stats.saved_db;
                    if(showGal) document.getElementById('gallery').innerHTML = d.images.map(i=>`<a href="${i}" target="_blank"><img src="${i}"></a>`).join('');
                });
            }
            function toggleGallery() {
                showGal = !showGal;
                document.getElementById('gallery-wrapper').className = showGal ? '' : 'hidden';
                refreshStats();
            }
            setInterval(refreshStats, 5000);
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status(gallery: str = "false"):
    try: saved_count = await collection.count_documents({})
    except: saved_count = "Err"
    
    resp = {
        "logs": logs,
        "stats": {"attempts": TOTAL_ATTEMPTS, "found": CAPTCHAS_FOUND, "saved_db": saved_count},
        "images": []
    }
    if gallery == "true":
        files = sorted(glob.glob(f'{DATASET_DIR}/*.jpg'), key=os.path.getmtime, reverse=True)[:50]
        resp["images"] = [f"/dataset/{os.path.basename(f)}" for f in files]
    return JSONResponse(resp)

@app.post("/start")
async def start_mining(bt: BackgroundTasks):
    global MINING_ACTIVE
    if not MINING_ACTIVE:
        MINING_ACTIVE = True
        bt.add_task(run_stable_loop)
    return {"status": "started"}

@app.post("/stop")
async def stop_mining():
    global MINING_ACTIVE
    MINING_ACTIVE = False
    log_msg("🛑 Stop command received. Finishing current cycle...")
    return {"status": "stopping"}

# --- HELPERS ---
async def visual_tap(page, element, desc):
    try:
        await element.scroll_into_view_if_needed()
        box = await element.bounding_box()
        if box:
            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2
            await page.touchscreen.tap(x, y)
            log_msg(f"✅ Clicked: {desc}")
            return True
    except: 
        log_msg(f"⚠️ Failed to click: {desc}")
    return False

# --- 🛌 STABLE MINING LOOP ---
async def run_stable_loop():
    global MINING_ACTIVE, TOTAL_ATTEMPTS, CAPTCHAS_FOUND
    log_msg("🌙 Sleep Mode Active: Slow, Stable, Reliable.")

    while MINING_ACTIVE:
        browser = None
        try:
            async with async_playwright() as p:
                target_number = get_random_number()
                TOTAL_ATTEMPTS += 1
                
                # Launch Fresh Browser
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
                
                log_msg(f"🎬 Cycle #{TOTAL_ATTEMPTS} Started ({target_number})")
                
                # 1. LOAD PAGE (Long Wait)
                try:
                    await page.goto(BASE_URL, timeout=60000)
                except:
                    log_msg("⚠️ Timeout loading page. Retrying next cycle...")
                    await browser.close()
                    continue

                await asyncio.sleep(5) # Let animations finish

                # 2. COOKIE
                cookie = page.get_by_text("Accept", exact=True).first
                if await cookie.count() > 0:
                    await visual_tap(page, cookie, "Cookie Accept")
                    await asyncio.sleep(2)

                # 3. REGISTER
                reg_btn = page.get_by_role("button", name="Register").first
                if await reg_btn.count() > 0:
                    await visual_tap(page, reg_btn, "Register Btn")
                    await asyncio.sleep(6) # Page transition wait

                # 4. TERMS
                agree_btn = page.get_by_text("Agree", exact=True).first
                if await agree_btn.count() == 0: agree_btn = page.get_by_text("Next", exact=True).first
                
                if await agree_btn.count() > 0:
                    await visual_tap(page, agree_btn, "Terms Agree")
                    await asyncio.sleep(5)

                # 5. DOB (The tricky part)
                if await page.get_by_text("Date of birth").count() > 0:
                    await page.mouse.move(200, 600)
                    await page.mouse.down()
                    await page.mouse.move(200, 750, steps=20) # Slow scroll
                    await page.mouse.up()
                    await asyncio.sleep(1)
                    
                    next_dob = page.get_by_text("Next", exact=True).first
                    if await next_dob.count() > 0:
                        await visual_tap(page, next_dob, "DOB Next")
                        await asyncio.sleep(4)

                # 6. PHONE OPTION
                use_phone = page.get_by_text("Use phone number", exact=False).first
                if await use_phone.count() > 0:
                    await visual_tap(page, use_phone, "Use Phone")
                    await asyncio.sleep(3)

                # 7. COUNTRY SWITCH
                hk = page.get_by_text("Hong Kong").first
                if await hk.count() == 0: hk = page.get_by_text("Country/Region").first
                
                if await hk.count() > 0:
                    await visual_tap(page, hk, "Country Selector")
                    await asyncio.sleep(3)
                    
                    search = page.locator("input").first
                    if await search.count() > 0:
                        await visual_tap(page, search, "Search Box")
                        await page.keyboard.type("Russia", delay=100) # Type slowly
                        await asyncio.sleep(3)
                        
                        rus = page.get_by_text("Russia", exact=False).first
                        if await rus.count() > 0:
                            await visual_tap(page, rus, "Selected Russia")
                            await asyncio.sleep(4)

                # 8. INPUT NUMBER
                inp = page.locator("input[type='tel']").first
                if await inp.count() == 0: inp = page.locator("input").first
                
                if await inp.count() > 0:
                    await visual_tap(page, inp, "Number Input")
                    await page.keyboard.type(target_number, delay=50)
                    await asyncio.sleep(1)
                    await page.touchscreen.tap(350, 100) # Dismiss Keyboard
                    await asyncio.sleep(2)

                    # 9. GET CODE
                    get_code = page.locator(".get-code-btn").first
                    if await get_code.count() == 0: get_code = page.get_by_text("Get code", exact=False).first
                    
                    if await get_code.count() > 0:
                        await visual_tap(page, get_code, "GET CODE")
                        log_msg("⏳ Waiting 15s for Captcha...")
                        
                        # Wait Loop
                        captcha_frame = None
                        for _ in range(15): # 15 seconds wait
                            for frame in page.frames:
                                if await frame.get_by_text("swap 2 tiles", exact=False).count() > 0:
                                    captcha_frame = frame
                                    break
                            if captcha_frame: break
                            await asyncio.sleep(1)
                        
                        if captcha_frame:
                            CAPTCHAS_FOUND += 1
                            log_msg("🎉 CAPTCHA DETECTED!")
                            
                            # 10. SAVE DATASET (Clean Crop)
                            try:
                                header = captcha_frame.get_by_text("Please complete verification", exact=False).first
                                footer = captcha_frame.get_by_text("swap 2 tiles", exact=False).first
                                
                                if await header.count() > 0 and await footer.count() > 0:
                                    hb = await header.bounding_box()
                                    fb = await footer.bounding_box()
                                    
                                    # Safe Crop Params
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
                                    log_msg(f"✅ Saved Image: {filename}")
                                    
                                    # Mongo
                                    await collection.insert_one({
                                        "filename": filename,
                                        "timestamp": datetime.now(),
                                        "number": target_number,
                                        "status": "raw_dataset"
                                    })
                            except Exception as save_err:
                                log_msg(f"⚠️ Save Error: {save_err}")
                        else:
                            log_msg("❌ No Captcha appeared this time.")
                
        except Exception as e:
            log_msg(f"⚠️ Cycle Crashed: {str(e)[:50]}...")
        
        finally:
            if browser:
                await browser.close()
                log_msg("💤 Cooling down (10s)...")
                await asyncio.sleep(10) # 10s Break between cycles