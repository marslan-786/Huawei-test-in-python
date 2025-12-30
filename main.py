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

# --- HK NUMBER GENERATOR ---
def generate_hk_number():
    prefix = random.choice(['5', '6', '9'])
    rest = ''.join([str(random.randint(0, 9)) for _ in range(7)])
    return f"{prefix}{rest}"

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei Scroll Master</title>
        <style>
            body { background: #121212; color: #e0e0e0; font-family: monospace; padding: 20px; text-align: center; }
            button { padding: 10px 20px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #3f51b5; color: white; border-radius: 4px; }
            .logs { height: 300px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; background: #1e1e1e; margin-bottom: 20px; font-size: 13px; }
            .gallery { display: flex; flex-wrap: wrap; justify-content: center; gap: 5px; }
            .gallery img { height: 120px; border: 1px solid #555; border-radius: 5px; transition: transform 0.2s; }
            .gallery img:hover { transform: scale(1.5); border-color: #fff; z-index:10; position:relative; }
            #video-section { display:none; margin-top:20px; border:1px solid #444; padding:10px; }
        </style>
    </head>
    <body>
        <h1>📜 HUAWEI SCROLL & FIND BOT</h1>
        <p>Features: Smart Scrolling | Cookie Buster | Taller Screen</p>
        <button onclick="startBot()">🚀 START BOT</button>
        <button onclick="refreshData()" style="background: #009688;">🔄 REFRESH</button>
        <button onclick="makeVideo()" style="background: #e91e63;">🎬 MAKE VIDEO</button>
        
        <div class="logs" id="logs">Waiting...</div>
        <div id="video-section"><video id="v-player" controls height="400"></video></div>
        <h3>📸 CAPTURE HISTORY</h3>
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
    bt.add_task(run_scroll_agent)
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

# --- VISUAL TAP HELPER ---
async def visual_tap(page, element, desc):
    try:
        box = await element.bounding_box()
        if box:
            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2
            
            await page.evaluate(f"""
                var dot = document.createElement('div');
                dot.style.position = 'absolute'; left = '{x}px'; top = '{y}px';
                dot.style.width = '25px'; height = '25px'; background = 'rgba(255, 0, 0, 0.8)';
                dot.style.borderRadius = '50%'; border = '3px solid yellow'; zIndex = '999999';
                document.body.appendChild(dot);
            """)
            
            log_msg(f"📍 Found: {desc}")
            await asyncio.sleep(0.5)
            log_msg(f"👆 Tapping {desc}...")
            await page.touchscreen.tap(x, y)
            return True
    except Exception as e:
        log_msg(f"⚠️ Tap Error: {e}")
    return False

# --- SCROLL HELPER ---
async def scroll_page(page, times=1):
    log_msg(f"📜 Scrolling down ({times}x)...")
    for _ in range(times):
        # Touch swipe gesture (Pull up to scroll down)
        await page.mouse.move(200, 600)
        await page.mouse.down()
        await page.mouse.move(200, 200, steps=15)
        await page.mouse.up()
        await asyncio.sleep(1)

# --- WAIT HELPER ---
async def wait_and_log(seconds):
    log_msg(f"⏳ Waiting {seconds}s...")
    await asyncio.sleep(seconds)

# --- MAIN AGENT ---
async def run_scroll_agent():
    session_id = int(time.time())
    current_number = generate_hk_number()
    log_msg(f"🎬 Session {session_id} | Number: {current_number}")

    async with async_playwright() as p:
        pixel_5 = p.devices['Pixel 5'].copy()
        pixel_5['user_agent'] = "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.101 Mobile Safari/537.36"
        
        # Taller viewport to see more
        pixel_5['viewport'] = {'width': 412, 'height': 950} 

        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            proxy=PROXY_CONFIG
        )

        context = await browser.new_context(**pixel_5, locale="en-US")
        page = await context.new_page()

        try:
            # STEP 1: LOAD
            log_msg("🚀 Navigating...")
            await page.goto(BASE_URL, timeout=90000)
            await wait_and_log(5)
            
            # KILL COOKIE BANNER
            cookie_close = page.locator(".cookie-close-btn").first # Generic class attempt
            if await cookie_close.count() == 0: cookie_close = page.get_by_text("Accept", exact=True).first
            
            if await cookie_close.count() > 0:
                log_msg("🍪 Closing Cookie Banner...")
                await visual_tap(page, cookie_close, "Cookie Accept")
                await wait_and_log(2)

            await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_01_loaded.jpg")

            # STEP 2: REGISTER BUTTON (With Scroll)
            reg_btn = page.get_by_text("Register", exact=True).first
            if await reg_btn.count() == 0: reg_btn = page.get_by_role("button", name="Register").first
            
            # Loop to find (Scroll if needed)
            found_reg = False
            for i in range(3):
                if await reg_btn.count() > 0 and await reg_btn.is_visible():
                    await visual_tap(page, reg_btn, "Register Button")
                    found_reg = True
                    break
                else:
                    log_msg("🔍 Register button hidden, scrolling...")
                    await scroll_page(page, 1)
            
            if not found_reg:
                log_msg("⚠️ Register button not found! (Maybe already on login/reg page?)")
            
            await wait_and_log(4)
            await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_02_post_register.jpg")

            # STEP 3: AGREE TO TERMS (Smart Scroll)
            # First, check for checkbox text
            agree_text = page.get_by_text("Huawei ID User Agreement").first
            if await agree_text.count() > 0:
                await visual_tap(page, agree_text, "Terms Checkbox")
                await wait_and_log(1)

            # Now find AGREE/NEXT button
            # Usually needs scrolling to bottom
            agree_btn = page.get_by_text("Agree", exact=True).first
            if await agree_btn.count() == 0: agree_btn = page.get_by_text("Next", exact=True).first
            
            found_agree = False
            for i in range(3): # Try scrolling 3 times
                if await agree_btn.count() > 0 and await agree_btn.is_visible():
                    await visual_tap(page, agree_btn, "Agree/Next")
                    found_agree = True
                    break
                else:
                    log_msg(f"📜 Scrolling to find Agree button ({i+1}/3)...")
                    await scroll_page(page, 1)
                    await wait_and_log(1)

            if not found_agree:
                log_msg("❌ Agree button STILL missing after scroll.")
                await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_03_agree_missing.jpg")
            else:
                await wait_and_log(4)
                await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_03_agreed.jpg")

            # STEP 4: DOB (Scroll Wheel Logic)
            log_msg("📅 Handling DOB...")
            await scroll_page(page, 1) # Scroll down a bit to see picker if hidden
            
            # Gesture to change year
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
                    log_msg("⏳ Waiting 10s for result...")
                    await asyncio.sleep(10)
                    await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_06_result.jpg")
                    log_msg("✅ Check screenshot for Captcha!")
                else:
                    log_msg("❌ Get Code button missing")
            else:
                log_msg("❌ Input field missing")

            await browser.close()

        except Exception as e:
            log_msg(f"❌ Error: {str(e)}")
            await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_ERROR.jpg")
            await browser.close()