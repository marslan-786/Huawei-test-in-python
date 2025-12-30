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
TARGET_COUNTRY = "Pakistan"
BASE_URL = "https://id5.cloud.huawei.com"

# 👇 PROXY CONFIG (Webshare)
PROXY_CONFIG = {
    "server": "http://p.webshare.io:80", 
    "username": "wwwsyxzg-rotate", 
    "password": "582ygxexguhx"
}

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
    if len(logs) > 200: logs.pop()

# --- FILE HELPER ---
def get_next_number():
    if not os.path.exists(NUMBERS_FILE): return None
    with open(NUMBERS_FILE, "r") as f: lines = f.readlines()
    numbers = [line.strip() for line in lines if line.strip()]
    if not numbers: return None
    current_number = numbers[0]
    # Rotate to end
    new_lines = numbers[1:] + [current_number]
    with open(NUMBERS_FILE, "w") as f: f.write("\n".join(new_lines))
    return current_number

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei Invisible Bot</title>
        <style>
            body { background: #000; color: #fff; font-family: monospace; padding: 20px; text-align: center; }
            button { padding: 10px 20px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #d50000; color: white; border-radius: 4px; }
            .logs { height: 300px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; background: #111; margin-bottom: 20px; font-size: 13px; color: #bbb; }
            .gallery { display: flex; flex-wrap: wrap; justify-content: center; gap: 5px; }
            .gallery img { height: 100px; border: 1px solid #333; }
            #video-section { display:none; margin-top:20px; }
        </style>
    </head>
    <body>
        <h1>👻 HUAWEI INVISIBLE BOT</h1>
        <p>No Visuals | Fail Fast Strategy | IP Rotation</p>
        <button onclick="startBot()">🚀 START GHOST AGENT</button>
        <button onclick="refreshData()" style="background: #009688;">🔄 REFRESH</button>
        <button onclick="makeVideo()" style="background: #2962ff;">🎬 MAKE VIDEO</button>
        
        <div class="logs" id="logs">Waiting...</div>
        <div id="video-section"><video id="v-player" controls height="400"></video></div>
        <h3>📸 LIVE FEED</h3>
        <div class="gallery" id="gallery"></div>

        <script>
            function startBot() { fetch('/start', {method: 'POST'}); logUpdate(">>> STARTING GHOST MODE..."); }
            function refreshData() {
                fetch('/status').then(r=>r.json()).then(d=>{
                    document.getElementById('logs').innerHTML = d.logs.map(l=>`<div>${l}</div>`).join('');
                    document.getElementById('gallery').innerHTML = d.images.map(i=>`<a href="${i}" target="_blank"><img src="${i}"></a>`).join('');
                });
            }
            function makeVideo() {
                fetch('/generate_video', {method: 'POST'}).then(r=>r.json()).then(d=>{
                    if(d.status === "done") {
                        document.getElementById('video-section').style.display = 'block';
                        document.getElementById('v-player').src = "/captures/proof.mp4?t=" + Date.now();
                    }
                });
            }
            function logUpdate(msg) { document.getElementById('logs').innerHTML = "<div>" + msg + "</div>" + document.getElementById('logs').innerHTML; }
            setInterval(refreshData, 4000);
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
    bt.add_task(run_ghost_agent)
    return {"status": "started"}

@app.post("/generate_video")
async def trigger_video():
    files = sorted(glob.glob(f'{CAPTURE_DIR}/*.jpg'), key=os.path.getmtime)
    if not files: return {"status": "error"}
    try:
        with imageio.get_writer(VIDEO_PATH, fps=1, format='FFMPEG') as writer:
            for filename in files: writer.append_data(imageio.imread(filename))
        return {"status": "done"}
    except: return {"status": "error"}

# --- INVISIBLE TAP HELPER (No Red Dot) ---
async def tap(page, element, desc):
    try:
        box = await element.bounding_box()
        if box:
            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2
            
            log_msg(f"👆 Tapping {desc}...")
            await page.touchscreen.tap(x, y)
            return True
    except Exception as e:
        log_msg(f"⚠️ Tap Error: {e}")
    return False

# --- WAIT HELPER ---
async def wait_and_log(seconds):
    log_msg(f"⏳ Waiting {seconds}s...")
    await asyncio.sleep(seconds)

# --- MAIN AGENT ---
async def run_ghost_agent():
    # Loop continuously through numbers
    while True:
        session_id = int(time.time())
        
        # Get Next Number
        current_number = get_next_number()
        if not current_number:
            log_msg("❌ No numbers in file!")
            return

        log_msg(f"🎬 New Session {session_id} | Number: {current_number}")
        log_msg("🔄 Connecting with NEW IP (Webshare Rotate)...")

        async with async_playwright() as p:
            pixel_5 = p.devices['Pixel 5'].copy()
            pixel_5['user_agent'] = "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.101 Mobile Safari/537.36"
            pixel_5['viewport'] = {'width': 412, 'height': 950} 

            # Launch Browser (New IP on every launch)
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                proxy=PROXY_CONFIG
            )

            context = await browser.new_context(**pixel_5, locale="en-US")
            page = await context.new_page()

            try:
                # STEP 1: LOAD MAIN PAGE
                log_msg("🚀 Navigating...")
                await page.goto(BASE_URL, timeout=60000)
                await wait_and_log(4)
                
                # Cookie Banner
                cookie_close = page.locator(".cookie-close-btn").first
                if await cookie_close.count() == 0: cookie_close = page.get_by_text("Accept", exact=True).first
                if await cookie_close.count() > 0:
                    await tap(page, cookie_close, "Cookie Accept")
                    await wait_and_log(2)

                await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_01_loaded.jpg")

                # STEP 2: REGISTER BUTTON
                reg_btn = page.get_by_text("Register", exact=True).first
                if await reg_btn.count() == 0: reg_btn = page.get_by_role("button", name="Register").first
                
                if await reg_btn.count() > 0:
                    await tap(page, reg_btn, "Register Button")
                    await wait_and_log(5)
                else:
                    log_msg("⚠️ Register button hidden")
                
                await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_02_register_page.jpg")

                # --- STEP 3: CHANGE COUNTRY (Hong Kong -> Pakistan) ---
                hk_selector = page.get_by_text("Hong Kong").first
                if await hk_selector.count() == 0: hk_selector = page.get_by_text("Country/Region").first
                
                if await hk_selector.count() > 0:
                    await tap(page, hk_selector, "Country Selector")
                    await wait_and_log(3)

                    # Search
                    search_box = page.locator("input").first
                    if await search_box.count() > 0:
                        await tap(page, search_box, "Search Bar")
                        log_msg(f"⌨️ Typing '{TARGET_COUNTRY}'...")
                        await page.keyboard.type(TARGET_COUNTRY, delay=100)
                        await wait_and_log(2)

                        # Select
                        target_country_opt = page.get_by_text(TARGET_COUNTRY, exact=True).first
                        if await target_country_opt.count() > 0:
                            await tap(page, target_country_opt, f"Select {TARGET_COUNTRY}")
                            await wait_and_log(3)
                        else:
                            log_msg("❌ Country not found in list")
                else:
                    log_msg("⚠️ Country Selector not found")

                await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_03_country_set.jpg")

                # STEP 4: AGREE TERMS
                agree_text = page.get_by_text("Huawei ID User Agreement").first
                if await agree_text.count() > 0:
                    await tap(page, agree_text, "Terms Checkbox")
                    await wait_and_log(1)

                agree_btn = page.get_by_text("Agree", exact=True).first
                if await agree_btn.count() == 0: agree_btn = page.get_by_text("Next", exact=True).first
                
                if await agree_btn.count() > 0:
                    await tap(page, agree_btn, "Agree/Next")
                    await wait_and_log(4)

                # STEP 5: DOB (Scroll Wheel)
                log_msg("📅 Handling DOB...")
                await page.mouse.move(200, 500)
                await page.mouse.down()
                await page.mouse.move(200, 800, steps=20)
                await page.mouse.up()
                await wait_and_log(2)
                
                dob_next = page.get_by_text("Next", exact=True).first
                if await dob_next.count() > 0:
                    await tap(page, dob_next, "DOB Next")
                    await wait_and_log(3)

                # STEP 6: PHONE OPTION
                use_phone = page.get_by_text("Use phone number", exact=False).first
                if await use_phone.count() > 0:
                    await tap(page, use_phone, "Use Phone Option")
                    await wait_and_log(2)

                await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_04_input_screen.jpg")

                # STEP 7: INPUT & CODE
                inp = page.locator("input[type='tel']").first
                if await inp.count() == 0: inp = page.locator("input").first
                
                if await inp.count() > 0:
                    await tap(page, inp, "Input")
                    
                    for char in current_number:
                        await page.keyboard.type(char)
                        await asyncio.sleep(0.3)
                    await page.touchscreen.tap(20, 100) # Blur
                    await wait_and_log(1)
                    
                    get_code = page.locator(".get-code-btn").first
                    if await get_code.count() == 0: get_code = page.get_by_text("Get code", exact=False).first
                    
                    if await get_code.count() > 0:
                        await tap(page, get_code, "GET CODE")
                        log_msg("⏳ Waiting 10s for result...")
                        await asyncio.sleep(10)
                        
                        await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_05_final.jpg")
                        
                        # --- 🚨 ERROR CHECK (ONE STRIKE POLICY) ---
                        if await page.get_by_text("Unexpected problem").count() > 0:
                            log_msg("🛑 BLOCKED! Closing session immediately to rotate IP...")
                            await browser.close()
                            continue # Jump to next iteration of While Loop (Next Number)
                        
                        # Check for Success
                        if len(page.frames) > 1 or await page.locator("iframe").count() > 0:
                             log_msg("🎉 BINGO! CAPTCHA DETECTED!")
                             await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_SUCCESS.jpg")
                             await browser.close()
                             return # Stop script on success? Or remove this return to keep going
                        else:
                             log_msg("❓ No popup? Check logs.")
                    else:
                        log_msg("❌ Get Code Button Missing")
                else:
                    log_msg("❌ Input Missing")

                await browser.close()

            except Exception as e:
                log_msg(f"❌ Error: {str(e)}")
                await browser.close()
                # Continue loop even on crash to keep rotating
                continue