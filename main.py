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

# 🇺🇸 USA LINK
MAGIC_URL = "https://id5.cloud.huawei.com/CAS/portal/userRegister/regbyphone.html?regionCode=ru&countryCode=ru&lang=en-us"

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
    if len(logs) > 100: logs.pop()

# --- HELPER: READ NUMBERS FROM FILE ---
def get_next_number():
    if not os.path.exists(NUMBERS_FILE):
        return None
    
    with open(NUMBERS_FILE, "r") as f:
        lines = f.readlines()
    
    # Filter empty lines and strip whitespace
    numbers = [line.strip() for line in lines if line.strip()]
    
    if not numbers:
        return None
        
    # Get the first number
    current_number = numbers[0]
    
    # Remove it from file (so we don't reuse it immediately) and append to end (rotation)
    # OR you can just delete it. Here I am rotating the list.
    new_lines = numbers[1:] + [current_number]
    
    with open(NUMBERS_FILE, "w") as f:
        f.write("\n".join(new_lines))
        
    return current_number

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei Number File Bot</title>
        <style>
            body { background: #1a1a1a; color: #ff9800; font-family: monospace; padding: 20px; text-align: center; }
            button { padding: 15px 30px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #d84315; color: white; font-size: 16px; border-radius: 5px; }
            .logs { height: 350px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; color: #ccc; background: #000; margin-bottom: 20px; }
            .gallery img { height: 110px; border: 1px solid #444; margin: 3px; border-radius: 4px; }
            #video-section { display:none; margin-top:20px; border: 1px dashed #555; padding: 10px; }
        </style>
    </head>
    <body>
        <h1>📁 FILE-BASED NUMBER TESTER</h1>
        <p style="color: #aaa;">Reading from: numbers.txt</p>
        <button onclick="startBot()">🚀 START FILE PROCESSING</button>
        <button onclick="refreshData()" style="background: #1565c0;">🔄 REFRESH</button>
        <button onclick="makeVideo()" style="background: #2e7d32;">🎬 MAKE VIDEO</button>
        
        <div class="logs" id="logs">Waiting...</div>
        <div id="video-section"><video id="v-player" controls width="600"></video></div>
        <div id="gallery"></div>

        <script>
            function startBot() { fetch('/start', {method: 'POST'}); logUpdate(">>> READING NUMBERS.TXT..."); }
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
    bt.add_task(run_file_agent)
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

# --- VISUAL CLICK ---
async def visual_click(page, element, desc):
    box = await element.bounding_box()
    if box:
        x = box['x'] + box['width'] / 2
        y = box['y'] + box['height'] / 2
        
        # Red Dot
        await page.evaluate(f"""
            var dot = document.createElement('div');
            dot.style.position = 'absolute'; left = '{x}px'; top = '{y}px';
            dot.style.width = '15px'; height = '15px'; background = 'red';
            dot.style.borderRadius = '50%'; border = '2px solid yellow'; zIndex = '99999';
            document.body.appendChild(dot);
        """)
        
        log_msg(f"🖱️ Moving to {desc}...")
        await page.mouse.move(x, y, steps=30)
        await asyncio.sleep(0.5)
        
        log_msg(f"🔴 CLICKING {desc}...")
        await page.mouse.down()
        await asyncio.sleep(0.2)
        await page.mouse.up()
        return True
    return False

# --- SLOW TYPE ---
async def slow_type(page, text):
    log_msg(f"⌨️ Typing {text} slowly...")
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(0.5) # Slow typing
    log_msg("✅ Typing Complete")

# --- MAIN LOGIC ---
async def run_file_agent():
    try:
        for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)
        
        while True: # Loop through numbers forever (or until file empty)
            
            # 1. GET NEW NUMBER FROM FILE
            current_number = get_next_number()
            if not current_number:
                log_msg("❌ No numbers found in numbers.txt! Stopping.")
                return
            
            log_msg(f"📱 Processing Number: {current_number}")

            async with async_playwright() as p:
                # 2. LAUNCH BROWSER (Rotating Proxy via Webshare)
                # Webshare rotates IP on every new connection
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--start-maximized", "--no-sandbox"],
                    proxy=PROXY_CONFIG
                )

                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    timezone_id="America/Los_Angeles", # USA Timezone
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
                await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")

                log_msg("🚀 Loading Website...")
                try:
                    await page.goto(MAGIC_URL, timeout=60000)
                except:
                    log_msg("❌ Network Error (Proxy Failed), Retrying...")
                    await browser.close()
                    continue

                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_01_loaded.jpg")

                # FIND INPUT
                inp = page.locator("input.huawei-input").first
                if await inp.count() == 0: inp = page.locator("input[type='text']").first
                
                if await inp.count() == 0:
                    log_msg("❌ Input Not Found")
                    await browser.close()
                    continue # Try next number/proxy

                # FILL NUMBER
                await visual_click(page, inp, "Input Field")
                await slow_type(page, current_number)
                await page.mouse.click(500, 500) # Blur
                await page.screenshot(path=f"{CAPTURE_DIR}/monitor_02_typed.jpg")
                await asyncio.sleep(1)

                # --- TRY CLICKING GET CODE (Max 2 attempts per number) ---
                retry_count = 0
                max_retries_per_number = 2 
                number_failed = False

                while retry_count < max_retries_per_number:
                    retry_count += 1
                    
                    # Click Button
                    btn = page.locator(".get-code-btn").first
                    if await btn.count() == 0: btn = page.get_by_text("Get code").first
                    
                    if await btn.count() > 0:
                        await visual_click(page, btn, "Get Code Button")
                        log_msg("⏳ Waiting 3s for response...")
                        await asyncio.sleep(3)
                    else:
                        log_msg("❌ Button Lost!")
                        break

                    # Check Result
                    await page.screenshot(path=f"{CAPTURE_DIR}/monitor_response_{current_number}_{retry_count}.jpg")
                    
                    # 1. Success (Captcha)
                    if len(page.frames) > 1:
                        log_msg("🎉 BINGO! CAPTCHA DETECTED! Stopping.")
                        await page.screenshot(path=f"{CAPTURE_DIR}/monitor_SUCCESS.jpg")
                        await browser.close()
                        return # STOP EVERYTHING

                    # 2. Error Check
                    if await page.get_by_text("An unexpected problem").count() > 0:
                        log_msg(f"🛑 Error on Try {retry_count} for {current_number}")
                        
                        # Find OK
                        ok_btn = page.locator("div.hwid-dialog-btn").filter(has_text="OK").first
                        if await ok_btn.count() == 0: ok_btn = page.get_by_text("OK", exact=True).first
                        
                        if await ok_btn.count() > 0:
                            await visual_click(page, ok_btn, "OK Button")
                            
                            # 10s Wait
                            log_msg("⏳ Waiting 10s cooldown...")
                            await asyncio.sleep(10)
                        else:
                            log_msg("⚠️ OK button missing")
                            await asyncio.sleep(5)
                    else:
                        # No error, no captcha? Wait a bit more
                        log_msg("❓ No popup, checking again...")
                        await asyncio.sleep(2)
                
                # If loop finishes without success
                log_msg(f"❌ Failed 2 times with {current_number}. Rotating to next number...")
                await browser.close()
                # Loop continues to next number in file

    except Exception as e:
        log_msg(f"❌ Critical Error: {str(e)}")