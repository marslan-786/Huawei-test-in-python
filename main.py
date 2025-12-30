import os
import glob
import asyncio
import random
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

# 👇 PROXY CONFIG 👇
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
    if len(logs) > 100: logs.pop()

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
        <title>Huawei Fixed Flow</title>
        <style>
            body { background: #111; color: #00e676; font-family: monospace; padding: 20px; text-align: center; }
            button { padding: 15px 30px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #6200ea; color: white; border-radius: 4px; }
            .logs { height: 350px; overflow-y: auto; text-align: left; border: 1px solid #444; padding: 10px; background: #000; margin-bottom: 20px; }
            .gallery img { height: 250px; border: 2px solid #555; margin: 3px; border-radius: 10px; }
            #video-section { display:none; margin-top:20px; }
        </style>
    </head>
    <body>
        <h1>🔄 HUAWEI ORGANIC FLOW (FIXED)</h1>
        <p>Using Pixel 5 Device Profile + Samsung UA</p>
        <button onclick="startBot()">🚀 START FIXED AGENT</button>
        <button onclick="refreshData()" style="background: #2962ff;">🔄 REFRESH</button>
        <button onclick="makeVideo()" style="background: #00c853;">🎬 MAKE VIDEO</button>
        
        <div class="logs" id="logs">Waiting...</div>
        <div id="video-section"><video id="v-player" controls height="450"></video></div>
        <div id="gallery"></div>

        <script>
            function startBot() { fetch('/start', {method: 'POST'}); logUpdate(">>> STARTING..."); }
            function refreshData() {
                fetch('/status').then(r=>r.json()).then(d=>{
                    document.getElementById('logs').innerHTML = d.logs.map(l=>`<div>${l}</div>`).join('');
                    document.getElementById('gallery').innerHTML = d.images.map(i=>`<img src="${i}">`).join('');
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
            setInterval(refreshData, 3000);
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
    bt.add_task(run_organic_agent)
    return {"status": "started"}

@app.post("/generate_video")
async def trigger_video():
    files = sorted(glob.glob(f'{CAPTURE_DIR}/monitor_*.jpg'))
    if not files: return {"status": "error"}
    try:
        with imageio.get_writer(VIDEO_PATH, fps=1, format='FFMPEG') as writer:
            for filename in files: writer.append_data(imageio.imread(filename))
        return {"status": "done"}
    except: return {"status": "error"}

# --- VISUAL TAP ---
async def visual_tap(page, element, desc):
    try:
        box = await element.bounding_box()
        if box:
            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2
            
            await page.evaluate(f"""
                var dot = document.createElement('div');
                dot.style.position = 'absolute'; left = '{x}px'; top = '{y}px';
                dot.style.width = '20px'; height = '20px'; background = 'rgba(255, 0, 255, 0.6)';
                dot.style.borderRadius = '50%'; border = '2px solid white'; zIndex = '99999';
                document.body.appendChild(dot);
            """)
            
            log_msg(f"👆 Tapping {desc}...")
            await page.touchscreen.tap(x, y)
            await asyncio.sleep(1) 
            return True
    except: pass
    return False

# --- MAIN AGENT ---
async def run_organic_agent():
    try:
        for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)
        
        current_number = generate_hk_number()
        log_msg(f"📱 Testing with HK Number: {current_number}")

        async with async_playwright() as p:
            # --- FIX: MODIFY DEVICE DICT BEFORE PASSING ---
            pixel_5 = p.devices['Pixel 5'].copy() # Copy original settings
            
            # Override User Agent in the dictionary itself
            pixel_5['user_agent'] = "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.101 Mobile Safari/537.36"
            
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                proxy=PROXY_CONFIG
            )

            # Now pass unpacked dict (no duplicate user_agent arg)
            context = await browser.new_context(
                **pixel_5,
                locale="en-US"
            )
            
            page = await context.new_page()

            # --- STEP 1: LANDING PAGE ---
            log_msg("🚀 Loading Base URL...")
            try:
                await page.goto(BASE_URL, timeout=60000)
            except:
                log_msg("❌ Network Fail")
                await browser.close()
                return

            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
            await page.screenshot(path=f"{CAPTURE_DIR}/01_landing.jpg")

            # --- STEP 1.5: CLICK REGISTER ---
            reg_btn = page.get_by_text("Register", exact=True).first
            if await reg_btn.count() == 0: reg_btn = page.get_by_role("button", name="Register").first
            
            if await reg_btn.count() > 0:
                await visual_tap(page, reg_btn, "Register Button")
                await asyncio.sleep(4)
                await page.screenshot(path=f"{CAPTURE_DIR}/02_register_clicked.jpg")
            else:
                log_msg("⚠️ Check: Maybe directly on register page?")

            # --- STEP 2: AGREE TO TERMS ---
            # Click Text to tick
            agreement_text = page.get_by_text("Huawei ID User Agreement").first
            if await agreement_text.count() > 0:
                await visual_tap(page, agreement_text, "Agreement Checkbox")
                await asyncio.sleep(1)
            
            # Click Agree/Next
            agree_btn = page.get_by_text("Agree", exact=True).first
            if await agree_btn.count() == 0: agree_btn = page.get_by_text("Next", exact=True).first
            
            if await agree_btn.count() > 0:
                await visual_tap(page, agree_btn, "Agree/Next")
                await asyncio.sleep(4)
                await page.screenshot(path=f"{CAPTURE_DIR}/03_after_agree.jpg")
            else:
                log_msg("❌ Agree Button Not Found")

            # --- STEP 3: DATE OF BIRTH ---
            log_msg("📅 Handling DOB...")
            
            # SWIPE DOWN GESTURE (To change year)
            for _ in range(3):
                await page.mouse.move(200, 500)
                await page.mouse.down()
                await page.mouse.move(200, 700, steps=10) # Pull down
                await page.mouse.up()
                await asyncio.sleep(0.5)

            await page.screenshot(path=f"{CAPTURE_DIR}/04_dob_scrolled.jpg")
            
            # Click Next
            dob_next = page.get_by_text("Next", exact=True).first
            if await dob_next.count() > 0:
                await visual_tap(page, dob_next, "DOB Next")
                await asyncio.sleep(4)
            
            # --- STEP 4: USE PHONE ---
            use_phone = page.get_by_text("Use phone number", exact=False).first
            if await use_phone.count() > 0:
                await visual_tap(page, use_phone, "Use Phone Option")
                await asyncio.sleep(2)

            await page.screenshot(path=f"{CAPTURE_DIR}/05_phone_input_screen.jpg")

            # --- STEP 5: INPUT & GET CODE ---
            inp = page.locator("input[type='tel']").first
            if await inp.count() == 0: inp = page.locator("input").first
            
            if await inp.count() > 0:
                await visual_tap(page, inp, "Phone Input")
                
                for char in current_number:
                    await page.keyboard.type(char)
                    await asyncio.sleep(0.2)
                
                await page.touchscreen.tap(10, 100) # Blur
                
                # GET CODE
                get_code = page.locator(".get-code-btn").first
                if await get_code.count() == 0: get_code = page.get_by_text("Get code", exact=False).first
                
                if await get_code.count() > 0:
                    await visual_tap(page, get_code, "GET CODE BUTTON")
                    log_msg("⏳ Waiting 10s for result...")
                    await asyncio.sleep(10)
                    
                    await page.screenshot(path=f"{CAPTURE_DIR}/06_final_result.jpg")
                    
                    if len(page.frames) > 1:
                        log_msg("🎉 BINGO! CAPTCHA DETECTED!")
                    elif await page.get_by_text("Unexpected problem").count() > 0:
                        log_msg("🛑 Error Popup Detected")
                    else:
                        log_msg("❓ No popup? Check screenshot.")
                else:
                    log_msg("❌ Get Code button not found")
            else:
                log_msg("❌ Input field not found")

            log_msg("✅ Session End")
            await browser.close()

    except Exception as e:
        log_msg(f"❌ Error: {str(e)}")