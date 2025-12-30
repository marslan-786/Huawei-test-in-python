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
    if len(logs) > 200: logs.pop() # Increased log limit

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
        <title>Huawei Slow & Steady</title>
        <style>
            body { background: #121212; color: #e0e0e0; font-family: monospace; padding: 20px; text-align: center; }
            button { padding: 10px 20px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #3f51b5; color: white; border-radius: 4px; }
            
            /* LOGS STYLING */
            .logs { height: 300px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; background: #1e1e1e; margin-bottom: 20px; font-size: 13px; }
            
            /* GALLERY STYLING (Small Grid) */
            .gallery { 
                display: flex; 
                flex-wrap: wrap; 
                justify-content: center; 
                gap: 5px; 
            }
            .gallery a {
                display: inline-block;
            }
            .gallery img { 
                height: 120px; /* Small height for grid view */
                width: auto;
                border: 1px solid #555; 
                border-radius: 5px; 
                transition: transform 0.2s;
            }
            .gallery img:hover { transform: scale(1.5); border-color: #fff; z-index:10; position:relative; }
            
            #video-section { display:none; margin-top:20px; border:1px solid #444; padding:10px; }
        </style>
    </head>
    <body>
        <h1>🐢 HUAWEI SLOW-MO HISTORY BOT</h1>
        <p>Full History Preserved | Slow Steps | Visual Clicks</p>
        <button onclick="startBot()">🚀 START SLOW TEST</button>
        <button onclick="refreshData()" style="background: #009688;">🔄 REFRESH GALLERY</button>
        <button onclick="makeVideo()" style="background: #e91e63;">🎬 MAKE VIDEO</button>
        
        <div class="logs" id="logs">Waiting...</div>
        <div id="video-section"><video id="v-player" controls height="400"></video></div>
        <h3>📸 CAPTURE HISTORY</h3>
        <div class="gallery" id="gallery"></div>

        <script>
            function startBot() { fetch('/start', {method: 'POST'}); logUpdate(">>> STARTING SLOW SEQUENCE..."); }
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
            // Auto refresh slightly slower
            setInterval(refreshData, 4000);
        </script>
    </body>
    </html>
    """

@app.get("/status")
async def get_status():
    # Sort by time, newest first
    files = sorted(glob.glob(f'{CAPTURE_DIR}/*.jpg'), key=os.path.getmtime, reverse=True)
    urls = [f"/captures/{os.path.basename(f)}" for f in files]
    return JSONResponse({"logs": logs, "images": urls})

@app.post("/start")
async def start_bot(bt: BackgroundTasks):
    bt.add_task(run_slow_organic_agent)
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
            
            # Draw Red Dot
            await page.evaluate(f"""
                var dot = document.createElement('div');
                dot.style.position = 'absolute'; 
                dot.style.left = '{x}px'; 
                dot.style.top = '{y}px';
                dot.style.width = '25px'; 
                dot.style.height = '25px'; 
                dot.style.background = 'rgba(255, 0, 0, 0.8)';
                dot.style.borderRadius = '50%'; 
                dot.style.border = '3px solid yellow'; 
                dot.style.zIndex = '999999';
                dot.style.pointerEvents = 'none';
                document.body.appendChild(dot);
            """)
            
            log_msg(f"📍 Target Locked: {desc}")
            await asyncio.sleep(0.5) # Wait for dot to render
            
            log_msg(f"👆 Tapping {desc}...")
            await page.touchscreen.tap(x, y)
            return True
    except Exception as e:
        log_msg(f"⚠️ Tap Error: {e}")
    return False

# --- WAIT HELPER ---
async def wait_and_log(seconds):
    log_msg(f"⏳ Waiting {seconds}s for page/action...")
    await asyncio.sleep(seconds)
    log_msg("✅ Wait Complete.")

# --- MAIN AGENT ---
async def run_slow_organic_agent():
    # NO FILE DELETION HERE! (History Preserved)
    
    # Generate unique session ID for filenames
    session_id = int(time.time())
    
    current_number = generate_hk_number()
    log_msg(f"🎬 New Session {session_id} | HK Number: {current_number}")

    async with async_playwright() as p:
        # Pixel 5 Setup
        pixel_5 = p.devices['Pixel 5'].copy()
        pixel_5['user_agent'] = "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.101 Mobile Safari/537.36"
        
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            proxy=PROXY_CONFIG
        )

        context = await browser.new_context(**pixel_5, locale="en-US")
        page = await context.new_page()

        try:
            # --- STEP 1: LOAD PAGE ---
            log_msg("🚀 Navigating to Base URL...")
            await page.goto(BASE_URL, timeout=90000) # Increased timeout
            
            # Explicit Wait
            await wait_and_log(5) 
            await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_01_main_page_loaded.jpg")

            # --- STEP 2: FIND & CLICK REGISTER ---
            reg_btn = page.get_by_text("Register", exact=True).first
            if await reg_btn.count() == 0: reg_btn = page.get_by_role("button", name="Register").first
            
            if await reg_btn.count() > 0:
                await visual_tap(page, reg_btn, "Register Button")
                await wait_and_log(4) # Wait for navigation
                await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_02_register_clicked.jpg")
            else:
                log_msg("⚠️ Register button not found (Already on page?)")
                await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_02_register_missing.jpg")

            # --- STEP 3: AGREE TO TERMS ---
            # Click the text "Huawei ID User Agreement" to tick box
            agree_text = page.get_by_text("Huawei ID User Agreement").first
            if await agree_text.count() > 0:
                await visual_tap(page, agree_text, "User Agreement Checkbox")
                await wait_and_log(2)
            
            # Click Agree/Next
            next_btn = page.get_by_text("Agree", exact=True).first
            if await next_btn.count() == 0: next_btn = page.get_by_text("Next", exact=True).first
            
            if await next_btn.count() > 0:
                await visual_tap(page, next_btn, "Agree/Next Button")
                await wait_and_log(4)
                await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_03_terms_agreed.jpg")
            else:
                log_msg("❌ Agree Button Missing")
                await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_03_agree_fail.jpg")

            # --- STEP 4: DATE OF BIRTH ---
            log_msg("📅 Handling DOB...")
            # Scroll gesture
            await page.mouse.move(200, 500)
            await page.mouse.down()
            await page.mouse.move(200, 800, steps=20) # Slower drag
            await page.mouse.up()
            await wait_and_log(2)
            
            await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_04_dob_scrolled.jpg")
            
            # Next
            dob_next = page.get_by_text("Next", exact=True).first
            if await dob_next.count() > 0:
                await visual_tap(page, dob_next, "DOB Next Button")
                await wait_and_log(3)

            # --- STEP 5: PHONE REGISTRATION ---
            use_phone = page.get_by_text("Use phone number", exact=False).first
            if await use_phone.count() > 0:
                await visual_tap(page, use_phone, "Use Phone Option")
                await wait_and_log(2)

            await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_05_input_screen.jpg")

            # --- STEP 6: INPUT & GET CODE ---
            inp = page.locator("input[type='tel']").first
            if await inp.count() == 0: inp = page.locator("input").first
            
            if await inp.count() > 0:
                await visual_tap(page, inp, "Phone Input Field")
                
                # Slow Typing
                for char in current_number:
                    await page.keyboard.type(char)
                    await asyncio.sleep(0.3)
                
                await page.touchscreen.tap(20, 100) # Blur
                await wait_and_log(1)
                
                # Get Code
                get_code = page.locator(".get-code-btn").first
                if await get_code.count() == 0: get_code = page.get_by_text("Get code", exact=False).first
                
                if await get_code.count() > 0:
                    await visual_tap(page, get_code, "GET CODE BUTTON")
                    
                    log_msg("⏳ Waiting 10s for final result...")
                    await asyncio.sleep(10)
                    
                    await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_06_final.jpg")
                    log_msg("✅ Flow Complete. Check Screenshot.")
                else:
                    log_msg("❌ Get Code Button Missing")
            else:
                log_msg("❌ Input Missing")

            await browser.close()

        except Exception as e:
            log_msg(f"❌ Error: {str(e)}")
            await page.screenshot(path=f"{CAPTURE_DIR}/{session_id}_ERROR.jpg")
            await browser.close()