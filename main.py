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
        <title>Huawei Stable Miner</title>
        <style>
            body { background: #000; color: #00e676; font-family: monospace; padding: 20px; text-align: center; }
            .stats { display: flex; justify-content: center; gap: 20px; margin-bottom: 20px; }
            .card { background: #111; padding: 20px; border-radius: 10px; border: 1px solid #333; width: 150px; }
            .btn { padding: 15px 30px; font-weight: bold; cursor: pointer; border:none; border-radius: 5px; margin: 10px; }
            .btn-start { background: #00c853; color: black; }
            .btn-stop { background: #d50000; color: white; }
            .logs { height: 300px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; background: #050505; color: #ccc; font-size: 12px; }
            .live-img { width: 300px; border: 2px solid red; margin-top: 10px; display: none; }
        </style>
    </head>
    <body>
        <h2>🛠️ HUAWEI DATA MINER (PRO LOGIC)</h2>
        <div class="stats">
            <div class="card"><h3>CYCLES</h3><h1 id="s-attempts">0</h1></div>
            <div class="card"><h3>CAPTCHAS</h3><h1 id="s-found">0</h1></div>
            <div class="card"><h3>MONGO DB</h3><h1 id="s-saved">0</h1></div>
        </div>
        <button class="btn btn-start" onclick="fetch('/start', {method:'POST'})">🚀 START BOT</button>
        <button class="btn btn-stop" onclick="fetch('/stop', {method:'POST'})">🛑 STOP BOT</button>
        <br>
        <button onclick="toggleLive()" style="background:#444; color:white;">🔴 TOGGLE LIVE VIEW</button>
        <img id="live-feed" class="live-img" src="">
        <div class="logs" id="logs">Waiting...</div>
        <script>
            let live = false;
            function refresh() {
                fetch('/status').then(r=>r.json()).then(d=>{
                    document.getElementById('logs').innerHTML = d.logs.map(l=>`<div>${l}</div>`).join('');
                    document.getElementById('s-attempts').innerText = d.stats.attempts;
                    document.getElementById('s-found').innerText = d.stats.found;
                    document.getElementById('s-saved').innerText = d.stats.saved_db;
                    if(live) {
                        document.getElementById('live-feed').style.display = 'inline-block';
                        document.getElementById('live-feed').src = "/captures/live.jpg?t=" + Date.now();
                    }
                });
            }
            function toggleLive() { live = !live; if(!live) document.getElementById('live-feed').style.display='none'; }
            setInterval(refresh, 3000);
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status():
    try: saved_count = await collection.count_documents({})
    except: saved_count = 0
    return JSONResponse({
        "logs": logs,
        "stats": {"attempts": TOTAL_ATTEMPTS, "found": CAPTCHAS_FOUND, "saved_db": saved_count}
    })

@app.post("/start")
async def start_bot(bt: BackgroundTasks):
    global MINING_ACTIVE
    if not MINING_ACTIVE:
        MINING_ACTIVE = True
        bt.add_task(run_pro_loop)
    return {"status": "started"}

@app.post("/stop")
async def stop_bot():
    global MINING_ACTIVE
    MINING_ACTIVE = False
    return {"status": "stopped"}

# --- WORKING VISUAL TAP LOGIC ---
async def visual_tap(page, element, desc):
    try:
        if await element.count() > 0:
            await element.scroll_into_view_if_needed()
            box = await element.bounding_box()
            if box:
                x = box['x'] + box['width'] / 2
                y = box['y'] + box['height'] / 2
                await page.touchscreen.tap(x, y)
                log_msg(f"✅ Tapped: {desc}")
                await page.screenshot(path="./captures/live.jpg") # Auto-update live view
                return True
    except: pass
    return False

# --- 🏃 PRO MINING LOOP ---
async def run_pro_loop():
    global MINING_ACTIVE, TOTAL_ATTEMPTS, CAPTCHAS_FOUND
    log_msg("🚀 Pro Logic Loop Started...")

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
                    user_agent="Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.101 Mobile Safari/537.36"
                )
                page = await context.new_page()
                
                log_msg(f"🎬 Starting Cycle #{TOTAL_ATTEMPTS} ({target_number})")
                
                # 1. GOTO
                await page.goto(BASE_URL, timeout=60000)
                await asyncio.sleep(6) # Let page load

                # 2. COOKIE
                cookie = page.get_by_text("Accept", exact=True).first
                if await cookie.count() == 0: cookie = page.locator(".cookie-close-btn").first
                await visual_tap(page, cookie, "Cookie")
                await asyncio.sleep(2)

                # 3. REGISTER
                reg = page.get_by_text("Register", exact=True).first
                if await reg.count() == 0: reg = page.get_by_role("button", name="Register").first
                if await visual_tap(page, reg, "Register Button"):
                    await asyncio.sleep(6)

                    # 4. TERMS
                    agree = page.get_by_text("Agree", exact=True).first
                    if await agree.count() == 0: agree = page.get_by_text("Next", exact=True).first
                    if await visual_tap(page, agree, "Terms/Agree"):
                        await asyncio.sleep(5)

                        # 5. DOB SCROLL
                        await page.mouse.move(200, 500); await page.mouse.down()
                        await page.mouse.move(200, 800, steps=20); await page.mouse.up()
                        await asyncio.sleep(1)
                        dob_next = page.get_by_text("Next", exact=True).first
                        await visual_tap(page, dob_next, "DOB Next")
                        await asyncio.sleep(4)

                        # 6. PHONE OPTION
                        use_phone = page.get_by_text("Use phone number", exact=False).first
                        if await visual_tap(page, use_phone, "Use Phone"):
                            await asyncio.sleep(3)

                            # 7. COUNTRY (RUSSIA)
                            hk = page.get_by_text("Hong Kong").first
                            if await hk.count() == 0: hk = page.get_by_text("Country/Region").first
                            if await visual_tap(page, hk, "Country List"):
                                await asyncio.sleep(3)
                                search = page.locator("input").first
                                if await search.count() > 0:
                                    await search.click()
                                    await page.keyboard.type("Russia", delay=100)
                                    await asyncio.sleep(3)
                                    rus = page.get_by_text("Russia", exact=False).first
                                    await visual_tap(page, rus, "Select Russia")
                                    await asyncio.sleep(4)

                            # 8. INPUT NUMBER
                            inp = page.locator("input[type='tel']").first
                            if await inp.count() == 0: inp = page.locator("input").first
                            if await visual_tap(page, inp, "Phone Input"):
                                await page.keyboard.type(target_number, delay=50)
                                await page.touchscreen.tap(350, 100) # Close keyboard
                                await asyncio.sleep(2)

                                # 9. GET CODE
                                get_code = page.get_by_text("Get code", exact=False).first
                                if await get_code.count() == 0: get_code = page.locator(".get-code-btn").first
                                if await visual_tap(page, get_code, "GET CODE"):
                                    log_msg("⏳ Waiting for Captcha...")
                                    
                                    # Captcha Discovery
                                    captcha_frame = None
                                    for _ in range(15):
                                        for frame in page.frames:
                                            if await frame.get_by_text("swap 2 tiles", exact=False).count() > 0:
                                                captcha_frame = frame; break
                                        if captcha_frame: break
                                        await asyncio.sleep(1)
                                    
                                    if captcha_frame:
                                        CAPTCHAS_FOUND += 1
                                        log_msg("🎉 CAPTCHA FOUND! Saving...")
                                        
                                        # SAVE DATASET
                                        header = captcha_frame.get_by_text("Please complete verification", exact=False).first
                                        footer = captcha_frame.get_by_text("swap 2 tiles", exact=False).first
                                        if await header.count() > 0 and await footer.count() > 0:
                                            hb = await header.bounding_box(); fb = await footer.bounding_box()
                                            
                                            grid_y = hb['y'] + hb['height'] + 25
                                            grid_h = fb['y'] - grid_y - 10
                                            grid_w = 340; grid_x = (fb['x'] + fb['width']/2) - (grid_w/2)
                                            
                                            ts = int(time.time())
                                            fname = f"captcha_{ts}_{target_number}.jpg"
                                            await page.screenshot(path=f"{DATASET_DIR}/{fname}", clip={"x":grid_x,"y":grid_y,"width":grid_w,"height":grid_h})
                                            
                                            await collection.insert_one({"filename":fname, "timestamp":datetime.now(), "number":target_number})
                                            log_msg(f"✅ Data Logged: {fname}")

            await browser.close()
            log_msg("💤 Cycle finished. Restarting in 10s...")
            await asyncio.sleep(10)
            
        except Exception as e:
            log_msg(f"⚠️ Error: {str(e)[:50]}")
            if browser: await browser.close()
            await asyncio.sleep(5)