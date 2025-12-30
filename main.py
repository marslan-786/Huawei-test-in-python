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
NUMBERS_FILE = "numbers.txt"

# 📱 MOBILE LINK (The Golden Link)
MAGIC_URL = "https://id5.cloud.huawei.com/CAS/mobile/standard/register/wapRegister.html#/wapRegister/regByPhone?countryCode=ru&regionCode=ru&lang=en-us"

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

# --- FILE HELPER ---
def get_next_number():
    if not os.path.exists(NUMBERS_FILE): return None
    with open(NUMBERS_FILE, "r") as f: lines = f.readlines()
    numbers = [line.strip() for line in lines if line.strip()]
    if not numbers: return None
    current_number = numbers[0]
    new_lines = numbers[1:] + [current_number]
    with open(NUMBERS_FILE, "w") as f: f.write("\n".join(new_lines))
    return current_number

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei Chrome Clone</title>
        <style>
            body { background: #fff; color: #333; font-family: sans-serif; padding: 20px; text-align: center; }
            button { padding: 15px 30px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #4285f4; color: white; border-radius: 4px; }
            .logs { height: 350px; overflow-y: auto; text-align: left; border: 1px solid #ddd; padding: 10px; background: #f1f1f1; margin-bottom: 20px; font-family: monospace; }
            .gallery img { height: 250px; border: 4px solid #333; margin: 3px; border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
            #video-section { display:none; margin-top:20px; }
        </style>
    </head>
    <body>
        <h1 style="color: #4285f4;">📱 CHROME MOBILE CLONE</h1>
        <p>Emulating: Android 13 / Chrome 121 (High Density)</p>
        <button onclick="startBot()">🚀 START CHROME AGENT</button>
        <button onclick="refreshData()" style="background: #34a853;">🔄 REFRESH</button>
        <button onclick="makeVideo()" style="background: #ea4335;">🎬 MAKE VIDEO</button>
        
        <div class="logs" id="logs">Waiting...</div>
        <div id="video-section"><video id="v-player" controls height="450"></video></div>
        <div id="gallery"></div>

        <script>
            function startBot() { fetch('/start', {method: 'POST'}); logUpdate(">>> INITIALIZING CHROME EMULATION..."); }
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
    bt.add_task(run_chrome_agent)
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

# --- VISUAL TAP (Strictly Touch Event) ---
async def visual_tap(page, element, desc):
    try:
        box = await element.bounding_box()
        if box:
            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2
            
            # Visual Marker (Green for Success)
            await page.evaluate(f"""
                var dot = document.createElement('div');
                dot.style.position = 'absolute'; left = '{x}px'; top = '{y}px';
                dot.style.width = '20px'; height = '20px'; background = 'rgba(0, 255, 0, 0.6)';
                dot.style.borderRadius = '50%'; border = '2px solid white'; zIndex = '99999';
                document.body.appendChild(dot);
            """)
            
            log_msg(f"👆 Tapping {desc}...")
            # FORCE TAP - No Mouse Click
            await page.touchscreen.tap(x, y)
            await asyncio.sleep(0.5)
            return True
    except Exception as e:
        log_msg(f"⚠️ Tap Failed: {str(e)}")
    return False

# --- MAIN AGENT ---
async def run_chrome_agent():
    try:
        for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)
        
        while True:
            current_number = get_next_number()
            if not current_number:
                log_msg("❌ No numbers left!")
                return
            
            log_msg(f"📱 Processing: {current_number}")

            async with async_playwright() as p:
                # 🔥 EXACT CHROME ANDROID CONFIGURATION 🔥
                # Ye settings Kiwi Browser se alag hain, aur 100% Chrome jaisi hain
                
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--use-gl=egl", # Mobile Graphics rendering
                        "--disable-dev-shm-usage"
                    ],
                    proxy=PROXY_CONFIG
                )

                context = await browser.new_context(
                    # 1. Official User Agent of Chrome on Pixel 5 (Android 13)
                    user_agent="Mozilla/5.0 (Linux; Android 13; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
                    
                    # 2. Viewport (Pixel 5 Exact Size)
                    viewport={"width": 393, "height": 851},
                    
                    # 3. High Pixel Density (Kiwi aksar isko miss karta hai)
                    device_scale_factor=3.0,
                    
                    # 4. Mobile Flags
                    is_mobile=True,
                    has_touch=True,
                    
                    timezone_id="America/Los_Angeles",
                    locale="en-US"
                )
                
                page = await context.new_page()

                log_msg("🚀 Loading Huawei (Chrome Mobile View)...")
                try:
                    await page.goto(MAGIC_URL, timeout=60000)
                except:
                    log_msg("❌ Network Fail")
                    await browser.close()
                    continue

                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(3)
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_01_loaded.jpg")

                # FIND INPUT
                inp = page.locator("input[type='tel']").first
                if await inp.count() == 0: inp = page.locator("input").first
                
                if await inp.count() > 0:
                    await visual_tap(page, inp, "Input")
                    
                    # Mobile Keyboard Simulation
                    for char in current_number:
                        await page.keyboard.type(char)
                        await asyncio.sleep(0.2)
                    
                    # Tap outside to close keyboard/blur
                    await page.touchscreen.tap(10, 100)
                    await page.screenshot(path=f"{CAPTURE_DIR}/monitor_02_typed.jpg")
                else:
                    log_msg("❌ Input Not Found")
                    await browser.close()
                    continue

                # TRY GET CODE
                retry_count = 0
                max_retries = 2
                
                while retry_count < max_retries:
                    retry_count += 1
                    
                    # Finding Button
                    btn = page.locator(".get-code-btn").first
                    if await btn.count() == 0: btn = page.get_by_text("Get code", exact=False).first
                    
                    if await btn.count() > 0:
                        # KIWI BROWSER ISSUE FIX:
                        # Hum 'tap' use kar rahay hain, 'click' nahi.
                        await visual_tap(page, btn, "Get Code")
                        
                        log_msg("⏳ Waiting 5s for response...")
                        await asyncio.sleep(5)
                    else:
                        log_msg("❌ Button Not Found")
                        break
                    
                    await page.screenshot(path=f"{CAPTURE_DIR}/monitor_{current_number}_{retry_count}.jpg")

                    # CHECK FOR CAPTCHA (SUCCESS)
                    # Agar link Chrome Mobile pe chal gaya, to yahan Captcha ana chahiye
                    if len(page.frames) > 1 or await page.locator("iframe").count() > 0:
                        log_msg("🎉 BINGO! CAPTCHA DETECTED! (Chrome Emulation Worked)")
                        await page.screenshot(path=f"{CAPTURE_DIR}/monitor_SUCCESS.jpg")
                        await browser.close()
                        return # SUCCESS!

                    # CHECK ERROR
                    if await page.get_by_text("Unexpected problem").count() > 0:
                        log_msg(f"🛑 Blocked on Try {retry_count}")
                        
                        ok_btn = page.get_by_text("OK").first
                        if await ok_btn.count() > 0:
                            await visual_tap(page, ok_btn, "OK")
                            log_msg("⏳ Waiting 10s...")
                            await asyncio.sleep(10)
                        else:
                            await asyncio.sleep(5)
                    else:
                        log_msg("❓ No response? Retrying...")
                        await asyncio.sleep(2)

                log_msg("❌ Failed. Rotating Number...")
                await browser.close()

    except Exception as e:
        log_msg(f"❌ Error: {str(e)}")