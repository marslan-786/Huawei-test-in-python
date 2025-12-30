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
        <title>Huawei Miner Pro</title>
        <style>
            body { background: #000; color: #00e676; font-family: monospace; padding: 20px; text-align: center; }
            .btn { padding: 15px 25px; font-weight: bold; cursor: pointer; border:none; border-radius: 4px; margin: 5px; }
            .btn-start { background: #6200ea; color: white; }
            .btn-view { background: #2962ff; color: white; }
            .logs { height: 300px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; background: #0a0a0a; color: #ccc; margin-top: 20px; }
            .gallery { display: none; flex-wrap: wrap; justify-content: center; gap: 5px; margin-top: 20px; }
            .gallery img { height: 100px; border: 1px solid #444; }
        </style>
    </head>
    <body>
        <h1>🛠️ HUAWEI MINER (PRO LOGIC)</h1>
        <button class="btn btn-start" onclick="fetch('/start', {method:'POST'})">🚀 START BOT</button>
        <button class="btn btn-view" onclick="toggleGallery()">📸 VIEW CAPTURES</button>
        <div class="logs" id="logs">Waiting...</div>
        <div id="gallery" class="gallery"></div>
        <script>
            let showGal = false;
            function refresh() {
                fetch('/status').then(r=>r.json()).then(d=>{
                    document.getElementById('logs').innerHTML = d.logs.map(l=>`<div>${l}</div>`).join('');
                    if(showGal) document.getElementById('gallery').innerHTML = d.images.map(i=>`<img src="${i}">`).join('');
                });
            }
            function toggleGallery() {
                showGal = !showGal;
                document.getElementById('gallery').style.display = showGal ? 'flex' : 'none';
                refresh();
            }
            setInterval(refresh, 3000);
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status():
    files = sorted(glob.glob(f'{CAPTURE_DIR}/*.jpg'), key=os.path.getmtime, reverse=True)[:50]
    urls = [f"/captures/{os.path.basename(f)}" for f in files]
    return JSONResponse({"logs": logs, "images": urls})

@app.post("/start")
async def start_bot(bt: BackgroundTasks):
    bt.add_task(run_pro_mining)
    return {"status": "started"}

# --- HELPERS ---
async def burst_record(page, desc, seconds=2):
    """Captures frames at high speed to show activity"""
    frames = int(seconds / 0.2)
    for i in range(frames):
        ts = datetime.now().strftime("%H%M%S%f")
        await page.screenshot(path=f"{CAPTURE_DIR}/{ts}_{desc}.jpg")
        await asyncio.sleep(0.2)

async def visual_tap(page, element, desc):
    """Logs and taps the element"""
    try:
        if await element.count() > 0:
            box = await element.bounding_box()
            if box:
                x = box['x'] + box['width'] / 2
                y = box['y'] + box['height'] / 2
                log_msg(f"👆 Tapping {desc}...")
                await page.touchscreen.tap(x, y)
                return True
    except: pass
    return False

# --- PRO MINING FLOW ---
async def run_pro_mining():
    while True:
        current_number = generate_russia_number()
        log_msg(f"🎬 CYCLE START | Number: {current_number}")
        
        async with async_playwright() as p:
            pixel_5 = p.devices['Pixel 5'].copy()
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"], proxy=PROXY_CONFIG)
            context = await browser.new_context(**pixel_5)
            page = await context.new_page()

            try:
                log_msg("🚀 Navigating to Huawei...")
                await page.goto(BASE_URL, timeout=60000)
                await burst_record(page, "01_loaded")

                # Register
                reg = page.get_by_text("Register", exact=True).first
                if await reg.count() == 0: reg = page.get_by_role("button", name="Register").first
                if await visual_tap(page, reg, "Register"):
                    await burst_record(page, "02_reg_clicked", 3)

                    # Agree
                    agree = page.get_by_text("Agree", exact=True).first
                    if await agree.count() == 0: agree = page.get_by_text("Next", exact=True).first
                    if await visual_tap(page, agree, "Agree/Next"):
                        await burst_record(page, "03_agreed", 3)

                        # DOB Scroll
                        log_msg("🖱️ Scrolling DOB...")
                        await page.mouse.move(200, 500); await page.mouse.down()
                        await page.mouse.move(200, 800, steps=10); await page.mouse.up()
                        dob_next = page.get_by_text("Next", exact=True).first
                        await visual_tap(page, dob_next, "DOB_Next")
                        await burst_record(page, "04_dob_done", 2)

                        # Phone
                        use_phone = page.get_by_text("Use phone number", exact=False).first
                        if await visual_tap(page, use_phone, "Use_Phone"):
                            await burst_record(page, "05_phone_page", 2)

                            # Russia Switch
                            hk = page.get_by_text("Hong Kong").first
                            if await visual_tap(page, hk, "Country_List"):
                                await asyncio.sleep(2)
                                await page.keyboard.type("Russia", delay=100)
                                rus = page.get_by_text("Russia", exact=False).first
                                await visual_tap(page, rus, "Russia_Select")
                                await burst_record(page, "06_russia_set", 3)

                                # Input
                                inp = page.locator("input[type='tel']").first
                                if await visual_tap(page, inp, "Input_Field"):
                                    await page.keyboard.type(current_number)
                                    await page.touchscreen.tap(350, 100) # Close KB
                                    
                                    get_code = page.get_by_text("Get code").first
                                    if await visual_tap(page, get_code, "GET_CODE"):
                                        log_msg("⏳ Waiting for Captcha...")
                                        await burst_record(page, "07_captcha_wait", 10)
                                        
                                        # SAVE DATASET
                                        for frame in page.frames:
                                            if await frame.get_by_text("swap 2 tiles").count() > 0:
                                                log_msg("🎉 CAPTCHA FOUND! Saving...")
                                                ts = int(time.time())
                                                fname = f"captcha_{ts}.jpg"
                                                await frame.screenshot(path=f"{DATASET_DIR}/{fname}")
                                                await collection.insert_one({"filename": fname, "number": current_number})

                await browser.close()
                log_msg("💤 Cycle Finished. Sleeping 10s...")
                await asyncio.sleep(10)

            except Exception as e:
                log_msg(f"❌ Error: {str(e)}")
                await browser.close()
                await asyncio.sleep(5)