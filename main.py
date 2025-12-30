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

# 🇺🇸 USA LINK
MAGIC_URL = "https://id5.cloud.huawei.com/CAS/portal/userRegister/regbyphone.html?regionCode=us&countryCode=us&lang=en-us"

# 👇 PROXY CONFIG 👇
PROXY_CONFIG = {
    "server": "http://142.111.48.253:7030", 
    "username": "wwwsyxzg", 
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

# --- HELPER: GENERATE REALISTIC US NUMBER ---
def generate_california_number():
    # 310 is Los Angeles (Matches our Timezone)
    prefix = random.randint(200, 999)
    suffix = random.randint(1000, 9999)
    return f"310{prefix}{suffix}"

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Huawei Smart Rotator</title>
        <style>
            body { background: #000; color: #00e676; font-family: monospace; padding: 20px; text-align: center; }
            button { padding: 15px 30px; font-weight: bold; cursor: pointer; border:none; margin:5px; background: #d50000; color: white; font-size: 16px; border-radius: 5px; }
            .logs { height: 300px; overflow-y: auto; text-align: left; border: 1px solid #333; padding: 10px; color: #fff; background: #111; }
            .gallery img { height: 100px; border: 1px solid #444; margin: 2px; }
            #video-section { display:none; margin-top:20px; }
        </style>
    </head>
    <body>
        <h1>🔄 SMART ROTATION & RETRY BOT</h1>
        <button onclick="startBot()">🚀 START SMART LOOP</button>
        <button onclick="refreshData()" style="background: #0277bd;">🔄 REFRESH</button>
        <button onclick="makeVideo()" style="background: #2e7d32;">🎬 MAKE VIDEO</button>
        
        <div class="logs" id="logs">Waiting...</div>
        <div id="video-section"><video id="v-player" controls width="600"></video></div>
        <div id="gallery"></div>

        <script>
            function startBot() { fetch('/start', {method: 'POST'}); logUpdate(">>> STARTING SMART LOOP..."); }
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
    bt.add_task(run_smart_retry_agent)
    return {"status": "started"}

@app.post("/generate_video")
async def trigger_video():
    files = sorted(glob.glob(f'{CAPTURE_DIR}/monitor_*.jpg'))
    if not files: return {"status": "error"}
    try:
        with imageio.get_writer(VIDEO_PATH, fps=2, format='FFMPEG') as writer:
            for filename in files: writer.append_data(imageio.imread(filename))
        return {"status": "done"}
    except: return {"status": "error"}

# --- INJECTION ---
FINGERPRINT_INJECTION = """
(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Google Inc. (Intel)';
        if (parameter === 37446) return 'ANGLE (Intel, Intel(R) HD Graphics 630 Direct3D11 vs_5_0 ps_5_0)';
        return getParameter(parameter);
    };
})();
"""

# --- MAIN LOGIC ---
async def run_smart_retry_agent():
    try:
        for f in glob.glob(f"{CAPTURE_DIR}/*"): os.remove(f)
        
        # Initial Number
        current_number = generate_california_number()

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--start-maximized", "--no-sandbox"],
                proxy=PROXY_CONFIG
            )

            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                timezone_id="America/Los_Angeles",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await page.add_init_script(FINGERPRINT_INJECTION)

            log_msg("🚀 Navigating...")
            try:
                await page.goto(MAGIC_URL, timeout=60000)
            except:
                log_msg("❌ Network Error")
                await browser.close()
                return

            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            await page.screenshot(path=f"{CAPTURE_DIR}/monitor_00.jpg")

            # FIND INPUT
            log_msg("🔍 Locating Input Field...")
            inp = page.locator("input.huawei-input").first
            if await inp.count() == 0: inp = page.locator("input[type='text']").first
            
            if await inp.count() == 0:
                log_msg("❌ Input Not Found")
                await browser.close()
                return

            # FIRST FILL
            log_msg(f"✍️ Typing Initial Number: {current_number}")
            await inp.click()
            await inp.fill(current_number)
            await page.mouse.click(500, 500) # Blur

            # --- SMART LOOP ---
            retry_count = 0
            max_retries = 50
            
            while retry_count < max_retries:
                retry_count += 1
                
                # --- LOGIC TO CHANGE NUMBER EVERY 2 TRIES ---
                if retry_count > 1 and retry_count % 2 != 0: 
                    # Jab 3, 5, 7... try ho, tab number badlo (Effectively every 2 failed attempts)
                    log_msg("♻️ Changing Phone Number (Rotation Strategy)...")
                    current_number = generate_california_number()
                    
                    # Clear and Type New Number
                    await inp.click()
                    await inp.fill("") # Clear field
                    await asyncio.sleep(0.5)
                    await inp.type(current_number, delay=50)
                    log_msg(f"🆕 New Number Set: {current_number}")
                    await page.mouse.click(500, 500) # Blur
                    await asyncio.sleep(1)

                # 1. CLICK GET CODE
                btn = page.locator(".get-code-btn").first
                if await btn.count() == 0: btn = page.get_by_text("Get code").first
                
                if await btn.count() > 0:
                    log_msg(f"🖱️ [Try {retry_count}] Clicking 'Get Code'...")
                    await btn.click(force=True)
                else:
                    log_msg("❌ Button Lost!")
                    break

                # 2. MONITOR RESULT
                error_detected = False
                
                # Fast check (3 seconds)
                for i in range(3):
                    await asyncio.sleep(1)
                    await page.screenshot(path=f"{CAPTURE_DIR}/monitor_loop_{retry_count}_{i}.jpg")
                    
                    # Check for Captcha (SUCCESS)
                    if len(page.frames) > 1:
                        log_msg("🎉 BINGO! CAPTCHA DETECTED! Stopping Loop.")
                        await page.screenshot(path=f"{CAPTURE_DIR}/monitor_SUCCESS.jpg")
                        await browser.close()
                        return

                    # Check for Error Popup
                    if await page.get_by_text("An unexpected problem").count() > 0:
                        error_detected = True
                        break # Stop waiting, handle error immediately
                
                if error_detected:
                    log_msg(f"🛑 Error Detected on Try {retry_count}!")
                    
                    # Find OK Button
                    ok_btn = page.locator("div.hwid-dialog-btn").filter(has_text="OK").first
                    if await ok_btn.count() == 0: ok_btn = page.get_by_text("OK", exact=True).first
                    
                    if await ok_btn.count() > 0:
                        # Wait a bit before clicking OK ensures dialog is interactable
                        await asyncio.sleep(1) 
                        log_msg("👊 Clicking 'OK' Button...")
                        await ok_btn.click(force=True)
                        
                        # --- THE 10 SECOND WAIT ---
                        log_msg("⏳ Waiting 10 seconds (Cool down)...")
                        await asyncio.sleep(10)
                    else:
                        log_msg("⚠️ Can't find OK button, waiting 5s anyway...")
                        await asyncio.sleep(5)
                else:
                    log_msg("❓ No popup detected yet, continuing...")

            log_msg("❌ Max retries reached.")
            await browser.close()

    except Exception as e:
        log_msg(f"❌ Error: {str(e)}")