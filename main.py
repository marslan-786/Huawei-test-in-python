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

# 🌍 TARGET COUNTRY
TARGET_COUNTRY = "Pakistan"

# 🏁 STARTING URL
BASE_URL = "https://id5.cloud.huawei.com"

# 👇 ROTATING PROXY CONFIG (Webshare) 👇
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
    # Rotate
    new_lines = numbers[1:] + [current_number]
    with open(NUMBERS_FILE, "w") as f: f.write("\n".join(new_lines))
    return current_number

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei Country Selector</title>
        <style>
            body { background: #121212; color: #00e676; font-family: monospace; padding: 20px; text-align: center; }
            button { padding: 10px 20px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #6200ea; color: white; border-radius: 4px; }
            .logs { height: 300px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; background: #1e1e1e; margin-bottom: 20px; font-size: 13px; color: #e0e0e0; }
            .gallery { display: flex; flex-wrap: wrap; justify-content: center; gap: 5px; }
            .gallery img { height: 120px; border: 1px solid #555; border-radius: 5px; }
            .gallery img:hover { transform: scale(1.5); border-color: #fff; z-index:10; position:relative; }
            #video-section { display:none; margin-top:20px; border:1px solid #444; padding:10px; }
        </style>
    </head>
    <body>
        <h1>🇵🇰 HUAWEI COUNTRY SELECTOR BOT</h1>
        <p>Target: Pakistan | Method: Search & Select</p>
        <button onclick="startBot()">🚀 START BOT</button>
        <button onclick="refreshData()" style="background: #009688;">🔄 REFRESH</button>
        <button onclick="makeVideo()" style="background: #e91e63;">🎬 MAKE VIDEO</button>
        
        <div class="logs" id="logs">Waiting...</div>
        <div id="video-section"><video id="v-player" controls height="400"></video></div>
        <h3>📸 LIVE FEED</h3>
        <div class="gallery" id="gallery"></div>

        <script>
            function startBot() { fetch('/start', {method: 'POST'}); logUpdate(">>> STARTING..."); }
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
    bt.add_task(run_country_select_agent)
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

# --- VISUAL TAP HELPER (WITH FORCE DOT) ---
async def visual_tap(page, element, desc):
    try:
        box = await element.bounding_box()
        if box:
            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2
            
            # Create Red Dot
            await page.evaluate(f"""
                var dot = document.createElement('div');
                dot.style.position = 'absolute'; 
                dot.style.left = '{x}px'; 
                dot.style.top = '{y}px';
                dot.style.width = '30px'; 
                dot.style.height = '30px'; 
                dot.style.background = 'rgba(255, 0, 0, 0.9)'; /* RED */
                dot.style.borderRadius = '50%'; 
                dot.style.border = '3px solid white'; 
                dot.style.zIndex = '999999';
                dot.style.pointerEvents = 'none';
                dot.id = 'temp-dot';
                document.body.appendChild(dot);
            """)
            
            log_msg(f"📍 Target: {desc}")
            await asyncio.sleep(0.5) # Show dot
            
            log_msg(f"🔴 FORCE TAPPING {desc}...")
            await page.touchscreen.tap(x, y)
            
            # Remove dot after tap (optional, keeping it shows history better in screenshots)
            return True
    except Exception as e:
        log_msg(f"⚠️ Tap Error: {e}")
    return False

# --- WAIT HELPER ---
async def wait_and_log(seconds):
    log_msg(f"⏳ Waiting {seconds}s...")
    await asyncio.sleep(seconds)

# --- MAIN AGENT ---
async def run_country_select_agent():
    session_id = int(time.time())
    
    # Use Next Number from File (Assuming Pakistani numbers now)
    current_number = get_next_number()
    if not current_number:
        log_msg("❌ No numbers in numbers.txt!")
        return

    log_msg(f"🎬 Session {session_id} | Changing Region to: {TARGET_COUNTRY}")

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
            # STEP 1: LOAD MAIN PAGE
            log_msg("🚀 Navigating...")
            await page.goto(BASE_URL, timeout=90000)
            await wait_and_log(4)
            
            # Close Cookie
            cookie_close = page.locator(".cookie-close-btn").first
            if await cookie_close.count() == 0: cookie_close = page.get_by_text("Accept", exact=True).first
            if await cookie_close.count() > 0:
                await visual_tap(page, cookie_close, "Cookie Accept")
                await wait_and_log(2)

            await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_01_loaded.jpg")

            # STEP 2: REGISTER BUTTON
            reg_btn = page.get_by_text("Register", exact=True).first
            if await reg_btn.count() == 0: reg_btn = page.get_by_role("button", name="Register").first
            
            if await reg_btn.count() > 0:
                await visual_tap(page, reg_btn, "Register Button")
                await wait_and_log(5)
            else:
                log_msg("⚠️ Register button hidden")
            
            await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_02_register_page.jpg")

            # --- 🔥 NEW: CHANGE COUNTRY TO PAKISTAN ---
            log_msg("🌍 Checking for Hong Kong/Country Selector...")
            
            # Find the element that shows current country (Usually "Hong Kong (China)")
            # Or the label "Country/Region" which is clickable
            hk_selector = page.get_by_text("Hong Kong").first
            if await hk_selector.count() == 0: hk_selector = page.get_by_text("Country/Region").first
            
            if await hk_selector.count() > 0:
                await visual_tap(page, hk_selector, "Country Selector (HK)")
                await wait_and_log(3)
                await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_03_country_list.jpg")

                # SEARCH
                search_box = page.locator("input").first # Generic input is usually search here
                if await search_box.count() > 0:
                    await visual_tap(page, search_box, "Search Bar")
                    log_msg(f"⌨️ Typing '{TARGET_COUNTRY}'...")
                    await page.keyboard.type(TARGET_COUNTRY, delay=100)
                    await wait_and_log(2)
                    await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_04_search_typed.jpg")

                    # SELECT FROM LIST
                    target_country_opt = page.get_by_text(TARGET_COUNTRY, exact=True).first
                    if await target_country_opt.count() > 0:
                        await visual_tap(page, target_country_opt, f"Select {TARGET_COUNTRY}")
                        await wait_and_log(3)
                        log_msg(f"✅ Country Changed to {TARGET_COUNTRY}")
                    else:
                        log_msg("❌ Country not found in list")
                else:
                    log_msg("❌ Search bar not found")
            else:
                log_msg("⚠️ Could not find Country Selector")

            await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_05_country_final.jpg")

            # STEP 3: AGREE
            agree_text = page.get_by_text("Huawei ID User Agreement").first
            if await agree_text.count() > 0:
                await visual_tap(page, agree_text, "Terms Checkbox")
                await wait_and_log(1)

            agree_btn = page.get_by_text("Agree", exact=True).first
            if await agree_btn.count() == 0: agree_btn = page.get_by_text("Next", exact=True).first
            
            if await agree_btn.count() > 0:
                await visual_tap(page, agree_btn, "Agree/Next")
                await wait_and_log(4)

            # STEP 4: DOB
            log_msg("📅 Handling DOB...")
            await page.mouse.move(200, 500)
            await page.mouse.down()
            await page.mouse.move(200, 800, steps=20)
            await page.mouse.up()
            await wait_and_log(2)
            
            dob_next = page.get_by_text("Next", exact=True).first
            if await dob_next.count() > 0:
                await visual_tap(page, dob_next, "DOB Next")
                await wait_and_log(3)

            # STEP 5: PHONE
            use_phone = page.get_by_text("Use phone number", exact=False).first
            if await use_phone.count() > 0:
                await visual_tap(page, use_phone, "Use Phone Option")
                await wait_and_log(2)

            await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_06_input_screen.jpg")

            # STEP 6: INPUT & CODE
            inp = page.locator("input[type='tel']").first
            if await inp.count() == 0: inp = page.locator("input").first
            
            if await inp.count() > 0:
                await visual_tap(page, inp, "Input")
                for char in current_number:
                    await page.keyboard.type(char)
                    await asyncio.sleep(0.3)
                await page.touchscreen.tap(20, 100) # Blur
                await wait_and_log(1)
                
                get_code = page.locator(".get-code-btn").first
                if await get_code.count() == 0: get_code = page.get_by_text("Get code", exact=False).first
                
                if await get_code.count() > 0:
                    await visual_tap(page, get_code, "GET CODE")
                    log_msg("⏳ Waiting 15s for CAPTCHA...")
                    await asyncio.sleep(15)
                    
                    await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_07_result.jpg")
                    
                    if len(page.frames) > 1 or await page.locator("iframe").count() > 0:
                         log_msg("🎉 BINGO! CAPTCHA DETECTED! (Mission Success)")
                         await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_SUCCESS.jpg")
                    else:
                         log_msg("ℹ️ Check screenshot for result")
                else:
                    log_msg("❌ Get Code Missing")
            else:
                log_msg("❌ Input Missing")

            await browser.close()

        except Exception as e:
            log_msg(f"❌ Error: {str(e)}")
            await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_ERROR.jpg")
            await browser.close()